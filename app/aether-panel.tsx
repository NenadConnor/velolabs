"use client";
import {useState} from 'react';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';
import {engineRequest, type Result} from '@/lib/design';
import './aether.css';

type Spec = {
  geometry: Record<string,number>;
  thermal: Record<string,number>;
  fluid: {coolant:string;volumetric_flow_l_min:number|null;mass_flow_kg_s:number|null;density_kg_m3:number;viscosity_pa_s:number;conductivity_w_mk:number;specific_heat_j_kgk:number;property_temperature_c:number;property_source:string};
  material: {name:string;conductivity_w_mk:number;density_kg_m3:number};
  limits: {minimum_wall_mm:number;minimum_channel_mm:number;maximum_length_mm:number;maximum_width_mm:number;maximum_thickness_mm:number;maximum_channel_pressure_drop_pa:number;process:string};
  optimization:{bounds:Record<string,{minimum:number;maximum:number}>;maximum_evaluations:number};
  assumptions:string[];
};
type Constraint = {name:string;value:number|null;limit:number|null;unit:string;status:string;margin:number|null;explanation:string};
type Physics = {reynolds:number;regime:string;channel_pressure_drop_pa:number|null;coolant_outlet_c:number;heat_transfer_w_m2k:number|null;representative_temperature_c:number|null;thermal_resistance_k_w:number|null;warnings:string[];assumptions:string[];validity:string[];unsupported_physics:string[]};
type Candidate = {index:number;parameters:Record<string,number>;specification:Spec|null;evaluation:{model_feasible:boolean;physics:Physics}|null;rejection:string|null};
type Report = {input_requirements:Spec;physics:Physics;constraints:Constraint[];geometry_checked:boolean;model_feasible:boolean;optimization_job_id?:string;optimizer:{candidates:Candidate[];feasible_found:boolean;runtime_s:number;objective:string}|null};
const label = (key:string) => key.replaceAll('_',' ');
const number = (value:number|null) => value === null ? 'Not evaluated' : Number(value.toPrecision(5)).toLocaleString();

export default function AetherPanel({engine,token,model,onBuilt,disabled}:{engine:string;token:string;model:string;onBuilt:(cad:Result)=>void;disabled:boolean}) {
  const [open,setOpen]=useState(false), [spec,setSpec]=useState<Spec|null>(null);
  const [report,setReport]=useState<Report|null>(null), [error,setError]=useState(''), [busy,setBusy]=useState(false);
  const [progress,setProgress]=useState(''), [prompt,setPrompt]=useState(''), [advanced,setAdvanced]=useState('');
  async function show() {
    setOpen(true);
    if(spec)return;
    setBusy(true);setError('');
    try { const defaults=await engineRequest<Spec>(engine,'/aether/cold-plate/defaults',token);setSpec(defaults);setAdvanced(JSON.stringify(defaults,null,2)); }
    catch(e){setError((e as Error).message);} finally{setBusy(false);}
  }
  function edit(next:Spec){setSpec(next);setReport(null);setAdvanced(JSON.stringify(next,null,2));setError('');}
  async function request<T>(operation:string,body:unknown):Promise<T>{
    const job=await engineRequest(engine,'/aether/cold-plate/'+operation,token,body);
    for(let i=0;i<420;i++){
      const state=await engineRequest<{status:string;error?:string;message?:string;result:T}>(engine,'/jobs/'+job.id,token);
      setProgress(state.message??'Working…');
      if(state.status==='failed')throw new Error(state.error??'Aether job failed');
      if(state.status==='complete')return state.result;
      await new Promise(resolve=>setTimeout(resolve,1000));
    }
    throw new Error('Job polling timed out. Check the engine before trying again.');
  }
  async function run(operation:'plan'|'evaluate'|'optimize'|'build', selected=spec){
    if(!selected||busy)return;
    setBusy(true);setError('');setProgress(`Aether: ${operation}…`);
    try{
      if(operation==='plan'){
        const planned=await request<{specification:Spec}>('plan',{prompt,model,specification:selected});
        edit(planned.specification);setProgress('Review all planned requirements and assumptions before evaluating.');
      }else if(operation==='build'){
        const path='build'+(report?.optimization_job_id?'?optimization_job_id='+report.optimization_job_id:'');
        const built=await request<{cad:Result;report:Report}>(path,selected);
        setReport(built.report);onBuilt(built.cad);
        setProgress('Geometry checked. Close this panel to inspect the solid and export STEP from the workspace.');
      }else{
        const result=await request<Report>(operation,selected);
        if(operation==='evaluate' && report?.optimizer){result.optimizer=report.optimizer;result.optimization_job_id=report.optimization_job_id;}
        setReport(result);setSpec(result.input_requirements);setAdvanced(JSON.stringify(result.input_requirements,null,2));
        setProgress(operation==='optimize'?'Search complete. The selected candidate is shown below.':'Evaluation complete.');
      }
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  function download(){
    if(!report)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
    const anchor=document.createElement('a');anchor.href=url;anchor.download='aether-engineering-report.json';anchor.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function applyJson(){
    setBusy(true);setError('');setReport(null);
    try{const validated=await engineRequest<Spec>(engine,'/aether/cold-plate/validate',token,JSON.parse(advanced));edit(validated);}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  function fields(group:'geometry'|'thermal'|'fluid'|'material'|'limits'){
    if(!spec)return null;
    return Object.entries(spec[group]).map(([key,value])=> typeof value==='number' ?
      <label key={key}>{label(key)}<input type="number" step={key==='channel_count'?'1':'any'} value={value}
        onChange={e=>{if(e.target.value!==''&&Number.isFinite(e.target.valueAsNumber))edit({...spec,[group]:{...spec[group],[key]:e.target.valueAsNumber}});}}/></label>:
      typeof value==='string' ? <label key={key}>{label(key)}{key==='coolant'||key==='process'?<select value={value} onChange={e=>edit({...spec,[group]:{...spec[group],[key]:e.target.value}})}>
        {(key==='coolant'?['water','user_supplied']:['unspecified','machining_and_bonding','additive']).map(v=><option key={v}>{v}</option>)}
      </select>:<input value={value} maxLength={key==='property_source'?300:100} onChange={e=>edit({...spec,[group]:{...spec[group],[key]:e.target.value}})}/>}</label>:null);
  }
  return <><button className="quiet" disabled={disabled} onClick={()=>void show()}>Aether CEM</button>
    <Dialog open={open} onOpenChange={v=>{if(!busy)setOpen(v);}}><DialogContent className="aether-dialog">
      <DialogTitle>Aether · Cold Plate CEM</DialogTitle>
      <DialogDescription>Straight parallel channels. Reduced-order estimates for early design comparison. NOT PHYSICALLY VALIDATED.</DialogDescription>
      {error&&<p className="aether-error" role="alert">{error}</p>}
      {!spec&&!busy&&<button onClick={()=>void show()}>Retry engine connection</button>}
      <p role="status">{busy?'Working — ':''}{progress}</p>
      {spec&&<><fieldset disabled={busy} className="aether-inputs"><section>
        <h3>Requirements</h3><label>Describe a cold plate<textarea value={prompt} maxLength={12000} onChange={e=>setPrompt(e.target.value)} placeholder="Describe heat load, size, coolant and limits…"/></label>
        <button disabled={prompt.trim().length<3} onClick={()=>void run('plan')}>Plan requirements with {model}</button>
        <p>Review planned values before running analysis. Explicit numbers below are the engineering inputs.</p>
        {fields('thermal')}
      </section><section><h3>Geometry · mm</h3>{fields('geometry')}<p>Channels run along X and open at both ends. Actual cover = thickness − base − channel height. No headers or ports are modeled.</p></section>
      <section><h3>Coolant · SI properties</h3><label>Flow input<select value={spec.fluid.mass_flow_kg_s===null?'volume':'mass'} onChange={e=>edit({...spec,fluid:{...spec.fluid,volumetric_flow_l_min:e.target.value==='volume'?0.02:null,mass_flow_kg_s:e.target.value==='mass'?0.0003327333333333333:null}})}><option value="volume">Volume · L/min</option><option value="mass">Mass · kg/s</option></select></label>{fields('fluid')}<p>Properties are fixed user inputs. Selecting a coolant name does not recalculate them.</p><h3>Material</h3>{fields('material')}</section>
      <section><h3>Constraints</h3>{fields('limits')}<h3>Optimization</h3><label>Maximum evaluations<input type="number" min={1} max={256} value={spec.optimization.maximum_evaluations} onChange={e=>{if(Number.isInteger(e.target.valueAsNumber))edit({...spec,optimization:{...spec.optimization,maximum_evaluations:e.target.valueAsNumber}});}}/></label>
      <p>Deterministic search: feasible model constraints first, then temperature, channel pressure and mass. Edit bounds or disable variables in the structured input below.</p></section></fieldset>
      <details><summary>Structured input, optimization bounds and assumptions</summary><p>{spec.assumptions.join(' · ')||'Default example: 10 W, water properties at 20 C, idealized aluminum.'}</p><textarea className="aether-json" aria-label="Cold plate JSON" maxLength={64000} value={advanced} disabled={busy} onChange={e=>{setAdvanced(e.target.value);setReport(null);}}/><button disabled={busy} onClick={()=>void applyJson()}>Apply JSON draft</button><p>The server validates every field before analysis or CAD construction.</p></details>
      <fieldset disabled={busy||advanced!==JSON.stringify(spec,null,2)} className="aether-actions"><button onClick={()=>void run('evaluate')}>Evaluate</button><button onClick={()=>void run('optimize')}>Optimize</button><button disabled={!report} onClick={()=>void run('build')}>Build selected CAD</button><button disabled={!report} onClick={download}>Save JSON report</button></fieldset>
      {report&&<section className="aether-results"><h3>{report.geometry_checked?'GEOMETRY CHECKED':'CAD NOT BUILT'} · NOT PHYSICALLY VALIDATED</h3>
        <p>{report.model_feasible?'Supported model constraints pass.':'Supported model constraints do not all pass.'} System pressure, device maximum temperature and manufacturing remain unevaluated.</p>
        <div className="aether-metrics">
          <div>CALCULATED · Reynolds<strong>{number(report.physics.reynolds)} · {report.physics.regime}</strong></div>
          <div>ESTIMATED · Channel pressure<strong>{number(report.physics.channel_pressure_drop_pa)} Pa</strong></div>
          <div>ESTIMATED · Representative plate<strong>{number(report.physics.representative_temperature_c)} °C</strong></div>
          <div>CALCULATED · Coolant outlet<strong>{number(report.physics.coolant_outlet_c)} °C</strong></div>
          <div>ESTIMATED · Heat transfer coefficient<strong>{number(report.physics.heat_transfer_w_m2k)} W/m²K</strong></div>
          <div>ESTIMATED · Thermal resistance<strong>{number(report.physics.thermal_resistance_k_w)} K/W</strong></div>
        </div><h3>Warnings and assumptions</h3><ul>{[...report.physics.warnings,...report.physics.assumptions].map((warning,i)=><li key={i}>{warning}</li>)}</ul>
        <details><summary>Validity and unsupported effects</summary><ul>{[...report.physics.validity,...report.physics.unsupported_physics].map((text,i)=><li key={i}>{text}</li>)}</ul></details>
        <div className="aether-table"><table><thead><tr><th>Constraint</th><th>Status</th><th>Value / limit</th><th>Margin</th><th>Interpretation</th></tr></thead><tbody>{report.constraints.map(c=><tr key={c.name}><td>{c.name}</td><td>{c.status}</td><td>{number(c.value)} / {number(c.limit)} {c.unit}</td><td>{number(c.margin)}</td><td>{c.explanation}</td></tr>)}</tbody></table></div>
        {report.optimizer&&<><h3>Candidate history · {report.optimizer.candidates.length} attempts</h3><p>{report.optimizer.feasible_found?'A model-feasible candidate was found.':'No model-feasible candidate found; best available is diagnostic only.'} Runtime: {report.optimizer.runtime_s.toFixed(3)} s.</p><p>{report.optimizer.objective}</p><div className="aether-table"><table><thead><tr><th>Candidate</th><th>Parameters</th><th>Result</th><th>Select</th></tr></thead><tbody>{report.optimizer.candidates.map(candidate=><tr key={candidate.index}><td>{candidate.index}</td><td>{Object.entries(candidate.parameters).map(([k,v])=>`${label(k)}: ${v}`).join(' · ')}</td><td>{candidate.rejection??(candidate.evaluation?.model_feasible?'Model constraints pass':'Not model-feasible')}</td><td><button disabled={busy||!candidate.specification} onClick={()=>void run('evaluate',candidate.specification)}>Inspect</button></td></tr>)}</tbody></table></div></>}
      </section>}</>}
    </DialogContent></Dialog></>;
}
