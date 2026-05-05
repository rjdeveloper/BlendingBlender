"""Compact bpy helper snippets fed to the Script Generator's prompt.

Patterns adapted from njanakiev/blender-scripting (MIT) - frame handler and
render-animation invocation - plus a minimal Grease Pencil 2D anchor template
authored for this project. Keep these strings short. The Script Generator
receives only the snippet relevant to the current segment's intent so the
context stays small.
"""

GP_ANCHOR_TEMPLATE = r"""
import bpy

def ensure_gp_anchor(name="Anchor"):
    obj = bpy.data.objects.get(name)
    if obj and obj.type == 'GREASEPENCIL':
        return obj
    # Blender 5.1 / GP3
    bpy.ops.object.grease_pencil_add(location=(0.0, 0.0, 2.5))
    obj = bpy.context.active_object
    obj.name = name
    gp = obj.data
    if "Body" not in gp.layers:
        gp.layers.new("Body")
    if "Mouth" not in gp.layers:
        gp.layers.new("Mouth")

    body = gp.layers["Body"]
    try:
        if 1 not in [f.frame_number for f in body.frames]:
            body.frames.new(1)
    except:
        pass
    bf = body.frames[0]
    
    # GP3 stroke creation
    import math
    if hasattr(bf, "drawing"):
        drawing = bf.drawing
        # Head (Circle)
        drawing.add_strokes([24])
        head = drawing.strokes[-1]
        for i, p in enumerate(head.points):
            a = (i / 24.0) * 2.0 * math.pi
            p.position = (0.4 * math.cos(a), 0.0, 0.4 * math.sin(a) + 0.5)
        # Body (Square)
        drawing.add_strokes([4])
        body_stroke = drawing.strokes[-1]
        body_stroke.points[0].position = (-0.5, 0.0, 0.0)
        body_stroke.points[1].position = (0.5, 0.0, 0.0)
        body_stroke.points[2].position = (0.5, 0.0, -1.0)
        body_stroke.points[3].position = (-0.5, 0.0, -1.0)
    else:
        # Fallback for GP2 (older Blender)
        if not bf.strokes:
            head = bf.strokes.new()
            head.points.add(count=24)
            for i, p in enumerate(head.points):
                a = (i / 24.0) * 2.0 * math.pi
                p.co = (0.4 * math.cos(a), 0.0, 0.4 * math.sin(a) + 0.5)
            body_stroke = bf.strokes.new()
            body_stroke.points.add(count=4)
            body_stroke.points[0].co = (-0.5, 0.0, 0.0)
            body_stroke.points[1].co = (0.5, 0.0, 0.0)
            body_stroke.points[2].co = (0.5, 0.0, -1.0)
            body_stroke.points[3].co = (-0.5, 0.0, -1.0)
    return obj
"""

MOUTH_CYCLE_HELPER = r"""
import bpy

MOUTH_STATES = ["M_Closed", "M_Open", "M_Closed", "M_Smile", "M_Open", "M_O", "M_Closed"]

def write_mouth_cycle(anchor_name="Anchor", start_frame=1, end_frame=1440, hold_frames=6):
    obj = bpy.data.objects.get(anchor_name)
    if obj is None or obj.type != 'GREASEPENCIL':
        return False
    gp = obj.data
    if "Mouth" not in gp.layers:
        gp.layers.new("Mouth", set_active=False)
    mouth = gp.layers["Mouth"]
    obj["mouth_state"] = MOUTH_STATES[0]
    obj.keyframe_insert(data_path='["mouth_state"]', frame=start_frame)
    f = start_frame
    idx = 0
    while f <= end_frame:
        state = MOUTH_STATES[idx % len(MOUTH_STATES)]
        obj["mouth_state"] = state
        obj.keyframe_insert(data_path='["mouth_state"]', frame=f)
        if f not in [k.frame_number for k in mouth.frames]:
            mouth.frames.new(f)
        f += hold_frames
        idx += 1
    return True
"""

FRAME_HANDLER_TEMPLATE = r"""
import bpy

def attach_frame_handler():
    def _handler(scene):
        anchor = bpy.data.objects.get("Anchor")
        if anchor is None:
            return
        f = scene.frame_current
        anchor.location.x = 0.05 * ((f % 48) - 24) / 24.0
    bpy.app.handlers.frame_change_pre.clear()
    bpy.app.handlers.frame_change_pre.append(_handler)
"""

RENDER_ANIMATION_HELPER = r"""
import bpy

def render_animation_to_mp4():
    bpy.ops.render.render(animation=True)
"""

SNIPPETS = {
    "gp_anchor": GP_ANCHOR_TEMPLATE,
    "mouth_cycle": MOUTH_CYCLE_HELPER,
    "frame_handler": FRAME_HANDLER_TEMPLATE,
    "render_animation": RENDER_ANIMATION_HELPER,
}


def snippets_for_intent(intent: str) -> str:
    intent_lower = (intent or "").lower()
    parts = []
    if any(k in intent_lower for k in ("anchor", "entrance", "idle", "body", "head")):
        parts.append(GP_ANCHOR_TEMPLATE)
    if any(k in intent_lower for k in ("mouth", "lip", "talk", "speak")):
        parts.append(MOUTH_CYCLE_HELPER)
    if any(k in intent_lower for k in ("motion", "sway", "subtle", "frame_handler", "movement")):
        parts.append(FRAME_HANDLER_TEMPLATE)
    if any(k in intent_lower for k in ("render", "finalize", "export", "mp4")):
        parts.append(RENDER_ANIMATION_HELPER)
    if not parts:
        parts = [GP_ANCHOR_TEMPLATE, MOUTH_CYCLE_HELPER]
    return "\n".join(parts)
