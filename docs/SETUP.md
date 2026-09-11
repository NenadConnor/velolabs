# Setup

## Requirements

- Windows 10 or 11 for the included launcher. The source itself is portable, but the launcher and `test:engine` package script use Windows paths.
- Node.js 22.13 or newer.
- Python 3.12, 64-bit.
- Ollama installed and signed in for cloud models.
- Sufficient disk space for the Open CASCADE, Gmsh, VTK, NumPy, and SciPy Python packages.

## First installation

```powershell
npm run install:ci
python -m venv work/cad-runtime/venv
work/cad-runtime/venv/Scripts/python.exe -m pip install -r engine/requirements.txt
ollama signin
ollama pull glm-5.3-flash:cloud
```

Start both application processes:

```powershell
work/cad-runtime/venv/Scripts/python.exe -m uvicorn server:app --app-dir engine --host 127.0.0.1 --port 8765
npm run dev
```

Open `http://localhost:5173/`. After the first installation, `outputs/Start Velolabs.cmd` starts missing processes and opens the app.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API base URL. Use `https://ollama.com` for direct cloud API access. |
| `OLLAMA_API_KEY` | unset | Server-side bearer token for direct Ollama Cloud access. Never put it in browser code. |
| `VELOLABS_ORIGINS` | local app and registered hosted UI origins | Exact, comma-separated browser origins allowed to call the engine. |
| `VELOLABS_TOKEN` | unset | Optional token required in `X-Velolabs-Token`. Set this for any non-loopback deployment. |

The Engine settings dialog stores the engine address and model name in local storage. Its optional access token stays only in the current browser memory.

## Troubleshooting

If the footer says the engine is disconnected, check that Ollama and the Python engine are running. Review `work/logs/engine.log` and `work/logs/web.log` when using the launcher.

If a cloud model fails, run it once from Ollama and confirm that the local Ollama account is signed in. The engine health endpoint lists the models visible to Ollama.

If a design fails twice, simplify the request or provide explicit dimensions. The first failure is automatically returned to the planner for one repair attempt. The second failure is shown to the user.

If simulation cannot find opposite planar end faces, choose another support axis or use a part whose minimum and maximum faces are planar along that axis.
