"""Independent source/contract delta review only. Never import any producer or recovery code."""
from pathlib import Path
import ast, copy, datetime, difflib, hashlib, json

EX=Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE=Path(__file__).parent
OLD=EX/'t6_recovery_preparation_20260930_0104'
NEW=EX/'t6_recovery_preparation_20260930_0405'
PROD=EX/'t6_new_boot_contract_derivation_20260930_0405'
OBS=EX/'heartbeat_observation_20260930_040510057'
STOP=EX/'efficiency_incident_20260929_1448/observation_20260930_040511476'
bindings={}; checks=[]

def raw(path,expected=None,sha=None):
    path=Path(path)
    assert path.suffix.lower() not in {'.pt','.pth','.npz','.npy','.png','.jpg','.zip'}
    assert path.stat().st_size<500000
    data=path.read_bytes()
    b={'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    if expected is not None: assert b==expected,str(path)
    if sha is not None: assert b['sha256']==sha,str(path)
    bindings[str(path)]=b
    return data

def binding(path):
    raw(path)
    return bindings[str(Path(path))]

def read(path,sha=None): return json.loads(raw(path,sha=sha))
def canonical(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def check(test,name):
    assert test,name
    checks.append(name)

oldraw=raw(OLD/'RECOVERY_CONTRACT.json',sha='d0aa27edfc5391689a947dc7a572d38a9a150186672c7d10965715f12e36d136')
newraw=raw(NEW/'RECOVERY_CONTRACT.json',sha='7e10d045a396c53a9ffb7ec0996e38f2a88101413cbf5655548a6f80edcb44ff')
old=json.loads(oldraw); new=json.loads(newraw)
manifest=read(NEW/'SOURCE_MANIFEST.json','6810affc21226b6e6c1bdea585b1fedbc6992ea7264df1b6e78eb0a0b08daca0')
derivation=read(PROD/'DERIVATION.json','089b35de1a5e5d637d10e9caf1b1e0912aa992c7845e14b75ddb5397d9debaad')
diff=read(PROD/'CONTRACT_SEMANTIC_DIFF.json','40ae596bb7b8f9e50d8d8ab9cd90287b20ef9ca03b86e087352b842c33188da9')
patch=raw(PROD/'RECOVERY_CONTRACT.patch',sha='b123d585d18d98308c89462f7315e2ae9afe58dadea21e25a08dd19b36dd8b52')
source=raw(PROD/'derive_new_boot_preparation.py',sha='251294561f41a8d627fc309544c44ae86ef90ac0fa7cb615e7af27f48b28afe5')
raw(PROD/'README.md')
root=read(OBS/'ROOT_BOOT_OBSERVATION_ADOPTION.json','c28fee27fa4036b199caa50daeee7813723e21c1edf7e854322d4e911c040b59')
obs=read(OBS/'OBSERVATION_WRAPPER_INCLUDED.json','46543c4e92245872f50aa1016ff09afb20d4197a05b872abe3c454837956615b')
stopped=read(STOP/'OBSERVATION.json','42422ac8b18e948b857478668c53c885847eb59be91f8dea08fce47ea25ec586')
oldmanifest=read(OLD/'SOURCE_MANIFEST.json','40b6ae257c53d77a024979d84bae71b85320a13e08a7a8c58a07f24bfacaa141')
oldroot=read(OLD/'ROOT_SOURCE_ADOPTION.json','fff6965e4d794902105f578cadb4680f363c7d6d31dcfd0a29bd3e636ea09343')
prior_review=read(HERE/'OBSERVATION_REVIEW.json','45ebcb84a5ce522c1595f2857b28979a3f5b629dd68c61ee3216d00483867394')
check(root['accepted_with_stated_limits'] is True and root['adopted_observation_only'] is True and root['execution_released'] is False,'Root authority adopted saved observation only')
check(binding(HERE/'OBSERVATION_REVIEW.json') in root['bindings'],'Root authority binds independent saved-observation review')
check(oldroot['source_manifest']==binding(OLD/'SOURCE_MANIFEST.json') and oldroot['execution_released'] is False,'Preceding adopted manifest stays unreleased and exact')
check(NEW.parent==EX,'New preparation remains direct EX child for unchanged guardian HERE.parent')
check(len(manifest['candidate_files'])==5 and manifest['candidate_files_count_excluding_this_manifest']==5,'Five actual candidate members declared')
check(manifest['input_contract']==binding(NEW/'RECOVERY_CONTRACT.json'),'Manifest binds new contract exact bytes')
check(manifest['scientific_sources_modified'] is False and manifest['required_release_schema']=='t6-pipeline-recovery-release.v1','Manifest retains release schema and no scientific source changes')
check(len(old['input_bindings'])==107 and len(new['input_bindings'])==114,'Only seven new contract input bindings appended')
check(canonical(old['input_bindings'])==canonical(new['input_bindings'][:107]),'All 107 original input bindings and scalar types unchanged without traversing their files')
expected_paths=[OLD/'RECOVERY_CONTRACT.json',OLD/'SOURCE_MANIFEST.json',OLD/'ROOT_SOURCE_ADOPTION.json',OBS/'OBSERVATION_WRAPPER_INCLUDED.json',STOP/'OBSERVATION.json',OBS/'ROOT_BOOT_OBSERVATION_ADOPTION.json',PROD/'derive_new_boot_preparation.py']
check([str(x) for x in expected_paths]==[x['path'] for x in new['input_bindings'][107:]],'Exactly specified seven provenance additions in original appended order')
for record in new['input_bindings'][107:]: raw(record['path'],expected=record)
check(len({x['path'] for x in new['input_bindings']})==114,'All new and inherited binding paths unique')
pins={'pipeline_recovery_candidate.py':'b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e','start_pipeline_recovery_candidate.ps1':'3c9e1ec672f6ef7b2a33060495c26d4a766add0b74e2780cc7dc4db732d4eb37','captured_pipeline_status.json':'47fd31336b8e742da91891a87c28a0767989cb45c375aeb000854f50e37acf12','pipeline_seed.json':'20973168dee96357397f27d103db79eec8f71375272fd3d1e9d240487f1d4360'}
for name,sha in pins.items():
    before=raw(OLD/name,sha=sha); after=raw(NEW/name,sha=sha)
    check(before==after,'Exact original bytes preserved: '+name)
    check(binding(OLD/name) in oldmanifest['candidate_files'] and binding(NEW/name) in manifest['candidate_files'],'Both manifests bind actual copy: '+name)
for record in manifest['candidate_files']: raw(record['path'],expected=record)
check({Path(x['path']).name for x in manifest['candidate_files']}==set(pins)|{'RECOVERY_CONTRACT.json'},'Manifest member names exactly match intended five')
captured=read(NEW/'captured_pipeline_status.json'); seed=read(NEW/'pipeline_seed.json'); spec=read(new['recovery_spec']['path'])
check(binding(new['recovery_spec']['path'])==new['recovery_spec'],'Original recovery spec actual small bytes bound')
check(len(captured['jobs'])==len(seed['jobs'])==7,'Seven original jobs retained in captured state and seed')
check(canonical(captured['jobs'][:6])==canonical(seed['jobs'][:6]),'First six entire completed job objects preserved in seed')
check(all(j['status']=='completed' and type(j['exit_code']) is int and j['exit_code']==0 for j in captured['jobs'][:6]),'First six stored original job records are completed with recorded exit zero')
check(captured['jobs'][6]['status']=='failed' and captured['jobs'][6]['exit_code']==1 and seed['jobs'][6]['status']=='pending','Original seventh failure retained in capture; existing unissued seed remains pending')
for i,(a,b) in enumerate(zip(captured['jobs'],seed['jobs'])):
    check(all(canonical(a[k])==canonical(b[k]) for k in ('id','command','entrypoint_sha256')),'Stored job identity/order/command/source unchanged: '+str(i+1))
check(canonical(captured['jobs'][6]['command'])==canonical(spec['original_t6_command']) and captured['jobs'][6]['entrypoint_sha256']==spec['original_t6_entrypoint_sha256'],'Original seventh scientific command and entrypoint digest preserved')
check(seed['recovery_preparation']['incident_capture']==old['incident_capture']==new['incident_capture'],'Seed links original incident unchanged')
check(new['host_boot_utc_ticks']==root['new_boot_ticks']=='639263337875000000' and new['host_boot_utc']=='2026-09-30T02:56:27.5000000+00:00','New contract boot matches independently reviewed root observation')
check(new['current_boot_authority']['previous_contract_boot_utc_ticks']==old['host_boot_utc_ticks']=='639263179115000000','Immediate preceding boot explicitly retained')
check(new['current_boot_authority']['original_incident_boot_utc_ticks']=='639262263395000000','Original scientific incident boot distinct and retained')
check(new['current_boot_authority']['root_observation_seal']==new['current_boot_authority']['boot_interpretation_adoption']==binding(OBS/'ROOT_BOOT_OBSERVATION_ADOPTION.json'),'Joint current root authority bound by both clearly explained fields')
check(new['current_boot_authority']['saved_observation_is_future_admission'] is False,'Saved observation not mislabeled future admission')
check(new['current_boot_authority']['saved_samples_utc']==[obs[k]['observed_utc'] for k in ('first','second')],'Actual saved scan times retained')
check(new['scientific_execution_performed'] is False and new['release_created'] is False,'Contract does not claim new execution or release')
unchanged={'schema','incident_capture','recovery_spec','live_state_bindings','append_log_prefixes','primary_controller_pid','candidate_scope','first_six_exact_records_preserved','scientific_execution_performed','release_created','predecessor_output_acceptance_roots'}
check(all(canonical(new[k])==canonical(old[k]) for k in unchanged),'All eleven unaffected contract fields strictly preserved')
check(set(new)-set(old)=={'future_root_runtime_attempt_absence_paths'} and not set(old)-set(new),'Only three-attempt annex added at top level; no field removed')
check(new['limits'][:5]==old['limits'][:5] and len(new['limits'])==8,'Five base limitations preserved; only attempt scope/GPU count and added history caveat change')
check('23 rows' in new['known_prerequisite'] and stopped['gpu_process_rows']==23 and stopped['original_gpu_exclusive_gate_would_be_satisfied'] is False,'Nonempty saved GPU query remains a release blocker')
attempts=[str(EX/n/'runtime_attempt') for n in ('t6_recovery_preparation_20260929_1548','t6_recovery_preparation_20260930_0104','t6_recovery_preparation_20260930_0405')]
check(new['future_root_runtime_attempt_absence_paths']==attempts,'All three attempt paths explicitly listed for future root readiness')
check(all(not Path(p).exists() for p in attempts),'All three attempt paths still absent at independent review')
check('future_root_runtime_attempt_absence_paths' not in (NEW/'pipeline_recovery_candidate.py').read_text(encoding='utf-8'),'Guardian does not parse the new root-only attempt annex')
check('current_boot_authority' not in (NEW/'pipeline_recovery_candidate.py').read_text(encoding='utf-8'),'Guardian does not parse provenance annex as a new admission gate')
rebuilt=[]
def inspect(a,b,path=''):
    if type(a) is not type(b): rebuilt.append({'pointer':path,'operation':'replace','old':a,'new':b}); return
    if isinstance(a,dict):
        for k in sorted(set(a)|set(b)):
            loc=path+'/'+k.replace('~','~0').replace('/','~1')
            if k not in a: rebuilt.append({'pointer':loc,'operation':'add','new':b[k]})
            elif k not in b: rebuilt.append({'pointer':loc,'operation':'remove','old':a[k]})
            else: inspect(a[k],b[k],loc)
    elif isinstance(a,list):
        for i in range(max(len(a),len(b))):
            loc=path+'/'+str(i)
            if i>=len(a): rebuilt.append({'pointer':loc,'operation':'add','new':b[i]})
            elif i>=len(b): rebuilt.append({'pointer':loc,'operation':'remove','old':a[i]})
            else: inspect(a[i],b[i],loc)
    elif canonical(a)!=canonical(b): rebuilt.append({'pointer':path,'operation':'replace','old':a,'new':b})
inspect(old,new)
check(canonical(rebuilt)==canonical(diff['changes']) and len(rebuilt)==40,'Complete strict-type recursive semantic diff independently reconstructed: forty changes')
check(not any(x['operation']=='remove' for x in rebuilt),'No semantic removals anywhere')
expected_patch=b''.join(difflib.diff_bytes(difflib.unified_diff,oldraw.splitlines(keepends=True),newraw.splitlines(keepends=True),fromfile=b'previous/RECOVERY_CONTRACT.json',tofile=b'new/RECOVERY_CONTRACT.json'))
check(expected_patch==patch,'Complete actual byte-line diff reconstructed and matches saved patch')
tree=ast.parse(source)
imports=[]
for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
        imports.extend([node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names])
check(set(imports)=={'pathlib','copy','datetime','difflib','hashlib','json','sys'},'Derivation imports only seven standard-library modules')
check(not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id in {'exec','eval','__import__'} for x in ast.walk(tree)),'No dynamic execution primitive in derivation AST')
check(derivation['added_small_input_bindings']==new['input_bindings'][107:] and derivation['new_input_count']==114,'Producer actual derivation report agrees with new contract additions')
for item in derivation['consumed_small_files']: raw(item['path'],expected=item)
for name in ('source','new_manifest','new_contract','root_boot_authority','semantic_diff','byte_line_diff'):
    raw(derivation[name]['path'],expected=derivation[name])
check(all(derivation[k] is False for k in ('execution_released','new_root_source_adoption_created','release_created','candidate_imported_or_executed','native_or_science_or_synthetic_tests_executed','live_state_old_source_logs_or_handoff_modified')),'Producer report keeps actual preparation distinct from release and execution')
binding(__file__)
report={'schema':'independent-t6-current-boot-contract-source-review.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accepted_source_only':True,'execution_released':False,'cleanup_authorized':False,'method':'Independent AI agent read complete new producer source, actual complete semantic and byte diffs, manifest, derivation report, root observation authority and README. Independently parsed actual old/new contracts and copied state/seed; only new focused stdlib binding/delta checks ran. Producer, guardian, PowerShell launcher, old scientific and synthetic suites were not imported or executed. Unchanged guardian runtime contract-coupling block read; prior full guardian/control adoption inherited by exact byte identity.','new_source_manifest':binding(NEW/'SOURCE_MANIFEST.json'),'new_contract':binding(NEW/'RECOVERY_CONTRACT.json'),'old_107_bindings_rehashed':False,'original_four_copied_files_exact':True,'semantic_change_count':40,'checks':checks,'binding_count_excluding_this_report':len(bindings),'bindings':list(bindings.values()),'limits':['This is source/delta review for a separate root source-adoption decision. It grants no execution release or process-control permission.','The unchanged guardian directly checks only its own HERE/runtime_attempt. The three-path annex remains a future root-readiness requirement, not a newly implemented runtime parser.','Current boot matching saved observations is not future admission. GPU still has 23 recorded rows; no resource exemption, release, launch-to-wait, native probe, lock acquisition, intent or seed publication follows.','Root future admission must freshly check all three attempt paths, source/state/current boot/processes, fully empty successful GPU query, available commit >=26 GiB, T6 output absence, closed log prefixes and carrier identity. Original three admissions/two fifteen-second gaps, real native child, six byte locks, final admission, <=900-second release, actual captured child exits and closed logs remain.','Stored first-six job exit records are not independent evidence of every historical controller or interpreter exit. No missing exit is manufactured.','Current Visio 29480 remains unowned; old process absences do not establish captured exits or cleanup authority.','All scientific acceptance restrictions, negative results, five-layer sequence and external DAC work remain unchanged. No weights/cache/images/large ZIP or scientific library was accessed.']}
data=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
with (HERE/'CONTRACT_SOURCE_REVIEW.json').open('xb') as f: f.write(data)
print(json.dumps({'report':{'path':str(HERE/'CONTRACT_SOURCE_REVIEW.json'),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},'checks':len(checks),'bindings':len(bindings)},ensure_ascii=False))
