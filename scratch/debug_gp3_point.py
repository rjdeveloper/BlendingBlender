import bpy

bpy.ops.object.grease_pencil_add()
gp = bpy.context.active_object.data
layer = gp.layers.new("TestLayer")
frame = layer.frames.new(1)
drawing = frame.drawing
drawing.add_strokes([24])
stroke = drawing.strokes[0]
point = stroke.points[0]

print("POINT_DIR:", dir(point))
if hasattr(point, 'position'):
    print("POINT_HAS_POSITION")
if hasattr(point, 'co'):
    print("POINT_HAS_CO")
