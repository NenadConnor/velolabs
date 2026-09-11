# Testing

## Automated checks

Install the project and run:

```powershell
npm run test:types
npm run lint
npm run build
python engine/test_engine.py
```

`engine/test_engine.py` covers:

- exact plate bounding dimensions and analytical volume after four through-holes;
- rejection of a part containing disconnected solids;
- rejection of cyclic assembly parents;
- parent-relative placement combined with a revolute joint transform;
- a 100 × 10 × 10 mm axial bar under 1,000 N compared with `FL/EA`, requiring less than 3% displacement error;
- reaction-force balance and finite-element residual.

## Manual acceptance test

1. Start Ollama, the engine, and the browser app.
2. Generate a 100 × 60 × 8 mm plate with four 6 mm holes centered at `(±40, ±20)`.
3. Confirm the assembly contains one part, Properties show the requested dimensions, the holes are visible, and Engineering status reports one valid solid.
4. Change the thickness to 10 mm. Confirm STEP export and Test are disabled until **Apply changes** completes, then confirm the displayed volume changes.
5. Save and reopen the project. Confirm the design is rebuilt rather than trusting saved mesh data.
6. Generate or open a two-part parent/child assembly with a revolute joint. In Motion, adjust the joint value and run Preview joints. Confirm the child moves around its stated pivot.
7. Run the plate structural test with stated material properties and load. Confirm all model assumptions appear and a JSON report can be saved.
8. Export a part and assembly STEP and validate them in an independent CAD viewer.

## Current verified baseline

During alpha construction, GLM-5.3-Flash generated the requested four-hole plate and the cadgen/build123d kernel returned one valid solid. A browser test changed thickness from 8 to 10 mm and rebuilt the part. The single-part static solver completed with a balanced reaction and low free-degree residual. Treat this as a development baseline, not a product guarantee.

## Future tests

- Property-based schema and geometry fuzzing.
- Cancellation, timeouts, disk quotas, and concurrency tests.
- Browser automation in Chromium, Firefox, and WebKit.
- Golden STEP topology and rendering comparisons.
- Joint hierarchy tests with multiple nested moving parts.
- Mesh-convergence tests and additional analytical FEA benchmarks.
- Security tests for origin checks, token handling, job isolation, and path traversal.
