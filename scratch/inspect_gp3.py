import bpy

# Check grease_pencil operators
print("GREASE_PENCIL_DIR:", dir(bpy.ops.grease_pencil))

# Check object types
print("OBJECT_TYPES:", [item.identifier for item in bpy.types.Object.bl_rna.properties['type'].enum_items])
