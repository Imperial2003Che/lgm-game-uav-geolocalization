"""Independent profile -> six fits -> twelve original-task evaluations -> aggregation."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timezone
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import traceback
import matched_runtime as r
import matched_audit as audit


def verify_membership():
    from prepare_matched_view import discover
    _,_,current,_,_=discover()
    if current!=r.read(r.HERE/'path_inventory.json'):raise RuntimeError('Prepared path membership/metadata changed')


def verify_profiles(plan,prepared):
    proofs={}
    for variant in ('visual','full'):
        index=r.read(r.HERE/'resource_profiles'/variant/'accepted.json')
        path=Path(index['proof']['path']);record=r.read(path);r.verify_seal(record)
        if r.artifact(path)!=index['proof'] or record['prepared_sha256']!=r.sha(prepared) or record['status']!='native_resource_profile_passed':raise RuntimeError('Resource measurement absent or stale')
        if (record['variant'],record['native_batch_size'],record['workers'],record['optimizer_updates'])!=(variant,64,8,2):raise RuntimeError('Resource measurement changed native controls')
        proofs[variant]=index
    return proofs


def command_for(spec,mode,output=None):
    api=r.original_api();data=r.dataset_spec()
    if mode=='evaluate':command=api.evaluation_command(r.HERE/'run_matched_child.py',data,spec)
    else:command=api.train_command(r.HERE/'run_matched_child.py',data,spec)
    command[0]=str(r.PYTHON)
    if output is not None:command[command.index('--output-dir')+1]=str(output)
    if mode=='profile':command[command.index('--resume')+1]='none'
    return command


def snapshot_resume(spec,attempt):
    folder=attempt/'resume_backup';folder.mkdir()
    proofs={}
    for path in sorted(spec.run_dir.iterdir()):
        if not path.is_file():continue
        before=r.artifact(path);destination=folder/path.name
        shutil.copy2(path,destination)
        if r.sha(destination)!=before['sha256'] or r.artifact(path)!=before:raise RuntimeError('Run changed while backing up the resumable state')
        proofs[path.name]={'source':before,'backup':r.artifact(destination)}
    r.save(folder/'backup_manifest.json',r.seal({'utc':r.utc(),'id':spec.identifier,'files':proofs}))


def spawn(spec,mode,plan,prepared,release,state,attempt_root,output=None):
    r.validate_prepared(prepared,check_runtime=True)
    gate=r.release_gate(prepared,release)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    attempt=attempt_root/(f'{mode}_{spec.variant}_seed{spec.seed}_{stamp}');attempt.mkdir(parents=True)
    if output is None:output=spec.run_dir if mode=='train' else spec.evaluation_dir
    output=r.inside(output)
    if mode=='train' and output.exists():snapshot_resume(spec,attempt)
    if mode=='evaluate' and output.exists():
        # Preserve all partial output before the original evaluator starts fresh.
        target=r.inside(r.HERE/'retained_partial_evaluations'/f'{spec.variant}_seed{spec.seed}_{stamp}')
        target.parent.mkdir(parents=True,exist_ok=True)
        output.rename(target)
        r.save(attempt/'retained_evaluation.json',{'original':str(output),'retained':str(target)})
    output.mkdir(parents=True,exist_ok=True)
    if mode=='train':
        origin=output/'training_origin.json'
        if origin.exists():audit.origin(spec,prepared)
        else:
            if any(output.iterdir()):raise RuntimeError('Unattributed existing run directory; refusing to train over it')
            r.save(origin,r.seal({'schema':'matched-view-training-origin.v1','prepared_sha256':r.sha(prepared),
                'id':spec.identifier,'run_dir':str(spec.run_dir),'created_utc':r.utc(),'source_family':r.FAMILY}))
    command=command_for(spec,mode,output)
    event={'id':spec.identifier,'mode':mode,'status':'launching','command':command,'output_dir':str(output),
           'attempt_dir':str(attempt),'started_utc':r.utc()}
    state['events'].append(event);state.update(status='running',active=event)
    r.save(r.HERE/'execution_state.json',state)
    lease=r.seal({'schema':'matched-view-child-lease.v1','id':spec.identifier,'seed':spec.seed,'mode':mode,'command':command,
        'output_dir':str(output),'attempt_dir':str(attempt),'prepared':str(prepared),'prepared_sha256':r.sha(prepared),
        'derived_sha256':r.sha(r.DERIVED),'controller_pid':os.getpid(),'controller_started_utc':state['started_utc'],'created_utc':r.utc()})
    lease_path=attempt/'lease.json';r.save(lease_path,lease);r.save(attempt/'release_gate.json',gate)
    environment=r.original_api().base_environment(r.PARENT,spec.seed)
    environment.update(MATCHED_VIEW_LEASE=str(lease_path),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    child=None
    try:
        with (attempt/'stdout.log').open('x',encoding='utf-8') as out,(attempt/'stderr.log').open('x',encoding='utf-8') as err:
            child=subprocess.Popen(command,cwd=r.HERE,env=environment,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
            event.update(pid=child.pid,status='running');r.save(r.HERE/'execution_state.json',state)
            while child.poll() is None:
                state['heartbeat_utc']=r.utc();r.save(r.HERE/'execution_state.json',state);time.sleep(30)
        event.update(status='completed' if child.returncode==0 else 'failed',exit_code=child.returncode,finished_utc=r.utc())
        r.save(attempt/'process_result.json',event);r.save(r.HERE/'execution_state.json',state)
        if child.returncode:raise RuntimeError('Independent child failed; retained logs/backup: '+str(attempt))
        r.validate_prepared(prepared)
        return attempt
    except BaseException:
        if child is not None and child.poll() is None:
            state['surviving_child_pid']=child.pid
            state['recovery_note']='Inspect the surviving child and workers; do not restart until all have exited.'
        raise


def aggregate(plan,prepared):
    rows=[];proofs=[]
    for spec in r.specifications():
        proof,metrics=audit.evaluation_complete(spec,plan,prepared);proofs.append(proof)
        for task,data in metrics.items():rows.append({'variant':spec.variant,'seed':spec.seed,'task':task,
            'training_views':'UAV + satellite','result_source':'independent local 80-epoch training',
            **{name:data[name] for name in ('r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP')}})
    if len(rows)!=12:raise RuntimeError('All twelve checkpoint-task results are required')
    summaries=[]
    for variant in ('visual','full'):
        for task in r.TASKS:
            values=[x for x in rows if x['variant']==variant and x['task']==task]
            if sorted(x['seed'] for x in values)!=[1,2,3]:raise RuntimeError('Missing or duplicate seed')
            row={'variant':variant,'task':task,'n_independent_fits':3}
            for metric in ('r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP'):
                series=[x[metric] for x in values];row[metric+'_mean']=statistics.fmean(series);row[metric+'_sample_sd']=statistics.stdev(series)
            summaries.append(row)
    folder=r.HERE/'aggregate';folder.mkdir(exist_ok=True)
    for name,table in (('per_seed.csv',rows),('mean_sample_sd.csv',summaries)):
        with (folder/name).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    r.save(folder/'completion.json',r.seal({'status':'completed','created_utc':r.utc(),'prepared':r.artifact(prepared),
        'fits':6,'checkpoint_task_evaluations':12,'unit':'fraction','dispersion':'sample standard deviation, ddof=1 over seeds1/2/3',
        'training_views':['UAV','satellite'],'parent_three_view_results_not_overwritten':True,
        'raw_evidence':proofs,'tables':{name:r.artifact(folder/name) for name in ('per_seed.csv','mean_sample_sd.csv')}}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['profile','train','evaluate','aggregate','all'],default='all')
    parser.add_argument('--prepared',type=Path,default=r.HERE/'prepared_manifest.json')
    parser.add_argument('--release-file',type=Path)
    parser.add_argument('--check-plan',action='store_true')
    args=parser.parse_args();prepared=r.inside(args.prepared);plan=r.validate_prepared(prepared,check_runtime=True)
    if args.check_plan:
        print({'status':'valid_preparation_not_executed','fits':6,'checkpoint_task_evaluations':12,'prepared_sha256':r.sha(prepared)});return
    if Path(sys.executable).resolve()!=r.PYTHON.resolve():raise RuntimeError('Use the frozen original baseline interpreter')
    with r.exclusive_lock():
        gate=r.release_gate(prepared,args.release_file)
        old=r.HERE/'execution_state.json'
        if old.exists():
            prior=r.read(old)
            if prior.get('prepared_sha256')!=r.sha(prepared):raise RuntimeError('Another preparation owns this execution state')
            for pid,started in r.recorded_owners(prior):
                if r.alive(pid,started):raise RuntimeError('Prior independent controller/child is still running')
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');root=r.HERE/'attempts'/stamp;root.mkdir(parents=True)
        if old.exists():shutil.copy2(old,root/'previous_execution_state.json')
        state={'schema':'matched-view-run.v1','status':'checking','controller_pid':os.getpid(),'started_utc':r.process_started_utc(os.getpid()),
               'prepared_sha256':r.sha(prepared),'stage':args.stage,'attempt_root':str(root),'events':[]}
        r.save(old,state);r.save(root/'release_gate.json',gate)
        try:
            verify_membership()
            if args.stage in ('profile','all'):
                for variant in ('visual','full'):
                    accepted=r.HERE/'resource_profiles'/variant/'accepted.json'
                    if accepted.exists():
                        record=r.read(accepted);proof=r.read(record['proof']['path']);r.verify_seal(proof)
                        if record['proof']!=r.artifact(record['proof']['path']) or proof['prepared_sha256']!=r.sha(prepared):raise RuntimeError('Existing resource proof changed')
                        continue
                    spec=next(s for s in r.specifications() if s.variant==variant and s.seed==1)
                    output=r.HERE/'resource_profiles'/variant/stamp
                    spawn(spec,'profile',plan,prepared,args.release_file,state,root,output)
                    r.save(accepted,{'proof':r.artifact(output/'resource_profile.json')})
            if args.stage in ('train','all'):
                verify_profiles(plan,prepared)
                for spec in r.specifications():
                    manifest=spec.run_dir/'run_manifest.json'
                    if manifest.exists() and r.read(manifest).get('status')=='completed':
                        audit.train_complete(spec,plan,prepared);continue
                    if spec.run_dir.exists():
                        audit.origin(spec,prepared)
                        if not (spec.run_dir/'last.pt').exists():raise RuntimeError('Prior partial run has no resumable checkpoint; preserve and explicitly review')
                    spawn(spec,'train',plan,prepared,args.release_file,state,root)
                    audit.train_complete(spec,plan,prepared)
            if args.stage in ('evaluate','all'):
                # No official test evaluation until every new fit is complete.
                for spec in r.specifications():audit.train_complete(spec,plan,prepared)
                for spec in r.specifications():
                    manifest=spec.evaluation_dir/'evaluation_manifest.json'
                    if manifest.exists() and r.read(manifest).get('status')=='completed':
                        audit.evaluation_complete(spec,plan,prepared);continue
                    spawn(spec,'evaluate',plan,prepared,args.release_file,state,root)
                    proof,_=audit.evaluation_complete(spec,plan,prepared)
                    r.save(root/(spec.variant+f'_seed{spec.seed}_evaluation_audit.json'),proof)
            if args.stage in ('aggregate','all'):aggregate(plan,prepared)
            state.update(status='completed_requested_stage',finished_utc=r.utc());state.pop('active',None)
        except BaseException as error:
            state.update(status='failed_or_interrupted',failed_utc=r.utc(),error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
            r.save(root/'failure.json',state);raise
        finally:r.save(old,state)


if __name__=='__main__':main()
