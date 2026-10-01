"""Root adoption of new boot provenance delta only; does not execute a runner."""
from pathlib import Path
import datetime, hashlib, json, difflib

HERE=Path(__file__).parent
EX=HERE.parent
OLD=EX/'t6_recovery_preparation_20260930_0104'
NEW=EX/'t6_recovery_preparation_20260930_0405'
PROD=EX/'t6_new_boot_contract_derivation_20260930_0405'
REVIEW=EX/'heartbeat_boot_review_20260930_0405'
bindings={}
checks=[]

def bind(path, expected=None, sha=None):
    path=Path(path)
    assert path.stat().st_size<500000 and path.suffix.lower() not in {'.pt','.pth','.npz','.npy','.zip','.png','.jpg'}
    data=path.read_bytes()
    b=dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    if expected: assert all(b[k]==expected[k] for k in ('path','bytes','sha256')),str(path)
    if sha: assert b['sha256']==sha,str(path)
    bindings[str(path)]=b
    return b

def read(path,sha=None):
    bind(path,sha=sha)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def ck(ok,label):
    assert ok,label
    checks.append(label)

review=read(REVIEW/'CONTRACT_SOURCE_REVIEW.json','26280101e6ff266a5cc69be4564a98026743543d915221022db0b8488b7a19b0')
producer=read(PROD/'DELIVERY.json','3bbea8250916edd9cba8efcc811c0c923b5280c935be821bedb2bffab9715631')
for b in review['bindings']+producer['artifacts']: bind(b['path'],b)
ck(review['accepted_source_only'] is True and review['execution_released'] is False,'Independent source/delta review accepted with execution withheld')
manifest=read(NEW/'SOURCE_MANIFEST.json','6810affc21226b6e6c1bdea585b1fedbc6992ea7264df1b6e78eb0a0b08daca0')
old=read(OLD/'RECOVERY_CONTRACT.json','d0aa27edfc5391689a947dc7a572d38a9a150186672c7d10965715f12e36d136')
new=read(NEW/'RECOVERY_CONTRACT.json','7e10d045a396c53a9ffb7ec0996e38f2a88101413cbf5655548a6f80edcb44ff')
obs=read(HERE/'OBSERVATION_WRAPPER_INCLUDED.json','46543c4e92245872f50aa1016ff09afb20d4197a05b872abe3c454837956615b')
root=read(HERE/'ROOT_BOOT_OBSERVATION_ADOPTION.json','c28fee27fa4036b199caa50daeee7813723e21c1edf7e854322d4e911c040b59')
ck(NEW.parent==EX and len(manifest['candidate_files'])==5,'Five candidate files in an EX direct child')
ck(manifest['input_contract']==bind(NEW/'RECOVERY_CONTRACT.json'),'Manifest exact contract binding')
ck(len(old['input_bindings'])==107 and len(new['input_bindings'])==114 and canon(new['input_bindings'][:107])==canon(old['input_bindings']),'107 inherited binding values preserved, seven appended')
for b in new['input_bindings'][107:]: bind(b['path'],b)
allowed={'prepared_utc','host_boot_utc','host_boot_utc_ticks','known_prerequisite','input_bindings','current_boot_authority','historical_source_provenance','limits'}
ck(all(canon(old[k])==canon(new[k]) for k in old if k not in allowed),'Every unaffected contract field strictly unchanged')
ck(set(new)-set(old)=={'future_root_runtime_attempt_absence_paths'} and not set(old)-set(new),'Only explicit future-root attempt annex added')
for name in ('pipeline_recovery_candidate.py','start_pipeline_recovery_candidate.ps1','captured_pipeline_status.json','pipeline_seed.json'):
    ck((NEW/name).read_bytes()==(OLD/name).read_bytes(),'Unmodified copy: '+name)
raw_old=(OLD/'RECOVERY_CONTRACT.json').read_bytes(); raw_new=(NEW/'RECOVERY_CONTRACT.json').read_bytes()
patch=b''.join(difflib.diff_bytes(difflib.unified_diff,raw_old.splitlines(keepends=True),raw_new.splitlines(keepends=True),fromfile=b'previous/RECOVERY_CONTRACT.json',tofile=b'new/RECOVERY_CONTRACT.json'))
ck(patch==(PROD/'RECOVERY_CONTRACT.patch').read_bytes(),'Reviewed full actual byte-line patch matches saved patch')
ck(new['host_boot_utc_ticks']==root['new_boot_ticks']=='639263337875000000','New boot bound to current adopted saved observation')
ck(new['current_boot_authority']['previous_contract_boot_utc_ticks']=='639263179115000000' and new['current_boot_authority']['original_incident_boot_utc_ticks']=='639262263395000000','Both previous boot and original scientific incident retained distinctly')
for b in obs['files']: bind(b['path'],b)
ck(len(obs['files'])==16,'Sixteen current state/log files still match saved observation')
bind(obs['carrier']['path'],obs['carrier'])
ck(Path(obs['carrier']['path']).read_bytes()==b'0','Persistent carrier remains unchanged; no held lock claimed')
expected=[str(EX/x/'runtime_attempt') for x in ('t6_recovery_preparation_20260929_1548','t6_recovery_preparation_20260930_0104','t6_recovery_preparation_20260930_0405')]
ck(new['future_root_runtime_attempt_absence_paths']==expected and all(not Path(x).exists() for x in expected),'All three attempt paths listed and absent')
ck(not (EX.parent/'transfer_native_visio_candidate_20260930_0104/runtime_attempt_v1').exists(),'No Visio candidate attempt')
ck(not Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists(),'T6 output absent')
ck(new['scientific_execution_performed'] is False and new['release_created'] is False and root['execution_released'] is False,'Source and saved observation do not release execution')
src=bind(__file__)
report={
 'schema':'t6-pipeline-recovery-source-adoption.v1',
 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_manifest':bind(NEW/'SOURCE_MANIFEST.json'),
 'source':src,
 'approved_for_future_gated_execution':True,
 'execution_released':False,
 'adopted_scope':'Unchanged guardian/PowerShell/captured-state/seed bytes and separately reviewed current-boot contract delta only.',
 'new_boot_utc_ticks':'639263337875000000',
 'old_107_inputs_rehashed':False,
 'old_science_or_control_suites_rerun':False,
 'candidate_imported_or_executed':False,
 'method':'Root AI read complete new derivation and producer sealer, full byte diff and new contract fields, independent checker/report, manifest and README. Prior unchanged guardian/full control review inherited by exact byte identity; relevant release parsing read. This source adoption is distinct from producer and independent review.',
 'checks':checks,
 'bindings':list(bindings.values()),
 'limits':[
 'Future execution release must bind this exact manifest and this source adoption, with original seven-field schema, actual CLI hashes, timezone-aware issued<=now<expires and TTL<=900 seconds. No release is issued now.',
 'The saved successful GPU query contains 23 rows. No resource exemption, launch-to-wait, native probe, intent, retirement, seed publication, COM, cleanup or live state mutation follows.',
 'Future root admission must freshly verify all three attempt paths absent, current source/state/boot/process identities, empty successful GPU query, integer available commit >=26 GiB, closed original log prefixes, existing carrier and T6 absence.',
 'The unchanged guardian directly checks only its own runtime_attempt. The added provenance and three-path annex are root-readiness requirements, not new runtime parsers.',
 'All original six-lock, triple-admission/two15-second gaps, real isolated native child and allowed environment, final admission, captured launcher/interpreter identities and exits, closed-stream and successor sequencing requirements remain.',
 'Scientific work had already stopped before this reboot. No new scientific interruption, missing historical exit, current Visio ownership or scientific result is inferred.',
 'Prior source roots and consumed recovery entries remain historical and are not overwritten or replayed. Scientific negative results, uncertainty and historical evidence limits remain.'
 ]
}
path=NEW/'ROOT_SOURCE_ADOPTION.json'
with path.open('x',encoding='utf-8',newline='\n') as f: f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'root':bind(path),'checks':len(checks),'bindings':len(report['bindings'])},ensure_ascii=False))
