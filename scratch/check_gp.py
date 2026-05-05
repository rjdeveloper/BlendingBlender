import bpy

# List grease pencil operators
gp_ops = [op for op in dir(bpy.ops.object) if 'gpencil' in op]
print(f"GP_OPERATORS: {gp_ops}")

# Check if FFMPEG is valid for the current scene
try:
    bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
    print("SET_FFMPEG: SUCCESS")
except Exception as e:
    print(f"SET_FFMPEG: FAILED - {e}")
