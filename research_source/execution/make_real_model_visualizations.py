"""Compute descriptors and visual-branch Grad-CAM from completed frozen models.

The plan can be written before completion. No model image is produced unless
all 42 training and official-evaluation records pass the original validators.
"""
from pathlib import Path
import argparse, csv, datetime, hashlib, importlib.metadata, importlib.util, json, os, platform, sys

HERE=Path(__file__).resolve().parent
ROOT=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
U=Path(r'C:\项目\IMTMN\datasets\University-1652')
S=Path(r'C:\项目\IMTMN\datasets\SUES-200')
OUT=HERE.parent/'real_model_visualizations'
VARIANTS=['visual','visual_content','visual_style','full']
PLAN={'schema':'lgm-real-visualizations.v1','registered_date':'2026-09-14',
      'dataset':'University-1652 official test','seed':1,'variants':VARIANTS,
      'selection':'First three lexicographically sorted query identities; first 50 UAV paths and first satellite path per identity. No metric-based selection.',
      'embedding':'FP32 L2-normalized model descriptor; separate 3D t-SNE fit for each model, cosine distance, random initialization, perplexity 20, max_iter 1500, random_state 20260914. Coordinates are qualitative, unitless, and not comparable between fitted panels.',
      'heatmap':'Grad-CAM of layer4 for cosine similarity to the fixed same-identity other-view image. CLIP content/style evidence held fixed; the map describes the visual path only. Average spatial gradients weight channels; ReLU; one common maximum over the complete panel set. Bilinear enlargement for display only.',
      'export':['raw descriptors NPZ','raw 7x7 Grad-CAM NPZ','selected path CSV and image hashes','t-SNE coordinates CSV','PDF/SVG with editable text','PNG preview'],
      'gate':'All 42 frozen fits and official evaluations pass original completion validators, with current source and checkpoint fingerprints.'}
PLAN['review_revision']='2026-09-14: content fingerprints, exact image crop, numeric checks and auditable Grad-CAM scores'
PLAN['heatmap'] += ' Input column shows the actual Resize(256)/CenterCrop(224) visual-encoder crop. The CLIP evidence remains the original cached per-image evidence. These are target-conditioned local sensitivities, not calibrated attention probabilities.'
PLAN['embedding'] += ' Labels select points for display only, never enter t-SNE fitting. Legend identifies each selected identity and view.'

def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    temporary=p.with_suffix(p.suffix+'.tmp')
    temporary.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temporary,p)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def module(name,path):
    sys.dont_write_bytecode=True  # Loading the frozen source must not write into it.
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);sys.modules[name]=obj;spec.loader.exec_module(obj);return obj

def gate():
    runner=module('visualization_frozen_runner',ROOT/'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py')
    ledger=json.loads((ROOT/'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json').read_text(encoding='utf-8'))
    corefile=ROOT/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'
    if sha(corefile)!=ledger['formal_script_sha256']:raise RuntimeError('Frozen model code changed')
    if sha(Path(runner.__file__))!=ledger['runner_sha256']:raise RuntimeError('Frozen runner changed')
    if sha(ROOT/'FORMAL_EXPERIMENT_PROTOCOL.md')!=ledger['protocol_sha256']:raise RuntimeError('Frozen protocol changed')
    datasets=runner.dataset_specs(ROOT,U,S)
    for name,ds in datasets.items():
        frozen=ledger['frozen_inputs'][name]
        if ds.evidence_sha256!=frozen['evidence_sha256']:
            raise RuntimeError(f'Frozen evidence changed: {name}')
        if ds.data_root!=Path(frozen['data_root']).resolve():
            raise RuntimeError(f'Frozen dataset root changed: {name}')
    main_specs=runner.main_run_specs(ROOT,runner.DATASETS,runner.MAIN_VARIANTS,runner.MAIN_SEEDS)
    sensitivity_specs=runner.sensitivity_run_specs(ROOT,runner.DATASETS)
    runner.validate_registry(main_specs,sensitivity_specs)
    specs=main_specs+sensitivity_specs
    if runner.registry_sha256(specs)!=ledger['registered_registry_sha256']:raise RuntimeError('Frozen registry changed')
    failures={}
    for spec in specs:
        issues=runner.training_completion_issues(spec,datasets[spec.dataset],sha(corefile))
        issues+=runner.evaluation_completion_issues(spec,datasets[spec.dataset])
        # Incomplete runs need no expensive checkpoint deserialization or hashing.
        if not issues:issues+=runner.checkpoint_artifact_hash_issues(spec)
        if not issues:
            manifest=json.loads((spec.evaluation_dir/'evaluation_manifest.json').read_text(encoding='utf-8'))
            arrays=[(name,rec) for name,rec in manifest['artifacts'].items() if name.startswith('per_query_arrays/') and name.endswith('.npz')]
            expected=3 if spec.dataset=='university1652' else 8
            if len(arrays)!=expected:issues.append('Official per-query NPZ artifact count differs')
            for name,rec in arrays:
                path=(spec.evaluation_dir/name).resolve()
                if not path.is_relative_to(spec.evaluation_dir.resolve()):
                    issues.append('Evaluation artifact escapes run directory');continue
                if not path.is_file() or path.stat().st_size!=rec['bytes'] or sha(path)!=rec['sha256']:
                    issues.append('Official per-query artifact changed: '+name)
        if issues:failures[spec.identifier]=issues
    if failures:raise RuntimeError('Formal visualization gate pending: '+json.dumps(failures,ensure_ascii=False))
    proof={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fit_count':len(specs),
           'ledger_sha256':sha(ROOT/'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'),
           'formal_script_sha256':sha(corefile),'runner_sha256':sha(Path(runner.__file__)),
           'registry_sha256':runner.registry_sha256(specs),'script_sha256':sha(Path(__file__)),
           'frozen_inputs':ledger['frozen_inputs']}
    return corefile,{s.variant:s for s in specs if s.dataset=='university1652' and s.family=='formal_main' and s.seed==1},proof


def verify_checkpoint(cp,spec,core,store):
    if cp.get('schema_version')!=core.SCHEMA_VERSION or cp.get('epoch')!=79:
        raise RuntimeError('Checkpoint schema or final-epoch selection differs')
    config=json.loads((spec.run_dir/'run_config.json').read_text(encoding='utf-8'))
    if cp.get('immutable_config')!=config['immutable_config'] or cp.get('run_config_sha256')!=config['run_config_sha256']:
        raise RuntimeError('Checkpoint and verified run configuration disagree')
    cfg=cp['model_config']
    for key,value in {'variant':spec.variant,'backbone':spec.backbone,'embed_dim':spec.embed_dim,'dropout':.2,'image_size':224,'resize_size':256}.items():
        if cfg.get(key)!=value:raise RuntimeError(f'Unexpected checkpoint model_config.{key}')
    core.validate_checkpoint_evidence_schema(cp,store)
    return cfg


def check_descriptors(arr,expected_rows,expected_width):
    import numpy as np
    if arr.shape!=(expected_rows,expected_width) or arr.dtype!=np.float32:
        raise RuntimeError('Descriptor shape or FP32 dtype differs')
    if not np.isfinite(arr).all() or not np.allclose(np.linalg.norm(arr,axis=1),1,atol=1e-4):
        raise RuntimeError('Descriptors are nonfinite or not L2 normalized')


def compute_gradcam(model,image_tensors,target_tensors):
    """Return a raw CAM and its scalar cosine target; no normalization is applied."""
    import torch
    import torch.nn.functional as F
    with torch.no_grad():target=model.encode_image(*target_tensors).detach()
    activation=[]
    hook=model.visual_backbone.layer4.register_forward_hook(lambda m,i,o:activation.append(o))
    try:
        with torch.enable_grad():
            model.zero_grad(set_to_none=True)
            output=model.encode_image(*image_tensors)
            score=(output*target).sum()
            if len(activation)!=1 or activation[0].ndim!=4 or activation[0].shape[0]!=1:
                raise RuntimeError('Grad-CAM requires one image and one layer4 activation')
            grad=torch.autograd.grad(score,activation[0])[0]
            cam=F.relu((grad.mean(dim=(2,3),keepdim=True)*activation[0]).sum(dim=1))[0]
            if not torch.isfinite(cam).all() or not torch.isfinite(score) or abs(float(score.detach()))>1.0001:
                raise RuntimeError('Nonfinite Grad-CAM or invalid cosine target')
            return cam.detach().cpu().numpy(),float(score.detach().cpu())
    finally:
        hook.remove()
        model.zero_grad(set_to_none=True)


def normalized_maps(maps):
    import numpy as np
    if not maps or any(not np.isfinite(x).all() or np.any(x<0) for x in maps.values()):
        raise RuntimeError('Grad-CAM arrays must be finite and nonnegative')
    maximum=max(float(x.max()) for x in maps.values())
    # A zero map remains zero; it is never replaced by noise or a synthetic hotspot.
    return maximum, maximum if maximum>0 else 1.0

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write-plan',action='store_true');parser.add_argument('--device',default='cuda')
    parser.add_argument('--check-gate',action='store_true',help='Validate inputs without importing the model or using GPU')
    parser.add_argument('--batch-size',type=int,default=16,help='FP32 descriptor inference batch size; never changes training')
    args=parser.parse_args()
    if args.write_plan:
        dump(HERE/'real_visualization_plan.json',PLAN);print('Plan written; no model images or scores generated');return
    corefile,specs,proof=gate()
    if args.check_gate:
        dump(HERE/'real_visualization_gate.json',proof);print('All 42 fits/evaluations passed; no model loaded');return
    if args.batch_size<1:raise ValueError('--batch-size must be positive')
    core=module('visualization_formal_core',corefile)
    import numpy as np
    import torch
    import torch.nn.functional as F
    import matplotlib as mpl
    mpl.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE
    if OUT.exists() and (OUT/'completion.json').exists():raise RuntimeError('Completed visualization exists; inspect before replacing')
    OUT.mkdir(exist_ok=True)
    dump(OUT/'plan.json',PLAN)
    dump(OUT/'gate.json',proof)
    device=torch.device(args.device);core.seed_everything(20260914)
    cache=ROOT/'lgm_game_pytorch/evidence_cache/university1652_clip_image_evidence.npz'
    store=core.EvidenceStore.load([cache]);records=core.derive_all_records(store,U,'university1652')
    tasks=core.build_official_evaluation_tasks(records,'university1652',[])
    # The original completion validator audits metric files, not current test image bytes.
    # Compare the full test inventory once before attributing new maps to those evaluations.
    inventory=core.inventory_hash([r for t in tasks for r in (*t.query,*t.gallery)],'content')
    membership=core.protocol_membership_hash(tasks)
    for variant in VARIANTS:
        evaluation=json.loads((specs[variant].evaluation_dir/'evaluation_manifest.json').read_text(encoding='utf-8'))
        if evaluation.get('image_inventory')!=inventory or evaluation.get('protocol_membership_sha256')!=membership:
            raise RuntimeError('Current official test images differ from completed evaluation: '+variant)
    dump(OUT/'test_inventory.json',{'image_inventory':inventory,'protocol_membership_sha256':membership})
    task=next(x for x in tasks if x.name=='university1652_drone_to_satellite')
    identities=sorted({x.label for x in task.query})[:3]
    selected=[];pairs=[]
    for identity in identities:
        queries=sorted([x for x in task.query if x.label==identity],key=lambda x:x.relative_path)[:50]
        satellites=sorted([x for x in task.gallery if x.label==identity],key=lambda x:x.relative_path)
        if not queries or not satellites:raise RuntimeError('Predeclared identity has no positive cross-view pair')
        satellite=satellites[0]
        selected+=queries+[satellite];pairs += [(queries[0],satellite),(satellite,queries[0])]
    if len(identities)!=3 or len(selected)<=20 or len({x.relative_path for x in selected})!=len(selected):
        raise RuntimeError('Predeclared selection has insufficient or duplicate samples')
    provenance=[{'path':r.relative_path,'label':r.label,'view':r.view,'sha256':sha(r.absolute_path)} for r in selected]
    with (OUT/'selected_images.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(provenance[0]));w.writeheader();w.writerows(provenance)
    descriptors={};maps={};checkpoints={};coords=[];scores=[];tsne_runs=[];display_inputs=[]
    for variant in VARIANTS:
        checkpoint_path=specs[variant].run_dir/'best.pt'
        checkpoint_sha=sha(checkpoint_path)
        cp=core.load_torch_checkpoint(checkpoint_path,'cpu');cfg=verify_checkpoint(cp,specs[variant],core,store)
        model=core.FormalRetrievalModel(variant,cfg['backbone'],int(cfg['embed_dim']),float(cfg['dropout']),False)
        model.load_state_dict(cp['model_state'],strict=True);model.to(device).eval()
        _,transform=core.build_transforms(int(cfg['resize_size']),int(cfg['image_size']))
        encoded=core.encode_records(model,selected,store,transform,device,args.batch_size,0,False,20260914)
        arr=np.stack([encoded[x.relative_path.casefold()] for x in selected]);descriptors[variant]=arr
        check_descriptors(arr,len(selected),specs[variant].embed_dim)
        estimator=TSNE(n_components=3,perplexity=min(20,(len(selected)-1)/3),metric='cosine',init='random',learning_rate='auto',max_iter=1500,random_state=20260914,n_jobs=1)
        xyz=estimator.fit_transform(arr)
        if xyz.shape!=(len(selected),3) or not np.isfinite(xyz).all() or not np.isfinite(estimator.kl_divergence_):
            raise RuntimeError('t-SNE produced nonfinite coordinates or divergence')
        tsne_runs.append({'variant':variant,'parameters':estimator.get_params(),'kl_divergence':float(estimator.kl_divergence_),'iterations':int(estimator.n_iter_)})
        for record,coord in zip(selected,xyz):coords.append({'variant':variant,'path':record.relative_path,'identity':record.label,'view':record.view,'x':float(coord[0]),'y':float(coord[1]),'z':float(coord[2])})
        def tensor(record):
            ds=core.RecordDataset([record],store,transform,variant)[0]
            return tuple(ds[k].unsqueeze(0).to(device) for k in ['image','content','style'])
        batchmaps=[]
        for image,reference in pairs:
            cam,score=compute_gradcam(model,tensor(image),tensor(reference))
            if cam.shape!=(7,7):raise RuntimeError('Expected the frozen ResNet18 224px layer4 to produce a 7x7 map')
            batchmaps.append(cam)
            scores.append({'variant':variant,'path':image.relative_path,'reference_path':reference.relative_path,'cosine_similarity':score,'raw_min':float(cam.min()),'raw_max':float(cam.max()),'zero_map':bool(np.all(cam==0))})
            if variant==VARIANTS[0]:
                # Exact deterministic crop used by the visual encoder, before ToTensor/Normalize.
                crop=core.load_rgb(image.absolute_path)
                for operation in transform.transforms[:2]:crop=operation(crop)
                display_inputs.append(np.asarray(crop))
        maps[variant]=np.stack(batchmaps)
        if sha(checkpoint_path)!=checkpoint_sha:raise RuntimeError('Checkpoint changed while reading')
        checkpoints[variant]={'path':str(checkpoint_path),'sha256':checkpoint_sha,'run_manifest_sha256':sha(specs[variant].run_dir/'run_manifest.json'),'evaluation_manifest_sha256':sha(specs[variant].evaluation_dir/'evaluation_manifest.json')}
        del model,cp,encoded
        if device.type=='cuda':torch.cuda.empty_cache()
    np.savez_compressed(OUT/'descriptors.npz',**descriptors,paths=np.array([x.relative_path for x in selected]))
    np.savez_compressed(OUT/'gradcam_raw.npz',**maps,paths=np.array([x.relative_path for x,y in pairs]),targets=np.array([y.relative_path for x,y in pairs]))
    np.savez_compressed(OUT/'visual_input_crops.npz',rgb=np.stack(display_inputs),paths=np.array([x.relative_path for x,y in pairs]))
    dump(OUT/'gradcam_targets.json',scores);dump(OUT/'tsne_runs.json',tsne_runs)
    with (OUT/'tsne_coordinates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(coords[0]));w.writeheader();w.writerows(coords)
    mpl.rcParams.update({'font.family':'Arial','font.size':9,'axes.labelsize':9,'axes.titlesize':10,'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9,'pdf.fonttype':42,'svg.fonttype':'none'})
    names=['V','V+C','V+S','V+C+S'];colors=['#282828','#A6A700','#D8525A']
    fig=plt.figure(figsize=(180/25.4,150/25.4))
    for i,(variant,name) in enumerate(zip(VARIANTS,names)):
        ax=fig.add_subplot(2,2,i+1,projection='3d')
        for k,label in enumerate(identities):
            for view,marker in [('drone','o'),('satellite','^')]:
                pts=np.array([[r['x'],r['y'],r['z']] for r in coords if r['variant']==variant and r['identity']==label and r['view']==view])
                if len(pts):ax.scatter(*pts.T,c=colors[k],marker=marker,s=11 if view=='drone' else 40,alpha=.8)
        ax.set_title(f'({chr(97+i)}) {name}',loc='left',fontweight='bold');ax.set_xlabel('t-SNE 1');ax.set_ylabel('t-SNE 2');ax.set_zlabel('t-SNE 3')
        ax.tick_params(pad=0);ax.view_init(elev=22,azim=-65)
    from matplotlib.lines import Line2D
    legend=[Line2D([],[],linestyle='none',marker='o',color=color,label='ID '+label) for label,color in zip(identities,colors)]
    legend += [Line2D([],[],linestyle='none',marker=marker,color='#666666',label=name) for marker,name in [('o','UAV'),('^','Satellite')]]
    fig.legend(handles=legend,loc='upper center',bbox_to_anchor=(.5,1),ncol=5,frameon=False,handletextpad=.3,columnspacing=.9)
    fig.subplots_adjust(left=.04,right=.94,bottom=.07,top=.89,hspace=.25,wspace=.19)
    for ext in ['pdf','svg','png']:fig.savefig(OUT/('feature_distribution.'+ext),dpi=600)
    plt.close(fig)
    maximum,denom=normalized_maps(maps)
    fig,axes=plt.subplots(len(pairs),5,figsize=(180/25.4,175/25.4))
    for row,(record,reference) in enumerate(pairs):
        axes[row,0].imshow(display_inputs[row],interpolation='none')
        for col,variant in enumerate(VARIANTS,1):
            display=F.interpolate(torch.from_numpy(maps[variant][row])[None,None],size=(224,224),mode='bilinear',align_corners=False)[0,0].numpy()/denom
            im=axes[row,col].imshow(display,vmin=0,vmax=1,cmap='viridis',interpolation='none')
        axes[row,0].set_ylabel(f'{record.label}\n'+('UAV' if record.view=='drone' else 'Satellite'),fontsize=9)
        for ax in axes[row]:ax.set_xticks([]);ax.set_yticks([])
    for ax,label in zip(axes[0],['Input crop']+names):ax.set_title(label,fontweight='bold')
    fig.subplots_adjust(left=.10,right=.98,top=.94,bottom=.08,wspace=.07,hspace=.06)
    cax=fig.add_axes([.33,.028,.5,.015]);fig.colorbar(im,cax=cax,orientation='horizontal',label='Visual-path Grad-CAM / common maximum')
    for ext in ['pdf','svg','png']:fig.savefig(OUT/('visual_path_gradcam.'+ext),dpi=600)
    plt.close(fig)
    for row,record in zip(provenance,selected):
        if sha(record.absolute_path)!=row['sha256']:raise RuntimeError('Selected image changed while generating maps')
    if sha(cache)!=proof['frozen_inputs']['university1652']['evidence_sha256']:
        raise RuntimeError('Image evidence cache changed while generating maps')
    dump(OUT/'completion.json',{'status':'computed_pending_visual_review','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checkpoints':checkpoints,'evidence_sha256':sha(cache),'evidence_metadata_sha256':sha(core.find_meta_path(cache)),'common_gradcam_maximum':maximum,'zero_gradcam_maps':sum(row['zero_map'] for row in scores),'images':len(selected),'heatmap_pairs':len(pairs),'descriptor_dtype':'float32','inference_batch_size':args.batch_size,'environment':{'python':platform.python_version(),'device':str(device),'packages':{name:importlib.metadata.version(name) for name in ['torch','torchvision','numpy','scikit-learn','matplotlib','Pillow']}},'script_sha256':sha(Path(__file__)),'note':'Qualitative figures are not a retrieval-performance experiment. Review PDF label clipping and caption before manuscript insertion. Separately fitted t-SNE coordinates are not comparable between panels. All-zero raw maps are retained and reported.','artifacts':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='completion.json'}})
    print('Computed real model visualizations; inspect render before publication')

if __name__=='__main__':main()
