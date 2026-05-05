import bpy

bpy.ops.object.grease_pencil_add()
gp = bpy.context.active_object.data
layer = gp.layers.new("TestLayer")
frame = layer.frames.new(1)
print("FRAME_DIR:", dir(frame))
if hasattr(frame, 'drawing'):
    print("FRAME_HAS_DRAWING")
    drawing = frame.drawing
    print("DRAWING_DIR:", dir(drawing))
    if hasattr(drawing, 'strokes'):
        print("DRAWING_HAS_STROKES")
if hasattr(frame, 'strokes'):
    print("FRAME_HAS_STROKES")
