# Product definition

## Vision

velolabs.io turns a plain-language mechanical design request into editable solid parts, an assembly, motion constraints, downloadable STEP files, and clearly bounded engineering checks. The product should help a user move from intent to a reviewable engineering artifact while preserving dimensions and assumptions.

It is inspired by the workflow of computational engineering systems, where requirements, geometry, physics, and manufacturing knowledge form an iterative loop. It does not contain or reproduce LEAP 71's proprietary Noyron software or engineering knowledge.

## Primary workflow

1. The user describes what an object must do, including size, load, material, interfaces, and motion where known.
2. The design planner either asks for essential missing requirements or returns a schema-valid design containing parts, features, placement, joints, materials, and assumptions.
3. The CAD kernel builds one connected B-rep solid per part and rejects invalid or disconnected results.
4. The browser displays the assembly, allows part selection, dimension and placement edits, and previews prescribed joint motion.
5. Every edit invalidates the previous CAD and simulation results until the user rebuilds.
6. The user can export individual parts or the complete assembly as STEP.
7. A supported single part can be run through the bounded linear static solver. Results always include their model assumptions.

## Current users

The alpha is intended for technically curious makers, mechanical designers, and engineers who can review geometry, supply materials and loads, and understand that calculated output must be independently checked before physical use.

## Alpha acceptance criteria

- A precise plate prompt creates a valid STEP solid with the requested dimensions and holes.
- Multi-part prompts can create separate labeled solids with a parent-child hierarchy.
- Revolute and slider values can be previewed without changing the source geometry.
- Nominal dimensions and placements can be edited and rebuilt.
- Invalid or disconnected part geometry is rejected rather than exported.
- Previous exports and test results become unavailable after an edit.
- A basic axial member benchmark agrees with the analytical displacement `FL/EA` within 3% and balances the applied force.
- The interface distinguishes geometry checks, simulation assumptions, and physical validation.

## Explicit non-goals for this alpha

- General autonomous engineering or automatic certification.
- A complete Noyron-like computational engineering model.
- Production manufacturing drawings, GD&T, CAM, or tolerance stack analysis.
- Full rigid-body dynamics, swept collision detection, contact, CFD, thermal analysis, buckling, fatigue, or plasticity.
- Cloud accounts, project collaboration, or durable hosted CAD jobs.
