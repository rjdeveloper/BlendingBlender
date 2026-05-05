import bpy

print("--- FFMPEG FORMATS ---")
try:
    items = bpy.types.FFMPEGSettings.bl_rna.properties['format'].enum_items
    print([item.identifier for item in items])
except Exception as e:
    print(f"ERROR: {e}")

print("--- FFMPEG CODECS ---")
try:
    items = bpy.types.FFMPEGSettings.bl_rna.properties['codec'].enum_items
    print([item.identifier for item in items])
except Exception as e:
    print(f"ERROR: {e}")
