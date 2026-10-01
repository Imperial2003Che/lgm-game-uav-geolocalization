#!/usr/bin/env python3
"""Measure T1 CUDA feasibility with the frozen training code, never its test split.

prepare: CPU source/weight/train-content/environment checks and immutable candidate plan.
measure: serial fresh-process candidates; native forward/backward/optimizer/AMP steps.
No trained checkpoint is retained or classified as a paper experiment result.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import functools
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import runpy
import subprocess
import sys
import time
import traceback
from typing import Any

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DEFAULT_DELIVERY = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
DEFAULT_WORK = Path(r'C:\项目\LGM-GAME-External-Baseline-Work')
DEFAULT_TRAIN = Path(r'C:\项目\IMTMN\datasets\University-1652\train')
CANDIDATES = {
    'qdfl_dinov2_b14': [24, 12, 8, 6, 4, 3, 2],
    'fsra_vit': [8, 4, 2],
    'sdpl_swinv2_b': [24, 12, 8, 6, 4, 3, 2],
    'ccr_convnext_b': [8, 4, 2],
    'mccg_convnext_tiny': [8],
}
NOMINAL = dict(zip(CANDIDATES, [24, 8, 24, 8, 8]))
SCHEMA = 'lgm-game.transactions-t1-resource-probe.v1'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()
def digest(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
def write(path, obj, exclusive=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True); f.write('\n')
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def under(path, root):
    try: Path(path).resolve().relative_to(Path(root).resolve()); return True
    except (ValueError, OSError): return False

def modules(delivery):
    sys.path.insert(0, str(Path(delivery).resolve()))
    from external_baselines import qdfl_adapter as q, mccg_adapter as m, run_transactions_t1_matrix as t
    return q, m, t

def validate_candidates(config, values):
    if config not in CANDIDATES or values != CANDIDATES[config]:
        raise ValueError('Candidate order must match the predefined protocol.')
    for n in values:
        if n < 2 or NOMINAL[config] % n: raise ValueError('Invalid accumulation or a degenerate single-item batch.')

def verify_proof(r):
    required = ('status', 'config_id', 'official_test_access', 'manuscript_result', 'completed_optimizer_steps', 'completed_amp_updates', 'peak_reserved_bytes', 'peak_allocated_bytes', 'sample_inventory', 'safety_margin_bytes', 'estimated_headroom_bytes', 'optimizer_parameter_change_observed')
    if any(k not in r for k in required): return False
    return (r['status'] == 'completed' and r['official_test_access'] is False and r['manuscript_result'] is False
            and r['completed_optimizer_steps'] >= 2 and r['completed_amp_updates'] >= 2
            and r['optimizer_parameter_change_observed'] is True
            and r['peak_allocated_bytes'] > 0 and r['peak_reserved_bytes'] >= r['peak_allocated_bytes']
            and len(r['sample_inventory']) > 0
            and r['estimated_headroom_bytes'] >= r['safety_margin_bytes'])

class AccessBoundary:
    """Enforce train-only image reads and read-only pinned code in this process."""
    def __init__(self, train_root, source_roots):
        self.train = Path(train_root).resolve()
        self.source_roots = [Path(p).resolve() for p in source_roots]
        self.images = set(); self.violations = []; self.integrity_hashing = False
    def check(self, raw, writing=False):
        if not isinstance(raw, (str, bytes, os.PathLike)): return
        p = Path(os.fsdecode(raw)).resolve()
        parts = {s.casefold() for s in p.parts}
        forbidden_names = {'query_drone', 'query_satellite', 'gallery_drone', 'gallery_satellite'}
        if parts & forbidden_names or under(p, self.train.parent/'test'):
            self.violations.append(str(p)); raise PermissionError('Official test access forbidden in resource probe: '+str(p))
        if writing and any(under(p, root) for root in self.source_roots):
            self.violations.append(str(p)); raise PermissionError('Pinned source mutation forbidden: '+str(p))
        if not writing and p.suffix.casefold() in IMAGE_SUFFIXES and not self.integrity_hashing:
            if not under(p, self.train):
                self.violations.append(str(p)); raise PermissionError('Only registered training images may be read: '+str(p))
            self.images.add(str(p))
    def hook(self, event, args):
        if event == 'open' and args:
            mode = args[1] if len(args)>1 else None
            flags = args[2] if len(args)>2 and isinstance(args[2],int) else 0
            writing = (isinstance(mode,str) and any(c in mode for c in 'wax+')) or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
            self.check(args[0], writing)
        elif event in ('os.listdir','os.scandir') and args: self.check(args[0])
        elif event in ('socket.connect','socket.getaddrinfo'):
            raise PermissionError('Network access is disabled: use only registered initialization weights.')
    def install_image_guards(self):
        from PIL import Image
        original = Image.open
        @functools.wraps(original)
        def guarded(fp, *a, **kw): self.check(fp); return original(fp,*a,**kw)
        Image.open = guarded
        try:
            import cv2
            old = cv2.imread
            def imread(filename,*a,**kw): self.check(filename); return old(filename,*a,**kw)
            cv2.imread = imread
        except ImportError: pass

def prepare(args):
    q,m,t = modules(args.delivery_root)
    ns = argparse.Namespace(delivery_root=args.delivery_root, train_root=args.train_root, external_work_root=args.external_work_root,
                            qdfl_python=args.qdfl_python, mccg_python=args.mccg_python)
    # This frozen function uses content hashes, not runtime_environment or CUDA construction.
    audit = t.verify_static_inputs(ns)
    torch_module=sys.modules.get('torch')
    if torch_module is not None and torch_module.cuda.is_initialized():
        raise RuntimeError('CPU preparation unexpectedly initialized CUDA.')
    output = args.output_root.resolve(); output.mkdir(parents=True,exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    session = output/('probe_'+stamp); session.mkdir()
    audit_path=session/'static_input_audit.json';write(audit_path,audit,exclusive=True)
    lock_path=args.delivery_root/'external_baselines/transactions_environment_lock.json'
    lock=load(lock_path)
    plan = dict(schema_version=SCHEMA, status='prepared_cpu_only', created_utc=now(), official_test_access=False, manuscript_result=False,
                delivery_root=str(args.delivery_root.resolve()),external_work_root=str(args.external_work_root.resolve()),
                train_root=str(args.train_root.resolve()),output_root=str(session),device_index=args.device_index,
                qdfl_python=str(args.qdfl_python.resolve()),mccg_python=str(args.mccg_python.resolve()),
                environment_lock_path=str(lock_path.resolve()),environment_lock_sha256=sha(lock_path),
                static_audit_path=str(audit_path),static_audit_sha256=sha(audit_path),
                profiler_path=str(Path(__file__).resolve()),profiler_sha256=sha(__file__),
                optimizer_steps=2,max_amp_step_attempts=16,workers=0,attempt_timeout_seconds=900,safety_margin_fraction=0.10,safety_margin_floor_bytes=512*1024**2,
                candidate_order={c:CANDIDATES[c] for c in args.configs},
                intended_selection='Largest predefined microbatch with two actual optimizer+AMP updates and reserved-memory safety margin.',
                resource_adaptation_disclosure='Gradient accumulation preserves nominal optimizer batch only; contrastive/triplet mining remains within each microbatch and is not equivalent to the nominal-batch objective.',
                scheduled_training='These engineering probes are discarded; formal fits start afresh from registered initialization.')
    for c,cs in plan['candidate_order'].items():validate_candidates(c,cs)
    plan['payload_sha256']=q.canonical_object_sha256(plan)
    write(session/'plan.json',plan,exclusive=True)
    write(output/'latest_prepared_plan.json',{'plan_path':str(session/'plan.json'),'plan_sha256':sha(session/'plan.json')})
    return {'status':plan['status'],'plan_path':str(session/'plan.json'),'cuda_initialized':False,'next_command':'Use --stage measure --plan <this plan> after the primary GPU matrix finishes.'}

def check_environment(plan, mccg, q):
    lock=load(plan['environment_lock_path'])
    key='mccg' if mccg else 'qdfl_framework'; expected=lock['environments'][key]
    if Path(sys.executable).resolve()!=Path(expected['interpreter_path']).resolve():raise RuntimeError('Interpreter does not match locked '+key+' environment.')
    rows=sorted({(str(d.metadata.get('Name','')).strip().lower(),d.version) for d in importlib.metadata.distributions() if d.metadata.get('Name')})
    registered=[tuple(row) for row in expected['installed_distributions']['rows']]
    if rows!=registered:raise RuntimeError('Installed package set differs from frozen environment; re-audit explicitly before profiling.')
    return dict(executable=sys.executable,python=sys.version,platform=platform.platform(),distributions=rows,
                distributions_sha256=q.canonical_object_sha256(rows),lock_sha256=sha(plan['environment_lock_path']))

class ProbeComplete(BaseException): pass

def child(args):
    plan=load(args.plan);config=args.config_id;micro=args.micro_batch
    if sha(__file__)!=plan['profiler_sha256']:raise RuntimeError('Profiler changed after plan preparation.')
    if micro not in plan['candidate_order'].get(config,[]):raise RuntimeError('Unregistered microbatch.')
    q,m,t=modules(Path(plan['delivery_root'])); plan_body=dict(plan);declared=plan_body.pop('payload_sha256')
    if q.canonical_object_sha256(plan_body)!=declared:raise RuntimeError('Plan hash mismatch.')
    q.assert_fit_environment_has_no_test_roots();m.assert_fit_environment_has_no_test_roots()
    t.assert_no_other_python_gpu_process()  # Runs before CUDA initialization.
    is_mccg=config=='mccg_convnext_tiny';env=check_environment(plan,is_mccg,q)
    ext=Path(plan['external_work_root']);directory=t.MCCG_SOURCE_DIR if is_mccg else t.QDFL_SOURCE_DIR
    source=ext/'patched_sources'/directory;patch=source.with_name(directory+'.patch_manifest.json')
    source_manifest=q.verify_patched_source(source,patch,expected_source_id='mccg' if is_mccg else 'qdfl')
    registry,registry_hash=q.load_weight_registry(Path(plan['delivery_root'])/'external_baselines/transactions_weight_registry.json')
    wid=m.WEIGHT_ID if is_mccg else q.CONFIG_SPECS[config].initialization
    weight=ext/'weights'/t.WEIGHT_FILES[wid];w=q.verify_weight(weight,registry[wid]['sha256'],registry[wid]['bytes'],wid)
    if sha(plan['static_audit_path'])!=plan['static_audit_sha256']:raise RuntimeError('Static input audit changed.')
    static=load(plan['static_audit_path']);attempt=Path(args.attempt_dir);attempt.mkdir(parents=True,exist_ok=True)
    boundary=AccessBoundary(plan['train_root'],[source]);sys.addaudithook(boundary.hook)
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',XFORMERS_DISABLED='1')
    import torch
    torch.cuda.set_device(plan['device_index']);torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
    start_free,total=torch.cuda.mem_get_info();start_reserved=torch.cuda.memory_reserved()
    stats=dict(completed_optimizer_steps=0,completed_amp_updates=0,optimizer_parameter_change_observed=False,optimizer_step_records=[],amp_scales=[])
    optimizer_seen=[];step_originals={};scaler_originals={};started=time.perf_counter()
    result=dict(schema_version=SCHEMA,status='running',created_utc=now(),config_id=config,micro_batch_size=micro,
                nominal_batch_size=NOMINAL[config],accumulate_grad_batches=NOMINAL[config]//micro,workers=0,
                resource_adapted=micro!=NOMINAL[config],official_test_access=False,manuscript_result=False,
                precision='16-mixed' if not is_mccg else 'native torch.cuda.amp autocast + GradScaler',
                native_recipe='mccg train.py via runpy' if is_mccg else 'QDFL U1652_model.training_step/configure_optimizers + Lightning Trainer',
                source_root=str(source),source_tree_sha256=source_manifest['patched_tree_sha256'],patch_manifest_sha256=sha(patch),
                initialization={'id':wid,**w},initialization_registry_sha256=registry_hash,
                static_audit_path=plan['static_audit_path'],static_audit_sha256=plan['static_audit_sha256'],
                training_inventory=static['dataset'],environment=env,profiler_sha256=sha(__file__),plan_sha256=sha(args.plan),
                device={'name':torch.cuda.get_device_name(),'total_memory_bytes':int(total),'index':plan['device_index'],'torch_cuda_runtime':torch.version.cuda},
                initial_free_bytes=int(start_free),initial_reserved_bytes=int(start_reserved),
                safety_margin_bytes=max(int(total*plan['safety_margin_fraction']),plan['safety_margin_floor_bytes']),
                accumulation_objective_notice=plan['resource_adaptation_disclosure'])
    write(attempt/'started.json',result,exclusive=True)
    def wrap_step(cls):
        original=cls.step;step_originals[cls]=original
        @functools.wraps(original)
        def step(opt,*a,**kw):
            # Actual native optimizer.step runs only if the GradScaler allows it.
            candidates=[p for g in opt.param_groups for p in g['params'] if p.grad is not None and p.requires_grad]
            samples=[(p,p.detach().reshape(-1)[:32].float().cpu().clone()) for p in candidates[:12]]
            out=original(opt,*a,**kw)
            torch.cuda.synchronize()
            changed=any(not torch.equal(before,p.detach().reshape(-1)[:32].float().cpu()) for p,before in samples)
            stats['optimizer_parameter_change_observed']|=changed
            stats['completed_optimizer_steps']+=1
            state_tensors=[v for st in opt.state.values() for v in st.values() if torch.is_tensor(v)]
            stats['optimizer_step_records'].append(dict(step=stats['completed_optimizer_steps'],optimizer=type(opt).__name__,parameters_with_grad=len(candidates),parameter_change_observed=changed,
                optimizer_state_tensors=len(state_tensors),optimizer_state_bytes=sum(x.numel()*x.element_size() for x in state_tensors),
                peak_allocated_bytes=int(torch.cuda.max_memory_allocated()),peak_reserved_bytes=int(torch.cuda.max_memory_reserved())))
            if not any(opt is x for x in optimizer_seen):optimizer_seen.append(opt)
            return out
        cls.step=step
    def wrap_scaler(cls):
        if cls in scaler_originals:return
        old=cls.update;scaler_originals[cls]=old
        @functools.wraps(old)
        def update(scaler,*a,**kw):
            before=float(scaler.get_scale());out=old(scaler,*a,**kw)
            stats['completed_amp_updates']+=1;stats['amp_scales'].append({'before':before,'after':float(scaler.get_scale())})
            if is_mccg and stats['completed_optimizer_steps']>=plan['optimizer_steps']:raise ProbeComplete()
            return out
        cls.update=update
    try:
        for cls in (torch.optim.SGD,torch.optim.AdamW,torch.optim.Adam):wrap_step(cls)
        # Patch base GradScaler once; the CUDA subclass inherits update.
        wrap_scaler(torch.amp.GradScaler if hasattr(torch,'amp') and hasattr(torch.amp,'GradScaler') else torch.cuda.amp.GradScaler)
        boundary.install_image_guards()
        if is_mccg:
            m.validate_published_recipe(source)
            os.environ['LGM_MCCG_OUTPUT_ROOT']=str(attempt/'native_scratch')
            os.environ['LGM_MCCG_CONVNEXT_T_22K_WEIGHTS']=str(weight)
            sys.path.insert(0,str(source));os.chdir(source)
            recipe=m.PUBLISHED_RECIPE
            sys.argv=[str(source/'train.py'),'--name','resource_probe','--data_dir',plan['train_root'],'--gpu_ids',str(plan['device_index']),
                      '--views',str(recipe['views']),'--lr',str(recipe['learning_rate']),'--batchsize','8','--triplet_loss',str(recipe['triplet_margin']),
                      '--epochs',str(recipe['epochs']),'--seed','1']
            try:runpy.run_path(str(source/'train.py'),run_name='__main__')
            except ProbeComplete:pass
        else:
            import pytorch_lightning as pl
            _,cfg=q.validate_official_config(source,q.CONFIG_SPECS[config])
            if cfg['model_configs'].get('grad_optimizer_name'):raise RuntimeError('Manual gradient optimizer requires a separately registered accumulation probe.')
            os.environ['LGM_QDFL_U1652_TRAIN_ROOT']=plan['train_root']
            envkeys={'dinov2_vitb14':'LGM_QDFL_DINOV2_VITB14_WEIGHTS','fsra_vit_base':'LGM_QDFL_FSRA_WEIGHTS','swin_v2_b_imagenet1k_v1':'LGM_QDFL_SWINV2_B_WEIGHTS','convnext_base_22k_1k_224':'LGM_QDFL_CONVNEXT_B_22K_WEIGHTS'}
            # The frozen backbones package imports the DINOv2 path dictionary even
            # for FSRA/SDPL/CCR; bind every already verified initialization path.
            for init_id,envkey in envkeys.items():os.environ[envkey]=str(ext/'weights'/t.WEIGHT_FILES[init_id])
            result['import_weight_bindings']={init_id:{'path':str(ext/'weights'/t.WEIGHT_FILES[init_id]),'registered_sha256':registry[init_id]['sha256'],'loaded_for_this_model':init_id==wid} for init_id in envkeys}
            pl.seed_everything(1,workers=True);DM,Model=q._load_qdfl_runtime(source)
            model=Model(**dict(cfg['model_configs']))
            data=DM(batch_size=micro,image_size=cfg['image_size'],sample_num=cfg['sample_num'],num_workers=0,DAC_sampling=cfg['DAC_sampling'],
                    drop_last=cfg.get('drop_last',True),show_data_stats=True,sources=['satellite','street','drone'])
            acc=NOMINAL[config]//micro
            class StopAfterActualUpdates(pl.Callback):
                def on_train_batch_end(self,trainer,module,outputs,batch,batch_idx):
                    if stats['completed_optimizer_steps']>=plan['optimizer_steps']:
                        trainer.should_stop=True
            # AMP can skip an optimizer request when the initial loss scale overflows.
            # Stop on actual native parameter updates, bounded by 16 AMP requests.
            trainer=pl.Trainer(accelerator='gpu',devices=[plan['device_index']],default_root_dir=attempt/'native_scratch',
                max_epochs=q.CONFIG_SPECS[config].epochs,max_steps=plan['max_amp_step_attempts'],limit_train_batches=plan['max_amp_step_attempts']*acc,
                accumulate_grad_batches=acc,precision='16-mixed',enable_checkpointing=False,logger=False,deterministic='warn',benchmark=False,
                callbacks=[StopAfterActualUpdates()],num_sanity_val_steps=0,limit_val_batches=0,limit_test_batches=0,enable_progress_bar=False,enable_model_summary=False)
            trainer.fit(model=model,datamodule=data)
            result['lightning_global_step']=int(trainer.global_step)
            result['native_logged_metrics']={k:float(v.detach().cpu()) for k,v in trainer.logged_metrics.items() if torch.is_tensor(v) and v.numel()==1}
        if stats['completed_optimizer_steps']<plan['optimizer_steps']:raise RuntimeError('Native optimizer did not complete the required updates (AMP may have skipped them).')
        if not stats['optimizer_parameter_change_observed']:raise RuntimeError('No sampled optimized parameter changed; feasibility proof rejected.')
        result['status']='completed'
    except BaseException as exc:
        if isinstance(exc,(KeyboardInterrupt,SystemExit)):status='interrupted'
        elif isinstance(exc,torch.cuda.OutOfMemoryError) or 'cuda out of memory' in str(exc).lower():status='oom'
        else:status='failed'
        result.update(status=status,error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
    finally:
        for cls,old in step_originals.items():cls.step=old
        for cls,old in scaler_originals.items():cls.update=old
        result.update(stats)
        result['duration_seconds']=time.perf_counter()-started
        result['peak_allocated_bytes']=int(torch.cuda.max_memory_allocated())
        result['peak_reserved_bytes']=int(torch.cuda.max_memory_reserved())
        free_end,_=torch.cuda.mem_get_info()
        result['end_free_bytes']=int(free_end)
        result['estimated_headroom_bytes']=int(min(free_end,start_free-max(0,result['peak_reserved_bytes']-start_reserved)))
        result['boundary_violations']=boundary.violations
        result['sample_inventory']=[{'relative_path':Path(p).relative_to(Path(plan['train_root'])).as_posix(),'bytes':Path(p).stat().st_size,'sha256':sha(p)} for p in sorted(boundary.images)]
        result['sample_inventory_sha256']=digest(result['sample_inventory'])
        try:
            # Source verification hashes any README figures as bytes; it performs no model/data read.
            boundary.integrity_hashing=True
            q.verify_patched_source(source,patch,expected_source_id='mccg' if is_mccg else 'qdfl')
        except Exception as e:result.update(status='source_integrity_failure',source_recheck_error=str(e))
        finally:boundary.integrity_hashing=False
        if result['status']=='completed' and not verify_proof(result):
            result['status']='insufficient_memory_margin' if result['estimated_headroom_bytes']<result['safety_margin_bytes'] else 'incomplete_optimizer_evidence'
        result['completed_utc']=now();result['payload_sha256']=q.canonical_object_sha256(result)
        write(attempt/'feasibility_manifest.json',result,exclusive=True)
    return {'status':result['status'],'manifest':str(attempt/'feasibility_manifest.json')}

def measure(args):
    plan=load(args.plan);q,m,t=modules(Path(plan['delivery_root']))
    if sha(__file__)!=plan['profiler_sha256']:raise RuntimeError('Profiler changed; prepare a new plan.')
    body=dict(plan);declared=body.pop('payload_sha256')
    if q.canonical_object_sha256(body)!=declared:raise RuntimeError('Plan payload hash mismatch.')
    if sha(plan['environment_lock_path'])!=plan['environment_lock_sha256']:raise RuntimeError('Environment lock changed.')
    t.assert_no_other_python_gpu_process()
    out=Path(plan['output_root']);measurement=out/('measurement_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));measurement.mkdir()
    fresh=t.verify_static_inputs(argparse.Namespace(delivery_root=Path(plan['delivery_root']),train_root=Path(plan['train_root']),
        external_work_root=Path(plan['external_work_root']),qdfl_python=Path(plan['qdfl_python']),mccg_python=Path(plan['mccg_python'])))
    if fresh['dataset']!=load(plan['static_audit_path'])['dataset']:raise RuntimeError('Training inventory changed since preparation.')
    write(measurement/'fresh_measurement_static_audit.json',fresh,exclusive=True)
    selected={};attempts=[]
    for config,values in plan['candidate_order'].items():
        validate_candidates(config,values)
        for micro in values:
            attempt=measurement/config/('micro_'+str(micro));attempt.mkdir(parents=True)
            executable=plan['mccg_python'] if config=='mccg_convnext_tiny' else plan['qdfl_python']
            command=[executable,'-B',str(Path(__file__).resolve()),'--stage','child','--plan',str(Path(args.plan).resolve()),'--config-id',config,'--micro-batch',str(micro),'--attempt-dir',str(attempt)]
            write(attempt/'launch.json',{'created_utc':now(),'command':command,'official_test_access':False},exclusive=True)
            environment=dict(os.environ);environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='1')
            with (attempt/'stdout.log').open('x',encoding='utf-8') as stdout,(attempt/'stderr.log').open('x',encoding='utf-8') as stderr:
                try:p=subprocess.run(command,env=environment,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,check=False,timeout=plan.get('attempt_timeout_seconds',900))
                except subprocess.TimeoutExpired:
                    write(attempt/'timeout.json',{'status':'timeout','timeout_seconds':plan.get('attempt_timeout_seconds',900),'terminated_by_parent':True},exclusive=True)
                    p=subprocess.CompletedProcess(command,124)
            path=attempt/'feasibility_manifest.json'
            if path.exists():r=load(path)
            else:
                r={'schema_version':SCHEMA,'status':'timeout' if p.returncode==124 else 'failed_before_model_probe','config_id':config,'micro_batch_size':micro,'returncode':p.returncode,'official_test_access':False,'manuscript_result':False,'stderr_path':str(attempt/'stderr.log')}
                write(path,r,exclusive=True)
            attempts.append({'config_id':config,'micro_batch':micro,'status':r['status'],'manifest_path':str(path),'manifest_sha256':sha(path)})
            write(measurement/'attempt_ledger.json',attempts)
            if verify_proof(r):
                common={'workers':0,'feasibility_manifest_path':str(path),'feasibility_manifest_sha256':sha(path)}
                if config=='mccg_convnext_tiny':common.update(batch_size=8,resource_adapted=False)
                else:common.update(micro_batch_size=micro,nominal_batch_size=NOMINAL[config],accumulate_grad_batches=NOMINAL[config]//micro)
                selected[config]=common;break
            # A predetermined smaller candidate is allowed only for a measured memory limit.
            if r['status'] not in ('oom','insufficient_memory_margin'):break
    full=set(selected)==set(CANDIDATES)
    device=next((load(r['feasibility_manifest_path'])['device'] for r in selected.values()),{})
    profile={'schema_version':t.PROFILE_SCHEMA,'status':'frozen' if full else 'incomplete_measured','created_utc':now(),'device':device,
        'configs':selected,'missing_configs':sorted(set(CANDIDATES)-set(selected)),
        'feasibility_policy':{'official_test_access':False,'manuscript_result':False,'scope':'native construction and two actual optimizer/AMP updates only','no_silent_oom_retry':True,'selection_rule':plan['intended_selection'],'accumulation_disclosure':plan['resource_adaptation_disclosure']},
        'plan_path':str(Path(args.plan).resolve()),'plan_sha256':sha(args.plan),'attempt_ledger_sha256':sha(measurement/'attempt_ledger.json')}
    profile['payload_sha256']=q.canonical_object_sha256(profile)
    path=measurement/'transactions_t1_resource_profile.json';write(path,profile,exclusive=True)
    if full:t.validate_profile(path,t.validate_matrix(Path(plan['delivery_root'])/'external_baselines/transactions_t1_matrix.json'))
    return {'status':profile['status'],'profile_path':str(path),'selected_configs':list(selected),'missing_configs':profile['missing_configs']}

def self_test():
    for c,x in CANDIDATES.items():validate_candidates(c,x)
    try:validate_candidates('fsra_vit',[8,3]);raise AssertionError('unregistered candidate accepted')
    except ValueError:pass
    assert not verify_proof({'status':'completed'})
    good=dict(status='completed',config_id='fsra_vit',official_test_access=False,manuscript_result=False,completed_optimizer_steps=2,completed_amp_updates=2,
              peak_reserved_bytes=20,peak_allocated_bytes=10,sample_inventory=[{'test_fixture':True}],safety_margin_bytes=10,estimated_headroom_bytes=11,optimizer_parameter_change_observed=True)
    assert verify_proof(good)
    for change in [{'official_test_access':True},{'completed_optimizer_steps':0},{'optimizer_parameter_change_observed':False},{'sample_inventory':[]},{'estimated_headroom_bytes':9}]:assert not verify_proof({**good,**change})
    boundary=AccessBoundary(HERE/'boundary_fixture/train',[HERE/'boundary_fixture/pinned'])
    boundary.check(HERE/'boundary_fixture/train/drone/0001/a.jpg')
    for p,w in [(HERE/'boundary_fixture/test',False),(HERE/'boundary_fixture/elsewhere/a.jpg',False),(HERE/'boundary_fixture/pinned/code.py',True)]:
        try:boundary.check(p,w);raise AssertionError('boundary accepted forbidden path')
        except PermissionError:pass
    return {'status':'passed','checks':['fixed candidate order/divisibility','no proof from global-step claim alone','no test access','no outside training image','no pinned source write','margin and optimizer-update evidence'],'cuda_imported':'torch' in sys.modules}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=['prepare','measure','child','self-test'],default='prepare')
    p.add_argument('--delivery-root',type=Path,default=DEFAULT_DELIVERY);p.add_argument('--external-work-root',type=Path,default=DEFAULT_WORK)
    p.add_argument('--train-root',type=Path,default=DEFAULT_TRAIN);p.add_argument('--output-root',type=Path,default=HERE/'resource_measurements')
    p.add_argument('--qdfl-python',type=Path,default=Path(r'C:\项目\.venvs\lgm-transactions\Scripts\python.exe'))
    p.add_argument('--mccg-python',type=Path,default=Path(r'C:\项目\.venvs\lgm-mccg\Scripts\python.exe'))
    p.add_argument('--device-index',type=int,default=0);p.add_argument('--configs',nargs='+',choices=list(CANDIDATES),default=list(CANDIDATES))
    p.add_argument('--plan',type=Path);p.add_argument('--config-id',choices=list(CANDIDATES));p.add_argument('--micro-batch',type=int);p.add_argument('--attempt-dir',type=Path)
    a=p.parse_args()
    if a.stage in ('measure','child') and not a.plan:p.error('--plan is required.')
    if a.stage=='child' and any(x is None for x in (a.config_id,a.micro_batch,a.attempt_dir)):p.error('child requires config/microbatch/attempt.')
    if a.device_index<0:p.error('device index must be nonnegative')
    result={'prepare':prepare,'measure':measure,'child':child,'self-test':lambda _:self_test()}[a.stage](a)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status'] in ('prepared_cpu_only','completed','frozen','passed') else 2

if __name__=='__main__':raise SystemExit(main())
