"""Preparation-only small-file binding and exact failed-state derivative; no live writes."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import datetime as dt

HERE=Path(__file__).absolute().parent
EX=HERE.parent
ROOT=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
spec=importlib.util.spec_from_file_location('candidate',HERE/'pipeline_recovery_candidate.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def write(path,data):
    with path.open('xb') as stream:stream.write(data)

def main():
    capture_path=EX/'efficiency_incident_20260929_1448/capture_20260929_144939892/CAPTURE.json'
    recovery_path=EX/'efficiency_incident_review_20260929_1448/RECOVERY_SPEC.json'
    capture=c.binding(capture_path)
    c.require(capture['sha256']=='7cd62f16dcf7f4a1ab9f3578b7c780ecb641ec02bf0fdf55a0a802f8bec2c1e4','Capture pin')
    recovery=c.binding(recovery_path)
    c.require(recovery['sha256']=='66e499c80036c3ef376993eb0decd01e28cd7adfa07cef54efc1001ac5dc0c45','Recovery pin')
    captured=c.read(capture_path)
    rows=captured['bindings']
    boot=dt.datetime.fromisoformat(captured['host_boot_utc'].replace('Z','+00:00'))
    delta=boot-dt.datetime(1,1,1,tzinfo=dt.timezone.utc)
    boot_ticks=str((delta.days*86400+delta.seconds)*10000000+delta.microseconds*10)
    inputs={}
    for row in rows:
        for k in ('source','snapshot'):
            c.verify_binding(row[k]);inputs[row[k]['path']]=row[k]
    state_rows=[r['source'] for r in rows if Path(r['source']['path']).name in c.STATE_NAMES]
    c.require(len(state_rows)==5,'Exact five state bindings')
    original_row=next(r for r in rows if Path(r['source']['path']).name=='pipeline_status.json')
    original_bytes=Path(original_row['snapshot']['path']).read_bytes()
    original=json.loads(original_bytes)
    native=EX/'continue_formal_matrix.py'
    c.require(c.binding(native)['sha256']=='4bac7204d1a152b726ed0fb4ebb806a9ef9f5a81b1c2d53f03ba44b0b124d4da','Native original source pin')
    io=EX/'state_io_retry_20260920_v2/SOURCE_MANIFEST.json'
    c.require(c.binding(io)['sha256']==c.IO_SHA,'State I/O manifest pin')
    extra=[capture_path,recovery_path,native,io]
    extra.extend(Path(row['path']) for row in c.read(io)['files'])
    extra.extend(Path(job['command'][1]) for job in original['jobs'])
    extra.extend([ROOT/'FORMAL_EXPERIMENT_PROTOCOL.md',
                  ROOT/'lgm_game_pytorch/experiments/run_frozen_formal_matrix.py',
                  ROOT/'lgm_game_pytorch/experiments/transactions_efficiency_analysis.py',
                  ROOT/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'])
    roots={
      EX/'completion_audits_20260928/ROOT_FIT_42_ADOPTION_20260928.json':'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87',
      EX/'evaluation_audits_20260929/ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json':'3b2bb1629f5b769fcd956c08068fa8ab2c947c9b36898a4bec2742e21110c17e',
      EX/'transfer_audit_20260929_0647/ROOT_TRANSFER12_AND_NATIVE2_ADOPTION.json':'fb7588357afa3e225b67088437233db397c067131fb8bc6adf97ce9ccbdd3bdd',
      EX/'pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json':'f55b05559de3ca536170de4ea0be79988dd7c5cf0c822be5f3572eb31a57af0a',
      EX/'efficiency_incident_review_20260929_1448/ROOT_INCIDENT_REVIEW_ADOPTION.json':'e0595908f2dfa911d3cf4662333c80119452802635d185634d7ee9280e614031'}
    for path,expected in roots.items():
        c.require(c.binding(path)['sha256']==expected,'Root pin '+str(path));extra.append(path)
    for path in extra:
        item=c.binding(path);inputs[item['path']]=item
    for job in original['jobs']:
        c.require(c.binding(job['command'][1])['sha256']==job['entrypoint_sha256'],'Frozen job source mismatch')
    prefixes=[r['source'] for r in rows if Path(r['source']['path']).name in
              ('formal_efficiency_component.stdout.log','formal_efficiency_component.stderr.log')]
    c.require(len(prefixes)==2 and sorted(r['bytes'] for r in prefixes)==[0,2387],'Closed original append logs')
    seed=c.derive_seed(original,c.read(recovery_path),capture)
    c.validate_seed(seed,original,c.read(recovery_path),capture)
    write(HERE/'captured_pipeline_status.json',original_bytes)
    write(HERE/'pipeline_seed.json',c.encoded(seed))
    diff=''.join(difflib.unified_diff(original_bytes.decode('utf-8-sig').splitlines(True),
             c.encoded(seed).decode('utf-8').splitlines(True),fromfile='captured original failed pipeline_status.json',
             tofile='preparation-only pipeline_seed.json'))
    write(HERE/'PIPELINE_STATE_DERIVATION.patch',diff.encode('utf-8'))
    contract={'schema':'t6-pipeline-recovery-contract.v1','prepared_utc':c.utc(),
      'incident_capture':capture,'recovery_spec':recovery,'input_bindings':list(inputs.values()),
      'host_boot_utc':captured['host_boot_utc'],'host_boot_utc_ticks':boot_ticks,
      'live_state_bindings':state_rows,'append_log_prefixes':prefixes,
      'primary_controller_pid':c.read(EX/'status.json')['controller_pid'],
      'candidate_scope':'pipeline only, original seventh stage; no primary or successors',
      'first_six_exact_records_preserved':seed['jobs'][:6]==original['jobs'][:6],
      'scientific_execution_performed':False,'release_created':False,
      'known_prerequisite':'latest_baseline_gpu.lock does not currently exist; separately reviewed initialization is required',
      'predecessor_output_acceptance_roots':[c.binding(p) for p in roots],
      'limits':['Preparation does not establish GPU exclusivity, memory admission, native runtime, launch or scientific completion.',
                'All old scientific acceptance limits are inherited; no weight/cache/image contents or old large artifacts rehashed.',
                'Old numerical PID absence cannot manufacture original interpreter identities or exit codes.']}
    write(HERE/'RECOVERY_CONTRACT.json',c.encoded(contract))
    print(json.dumps({'input_bindings':len(inputs),'contract':c.binding(HERE/'RECOVERY_CONTRACT.json'),
                      'seed':c.binding(HERE/'pipeline_seed.json'),'diff':c.binding(HERE/'PIPELINE_STATE_DERIVATION.patch')},ensure_ascii=False))

if __name__=='__main__':main()
