import os
import re
import asyncio
import json
from typing import TypedDict, Annotated, List, Any, Optional, Callable, Dict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, END
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import tool
from logger_utils import log_audit, natural_error_response

from director.scaffolding import get_scaffold_script
from director.bpy_helpers import snippets_for_intent

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    mcp_tools: List[Any]
    plan: str
    mode: str
    trace: Annotated[List[str], lambda x, y: x + y]
    progress_callback: Any


class BlenderMCPToolbox:
    def __init__(self):
        self.session = None
        self.cleanup = None
        self.tools = []

    async def connect(self):
        env = os.environ.copy()
        env["DISABLE_TELEMETRY"] = "true"
        server_params = StdioServerParameters(
            command="blender-mcp",
            args=[],
            env=env
        )
        self.cleanup = stdio_client(server_params)
        read, write = await self.cleanup.__aenter__()
        self.session = ClientSession(read, write)
        await self.session.__aenter__()
        await self.session.initialize()
        tools_list = await self.session.list_tools()
        self.tools = tools_list.tools
        return self.tools

    async def call_tool(self, name: str, arguments: dict):
        result = await self.session.call_tool(name, arguments)
        return result.content

    async def disconnect(self):
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self.cleanup:
            await self.cleanup.__aexit__(None, None, None)


toolbox = BlenderMCPToolbox()

planner_model = ChatGroq(
    temperature=0.1,
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

executioner_model = ChatGroq(
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="meta-llama/llama-4-scout-17b-16e-instruct"
)


def mcp_to_langchain_tool(mcp_tool):
    def wrapper(**kwargs):
        """Dynamic wrapper for Blender MCP tools."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(toolbox.call_tool(mcp_tool.name, kwargs))

    lc_tool = tool(wrapper)
    lc_tool.name = mcp_tool.name
    lc_tool.description = mcp_tool.description
    return lc_tool


def _read_skill(mode: str) -> str:
    path = "director_skill.md" if mode == "director" else "skill.md"
    with open(path, "r") as f:
        return f.read()


# =====================================================================
# DIRECTOR MODE PIPELINE - chunked script generation, no bind_tools
# =====================================================================

DEFAULT_DIRECTOR_SEGMENTS: List[Dict[str, Any]] = [
    {"segment": 1, "frames": [1, 288], "intent": "anchor entrance and idle pose with green screen visible"},
    {"segment": 2, "frames": [289, 576], "intent": "lip-sync segment 1 with M_Closed and M_Open mouth states, subtle head sway"},
    {"segment": 3, "frames": [577, 864], "intent": "lip-sync segment 2 with M_Smile and M_O mouth states, hand gesture"},
    {"segment": 4, "frames": [865, 1152], "intent": "lip-sync segment 3 with full mouth cycle, minor body movement"},
    {"segment": 5, "frames": [1153, 1440], "intent": "settle pose, final hold, fade to closed mouth"},
]


def _strip_code_fences(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    fence = re.match(r"^```(?:python)?\s*\n", t)
    if fence:
        t = t[fence.end():]
        if t.endswith("```"):
            t = t[: -3]
        elif "```" in t:
            t = t.rsplit("```", 1)[0]
    return t.strip()


def _parse_segments(raw: str) -> List[Dict[str, Any]]:
    try:
        match = re.search(r"\[\s*\{.*?\}\s*\]", raw, re.DOTALL)
        candidate = match.group(0) if match else raw.strip()
        data = json.loads(candidate)
        if not isinstance(data, list) or not data:
            raise ValueError("empty list")
        cleaned: List[Dict[str, Any]] = []
        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                continue
            frames = item.get("frames")
            if not (isinstance(frames, list) and len(frames) == 2):
                frames = [(i - 1) * 144 + 1, i * 144]
            cleaned.append({
                "segment": int(item.get("segment", i)),
                "frames": [int(frames[0]), int(frames[1])],
                "intent": str(item.get("intent", "")).strip() or DEFAULT_DIRECTOR_SEGMENTS[min(i - 1, 4)]["intent"],
            })
        return cleaned if cleaned else DEFAULT_DIRECTOR_SEGMENTS
    except Exception as e:
        log_audit("DIRECTOR_PLAN_PARSE_FAIL", {"error": str(e), "raw_preview": raw[:300]})
        return DEFAULT_DIRECTOR_SEGMENTS


def _mcp_text(result: Any) -> str:
    try:
        return "".join(
            getattr(item, "text", str(item)) if not isinstance(item, str) else item
            for item in result
        )
    except Exception:
        return str(result)


def _emit(progress_callback: Optional[Callable[[str], None]], msg: str):
    if callable(progress_callback):
        try:
            progress_callback(msg)
        except Exception:
            pass


async def run_director_pipeline(
    user_input: str,
    history: List[BaseMessage],
    settings: Optional[dict],
    progress_callback: Optional[Callable[[str], None]],
) -> Dict[str, Any]:
    skill = _read_skill("director")
    trace_collected: List[str] = []

    def push(msg: str):
        trace_collected.append(msg)
        _emit(progress_callback, msg)

    push("Director: planner producing JSON segment list (5 segments, 30s @ 24fps).")

    planner_prompt = (
        "You are the Director Mode planner. Output ONLY a JSON array (no prose, no code fences) "
        "of exactly 5 segments for a 60-second 24fps green-screen 2D Grease Pencil anchor animation. "
        "Total frame range: 1..1440. Each segment ~288 frames.\n"
        "Schema: [{\"segment\": int, \"frames\": [start_frame, end_frame], \"intent\": \"short imperative\"}]\n"
        "Cover: entrance/idle, two lip-sync passes, subtle motion, settle/hold."
    )
    planner_messages = [
        SystemMessage(content=skill),
        HumanMessage(content=f"{planner_prompt}\n\nUser request: {user_input}"),
    ]
    try:
        plan_resp = await planner_model.ainvoke(planner_messages)
        plan_raw = plan_resp.content if isinstance(plan_resp.content, str) else str(plan_resp.content)
    except Exception as e:
        push(f"Planner error: {e}. Falling back to default segment list.")
        plan_raw = ""

    log_audit("DIRECTOR_PLAN_RAW", {"text": plan_raw[:500]})
    segments = _parse_segments(plan_raw) if plan_raw else DEFAULT_DIRECTOR_SEGMENTS
    push(f"Plan ready ({len(segments)} segments).")
    plan_json_pretty = json.dumps(segments, indent=2)
    push("PLAN_PREVIEW:\n" + plan_json_pretty)

    push("Scaffold: setting up green screen / camera / lights / render config.")
    try:
        scaffold_result = await toolbox.call_tool("execute_blender_code", {"code": get_scaffold_script()})
        scaffold_text = _mcp_text(scaffold_result)
        if "SCAFFOLD_OK" in scaffold_text:
            push("Scaffold complete.")
        else:
            push(f"Scaffold finished but marker missing. Output preview: {scaffold_text[:200]}")
    except Exception as e:
        push(f"Scaffold failed: {e}")
        log_audit("DIRECTOR_SCAFFOLD_FAIL", {"error": str(e)})

    total = len(segments)
    for i, seg in enumerate(segments, 1):
        seg_id = f"Segment {i}/{total}"
        intent = seg.get("intent", "")
        frames = seg.get("frames", [1, 144])
        push(f"{seg_id}: generating script ({intent})")

        snippets = snippets_for_intent(intent)
        script_gen_prompt = (
            "Write a single complete Python bpy script for ONE animation segment. "
            "Output ONLY runnable Python. No markdown fences. No explanations.\n\n"
            f"Frames: {frames[0]}..{frames[1]}\n"
            f"Intent: {intent}\n\n"
            "REUSE existing scene objects when present: bpy.data.objects.get('Anchor'), 'GreenScreen', 'AnchorCam'. "
            "If 'Anchor' is missing, create it using the helper. "
            "2D Grease Pencil only. No 3D primitives. No file saves; rendering is handled at finalize.\n\n"
            "Helper snippets you may paste at top and call:\n"
            f"{snippets}\n\n"
            "End the script with: print('SEGMENT_OK')"
        )

        try:
            sg_resp = await executioner_model.ainvoke([
                SystemMessage(content=skill),
                HumanMessage(content=script_gen_prompt),
            ])
            script_text = _strip_code_fences(
                sg_resp.content if isinstance(sg_resp.content, str) else str(sg_resp.content)
            )
        except Exception as e:
            push(f"{seg_id}: script generation error: {e}")
            log_audit("DIRECTOR_SCRIPT_GEN_FAIL", {"segment": i, "error": str(e)})
            continue

        log_audit("DIRECTOR_SCRIPT_GEN", {"segment": i, "preview": script_text[:300]})
        push(f"{seg_id}: executing")
        try:
            exec_result = await toolbox.call_tool("execute_blender_code", {"code": script_text})
            exec_text = _mcp_text(exec_result)
        except Exception as e:
            exec_text = f"ERROR: {e}"

        ok = ("SEGMENT_OK" in exec_text) and not any(
            tok in exec_text for tok in ("Traceback", "ERROR:", "Error:")
        )
        if ok:
            push(f"{seg_id}: monitor ok")
            log_audit("DIRECTOR_SEGMENT_OK", {"segment": i})
            continue

        push(f"{seg_id}: monitor flagged issue; one patch attempt")
        log_audit("DIRECTOR_SEGMENT_FAIL", {"segment": i, "output_preview": exec_text[:300]})
        patch_prompt = (
            "The previous segment script failed. Rewrite ONLY the script to fix the issue. "
            "Output runnable Python only, no fences, no prose. End with print('SEGMENT_OK').\n\n"
            f"PREVIOUS OUTPUT:\n{exec_text[:600]}\n\n"
            f"PREVIOUS SCRIPT:\n{script_text[:1800]}"
        )
        try:
            patch_resp = await executioner_model.ainvoke([
                SystemMessage(content=skill),
                HumanMessage(content=patch_prompt),
            ])
            patch_text = _strip_code_fences(
                patch_resp.content if isinstance(patch_resp.content, str) else str(patch_resp.content)
            )
            patch_result = await toolbox.call_tool("execute_blender_code", {"code": patch_text})
            patch_out = _mcp_text(patch_result)
        except Exception as e:
            patch_out = f"ERROR: {e}"
        if "SEGMENT_OK" in patch_out:
            push(f"{seg_id}: patch ok")
            log_audit("DIRECTOR_SEGMENT_PATCH_OK", {"segment": i})
        else:
            push(f"{seg_id}: patch failed, continuing")
            log_audit("DIRECTOR_SEGMENT_PATCH_FAIL", {"segment": i, "preview": patch_out[:300]})

    push("Finalize: saving project and rendering mp4.")
    finalize_script = (
        "import bpy\n"
        "bpy.ops.wm.save_as_mainfile(filepath=r\"c:\\blundai\\director\\out.blend\")\n"
        "bpy.ops.render.render(animation=True)\n"
        "print('RENDER_OK', bpy.context.scene.render.filepath)\n"
    )
    try:
        fin_result = await toolbox.call_tool("execute_blender_code", {"code": finalize_script})
        fin_text = _mcp_text(fin_result)
    except Exception as e:
        fin_text = f"ERROR: {e}"

    if "RENDER_OK" in fin_text:
        push("Finalize: render complete.")
    else:
        push(f"Finalize: render did not confirm. Output: {fin_text[:200]}")
    log_audit("DIRECTOR_FINALIZE", {"output_preview": fin_text[:300]})

    summary = (
        "Director run complete.\n\n"
        f"**Plan ({len(segments)} segments)**\n\n"
        f"```json\n{plan_json_pretty}\n```\n\n"
        f"**Output**\n- Video: `c:\\blundai\\director\\out.mp4`\n- Project: `c:\\blundai\\director\\out.blend`\n\n"
        f"**Finalize log preview**\n```\n{fin_text[:600]}\n```"
    )

    return {"response": summary, "trace": trace_collected, "plan": segments}


# =====================================================================
# CNC MODE PIPELINE - existing planner/executioner/tools graph
# =====================================================================

async def plan_task(state: AgentState):
    last_msg = state['messages'][-1]
    mode = state.get('mode', 'cnc')
    progress_callback = state.get("progress_callback")

    planning_msg = f"Planner started ({mode} mode)."
    _emit(progress_callback, planning_msg)

    skill_content = _read_skill(mode)

    tool_categories = {
        "Modeling": "Direct bpy scripting and mesh manipulation",
        "Scene": "Viewport screenshots, object list, and scene metadata",
        "Assets": "Polyhaven and Sketchfab library access",
        "Export": "DXF, STEP, STL, and .blend file generation",
    }
    planner_prompt = (
        f"You are the Lead CNC Engineer. Create a technical modeling plan.\n"
        f"Capabilities: {tool_categories}\n\n"
        "Plan format:\n"
        "1. Goal: [Summary]\n"
        "2. Detailed Steps: [Step-by-step bpy/tool operations]\n"
        "3. Auto-Render: ALWAYS end with a high-quality Cycles/Eevee render command to show the final result.\n\n"
        "BE CONCISE."
    )

    if isinstance(last_msg.content, list):
        planner_messages = [
            SystemMessage(content=skill_content),
            HumanMessage(content=[{"type": "text", "text": planner_prompt}] + last_msg.content),
        ]
    else:
        planner_messages = [
            SystemMessage(content=skill_content),
            HumanMessage(content=f"{planner_prompt}\n\nUser Request: {last_msg.content}"),
        ]

    response = await planner_model.ainvoke(planner_messages)
    planned_msg = "Planner finished and produced an execution plan."
    _emit(progress_callback, planned_msg)
    return {"plan": response.content, "trace": [planning_msg, planned_msg]}


async def call_executioner(state: AgentState):
    tool_names = [t.name for t in state['mcp_tools']]
    mode = state.get('mode', 'cnc')
    current_skill = _read_skill(mode)
    progress_callback = state.get("progress_callback")

    last_msg = state['messages'][-1]
    if isinstance(last_msg, ToolMessage):
        exec_instruction = (
            f"TOOL RESULT RECEIVED:\n{last_msg.content}\n\n"
            f"Continue with the next step in the plan:\n{state['plan']}\n\n"
            "Acknowledge the success and either call the next tool or confirm completion."
        )
    else:
        exec_instruction = (
            f"AUTONOMOUS EXECUTION MODE:\nYou HAVE FULL ACCESS to these tools: {tool_names}.\n"
            f"YOUR PLAN: {state['plan']}\n"
            "You should call an appropriate tool immediately whenever execution is required.\n\n"
            "ACT NOW: Execute the first step using the appropriate tool. NO PREAMBLE."
        )

    messages = [
        SystemMessage(content=current_skill),
        SystemMessage(content=exec_instruction),
    ] + state['messages']

    langchain_tools = [mcp_to_langchain_tool(t) for t in state['mcp_tools']]
    bound_model = executioner_model.bind_tools(langchain_tools)
    executioner_start_msg = "Executioner deciding next tool action."
    _emit(progress_callback, executioner_start_msg)
    response = await bound_model.ainvoke(messages)

    if not getattr(response, "tool_calls", None):
        no_tool_msg = "Executioner returned prose without tool calls; forcing retry."
        _emit(progress_callback, no_tool_msg)
        correction_instruction = (
            "Your previous reply did not call tools. Convert your own plan into an immediate tool call now. "
            "Return ONLY tool calls. If creating geometry, call execute_code."
        )
        retry_messages = messages + [
            AIMessage(content=response.content),
            HumanMessage(content=correction_instruction),
        ]
        response = await bound_model.ainvoke(retry_messages)
        retry_success_msg = (
            f"Executioner retry produced {len(response.tool_calls)} tool call(s)."
            if getattr(response, "tool_calls", None)
            else "Executioner retry still produced no tool calls."
        )
        _emit(progress_callback, retry_success_msg)
        return {"messages": [response], "trace": [executioner_start_msg, no_tool_msg, retry_success_msg]}

    calls_msg = f"Executioner produced {len(response.tool_calls)} tool call(s)."
    _emit(progress_callback, calls_msg)
    return {"messages": [response], "trace": [executioner_start_msg, calls_msg]}


async def execute_tools(state: AgentState):
    last_message = state['messages'][-1]
    tool_messages = []

    mode = state.get('mode', 'cnc')
    progress_callback = state.get("progress_callback")
    trace_updates: List[str] = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        start_msg = f"Running tool: {tool_name}"
        trace_updates.append(start_msg)
        _emit(progress_callback, start_msg)

        log_audit("TOOL_CALL", {"name": tool_name, "args": tool_args})

        try:
            result = await toolbox.call_tool(tool_name, tool_args)
            content = "".join([item.text if hasattr(item, 'text') else str(item) for item in result])

            if "error" in content.lower():
                content = natural_error_response(content, mode)
                log_audit("TOOL_ERROR_MAPPED", {"original": content})
            else:
                log_audit("TOOL_SUCCESS", {"name": tool_name})
                success_msg = f"Tool succeeded: {tool_name}"
                trace_updates.append(success_msg)
                _emit(progress_callback, success_msg)

        except Exception as e:
            content = natural_error_response(str(e), mode)
            log_audit("TOOL_EXCEPTION", {"error": str(e)})
            error_msg = f"Tool failed: {tool_name} -> {str(e)}"
            trace_updates.append(error_msg)
            _emit(progress_callback, error_msg)

        tool_messages.append(ToolMessage(tool_call_id=tool_call["id"], content=content))

    return {"messages": tool_messages, "trace": trace_updates}


def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    return "continue" if last_message.tool_calls else "end"


workflow = StateGraph(AgentState)
workflow.add_node("planner", plan_task)
workflow.add_node("executioner", call_executioner)
workflow.add_node("tools", execute_tools)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "executioner")
workflow.add_conditional_edges("executioner", should_continue, {"continue": "tools", "end": END})
workflow.add_edge("tools", "executioner")
compiled_app = workflow.compile()


# =====================================================================
# ENTRY POINT - routes director vs cnc
# =====================================================================

async def chat_with_agent(
    user_input: str,
    history: List[BaseMessage] = [],
    image_data: Optional[str] = None,
    settings: Optional[dict] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
):
    if not toolbox.session:
        await toolbox.connect()

    mode = settings.get('mode', 'cnc') if settings else 'cnc'

    smart_history = history[-10:] if len(history) > 10 else history
    for msg in smart_history:
        if isinstance(msg.content, list):
            msg.content = "".join(
                item.get("text", "") for item in msg.content
                if isinstance(item, dict) and item.get("type") == "text"
            )

    if mode == "director":
        result = await run_director_pipeline(user_input, smart_history, settings, progress_callback)
        _emit(progress_callback, "Run completed.")
        return result

    if image_data:
        image_url_val = image_data if image_data.startswith("http") else f"data:image/jpeg;base64,{image_data}"
        content = [
            {"type": "text", "text": f"{user_input} (Settings: {settings})"},
            {"type": "image_url", "image_url": {"url": image_url_val}},
        ]
        user_message = HumanMessage(content=content)
    else:
        user_message = HumanMessage(content=f"{user_input} (Settings: {settings})")

    inputs = {
        "messages": smart_history + [user_message],
        "mcp_tools": toolbox.tools,
        "plan": "",
        "mode": mode,
        "trace": [],
        "progress_callback": progress_callback,
    }
    result = await compiled_app.ainvoke(inputs)
    final_trace = result.get("trace", [])
    _emit(progress_callback, "Run completed.")
    return {"response": result["messages"][-1].content, "trace": final_trace}
