"""Read-only CPU proof for the preserved University ResNet50 seed-1 epoch 75 after host interruption.

Uses the original frozen model/optimizer/scheduler/checkpoint reader on CPU.
Never calls run_train, saves state, starts a controller, or initializes CUDA.
The report proves a complete partial checkpoint, not a completed 80-epoch fit.
"""
import datetime
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
PATH_SHA = '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1'
CAPTURE_SHA = 'b572bb641a696ae216c52563f3e65e92004bc23576c331f14a0b6b1585bd69e0'
BASELINE = Path(r'C:\项目\.venvs\lgm-baselines\Scripts\python.exe')
REPORT = HERE/'CHECKPOINT_RECOVERY_PROOF.json'
DERIVED_SOURCE = EXECUTION/'resource_incident_20260922_0945/review_checkpoint_recovery.py'
DERIVED_SHA = '7629801d90f4fe50cfa0486f0040feb62cdefe06c24da8ca1db636c670b591fe'

def check(value, message):
    if not value:
        raise RuntimeError(message)

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def record(path):
    path = Path(path)
    return {'path':str(path), 'bytes':path.stat().st_size, 'sha256':sha(path)}

def owner_resource():
    ps = r"""$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$rows=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^python(w)?\.exe$'} | Select-Object ProcessId,ParentProcessId,Name,@{n='CreationDate';e={$_.CreationDate.ToString('o')}},CommandLine)
$m=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
[ordered]@{time=(Get-Date).ToString('o');python_processes=$rows;last_boot_utc=$boot;memory=[ordered]@{AvailableBytes=$m.AvailableBytes;CommittedBytes=$m.CommittedBytes;CommitLimit=$m.CommitLimit}} | ConvertTo-Json -Depth 6 -Compress
"""
    raw = subprocess.check_output(['powershell.exe','-NoProfile','-Command',ps],encoding='utf-8',errors='strict')
    result = json.loads(raw)
    own_ids = {os.getpid(),os.getppid()}
    others = [p for p in result['python_processes'] if p['ProcessId'] not in own_ids]
    check(not others, 'Another Python process exists; CPU audit must not overlap science')
    check(all(str(Path(__file__)) in p['CommandLine'] for p in result['python_processes']), 'Unidentified audit ancestor')
    m = result['memory']
    check(all(isinstance(m[k],int) and m[k]>0 for k in ('AvailableBytes','CommittedBytes','CommitLimit')), 'Memory counters invalid')
    headroom = m['CommitLimit']-m['CommittedBytes']
    check(headroom >= 26*1024**3 and m['AvailableBytes'] >= 2*1024**3, 'Insufficient CPU audit resources')
    result.update(commit_headroom_GiB=headroom/1024**3, no_other_python_owners=True,
                  audit_process_ids=sorted(own_ids),scope='Immediate CPU audit admission only; not a training launch gate or stability guarantee.')
    return result

def load_module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def main():
    check(not REPORT.exists(), 'Never overwrite an existing proof')
    check(Path(sys.executable).samefile(BASELINE), 'Wrong interpreter')
    before = owner_resource()
    check(sha(HERE/'CAPTURE.json') == CAPTURE_SHA, 'Sealed capture changed')
    capture = read(HERE/'CAPTURE.json')
    check(sha(DERIVED_SOURCE)==DERIVED_SHA, 'Original reviewed audit source changed')
    check(capture['schema']=='host-interruption-preservation.v1' and len(capture['files'])==35, 'Wrong capture schema or file count')
    check(capture['old_science_and_controllers_absent'] is True and capture['actual_python_processes']==[], 'Captured old owners were not absent')
    check(capture['history_count']==75 and capture['history_last']['epoch']==74, 'Wrong captured partial progress')
    boot=datetime.datetime.fromisoformat(capture['last_boot_utc'])
    check(datetime.datetime.fromisoformat(before['last_boot_utc'])==boot, 'Host boot changed since capture')
    capture_rows = {Path(row['backup']).name:row for row in capture['files'] if Path(row['backup']).parent.name=='active_run'}
    checked_archives=[]
    for row in capture['files']:
        actual=record(row['backup'])
        check(actual['bytes']==row['bytes'] and actual['sha256']==row['sha256'], 'Sealed artifact changed: '+row['backup'])
        checked_archives.append(actual)
    check(len(capture_rows)==8, 'Expected eight sealed active-run files')
    live_records=[]
    for row in capture['files']:
        if Path(row['backup']).parent.name not in ('active_run','ledger'):
            continue
        actual=record(row['path'])
        check(actual['bytes']==row['bytes'] and actual['sha256']==row['sha256'], 'Live stopped run/ledger changed: '+row['path'])
        live_records.append(actual)
    ledger_path=HERE/'ledger/frozen_formal_matrix_ledger.json'
    ledger=read(ledger_path)
    parent=read(HERE/'states/status.json')
    active=parent['active']
    for key,value in capture['active'].items():
        if key in ('started_utc','finished_utc'):
            check(datetime.datetime.fromisoformat(value)==datetime.datetime.fromisoformat(active[key]), 'Capture event timestamp instant mismatch')
        else:
            check(value==active[key], 'Capture event field mismatch: '+key)
    check(active['status']=='running' and active['pid']==27308 and 'exit_code' not in active and 'finished_utc' not in active, 'Unexpected interrupted launcher event')
    check(any(e==active for e in parent['events']), 'Capture event not present in original parent history')
    check(parent['status']=='running' and parent['controller_pid']==31792, 'Wrong stale original parent')
    check(capture['primary_status']=='running' and datetime.datetime.fromisoformat(capture['primary_heartbeat'])==datetime.datetime.fromisoformat(parent['heartbeat_utc']), 'Capture heartbeat differs from sealed parent')
    check(datetime.datetime.fromisoformat(parent['heartbeat_utc']) < boot < datetime.datetime.fromisoformat(capture['time']), 'Host boot does not postdate the interrupted owner heartbeat')
    previous_identity=read(HERE/'previous_identity/LIVE_SNAPSHOT_20260922_152741.json')
    expected_ids={31792,8124,45592,44300,43076,35716,45980,2036,33528,35608,27308,12096}
    old_owners=[r for r in previous_identity['actual_python_processes'] if r['ProcessId'] in expected_ids]
    check({r['ProcessId'] for r in old_owners}==expected_ids and all(datetime.datetime.fromisoformat(r['creation']) < boot for r in old_owners), 'Old owner identity or boot ordering mismatch')
    check(previous_identity['active']['command']==active['command'], 'Interrupted science command differs from last live observation')
    stderr_record=record(HERE/'active_run/process_stderr.log')
    check(stderr_record['bytes']==3518 and stderr_record['sha256']=='111d8b82a03878991ebcc22639d1fd7bad0a5039fb55639413aa188568cb7934', 'Historical stderr changed; investigate before recovery')
    # The old Win1455 content is unchanged; this audit assigns no new failure cause or exit code.
    sys.path.insert(0,str(EXECUTION/'primary_path_repair_20260918'))
    from project_paths import FrozenProjectPath
    from source_contract import verify
    provenance=verify(PATH_SHA)
    root=FrozenProjectPath(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
    sources={
        'runner_sha256':(root/'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py','f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f'),
        'formal_script_sha256':(root/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py','081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'),
        'protocol_sha256':(root/'FORMAL_EXPERIMENT_PROTOCOL.md','29c0502b07f09d45c6fd7d4a5b582fdd9a443acc9e8b818cd9941c18a0ee34f9'),
    }
    source_records={}
    for key,(path,pin) in sources.items():
        row=record(path)
        check(row['sha256']==pin==ledger[key], 'Frozen source changed: '+key)
        source_records[key]=row
    runner=load_module('checkpoint_audit_original_runner',sources['runner_sha256'][0])
    runner.Path=FrozenProjectPath
    datasets=runner.dataset_specs(root,FrozenProjectPath(r'C:\项目\IMTMN\datasets\University-1652'),FrozenProjectPath(r'C:\项目\IMTMN\datasets\SUES-200'))
    specs=runner.main_run_specs(root,runner.DATASETS,runner.MAIN_VARIANTS,runner.MAIN_SEEDS)+runner.sensitivity_run_specs(root,runner.DATASETS)
    check(len(specs)==42, 'Wrong frozen spec count')
    registry=runner.registry_sha256(specs)
    check(registry==ledger['registered_registry_sha256'], 'Frozen registry mismatch')
    frozen_inputs={name:{'data_root':str(d.data_root),'evidence_path':str(d.evidence),'evidence_sha256':d.evidence_sha256} for name,d in datasets.items()}
    check(frozen_inputs==ledger['frozen_inputs'], 'Frozen inputs mismatch')
    target=[s for s in specs if s.identifier=='formal_sensitivity/university1652/full/seed_1/resnet50/dim_512']
    check(len(target)==1, 'Wrong target registry')
    target=target[0]
    check(str(target.run_dir)==active['output_dir'], 'Wrong target output directory')
    config=read(HERE/'active_run/run_config.json')
    immutable=config['immutable_config']
    manifest=read(HERE/'active_run/run_manifest.json')
    history=read(HERE/'active_run/history.json')
    config_sha=runner.canonical_sha256(immutable)
    check(config_sha==config['run_config_sha256']==manifest['run_config_sha256'], 'Immutable hash mismatch')
    payload=dict(manifest)
    check(payload.pop('payload_sha256')==runner.canonical_sha256(payload), 'Running manifest canonical hash mismatch')
    check(manifest['status']=='running' and manifest['last_completed_epoch']==74 and manifest['history_rows']==75, 'Wrong preserved progress')
    check(manifest['best_epoch']==74 and manifest['best_validation_mAP'] is None, 'Unexpected checkpoint selection')
    check(len(history)==75 and [r['epoch'] for r in history]==list(range(75)), 'History not continuous through epoch74')
    optimization=immutable['optimization']
    expected_optimization={'epochs':80,'learning_rate':0.0003,'backbone_lr_multiplier':0.1,'weight_decay':0.0001,'warmup_epochs':5,'gradient_clip_norm':5.0,'identities_per_batch':16,'instances_per_identity':4,'samples_per_class_per_epoch':0,'steps_per_epoch_requested':0,'steps_per_epoch_actual':652,'sampler_schedule_audited_epochs':80,'sampler_step_count_fixed_across_epochs':True,'amp':True}
    check(all(optimization[k]==v for k,v in expected_optimization.items()), 'Frozen optimization mismatch')
    check(optimization['sampler_step_count_schedule_sha256']==runner.canonical_sha256([652]*80), 'Sampler schedule hash mismatch')
    check(all(r['optimizer_steps']==652 and r['validation_selection_mAP'] is None and r['validation']=={} and r['examples_seen']==652*64 for r in history), 'History steps/examples/no-test contract mismatch')
    check(immutable['schema_version']=='formal-retrieval-v1' and immutable['command']=='train' and immutable['dataset']==target.dataset and immutable['seed']==target.seed, 'Wrong immutable identity')
    check(immutable['code_sha256']==sources['formal_script_sha256'][1], 'Wrong embedded source SHA')
    check(immutable['validation_ids']==[] and immutable['protocol']['holdout_fraction']==0 and immutable['protocol']['official_test_images_used_by_train_or_validation']==0 and immutable['selection']['patience']==0, 'Wrong training protocol')
    check(len(immutable['evidence_caches'])==1 and immutable['evidence_caches'][0]['sha256']==datasets[target.dataset].evidence_sha256, 'Evidence source differs')
    check(FrozenProjectPath(immutable['evidence_caches'][0]['path']).resolve()==datasets[target.dataset].evidence and FrozenProjectPath(immutable['data_root']).resolve()==datasets[target.dataset].data_root, 'Frozen input paths differ')
    fingerprint_payload={
        'dataset':target.dataset,'data_root':immutable['data_root'],'image_inventory':immutable['image_inventory'],
        'train_ids_sha256':runner.canonical_sha256(immutable['train_ids']),'sues_manifest':immutable.get('sues_manifest'),'evidence_caches':immutable['evidence_caches'],
    }
    fingerprint_sha=runner.canonical_sha256(fingerprint_payload)
    check(fingerprint_sha==ledger['dataset_fingerprints'][target.dataset]['sha256'], 'Pinned dataset fingerprint mismatch')
    completion_issues=runner.training_completion_issues(target,datasets[target.dataset],sources['formal_script_sha256'][1])
    check(completion_issues==["manifest status is 'running'"], 'Unexpected original completion gate response')
    # This command constructor applies equally to main and sensitivity RunSpec.
    resume_command=runner.train_command(sources['formal_script_sha256'][0],datasets[target.dataset],target)
    check(resume_command[-2:]==['--resume','last'], 'Original runner did not select last checkpoint')
    expected_original=active['command'][4:]
    check(expected_original[0]=='train', 'Unexpected preserved command')
    check(expected_original[-2:]==['--resume','last'], 'Preserved active command was not resume last')
    check(resume_command[2:]==expected_original, 'Resume command changed a frozen science argument')
    versions={key:importlib.metadata.version(key) for key in ('torch','torchvision','numpy','Pillow')}
    check(versions==config['environment']['packages'], 'Baseline package versions changed')
    check(sys.version==config['environment']['python'], 'Baseline Python version changed')
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[key]='1'
    # Necessary trusted-checkpoint CPU subprocess, after no-owner/resource gate.
    core=load_module('checkpoint_audit_original_core',sources['formal_script_sha256'][0])
    core.Path=FrozenProjectPath
    torch=core.torch
    torch.set_num_threads(1)
    check(not torch.cuda.is_initialized(), 'CUDA initialized before CPU audit')
    args=core.build_parser().parse_args(resume_command[2:])
    core.validate_cli(args)
    check(core.args_to_json(args)==dict(config['cli'],resume='last'), 'Original parser changed preserved CLI')
    resolved=core.resolve_resume(target.run_dir,args.resume)
    check(resolved.samefile(target.run_dir/'last.pt'), 'Original resume resolved wrong artifact')
    model_config=immutable['model']
    check(all(model_config[k]==v for k,v in {'variant':target.variant,'backbone':target.backbone,'embed_dim':target.embed_dim,'dropout':0.2,'image_size':224,'resize_size':256}.items()), 'Frozen model config mismatch')
    check(core.pretrained_weight_record(args.backbone,True)==model_config['pretrained_initialization'], 'Original immutable pretrained record changed')
    reports=[]
    for name in ('last.pt','best.pt'):
        row=capture_rows[name]
        reports.append({'file':row['backup'],'live_file':row['path'],'sha256':row['sha256'],'bytes':row['bytes'],'epoch_zero_based':74,'completed_epochs':75,'config_sha256':config_sha})
    check(reports[0]['sha256']==reports[1]['sha256'] and reports[0]['bytes']==reports[1]['bytes'], 'Expected equal final-epoch partial artifacts')
    checkpoint=Path(reports[0]['file'])
    with zipfile.ZipFile(checkpoint) as archive:
        check(archive.testzip() is None, 'Checkpoint archive CRC failed')
    state=core.load_torch_checkpoint(checkpoint,'cpu')
    required={'schema_version','model_state','optimizer_state','scheduler_state','scaler_state','rng_state','immutable_config','run_config_sha256','model_config','evidence_schema','history','epoch','best_validation_mAP','best_epoch','epochs_without_improvement'}
    check(required<=state.keys(), 'Checkpoint resume fields missing')
    check(state['schema_version']==core.SCHEMA_VERSION and state['epoch']==74 and state['history']==history, 'Checkpoint epoch/history mismatch')
    check(state['immutable_config']==immutable and state['run_config_sha256']==config_sha and state['model_config']==model_config and state['evidence_schema']==immutable['evidence_schema'], 'Checkpoint metadata mismatch')
    check(state['best_epoch']==74 and state['epochs_without_improvement']==0 and state['best_validation_mAP']==0.0, 'Checkpoint selection state mismatch')
    counts={'tensors':0,'floating_tensors':0}
    def finite(value):
        if isinstance(value,torch.Tensor):
            check(value.device.type=='cpu', 'A checkpoint tensor is not on CPU')
            counts['tensors']+=1
            if value.is_floating_point():
                check(bool(torch.isfinite(value).all()), 'Nonfinite checkpoint tensor')
                counts['floating_tensors']+=1
        elif isinstance(value,dict):
            for v in value.values(): finite(v)
        elif isinstance(value,(tuple,list)):
            for v in value: finite(v)
        elif isinstance(value,float):
            check(math.isfinite(value), 'Nonfinite optimizer/scheduler/scaler value')
    for field in ('model_state','optimizer_state','scheduler_state','scaler_state'): finite(state[field])
    model=core.FormalRetrievalModel(variant=args.variant,backbone=args.backbone,embed_dim=args.embed_dim,dropout=args.dropout,pretrained=False)
    incompatible=model.load_state_dict(state['model_state'],strict=True)
    check(not incompatible.missing_keys and not incompatible.unexpected_keys, 'Strict original model load failed')
    optimizer=core.optimizer_for_model(model,args.learning_rate,args.backbone_lr_multiplier,args.weight_decay)
    scheduler=core.cosine_warmup_scheduler(optimizer,652*80,652*5)
    optimizer.load_state_dict(state['optimizer_state'])
    scheduler.load_state_dict(state['scheduler_state'])
    # Original scaler object loads the serialized state without scale/update or CUDA allocation.
    scaler=core.make_grad_scaler(True)
    check(scaler.is_enabled(), 'Original CUDA AMP scaler unavailable for state-only load')
    scaler.load_state_dict(state['scaler_state'])
    check(scaler.state_dict()==state['scaler_state'] and bool(state['scaler_state']), 'Scaler restore changed state')
    parameter_count=sum(len(g['params']) for g in optimizer.param_groups)
    check(len(optimizer.state)==parameter_count>0, 'Optimizer state coverage incomplete')
    optimizer_steps=[]
    for parameter,row in optimizer.state.items():
        check(set(row)=={'step','exp_avg','exp_avg_sq'}, 'Unexpected AdamW parameter state')
        check(row['exp_avg'].shape==row['exp_avg_sq'].shape==parameter.shape, 'AdamW moments do not match parameter shape')
        step=float(row['step'].item())
        check(step.is_integer() and 0<step<=75*652, 'Invalid AdamW update counter')
        optimizer_steps.append(int(step))
    check(len(set(optimizer_steps))==1, 'Inconsistent AdamW update counts')
    scheduled_steps=75*652
    check(state['scheduler_state']['last_epoch']==scheduled_steps and state['scheduler_state']['_step_count']==scheduled_steps+1, 'Wrong scheduler position')
    check(scheduler.state_dict()==state['scheduler_state'], 'Original scheduler state restore mismatch')
    expected_factor=scheduler.lr_lambdas[0](scheduled_steps)
    expected_lrs=[base*expected_factor for base in scheduler.base_lrs]
    check(all(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-15) for a,b in zip(expected_lrs,history[-1]['learning_rates'])), 'Frozen schedule learning rates differ')
    check(scheduler.get_last_lr()==history[-1]['learning_rates']==[g['lr'] for g in optimizer.param_groups], 'Loaded optimizer/scheduler/history LR mismatch')
    rng=state['rng_state']
    check(set(rng)=={'python','numpy','torch_cpu','torch_cuda'}, 'RNG fields incomplete')
    random.Random().setstate(rng['python'])
    core.np.random.RandomState().set_state(rng['numpy'])
    torch.Generator(device='cpu').set_state(rng['torch_cpu'])
    check(rng['torch_cpu'].dtype==torch.uint8 and rng['torch_cpu'].ndim==1, 'CPU RNG serialization invalid')
    check(len(rng['torch_cuda'])==1 and all(x.device.type=='cpu' and x.dtype==torch.uint8 and x.ndim==1 and x.numel()>0 for x in rng['torch_cuda']), 'CUDA RNG byte state missing/invalid')
    check(not torch.cuda.is_initialized(), 'CPU audit initialized CUDA')
    after=owner_resource()
    check(datetime.datetime.fromisoformat(after['last_boot_utc'])==boot, 'Host boot changed during audit')
    # Bind sealed and live bytes; no science writer was allowed throughout this probe.
    for row in live_records:
        check(record(row['path'])==row, 'Stopped run or ledger changed during audit')
    check(sha(HERE/'CAPTURE.json')==CAPTURE_SHA, 'Capture changed during audit')
    report={
        'schema':'host-interruption-checkpoint-recovery-proof.v1','passed':True,'status':'verified_complete_epoch_75',
        'checked_utc':now(),'executable':sys.executable,'versions':versions,'cuda_initialized':False,
        'run_id':target.identifier,'completed_epochs':75,'epoch_zero_based':74,'resume_start_epoch':75,'target_epochs':80,
        'capture':record(HERE/'CAPTURE.json'),'script':record(__file__),'derived_from_source':record(DERIVED_SOURCE),'source_contract':provenance,'frozen_sources':source_records,
        'registry_sha256':registry,'frozen_spec_count':42,'frozen_inputs':frozen_inputs,'ledger':record(ledger_path),
        'dataset_fingerprint_sha256':fingerprint_sha,'run_config_sha256':config_sha,'reports':reports,
        'owner_resource_before':before,'owner_resource_after':after,'archived_artifacts_verified':checked_archives,'live_run_and_ledger_verified':live_records,
        'checkpoint_checks':{'all_required_fields':True,'full_archive_crc':True,'two_artifacts_identical_bytes':True,'loaded_artifact':str(checkpoint),
            'second_artifact_validation':'Full independent SHA/size equals loaded artifact; identical bytes share the same CPU state proof.',
            'strict_original_model_load':True,'model_state_tensors':len(state['model_state']),'finite_counts':counts,
            'original_optimizer_load':True,'optimizer_parameter_states':len(optimizer.state),'optimizer_update_count':optimizer_steps[0],
            'original_scheduler_load':True,'scheduler_steps':scheduled_steps,'scheduler_state':state['scheduler_state'],
            'original_amp_scaler_state_load':True,'scaler_state':state['scaler_state'],
            'python_numpy_cpu_rng_state_settable':True,'cuda_rng_state_count':len(rng['torch_cuda']),
            'cuda_rng_state_bytes':[x.numel() for x in rng['torch_cuda']],
            'cuda_rng_restored_on_hardware':False},
        'resume_interface':{'applicable':True,'requested':'last','resolved_path':str(resolved),'original_runner_command':resume_command,
            'original_core_resolve_resume':True,'original_parser_config_equal_except_resume':True,
            'original_core_state_load_methods_validated_on_cpu':True,
            'scope':'Sensitivity RunSpec uses the same original train_command and run_train checkpoint interface. Strict original ResNet50/full model and optimizer/scheduler/scaler restore validated on CPU; no training invoked.'},
        'original_completion_issues':completion_issues,'fit_complete':False,'new_completed_fit_count':0,
        'exit_evidence':{'parent_event':active,'source':str(HERE/'states/status.json'),
            'type':'Host boot after last owner heartbeat; old running/waiting state is stale; all old Python processes absent at capture and CPU audit admission',
            'last_boot_utc':capture['last_boot_utc'],'old_owner_identities':old_owners,'launcher_exit_code_observed':False,
            'independent_windows_process_handles_held':False,'interpreter_exit_code_observed':False},
        'interruption_evidence':{'classification':'host_interruption','cause_not_inferred':True,
            'stale_primary_status':parent['status'],'stale_primary_heartbeat_utc':parent['heartbeat_utc'],
            'last_boot_utc':capture['last_boot_utc'],'old_stderr':stderr_record,
            'historical_win1455_unchanged':True,'new_win1455_claimed':False,'actual_old_exit_codes_known':False},
        'limitations':['No GPU forward/backward or CUDA RNG hardware restore was executed.',
            'No full image-dataset rehash: original immutable inventory and train-ID/evidence fingerprint match the frozen ledger; the original training entrypoint retains its full inventory checks.',
            'Checkpoint proof is not a restart authorization or resource stability guarantee. Root must verify all owners absent and its multi-sample admission gate immediately before any new recovery.',
            '75 complete epochs do not constitute a completed 80-epoch fit or any formal retrieval evaluation.'],
    }
    with REPORT.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    print(json.dumps({'passed':True,'report':str(REPORT),'sha256':sha(REPORT),'script_sha256':sha(__file__),'epoch':74,'completed_epochs':75,'cuda_initialized':False,'optimizer_update_count':optimizer_steps[0]},ensure_ascii=False))

if __name__=='__main__':
    main()
