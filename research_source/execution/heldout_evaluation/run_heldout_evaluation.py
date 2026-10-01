"""Official T2 final-checkpoint evaluation; never trains or selects a model.

Default scope evaluates the held-out height (48 tasks). Scope ``all`` also
reports the three seen heights required by the existing extension protocol
(192 tasks). Every task retains the complete 200-identity gallery.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import statistics
import sys
import traceback

HERE=Path(__file__).resolve().parent
DEFAULT_ROOT=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
HEIGHTS=('150','200','250','300')
METRICS=('r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP','MRR')
SCHEMA='lgm-game.t2-official-evaluation.v1'
sys.dont_write_bytecode=True

def utc(): return datetime.now(timezone.utc).isoformat()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+f'.tmp.{os.getpid()}')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temp,path)
def sealed(obj):return {**obj,'payload_sha256':canonical(obj)}
def validate_seal(obj):
    body=dict(obj);declared=body.pop('payload_sha256',None)
    if canonical(body)!=declared:raise RuntimeError('Manifest payload hash differs')
def artifact(path):return {'path':str(Path(path).resolve()),'bytes':Path(path).stat().st_size,'sha256':sha(path)}

def task_names(height,scope):
    heights=HEIGHTS if scope=='all' else (height,)
    return [name for h in heights for name in (f'sues200_uav_{h}m_to_satellite',f'sues200_satellite_to_uav_{h}m')]

def task_height(name):
    matches=[h for h in HEIGHTS if f'{h}m' in name]
    if len(matches)!=1:raise RuntimeError('Unexpected official task name: '+name)
    return matches[0]

def select_tasks(tasks,height,scope,train_ids):
    wanted=task_names(height,scope);by_name={t.name:t for t in tasks}
    if len(by_name)!=len(tasks) or set(by_name)!=set(task_names(height,'all')):
        raise RuntimeError('Frozen core did not return exactly eight official SUES tasks')
    selected=[by_name[name] for name in wanted]
    all_ids={f'{i:04d}' for i in range(1,201)};test_ids=all_ids-set(train_ids)
    if len(set(train_ids))!=120 or len(test_ids)!=80:raise RuntimeError('SUES split differs')
    for task in selected:
        d2s='_uav_' in task.name and task.name.endswith('_to_satellite')
        nq,ng=(4000,200) if d2s else (80,10000)
        if (len(task.query),len(task.gallery))!=(nq,ng):raise RuntimeError('Incomplete query/gallery task: '+task.name)
        if {r.label for r in task.query}!=test_ids or {r.label for r in task.gallery}!=all_ids:
            raise RuntimeError('Test identity or full-gallery membership differs: '+task.name)
        if len({r.relative_path for r in task.query})!=nq or len({r.relative_path for r in task.gallery})!=ng:
            raise RuntimeError('Duplicate paths in official task')
        h=task_height(task.name)
        for r in (*task.query,*task.gallery):
            if r.view=='drone' and r.altitude!=h:raise RuntimeError('Wrong altitude in official task')
        if {r.view for r in task.query}!={'drone' if d2s else 'satellite'} or {r.view for r in task.gallery}!={'satellite' if d2s else 'drone'}:
            raise RuntimeError('Query/gallery view roles differ')
    return selected

def pinned_sources(args):
    pins=load(HERE/'frozen_source_pins.json')
    for relative,expected in pins['files'].items():
        path=args.delivery_root/relative
        if not path.is_file() or path.stat().st_size!=expected['bytes'] or sha(path)!=expected['sha256']:
            raise RuntimeError('Pinned original source changed: '+str(path))
    return pins

def modules(args):
    sys.path.insert(0,str(args.delivery_root/'lgm_game_pytorch'))
    core=importlib.import_module('lgm_game_pytorch.formal_retrieval')
    primary=importlib.import_module('experiments.run_frozen_formal_matrix')
    t2=importlib.import_module('experiments.run_transactions_t2_heldout_matrix')
    fit=importlib.import_module('experiments.run_sues_heldout_fit')
    for m in (core,primary,t2,fit):
        if not Path(m.__file__).resolve().is_relative_to(args.delivery_root):
            raise RuntimeError('Module imported from another delivery: '+m.__name__)
    return core,primary,t2,fit

def pre_gate_presence(args,matrix):
    """Fail before importing models when whole-block prerequisites are absent."""
    missing=[]
    runroot=args.delivery_root/'lgm_game_pytorch/runs/transactions_t2_heldout'
    for row in matrix['runs']:
        p=runroot/'fits'/row['run_id']/'heldout_fit_manifest.json'
        if not p.is_file() or load(p).get('status')!='completed':missing.append(row['run_id'])
    if missing:raise RuntimeError(f'All 24 completed T2 fits are required; {len(missing)} pending: {missing[:3]}')

def gate(args):
    pins=pinned_sources(args)
    matrix_path=args.delivery_root/'lgm_game_pytorch/experiments/transactions_t2_heldout_matrix.json'
    matrix=load(matrix_path);pre_gate_presence(args,matrix)
    core,primary,t2,fit=modules(args)
    matrix=t2.validate_matrix(matrix_path)
    primary_ledger_path=args.delivery_root/'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'
    primary_ledger=load(primary_ledger_path)
    data=primary.dataset_specs(args.delivery_root,args.university_root,args.sues_root)
    mains=primary.main_run_specs(args.delivery_root,primary.DATASETS,primary.MAIN_VARIANTS,primary.MAIN_SEEDS)
    sensitivity=primary.sensitivity_run_specs(args.delivery_root,primary.DATASETS)
    primary.validate_registry(mains,sensitivity);all_primary=mains+sensitivity
    expected={'formal_script_sha256':sha(Path(core.__file__)),'runner_sha256':sha(Path(primary.__file__)),
              'protocol_sha256':sha(args.delivery_root/'FORMAL_EXPERIMENT_PROTOCOL.md'),
              'registered_registry_sha256':primary.registry_sha256(all_primary)}
    for key,value in expected.items():
        if primary_ledger.get(key)!=value:raise RuntimeError('Primary ledger fingerprint differs: '+key)
    primary_manifest_hashes={}
    for spec in all_primary:
        ds=data[spec.dataset]
        if ds.evidence_sha256!=primary_ledger['frozen_inputs'][spec.dataset]['evidence_sha256']:
            raise RuntimeError('Primary evidence differs from ledger')
        issues=primary.training_completion_issues(spec,ds,expected['formal_script_sha256'])
        issues+=primary.evaluation_completion_issues(spec,ds)
        if not issues:issues+=primary.checkpoint_artifact_hash_issues(spec)
        if issues:raise RuntimeError(f'Primary gate failed: {spec.identifier}: {issues}')
        evaluation=load(spec.evaluation_dir/'evaluation_manifest.json')
        arrays=[(name,item) for name,item in evaluation['artifacts'].items() if name.startswith('per_query_arrays/') and name.endswith('.npz')]
        if len(arrays)!=(3 if spec.dataset=='university1652' else 8):raise RuntimeError('Primary per-query artifact count differs')
        for name,item in arrays:
            p=(spec.evaluation_dir/name).resolve()
            if not p.is_relative_to(spec.evaluation_dir.resolve()) or not p.is_file() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:
                raise RuntimeError('Primary per-query artifact differs: '+name)
        primary_manifest_hashes[spec.identifier]=sha(spec.evaluation_dir/'evaluation_manifest.json')
    # Reuse the original training inventory and exact frozen-audit comparison.
    audit=t2.static_audit(args,require_primary=True)
    runroot=args.delivery_root/'lgm_game_pytorch/runs/transactions_t2_heldout'
    ledger_path=runroot/'transactions_t2_ledger.json';ledger=load(ledger_path)
    if ledger.get('schema_version')!=t2.LEDGER_SCHEMA or ledger.get('frozen_inputs')!={'static_audit':audit,'static_audit_payload_sha256':audit['payload_sha256']}:
        raise RuntimeError('Original T2 source/data ledger differs from the current original audit')
    fits={}
    for row in matrix['runs']:
        directory=runroot/'fits'/row['run_id']
        command=t2.fit_command(args,row,directory,resume='none')
        height,_,fit_args=fit.parse_args(command[3:])
        fit.validate_core_args(fit_args,height)
        expected_config=fit.build_adapter_config(fit_args,height)
        if load(directory/'heldout_adapter_config.json')!=expected_config:
            raise RuntimeError('T2 adapter configuration differs from registered command: '+row['run_id'])
        manifest=fit.validate_completed_fit(directory,sha(directory/'heldout_adapter_config.json'),height,row['variant'],row['seed'])
        fits[row['run_id']]={'directory':str(directory),'checkpoint':artifact(directory/'best.pt'),
                             'fit_manifest':artifact(directory/'heldout_fit_manifest.json'),
                             'config_sha256':manifest['core_run_config_payload_sha256']}
    cache=args.delivery_root/'lgm_game_pytorch/evidence_cache/sues200_clip_image_evidence.npz'
    split=args.delivery_root/'lgm_game_pytorch/manifests/sues200_official_train_ids.yaml'
    store=core.EvidenceStore.load([cache]);records=core.derive_all_records(store,args.sues_root,'sues200')
    train_ids,_=core.parse_sues_manifest(split)
    tasks=core.build_official_evaluation_tasks(records,'sues200',train_ids)
    task_contracts={}
    for height in HEIGHTS:
        chosen=select_tasks(tasks,height,args.scope,train_ids)
        task_contracts[height]={'tasks':task_names(height,args.scope),
                              'membership_sha256':core.protocol_membership_hash(chosen),
                              'image_inventory':core.inventory_hash([r for t in chosen for r in (*t.query,*t.gallery)],'content')}
    fingerprint={'schema_version':SCHEMA,'source_pins':pins,'new_runner':artifact(Path(__file__)),
                 'source_pin_file':artifact(HERE/'frozen_source_pins.json'),
                 'matrix':artifact(matrix_path),'t2_training_ledger':artifact(ledger_path),
                 'primary_evaluation_manifest_hashes':primary_manifest_hashes,
                 'fits':fits,'task_contracts':task_contracts,'scope':args.scope,
                 'evaluation_settings':{'python':str(args.python),'device':args.device,'amp':args.amp,
                                        'batch_size':args.batch_size,'workers':args.workers,'chunk_size':args.chunk_size},
                 'sues_root':str(args.sues_root),'cache':artifact(cache),'cache_metadata':artifact(core.find_meta_path(cache)),
                 'official_split':artifact(split)}
    return core,t2,matrix,fingerprint,tasks,train_ids

def read_query_metrics(npz_path,task):
    import numpy as np
    with np.load(npz_path,allow_pickle=False) as payload:
        a={k:payload[k] for k in payload.files}
    n=len(task.query)
    if any(len(value)!=n for value in a.values()):raise RuntimeError('Per-query row counts differ')
    for key,expected in [('query_paths',[r.relative_path for r in task.query]),('query_labels',[r.label for r in task.query])]:
        if a[key].tolist()!=expected:raise RuntimeError('Per-query ordering/identity differs: '+key)
    indices=a['top1_gallery_indices']
    if indices.dtype.kind not in 'iu' or (indices<0).any() or (indices>=len(task.gallery)).any():raise RuntimeError('Invalid top-1 indices')
    for key,attr in [('top1_gallery_paths','relative_path'),('top1_gallery_labels','label')]:
        if a[key].tolist()!=[getattr(task.gallery[int(i)],attr) for i in indices]:raise RuntimeError('Top-1 gallery provenance differs')
    if not np.array_equal(a['correct'],a['query_labels']==a['top1_gallery_labels']):raise RuntimeError('Top-1 correctness differs')
    rr=a['reciprocal_rank'];ap=a['per_query_official_trapezoid_AP'];margin=a['margin']
    if not all(np.isfinite(x).all() for x in (rr,ap,margin)) or (rr<=0).any() or (rr>1).any() or (ap<0).any() or (ap>1).any():
        raise RuntimeError('Invalid query metrics')
    rank=np.rint(1/rr.astype(np.float64)).astype(np.int64)
    if (rank<1).any() or (rank>len(task.gallery)).any() or not np.allclose(rr,1/rank,rtol=1e-6,atol=0):
        raise RuntimeError('Reciprocal rank does not encode an integer first-positive rank')
    if not np.array_equal(rank==1,a['correct'].astype(bool)):raise RuntimeError('Recall and first-positive rank disagree')
    metrics={f'r_at_{k}':float(np.mean(rank<=k)) for k in (1,5,10,20)}
    metrics.update(official_trapezoid_mAP=float(ap.mean()),MRR=float(rr.mean()),mean_top1_margin=float(margin.mean()))
    return metrics

def validate_evaluation(directory,row,fingerprint,tasks,train_ids,core):
    directory=Path(directory)
    chosen=select_tasks(tasks,row['heldout_altitude_m'],fingerprint['scope'],train_ids)
    manifest=load(directory/'evaluation_manifest.json');validate_seal(manifest)
    if manifest.get('schema_version')!=core.SCHEMA_VERSION or manifest.get('status')!='completed' or manifest.get('dataset')!='sues200':
        raise RuntimeError('Incomplete frozen-core evaluation manifest')
    fit=fingerprint['fits'][row['run_id']]
    cp=manifest.get('checkpoint',{})
    if cp.get('sha256')!=fit['checkpoint']['sha256'] or Path(cp.get('path','')).resolve()!=Path(fit['checkpoint']['path']) or cp.get('selected_training_epoch')!=79 or cp.get('variant')!=row['variant'] or cp.get('training_run_config_sha256')!=fit['config_sha256']:
        raise RuntimeError('Evaluation checkpoint provenance differs')
    contract=fingerprint['task_contracts'][row['heldout_altitude_m']]
    if manifest.get('image_inventory')!=contract['image_inventory'] or manifest.get('protocol_membership_sha256')!=contract['membership_sha256']:
        raise RuntimeError('Evaluation data bytes or task membership differ')
    caches=manifest.get('evidence_caches',[])
    if len(caches)!=1 or caches[0].get('sha256')!=fingerprint['cache']['sha256']:
        raise RuntimeError('Evaluation evidence provenance differs')
    controls=manifest.get('leakage_controls',{})
    if controls.get('test_used_during_training_or_model_selection') is not False or controls.get('all_official_queries_used') is not True or controls.get('all_official_gallery_images_used') is not True:
        raise RuntimeError('Evaluation protocol controls absent')
    required={'metrics.json','metrics.csv'}|{f'per_query_arrays/{core.slugify(t.name)}_per_query.npz' for t in chosen}
    if not required<=set(manifest.get('artifacts',{})):raise RuntimeError('Evaluation manifest omits required artifacts')
    for name,item in manifest['artifacts'].items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file() or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:
            raise RuntimeError('Evaluation artifact bytes differ: '+name)
    metrics=load(directory/'metrics.json')
    if metrics.get('full_gallery') is not True or set(metrics.get('results',{}))!=set(contract['tasks']):
        raise RuntimeError('Missing/extra metrics tasks')
    with (directory/'metrics.csv').open(newline='',encoding='utf-8') as f:raw_csv=list(csv.DictReader(f))
    csv_rows={r['task']:r for r in raw_csv}
    if len(raw_csv)!=len(chosen) or set(csv_rows)!=set(contract['tasks']):raise RuntimeError('CSV tasks differ')
    for task in chosen:
        reported=metrics['results'][task.name]
        expected_scale={'queries':len(task.query),'gallery':len(task.gallery),'query_identities':80,'gallery_identities':200}
        for key,value in expected_scale.items():
            if reported.get(key)!=value or int(csv_rows[task.name][key])!=value:raise RuntimeError('Task scale differs: '+key)
        derived=read_query_metrics(directory/'per_query_arrays'/f'{core.slugify(task.name)}_per_query.npz',task)
        for key,value in derived.items():
            if abs(float(reported[key])-value)>2e-7 or abs(float(csv_rows[task.name][key])-value)>2e-7:
                raise RuntimeError('Aggregate/query metric discrepancy: '+task.name+'/'+key)
    return metrics['results']

def aggregate(rows):
    groups={}
    for row in rows:
        key=(row['heldout_altitude_m'],row['variant'],row['task'])
        groups.setdefault(key,[]).append(row)
    output=[]
    for (height,variant,task),group in sorted(groups.items()):
        if sorted(r['seed'] for r in group)!=[1,2,3]:raise RuntimeError('Aggregation requires all three distinct seeds')
        result={'heldout_altitude_m':height,'evaluated_altitude_m':task_height(task),
                'evaluation_height_role':'heldout' if height==task_height(task) else 'seen',
                'variant':variant,'task':task,'seeds':3,'queries_per_seed':group[0]['queries'],'gallery_per_seed':group[0]['gallery']}
        for metric in METRICS:
            values=[float(r[metric]) for r in group]
            result[metric+'_mean']=statistics.mean(values);result[metric+'_sd']=statistics.stdev(values)
        output.append(result)
    return output

def write_csv(path,rows):
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

@contextmanager
def exclusive_output(root):
    root.mkdir(parents=True,exist_ok=True)
    with (root/'evaluation.lock').open('a+b') as lock:
        lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield

def run(args):
    # Keep scopes in separate directories, with independently locked fingerprints.
    out=args.output_root/args.scope
    with exclusive_output(out):
        invocations=out/'invocations';invocations.mkdir(exist_ok=True)
        invocation_number=max([int(p.stem) for p in invocations.glob('*.json') if p.stem.isdigit()],default=0)+1
        invocation_path=invocations/f'{invocation_number:04d}.json'
        status={'schema_version':SCHEMA,'status':'checking_gate','started_utc':utc(),'pid':os.getpid(),'scope':args.scope}
        save(out/'status.json',status);save(invocation_path,status)
        try:
            core,t2,matrix,fingerprint,tasks,train_ids=gate(args)
            digest=canonical(fingerprint);gate_path=out/'gate.json'
            if gate_path.exists():
                previous=load(gate_path);validate_seal(previous)
                if previous['fingerprint']!=fingerprint:raise RuntimeError('Frozen evaluation inputs/settings changed; use a separate reviewed output root')
            else:save(gate_path,sealed({'schema_version':SCHEMA,'created_utc':utc(),'fingerprint':fingerprint}))
            status.update(status='gate_passed',fingerprint_sha256=digest);save(out/'status.json',status)
            if args.stage=='gate':return
            all_rows=[];completed_manifests={}
            for row in matrix['runs']:
                run_dir=out/'runs'/row['run_id'];completion=run_dir/'completion.json'
                status.update(status='evaluating',active_run=row['run_id'],updated_utc=utc());save(out/'status.json',status)
                if completion.exists():
                    receipt=load(completion);validate_seal(receipt)
                    if receipt.get('fingerprint_sha256')!=digest:raise RuntimeError('Completed evaluation fingerprint differs')
                    attempt=Path(receipt['attempt_directory']).resolve()
                    if not attempt.is_relative_to(run_dir.resolve()):raise RuntimeError('Completed attempt path escapes run')
                    if sha(attempt/'evaluation_manifest.json')!=receipt['evaluation_manifest_sha256']:raise RuntimeError('Completed evaluation manifest changed')
                    results=validate_evaluation(attempt,row,fingerprint,tasks,train_ids,core)
                else:
                    if args.stage=='aggregate':raise RuntimeError('Cannot aggregate an incomplete run: '+row['run_id'])
                    if args.device.startswith('cuda'):t2.assert_no_other_python_gpu_process()
                    attempts=run_dir/'attempts';attempts.mkdir(parents=True,exist_ok=True)
                    numbers=[int(p.name) for p in attempts.iterdir() if p.is_dir() and p.name.isdigit()]
                    attempt=attempts/f'{max(numbers,default=0)+1:04d}';attempt.mkdir()
                    attempt_status={'schema_version':SCHEMA,'event':'attempt_started','started_utc':utc(),'run':row,'fingerprint_sha256':digest}
                    save(attempt/'attempt_start.json',attempt_status)
                    original=core.build_official_evaluation_tasks
                    def restricted(records,dataset,ids):
                        if dataset!='sues200':raise RuntimeError('T2 evaluates only SUES-200')
                        return select_tasks(original(records,dataset,ids),row['heldout_altitude_m'],args.scope,ids)
                    try:
                        fit=fingerprint['fits'][row['run_id']]
                        cmd=['evaluate','--dataset','sues200','--data-root',str(args.sues_root),
                             '--evidence',fingerprint['cache']['path'],'--sues-manifest',fingerprint['official_split']['path'],
                             '--checkpoint',fit['checkpoint']['path'],'--output-dir',str(attempt),'--device',args.device,
                             '--seed',str(row['seed']),'--workers',str(args.workers),'--eval-batch-size',str(args.batch_size),
                             '--eval-chunk-size',str(args.chunk_size),'--data-hash-mode','content','--amp' if args.amp else '--no-amp']
                        save(attempt/'evaluation_request.json',{'arguments':cmd,'row':row,'scope':args.scope,'fingerprint_sha256':digest})
                        core_args=core.build_parser().parse_args(cmd);core.validate_cli(core_args)
                        core.build_official_evaluation_tasks=restricted
                        core.run_evaluate(core_args)
                        results=validate_evaluation(attempt,row,fingerprint,tasks,train_ids,core)
                        if sha(Path(fit['checkpoint']['path']))!=fit['checkpoint']['sha256']:raise RuntimeError('Checkpoint changed during evaluation')
                        receipt=sealed({'schema_version':SCHEMA,'status':'completed','run':row,'scope':args.scope,
                                        'fingerprint_sha256':digest,'attempt_directory':str(attempt.resolve()),'completed_utc':utc(),
                                        'evaluation_manifest_sha256':sha(attempt/'evaluation_manifest.json')})
                        save(completion,receipt)
                    except BaseException as exc:
                        save(attempt/'failure.json',sealed({'status':'failed','failed_utc':utc(),'error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc(),'retained_attempt_directory':str(attempt)}))
                        raise
                    finally:
                        core.build_official_evaluation_tasks=original
                        import torch
                        if args.device.startswith('cuda'):torch.cuda.empty_cache()
                completed_manifests[row['run_id']]=artifact(completion)
                for task,values in results.items():all_rows.append({'run_id':row['run_id'],'heldout_altitude_m':row['heldout_altitude_m'],'variant':row['variant'],'seed':row['seed'],'task':task,**values})
            expected_tasks=192 if args.scope=='all' else 48
            if len(all_rows)!=expected_tasks:raise RuntimeError('Matrix evaluation count differs')
            pinned_sources(args)
            if sha(Path(__file__))!=fingerprint['new_runner']['sha256']:raise RuntimeError('Evaluation runner changed while executing')
            summary=aggregate(all_rows)
            save(out/'per_seed_metrics.json',{'unit':'fraction','rows':all_rows});write_csv(out/'per_seed_metrics.csv',all_rows)
            save(out/'three_seed_summary.json',{'unit':'fraction','SD':'sample standard deviation, ddof=1 across three independent training seeds','rows':summary});write_csv(out/'three_seed_summary.csv',summary)
            table=[{**{k:v for k,v in r.items() if not k.endswith(('_mean','_sd'))},**{k:100*v for k,v in r.items() if k.endswith(('_mean','_sd'))}} for r in summary]
            write_csv(out/'three_seed_summary_percent.csv',table)
            save(out/'completion.json',sealed({'schema_version':SCHEMA,'status':'completed','completed_utc':utc(),'scope':args.scope,'checkpoint_count':24,'task_evaluations':expected_tasks,'fingerprint_sha256':digest,'run_receipts':completed_manifests,'summary_artifacts':{name:artifact(out/name) for name in ['per_seed_metrics.json','per_seed_metrics.csv','three_seed_summary.json','three_seed_summary.csv','three_seed_summary_percent.csv']}}))
            status.update(status='completed',completed_utc=utc(),task_evaluations=expected_tasks);status.pop('active_run',None);save(out/'status.json',status)
        except BaseException as exc:
            status.update(status='failed_or_blocked',failed_utc=utc(),error_type=type(exc).__name__,error=str(exc));save(out/'status.json',status)
            raise
        finally:
            save(invocation_path,status)

def parse_args(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--delivery-root',type=Path,default=DEFAULT_ROOT)
    p.add_argument('--university-root',type=Path,default=Path(r'C:\项目\IMTMN\datasets\University-1652'))
    p.add_argument('--sues-root',type=Path,default=Path(r'C:\项目\IMTMN\datasets\SUES-200'))
    p.add_argument('--python',type=Path,default=Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe'))
    p.add_argument('--output-root',type=Path,default=HERE/'results')
    p.add_argument('--scope',choices=['heldout','all'],default='heldout')
    p.add_argument('--stage',choices=['plan','gate','evaluate','aggregate'],default='plan')
    p.add_argument('--device',default='cuda:0');p.add_argument('--device-index',type=int,default=0)
    p.add_argument('--batch-size',type=int,default=128);p.add_argument('--workers',type=int,default=0)
    p.add_argument('--chunk-size',type=int,default=128);p.add_argument('--amp',action=argparse.BooleanOptionalAction,default=True)
    args=p.parse_args(argv)
    for key in ['delivery_root','university_root','sues_root','python','output_root']:setattr(args,key,getattr(args,key).resolve())
    if not args.output_root.is_relative_to(HERE):p.error('All evaluation outputs must remain inside this new heldout_evaluation directory')
    if args.batch_size<1 or args.chunk_size<1 or args.workers<0 or args.device_index<0:p.error('Invalid runtime resource settings')
    if args.stage!='plan' and Path(sys.executable).resolve()!=args.python:p.error('Use the declared original baseline interpreter')
    return args

def main():
    args=parse_args()
    if args.stage=='plan':
        pinned_sources(args)
        matrix=load(args.delivery_root/'lgm_game_pytorch/experiments/transactions_t2_heldout_matrix.json')
        plan={'schema_version':SCHEMA,'status':'plan_only_no_model_loaded','scope':args.scope,'fits':24,
              'task_evaluations':192 if args.scope=='all' else 48,
              'query_gallery':{'uav_to_satellite':[4000,200],'satellite_to_uav':[80,10000]},
              'query_identities':80,'gallery_identities':200,'checkpoint_selection':'registered final epoch 79',
              'runs':[{**r,'tasks':task_names(r['heldout_altitude_m'],args.scope)} for r in matrix['runs']]}
        save(HERE/f'evaluation_plan_{args.scope}.json',plan);print(json.dumps({k:v for k,v in plan.items() if k!='runs'},indent=2));return
    run(args)

if __name__=='__main__':main()
