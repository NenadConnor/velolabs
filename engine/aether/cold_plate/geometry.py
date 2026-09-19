"""Map bounded domain parameters to the existing trusted CAD language."""
from schema import Design, Feature, Part
from .schema import ColdPlateSpecification

def channel_centers(spec: ColdPlateSpecification) -> list[tuple[float, float, float]]:
    g = spec.geometry
    pitch = g.channel_width_mm + g.rib_mm
    z = -g.thickness_mm / 2 + g.base_mm + g.channel_height_mm / 2
    return [(0, (i - (g.channel_count - 1) / 2) * pitch, z) for i in range(g.channel_count)]

def design(spec: ColdPlateSpecification) -> Design:
    # Revalidate at the adapter boundary; model_copy must not bypass constraints.
    spec = ColdPlateSpecification.model_validate(spec.model_dump())
    g = spec.geometry
    features = [Feature(name='Plate envelope', shape='box', size=(g.length_mm, g.width_mm, g.thickness_mm))]
    features += [Feature(name=f'Open channel {i + 1}', operation='subtract', shape='box',
                         size=(g.length_mm + 2, g.channel_width_mm, g.channel_height_mm), position=center)
                 for i, center in enumerate(channel_centers(spec))]
    return Design(title='Aether parallel-channel cold plate',
                  summary='Rectangular plate with straight passages open at both X ends. External headers are required.',
                  assumptions=['One connected idealized solid; bonded cover/process not modeled.',
                               'No inlet/outlet manifolds, ports, seals or fittings.',
                               'CAD validity is not manufacturing or physical validation.'],
                  parts=[Part(id='cold_plate', name='Cold plate', material=spec.material.name, features=features)])
