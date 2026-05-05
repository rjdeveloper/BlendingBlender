import bpy

print("--- GREASE PENCIL OPERATORS ---")
try:
    for op in dir(bpy.ops.grease_pencil):
        print(f"grease_pencil.{op}")
except:
    pass

print("--- GPENCIL OPERATORS ---")
try:
    for op in dir(bpy.ops.gpencil):
        print(f"gpencil.{op}")
except:
    pass

print("--- OBJECT TYPES ---")
print(list(bpy.types.Object.bl_rna.properties['type'].enum_items.keys()))
