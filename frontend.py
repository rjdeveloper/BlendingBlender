import streamlit as st
import requests
import json
import base64
import re
from datetime import datetime
import time
import html

st.set_page_config(page_title="Titanium Studio | CNC", layout="wide", page_icon="⚙️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@500&display=swap');

    .stApp {
        background: #f5f5f7;
        font-family: 'Inter', sans-serif;
    }

    .deployment-bar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 60px;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        padding: 0 30px;
        z-index: 1000;
        justify-content: space-between;
    }

    .engine-title {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 1.1rem;
        color: #1d1d1f;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .segment-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        background: #ffffff;
        border: 1px solid #d9d9d9;
        color: #111111;
        padding: 6px 12px;
        border-radius: 8px;
        margin-bottom: 6px;
        display: inline-block;
    }

    .segment-badge.idle { color: #6e6e73; }
    .segment-badge.active { color: #007AFF; border-color: #007AFF; }
    .segment-badge.done { color: #1d1d1f; border-color: #1d1d1f; }

    .main .block-container {
        padding-top: 80px !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="deployment-bar">
    <div class="engine-title">
        <div style="background:#007AFF; width:24px; height:24px; border-radius:6px;"></div>
        TITANIUM STUDIO <span style="color:#86868b; font-weight:300;">| ENGINE V2.0</span>
    </div>
    <div style="font-size:0.8rem; color:#007AFF; font-weight:600; background:rgba(0,122,255,0.1); padding:4px 12px; border-radius:20px;">
        STATUS: READY
    </div>
</div>
""", unsafe_allow_html=True)


CANNED_DIRECTOR_PROMPT = (
    "Director self-test: produce a 30s green-screen 2D Grease Pencil news anchor reading a placeholder script. "
    "Mouth cycles through M_Closed, M_Open, M_Smile, M_O. "
    "Save to c:\\blundai\\director\\out.mp4."
)
DIRECTOR_STARTER_PROMPT = (
    "Anchor segment 1: anchor enters frame, idle pose, mouth M_Closed. "
    "30s total. Green screen behind."
)


if "messages" not in st.session_state:
    st.session_state.messages = []
if "pipeline_logs" not in st.session_state:
    st.session_state.pipeline_logs = []
if "previous_mode" not in st.session_state:
    st.session_state.previous_mode = "cnc"
if "director_starter_injected" not in st.session_state:
    st.session_state.director_starter_injected = False
if "director_starter_text" not in st.session_state:
    st.session_state.director_starter_text = ""
if "self_test_pending" not in st.session_state:
    st.session_state.self_test_pending = False
if "current_segment" not in st.session_state:
    st.session_state.current_segment = None
if "total_segments" not in st.session_state:
    st.session_state.total_segments = None
if "plan_preview_injected" not in st.session_state:
    st.session_state.plan_preview_injected = False


with st.sidebar:
    st.markdown("### 🎛️ Parameters")
    mode_label = st.radio("Mode", ["CNC Designer", "Director"], index=0, horizontal=True)
    mode = "director" if mode_label == "Director" else "cnc"

    if mode == "director" and st.session_state.previous_mode != "director":
        st.session_state.director_starter_injected = False
    if mode != "director":
        st.session_state.director_starter_injected = False
        st.session_state.director_starter_text = ""
    st.session_state.previous_mode = mode

    export_dxf = st.checkbox("AutoCAD DXF", value=True)
    export_step = st.checkbox("Solid STEP", value=False)

    st.divider()

    if mode == "director":
        st.markdown("### Director Self-Test")
        if st.button("Run Sample Director Pipeline", use_container_width=True, type="primary"):
            st.session_state.self_test_pending = True
            st.session_state.messages.append({"role": "user", "content": CANNED_DIRECTOR_PROMPT})
            st.session_state.pipeline_logs = [
                f"{datetime.now().strftime('%H:%M:%S')} SELF-TEST triggered with canned prompt"
            ]
            st.session_state.plan_preview_injected = False
            st.session_state.current_segment = None
            st.session_state.total_segments = None
            st.rerun()
        st.divider()

    st.markdown("### 📎 Attachments")
    uploaded_file = st.file_uploader("Upload Schematic", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")

    if st.button("🔄 Clear Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pipeline_logs = []
        st.session_state.current_segment = None
        st.session_state.total_segments = None
        st.session_state.plan_preview_injected = False
        st.session_state.director_starter_injected = False
        st.session_state.director_starter_text = ""
        st.rerun()


def build_full_window_text():
    audit_text = "\n".join(st.session_state.pipeline_logs) if st.session_state.pipeline_logs else "No pipeline events."
    chat_lines = []
    for msg in st.session_state.messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        chat_lines.append(f"[{role}] {content}")
    chat_text = "\n\n".join(chat_lines) if chat_lines else "No chat messages."
    return f"=== PIPELINE AUDIT LOGS ===\n{audit_text}\n\n=== CHAT TRANSCRIPT ===\n{chat_text}"


def render_segment_badge(placeholder):
    cur = st.session_state.current_segment
    total = st.session_state.total_segments
    if cur is None or total is None:
        klass = "idle"
        text = "Segment - / -"
    elif cur >= total:
        klass = "done"
        text = f"Segment {cur} / {total}"
    else:
        klass = "active"
        text = f"Segment {cur} / {total}"
    placeholder.markdown(
        f"<div class='segment-badge {klass}'>{html.escape(text)}</div>",
        unsafe_allow_html=True,
    )


def render_logs(placeholder, lines):
    text = "\n".join(lines) if lines else "No pipeline events yet. Submit a request to see planner / executioner / tool activity."
    placeholder.markdown(
        f"""
<div style="height:330px; overflow:auto; background:#ffffff; border:1px solid #d9d9d9; border-radius:10px; padding:10px;">
  <pre style="margin:0; color:#111111; white-space:pre-wrap; font-family:'JetBrains Mono', monospace; font-size:12px;">{html.escape(text)}</pre>
</div>
""",
        unsafe_allow_html=True,
    )


chat_col, monitor_col = st.columns([2, 1], gap="large")

with chat_col:
    if mode == "director" and not st.session_state.director_starter_injected:
        st.session_state.director_starter_text = DIRECTOR_STARTER_PROMPT
        st.session_state.director_starter_injected = True

    if mode == "director" and st.session_state.director_starter_text:
        st.caption("Director starter prompt - edit then send below or press 'Use this prompt' to send as-is.")
        st.session_state.director_starter_text = st.text_area(
            "Director starter",
            value=st.session_state.director_starter_text,
            height=80,
            label_visibility="collapsed",
            key="director_starter_textarea",
        )
        send_starter = st.button("Use this prompt", use_container_width=False)
        if send_starter and st.session_state.director_starter_text.strip():
            st.session_state.messages.append(
                {"role": "user", "content": st.session_state.director_starter_text.strip()}
            )
            st.session_state.director_starter_text = ""
            st.session_state.plan_preview_injected = False
            st.session_state.current_segment = None
            st.session_state.total_segments = None
            st.rerun()

    chat_container = st.container(height=620, border=False)
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant", avatar="⚙️"):
                    st.markdown(message["content"])

with monitor_col:
    st.markdown("### Live Pipeline Logs")
    segment_placeholder = st.empty()
    render_segment_badge(segment_placeholder)
    logs_placeholder = st.empty()
    render_logs(logs_placeholder, st.session_state.pipeline_logs)

    st.markdown("#### Copyable Audit Logs")
    audit_logs_text = "\n".join(st.session_state.pipeline_logs) if st.session_state.pipeline_logs else "No pipeline events."
    st.text_area("All audit events", value=audit_logs_text, height=170, key="all_audit_logs_text")

    st.markdown("#### Copyable Full Window")
    full_window_text = build_full_window_text()
    st.text_area("Audit logs + full chat transcript", value=full_window_text, height=190, key="full_window_copy_text")
    st.download_button(
        "Download full run log",
        data=full_window_text,
        file_name=f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True,
    )


user_input = st.chat_input("Enter engineering command...")

if user_input:
    image_to_send = None
    if uploaded_file:
        image_to_send = base64.b64encode(uploaded_file.read()).decode("utf-8")
    elif any(ext in user_input.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]) and "http" in user_input:
        url_match = re.search(r'https?://\S+', user_input)
        if url_match:
            image_to_send = url_match.group(0)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.plan_preview_injected = False
    st.session_state.current_segment = None
    st.session_state.total_segments = None
    st.rerun()


if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.spinner("Processing..."):
        try:
            last_msg = st.session_state.messages[-1]
            st.session_state.pipeline_logs.append(
                f"{datetime.now().strftime('%H:%M:%S')} Request queued from UI."
            )
            payload = {
                "message": last_msg["content"],
                "history": st.session_state.messages[:-1],
                "image": None,
                "settings": {"dxf": export_dxf, "step": export_step},
                "mode": mode,
            }
            start_resp = requests.post("http://localhost:8000/chat/start", json=payload, timeout=10)
            if start_resp.status_code != 200:
                st.session_state.pipeline_logs.append(
                    f"{datetime.now().strftime('%H:%M:%S')} Backend error starting run: HTTP {start_resp.status_code}"
                )
                st.error(f"Engine Error: could not start run ({start_resp.status_code})")
                st.stop()

            request_id = start_resp.json().get("request_id")
            st.session_state.pipeline_logs.append(
                f"{datetime.now().strftime('%H:%M:%S')} Started run id: {request_id}"
            )
            st.session_state.self_test_pending = False

            max_polls = 240  # ~8 minutes at 2s interval
            final_response = None
            for _ in range(max_polls):
                status_resp = requests.get(
                    f"http://localhost:8000/chat/status/{request_id}", timeout=4
                )
                if status_resp.status_code != 200:
                    st.session_state.pipeline_logs.append(
                        f"{datetime.now().strftime('%H:%M:%S')} Poll failed: HTTP {status_resp.status_code}"
                    )
                    time.sleep(2)
                    continue

                status_json = status_resp.json()
                trace = status_json.get("trace", []) or []
                stamped = [f"{datetime.now().strftime('%H:%M:%S')} {step}" for step in trace]
                if stamped:
                    st.session_state.pipeline_logs = stamped

                seg_cur = status_json.get("segment_current")
                seg_total = status_json.get("segment_total")
                if seg_cur is not None:
                    st.session_state.current_segment = seg_cur
                if seg_total is not None:
                    st.session_state.total_segments = seg_total

                plan_preview = status_json.get("plan_preview")
                if (
                    plan_preview
                    and not st.session_state.plan_preview_injected
                    and mode == "director"
                ):
                    plan_preview_msg = (
                        "**Planner segment list (preview):**\n\n"
                        f"```json\n{plan_preview}\n```\n"
                        "_Continuing with scaffold and per-segment script generation..._"
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": plan_preview_msg}
                    )
                    st.session_state.plan_preview_injected = True

                render_segment_badge(segment_placeholder)
                render_logs(logs_placeholder, st.session_state.pipeline_logs)

                status = status_json.get("status")
                if status == "completed":
                    final_response = status_json.get("response", "")
                    break
                if status == "failed":
                    err = status_json.get("error", "Unknown error")
                    st.session_state.pipeline_logs.append(
                        f"{datetime.now().strftime('%H:%M:%S')} Run failed: {err}"
                    )
                    st.error(f"Engine Error: {err}")
                    st.stop()

                time.sleep(2)

            if final_response is None:
                st.session_state.pipeline_logs.append(
                    f"{datetime.now().strftime('%H:%M:%S')} Polling timeout after 2s checks."
                )
                st.error("Engine timeout: no final response yet. Check logs panel.")
                st.stop()

            st.session_state.messages.append({"role": "assistant", "content": final_response})
            st.rerun()
        except Exception as e:
            st.session_state.pipeline_logs.append(
                f"{datetime.now().strftime('%H:%M:%S')} Engine exception: {str(e)}"
            )
            st.error(f"Engine Error: {e}")
