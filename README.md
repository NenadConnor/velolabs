# velolabs.io

> Alpha software for prompt-driven, editable mechanical CAD and bounded engineering analysis.

![Status](https://img.shields.io/badge/status-alpha-b6ed7a) ![CAD](https://img.shields.io/badge/CAD-STEP-7eaac7) ![AI](https://img.shields.io/badge/AI-Ollama-232a34)

A local-first prompt-to-CAD application connected to Ollama Cloud through the user's local, signed-in Ollama service. It integrates the `cadgen` runtime published by [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad), including its build123d entry point, assembly helper, and color handling. It uses a custom Three.js workspace rather than embedding the upstream CAD Viewer.

## Run on this computer

Open `outputs/Start Velolabs.cmd`, keep Ollama running, and visit http://localhost:5173/. The launcher starts the browser interface and CAD bridge only if they are not already available. Logs are in `work/logs/`. Nothing is added to system startup.

The default model is `glm-5.3-flash:cloud`, already tested against this machine's Ollama connection. Change the model in **Engine settings**. No Ollama API key is exposed to the browser. The local engine listens only on 127.0.0.1:8765.

For a clean installation, follow [docs/SETUP.md](docs/SETUP.md). For the product's scope and intended workflow, read [docs/PRODUCT.md](docs/PRODUCT.md).

## What works

- **Aether Cold Plate CEM v0.1**: bounded straight-channel geometry, laminar reduced-order thermal/hydraulic estimates, explicit validity gates, deterministic optimization, STEP and JSON reports. Open **Aether CEM** in the workspace. This is not CFD or physical validation; see [Aether](docs/AETHER.md) and [cold-plate scope](docs/AETHER_COLD_PLATE.md).

- Real prompt generation and conversational revision through Ollama `/api/chat`.
- Schema-validated CAD plans: boxes, cylinders, spheres, cones, polygon extrusions, additions and cuts; up to 24 distinct parts and 160 features. Arbitrary AI-generated Python is never executed.
- Connected-solid checks, actual STEP export, nominal dimensions, part selection/hiding, parent-child transforms, revolute and slider joint previews.
- Editing feature sizes and centers, part positions/rotations, and joint limits/pivots. Rebuild before exporting or testing; edits invalidate previous results.
- Exact volumetric overlap checks at the built pose. They do not test swept collisions across motion.
- A real single-part linear static finite element solver using Gmsh first-order tetrahedra and SciPy sparse linear algebra. Supports are the minimum-coordinate face; force is distributed by triangle area on the opposite face. The UI uses a Z-directed force; the API accepts a vector. Units are N, mm, MPa.
- Explicit project JSON save/open and test-report export. Projects are saved by the user, not to an account or cloud database. Engine outputs remain under `work/designs/`.

## Engineering limits

This is a bounded CAD authoring and analysis application, not a general computational engineering model comparable in validation coverage to Noyron. AI can misunderstand requirements, and a valid solid does not prove a design functions. No manufacturing tolerances, threads, involute gearing, advanced surfaces, drawing generation, or CAM validation are promised by the first version. Unsupported geometry must be clarified instead of silently replaced.

Motion is prescribed kinematics, not rigid-body dynamics. FEA covers one homogeneous isotropic part, small deformation, linear elasticity, ideal fixed supports, and static loading. No assembly contact, buckling, fatigue, plasticity, thermal or fluid simulation is included. Material numbers must be supplied/confirmed by the user. Peak fixed-edge stresses can be singular. No automatic mesh convergence assessment or physical validation is performed. Yield/peak stress is a reported ratio, not a certified safety factor.

## Install elsewhere

Use Node.js 22.13+ and Python 3.12. Install web dependencies using `npm run install:ci`. Create `work/cad-runtime/venv` with Python, then install `engine/requirements.txt` into it. Start the API using `python -m uvicorn server:app --app-dir engine --host 127.0.0.1 --port 8765`; start the interface using `npm run dev`. In Ollama, sign in and pull `glm-5.3-flash:cloud` (or another supported cloud model).

Configuration is server-side: `OLLAMA_URL` defaults to http://127.0.0.1:11434. For direct cloud API access use https://ollama.com and set `OLLAMA_API_KEY` in the engine's environment. `VELOLABS_ORIGINS` is a comma-separated exact browser-origin allowlist. `VELOLABS_TOKEN` optionally requires an engine token. Keep the API on loopback for personal use. Before exposing it remotely, use TLS, a non-empty token, a narrow origin allowlist, resource limits, storage quotas and an operational hosting plan.

## Hosted interface

The Sites deployment hosts the web interface only. CAD generation and FEA still require the local engine or a separately provisioned HTTPS CAD server. This project has not registered or connected the custom domain velolabs.io. The interface's engine address is configurable; only that preference and model name are kept in browser local storage.

## Documentation

- [Product definition](docs/PRODUCT.md)
- [Architecture and data flow](docs/ARCHITECTURE.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Local installation and configuration](docs/SETUP.md)
- [HTTP API](docs/API.md)
- [CAD and simulation limitations](docs/ENGINEERING.md)
- [Security model](SECURITY.md)
- [Testing](docs/TESTING.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Third-party software](THIRD_PARTY.md)

## Validation

Run `python engine/test_engine.py` inside the installed environment, and `npm run test:types`. The engineering tests include analytic plate dimensions/volume, disjoint-solid rejection, parent/joint placement, and axial FEA against FL/EA with force equilibrium and solver residual checks. See [docs/TESTING.md](docs/TESTING.md) for the full test matrix.
