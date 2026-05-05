import bpy

# Check for grease pencil in bpy.ops
print("OBJECT_OPS:", [op for op in dir(bpy.ops.object) if 'gp' in op.lower()])
print("GREASE_PENCIL_OPS:", [op for op in dir(bpy.ops) if 'gp' in op.lower() or 'grease' in op.lower()])

# Check for render formats again, but look at the actual values
props = bpy.types.RenderSettings.bl_rna.properties['image_settings'].fixed_type.properties['file_format']
print("FORMAT_ENUMS:", [item.identifier for item in props.enum_items])
