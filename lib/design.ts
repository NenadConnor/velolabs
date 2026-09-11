export type Vec3=[number,number,number];
export type Feature={name:string;operation:'add'|'subtract';shape:'box'|'cylinder'|'sphere'|'cone'|'extrusion';size:Vec3;radius:number;top_radius:number;height:number;points:[number,number][];position:Vec3;rotation:Vec3};
export type Joint={type:'fixed'|'revolute'|'slider';axis:'x'|'y'|'z';origin:Vec3;min:number;max:number;value:number};
export type Part={id:string;name:string;color:string;material:string;position:Vec3;rotation:Vec3;parent:string|null;joint:Joint;features:Feature[]};
export type Design={title:string;summary:string;units:'mm';assumptions:string[];questions:string[];parts:Part[]};
export type MeshData={id:string;vertices:Vec3[];triangles:Vec3[];volume_mm3:number;bounds:{min:Vec3;max:Vec3};valid:boolean};
export type Result={id:string;design:Design;meshes:MeshData[];checks:{valid_solids:number;overlaps:{a:string;b:string;volume_mm3:number}[];mesh_tolerance_mm:number;physical_validation:false}|null};
export type Simulation={type:string;part_id:string;nodes:number;elements:number;max_displacement_mm:number;max_von_mises_mpa:number;yield_ratio:number;relative_residual:number;reaction_n:Vec3;convergence_tested:boolean;assumptions:string[];settings:{axis:string;force:Vec3;young_mpa:number;poisson:number;yield_mpa:number;mesh_divisions:number}};
export const DEFAULT_ENGINE='http://127.0.0.1:8765';
export async function engineRequest<T = {id:string}>(base:string,path:string,token:string,body?:unknown){
 const url=new URL(base);if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw new Error('Use a valid HTTP or HTTPS engine address.');
 const response=await fetch(base.replace(/\/$/,'')+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(token?{'X-Velolabs-Token':token}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
 if(!response.ok){let msg=`Engine request failed (${response.status})`;try{const r=await response.json() as {detail?:unknown};msg=typeof r.detail==='string'?r.detail:JSON.stringify(r.detail)}catch{}throw new Error(msg)}return response.json() as Promise<T>;
}
export function validateModel(value:unknown):asserts value is Result{
 const v=value as Result;if(!v?.design?.parts||!Array.isArray(v.meshes)||v.design.units!=='mm')throw new Error('This is not a velolabs project.');
 if(v.design.parts.length>24||v.meshes.length>24)throw new Error('Project exceeds the part limit.');
}

