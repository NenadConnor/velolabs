# Contributing

velolabs is currently an early owner-led project. Small, focused issues and pull requests are welcome once the repository owner enables public contribution.

## Development workflow

1. Read [docs/PRODUCT.md](docs/PRODUCT.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/ENGINEERING.md](docs/ENGINEERING.md).
2. Create a branch from the current default branch.
3. Keep model output declarative. Do not add execution of model-generated code.
4. Add a meaningful test for geometry, transforms, solvers, validation boundaries, or security behavior when changing those areas.
5. Run the checks in [docs/TESTING.md](docs/TESTING.md).
6. Describe the user-visible behavior, engineering validity domain, tests, and remaining limitations in the pull request.

## Engineering contributions

A new primitive or solver capability needs explicit units, parameter bounds, invalid-input behavior, known singularities or unsupported cases, at least one analytical or trusted-reference benchmark, and UI copy that accurately describes what was tested. Do not label a result as validated solely because code completed without an exception.

## Style

Use plain names and small modules. Keep secrets server-side. Prefer strict schemas and deterministic geometry operations. Make failures visible and actionable. Preserve the distinction between nominal geometry, simulated behavior, and physical validation.

## Issues

Bug reports should include the request, intended dimensions/behavior, model name, user-visible error, and a minimal non-sensitive project file when possible. Remove proprietary geometry, credentials, and personal data before attaching anything.
