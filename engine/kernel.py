"""text-to-cad/cadgen adapter; executed in a bounded subprocess per build."""
import json, math, sys
from pathlib import Path
from cadgen import build123d as bd, AssemblyHelper, srgb
from schema import Design

def feature_shape(f):
    if f.shape == 'box': shape = bd.Box(*f.size)
    elif f.shape == 'cylinder': shape = bd.Cylinder(f.radius, f.height)
    elif f.shape == 'sphere': shape = bd.Sphere(f.radius)
    elif f.shape == 'cone': shape = bd.Cone(f.radius, f.top_radius, f.height)
    else:
        shape = bd.extrude(bd.Polygon(*f.points, align=None), amount=f.height)
    return bd.Location(f.position, f.rotation) * shape

def local_shape(part):
    shape = None
    for feature in part.features:
        addition = feature_shape(feature)
        shape = addition if shape is None else shape + addition if feature.operation == 'add' else shape - addition
    if shape is None or not shape.is_valid or len(shape.solids()) != 1 or shape.volume <= 1e-9:
        raise ValueError(f'{part.name}: expected one valid, connected solid; review feature dimensions and placements.')
    shape.label = part.name
    shape.color = srgb(part.color)
    return shape

def placements(design):
    by_id = {p.id:p for p in design.parts}
    result = {}
    def place(part):
        if part.id in result: return result[part.id]
        j = part.joint
        axis = 'xyz'.index(j.axis)
        shift, rotation = [0,0,0], [0,0,0]
        if j.type == 'slider': shift[axis] = j.value
        if j.type == 'revolute': rotation[axis] = j.value
        loc = bd.Location(part.position, part.rotation) * bd.Location(j.origin) * bd.Location(shift, rotation) * bd.Location(tuple(-v for v in j.origin))
        if part.parent: loc = place(by_id[part.parent]) * loc
        result[part.id] = loc
        return loc
    for part in design.parts: place(part)
    return result

def build(spec_path, output):
    design = Design.model_validate_json(Path(spec_path).read_text('utf-8'))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    asm = AssemblyHelper(design.title)
    locations = placements(design)
    meshes, shapes = [], []
    for p in design.parts:
        shape = local_shape(p)
        bd.export_step(shape, output / f'{p.id}.step')
        points, triangles = shape.tessellate(0.1, 0.15)
        if len(triangles) > 180000: raise ValueError('Part mesh is too complex for this version')
        bounds = shape.bounding_box()
        placed = locations[p.id] * shape
        placed.label = p.name; placed.color = srgb(p.color)
        asm.add(placed, p.id)
        shapes.append((p.id, placed))
        meshes.append({'id':p.id, 'vertices':[list(v) for v in points], 'triangles':[list(t) for t in triangles],
            'volume_mm3':shape.volume,'bounds':{'min':list(bounds.min),'max':list(bounds.max)}, 'valid':True})
    bd.export_step(asm.build(), output / 'assembly.step')
    overlaps = []
    for i,(a,sa) in enumerate(shapes):
        for b,sb in shapes[i+1:]:
            intersection = sa & sb
            volume = abs(intersection.volume) if intersection else 0
            if volume > 1e-5: overlaps.append({'a':a,'b':b,'volume_mm3':volume})
    result={'design':design.model_dump(),'meshes':meshes,'checks':{'valid_solids':len(meshes),'overlaps':overlaps,
        'mesh_tolerance_mm':0.1,'manufacturing_tolerance':'Not specified or verified', 'physical_validation':False}}
    (output / 'result.json').write_text(json.dumps(result,allow_nan=False),'utf-8')
    print(json.dumps({'ok':True,'parts':len(meshes)}))

if __name__ == '__main__':
    build(sys.argv[1],sys.argv[2])
