# Security policy

## Supported version

This repository is pre-release alpha software. Only the latest commit on the default branch receives security fixes.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, or private design files. Use GitHub's private vulnerability reporting feature when enabled. If it is unavailable, contact the repository owner privately through the GitHub profile associated with this repository. Include the affected version, reproduction steps, impact, and a minimal test case without real secrets.

## Security model

- Model output is untrusted JSON. It passes a strict schema and is never executed as source code.
- The engine binds to `127.0.0.1` by default and uses an exact browser-origin allowlist.
- A non-loopback or shared deployment must use HTTPS and a non-empty `VELOLABS_TOKEN` behind an authenticated gateway.
- Ollama credentials remain in the engine environment. The browser never receives the Ollama API key.
- Engine access tokens entered in the UI remain in memory for the current page and are not written to project files or local storage.
- Download paths accept only server-generated hexadecimal job IDs and restricted STEP/JSON filenames.
- Request sizes, identifiers, numeric ranges, part/feature counts, job concurrency, mesh complexity, and FEA mesh size are bounded.

## Deployment risks

The personal engine has no user accounts, persistent authorization database, worker isolation, job cancellation, durable audit log, automated artifact retention policy, or per-user quota. Do not expose it directly to the public internet. CAD and meshing libraries process complex geometry; treat uploaded or externally sourced files as hostile and isolate them before adding import capabilities.

Generated CAD and simulation results may be wrong. Engineering misuse is a product-safety risk as well as a software risk; review [docs/ENGINEERING.md](docs/ENGINEERING.md).

## Secret handling

Never commit `.env` files, Ollama API keys, engine tokens, source-repository credentials, or generated user designs. The repository ignores `.env*`, `work/`, build outputs, and local runtime state. Rotate a credential immediately if it is ever committed, even if the commit is later removed.
