import bpy

print("--- OBJECT OPERATORS ---")
for op in dir(bpy.ops.object):
    if 'grease' in op.lower() or 'gp' in op.lower() or 'add' in op.lower():
        print(f"object.{op}")
