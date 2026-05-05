import bpy
import json

# Get available file formats
formats = bpy.types.RenderSettings.bl_rna.properties['image_settings'].fixed_type.properties['file_format'].enum_items.keys()
print(f"AVAILABLE_FORMATS: {list(formats)}")
