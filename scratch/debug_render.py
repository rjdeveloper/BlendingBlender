import bpy

# Check the type of scene.render.ffmpeg
print("FFMPEG_TYPE:", type(bpy.context.scene.render.ffmpeg))

# List properties of scene.render
print("RENDER_PROPS:", [p for p in dir(bpy.context.scene.render) if 'ffmpeg' in p.lower()])
