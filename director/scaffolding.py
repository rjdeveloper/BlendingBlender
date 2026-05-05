"""Hardcoded Blender scaffolding for Director mode 2D green-screen anchor POC.

Sent to MCP execute_code ONCE at the beginning of every Director run. No Groq.
Sets up: clean scene, green chroma-key plane backdrop, locked camera, two-point
lighting, and FFmpeg/H.264 render config at 1920x1080 / 24fps for 30s (frames 1..720).
"""

OUTPUT_DIR = r"c:\blundai\director"
RENDER_PATH = OUTPUT_DIR + r"\out.mp4"
BLEND_PATH = OUTPUT_DIR + r"\out.blend"
TOTAL_FRAMES = 1440
FPS = 24

SCAFFOLD_SCRIPT = r"""
import bpy
import os

OUTPUT_DIR = r"c:\blundai\director"
RENDER_PATH = os.path.join(OUTPUT_DIR, "out.mp4")
BLEND_PATH = os.path.join(OUTPUT_DIR, "out.blend")

os.makedirs(OUTPUT_DIR, exist_ok=True)

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 1440
scene.render.fps = 24
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
try:
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
except:
    scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = RENDER_PATH

if scene.world is None:
    scene.world = bpy.data.worlds.new("DirectorWorld")
scene.world.use_nodes = False
scene.world.color = (0.0, 1.0, 0.0)

# Create objects first
bpy.ops.object.grease_pencil_add(location=(0.0, 4.0, 2.5), rotation=(1.5708, 0.0, 0.0))
bpy.ops.mesh.primitive_plane_add(size=20, location=(0.0, 4.0, 2.5), rotation=(1.5708, 0.0, 0.0))
backdrop = bpy.context.active_object
backdrop.name = "GreenScreen"
green_mat = bpy.data.materials.new("GreenScreenMat")
green_mat.use_nodes = True
nodes = green_mat.node_tree.nodes
links = green_mat.node_tree.links
for n in list(nodes):
    nodes.remove(n)
emit = nodes.new(type='ShaderNodeEmission')
emit.inputs['Color'].default_value = (0.0, 1.0, 0.0, 1.0)
emit.inputs['Strength'].default_value = 1.5
out = nodes.new(type='ShaderNodeOutputMaterial')
links.new(emit.outputs['Emission'], out.inputs['Surface'])
backdrop.data.materials.append(green_mat)

bpy.ops.object.camera_add(location=(0.0, -4.0, 2.5), rotation=(1.5708, 0.0, 0.0))
cam = bpy.context.active_object
cam.name = "AnchorCam"
cam.data.lens = 50
scene.camera = cam

bpy.ops.object.light_add(type='AREA', location=(-2.5, -2.5, 4.0))
key = bpy.context.active_object
key.name = "KeyLight"
key.data.energy = 600
key.data.size = 2.0

bpy.ops.object.light_add(type='AREA', location=(2.5, -2.5, 3.0))
fill = bpy.context.active_object
fill.name = "FillLight"
fill.data.energy = 250
fill.data.size = 2.0

# Render settings last
try:
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
except:
    scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = RENDER_PATH

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

print("SCAFFOLD_OK frames=1..1440 fps=24 res=1920x1080 backdrop=GreenScreen camera=AnchorCam")
"""


def get_scaffold_script() -> str:
    return SCAFFOLD_SCRIPT
