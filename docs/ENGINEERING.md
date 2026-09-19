# Engineering interpretation

## Aether cold-plate estimates

Aether adds a separate laminar rectangular-duct reduced-order model, not CFD or a general thermal solver. Its representative plate temperature is an idealized isothermal-wall network; local device hot spots and total system pressure are not evaluated. Correlation validity gates can withhold estimates. A model-feasible result does not imply manufacturing or physical validation. See [AETHER_COLD_PLATE.md](AETHER_COLD_PLATE.md) for equations, property assumptions, application gates and omitted effects. The single-part FEA scope below is unchanged.

## Geometry

The CAD kernel produces boundary-representation solids and STEP files. A geometry pass means each requested part became one connected, non-empty, kernel-valid solid. It does not establish dimensional tolerance, surface finish, material availability, fastener selection, assembly sequence, tool access, printability, machinability, or regulatory compliance.

Dimensions are nominal millimeters. The tessellated browser mesh uses a 0.1 mm linear tolerance for visualization; it is not the source of truth. STEP geometry is the export artifact.

The overlap check computes volume intersections between parts at the built pose. A zero overlap does not establish clearance and does not check swept motion, minimum distances, or collisions at another joint value.

## Motion

The viewer applies parent-relative fixed, revolute, or slider transforms. It is a prescribed kinematic preview. It does not solve inertia, acceleration, force, torque, friction, damping, contact, or control behavior. Joint frames and limits come from the generated or edited design and must be checked against the intended mechanism.

## Linear static solver

The finite-element solver imports one STEP part into Gmsh and creates first-order tetrahedra. It fixes every degree of freedom on the minimum-coordinate face along the selected axis. It distributes the total load over triangles on the opposite maximum-coordinate face in proportion to triangle area.

The constitutive model is homogeneous, isotropic, small-strain linear elasticity. Inputs use newtons, millimeters, and megapascals. The result reports nodal displacement and element von Mises stress.

The displayed yield-to-peak-stress ratio is not a certified factor of safety. It omits allowable-stress policies, statistical material variation, manufacturing effects, fatigue, stress concentrations below the mesh scale, and every load case not modeled.

## Known limitations

- Fixed-edge stress can be mathematically singular and mesh-dependent.
- The interface does not run an automatic mesh-convergence study.
- Linear geometry can become invalid when displacement is large relative to part size.
- The solver has no contact, bolt preload, bearing loads, gravity, pressure surfaces, plasticity, thermal strain, buckling, vibration, fatigue, composite, anisotropic, or fluid physics.
- A single material is assigned to the whole part.
- The support and load surfaces must be planar extrema along the chosen axis.

Use results for early comparison and debugging. Before manufacturing or operating a consequential design, have the complete requirements, load cases, material data, tolerances, analysis setup, convergence, and physical tests reviewed by qualified engineers.
