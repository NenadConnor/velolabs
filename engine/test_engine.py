import json, math, tempfile, unittest
from pathlib import Path
from schema import Design, Part, Feature, Joint
from kernel import local_shape, placements, build
from simulate import solve

class EngineeringTests(unittest.TestCase):
    def test_plate_dimensions_volume_and_holes(self):
        p=Part(id='plate',name='Plate',features=[Feature(name='body',shape='box',size=(100,60,8))]+[
            Feature(name='hole',shape='cylinder',operation='subtract',radius=3,height=10,position=(x,y,0)) for x in (-40,40) for y in (-20,20)])
        s=local_shape(p); bounds=s.bounding_box()
        for actual,expected in zip(bounds.size,(100,60,8)): self.assertAlmostEqual(actual,expected,places=6)
        self.assertAlmostEqual(s.volume,100*60*8-4*math.pi*3**2*8,places=5)
        self.assertEqual(len(s.solids()),1)
        self.assertTrue(s.is_valid)

    def test_reject_disconnected_parts_and_cycles(self):
        p=Part(id='bad',name='Bad',features=[Feature(name='one',shape='box'),Feature(name='two',shape='box',position=(100,0,0))])
        with self.assertRaises(ValueError): local_shape(p)
        with self.assertRaises(ValueError): Design(title='Cycle',summary='',parts=[p.model_copy(update={'parent':'bad'})])

    def test_parent_and_joint_transform(self):
        from cadgen import build123d as bd
        parent=Part(id='base',name='Base',position=(100,0,0),rotation=(0,0,90),features=[Feature(name='base',shape='box')])
        child=Part(id='arm',name='Arm',parent='base',position=(20,0,0),joint=Joint(type='revolute',axis='z',value=90,min=0,max=180),features=[Feature(name='arm',shape='box')])
        transforms=placements(Design(title='Mechanism',summary='',parts=[parent,child]))
        point=(transforms['arm']*bd.Vertex(10,0,0)).center()
        for actual,expected in zip(point,(90,20,0)): self.assertAlmostEqual(actual,expected,places=5)

    def test_axial_fea_against_closed_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            part=Part(id='beam',name='Beam',features=[Feature(name='bar',shape='box',size=(100,10,10))])
            design=Design(title='Axial benchmark',summary='100 x 10 x 10 mm bar',parts=[part])
            (directory/'spec.json').write_text(design.model_dump_json(),'utf-8')
            build(directory/'spec.json',directory)
            request={'part_id':'beam','axis':'x','force':[1000,0,0],'young_mpa':200000,'poisson':.3,'yield_mpa':250,'mesh_divisions':12}
            (directory/'request.json').write_text(json.dumps(request),'utf-8')
            solve(directory/'beam.step',directory/'request.json',directory/'simulation.json')
            result=json.loads((directory/'simulation.json').read_text('utf-8'))
            exact=1000*100/(200000*100)
            self.assertLess(abs(result['max_displacement_mm']-exact)/exact,.03)
            self.assertAlmostEqual(result['reaction_n'][0],-1000,places=4)
            self.assertLess(result['relative_residual'],1e-7)

if __name__=='__main__': unittest.main()

