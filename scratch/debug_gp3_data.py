import bpy

# Create a Grease Pencil object
bpy.ops.object.grease_pencil_add()
gp = bpy.context.active_object.data

print("GP_DATA_DIR:", dir(gp))
if hasattr(gp, 'layers'):
    layer = gp.layers.new("TestLayer")
    print("LAYER_DIR:", dir(layer))
    # In GP3, layers might not have 'frames'
    if hasattr(layer, 'drawings'):
        print("LAYER_HAS_DRAWINGS")
    if hasattr(layer, 'frames'):
        print("LAYER_HAS_FRAMES")
