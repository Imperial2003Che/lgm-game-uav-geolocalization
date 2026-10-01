"""Prepare, bind completed training evidence, or execute 3x10 DAC evaluations.

All scientific imports are inside functions reached only after future release.
The present delivery is source preparation and standard-library mock validation.
"""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import statistics
import subprocess
import sys
import traceback
from protocol import *

def read_prepared(path):
    path=local_output(path);value=load(path);verify_seal(value)
    if value.get('schema')!=SCHEMA or value.get('status')!='prepared_waiting_for_training':raise RuntimeError('Unexpected independent evaluation contract')
    if value['sources']!=source_evidence():raise RuntimeError('Prepared scientific sources changed')
    for item in value['training_plans']:verify_artifact(item['plan'])
    verify_artifact(value['training_execution_plan']);verify_artifact(value['training_execution_package']);verify_execution_package(value['training_execution_package'])
    validate_execution_plan(value['training_execution_plan']['path'],value['training_plans'],value['python'])
    for key in ('source_manifest','inventory','tasks'):verify_artifact(value['membership'][key])
    return value

def prepare(args):
    output=local_output(args.output)
    if output.exists():raise RuntimeError('Prepared contracts are immutable; choose a new output path')
    if len(args.training_plan)!=3:raise RuntimeError('Supply exactly three registered training plans')
    plans=[]
    for seed,path in zip(SEEDS,args.training_plan):
        path=Path(path).resolve();plan=load(path);directory=validate_training_plan(plan,seed)
        plans.append({'seed':seed,'plan':artifact(path),'output_directory':str(directory),
                      'future_checkpoint':'weights_end.pth','checkpoint_sha256':None,
                      'checkpoint_binding_status':'awaiting verified completed training; no weight hash is invented'})
    require(sha(args.training_execution_plan)==args.training_execution_sha256,'Externally pinned DAC execution specification required')
    verify_execution_package(execution_package_evidence(),args.training_package_sha256)
    validate_execution_plan(args.training_execution_plan,plans,args.python)
    member=membership_evidence(args.membership)
    runtime=helpers().runtime_snapshot(args.python)
    if runtime!=member['runtime']:raise RuntimeError('Use the same locked environment as the validated common evaluator')
    settings={key:member['settings'][key] for key in ('image_size','descriptor_dim','descriptor','normalization','amp','flip_tta','batch_size','workers','ranking_chunk_size','device','gallery_protocol','ranking')}
    settings.update(checkpoint_schema='402 original DAC state tensors; three classifier heads and DSA projection retained',thread_environment=THREAD_ENVIRONMENT)
    contract=seal({'schema':SCHEMA,'status':'prepared_waiting_for_training','created_utc':utc(),
        'method':'DAC','result_type':'independent local training, fixed final epoch',
        'source_training_dataset':'University-1652','seeds':list(SEEDS),'task_count':30,
        'sources':source_evidence(),'membership':member,'runtime':runtime,'python':str(args.python.resolve()),
        'training_plans':plans,'training_execution_plan':artifact(args.training_execution_plan),
        'training_execution_package':execution_package_evidence(),'settings':settings,
        'selection_rule':'All registered seeds1/2/3 and their completed one-epoch final checkpoints; no seed or target-test selection',
        'checkpoint_binding':'Future bind stage verifies external process exit, complete epoch evidence and actual checkpoint manifest hashes before freezing all three.'})
    save(output,contract)
    print({'status':contract['status'],'prepared':str(output),'sha256':sha(output),'checkpoints_bound':False})

def completion_and_bindings(prepared,completion_path):
    completion_path=Path(completion_path).resolve()
    require(completion_path==TRAIN_EXECUTION/'runtime/completion_manifest.json','Expected exact DAC v2 terminal manifest')
    completion_before=artifact(completion_path)
    receipt=verify_completed_supervision(prepared,completion_path,completion_before['sha256'])
    state_path=TRAIN_EXECUTION/'runtime/status.json';state_before=artifact(state_path)
    validate_training_completion(load(state_path),prepared)
    seeds=[bind_seed(item) for item in prepared['training_plans']]
    require([row['seed'] for row in receipt['seeds']]==list(SEEDS),'Supervised seed inventory differs')
    for recorded,bound in zip(receipt['seeds'],seeds):
        require(recorded['plan_sha256']==bound['plan']['sha256'] and Path(recorded['output_directory']).resolve()==Path(bound['output_directory']).resolve(),'Supervised seed plan/output differs')
        for name,item in recorded['artifacts']['files'].items():
            require(item==({**bound['training_files'],**bound['checkpoints']})[name],'Supervised artifact differs from actual binding: '+name)
    require(receipt==verify_completed_supervision(prepared,completion_path,completion_before['sha256']),'Completed supervision evidence changed during checkpoint binding')
    verify_artifact(completion_before);verify_artifact(state_before)
    return state_before,completion_before,seeds

def bind(args):
    prepared=read_prepared(args.prepared);output=local_output(args.output)
    if output.exists():raise RuntimeError('A checkpoint binding is immutable')
    latest,completion,seeds=completion_and_bindings(prepared,args.training_completion)
    value=seal({'schema':BINDING_SCHEMA,'status':'all_three_final_checkpoints_bound_not_evaluated','created_utc':utc(),
        'prepared':artifact(args.prepared),'training_status':latest,'training_completion':completion,
        'seeds':seeds,'tensor_load_executed':False,'checkpoint_sha256_source':'Actual completed training files and checkpoint_manifest; not planned/example values'})
    save(output,value)
    save(output.with_name(output.stem+'_release_template.json'),{'schema':RELEASE_SCHEMA,'allow_cuda':False,
        'prepared_sha256':sha(args.prepared),'binding_sha256':sha(output),
        'training_execution_package_sha256':prepared['training_execution_package']['sha256'],
        'training_execution_plan_sha256':prepared['training_execution_plan']['sha256']})
    print({'status':value['status'],'binding':str(output),'sha256':sha(output),'checkpoint_count':3})

def verify_bound(prepared,path):
    binding=load(path);verify_seal(binding)
    if binding.get('schema')!=BINDING_SCHEMA or binding.get('status')!='all_three_final_checkpoints_bound_not_evaluated':raise RuntimeError('Incomplete checkpoint binding')
    verify_artifact(binding['prepared']);verify_artifact(binding['training_status']);verify_artifact(binding['training_completion'])
    if load(binding['prepared']['path'])!=prepared:raise RuntimeError('Binding belongs to another prepared contract')
    latest,completion,seeds=completion_and_bindings(prepared,binding['training_completion']['path'])
    if latest!=binding['training_status'] or completion!=binding['training_completion'] or seeds!=binding['seeds']:raise RuntimeError('Completed training evidence changed since binding')
    return binding

def release_gate(prepared,prepared_path,binding_path,release_path):
    if release_path is None:raise RuntimeError('Exact independent evaluation release is required')
    release=load(release_path)
    expected={'schema':RELEASE_SCHEMA,'allow_cuda':True,'prepared_sha256':sha(prepared_path),
              'binding_sha256':sha(binding_path),'training_execution_package_sha256':prepared['training_execution_package']['sha256'],
              'training_execution_plan_sha256':prepared['training_execution_plan']['sha256']}
    if any(release.get(k)!=v for k,v in expected.items()):raise RuntimeError('Release does not bind this exact complete independent evaluation')
    if 'controller_release' in release:
        verify_artifact(release['controller_release'])
        validate_controller_release(prepared,prepared_path,release['controller_release']['path'])
    verify_execution_package(prepared['training_execution_package'])
    result=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader,nounits'],
        capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30,check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if any('python' in line.lower() for line in result.stdout.splitlines()):raise RuntimeError('Another Python GPU process is active')
    return {'release':artifact(release_path),'checked_utc':utc(),'nvidia_compute_rows':result.stdout.splitlines()}


def validate_controller_release(prepared,prepared_path,release_path):
    """Authorize a fixed future binding policy, never pretend future hashes exist."""
    if release_path is None:raise RuntimeError('A pinned parent controller release is required')
    release=load(release_path)
    expected={'schema':CONTROLLER_RELEASE_SCHEMA,'allow_cuda':True,'prepared_sha256':sha(prepared_path),
              'training_execution_package_sha256':prepared['training_execution_package']['sha256'],
              'training_execution_plan_sha256':prepared['training_execution_plan']['sha256'],
              'binding_policy':BINDING_POLICY,'seeds':list(SEEDS),'task_count':30}
    if any(release.get(k)!=v for k,v in expected.items()):raise RuntimeError('Parent release does not authorize this exact independent evaluation policy')
    return artifact(release_path)


def run(args):
    """One future queued job: validate completion, freeze actual hashes, evaluate."""
    prepared=read_prepared(args.prepared)
    output=local_output(args.output_directory)
    if output.exists():raise RuntimeError('Existing run evidence must be reviewed; no automatic replay or overwrite')
    output.mkdir(parents=True,exist_ok=False)
    state={'schema':SCHEMA,'status':'checking_parent_release','started_utc':utc(),'pid':os.getpid(),
           'prepared':artifact(args.prepared),'command':list(sys.argv)}
    save(output/'status.json',state)
    try:
        controller=validate_controller_release(prepared,args.prepared,args.controller_release)
        state.update(controller_release=controller,status='binding_completed_training');save(output/'status.json',state)
        binding_path=output/'completed_training_binding.json'
        # The sealed six-stage completion API verifies all registered predecessors,
        # actual stage owners and the controller before final weights are bound.
        bind(argparse.Namespace(prepared=args.prepared,training_completion=args.training_completion,output=binding_path))
        verify_artifact(controller)
        validate_controller_release(prepared,args.prepared,args.controller_release)
        release_path=output/'exact_evaluation_release.json'
        release={'schema':RELEASE_SCHEMA,'allow_cuda':True,'prepared_sha256':sha(args.prepared),
                 'binding_sha256':sha(binding_path),'training_execution_package_sha256':prepared['training_execution_package']['sha256'],
                 'training_execution_plan_sha256':prepared['training_execution_plan']['sha256'],
                 'controller_release':controller,'derivation':'Bound only after all declared completed training files and exited owners were verified',
                 'created_utc':utc()}
        save(release_path,release)
        state.update(status='evaluating_all_30',binding=artifact(binding_path),exact_release=artifact(release_path));save(output/'status.json',state)
        result=evaluate(argparse.Namespace(prepared=args.prepared,binding=binding_path,release_file=release_path))
        state.update(status='completed',exit_code=0,finished_utc=utc(),result_directory=str(result),completion=artifact(result/'completion.json'))
        save(output/'status.json',state)
        print(json.dumps({'status':'completed','task_count':30,'run_directory':str(output),'result_directory':str(result)}))
    except BaseException as error:
        state.update(status='failed_or_blocked',exit_code=1,finished_utc=utc(),error=str(error),traceback=traceback.format_exc())
        save(output/'status.json',state);save(output/'failure.json',state);raise

def encode_seed(prepared,binding,inventory,directory,log):
    import cv2
    import numpy as np
    import torch
    import torch.nn.functional as F
    from dac_independent_model import load_complete_final_model
    h=helpers();torch.set_num_threads(1);cv2.setNumThreads(1)
    model,proof,no_network=load_complete_final_model(binding)
    save(directory/'strict_complete_final_load.json',proof)
    model=model.to('cuda:0').eval();transform=h.make_validation_transform();batch_size=prepared['settings']['batch_size']
    features=np.lib.format.open_memmap(directory/'descriptors.npy',mode='w+',dtype=np.float32,shape=(len(inventory),1024))
    torch.backends.cudnn.benchmark=True;torch.backends.cudnn.deterministic=False
    with (directory/'image_content_sha256.jsonl').open('x',encoding='utf-8') as evidence,no_network(),torch.no_grad():
        for start in range(0,len(inventory),batch_size):
            images=[];rows=inventory[start:start+batch_size]
            for row in rows:
                path=h.record_path(row,prepared['membership']['roots']);before=path.stat();raw=path.read_bytes();after=path.stat()
                if (before.st_size,before.st_mtime_ns)!=(row['bytes'],row['mtime_ns']) or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('Image changed before/during decoding')
                image=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
                if image is None:raise RuntimeError('Image decode failed: '+str(path))
                images.append(transform(image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB))['image'])
                evidence.write(json.dumps({'key':row['key'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},ensure_ascii=False)+'\n')
            batch=torch.stack(images).to('cuda:0')
            with torch.autocast('cuda',dtype=torch.float16):
                descriptor=F.normalize(model(batch)[-2],dim=-1)
            values=descriptor.to(torch.float32).cpu().numpy()
            if values.shape!=(len(rows),1024) or not np.isfinite(values).all() or np.max(np.abs(np.linalg.norm(values,axis=1)-1))>2e-3:raise RuntimeError('Invalid independent DAC descriptor')
            features[start:start+len(rows)]=values
            if start==0 or (start//batch_size)%100==0:log(f'seed{binding["seed"]}: encoded {start+len(rows)}/{len(inventory)}')
            del batch,descriptor,values
        evidence.flush();os.fsync(evidence.fileno())
    features.flush();del features,model;torch.cuda.empty_cache()
    save(directory/'runtime_actual.json',{'python':sys.executable,'torch':torch.__version__,'cuda':torch.version.cuda,
        'device':torch.cuda.get_device_name(0),'cuda_initialized':torch.cuda.is_initialized(),'amp':True,
        'thread_environment':{name:os.environ.get(name) for name in THREAD_ENVIRONMENT},
        'torch_cpu_threads':torch.get_num_threads(),'opencv_cpu_threads':cv2.getNumThreads()})

def evaluate(args):
    os.environ.update(THREAD_ENVIRONMENT)
    prepared=read_prepared(args.prepared)
    if Path(sys.executable).resolve()!=Path(prepared['python']).resolve():raise RuntimeError('Use the prepared shared independent environment')
    directory=HERE/'results'/prepared['payload_sha256'][:16]/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory.mkdir(parents=True,exist_ok=False)
    status={'schema':SCHEMA,'status':'checking_prerequisites','started_utc':utc(),'pid':os.getpid(),'prepared':artifact(args.prepared)}
    save(directory/'status.json',status)
    try:
        with helpers().evaluation_lock():
            binding=verify_bound(prepared,args.binding)
            gate=release_gate(prepared,args.prepared,args.binding,args.release_file)
            if helpers().runtime_snapshot(sys.executable)!=prepared['runtime']:raise RuntimeError('Prepared runtime changed')
            inventory=load(prepared['membership']['inventory']['path']);tasks=load(prepared['membership']['tasks']['path'])
            current_inventory,current_tasks=helpers().discover_tasks(prepared['membership']['roots']['university1652'],prepared['membership']['roots']['sues200'])
            if current_inventory!=inventory or current_tasks!=tasks:raise RuntimeError('Complete gallery membership changed')
            del current_inventory,current_tasks
            save(directory/'release_gate.json',gate);save(directory/'bound_checkpoints.json',binding)
            os.environ['CUDA_VISIBLE_DEVICES']='0'
            # First scientific import in this execution path follows every gate.
            import numpy as np
            h=helpers();all_metrics={};records=[h.Record(row['key'],row['label']) for row in inventory]
            with (directory/'run.log').open('x',encoding='utf-8') as stream:
                def log(message):stream.write(utc()+' '+message+'\n');stream.flush();print(message,flush=True)
                for seed_binding in binding['seeds']:
                    seed=seed_binding['seed'];out=directory/f'seed_{seed}';out.mkdir()
                    encode_seed(prepared,seed_binding,inventory,out,log)
                    features=np.load(out/'descriptors.npy',mmap_mode='r',allow_pickle=False)
                    encoded={row['key'].casefold():features[i] for i,row in enumerate(inventory)}
                    arrays_dir=out/'per_query_arrays';arrays_dir.mkdir();metrics={}
                    for item in tasks:
                        task=h.Task(item['name'],tuple(records[i] for i in item['query_indices']),tuple(records[i] for i in item['gallery_indices']))
                        score,arrays=h.rank_with_query_evidence(task,encoded,prepared['settings']['ranking_chunk_size'])
                        kind='independent_training_in_domain' if task.name.startswith('university') else 'university1652_to_sues200_transfer'
                        score.update(method='DAC',seed=seed,result_type='independent local training, fixed final epoch',task_type=kind,
                            source_training_dataset='University-1652',checkpoint_sha256=seed_binding['checkpoints']['weights_end.pth']['sha256'],
                            gallery_protocol='all original identities; no junk removal')
                        path=arrays_dir/(task.name+'_per_query.npz');np.savez_compressed(path,**arrays)
                        save(arrays_dir/(task.name+'_validation.json'),h.validate_query_arrays(path,task,score))
                        metrics[task.name]=score;save(out/'metrics.partial.json',metrics)
                    if len(metrics)!=10:raise RuntimeError('All ten tasks are required for each seed')
                    save(out/'metrics.json',metrics);all_metrics[str(seed)]=metrics;del encoded,features
                if list(all_metrics)!=['1','2','3']:raise RuntimeError('All three registered seeds are required')
            image_hashes=[sha(directory/f'seed_{seed}'/'image_content_sha256.jsonl') for seed in SEEDS]
            require(len(set(image_hashes))==1,'Decoded image content changed across seed evaluations')
            summary={}
            for item in tasks:
                name=item['name'];summary[name]={}
                for metric in ('r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP','rank_precision_mAP','MRR'):
                    values=[all_metrics[str(seed)][name][metric] for seed in SEEDS]
                    summary[name][metric]={'values_by_seed':dict(zip(map(str,SEEDS),values)),'mean':statistics.mean(values),'sample_sd':statistics.stdev(values),'n_seeds':3}
            save(directory/'metrics_all_30.json',all_metrics);save(directory/'three_seed_summary.json',summary)
            with (directory/'metrics_all_30.csv').open('x',encoding='utf-8',newline='') as stream:
                rows=[{'task':task,**score} for scores in all_metrics.values() for task,score in scores.items()]
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            h.verify_inventory(inventory,prepared['membership']['roots']);verify_bound(prepared,args.binding)
            require(prepared['sources']==source_evidence(),'Scientific sources changed during evaluation')
            artifacts={str(p.relative_to(directory)):artifact(p) for p in directory.rglob('*') if p.is_file() and p.name not in ('status.json','completion.json')}
            completion=seal({'schema':SCHEMA,'status':'completed','finished_utc':utc(),'task_count':30,'seeds':list(SEEDS),
                'prepared':artifact(args.prepared),'binding':artifact(args.binding),'artifacts':artifacts,
                'scientific_label':'Three independent University-trained DAC final checkpoints; full-gallery U in-domain and SUES transfer. Mean and sample SD include all registered seeds.'})
            save(directory/'completion.json',completion);save(directory/'status.json',{'status':'completed','completion':artifact(directory/'completion.json')})
        return directory
    except BaseException as error:
        status.update(status='failed_or_blocked',failed_utc=utc(),error=str(error),traceback=traceback.format_exc())
        save(directory/'status.json',status);save(directory/'failure.json',status);raise

def parser():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='stage',required=True)
    prepare_p=sub.add_parser('prepare');prepare_p.add_argument('--training-plan',type=Path,action='append',required=True)
    prepare_p.add_argument('--training-execution-plan',type=Path,required=True)
    prepare_p.add_argument('--training-execution-sha256',required=True)
    prepare_p.add_argument('--training-package-sha256',required=True)
    prepare_p.add_argument('--membership',type=Path,default=DEFAULT_MEMBERSHIP)
    prepare_p.add_argument('--python',type=Path,default=Path(r'C:\项目\.venvs\lgm-camp\Scripts\python.exe'))
    prepare_p.add_argument('--output',type=Path,required=True)
    bind_p=sub.add_parser('bind');bind_p.add_argument('--prepared',type=Path,required=True)
    bind_p.add_argument('--training-completion',type=Path,default=EXECUTION/'dac_training_execution_v2/runtime/completion_manifest.json')
    bind_p.add_argument('--output',type=Path,required=True)
    eval_p=sub.add_parser('evaluate');eval_p.add_argument('--prepared',type=Path,required=True)
    eval_p.add_argument('--binding',type=Path,required=True);eval_p.add_argument('--release-file',type=Path,required=True)
    run_p=sub.add_parser('run');run_p.add_argument('--prepared',type=Path,required=True)
    run_p.add_argument('--training-completion',type=Path,default=EXECUTION/'dac_training_execution_v2/runtime/completion_manifest.json')
    run_p.add_argument('--controller-release',type=Path,required=True);run_p.add_argument('--output-directory',type=Path,required=True)
    return p

if __name__=='__main__':
    args=parser().parse_args();{'prepare':prepare,'bind':bind,'evaluate':evaluate,'run':run}[args.stage](args)
