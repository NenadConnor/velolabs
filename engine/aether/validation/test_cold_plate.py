"""Independent analytical values, geometry invariants and API regressions."""
import asyncio
import json
import math
import tempfile
import unittest
from pathlib import Path
from pydantic import ValidationError
from aether.cold_plate.schema import ColdPlateSpecification
from aether.cold_plate.geometry import design, channel_centers
from aether.cold_plate.objective import evaluate
from aether.cold_plate.optimizer import optimize
from aether.cold_plate.report import report
from kernel import local_shape, build

def changed(**sections) -> ColdPlateSpecification:
    raw = ColdPlateSpecification().model_dump()
    for key, values in sections.items():
        raw[key].update(values)
    return ColdPlateSpecification.model_validate(raw)

class SchemaTests(unittest.TestCase):
    def test_invalid_numbers_dimensions_and_combinations(self):
        for section, field, value in [('geometry','length_mm',-1), ('geometry','channel_count',33),
            ('geometry','channel_count',True), ('geometry','channel_width_mm',49),
            ('geometry','channel_height_mm',7), ('geometry','rib_mm',0.2),
            ('thermal','heat_w',-1), ('fluid','volumetric_flow_l_min',-1),
            ('fluid','viscosity_pa_s',float('nan')), ('thermal','footprint_width_mm',61)]:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                changed(**{section: {field: value}})

    def test_flow_and_bounds(self):
        for updates in [{'mass_flow_kg_s':0.1}, {'volumetric_flow_l_min':None}]:
            with self.assertRaises(ValidationError): changed(fluid=updates)
        for bounds in [{'channel_count':{'minimum':1.5,'maximum':8}},
                       {'channel_width_mm':{'minimum':5,'maximum':1}},
                       {'source_code':{'minimum':1,'maximum':2}}]:
            with self.assertRaises(ValidationError): changed(optimization={'bounds':bounds})
        with self.assertRaises(ValidationError): changed(optimization={'maximum_evaluations':257})
        with self.assertRaises(ValidationError): changed(geometry={'python':'print(1)'})

class PhysicsTests(unittest.TestCase):
    def test_square_duct_hand_calculation(self):
        s = ColdPlateSpecification()
        p = evaluate(s).physics
        self.assertTrue(p.correlation_valid)
        velocity = (0.02e-3 / 60) / (8 * 0.002**2)
        re = 998.2 * velocity * 0.002 / 0.001002
        self.assertAlmostEqual(p.velocity_m_s, velocity, places=12)
        self.assertAlmostEqual(p.hydraulic_diameter_m, 0.002, places=12)
        self.assertAlmostEqual(p.reynolds, re, places=12)
        # Independent square-duct series reference; polynomial fit differs ~0.018%.
        self.assertAlmostEqual(p.darcy_friction_factor * re, 56.90832, delta=0.02)
        exact_dp = 56.90832/re * 100 * 998.2 * velocity**2/2
        self.assertLess(abs(p.channel_pressure_drop_pa-exact_dp)/exact_dp, 0.0002)
        self.assertAlmostEqual(p.nusselt, 2.9786, delta=0.003)
        self.assertIsNone(p.total_pressure_drop_pa)
        capacity = p.mass_flow_kg_s * s.fluid.specific_heat_j_kgk
        ua = p.heat_transfer_w_m2k * 8 * 0.008 * 0.2
        wall = s.thermal.inlet_c + s.thermal.heat_w / (capacity * (1-math.exp(-ua/capacity)))
        expected = wall + s.thermal.heat_w * 0.002/(167*0.012)
        self.assertAlmostEqual(p.representative_temperature_c, expected, places=10)

    def test_energy_balance_and_mass_flow_equivalence(self):
        s = ColdPlateSpecification()
        p = evaluate(s).physics
        self.assertAlmostEqual(p.mass_flow_kg_s*s.fluid.specific_heat_j_kgk*p.coolant_rise_k, 10, places=12)
        other = changed(fluid={'volumetric_flow_l_min':None, 'mass_flow_kg_s':p.mass_flow_kg_s})
        self.assertAlmostEqual(evaluate(other).physics.reynolds, p.reynolds, places=12)

    def test_invalid_domains_are_not_feasible(self):
        for flow in (0.0001, 0.05, 3, 10):
            result = evaluate(changed(fluid={'volumetric_flow_l_min':flow}))
            self.assertFalse(result.model_feasible)
            self.assertFalse(result.physics.correlation_valid)
            self.assertIsNone(result.physics.representative_temperature_c)
            self.assertIsNone(result.physics.channel_pressure_drop_pa)

    def test_constraints_and_reports(self):
        result = evaluate(changed(limits={'maximum_channel_pressure_drop_pa':0.001}))
        self.assertFalse(result.model_feasible)
        pressure = next(c for c in result.constraints if c.name == 'Channel pressure drop')
        self.assertEqual(pressure.status, 'FAIL')
        self.assertLess(pressure.margin, 0)
        r = report(ColdPlateSpecification())
        self.assertFalse(r['physical_validation'])
        self.assertFalse(r['high_fidelity_simulation'])
        self.assertFalse(r['geometry_checked'])
        self.assertEqual(r['input_sha256'], report(ColdPlateSpecification())['input_sha256'])
        json.dumps(r, allow_nan=False)

class GeometryTests(unittest.TestCase):
    def test_bounds_layout_connected_volume_and_step(self):
        from cadgen import build123d as bd
        s = ColdPlateSpecification()
        d = design(s)
        shape = local_shape(d.parts[0])
        self.assertTrue(shape.is_valid)
        self.assertEqual(len(shape.solids()), 1)
        self.assertEqual(len(channel_centers(s)), 8)
        for actual, target in zip(shape.bounding_box().size, (200,60,8)):
            self.assertAlmostEqual(actual, target, places=6)
        self.assertAlmostEqual(shape.volume, 200*60*8-8*200*2*2, places=5)
        # Every channel center is empty and every rib midpoint contains material.
        for _, y, z in channel_centers(s):
            self.assertFalse(shape.is_inside((0,y,z)))
        centers = channel_centers(s)
        for a, b in zip(centers, centers[1:]):
            self.assertTrue(shape.is_inside((0,(a[1]+b[1])/2,a[2])))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'spec.json').write_text(d.model_dump_json(), 'utf-8')
            build(path/'spec.json', path)
            imported = bd.import_step(path/'cold_plate.step')
            self.assertTrue(imported.is_valid)
            self.assertEqual(len(imported.solids()), 1)
            self.assertAlmostEqual(imported.volume, shape.volume, places=4)

    def test_adapter_revalidates(self):
        s = ColdPlateSpecification()
        unsafe = s.model_copy(update={'geometry':s.geometry.model_copy(update={'channel_width_mm':100})})
        with self.assertRaises(ValidationError): design(unsafe)

class OptimizationTests(unittest.TestCase):
    def test_reproducible_and_bounded_with_rejections(self):
        s = changed(optimization={'maximum_evaluations':16,
            'bounds':{'channel_count':{'minimum':4,'maximum':32},
                      'channel_width_mm':{'minimum':1,'maximum':10}}})
        first, second = optimize(s), optimize(s)
        self.assertEqual(len(first.candidates), 16)
        self.assertTrue(any(c.rejection for c in first.candidates))
        self.assertIsNotNone(first.best_candidate)
        self.assertEqual(first.best_candidate.model_dump(), second.best_candidate.model_dump())
        for candidate in first.candidates:
            for name, value in candidate.parameters.items():
                self.assertLessEqual(value, s.optimization.bounds[name].maximum)
                self.assertGreaterEqual(value, s.optimization.bounds[name].minimum)

    def test_no_feasible_result_is_explicit(self):
        s = changed(fluid={'volumetric_flow_l_min':10}, optimization={'maximum_evaluations':3})
        result = optimize(s)
        self.assertFalse(result.feasible_found)
        self.assertIsNotNone(result.best_candidate)

class ApiTests(unittest.TestCase):
    def test_planner_validates_data_for_both_contracts(self):
        from unittest.mock import AsyncMock, patch
        import httpx
        import server
        from schema import Design

        async def exercise():
            client = AsyncMock()
            client.post.return_value = httpx.Response(200, json={'message':{'content':'{}'}})
            with patch('server.httpx.AsyncClient') as factory:
                factory.return_value.__aenter__.return_value = client
                planned = await server.chat([], 'test-model', ColdPlateSpecification)
                self.assertIsInstance(planned, ColdPlateSpecification)
                client.post.return_value = httpx.Response(200, json={'message':{'content':'{"python":"print(1)"}'}})
                with self.assertRaises(ValidationError):
                    await server.chat([], 'test-model', ColdPlateSpecification)
                existing = design(ColdPlateSpecification())
                client.post.return_value = httpx.Response(200, json={'message':{'content':existing.model_dump_json()}})
                self.assertIsInstance(await server.chat([], 'test-model'), Design)
        asyncio.run(exercise())

    def test_routes_security_jobs_and_build(self):
        import httpx
        import server
        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='http://test') as client:
                headers = {'X-Velolabs-Token':server.TOKEN} if server.TOKEN else {}
                denied = await client.post('/aether/cold-plate/evaluate', json={}, headers={'origin':'https://invalid.example'})
                self.assertEqual(denied.status_code,403)
                invalid = await client.post('/aether/cold-plate/evaluate', json={'python':'evil'}, headers=headers)
                self.assertEqual(invalid.status_code,422)
                from unittest.mock import patch
                with patch.object(server, 'TOKEN', 'test-only-token'):
                    missing = await client.get('/aether/cold-plate/defaults')
                    self.assertEqual(missing.status_code,401)
                    authenticated = await client.get('/aether/cold-plate/defaults', headers={'X-Velolabs-Token':'test-only-token'})
                    self.assertEqual(authenticated.status_code,200)
                for operation in ('evaluate','optimize','build'):
                    path = '/aether/cold-plate/'+operation
                    payload = ColdPlateSpecification().model_dump()
                    if operation == 'build':
                        path += '?optimization_job_id=' + optimization_id
                        payload = best_spec
                    response = await client.post(path, json=payload, headers=headers)
                    self.assertEqual(response.status_code,200)
                    job_id = response.json()['id']
                    for _ in range(600):
                        job = (await client.get('/jobs/'+job_id, headers=headers)).json()
                        if job['status'] in ('complete','failed'): break
                        await asyncio.sleep(0.1)
                    self.assertEqual(job['status'],'complete', job)
                    if operation == 'optimize':
                        optimization_id = job_id
                        best_spec = job['result']['input_requirements']
                        wrong_spec = ColdPlateSpecification().model_dump()
                        wrong_spec['thermal']['heat_w'] = 11.0
                        mismatch = await client.post('/aether/cold-plate/build?optimization_job_id='+job_id, json=wrong_spec, headers=headers)
                        self.assertEqual(mismatch.status_code,422)
                    if operation == 'build':
                        self.assertTrue(job['result']['report']['geometry_checked'])
                        self.assertEqual(len(job['result']['report']['optimizer']['candidates']),40)
                        exported = await client.get(f'/files/{job_id}/assembly.step', headers=headers)
                        self.assertEqual(exported.status_code,200)
        # Router holds the original DATA path; artifacts remain in ignored work/designs.
        asyncio.run(exercise())

if __name__ == '__main__':
    unittest.main()
