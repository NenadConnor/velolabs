import {spawn} from 'node:child_process';
import {mkdirSync,openSync,existsSync,readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
mkdirSync(path.join(root,'work','logs'),{recursive:true});
async function alive(url){try{return (await fetch(url,{signal:AbortSignal.timeout(3000)})).ok}catch{return false}}
function launch(name,executable,args){const log=openSync(path.join(root,'work','logs',name+'.log'),'a');const child=spawn(executable,args,{cwd:root,detached:true,windowsHide:true,stdio:['ignore',log,log]});child.unref()}
const py=path.join(root,'work','cad-runtime','venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
if(!existsSync(py))throw new Error('CAD engine environment is missing. Follow README.md installation instructions.');
if(!await alive('http://127.0.0.1:8765/health'))launch('engine',py,['-m','uvicorn','server:app','--app-dir','engine','--host','127.0.0.1','--port','8765']);
if(!await alive('http://localhost:5173/')){const pkg=JSON.parse(readFileSync(path.join(root,'node_modules','vinext','package.json'),'utf8'));const bin=typeof pkg.bin==='string'?pkg.bin:pkg.bin.vinext;launch('web',process.execPath,[path.join(root,'node_modules','vinext',bin),'dev','--port','5173']);}
console.log('velolabs is starting at http://localhost:5173/ — keep Ollama running.');
