/* eslint-disable react-hooks/refs, react-hooks/set-state-in-effect */
"use client";
import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import type {Design,MeshData} from '@/lib/design';

export default function Viewer({design,meshes,selected,onSelect,hidden,explode,playing,view,reset}:{design:Design;meshes:MeshData[];selected:string|null;onSelect:(id:string)=>void;hidden:string[];explode:number;playing:boolean;view:string;reset:number}){
 const host=useRef<HTMLDivElement>(null), select=useRef(onSelect), live=useRef({selected,hidden,explode,playing});
 const [error,setError]=useState('');select.current=onSelect;live.current={selected,hidden,explode,playing};
 useEffect(()=>{
  const el=host.current;if(!el)return;
  let renderer:THREE.WebGLRenderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});}catch{setError('3D acceleration is unavailable in this browser. STEP export and dimension editing still work.');return}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));renderer.setClearColor(0x000000,0);renderer.outputColorSpace=THREE.SRGBColorSpace;el.appendChild(renderer.domElement);
  const scene=new THREE.Scene(), camera=new THREE.PerspectiveCamera(38,1,.1,100000);
  camera.up.set(0,0,1);
  scene.add(new THREE.HemisphereLight(0xd8eaff,0x383e30,2.3));
  const light=new THREE.DirectionalLight(0xffffff,3.5);light.position.set(200,-300,500);scene.add(light);
  const fill=new THREE.DirectionalLight(0xa7d0ff,1.7);fill.position.set(-300,100,80);scene.add(fill);
  const groups=new Map<string,THREE.Group>(), solids:THREE.Mesh[]=[], materials=new Map<string,THREE.MeshStandardMaterial>();
  const geometryResources:THREE.BufferGeometry[]=[], edgeMaterials:THREE.LineBasicMaterial[]=[];
  for(const part of design.parts){
   const data=meshes.find(m=>m.id===part.id);if(!data)continue;
   const group=new THREE.Group();group.name=part.id;groups.set(part.id,group);
   group.position.fromArray(part.position);group.rotation.set(...part.rotation.map(v=>THREE.MathUtils.degToRad(v)) as [number,number,number],'XYZ');
   const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.triangles.flat());g.computeVertexNormals();geometryResources.push(g);
   const material=new THREE.MeshStandardMaterial({color:part.color,metalness:.42,roughness:.4,flatShading:false});materials.set(part.id,material);
   const mesh=new THREE.Mesh(g,material);mesh.userData.id=part.id;group.add(mesh);solids.push(mesh);
   const eg=new THREE.EdgesGeometry(g,28);geometryResources.push(eg);const em=new THREE.LineBasicMaterial({color:0x19232e,transparent:true,opacity:.45});edgeMaterials.push(em);group.add(new THREE.LineSegments(eg,em));
  }
  for(const part of design.parts){const g=groups.get(part.id);if(g)(part.parent?groups.get(part.parent)??scene:scene).add(g)}
  scene.updateMatrixWorld(true);
  const box=new THREE.Box3();solids.forEach(m=>box.expandByObject(m));
  const center=box.getCenter(new THREE.Vector3()), span=Math.max(box.getSize(new THREE.Vector3()).length(),20);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(center);controls.enableDamping=true;controls.dampingFactor=.09;controls.minDistance=span*.1;controls.maxDistance=span*12;
  const offset=view==='top'?new THREE.Vector3(.001,0,2):view==='front'?new THREE.Vector3(0,-2,.001):new THREE.Vector3(1.3,-1.8,1.2);
  camera.position.copy(center).add(offset.multiplyScalar(span));camera.lookAt(center);camera.near=Math.max(span/10000,.01);camera.far=span*100;camera.updateProjectionMatrix();
  const grid=new THREE.GridHelper(span*3,30,0x586573,0x364351);grid.rotation.x=Math.PI/2;grid.position.z=box.min.z-1;scene.add(grid);
  const ray=new THREE.Raycaster(), pointer=new THREE.Vector2();let down=[0,0];
  const onDown=(e:PointerEvent)=>{down=[e.clientX,e.clientY]};
  const onUp=(e:PointerEvent)=>{if(Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;const r=el.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(solids.filter(s=>{let p:THREE.Object3D|null=s;while(p){if(!p.visible)return false;p=p.parent}return true}))[0];if(hit)select.current(hit.object.userData.id)};
  renderer.domElement.addEventListener('pointerdown',onDown);renderer.domElement.addEventListener('pointerup',onUp);
  const resize=()=>{const {width,height}=el.getBoundingClientRect();if(!width||!height)return;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix()};
  const observer=new ResizeObserver(resize);observer.observe(el);resize();
  let frame=0;const started=performance.now();
  const render=()=>{
   const state=live.current;
   design.parts.forEach((part,index)=>{const g=groups.get(part.id);if(!g)return;g.visible=!state.hidden.includes(part.id);const material=materials.get(part.id)!;material.emissive.set(state.selected===part.id?0x244515:0x000000);material.emissiveIntensity=.65;
    const j=part.joint;const value=state.playing&&j.type!=='fixed'?j.min+(j.max-j.min)*(.5+.5*Math.sin((performance.now()-started)/1800)):j.value;
    const pos=new THREE.Vector3(...part.position);if(state.explode)pos.add(new THREE.Vector3((index%3-1)*span*.35,0,index*span*.13).multiplyScalar(state.explode/100));
    const base=new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(...part.rotation.map(v=>v*Math.PI/180) as [number,number,number],'XYZ'));base.setPosition(pos);
    const pivot=new THREE.Matrix4().makeTranslation(...j.origin);const jp=new THREE.Matrix4();
    if(j.type==='revolute')jp.makeRotationAxis(new THREE.Vector3(j.axis==='x'?1:0,j.axis==='y'?1:0,j.axis==='z'?1:0),value*Math.PI/180);
    if(j.type==='slider')jp.makeTranslation(j.axis==='x'?value:0,j.axis==='y'?value:0,j.axis==='z'?value:0);
    const matrix=base.multiply(pivot).multiply(jp).multiply(new THREE.Matrix4().makeTranslation(...j.origin.map(v=>-v) as [number,number,number]));matrix.decompose(g.position,g.quaternion,g.scale);
   });controls.update();renderer.render(scene,camera);frame=requestAnimationFrame(render);
  };render();
  return()=>{cancelAnimationFrame(frame);observer.disconnect();controls.dispose();renderer.domElement.removeEventListener('pointerdown',onDown);renderer.domElement.removeEventListener('pointerup',onUp);geometryResources.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());edgeMaterials.forEach(m=>m.dispose());grid.geometry.dispose();(grid.material as THREE.Material).dispose();renderer.dispose();el.replaceChildren()};
 },[design,meshes,view,reset]);
 return <div className="viewer" ref={host} aria-label="Interactive 3D CAD assembly">{error&&<p className="viewer-error" role="alert">{error}</p>}</div>
}
