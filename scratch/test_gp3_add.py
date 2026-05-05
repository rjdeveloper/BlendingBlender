import bpy

bpy.ops.object.grease_pencil_add()
gp = bpy.context.active_object.data
layer = gp.layers.new("TestLayer")
frame = layer.frames.new(1)
drawing = frame.drawing

print("ADD_STROKES_DOC:", drawing.add_strokes.__doc__)
# Try adding a stroke
drawing.add_strokes([24])
print("STROKES_COUNT:", len(drawing.strokes))
stroke = drawing.strokes[0]
print("STROKE_DIR:", dir(stroke))
print("POINTS_COUNT:", len(stroke.points))
