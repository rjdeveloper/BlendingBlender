# Director Mode Skill (2D Green-Screen Anchor POC)

## Scope
- 2D animation only. No 3D rigs, NLA, drivers, or shape-key armatures.
- Green-screen anchor on a flat solid background.
- 24 fps. 60 seconds total = frames 1..1440.

## Required techniques
- Anchor body: Grease Pencil object created with `bpy.ops.object.gpencil_add(type='EMPTY')` then add strokes.
- Background: a single plane behind the anchor, material with emissive color `(0.0, 1.0, 0.0)` (chroma-key green `#00FF00`).
- Mouth states (placeholder, no audio): swap GP layers/materials between the four canonical names below.

## Canonical mouth states
- `M_Closed`
- `M_Open`
- `M_Smile`
- `M_O`

Cycle order for placeholder lip-sync (every 6 frames): `M_Closed -> M_Open -> M_Closed -> M_Smile -> M_Open -> M_O -> M_Closed`.

## Output
- Save final render to `c:\blundai\director\out.mp4` (FFmpeg, H.264, 1920x1080, 24fps).
- Save the project file to `c:\blundai\director\out.blend`.

## Hard rules
- NEVER call `bpy.ops.export_scene.dxf` or any CAD exporter.
- NEVER add 3D primitives (cubes, spheres, IK chains).
- Reuse existing scene objects when present (`bpy.data.objects.get(name)`).
- All scripts must be standalone Python that runs inside Blender via `execute_blender_code`.
