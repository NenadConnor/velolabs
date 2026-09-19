"""SI reduced-order model. Shah–London fully developed laminar duct fits.

No developing-flow correction, turbulence model, or CFD. Unsupported correlation
domains return null estimates; entrance effects within the domain are flagged.
"""
import math
from aether.core.result import PhysicsResult
from aether.core.units import MM_TO_M, MM3_TO_M3, L_MIN_TO_M3_S
from .schema import ColdPlateSpecification

LAMINAR_RE_LIMIT = 2300
TURBULENT_RE_THRESHOLD = 4000
MINIMUM_PECLET = 100
ENTRANCE_LENGTH_FACTOR = 0.05
MAXIMUM_ENTRANCE_FRACTION = 0.1
PROPERTY_TEMPERATURE_TOLERANCE_K = 10
MAXIMUM_LIQUID_TEMPERATURE_C = 80

UNSUPPORTED = ['CFD and conjugate heat transfer', 'Manifolds, ports, bends, minor losses and flow maldistribution',
               'Boiling, freezing, temperature-dependent properties and buoyancy',
               'Spreading/contact resistance, fin efficiency and local device hot spots',
               'Roughness, fouling, turbulence, entrance-flow corrections',
               'Cover joints, leakage, fatigue, pressure-vessel or manufacturing certification']

class ReducedOrderEvaluator:
    def evaluate(self, specification: ColdPlateSpecification) -> PhysicsResult:
        s = specification
        g, fluid, t = s.geometry, s.fluid, s.thermal
        w, h, length = (v * MM_TO_M for v in (g.channel_width_mm, g.channel_height_mm, g.length_mm))
        flow = (fluid.volumetric_flow_l_min * L_MIN_TO_M3_S if fluid.volumetric_flow_l_min is not None
                else fluid.mass_flow_kg_s / fluid.density_kg_m3)
        mass_flow = flow * fluid.density_kg_m3
        velocity = flow / (g.channel_count * w * h)
        diameter = 2 * w * h / (w + h)
        re = fluid.density_kg_m3 * velocity * diameter / fluid.viscosity_pa_s
        pr = fluid.viscosity_pa_s * fluid.specific_heat_j_kgk / fluid.conductivity_w_mk
        rise = t.heat_w / (mass_flow * fluid.specific_heat_j_kgk)
        outlet = t.inlet_c + rise
        alpha = min(w, h) / max(w, h)
        regime = 'laminar' if re < LAMINAR_RE_LIMIT else 'transitional' if re < TURBULENT_RE_THRESHOLD else 'turbulent'
        warnings = ['Channel pressure drop excludes headers and fittings; total system pressure drop is not evaluated.',
                    'Representative plate temperature is an idealized isothermal-wall estimate, not a local device maximum.']
        valid = regime == 'laminar' and re * pr >= MINIMUM_PECLET
        if regime != 'laminar':
            warnings.append('No transitional or turbulent correlation is implemented. Thermal and pressure estimates withheld.')
        if re * pr < MINIMUM_PECLET:
            warnings.append('Peclet number below the conservative Pe >= 100 gate; axial conduction may matter. Estimates withheld.')
        # Fully developed formulas applied only if estimated entrance regions are <=10% of length.
        hydro_entry = ENTRANCE_LENGTH_FACTOR * re * diameter
        thermal_entry = hydro_entry * pr
        if max(hydro_entry, thermal_entry) > MAXIMUM_ENTRANCE_FRACTION * length:
            valid = False
            warnings.append('Estimated entrance length exceeds 10% of passage length. Fully developed estimates withheld.')
        if max(abs(t.inlet_c - fluid.property_temperature_c), abs(outlet - fluid.property_temperature_c)) > PROPERTY_TEMPERATURE_TOLERANCE_K:
            valid = False
            warnings.append('Coolant temperatures differ from supplied property temperature by more than 10 K. Estimates withheld.')
        if outlet > MAXIMUM_LIQUID_TEMPERATURE_C:
            valid = False
            warnings.append('Outlet exceeds the v0.1 liquid operating envelope of 5–80 C. Estimates withheld.')
        friction = pressure = nu = coefficient = resistance = temperature = None
        area = t.footprint_length_mm * t.footprint_width_mm * MM_TO_M**2
        conduction = g.base_mm * MM_TO_M / (s.material.conductivity_w_mk * area)
        if valid:
            friction = 96 * (1 - 1.3553*alpha + 1.9467*alpha**2 - 1.7012*alpha**3
                             + 0.9564*alpha**4 - 0.2537*alpha**5) / re
            pressure = friction * length / diameter * fluid.density_kg_m3 * velocity**2 / 2
            nu = 7.541 * (1 - 2.610*alpha + 4.970*alpha**2 - 5.119*alpha**3
                          + 2.702*alpha**4 - 0.548*alpha**5)
            coefficient = nu * fluid.conductivity_w_mk / diameter
            wetted_area = g.channel_count * 2 * (w + h) * length
            capacity = mass_flow * fluid.specific_heat_j_kgk
            # Isothermal-wall heat exchanger balance Q=C*(Tw-Tin)*(1-exp(-hA/C)).
            resistance = conduction + 1 / (capacity * -math.expm1(-coefficient*wetted_area/capacity))
            temperature = t.inlet_c + t.heat_w * resistance
            if temperature > MAXIMUM_LIQUID_TEMPERATURE_C:
                valid = False
                warnings.append('Diagnostic wall estimate exceeds 80 C; single-phase assumptions are not accepted. Thermal estimate withheld.')
                temperature = resistance = None
        if area < g.length_mm * g.width_mm * MM_TO_M**2:
            warnings.append('Partial footprint: spreading resistance is omitted; device hot spots cannot be assessed.')
        volume = g.length_mm * (g.width_mm*g.thickness_mm - g.channel_count*g.channel_width_mm*g.channel_height_mm)
        return PhysicsResult(velocity_m_s=velocity, hydraulic_diameter_m=diameter, mass_flow_kg_s=mass_flow,
            reynolds=re, prandtl=pr, regime=regime, darcy_friction_factor=friction,
            channel_pressure_drop_pa=pressure, coolant_rise_k=rise, coolant_outlet_c=outlet,
            nusselt=nu, heat_transfer_w_m2k=coefficient, conduction_resistance_k_w=conduction,
            thermal_resistance_k_w=resistance, representative_temperature_c=temperature,
            mass_kg=volume*MM3_TO_M3*s.material.density_kg_m3, correlation_valid=valid,
            equations={'flow':'v=Vdot/(N*w*h); Dh=2*w*h/(w+h); Re=rho*v*Dh/mu; Pr=mu*cp/k',
                'friction':'Darcy f=96/Re*(1-1.3553a+1.9467a²-1.7012a³+0.9564a⁴-0.2537a⁵)',
                'pressure':'dp=f*(L/Dh)*rho*v²/2; one parallel passage (not multiplied by N)',
                'thermal':'Nu=7.541*(1-2.610a+4.970a²-5.119a³+2.702a⁴-0.548a⁵); h=Nu*k/Dh',
                'energy':'dT=Q/(mdot*cp); Tout=Tin+dT',
                'resistance':'Rb=base/(km*footprint); C=mdot*cp; A=N*2*(w+h)*L; R=Rb+1/[C*(1-exp(-h*A/C))]; T=Tin+Q*R'},
            validity=['Shah–London smooth rectangular duct, 0<a<=1, Re<2300; constant wall temperature.',
                      'Application gates: Pe>=100; 0.05*Re*Dh*max(1,Pr)<=0.1*L; property mismatch<=10 K.',
                      'Liquid 5–80 C; Newtonian single phase; equal flow through identical channels.',
                      'Entrance length and temperature gates are conservative application policies, not correlation error bounds.'],
            warnings=warnings, assumptions=['All heat enters coolant; no environmental losses.',
                'All four channel walls share one temperature; ribs/cover perfectly redistribute heat.',
                'Base conduction is one dimensional over the centered footprint; no contact/spreading resistance.',
                'Constant user-confirmed material and fluid properties.'] + s.assumptions,
            unsupported_physics=UNSUPPORTED)
