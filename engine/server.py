"""Local CAD bridge. Only the configured browser origins may use it."""
import asyncio, json, os, secrets, subprocess, sys, time, uuid
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from schema import Design, GenerateRequest, SimulationRequest

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'work' / 'designs'
DATA.mkdir(parents=True, exist_ok=True)
OLLAMA = os.environ.get('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
ORIGINS = os.environ.get('VELOLABS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,https://velolabs.theviralclipai.chatgpt.site').split(',')
TOKEN = os.environ.get('VELOLABS_TOKEN','')
app = FastAPI(title='velolabs CAD engine')
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=['GET','POST','OPTIONS'], allow_headers=['Content-Type','X-Velolabs-Token'])
jobs = {}
tasks = set()
gate = asyncio.Semaphore(1)

@app.middleware('http')
async def guard(request: Request, call_next):
    origin = request.headers.get('origin')
    if origin and origin not in ORIGINS:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Browser origin is not authorized for this engine'},status_code=403)
    if TOKEN and request.method != 'OPTIONS' and not secrets.compare_digest(request.headers.get('X-Velolabs-Token',''), TOKEN):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Engine access token is required'},status_code=401)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    if origin in ORIGINS: response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

SYSTEM = '''You are the mechanical CAD design planner for velolabs.io. Return ONLY one JSON object matching the provided schema.
Generate real, dimensioned, separately manufacturable connected solids using a bounded CAD language.
All dimensions are millimeters. All rotations are degrees, intrinsic XYZ. Box size is [X,Y,Z], centered at origin.
Cylinders/cones are centered at origin along Z (height/2 on either side). Sphere centered at origin.
Extrusions use a closed polygon of XY points and extend from z=0 to height. No repeated closing point needed.
Features are applied in order: add=fuse, subtract=cut. The first feature MUST add.
Each part must be ONE connected solid. Use subtract cylinders for real through-holes; overshoot cutters by 1 mm.
Feature coordinates are part-local. Part position/rotation are parent-relative, world-relative when parent=null.
Joints rotate/translate the whole part and its descendants around joint.origin in PART-LOCAL coordinates.
Use parent IDs to build an acyclic mechanism hierarchy. Fixed bases have parent=null. Joint value must be within min/max.
Create editable parts for functional objects. Do not invent pre-existing engineering validation, simulations or passing tests.
Every unspecified dimension, material, manufacturing clearance, or simplification must be in assumptions.
If key functional requirements cannot be responsibly inferred, return parts=[] and ask questions. If a requirement cannot be
represented using available primitives, explain the limitation and ask a question instead of silently substituting a box.
Decorative approximation is not functional design: gear teeth must not be replaced with smooth cylinders without explicit disclosure.
Avoid fasteners unless relevant. For a first concept use 1-8 parts and few features. Preserve supplied exact dimensions.
When revising an existing design return the ENTIRE revised design with stable part IDs. Review support and mating placements.
Never claim the CAD model is ready for manufacturing or structurally verified. No markdown fences, no executable code.
Schema: ''' + json.dumps(Design.model_json_schema())

async def chat(messages, model):
    headers = {}
    if os.environ.get('OLLAMA_API_KEY'): headers['Authorization'] = 'Bearer '+os.environ['OLLAMA_API_KEY']
    async with httpx.AsyncClient(timeout=240) as client:
        response = await client.post(OLLAMA+'/api/chat',json={'model':model,'messages':messages,'stream':False,'options':{'temperature':0.15}},headers=headers)
        if response.status_code == 401: raise ValueError('Ollama needs sign-in before using this cloud model.')
        if response.status_code >= 400: raise ValueError('Ollama: '+response.text[:400])
        content = response.json().get('message',{}).get('content','').strip()
    if content.startswith('```'): content = content.split('\n',1)[1].rsplit('```',1)[0].strip()
    return Design.model_validate_json(content)

def build(design, directory):
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'spec.json').write_text(design.model_dump_json(indent=2),'utf-8')
    result = subprocess.run([sys.executable,str(ROOT/'kernel.py'),str(directory/'spec.json'),str(directory)],cwd=ROOT,capture_output=True,text=True,timeout=120)
    if result.returncode:
        raise ValueError((result.stderr or result.stdout).strip().splitlines()[-1][:600])
    return json.loads((directory/'result.json').read_text('utf-8'))

async def generate(job_id, req):
    job = jobs[job_id]
    try:
        async with gate:
            job.update(status='planning',message='Turning your requirements into a dimensioned design…')
            context = '\nEarlier requests:\n'+'\n'.join(req.history) if req.history else ''
            if req.design: context += '\nCurrent design:\n'+req.design.model_dump_json()
            messages=[{'role':'system','content':SYSTEM},{'role':'user','content':context+'\nRequest: '+req.prompt}]
            for attempt in range(2):
                try:
                    spec=await chat(messages,req.model)
                    if not spec.parts:
                        job.update(status='complete',result={'design':spec.model_dump(),'meshes':[],'checks':None})
                        return
                    job.update(status='building',message='Building and checking CAD solids…')
                    result=await asyncio.to_thread(build,spec,DATA/job_id)
                    result['id']=job_id
                    job.update(status='complete',result=result,message='CAD solids generated')
                    return
                except (ValueError, subprocess.TimeoutExpired) as error:
                    if attempt: raise
                    job.update(status='repairing',message='Correcting a geometry or format issue…')
                    messages.append({'role':'user','content':'The previous attempt failed validation. Correct it and return the complete JSON. Error: '+str(error)[-1800:]})
    except Exception as error:
        job.update(status='failed',error=str(error)[:2000] or 'The engine could not complete this job.')

def launch(coro):
    task=asyncio.create_task(coro); tasks.add(task); task.add_done_callback(tasks.discard)

def new_job():
    if sum(j['status'] not in ['complete','failed'] for j in jobs.values()) >= 4:
        raise HTTPException(429,'The engine already has four jobs queued. Wait for one to finish.')
    job_id=uuid.uuid4().hex
    jobs[job_id]={'id':job_id,'status':'queued','message':'Waiting for the CAD engine…'}
    if len(jobs)>100:
        for key in list(jobs):
            if jobs[key]['status'] in ['complete','failed']:
                del jobs[key]
                break
    return job_id

@app.get('/health')
async def health():
    models=[]; error=None
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r=await client.get(OLLAMA+'/api/tags'); r.raise_for_status()
            models=[m['name'] for m in r.json().get('models',[])]
    except Exception: error='Ollama is not reachable. Start Ollama, then reconnect.'
    return {'engine':'cadgen 0.5.1 / build123d','ready':error is None,'models':models,'error':error}

@app.post('/generate')
async def create(req: GenerateRequest):
    job_id=new_job(); launch(generate(job_id,req)); return {'id':job_id}

@app.get('/jobs/{job_id}')
async def job(job_id: str):
    if job_id not in jobs: raise HTTPException(404,'Job not found. The engine may have restarted.')
    return jobs[job_id]

@app.post('/rebuild')
async def rebuild(spec: Design):
    if not spec.parts: raise HTTPException(422,'No parts to rebuild')
    job_id=new_job()
    async def run():
        try:
            async with gate:
                jobs[job_id].update(status='building',message='Rebuilding the edited geometry…')
                result=await asyncio.to_thread(build,spec,DATA/job_id); result['id']=job_id
                jobs[job_id].update(status='complete',result=result)
        except Exception as error: jobs[job_id].update(status='failed',error=str(error)[:1600])
    launch(run()); return {'id':job_id}

@app.get('/files/{job_id}/{filename}')
async def file(job_id: str, filename: str):
    import re
    if not re.fullmatch(r'[a-f0-9]{32}',job_id) or not re.fullmatch(r'[a-z][a-z0-9_]*\.(step|json)',filename):
        raise HTTPException(400,'Invalid file name')
    target=DATA/job_id/filename
    if not target.is_file(): raise HTTPException(404,'File not found')
    return FileResponse(target,filename=filename)

@app.post('/simulate/{design_id}')
async def simulate(design_id: str, req: SimulationRequest):
    import re
    if not re.fullmatch(r'[a-f0-9]{32}',design_id): raise HTTPException(400,'Invalid design')
    source=DATA/design_id/f'{req.part_id}.step'
    if not source.is_file(): raise HTTPException(404,'Build this part before running a simulation')
    job_id=new_job()
    async def run():
        try:
            async with gate:
                jobs[job_id].update(status='simulating',message='Meshing the solid and solving linear elasticity…')
                directory=DATA/job_id; directory.mkdir(parents=True,exist_ok=True)
                (directory/'simulation.json').write_text(req.model_dump_json(),'utf-8')
                proc=await asyncio.to_thread(subprocess.run,[sys.executable,str(ROOT/'simulate.py'),str(source),str(directory/'simulation.json'),str(directory/'result.json')],cwd=ROOT,capture_output=True,text=True,timeout=150)
                if proc.returncode: raise ValueError((proc.stderr or proc.stdout).strip().splitlines()[-1][:600])
                jobs[job_id].update(status='complete',result=json.loads((directory/'result.json').read_text('utf-8')))
        except Exception as error: jobs[job_id].update(status='failed',error=str(error)[:1600])
    launch(run()); return {'id':job_id}

