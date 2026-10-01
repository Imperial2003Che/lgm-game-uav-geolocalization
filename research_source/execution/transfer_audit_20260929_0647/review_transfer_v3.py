"""Fixed 12-run T3 read-only audit. Stdlib only; no checkpoint bytes or scientific imports."""
from __future__ import annotations
import ast, csv, hashlib, io, json, logging, math, operator, os, re, struct, subprocess, sys, traceback, types, zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

HERE=Path(__file__).parent
EX=HERE.parent
ROOT=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PKG=ROOT/'lgm_game_pytorch'
EV=PKG/'evaluations/transactions_t3_transfer'
OUT=HERE/('attempt_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
OUT.mkdir()
BINDINGS=[]
HASH_QUERIES=[]
def now(): return datetime.now(timezone.utc).isoformat()
def check(value, message):
    if not value: raise AssertionError(message)
def stat(path):
    s=Path(path).stat()
    return dict(bytes=s.st_size,mtime_ns=s.st_mtime_ns,device=s.st_dev,inode=s.st_ino)
def guard(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        check(Path(os.fsdecode(args[0])).suffix.lower() not in ('.pt','.pth','.ckpt'),'Checkpoint byte open forbidden')
sys.addaudithook(guard)
def sha(path):
    path=Path(path)
    check(path.suffix.lower() not in ('.pt','.pth','.ckpt'),'Checkpoint hashing forbidden')
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,data):
    p=OUT/name
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(data)
    return p
def snap(path,name=None,expected=None):
    p=Path(path); before=stat(p); data=p.read_bytes(); digest=hashlib.sha256(data).hexdigest()
    check(expected is None or expected==digest,'SHA mismatch: '+str(p))
    check(before==stat(p),'File changed during snapshot: '+str(p))
    out=save(name or ('b%03d_'%len(BINDINGS)+p.name),data)
    item=dict(path=str(p),snapshot=str(out),bytes=len(data),sha256=digest)
    BINDINGS.append(item)
    return json.loads(data.decode('utf-8-sig')) if p.suffix.lower()=='.json' else data,item
def canon(obj): return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def payload(obj):
    tmp=dict(obj); declared=tmp.pop('payload_sha256');check(canon(tmp)==declared,'Canonical payload mismatch')
def same(a,b): return os.path.samefile(a,b)
def references(obj):
    if isinstance(obj,dict):
        for pathkey,hashkey in (('path','sha256'),('snapshot','sha256'),('audit_path','audit_sha256'),('report_path','report_sha256')):
            if isinstance(obj.get(pathkey),str) and isinstance(obj.get(hashkey),str): yield Path(obj[pathkey]),obj[hashkey]
        for value in obj.values(): yield from references(value)
    elif isinstance(obj,list):
        for value in obj: yield from references(value)

# Minimal typed one-dimensional vector support, restricted to actual non-object NPZ schema.
# This is explicitly a compatibility execution, not the original NumPy runtime.
class Vec:
    def __init__(self,values,kind): self.values=list(values);self.dtype=types.SimpleNamespace(kind=kind);self.ndim=1;self.shape=(len(self.values),)
    def __len__(self): return len(self.values)
    def __iter__(self): return iter(self.values)
    def __getitem__(self,key): return self.values[key]
    def tolist(self): return list(self.values)
    def astype(self,dtype): return NP.asarray(self,dtype)
    def mean(self): return math.fsum(self.values)/len(self.values)
    def any(self): return any(self.values)
    def all(self): return all(self.values)
    def op(self,other,fn,kind):
        if isinstance(other,Vec):
            check(len(self)==len(other),'Vector length mismatch')
            values=[fn(a,b) for a,b in zip(self,other)]
        else: values=[fn(a,other) for a in self]
        return Vec(values,kind)
    def __lt__(self,o): return self.op(o,operator.lt,'b')
    def __le__(self,o): return self.op(o,operator.le,'b')
    def __gt__(self,o): return self.op(o,operator.gt,'b')
    def __ge__(self,o): return self.op(o,operator.ge,'b')
    def __eq__(self,o): return self.op(o,operator.eq,'b')
    def __mul__(self,o): return self.op(o,operator.mul,'f')
    def __rtruediv__(self,o): return Vec([o/v for v in self],'f')
def read_npy(data):
    f=io.BytesIO(data);check(f.read(6)==b'\x93NUMPY','NPY magic')
    v=f.read(2);check(v in (b'\x01\x00',b'\x02\x00'),'NPY version')
    size=struct.unpack('<H' if v[0]==1 else '<I',f.read(2 if v[0]==1 else 4))[0]
    h=ast.literal_eval(f.read(size).decode('latin1').strip())
    check(not h['fortran_order'] and len(h['shape'])==1,'Only non-Fortran vectors accepted')
    n=h['shape'][0];desc=h['descr'];raw=f.read()
    if desc.startswith('<U'):
        width=int(desc[2:])*4; check(len(raw)==n*width,'Text byte size')
        values=[raw[i:i+width].decode('utf-32-le').rstrip('\0') for i in range(0,len(raw),width)];kind='U'
    else:
        formats={'<f4':('f',4,'f'),'<f8':('d',8,'f'),'<i8':('q',8,'i'),'|b1':('?',1,'b')}
        check(desc in formats,'Unsupported/object NPY dtype '+desc)
        fmt,width,kind=formats[desc];check(len(raw)==n*width,'Numeric byte size')
        values=struct.unpack('<'+str(n)+fmt,raw)
    return Vec(values,kind)
class NPZ:
    def __init__(self,path):
        self.z=zipfile.ZipFile(path); names=self.z.namelist()
        check(len(names)==len(set(names)) and all(n.endswith('.npy') and '/' not in n for n in names),'NPZ member names')
        self.files=[n[:-4] for n in names];self.cache={}
    def __enter__(self): return self
    def __exit__(self,*args): self.z.close()
    def __getitem__(self,name):
        if name not in self.cache: self.cache[name]=read_npy(self.z.read(name+'.npy'))
        return self.cache[name]
class NP:
    float64='float64';bool_='bool';int64='int64'
    @staticmethod
    def load(path,allow_pickle=False):
        check(allow_pickle is False,'Pickle forbidden');return NPZ(path)
    @staticmethod
    def asarray(value,dtype=None):
        check(isinstance(value,Vec),'Only typed vectors accepted by compatibility runtime')
        if dtype is None:return value
        converters={NP.float64:(float,'f'),NP.bool_:(bool,'b'),NP.int64:(int,'i'),str:(str,'U')}
        check(dtype in converters,'Unexpected compatibility dtype')
        fn,kind=converters[dtype];converted=[fn(v) for v in value]
        if dtype==NP.int64:check(all(-(2**63)<=v<2**63 for v in converted),'Compatibility int64 overflow rejected')
        return Vec(converted,kind)
    @staticmethod
    def isfinite(a):return Vec([math.isfinite(v) for v in a],'b')
    @staticmethod
    def rint(a):return Vec([round(v) for v in a],'f')
    @staticmethod
    def ones(n,dtype=None):return Vec([1.0]*n,'f')
    @staticmethod
    def allclose(a,b,rtol=1e-5,atol=1e-8):
        check(len(a)==len(b),'allclose length');return all(abs(x-y)<=atol+rtol*abs(y) for x,y in zip(a,b))
    @staticmethod
    def array_equal(a,b):return len(a)==len(b) and all(x==y for x,y in zip(a,b))
    @staticmethod
    def mean(a):return a.mean()

EXTRACTED=[]
SOURCE_BYTES={}
def extract(path,names,env):
    check(str(path) in SOURCE_BYTES,'Original AST source must come from SHA-verified immutable snapshot bytes')
    text=SOURCE_BYTES[str(path)].decode('utf-8');tree=ast.parse(text)
    selected=[]
    for n in tree.body:
        name=getattr(n,'name',None)
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):name=n.targets[0].id
        if name in names:
            selected.append(n);segment=ast.get_source_segment(text,n)
            EXTRACTED.append(dict(path=str(path),name=name,first_line=n.lineno,last_line=n.end_lineno,source_segment_sha256=hashlib.sha256(segment.encode()).hexdigest(),body_changed=False))
    check(len(selected)==len(names),'Requested original definitions missing '+str(names))
    tree=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+selected,type_ignores=[])
    ast.fix_missing_locations(tree)
    exec(compile(tree,str(path),'exec'),env)
    return env

report=dict(schema='bounded-t3-transfer-review-v1',started_utc=now(),source=dict(path=str(Path(__file__)),sha256=sha(__file__)),scope=dict(runs=12,tasks=66),fresh_checkpoint_byte_hashes=0,checkpoint_loaded=False,scientific_entrypoints_executed=False,live_files_modified=False)
try:
    rejected_source=snap(HERE/'review_transfer.py',expected='3ccba056f279227aa0b425d318b77cab23123c92dabea55e4ada7d38ae012645')[1]
    rejected_report=snap(HERE/'attempt_20260929_055612_827811/TRANSFER_REVIEW.json',expected='df43c200e9ec1a364ab2571eae73424b58997a6ac05747c6919feb0d47f5180a')[1]
    report['rejected_candidate_retained']=dict(source=rejected_source,report=rejected_report,reason='Inherited metadata traversal followed a historical rejected same-name report; v2 pins all four accepted review SHAs and adds statically identified missing pure canonical helper. No scientific change.')
    snap(HERE/'V1_TO_V2.patch')
    snap(HERE/'V2_TO_V3.patch')
    snap(HERE/'review_transfer_v2.py',expected='51493d8e86df998581668e8485f7e8c23bfca7c17d469757a0dc4cf385310130')
    report['unexecuted_v2_candidate_retained']=True
    report['v3_static_review_changes']=['Extract only SHA-verified source bytes','Apply original path normalizer and casefold uniqueness','Bind ledger terminal fields to completed event','Fail closed on compatibility int64 overflow']
    matrix_path=PKG/'experiments/run_transactions_t3_transfer_matrix.py'
    adapter_path=PKG/'experiments/run_cross_dataset_evaluation.py'
    core_path=PKG/'lgm_game_pytorch/formal_retrieval.py'
    for p,h in [(matrix_path,'50e681a17bd21188ec059112a77653e04f0cd716a95f4e1c0dfbb486375cc84c'),(adapter_path,'29cccd4ff3e975571b578288f7a691ceccaf4a8ed7ab9483812b68edbc4f5ed8'),(core_path,'081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862')]:SOURCE_BYTES[str(p)]=snap(p,expected=h)[0]
    # Adopted report metadata only: no prior official metrics/arrays/checkpoint bytes re-read.
    eval_start=EX/'evaluation_audits_20260929/ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json'
    training_start=EX/'completion_audits_20260928/ROOT_FIT_42_ADOPTION_20260928.json'
    allowed_eval={'BATCH10_EVALUATION_REVIEW.json':'7dc08f79d974394c95c53fca990fd55b3832981d72bc0d09a2b64b53206988c8','BATCH6_EVALUATION_REVIEW.json':'f2d578c904e14c99b4d5b4a00ace980d3ecca99c5ba43d2ebe6c7b228e98acf1','SUES_BATCH11_EVALUATION_REVIEW.json':'78b187ce0388f5d8d28ebcb7139039059cf897eb574051c38ee50e72a60e6a1a','SUES_BATCH9_EVALUATION_REVIEW.json':'3cb6894e754bf9388519b5886491deca61e807472b7dbde9c2e93dd3ff65c074'}
    q=[(eval_start,'3b2bb1629f5b769fcd956c08068fa8ab2c947c9b36898a4bec2742e21110c17e',None),(training_start,'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87',None)]
    docs={};graph=[];seen=set()
    while q:
        p,h,parent=q.pop(0)
        if str(p) in seen:continue
        seen.add(str(p));obj,b=snap(p,expected=h);docs[p.name]=obj
        graph.append(dict(path=str(p),sha256=h,parent=parent,actual_sha_verified=True))
        for dest,digest in references(obj):
            if dest.suffix=='.json' and ((dest.name in allowed_eval and digest==allowed_eval[dest.name]) or (dest.name.startswith('ROOT_') and 'ADOPTION' in dest.name) or dest.name.startswith('BATCH_COMPLETION')):q.append((dest,digest,str(p)))
    check(set(allowed_eval).issubset(docs),'Missing accepted source audit metadata')
    prior=docs[eval_start.name];check(prior['accepted_total_evaluation_runs']==42 and prior['adopted_with_stated_inheritance_limits'],'Prior primary official adoption')
    root42=docs[training_start.name];check(root42['adopted'] and root42['completed_fit_count']==42,'Training42 adoption')
    ledger_path=EX/'completion_audits_20260922/BATCH_0944_LEDGER_RAW.json';ledger_sha='55e5ffe63d9f4c907076552db832e2b4c0647fa10dadea8bcdaf7668c4be8187'
    check(any(p.name==ledger_path.name and h==ledger_sha for d in docs.values() for p,h in references(d)),'Adopted checkpoint ledger edge missing')
    training_ledger,ledger_binding=snap(ledger_path,expected=ledger_sha)
    source_runs={}
    for name in allowed_eval:
        for r in docs[name]['runs']:
            ident=r['identifier']
            if '/visual/' in ident or '/full/' in ident:
                if ident.startswith('formal_main/'):
                    check(ident not in source_runs,'Duplicate source identifier in adopted review metadata')
                    source_runs[ident]=(r,docs[name],next(e for e in graph if Path(e['path']).name==name))
    check(len(source_runs)==12,'Exactly twelve source checkpoint authorities')
    report['adoption_graph']=graph
    report['inherited_training_checkpoint_ledger']=ledger_binding
    core_env={'__name__':'t3_pure_protocol','Path':Path,'PurePosixPath':PurePosixPath,'dataclass':dataclass,'defaultdict':defaultdict,'hashlib':hashlib,'json':json,'re':re,'LOGGER':logging.getLogger('t3_readonly')}
    # dataclasses resolves postponed annotation module names through sys.modules.
    module=types.ModuleType(core_env['__name__']);sys.modules[core_env['__name__']]=module;module.__dict__.update(core_env);core_env=module.__dict__
    extract(core_path,{'EvidenceRecord','RetrievalTask','SUES_ALTITUDES','SUES_OFFICIAL_TRAIN_IDS','SUES_MANIFEST_SOURCE','canonical_json_bytes','canonical_sha256','normalized_relative_path','slugify','_component_after','derive_record','derive_all_records','_group_by_label','_assert_task','build_official_evaluation_tasks','protocol_membership_hash','parse_sues_manifest','sha256_file'},core_env)
    # All pure protocol file hashes reject checkpoints as a defense in depth.
    core_env['sha256_file']=sha
    core=types.SimpleNamespace(**core_env)
    adapter_env=dict(__name__='t3_adapter_completion_only',Path=Path,hashlib=hashlib,json=json,math=math,csv=csv,core=core,np=NP)
    extract(adapter_path,{'TransferIntegrityError','CONFIG_SCHEMA','METRICS_SCHEMA','MANIFEST_SCHEMA','STATUS_SCHEMA','EXPECTED_TASKS','EXPECTED_CORE_SHA256','EXPECTED_EVIDENCE','EXPECTED_SUES_MANIFEST_SHA256','canonical_sha256','load_json','validate_payload_hash','recompute_metrics_from_arrays','validate_metrics_csv','validate_completed'},adapter_env)
    def tracked_sha(path):
        digest=sha(path);HASH_QUERIES.append(dict(path=str(path),sha256=digest,mode='fresh_non_checkpoint_hash'));return digest
    adapter_env['sha256_file']=tracked_sha
    matrix_env=dict(__name__='t3_matrix_contract_only',Path=Path,hashlib=hashlib,json=json,EXPECTED_TASKS=adapter_env['EXPECTED_TASKS'])
    extract(matrix_path,{'MATRIX_SCHEMA','LEDGER_SCHEMA','AUDIT_SCHEMA','EXPECTED_ROWS','T3IntegrityError','canonical_sha256','load_json','validate_matrix','validate_payload_hash'},matrix_env)
    registration_path=PKG/'experiments/transactions_t3_transfer_matrix.json'
    matrix,matrix_binding=snap(registration_path)
    check(matrix_env['validate_matrix'](registration_path)==matrix,'Original registration validator')
    ledger,t3binding=snap(EV/'transactions_t3_ledger.json','T3_LEDGER.json')
    check(ledger['schema_version']==matrix_env['LEDGER_SCHEMA'] and ledger['status']=='all_evaluations_complete' and ledger['registered_evaluation_count']==12,'T3 ledger terminal header')
    expected_ids=[r['evaluation_id'] for r in matrix['evaluations']]
    check(set(ledger['evaluations'])==set(expected_ids),'Exact preregistered ledger evaluation keys')
    check(len(ledger['invocations'])==1 and ledger['invocations'][0]['stage']=='evaluate' and ledger['invocations'][0]['status']=='completed','Single complete T3 invocation')
    static=ledger['frozen_inputs']['static_audit'];payload(static)
    check(ledger['frozen_inputs']['static_audit_payload_sha256']==static['payload_sha256'],'T3 static audit binding')
    check(static['status']=='ready_for_evaluation' and static['source_gate']['all_source_checkpoints_complete'] and static['source_gate']['registered_source_checkpoint_count']==12,'Original producer primary source gate')
    for pathkey,hashkey in [('matrix_path','matrix_sha256'),('runner_path','runner_sha256'),('adapter_path','adapter_sha256'),('formal_core_path','formal_core_sha256'),('protocol_path','protocol_sha256')]:
        snap(static[pathkey],expected=static[hashkey])
    check(static['matrix_sha256']==matrix_binding['sha256'],'Exact registered matrix bytes')
    pipeline,pipeline_binding=snap(EX/'pipeline_status.json','PIPELINE_STATUS.json')
    stages=[r for r in pipeline['jobs'] if r['id']=='cross_dataset_transfer']
    check(len(stages)==1 and stages[0]['status']=='completed' and stages[0]['exit_code']==0 and stages[0]['pid']==20604,'Original parent T3 stage completion')
    check(stages[0]['entrypoint_sha256']==static['runner_sha256'],'Pipeline T3 source binding')
    report['parent_pipeline_stage']=stages[0]
    report['producer_source_checkpoint_gate_executed_not_independently_repeated']=static['source_gate']
    # Small compatibility controls exercise semantics relied upon by the untouched helper.
    check(NP.rint(Vec([0.5,1.5,2.5,3.5],'f')).tolist()==[0,2,2,4],'ties-to-even')
    check(NP.allclose(Vec([1+1.0e-6],'f'),Vec([1.0],'f'),rtol=1e-6,atol=1e-7),'allclose accepted boundary')
    check(not NP.allclose(Vec([1+1.3e-6],'f'),Vec([1.0],'f'),rtol=1e-6,atol=1e-7),'allclose rejection boundary')
    check(NP.array_equal(Vec([True,False],'b'),Vec([1,2],'i')==1),'correct flags/rank1')
    check(NP.asarray(Vec([True,False,True],'b'),NP.float64).mean()==2/3,'float64 mean compatibility')
    report['compatibility_controls']=dict(passed=5,scientific_runtime_used=False)
    target_tasks={};target_info={};cache_stats={}
    for dataset in ('university1652','sues200'):
        target=static['targets'][dataset];data=Path(target['data_root']);cache=Path(target['evidence_path']);before=stat(cache)
        check(target['evidence_sha256']==adapter_env['EXPECTED_EVIDENCE'][dataset]['sha256'],'Frozen target cache inherited SHA')
        snap(target['evidence_meta_path'],expected=adapter_env['EXPECTED_EVIDENCE'][dataset]['meta_sha256'])
        with NPZ(cache) as z:paths=z['paths'].tolist()
        check(paths==[core.normalized_relative_path(p) for p in paths],'Evidence paths must already equal original normalized form')
        check(len(paths)==len(set(p.casefold() for p in paths)),'Casefold-unique evidence paths')
        records=core.derive_all_records(types.SimpleNamespace(paths=paths),data,dataset)
        train_ids,sues_info=core.parse_sues_manifest(PKG/'manifests/sues200_official_train_ids.yaml' if dataset=='sues200' else None)
        tasks=core.build_official_evaluation_tasks(records,dataset,train_ids)
        check(tuple(t.name for t in tasks)==adapter_env['EXPECTED_TASKS'][dataset],'Original exact target tasks')
        membership=core.protocol_membership_hash(tasks)
        check(membership==target['protocol']['protocol_membership_sha256'],'Derived membership differs from frozen target audit')
        unique={r.relative_path:r.absolute_path for t in tasks for r in (*t.query,*t.gallery)}
        count=len(unique);total=sum(p.stat().st_size for p in unique.values())
        scale={t.name:dict(queries=len(t.query),gallery_images=len(t.gallery),query_identities=len({r.label for r in t.query}),gallery_identities=len({r.label for r in t.gallery})) for t in tasks}
        check(scale==target['protocol']['task_scale'],'Original-derived scale differs from static audit')
        check(before==stat(cache),'Cache metadata changed')
        expected_counts=(146520,137576,8944,93441) if dataset=='university1652' else (40200,40200,0,40200)
        check((len(paths),len(records),len(paths)-len(records),count)==expected_counts,'All records, ignored auxiliary, and evaluation union counts')
        membership_path=save(dataset+'_MEMBERSHIP.json',json.dumps([dict(name=t.name,protocol=t.protocol,query=[r.relative_path for r in t.query],gallery=[r.relative_path for r in t.gallery]) for t in tasks],ensure_ascii=False,indent=1).encode())
        target_tasks[dataset]=tasks;cache_stats[dataset]=(cache,before)
        target_info[dataset]=dict(evidence_rows=len(paths),derived_supported_records=len(records),ignored_auxiliary=len(paths)-len(records),evaluation_unique_files=count,evaluation_unique_bytes=total,membership_sha256=membership,membership_artifact=dict(path=str(membership_path),sha256=sha(membership_path)),task_scale=scale,cache_SHA_inherited=target['evidence_sha256'],cache_stat=before,full_cache_hash_repeated=False,all_image_content_hashes_repeated=False,sues_manifest=sues_info if dataset=='sues200' else None)
    report['target_protocol_membership']=target_info
    results=[];artifact_count=0
    for row in matrix['evaluations']:
        eid=row['evaluation_id'];tag='r%02d'%row['ordinal'];lr=ledger['evaluations'][eid]
        source=row['source_dataset'];target=row['target_dataset'];variant=row['variant'];seed=row['seed']
        check(all(lr[k]==row[k] for k in ('ordinal','source_dataset','target_dataset','variant','seed')),'Registered ledger row fields')
        check(lr['status']=='completed' and lr['attempt']==1 and lr['return_code']==0 and len(lr['events'])==2,'Single successful original T3 attempt')
        start,end=lr['events']
        check(all(lr[k]==end[k] for k in ('status','attempt','return_code','finished_utc','elapsed_seconds','manifest_sha256','checkpoint_sha256','stdout_sha256','stderr_sha256')),'Ledger terminal row differs from original completion event')
        check(start['status']=='running' and end['status']=='completed' and end['return_code']==0 and start['attempt']==end['attempt']==1,'Original subprocess return0 events')
        ev=EV/eid;run=PKG/'runs/formal_main'/source/variant/('seed_'+str(seed));ident=f'formal_main/{source}/{variant}/seed_{seed}/resnet18/dim_512'
        check(ident in root42['completed_fit_ids'],'Unaccepted training identifier')
        accepted,accepted_report,accepted_edge=source_runs[ident];cp=accepted['inherited_checkpoint_SHA'];inherited=training_ledger['runs'][ident]['checkpoint_sha256']
        check(inherited==cp['inherited_sha256']==lr['checkpoint_sha256'],'Original-adopted training ledger/current transfer inherited checkpoint identity')
        before=stat(run/'best.pt');check(before['bytes']==cp['stat_before']['bytes'],'Checkpoint size differs from adopted source metadata')
        originals={}
        for small in ('run_config.json','run_manifest.json'):
            candidates=[b for b in accepted_report['raw_evidence_bindings'] if Path(b['path']).name==small and same(b['path'],run/small)]
            check(candidates and len({b['sha256'] for b in candidates})==1,'Accepted small training artifact binding missing/ambiguous')
            originals[small]=snap(run/small,tag+'/training_'+small,expected=candidates[0]['sha256'])[0]
        train=originals['run_manifest.json'];run_config=originals['run_config.json'];payload(train)
        check(train['status']=='completed' and train['epochs_completed']==80 and train['best_epoch']==79 and train['best_validation_mAP'] is None and train['test_protocol_was_evaluated'] is False,'Original source training manifest conditions')
        check(canon(run_config['immutable_config'])==run_config['run_config_sha256']==train['run_config_sha256'],'Source training config canonical hash')
        check(train['artifacts']['best.pt']['sha256']==train['artifacts']['last.pt']['sha256']==inherited,'Source best/last declared SHA matches exact adopted checkpoint')
        config,config_binding=snap(ev/'transfer_evaluation_config.json',tag+'/config.json')
        manifest,manifest_binding=snap(ev/'transfer_evaluation_manifest.json',tag+'/manifest.json',expected=end['manifest_sha256'])
        status,status_binding=snap(ev/'transfer_evaluation_status.json',tag+'/status.json')
        check(status['schema_version']==adapter_env['STATUS_SCHEMA'] and status['status']=='completed' and status['config_sha256']==config_binding['sha256'] and status['manifest_sha256']==manifest_binding['sha256'] and status['completed_utc']==manifest['completed_utc'],'Transfer completed status exact bindings')
        check(manifest['config_sha256']==config_binding['sha256'] and manifest['checkpoint_sha256']==inherited,'T3 config/checkpoint SHA')
        # Original completed function and both its metric helpers execute unchanged via stdlib facade.
        validated=adapter_env['validate_completed'](ev,config_binding['sha256'],source,target,variant,seed)
        check(validated==manifest,'Original completion function returned different manifest')
        checkpoint=config['checkpoint'];check(same(checkpoint['path'],run/'best.pt') and same(manifest['checkpoint_path'],run/'best.pt'),'Exact samefile checkpoint source')
        check(checkpoint['sha256']==inherited and checkpoint['bytes']==before['bytes'] and checkpoint['selected_training_epoch']==manifest['selected_training_epoch']==79,'T3 checkpoint descriptor/final epoch')
        check(checkpoint['training_run_config_sha256']==run_config['run_config_sha256'] and checkpoint['training_manifest_payload_sha256']==train['payload_sha256'],'T3 source training canonical bindings')
        check(config['design']=='bidirectional_zero_shot_cross_dataset_transfer','Design binding')
        check(config['evaluation']==dict(device='cuda:0',workers=8,eval_batch_size=128,eval_chunk_size=128,data_hash_mode='content',amp=True,all_official_queries=True,all_official_gallery_images=True),'Frozen T3 evaluation settings')
        check(config['frozen_core']['sha256']==static['formal_core_sha256'] and same(config['frozen_core']['path'],core_path),'Core identity')
        check(config['adapter']['sha256']==static['adapter_sha256'] and same(config['adapter']['path'],adapter_path),'Adapter identity')
        targetrow=static['targets'][target];info=target_info[target];cache,cache_before=cache_stats[target]
        check(same(config['target']['data_root'],targetrow['data_root']) and same(config['target']['evidence']['path'],cache),'Target source paths')
        check(config['target']['evidence']['sha256']==manifest['target_evidence_sha256']==targetrow['evidence_sha256'] and config['target']['evidence']['bytes']==cache_before['bytes'],'Exact inherited cache descriptor')
        check(config['target']['evidence']['meta_sha256']==targetrow['evidence_meta_sha256'] and same(config['target']['evidence']['meta_path'],targetrow['evidence_meta_path']),'Evidence meta identity')
        if target=='sues200':
            check(config['target']['sues_manifest']['sha256']==adapter_env['EXPECTED_SUES_MANIFEST_SHA256'] and same(config['target']['sues_manifest']['path'],PKG/'manifests/sues200_official_train_ids.yaml'),'SUES split descriptor')
            check(manifest['sues_manifest']['sha256']==info['sues_manifest']['sha256'] and manifest['sues_manifest']['train_id_count']==120 and manifest['sues_manifest']['test_id_count']==80,'SUES split provenance')
        else:check(config['target']['sues_manifest'] is None and manifest['sues_manifest'] is None,'University has no SUES split')
        check(manifest['target_protocol_membership_sha256']==info['membership_sha256'],'Full derived target membership')
        inventory=manifest['target_image_inventory'];check(inventory['mode']=='content' and inventory['file_count']==info['evaluation_unique_files'] and inventory['total_bytes']==info['evaluation_unique_bytes'],'Target image inventory metadata')
        check(manifest['amp'] is True,'Actual AMP')
        cmd=start['command'];expected=[str(Path(sys.executable).resolve()),'-B',str(adapter_path.resolve()),'--source-dataset',source,'--target-dataset',target,'--variant',variant,'--seed',str(seed),'--checkpoint',str((run/'best.pt').resolve()),'--data-root',str(Path(targetrow['data_root']).resolve()),'--evidence',str(cache.resolve()),'--sues-manifest',str((PKG/'manifests/sues200_official_train_ids.yaml').resolve()),'--output-dir',str(ev.resolve()),'--device','cuda:0','--workers','8','--data-hash-mode','content','--amp','--eval-batch-size','128','--eval-chunk-size','128']
        check(cmd==expected,'Exact original T3 registered command')
        for logkind in ('stdout','stderr'):
            _,binding=snap(start[logkind+'_path'],tag+'/'+logkind+'.log',expected=end[logkind+'_sha256'])
            if logkind=='stderr':check(binding['bytes']==0,'T3 stderr nonempty')
        _,log_binding=snap(ev/'run.log',tag+'/run.log')
        metrics,metrics_binding=snap(ev/'metrics.json',tag+'/metrics.json',expected=manifest['metrics_sha256'])
        _,csv_binding=snap(ev/'metrics.csv',tag+'/metrics.csv',expected=manifest['metrics_csv_sha256'])
        artifact_records=[config_binding,manifest_binding,status_binding,metrics_binding,csv_binding,log_binding]
        taskchecks=[]
        for task in target_tasks[target]:
            name=task.name;declared=manifest['per_query_arrays'][name];path=Path(declared['path'])
            _,array_binding=snap(path,tag+'/'+path.name,expected=declared['sha256']);check(array_binding['bytes']==declared['bytes'],'Declared perquery byte size')
            artifact_records.append(array_binding)
            with NPZ(array_binding['snapshot']) as z:arrays={name:z[name].tolist() for name in z.files}
            qpaths=[r.relative_path for r in task.query];gpaths=[r.relative_path for r in task.gallery];qlabels=[r.label for r in task.query];glabels=[r.label for r in task.gallery]
            check(arrays['query_paths']==qpaths and arrays['query_labels']==qlabels,'Exact original-derived query membership/order/labels')
            idx=arrays['top1_gallery_indices'];check(all(0<=i<len(gpaths) for i in idx),'Gallery index bounds')
            check(arrays['top1_gallery_paths']==[gpaths[i] for i in idx] and arrays['top1_gallery_labels']==[glabels[i] for i in idx],'Top1 full gallery alignment')
            ranks=[int(round(1/v)) for v in arrays['reciprocal_rank']];check(all(1<=r<=len(gpaths) for r in ranks),'RR full gallery bound')
            check(all(v>=0 for v in arrays['margin']),'Nonnegative top1 margin')
            m=metrics['results'][name];expected_scale={**info['task_scale'][name],'protocol':task.protocol}
            check(manifest['target_task_scale'][name]==expected_scale,'Independent full target task scale')
            taskchecks.append(dict(task=name,queries=len(qpaths),gallery=len(gpaths),original_completed_gate_compatibility_passed=True,query_and_top1_mapping_verified=True,stored_AP_RR_and_margin_aggregates_verified=True,full_ranking_and_AP_from_positive_positions_recomputed=False))
        check(len(taskchecks)==row['expected_target_task_count'],'Registered target task count')
        check(before==stat(run/'best.pt') and cache_before==stat(cache),'Source/cache metadata changed during audit')
        artifact_count+=len(artifact_records)
        results.append(dict(evaluation_id=eid,source_training_identifier=ident,original_completed_gate_passed_with_stdlib_compatibility=True,source_adoption_metadata=accepted_edge,inherited_checkpoint_SHA=inherited,checkpoint_stat_only=before,source_training_authority=cp.get('specific_training_authority',{'limitation':'Original first12 inventory whole-file historical SHA edge missing; accepted ROOT42 ID, adopted ledger and accepted official report metadata supply inherited SHA authority.'}),training_ledger_record_status=training_ledger['runs'][ident]['status'],manifest_binding=manifest_binding,artifacts=artifact_records,subprocess_run_return_code=end['return_code'],original_parent_events=lr['events'],tasks=taskchecks,image_content_SHA_inherited_from_actual_T3_producer=inventory['sha256']))
    # Only original recorded stage pair is known here; child subprocess.run records contain no PID.
    ps="$ErrorActionPreference='Stop'; [pscustomobject]@{sampled_utc=[DateTime]::UtcNow.ToString('o'); processes=@(Get-CimInstance Win32_Process -Filter 'ProcessId=20604 OR ProcessId=39488'|Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)}|ConvertTo-Json -Depth 6 -Compress"
    obs=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],capture_output=True,text=True,check=True)
    report['stage_CIM_observation']=json.loads(obs.stdout)
    report['known_stage_pid_numbers']=[20604,39488]
    report['independent_exit_handles_held']=False
    report['individual_child_pid_or_creation_fabricated']=False
    report['source_definitions_extracted_unchanged']=EXTRACTED
    report['AST_definitions_loaded_from_SHA_verified_snapshot_bytes']=True
    report['validator_compatibility_limit']='Original AST function bodies executed unchanged with typed stdlib one-dimensional NPZ/vector facade. This is not a NumPy runtime rerun. Scalar binary64 and math.fsum means checked with original comparison tolerances.'
    report['original_gate_gaps_closed_by_additional_readonly_checks']=['Exact registered ledger keys/row fields/single completed attempt','Specific adopted source checkpoint SHA and source config/manifest linkage','Frozen evaluation parameters/source/evidence descriptors/final epoch','Original pure core protocol membership and full target task scale','Official query order/path-derived labels/full-gallery top1 mapping/RR gallery bound','Declared NPZ byte sizes']
    report['limits']=['No checkpoint bytes loaded or rehashed; historical inherited SHA plus stable stat does not prove current bytes.','University visual sources retain original first12 inventory historical whole-file SHA edge gap; no new historical provenance invented.','Original source checkpoint loading/full-state inspection and producer source gate were not independently re-executed.','Full cache and image-content SHA inherited; actual metadata and memberships checked, not full cache/image-content rehash.','Stored AP/RR/margin aggregation checked; no model inference/full ranking/AP recomputation from all positive ranks.','Original subprocess.run child return0 and parent pipeline Popen exit0 plus current stage PID observation; no independent launcher/interpreter exit handles.','Actual NumPy runtime not imported; original completion functions ran in bounded stdlib compatibility environment.']
    report.update(runs=results,accepted_transfer_runs=len(results),accepted_transfer_tasks=sum(len(r['tasks']) for r in results),new_evaluation_artifact_count=artifact_count,original_hash_queries=HASH_QUERIES,checkpoint_hash_queries=0,scientific_modules=[n for n in sys.modules if n.split('.')[0] in ('torch','numpy','PIL','torchvision','scipy','matplotlib')])
    check(report['accepted_transfer_runs']==12 and report['accepted_transfer_tasks']==66 and not report['scientific_modules'],'Final bounded scope/import checks')
    report['passed_with_stated_limits']=True
except Exception as exc:
    report.update(passed_with_stated_limits=False,error=repr(exc),traceback=traceback.format_exc())
finally:
    report['finished_utc']=now();report['raw_evidence_bindings']=BINDINGS
    rp=save('TRANSFER_REVIEW.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
    meta=dict(schema='sealed-t3-readonly-review-v1',created_utc=now(),source=report['source'],report=dict(path=str(rp),sha256=sha(rp)),files=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in OUT.rglob('*') if p.is_file()])
    mp=save('METADATA.json',json.dumps(meta,ensure_ascii=False,indent=2).encode())
    print(json.dumps(dict(report=str(rp),report_sha256=sha(rp),metadata=str(mp),metadata_sha256=sha(mp),passed=report.get('passed_with_stated_limits'),error=report.get('error')),ensure_ascii=True))
sys.exit(0 if report.get('passed_with_stated_limits') else 1)
