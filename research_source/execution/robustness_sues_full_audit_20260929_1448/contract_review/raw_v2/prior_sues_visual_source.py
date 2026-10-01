"""Bounded read-only review of SUES visual seed1 robustness. Stdlib only."""
from __future__ import annotations
import ast, csv, hashlib, io, json, logging, math, os, re, struct, subprocess, sys, traceback, types, zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

HERE=Path(__file__).parent
EX=HERE.parent
PKG=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch')
DATA=Path(r'C:\项目\IMTMN\datasets\SUES-200')
RUN=PKG/'runs/formal_robustness/sues200/visual/seed_1'
OUT=HERE/'a1'
OUT.mkdir()
TREE=OUT/'r'
BINDINGS=[]
SOURCE_BYTES={}
EXTRACTED=[]
HASH_QUERIES=[]
CHECKS=defaultdict(int)

def check(value,message):
    CHECKS['assertions']+=1
    if not value: raise AssertionError(message)
def now():return datetime.now(timezone.utc).isoformat()
def norm(path):return os.path.normcase(str(Path(path).resolve()))
def audit_guard(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])); low=str(p).replace('\\','/').lower()
        check(p.suffix.lower() not in ('.pt','.pth','.ckpt'),'Checkpoint byte open prohibited')
        check(not ('/evidence_cache/' in low and p.suffix.lower()=='.npz'),'Evidence cache open prohibited')
        check(not low.startswith(str(DATA).replace('\\','/').lower()+'/'),'Image byte open prohibited')
sys.addaudithook(audit_guard)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def save(name,data):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:stream.write(data)
    return p
def snap(path,name=None,expected=None,size=None):
    path=Path(path); before=path.stat();data=path.read_bytes();after=path.stat();digest=hashlib.sha256(data).hexdigest()
    check((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Input changed during read '+str(path))
    check(expected is None or digest==expected,'SHA mismatch '+str(path))
    check(size is None or len(data)==size,'Size mismatch '+str(path))
    dest=save(name or f'b{len(BINDINGS):03d}_{path.name}',data)
    item=dict(path=str(path),snapshot=str(dest),sha256=digest,bytes=len(data));BINDINGS.append(item)
    return (json.loads(data.decode('utf-8-sig')) if path.suffix.lower()=='.json' else data),item
def extract(path,names,env):
    text=SOURCE_BYTES[str(path)].decode('utf-8-sig');tree=ast.parse(text);selected=[]
    for node in tree.body:
        name=getattr(node,'name',None)
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):name=node.targets[0].id
        if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name):name=node.target.id
        if name in names:
            selected.append(node); segment=ast.get_source_segment(text,node)
            EXTRACTED.append(dict(source_path=str(path),name=name,first_line=node.lineno,last_line=node.end_lineno,
                                  source_segment_sha256=hashlib.sha256(segment.encode()).hexdigest(),body_changed=False))
    check(len(selected)==len(names),'Missing source definitions '+str(names))
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+selected,type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(path),'exec'),env)
def namespace(name,**items):
    module=types.ModuleType(name);sys.modules[name]=module;module.__dict__.update(items);return module.__dict__

class Vec:
    def __init__(self,values,kind,descr=None):
        self.values=tuple(values);self.dtype=types.SimpleNamespace(kind=kind);self.shape=(len(self.values),);self.ndim=1;self.descr=descr
    def __len__(self):return len(self.values)
    def __iter__(self):return iter(self.values)
    def __getitem__(self,key):return self.values[key]
    def tolist(self):return list(self.values)
    def astype(self,dtype):
        check(dtype is str,'Only text cast supported in this completion facade');return Vec(map(str,self.values),'U')
    def all(self):return all(self.values)
def read_npy(data):
    f=io.BytesIO(data);check(f.read(6)==b'\x93NUMPY','NPY magic');version=f.read(2)
    check(version in (b'\x01\x00',b'\x02\x00'),'NPY version')
    nbytes=2 if version[0]==1 else 4;size=struct.unpack('<H' if nbytes==2 else '<I',f.read(nbytes))[0]
    header=ast.literal_eval(f.read(size).decode('latin1').strip())
    check(not header['fortran_order'] and len(header['shape'])==1,'Only one-dimensional non-Fortran arrays supported')
    count=header['shape'][0];descr=header['descr'];raw=f.read()
    if descr.startswith('<U'):
        width=int(descr[2:])*4;check(width>0 and len(raw)==count*width,'Unicode NPY size')
        values=[raw[i:i+width].decode('utf-32-le').rstrip('\0') for i in range(0,len(raw),width)];kind='U'
    else:
        formats={'<f4':('f',4,'f'),'<f8':('d',8,'f'),'<i8':('q',8,'i'),'|b1':('?',1,'b'),'|i1':('b',1,'i')}
        check(descr in formats,'Unsupported/object dtype '+str(descr));fmt,width,kind=formats[descr]
        check(len(raw)==count*width,'Numeric NPY size');values=struct.unpack('<'+str(count)+fmt,raw)
    return Vec(values,kind,descr)
class NPZ:
    def __init__(self,path):
        self.z=zipfile.ZipFile(path);names=self.z.namelist()
        check(len(names)==len(set(names)) and all(n.endswith('.npy') and '/' not in n for n in names),'NPZ names')
        self.files=[n[:-4] for n in names];self.cache={}
    def __enter__(self):return self
    def __exit__(self,*args):self.z.close()
    def __getitem__(self,name):
        if name not in self.cache:self.cache[name]=read_npy(self.z.read(name+'.npy'))
        return self.cache[name]
class NP:
    @staticmethod
    def load(path,allow_pickle=False):
        check(allow_pickle is False,'Pickle forbidden');return NPZ(path)
    @staticmethod
    def asarray(value):check(isinstance(value,Vec),'Only typed vectors supported');return value
    @staticmethod
    def isfinite(value):
        return Vec([math.isfinite(v) for v in value],'b') if isinstance(value,Vec) else math.isfinite(value)

def close(a,b,label,rel=1e-6,abs_=1e-7):
    check(math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=rel,abs_tol=abs_),label)
    CHECKS['numeric_comparisons']+=1
def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
METRIC_FIELDS=['task','queries','gallery','query_identities','gallery_identities','r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP','MRR','mean_top1_margin','protocol']
DROP_FIELDS=['task','metric','clean','corrupted','absolute_drop_fraction','percentage_point_drop','relative_drop_fraction','relative_drop_percent']
SUMMARY_FIELDS=['corruption','severity_index','parameter','value','units']+DROP_FIELDS
def csv_check(path,expected,fields=None):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);rows=list(reader)
    check(len(rows)==len(expected),'CSV row count '+str(path))
    check(fields is not None and reader.fieldnames==fields and len(reader.fieldnames)==len(set(reader.fieldnames)) and set(reader.fieldnames)==set(expected[0]),'Exact ordered unique CSV columns '+str(path))
    for row,original in zip(rows,expected):
        for key,value in original.items():
            if value is None:check(row[key]=='','CSV None encoding')
            elif isinstance(value,(float,int)) and not isinstance(value,bool):close(float(row[key]),value,'CSV numeric',1e-12,1e-14)
            else:check(row[key]==str(value),'CSV text '+key)
    CHECKS['csv_tables']+=1

report=dict(schema='bounded-sues-visual1-robustness-review-v1',started_utc=now(),passed_with_stated_limits=False,
            source=dict(path=str(Path(__file__)),sha256=sha(__file__)),scope=dict(runs=1,corrupted_conditions=30,corrupted_tasks=240,clean_tasks=8),
            checkpoint_bytes_read=0,cache_or_image_bytes_read=0,scientific_entrypoints_executed=False,live_files_modified=False)
try:
    adopted_root=EX/'transfer_audit_20260929_0647/ROOT_TRANSFER12_AND_NATIVE2_ADOPTION.json'
    root,rootbind=snap(adopted_root,expected='fb7588357afa3e225b67088437233db397c067131fb8bc6adf97ce9ccbdd3bdd')
    check(root['accepted'] and root['accepted_transfer_runs']==12,'Accepted prior root')
    adopted,b=snap(root['independent_transfer_review']['path'],expected='b0627920c9e8ab1da0dbc6d2d48795b3abe68cf3b79f7d7dba7afa9bba3847c7')
    prior=next(r for r in adopted['runs'] if r['source_training_identifier']=='formal_main/sues200/visual/seed_1/resnet18/dim_512')
    official_ref=prior['source_adoption_metadata']
    official,officialbind=snap(official_ref['path'],expected=official_ref['sha256'])
    officialrun=next(r for r in official['runs'] if r['identifier']=='formal_main/sues200/visual/seed_1/resnet18/dim_512')
    for node in adopted['adoption_graph']:
        if Path(node['path']).name in ('ROOT_FIT_42_ADOPTION_20260928.json','ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json','ROOT_SUES_BATCH11_ADOPTION_20260929.json'):
            snap(node['path'],expected=node['sha256'])
    trainledger,tb=snap(adopted['inherited_training_checkpoint_ledger']['path'],expected=adopted['inherited_training_checkpoint_ledger']['sha256'])
    check(trainledger['runs'][prior['source_training_identifier']]['checkpoint_sha256']==prior['inherited_checkpoint_SHA']==officialrun['inherited_checkpoint_SHA']['inherited_sha256'],'Specific adopted training/official inherited SHA agreement')
    authority=prior['source_training_authority']
    training_batch,trainbind=snap(authority['report_path'],expected=authority['report_sha256'])
    check(training_batch['batch_passed'],'Specific adopted SUES training batch passed')
    entries=[r for r in training_batch['new_runs'] if r['run_identifier']==prior['source_training_identifier']]
    check(len(entries)==1,'Exactly one SUES Visual1 training authority member')
    training=entries[0]
    check(training['epochs_completed']==80 and training['last_epoch']==79 and training['original_training_completion_issues']==[] and training['optimizer_steps_each_epoch_from_original_config']==375,'SUES Visual1 accepted original 80x375 training completion')
    accepted_best=training['artifacts_sha256_verified']['best.pt']
    check(accepted_best['sha256']==prior['inherited_checkpoint_SHA'] and accepted_best['bytes']==prior['checkpoint_stat_only']['bytes'],'SUES Visual1 historically fresh best.pt authority')
    check(officialrun['inherited_checkpoint_SHA']['specific_training_authority']==authority and officialrun['inherited_checkpoint_SHA']['specific_historical_artifact']==accepted_best,'SUES official and T3 exact specific training authority agreement')
    official_root,orb=snap(official_ref['parent'],expected='657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b')
    check(official_root['adopted_with_stated_inheritance_limits'] and official_root['independent_report']['sha256']==officialbind['sha256'],'Specific SUES official root/report edge')
    # Rebind only the small adopted ancestry needed for this specific training report.
    # This does not hash any old training weights or old official per-query artifacts.
    graph={norm(g['to_document']):g for g in official['inherited_training_acceptance_graph']}
    edge=graph[norm(trainbind['path'])];ancestry=[];seen=set()
    def has_ref(obj,path,digest):
        if isinstance(obj,dict):
            vals=list(obj.values())
            if digest in vals and any(isinstance(v,str) and v.lower().endswith('.json') and norm(v)==norm(path) for v in vals):return True
            return any(has_ref(v,path,digest) for v in vals if isinstance(v,(dict,list)))
        return isinstance(obj,list) and any(has_ref(v,path,digest) for v in obj)
    while True:
        check(edge['sha256']==(trainbind['sha256'] if not ancestry else edge['sha256']) and norm(edge['to_document']) not in seen,'Unique accepted ancestry node')
        seen.add(norm(edge['to_document']));ancestry.append(edge)
        parent_path=edge['from_document']
        if parent_path is None:
            check(Path(edge['to_document']).name=='ROOT_FIT_42_ADOPTION_20260928.json' and edge['sha256']=='ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87','Exact ROOT42 ancestry anchor')
            break
        parent_edge=graph[norm(parent_path)]
        parent_doc,parent_binding=snap(parent_path,expected=parent_edge['sha256'])
        check(has_ref(parent_doc,edge['to_document'],edge['sha256']),'Actual parent JSON contains precise path/SHA ancestry edge')
        edge=parent_edge
    report['specific_training_source_bindings']=dict(report=trainbind,official_root=orb,root42_ancestry=ancestry)
    report['inherited_authority']=dict(root=rootbind,transfer_review=b,official_review=officialbind,
        source_training_identifier=prior['source_training_identifier'],checkpoint_sha256=prior['inherited_checkpoint_SHA'],
        training_authority=prior['source_training_authority'],training_ledger=tb,
        limitation='SUES Visual1 uses its own accepted Sep21 BATCH_COMPLETION_1611 member reached by actual ROOT42 ancestry, then specific SUES batch11 official/T3 authority. Historical initial12/visual_style1 whole-file SHA gaps elsewhere in the global chain are retained, not used as this checkpoint authority. Current weight bytes are not proven by stat.')

    ledger,lb=snap(PKG/'runs/frozen_robustness_matrix_ledger.json')
    check(canonical(ledger['immutable_config'])==ledger['config_sha256']=='f1016dadeefb98d142d49ea6b46780a0abbaa4cf74727a7c7c237138c0616514','Stage canonical config')
    specrow=next(x for x in ledger['immutable_config']['registered_runs'] if x['identifier']=='sues200/visual/seed_1')
    completed=ledger['runs'][specrow['identifier']]
    check(completed['status']=='completed_and_verified' and len(completed['attempts'])==1,'Original completed record')
    attempt=completed['attempts'][0]
    check(attempt['returncode']==0 and attempt['command']==specrow['command'],'Original return0/exact registered command')
    for label in ('stdout','stderr'):
        d=attempt[label];snap(d['path'],f'{label}.log',expected=d['sha256'],size=d['bytes'])
    check(attempt['stderr']['bytes']==0,'Completed SUES Visual stderr is empty')
    report['original_parent_record']=dict(ledger=lb,run_record=completed,limitation='Original parent subprocess.run return0 and closed log hashes; no independent interpreter/launcher exit handles.')
    snapshot,ob=snap(EX/'robustness_observation_20260929_0647/snapshot_20260929_135047460/OBSERVATION.json',expected='e5c4d484bdb7e703b373863b60fb02cdd3f372bf307559f0d00df96a5bc9d950')
    report['latest_parent_observation']=ob
    cps=subprocess.run(['powershell','-NoProfile','-Command',"@{utc=[DateTime]::UtcNow.ToString('o'); matches=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @(24428,40060)} | ForEach-Object {@{pid=$_.ProcessId;parent=$_.ParentProcessId;creation_utc=$_.CreationDate.ToUniversalTime().ToString('o');creation_ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();command=$_.CommandLine}})} | ConvertTo-Json -Depth 5 -Compress"],capture_output=True,text=True,encoding='utf-8',check=True)
    report['old_worker_CIM_observation']=json.loads(cps.stdout)
    old_ticks={24428:'639262775229496270',40060:'639262775229943530'}
    for row in report['old_worker_CIM_observation']['matches']:
        check(row['creation_ticks']!=old_ticks[row['pid']],'Original SUES Visual worker identity still exists; review required')
    report['old_worker_CIM_observation']['original_identity_ticks']=old_ticks
    report['old_worker_CIM_observation']['interpretation']='Original SUES Visual identities absent; any same numeric PID with different exact UTC ticks is a reused process. No historical dual-handle exit code is inferred.' 

    source_table={
      'common':(PKG/'experiments/formal_robustness_common.py',ledger['immutable_config']['source_hashes']['common_validator']),
      'evaluator':(PKG/'experiments/run_image_level_robustness.py',ledger['immutable_config']['source_hashes']['evaluator']),
      'orchestrator':(PKG/'experiments/run_frozen_robustness_matrix.py',ledger['immutable_config']['source_hashes']['orchestrator']),
      'core':(PKG/'lgm_game_pytorch/formal_retrieval.py',ledger['immutable_config']['source_hashes']['formal_retrieval'])}
    for p,digest in source_table.values():SOURCE_BYTES[str(p)]=snap(p,expected=digest)[0]
    manifest,mb=snap(RUN/'robustness_manifest.json','r/robustness_manifest.json',expected=completed['robustness_manifest_sha256'])
    check(manifest['run_config_sha256']==completed['run_config_sha256']=='d19283877ee9967fc36ca82155564cdc5945a44f7633273e119a661bf684f6d9','Run canonical config distinct from stage')
    artifacts=manifest['artifacts']
    check(set(artifacts)=={p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file() and p.name not in ('robustness_manifest.json','run.log')},'Root inventory exact coverage')
    artifact_bindings=[]
    for relative,d in artifacts.items():
        check('..' not in Path(relative).parts and not Path(relative).is_absolute(),'Safe artifact path')
        _,ab=snap(RUN/relative,'r/'+relative,expected=d['sha256'],size=d['bytes']);artifact_bindings.append(ab)
    snap(RUN/'run.log','run.log')
    config=json.loads((TREE/'run_config.json').read_text(encoding='utf-8-sig'));imm=config['immutable_config']
    cp=Path(specrow['checkpoint']);check(cp.is_file() and os.path.samefile(RUN,specrow['output_dir']),'Original path identity')
    report['checkpoint_stat_only']=dict(bytes=cp.stat().st_size,mtime_ns=cp.stat().st_mtime_ns)
    check(cp.stat().st_size==prior['checkpoint_stat_only']['bytes'] and os.path.samefile(cp,accepted_best['path']),'SUES Visual checkpoint exists, same file as own accepted artifact, size matches inherited metadata')
    check(manifest['checkpoint']==imm['checkpoint'],'Manifest/config checkpoint agreement')
    check(imm['checkpoint']['checkpoint_sha256']==prior['inherited_checkpoint_SHA'],'Inherited checkpoint SHA binding')
    check(imm['checkpoint']['selected_training_epoch_one_based']==80,'Frozen epoch80 checkpoint')
    for filename,expectedhash in [('run_config.json',imm['checkpoint']['training_run_config_sha256']),('run_manifest.json',imm['checkpoint']['training_manifest_sha256'])]:
        current=cp.parent/filename
        old=next(r for r in adopted['raw_evidence_bindings'] if norm(r['path'])==norm(current))
        doc,bind=snap(current,'training_'+filename,expected=old['sha256'],size=old['bytes'])
        check(doc.get('run_config_sha256')==expectedhash if filename=='run_config.json' else bind['sha256']==expectedhash,'Actual small training binding')
    check(imm['encoding']==dict(eval_batch_size=128,image_workers=8,amp=True,clip_precision='match-cache',clip_local_files_only=True,clip_clean_audit_samples=64),'Encoding immutable settings')
    check(imm['ranking']==dict(score='float32 query matrix @ float32 clean-gallery matrix.T',sort='numpy stable descending argsort',chunk_size=128,full_gallery=True),'Ranking immutable settings')
    for d in imm['sources'].values():snap(d['path'],expected=d['sha256'])
    for evidence in imm['evidence_caches']:
        check(evidence['sha256']==specrow['evidence_sha256']=='6c3a82fdcf59e401f5da4ed0f3d9dca99fdcbab0a46aa66fb47a055c832cdabd','Inherited evidence hash declaration')
        cachemeta,cachemetabind=snap(evidence['meta_path'],expected=evidence['meta_sha256'])
    check(manifest['clip_clean_reproduction_audit'] is None,'SUES Visual intentionally does not initialize online CLIP')
    check('clip_clean_reproduction_audit.json' not in artifacts,'SUES Visual has no Full CLIP diagnostic artifact')

    corepath=source_table['core'][0]
    core=namespace('robustness_pure_protocol',Path=Path,PurePosixPath=PurePosixPath,dataclass=dataclass,defaultdict=defaultdict,json=json,hashlib=hashlib,re=re,LOGGER=logging.getLogger('readonly'))
    extract(corepath,{'EvidenceRecord','RetrievalTask','SUES_ALTITUDES','SUES_OFFICIAL_TRAIN_IDS','SUES_MANIFEST_SOURCE','canonical_json_bytes','canonical_sha256','normalized_relative_path','slugify','_component_after','derive_record','derive_all_records','_group_by_label','_assert_task','build_official_evaluation_tasks','protocol_membership_hash'},core)
    # Only directory-entry metadata is read; no cached embeddings, image content or image decoding.
    paths=[]
    for role in ('drone_view_512','satellite-view'):
        for p in (DATA/role).rglob('*'):
            if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.bmp','.webp'):paths.append(p.relative_to(DATA).as_posix())
    paths.sort();check(len(paths)==40200 and len(set(p.casefold() for p in paths))==40200,'Exact SUES full image path union')
    check(paths==[core['normalized_relative_path'](p) for p in paths],'Directory paths already normalized')
    sm=imm['sues_manifest']
    manifest_bytes,suesbind=snap(sm['path_or_source'],'SUES_OFFICIAL_TRAIN_IDS_RAW.yaml',expected='c1386d5c746aca48bbb2793ed1ee19d6cd7330a7f5f1b27a5ec43727317ec226')
    train_ids=re.findall(r'^\s*-\s*["]([0-9]{4})["]\s*$',manifest_bytes.decode('utf-8'),flags=re.MULTILINE)
    check(tuple(train_ids)==core['SUES_OFFICIAL_TRAIN_IDS'] and len(set(train_ids))==120,'Exact ordered original 120 SUES training IDs')
    check(tuple(core['SUES_ALTITUDES'])==('150','200','250','300') and sm['sha256']==suesbind['sha256'] and sm['official_source_url']==core['SUES_MANIFEST_SOURCE'] and sm['train_id_count']==120 and sm['test_id_count']==80,'Four official heights and fixed manifest declaration')
    all_ids={f'{i:04d}' for i in range(1,201)};test_ids=all_ids-set(train_ids)
    check(len(test_ids)==80,'Official complementary 80 test IDs')
    records=core['derive_all_records'](types.SimpleNamespace(paths=paths),DATA,'sues200')
    check(len(records)==40200,'All SUES directory images belong to supported roles')
    tasks=core['build_official_evaluation_tasks'](records,'sues200',train_ids)
    check(len(tasks)==8 and core['protocol_membership_hash'](tasks)==imm['protocol_membership_sha256']=='1f543fb48416204dacfb5ac48b3bbf3ce4080ce164e75e7a86be748e3d798772','Exact SUES eight-task membership')
    for altitude in core['SUES_ALTITUDES']:
        forward=next(t for t in tasks if t.name==f'sues200_uav_{altitude}m_to_satellite')
        reverse=next(t for t in tasks if t.name==f'sues200_satellite_to_uav_{altitude}m')
        check((len(forward.query),len(forward.gallery),len(reverse.query),len(reverse.gallery))==(4000,200,80,10000),'Exact SUES direction scales')
        check({r.label for r in forward.query}=={r.label for r in reverse.query}==test_ids and {r.label for r in forward.gallery}=={r.label for r in reverse.gallery}==all_ids,'All 80 query IDs/all 200 gallery IDs retained')
        check(all(r.altitude==altitude and r.view=='drone' for r in forward.query+reverse.gallery),'Exact altitude and UAV role')
        check(all(r.view=='satellite' for r in forward.gallery+reverse.query),'Exact satellite role')
        counts=defaultdict(int)
        for rec in reverse.gallery:counts[rec.label]+=1
        check(set(counts)==all_ids and set(counts.values())=={50},'Each altitude has 50 UAV images per each of 200 IDs')
    pathfile=save('OFFICIAL_TEST_DIRECTORY_PATHS.json',json.dumps(paths,ensure_ascii=False).encode())
    report['directory_membership']=dict(path=str(pathfile),sha256=sha(pathfile),count=len(paths),image_bytes_read=False,source='Image directory-entry metadata from both official SUES roles; original pure core task builder.')
    report['sues_official_protocol']=dict(manifest=suesbind,train_ids=train_ids,test_ids=sorted(test_ids),heights=list(core['SUES_ALTITUDES']),tasks=8,all_200_gallery_ids_retained=True)
    querypaths=sorted({r.relative_path for t in tasks for r in t.query});gallerypaths=sorted({r.relative_path for t in tasks for r in t.gallery})
    check(len(querypaths)==16080 and len(gallerypaths)==40200 and set(querypaths)<=set(gallerypaths),'SUES query/gallery union counts and containment')
    check(canonical(querypaths)==imm['query_path_membership_sha256'] and canonical(gallerypaths)==imm['gallery_path_membership_sha256'],'Query/gallery union hashes')
    for field,values in [('clean_query_coverage',querypaths),('clean_gallery_coverage',gallerypaths)]:
        coverage=manifest[field]
        check(coverage['expected_unique_images']==coverage['encoded_unique_images']==len(values) and coverage['complete'] and coverage['coverage_fraction']==1 and coverage['missing_images']==coverage['extra_images']==0,'Clean coverage declaration')
        check(coverage['path_membership_sha256']==canonical(values) and coverage['pixels_decoded_for_every_active_visual_embedding'] and not coverage['corruption_applied_before_all_model_preprocessing'],'Clean coverage semantics')
        check(coverage['embedding_dim']==512 and coverage['embedding_storage_dtype_for_hash']=='little-endian float32' and coverage['query_content_style_evidence_mode']=='clean_cache','Complete clean coverage dtype/evidence path')
        check(re.fullmatch('[0-9a-f]{64}',coverage['encoded_feature_sha256']) is not None and coverage['elapsed_seconds']>=0,'Clean coverage declared feature hash/time')
    clean_manifest=json.loads((TREE/'clean/condition_manifest.json').read_text(encoding='utf-8-sig'))
    check(clean_manifest['query_coverage']==manifest['clean_query_coverage'],'Exact clean condition/top query coverage identity')
    evaluator=namespace('robustness_conditions_only' ,dataclass=dataclass,formal=types.SimpleNamespace(**core))
    extract(source_table['evaluator'][0],{'SCHEMA_VERSION','DEFAULT_CORRUPTION_SEED','CORE_METRICS','CorruptionSpec','CORRUPTION_SPECS','SPEC_BY_NAME','corruption_matrix_payload','_condition_payload','compute_degradation','_summary_rows'},evaluator)
    common=namespace('robustness_original_completion',Path=Path,dataclass=dataclass,hashlib=hashlib,json=json,np=NP)
    extract(source_table['common'][0],{'SCHEMA_VERSION','ROBUSTNESS_MANIFEST_SCHEMA','DATASETS','VARIANTS','EXPECTED_RUN_COUNT','EXPECTED_CONDITION_COUNT','EXPECTED_SEED','OFFICIAL_TASK_SCALE','EXPECTED_UNIQUE_QUERIES','EXPECTED_UNIQUE_GALLERIES','REQUIRED_METRICS','REQUIRED_CLEAN_ARRAYS','REQUIRED_CORRUPTED_ARRAYS','canonical_json_bytes','canonical_sha256','sha256_file','load_json','verify_payload_hash','RobustnessRunSpec','expected_condition_payloads','condition_directory','_validate_artifact_inventory','_metrics_issues','_per_query_issues','RobustnessValidation','validate_completed_robustness'},common)
    def tracked_hash(path,block_size=8*1024*1024):
        p=Path(path)
        if p.suffix.lower() in ('.pt','.pth','.ckpt'):
            check(norm(p)==norm(cp) and os.path.samefile(p,cp),'Only exact accepted source checkpoint SHA inheritance permitted')
            digest=prior['inherited_checkpoint_SHA'];mode='exact_inherited_checkpoint_SHA_no_read'
        else:
            check(p.resolve().is_relative_to(TREE.resolve()),'Completion helper read outside captured tree')
            digest=sha(p);mode='actual_sealed_artifact_hash'
        HASH_QUERIES.append(dict(path=str(p),sha256=digest,mode=mode));return digest
    common['sha256_file']=tracked_hash
    rspec=common['RobustnessRunSpec']('sues200','visual',DATA,Path(specrow['evidence']),cp,TREE)
    validation=common['validate_completed_robustness'](rspec,types.SimpleNamespace(**evaluator),verify_artifacts=True,verify_per_query=True,expected_evaluator_sha256=source_table['evaluator'][1])
    report['original_completion_issues']=validation.issues
    check(validation.complete,'Original completion gate issues: '+repr(validation.issues))
    check(sum(h['mode'].startswith('exact_inherited') for h in HASH_QUERIES)==1,'Exactly one inherited checkpoint hash query')

    summary=json.loads((TREE/'robustness_summary.json').read_text(encoding='utf-8-sig'))
    check(summary['clean']==validation.clean_metrics and summary['run_config_sha256']==manifest['run_config_sha256'],'Summary clean/config')
    conditions=common['expected_condition_payloads'](types.SimpleNamespace(**evaluator))
    cleancondition=evaluator['_condition_payload'](corruption=None,severity_index=None,corruption_seed=20260727)
    clean_arrays={};task_reviews=[];all_summary=[]
    for condition in [cleancondition]+conditions:
        corrupted=condition['kind']=='corruption'
        subdir=Path('conditions')/condition['name']/f"severity_{condition['severity_index']:02d}" if corrupted else Path('clean')
        d=TREE/subdir;metrics=json.loads((d/'metrics.json').read_text(encoding='utf-8-sig'));cm=json.loads((d/'condition_manifest.json').read_text(encoding='utf-8-sig'))
        check(metrics['unit']=='fraction' and metrics['AP_definition']=='Official trapezoidal interpolation used by the University-1652/SUES reference evaluator.','Top-level metric fraction/AP semantics')
        cov=cm['query_coverage'];check(cov['path_membership_sha256']==canonical(querypaths),'Per-condition query union hash')
        check(cov['query_content_style_evidence_mode']==('not_used_by_visual_variant' if corrupted else 'clean_cache') and cov['corruption_applied_before_all_model_preprocessing'] is corrupted,'SUES Visual clean/corrupt visual-only pixel pathway declarations')
        check(cov['elapsed_seconds']>=0,'Condition encoded elapsed time declaration')
        check(cov['missing_images']==cov['extra_images']==0 and cov['embedding_dim']==512 and cov['embedding_storage_dtype_for_hash']=='little-endian float32' and cov['pixels_decoded_for_every_active_visual_embedding'],'Coverage additional fields')
        check(re.fullmatch('[0-9a-f]{64}',cov['encoded_feature_sha256']) is not None,'Encoded-feature declared hash syntax')
        check(set(cm['artifacts'])=={p.relative_to(d).as_posix() for p in d.rglob('*') if p.is_file() and p.name!='condition_manifest.json'},'Condition inventory exact coverage')
        check(cm['condition_sha256']==canonical(dict(run_config_sha256=manifest['run_config_sha256'],condition=condition)),'Clean/corruption condition digest')
        for task in tasks:
            name=task.name;result=metrics['results'][name];npz=d/'per_query_arrays'/(core['slugify'](name)+'_per_query.npz')
            with NPZ(npz) as archive:
                base={'margin','correct','first_positive_rank_zero_based','per_query_official_trapezoid_AP','reciprocal_rank','query_paths','query_labels','top1_gallery_indices','top1_gallery_paths','top1_gallery_labels'}
                extra={'clean_margin','clean_correct','clean_first_positive_rank_zero_based','clean_per_query_official_trapezoid_AP','clean_reciprocal_rank','delta_official_trapezoid_AP_corrupted_minus_clean','delta_reciprocal_rank_corrupted_minus_clean','top1_correctness_transition_corrupted_minus_clean'}
                check(set(archive.files)==base|(extra if corrupted else set()),'Exact producer array schema')
                arrays={k:archive[k] for k in archive.files}
            count=len(task.query);gallery=len(task.gallery)
            check(all(a.shape==(count,) for a in arrays.values()),'All arrays exact one-dimensional query shape')
            check(arrays['query_paths'].tolist()==[r.relative_path for r in task.query] and arrays['query_labels'].tolist()==[r.label for r in task.query],'Actual official query membership/order/labels')
            for key,a in arrays.items():
                kind='U' if key in ('query_paths','query_labels','top1_gallery_paths','top1_gallery_labels') else 'b' if key in ('correct','clean_correct') else 'i' if key in ('first_positive_rank_zero_based','clean_first_positive_rank_zero_based','top1_gallery_indices','top1_correctness_transition_corrupted_minus_clean') else 'f'
                check(a.dtype.kind==kind,'Array dtype kind '+key)
                if kind=='i':check(a.descr==('|i1' if key=='top1_correctness_transition_corrupted_minus_clean' else '<i8'),'Exact producer integer dtype '+key)
                if kind=='b':check(a.descr=='|b1','Exact producer boolean dtype '+key)
                if kind=='f':check(a.descr=='<f4' and all(math.isfinite(x) for x in a),'Finite float32 '+key)
            ranks=arrays['first_positive_rank_zero_based'];rr=arrays['reciprocal_rank'];ap=arrays['per_query_official_trapezoid_AP'];correct=arrays['correct'];idx=arrays['top1_gallery_indices']
            for i in range(count):
                check(0<=ranks[i]<gallery and 0<=idx[i]<gallery,'Rank/index bounds')
                check(correct[i]==(ranks[i]==0)==(task.query[i].label==task.gallery[idx[i]].label),'Correct/rank/label mapping')
                check(arrays['top1_gallery_paths'][i]==task.gallery[idx[i]].relative_path and arrays['top1_gallery_labels'][i]==task.gallery[idx[i]].label,'Top1 exact gallery index mapping')
                check(rr[i]==f32(1.0/(ranks[i]+1)) and 0<=ap[i]<=1 and arrays['margin'][i]>=0,'RR float32/AP range/margin')
            for k in (1,5,10,20):close(result[f'r_at_{k}'],sum(r<min(k,gallery) for r in ranks)/count,'Recall from rank',1e-12,1e-14)
            for key,arr in [('official_trapezoid_mAP',ap),('MRR',rr),('mean_top1_margin',arrays['margin'])]:close(result[key],math.fsum(arr)/count,'Stored float32 mean tolerance')
            scale=dict(queries=count,gallery=gallery,query_identities=len({r.label for r in task.query}),gallery_identities=len({r.label for r in task.gallery}),protocol=task.protocol)
            check(all(result[k]==v for k,v in scale.items()) and result['unit']=='fraction','Task scale/protocol')
            if not corrupted:clean_arrays[name]=arrays
            else:
                original=clean_arrays[name]
                for key in ('margin','correct','first_positive_rank_zero_based','per_query_official_trapezoid_AP','reciprocal_rank'):
                    check(arrays['clean_'+key].values==original[key].values,'Exact copied clean array '+key)
                check(arrays['top1_correctness_transition_corrupted_minus_clean'].descr=='|i1','Signed int8 transition')
                for i in range(count):
                    check(arrays['delta_official_trapezoid_AP_corrupted_minus_clean'][i]==f32(ap[i]-original['per_query_official_trapezoid_AP'][i]),'Float32 AP delta')
                    check(arrays['delta_reciprocal_rank_corrupted_minus_clean'][i]==f32(rr[i]-original['reciprocal_rank'][i]),'Float32 RR delta')
                    check(arrays['top1_correctness_transition_corrupted_minus_clean'][i]==int(correct[i])-int(original['correct'][i]),'Signed correctness transition')
            task_reviews.append(dict(condition=condition['name'],severity=condition.get('severity_index'),task=name,queries=count,gallery=gallery,arrays=len(arrays),membership_mapping_and_stored_aggregates_checked=True,full_ranking_and_AP_from_all_positive_ranks_recomputed=False))
        ordered_metrics=[dict(task=name,**row) for name,row in metrics['results'].items()]
        # Original write_metrics_csv excludes the JSON-only unit field.
        ordered_metrics=[{k:v for k,v in row.items() if k!='unit'} for row in ordered_metrics]
        csv_check(d/'metrics.csv',ordered_metrics,METRIC_FIELDS)
        if corrupted:
            expected_degradation=evaluator['compute_degradation'](validation.clean_metrics['results'],metrics['results'])
            check(metrics['degradation_vs_clean']==expected_degradation,'Original degradation computation exact')
            degradation_rows=[dict(task=task,metric=metric,**values) for task,ms in expected_degradation.items() for metric,values in ms.items()]
            csv_check(d/'degradation_vs_clean.csv',degradation_rows,DROP_FIELDS)
            all_summary.extend(evaluator['_summary_rows'](condition,metrics))
    check(len(task_reviews)==248 and len(all_summary)==1440,'Fixed 248 tasks / 1440 degradation records')
    check(summary['rows']==all_summary,'Summary JSON equals all original pure summary rows')
    check(len(summary['corruption_conditions'])==30,'Summary condition count')
    for row,condition in zip(summary['corruption_conditions'],conditions):
        check(row['condition']==condition and row['status']=='completed' and os.path.samefile(row['directory'],RUN/'conditions'/condition['name']/f"severity_{condition['severity_index']:02d}"),'Summary condition identity/status/directory')
    csv_check(TREE/'robustness_summary.csv',all_summary,SUMMARY_FIELDS)
    check(report['checkpoint_stat_only']==dict(bytes=cp.stat().st_size,mtime_ns=cp.stat().st_mtime_ns),'Checkpoint metadata changed during bounded audit')
    check(not any(m in sys.modules for m in ('numpy','torch','pandas','scipy','PIL','matplotlib')),'No scientific modules imported')
    report.update(passed_with_stated_limits=True,accepted_runs=1,accepted_corrupted_conditions=30,accepted_corrupted_tasks=240,accepted_clean_tasks=8,
        manifest_binding=mb,artifact_bindings=artifact_bindings,unique_artifact_count=len(artifact_bindings),tasks=task_reviews,
        summary_rows=1440,original_hash_queries=HASH_QUERIES,original_functions=EXTRACTED,
        compatibility='Unchanged AST completion-function bodies from SHA-verified captured sources, typed stdlib 1D NPZ facade; scalar/array isfinite supported. Not a native NumPy rerun. Only one exact best.pt SHA request inherits adopted authority; other checkpoint requests/open reject.',
        independent_mean_check='Stored float32 AP/RR/margin values aggregated with math.fsum binary64 reference; relative tolerance1e-6 absolute1e-7 permits original float32 reduction rounding. Rank recalls use1e-12/1e-14; per-query AP/RR deltas require exact float32-roundtrip equality.',
        limits=[
          'Checkpoint bytes/state and full evidence/image content not re-read; exact inherited accepted SHA does not prove current bytes. SUES Visual1 has its own historical independent Sep21 batch member reached by ROOT42 ancestry. Historical initial12/visual_style1 whole-file SHA gaps elsewhere remain and are not silently repaired.',
          'Source/pixel-corruption/encoded-feature coverage declarations are bound, not independently executed. No image decoding, CLIP, model inference, feature recomputation or full ranking was run.',
          'Stored AP, RR and margin consistency was checked; AP was not recomputed from all positive ranks and margin not from full scores.',
          'SUES Visual intentionally skips online CLIP and has null clean reproduction audit. This does not establish any Full cached/online equivalence, Full corruption result or full-dataset onlineCLIP accuracy/efficiency.',
          'Only SUES Visual seed1 is accepted; no across-seed robustness SD/significance or whole4-run pipeline completion. No SUES Full result is included.',
          'Original parent subprocess.run return0 plus old worker PID observation is not independent dual-handle exit proof.',
          'Original completion helper does not ensure absent checkpoint fails, enforce exact array set/dtypes, recompute metric/degradation/summary numbers or fully bind membership. Additional read-only checks enforce these on this result without editing the original gate.'
        ])
except Exception as exc:
    report['error']=repr(exc);report['traceback']=traceback.format_exc()
finally:
    report['finished_utc']=now();report['checks']=dict(CHECKS);report['raw_evidence_bindings']=BINDINGS
    report['scientific_modules']=[m for m in ('numpy','torch','pandas','scipy','PIL','matplotlib') if m in sys.modules]
    r=save('REVIEW.json',json.dumps(report,ensure_ascii=False,indent=2,default=str).encode())
    metadata=dict(source=report['source'],report=dict(path=str(r),sha256=sha(r)),files=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()])
    m=save('METADATA.json',json.dumps(metadata,ensure_ascii=False,indent=2).encode())
    print(json.dumps(dict(passed=report['passed_with_stated_limits'],report=str(r),report_sha256=sha(r),metadata=str(m),metadata_sha256=sha(m),error=report.get('error'),checks=report['checks']),ensure_ascii=True))
    if not report['passed_with_stated_limits']:sys.exit(1)
