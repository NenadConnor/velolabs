"""Small-strain, isotropic, linear tetrahedral FEA for one solid in N / mm / MPa.
Fixed nodes on minimum coordinate plane; total force distributed over opposite-plane
surface triangles. No contacts, gravity, buckling, plasticity or thermal effects.
"""
import json, sys
from pathlib import Path
import gmsh
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from schema import SimulationRequest

def solve(step_path, request, output):
    req=SimulationRequest.model_validate_json(Path(request).read_text('utf-8'))
    gmsh.initialize(); gmsh.option.setNumber('General.Terminal',0)
    try:
        gmsh.model.occ.importShapes(str(step_path)); gmsh.model.occ.synchronize()
        bounds=gmsh.model.getBoundingBox(-1,-1)
        span=max(bounds[i+3]-bounds[i] for i in range(3))
        gmsh.option.setNumber('Mesh.MeshSizeMax',span/req.mesh_divisions)
        gmsh.option.setNumber('Mesh.MeshSizeMin',span/(req.mesh_divisions*2))
        gmsh.option.setNumber('Mesh.ElementOrder',1)
        gmsh.model.mesh.generate(3)
        tags,coords,_=gmsh.model.mesh.getNodes()
        nodes=np.asarray(coords).reshape(-1,3)
        lookup={int(tag):i for i,tag in enumerate(tags)}
        types,_,connectivity=gmsh.model.mesh.getElements(3)
        raw=next((c for t,c in zip(types,connectivity) if t==4),None)
        if raw is None: raise ValueError('No tetrahedral volume elements were generated')
        tets=np.array([lookup[int(t)] for t in raw]).reshape(-1,4)
        surface=[]
        stypes,_,sconnectivity=gmsh.model.mesh.getElements(2)
        for t,c in zip(stypes,sconnectivity):
            if t==2: surface.extend([lookup[int(tag)] for tag in c])
        surface=np.array(surface).reshape(-1,3)
    finally: gmsh.finalize()
    if len(nodes)>20000 or len(tets)>80000: raise ValueError('Mesh is too large; reduce mesh divisions.')
    axis='xyz'.index(req.axis)
    low,high=nodes[:,axis].min(),nodes[:,axis].max()
    tol=max((high-low)*1e-6,1e-6)
    fixed=np.where(nodes[:,axis]<=low+tol)[0]
    loaded=surface[np.all(nodes[surface,axis]>=high-tol,axis=1)]
    if len(fixed)<3 or len(loaded)<1:
        raise ValueError('This axis needs flat opposite end faces. Choose another axis or a part with planar ends.')
    E,nu=req.young_mpa,req.poisson
    lam=E*nu/((1+nu)*(1-2*nu)); mu=E/(2*(1+nu))
    D=np.zeros((6,6)); D[:3,:3]=lam; np.fill_diagonal(D[:3,:3],lam+2*mu); D[3:,3:]=np.eye(3)*mu
    pts=nodes[tets]
    matrices=np.concatenate([np.ones((len(tets),4,1)),pts],axis=2)
    volume=np.abs(np.linalg.det(matrices))/6
    if np.any(volume<1e-12): raise ValueError('Degenerate mesh element')
    gradients=np.linalg.inv(matrices)[:,1:,:]
    B=np.zeros((len(tets),6,12))
    for i in range(4):
        dx,dy,dz=gradients[:,:,i].T
        B[:,0,3*i]=dx; B[:,1,3*i+1]=dy; B[:,2,3*i+2]=dz
        B[:,3,3*i]=dy; B[:,3,3*i+1]=dx
        B[:,4,3*i+1]=dz; B[:,4,3*i+2]=dy
        B[:,5,3*i]=dz; B[:,5,3*i+2]=dx
    Klocal=np.einsum('eji,jk,ekl,e->eil',B,D,B,volume)
    dofs=(tets[:,:,None]*3+np.arange(3)).reshape(-1,12)
    rows=np.repeat(dofs,12,axis=1).ravel(); cols=np.tile(dofs,(1,12)).ravel()
    K=coo_matrix((Klocal.ravel(),(rows,cols)),shape=(len(nodes)*3,len(nodes)*3)).tocsr()
    force=np.zeros((len(nodes),3))
    facepts=nodes[loaded]
    areas=np.linalg.norm(np.cross(facepts[:,1]-facepts[:,0],facepts[:,2]-facepts[:,0]),axis=1)/2
    total_area=areas.sum()
    if total_area<=0: raise ValueError('Loaded face has no area')
    for i,face in enumerate(loaded):
        for n in face: force[n]+=np.array(req.force)*areas[i]/(3*total_area)
    fixed_dofs=(fixed[:,None]*3+np.arange(3)).ravel()
    free=np.setdiff1d(np.arange(len(nodes)*3),fixed_dofs)
    u=np.zeros(len(nodes)*3); u[free]=spsolve(K[free][:,free],force.ravel()[free])
    if not np.all(np.isfinite(u)): raise ValueError('Singular system; supports do not constrain this part')
    residual=K@u-force.ravel()
    relative_residual=float(np.linalg.norm(residual[free])/max(np.linalg.norm(force),1e-12))
    if relative_residual>1e-5: raise ValueError('Solver residual is too large')
    stress=np.einsum('ij,ejk,ek->ei',D,B,u[dofs])
    sx,sy,sz,txy,tyz,txz=stress.T
    vm=np.sqrt(.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)+3*(txy*txy+tyz*tyz+txz*txz))
    disp=np.linalg.norm(u.reshape(-1,3),axis=1)
    result={'type':'linear_static','part_id':req.part_id,'settings':req.model_dump(),'nodes':len(nodes),'elements':len(tets),
        'max_displacement_mm':float(disp.max()),'max_von_mises_mpa':float(vm.max()),
        'yield_ratio':float(req.yield_mpa/max(vm.max(),1e-12)), 'relative_residual':relative_residual,
        'reaction_n':residual.reshape(-1,3)[fixed].sum(axis=0).tolist(), 'loaded_area_mm2':float(total_area),
        'convergence_tested':False,'physical_validation':False,
        'assumptions':['One part only; its minimum '+req.axis.upper()+' end is fully fixed.',
        'Total force distributed over the opposite planar end face. Coordinates are part-local.',
        'Homogeneous isotropic material, small deformation, linear elastic response.',
        'No assembly contact, plasticity, fatigue, buckling, gravity or thermal loads.',
        'Peak stresses near fixed edges may be singular. No mesh convergence study has been run.']}
    if disp.max()>span*.01: result['assumptions'].append('Displacement exceeds 1% of part size; small-deformation assumptions may be invalid.')
    Path(output).write_text(json.dumps(result,allow_nan=False,indent=2),'utf-8')
    print('Solved linear static test')

if __name__=='__main__': solve(*sys.argv[1:4])
