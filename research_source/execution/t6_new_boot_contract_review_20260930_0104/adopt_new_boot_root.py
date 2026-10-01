"""Root review of the new contract delta; no candidate import or execution."""
from pathlib import Path
import datetime as dt
import difflib
import hashlib
import json

HERE = Path(__file__).absolute().parent
EX = HERE.parent
OLD = EX/'t6_recovery_preparation_20260929_1548'
NEW = EX/'t6_recovery_preparation_20260930_0104'
OBS = EX/'heartbeat_observation_20260930_0102'
pins = {}
checks = 0

def check(ok, message):
    global checks
    checks += 1
    if not ok:
        raise RuntimeError(message)

def bind(path, expected=None):
    path = Path(path)
    check(path.suffix.lower() not in {'.pt','.npz','.npy','.png','.jpg','.zip'}, 'Forbidden input')
    check(path.stat().st_size < 2**21, 'Small-file bound')
    raw = path.read_bytes()
    item = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if expected:
        check(item == {k:expected[k] for k in item}, 'Binding changed: '+str(path))
    pins[str(path)] = item
    return item

def read(path):
    bind(path)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

manifest = read(NEW/'SOURCE_MANIFEST.json')
check(bind(NEW/'SOURCE_MANIFEST.json')['sha256'] == '40b6ae257c53d77a024979d84bae71b85320a13e08a7a8c58a07f24bfacaa141', 'Unexpected manifest')
old, new = read(OLD/'RECOVERY_CONTRACT.json'), read(NEW/'RECOVERY_CONTRACT.json')
check(bind(NEW/'RECOVERY_CONTRACT.json')['sha256'] == 'd0aa27edfc5391689a947dc7a572d38a9a150186672c7d10965715f12e36d136', 'Unexpected contract')
check(NEW.parent == EX and len(manifest['candidate_files']) == 5, 'Local runtime path or member count')
expected_names = {'pipeline_recovery_candidate.py','start_pipeline_recovery_candidate.ps1','captured_pipeline_status.json','pipeline_seed.json','RECOVERY_CONTRACT.json'}
check({Path(x['path']).name for x in manifest['candidate_files']} == expected_names, 'Candidate membership')
for item in manifest['candidate_files']:
    check(Path(item['path']).parent == NEW, 'Unexpected candidate location')
    bind(item['path'], item)
    if Path(item['path']).name != 'RECOVERY_CONTRACT.json':
        previous = OLD/Path(item['path']).name
        bind(previous)
        check(previous.read_bytes() == Path(item['path']).read_bytes(), 'Executable/state/seed bytes changed')
check(new['input_bindings'][:96] == old['input_bindings'] and len(new['input_bindings']) == 107, 'Inherited contract changed')
check(len({p['path'] for p in new['input_bindings']}) == 107, 'Duplicate contract binding')
for item in new['input_bindings'][96:]:
    bind(item['path'], item)
changed = {k for k in set(old)|set(new) if old.get(k) != new.get(k)}
check(changed == {'prepared_utc','host_boot_utc','host_boot_utc_ticks','known_prerequisite','input_bindings','limits','current_boot_authority','historical_source_provenance'}, 'Unexpected contract delta')
check(new['host_boot_utc_ticks'] == '639263179115000000' and old['host_boot_utc_ticks'] == '639262263395000000', 'Boot binding differs')
check(new['current_boot_authority']['original_incident_capture_and_recovery_spec_unchanged'] is True and new['current_boot_authority']['saved_observation_is_future_admission'] is False, 'Provenance meaning differs')
check(new['historical_source_provenance']['previous_source_adoption_authorizes_this_manifest'] is False, 'Old root reused as new authority')
check(new['limits'][:len(old['limits'])] == old['limits'], 'Inherited limits removed')

# Apply the saved complete semantic patch to a deep JSON copy, independently of
# the producer's diff function; require exact reconstructed equality.
diff = read(HERE/'CONTRACT_SEMANTIC_DIFF.json')
reconstructed = json.loads(json.dumps(old))
check(len(diff['changes']) == 21, 'Unexpected semantic delta count')
for change in diff['changes']:
    parts = [p.replace('~1','/').replace('~0','~') for p in change['pointer'].split('/')[1:]]
    target = reconstructed
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    key = int(parts[-1]) if isinstance(target, list) else parts[-1]
    if change['operation'] == 'replace':
        check(target[key] == change['old'], 'Semantic patch old value differs')
        target[key] = change['new']
    else:
        check(change['operation'] == 'add', 'Unexpected removal')
        if isinstance(target, list):
            check(key == len(target), 'Unexpected array insertion')
            target.append(change['new'])
        else:
            check(key not in target, 'Existing object key added')
            target[key] = change['new']
check(reconstructed == new, 'Semantic patch does not reconstruct entire contract')
patch = b''.join(difflib.diff_bytes(difflib.unified_diff, (OLD/'RECOVERY_CONTRACT.json').read_bytes().splitlines(keepends=True), (NEW/'RECOVERY_CONTRACT.json').read_bytes().splitlines(keepends=True), fromfile=b'old/RECOVERY_CONTRACT.json',tofile=b'new/RECOVERY_CONTRACT.json'))
bind(HERE/'RECOVERY_CONTRACT.patch')
check((HERE/'RECOVERY_CONTRACT.patch').read_bytes() == patch, 'Complete byte diff differs')
derivation = read(HERE/'DERIVATION.json')
for item in derivation['consumed_small_files']:
    bind(item['path'], item)
original, seed = read(NEW/'captured_pipeline_status.json'), read(NEW/'pipeline_seed.json')
check(len(original['jobs']) == len(seed['jobs']) == 7 and original['jobs'][:6] == seed['jobs'][:6], 'First-six complete records changed')
for x,y in zip(original['jobs'],seed['jobs']):
    check(all(x[k] == y[k] for k in ('id','command','entrypoint_sha256')), 'Frozen job changed')
check(original['jobs'][6]['exit_code'] == 1 and seed['jobs'][6]['status'] == 'pending', 'Failed attempt or seed changed')
observation = read(OBS/'OBSERVATION_WRAPPER_INCLUDED.json')
for row in observation['files']:
    bind(row['path'],row)
check(all(x in observation['files'] for x in new['live_state_bindings']+new['append_log_prefixes']), 'Current source snapshot differs')
check(all(observation[k]['boot_utc_ticks'] == new['host_boot_utc_ticks'] for k in ('first','second')), 'Observed boot differs')
for folder in (OLD,NEW):
    check(not (folder/'runtime_attempt').exists(), 'Attempt already exists')
check(not Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal').exists(), 'T6 output exists')
bind(__file__)
report = dict(
    schema='t6-pipeline-recovery-source-adoption.v1',
    utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    source_manifest=pins[str(NEW/'SOURCE_MANIFEST.json')],
    source=pins[str(Path(__file__).absolute())],
    approved_for_future_gated_execution=True,
    execution_released=False,
    adopted_scope='Unchanged guardian and thin entry, exact captured state/seed copies, separately bound current-boot contract only.',
    checks=checks, bindings=list(pins.values()),
    inherited_96_inputs_rehashed=False,
    old_science_or_control_suites_rerun=False,
    candidate_imported_or_executed=False,
    limits=[
        'Root read complete original guardian/PowerShell bytes, complete new derivation source and byte diff, and all new contract fields; this is source/contract adoption, not runtime evidence.',
        'Five candidate members plus manifest replace the old fourteen-file packaging scope; old 96 input bindings are value-identical, eleven new small provenance bindings are appended.',
        'Current boot authority is separate from the old scientific incident; no new scientific interruption or missing historical exit code is inferred.',
        'Latest saved GPU query has 26 rows; no execution release, native probe, lock acquisition, intent, retirement, seed publication or scientific launch is authorized now.',
        'Any future release must freshly verify both old and new attempt absence, current source/state/boot/owner identities, empty successful GPU query, 26GiB available commit, closed log prefixes, carrier and T6 absence.',
        'The unchanged guardian directly checks its own runtime_attempt only. Current-boot provenance is bound evidence, not separately interpreted runtime gates.',
        'All original six-lock, triple-admission, real isolated native probe, final admission, fifteen-minute release, child-handle/closed-log and predecessor requirements remain; no successor release is issued.',
        'Root review is distinct from the producer offline derivation. Existing independent old source/static and control evidence is inherited, not newly executed.'
    ])
target = NEW/'ROOT_SOURCE_ADOPTION.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps(bind(target),ensure_ascii=False))
