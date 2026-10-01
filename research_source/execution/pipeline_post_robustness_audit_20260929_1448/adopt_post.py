"""Root bounded adoption of two new pipeline outputs; no scientific execution."""
import argparse, datetime, difflib, hashlib, json, os
from pathlib import Path

HERE=Path(__file__).resolve().parent
EX=HERE.parent
BINDINGS={}
def require(v, why):
    if not v: raise AssertionError(why)
def norm(p): return str(Path(p)).replace('/', '\\').casefold()
def bind(p, sha=None, size=None):
    p=Path(p)
    require(p.suffix.lower() not in ('.pt','.pth','.jpg','.jpeg','.npy'), 'forbidden scientific inputs')
    if p.suffix.lower()=='.png':
        require(any(p.is_relative_to(base) for base in (HERE/'a1/aggregate', Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\results\formal_robustness_aggregate'),Path(r'C:\项目\LGM\02_代码与实验\正式实验工程\lgm_game_pytorch\results\formal_robustness_aggregate'))), 'PNG only new aggregate figure artifacts')
    k=norm(p)
    if k in BINDINGS:
        rec=BINDINGS[k]
        require(sha is None or rec['sha256']==sha, 'conflicting SHA')
        require(size is None or rec['bytes']==size, 'conflicting size')
        return rec
    raw=p.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    require(sha is None or digest==sha, f'SHA {p}')
    require(size is None or len(raw)==size, f'size {p}')
    rec={'path':str(p),'sha256':digest,'bytes':len(raw)}; BINDINGS[k]=rec
    return rec
def desc(d, snapshot=False):
    return bind(d['snapshot'] if snapshot else d['path'], d['sha256'], d.get('bytes'))
def read(p, sha=None):
    bind(p,sha)
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def walk_bind(v):
    if isinstance(v,dict):
        if 'path' in v and 'sha256' in v: desc(v)
        for x in v.values(): walk_bind(x)
    elif isinstance(v,list):
        for x in v: walk_bind(x)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--observation',type=Path,required=True); ap.add_argument('--observation-sha',required=True); args=ap.parse_args()
    delivery=read(HERE/'DELIVERY.json','bbf6eb2a77cab73fe20cb4703bdc4dcafecb3a94bcd474971bfe49f629018e42')
    walk_bind(delivery)
    manifest=read(delivery['manifest']['path'])
    for d in manifest['actual_small_file_bindings']: desc(d)
    review=read(delivery['main_review']['path'])
    annex=read(delivery['annex_review']['path'])
    capture=read(delivery['capture']['path'])
    require(review['passed_with_stated_limits'] is True and annex['passed'] is True, 'joint passed reports')
    require(annex['aggregate_SUES_Full_input_adoption_pending'] is False, 'four-run input reconciliation')
    authority=review['query']['source_authority']
    require(authority['exact_input_path_sha_size_bindings']==66 and authority['not_directly_found']==[] and authority['all_12_run_identifiers_adopted'] is True, 'mandatory official authority')
    require(authority==annex['prior_official_input_authority_mandatory_gate'], 'annex authority equality')
    require(manifest['raw_snapshot_bindings_inherited_without_rehash']==capture['bindings'], 'capture descriptor equality')
    npz=0; new_originals=0
    for d in capture['bindings']:
        desc(d,True)
        if Path(d['path']).suffix.lower()=='.npz':
            # Audit uses this authorized subset for new query arithmetic; do not reread originals here.
            require(Path(d['snapshot']).is_relative_to(HERE/'a1'), 'sealed NPZ only')
            npz+=1
        else:
            desc(d); new_originals+=1
    require(npz==66 and len(capture['bindings'])==184, 'explicit bounded capture')
    for d in review['metadata_chain_additions']: desc(d); desc(d,True)
    for d in annex['input_bindings']:
        desc(d)
        if 'snapshot' in d: desc(d,True)
    require(len(annex['input_bindings'])==141 and len(annex['run_reports'])==4, 'four-run annex bindings')
    require(annex['metric_files']==124 and annex['clean_task_records']==22 and annex['corrupt_task_records']==660, 'adopted aggregate totals')
    expected={('university1652','visual'):'81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6',('university1652','full'):'ea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5',('sues200','visual'):'a6795283cb384c77732bdb1e63af93d582d7844879f415e45ef38c8861d3af74',('sues200','full'):'abe0d740103c44792f134ac69816030e40947170f2c245c0e6e37efda0190596'}
    require({(r['dataset'],r['variant']):r['root_sha256'] for r in annex['run_reports']}==expected, 'four exact root authorities')
    for r in annex['run_reports']:
        root=read(r['root'],r['root_sha256']); require(root['accepted_with_stated_limits'] is True,'accepted source root')
    for d in annex['actual_junction_identity_checks']:
        require(d['actual_samefile'] is True and os.path.samefile(d['declared_path'],d['adopted_original_path']), 'actual samefile junction identity')
    require(len(annex['actual_junction_identity_checks'])==4,'four alias identities')
    # Exact readable diff reconstruction, without executing any review or preparation source.
    old=HERE/'review_adopted_aggregate_inputs.py'; new=HERE/'review_adopted_aggregate_inputs_v2.py'
    diff=''.join(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),new.read_text(encoding='utf-8').splitlines(True),fromfile=old.name,tofile=new.name))
    require(diff==(HERE/'ANNEX_V2_FROM_REJECTED_V1.patch').read_text(encoding='utf-8'), 'exact annex diff')
    static=read(delivery['static_review']['path']); require(static['blocking_findings']==[], 'static findings')
    for d in static['source_and_small_file_bindings']: desc(d)
    observation=read(args.observation,args.observation_sha)
    require(observation['first_CIM']['records']==observation['second_CIM']['records']==[], 'fresh stopped process context')
    require(observation['t6_output_exists'] is False and observation['scientific_or_recovery_execution'] is False, 'no T6/recovery execution')
    for r in observation['states']:
        require(r['unchanged_since_incident'] is True,'stable incident state'); desc(r['source']); desc(r['snapshot'])
    walk_bind(observation['source']); walk_bind(observation['gpu_query'])
    state=read(EX/'pipeline_status.json','47fd31336b8e742da91891a87c28a0767989cb45c375aeb000854f50e37acf12')
    jobs={r['id']:r for r in state['jobs']}
    for key,record in review['parent_stage_records'].items():
        require(jobs[key]==record and record['status']=='completed' and record['exit_code']==0, 'exact original parent job record')
        bind(record['command'][1],record['entrypoint_sha256'])
    require(sum(r['status']=='completed' for r in state['jobs'])==6 and jobs['formal_efficiency_component']['status']=='failed', 'actual six completed and T6 failed')
    require(review['aggregate']['rows']==3960 and review['aggregate']['new_artifacts']==94 and review['aggregate']['figure_groups']==22,'aggregate scope')
    require(review['query']['T4_rows']==462 and review['query']['T4_margin_strata_recomputed']==132 and review['query']['T5_native_query_recomputed']==66 and review['query']['T5_paired_query_recomputed']==132,'query scope')
    require(review['query']['T4_other_strata_membership_and_values_recomputed'] is False and review['query']['bootstrap_CI_recomputed'] is False,'bounded query scope')
    source=bind(__file__)
    result={'schema':'root-post-robustness-bounded-adoption.v1','time':datetime.datetime.now().astimezone().isoformat(),'accepted_with_stated_limits':True,'source':source,'joint_independent_delivery':delivery['main_review'],'delivery':bind(HERE/'DELIVERY.json'),'mandatory_annex':delivery['annex_review'],'root_review_scope':'Complete independent main/annex source, complete annex diff, original aggregate source and query primitive/runner relevant scientific blocks, independent contract static review; actual bindings below. No independent audit or producer re-execution.', 'unique_files_checked':len(BINDINGS),'bindings':list(BINDINGS.values()),'sealed_official_npz_subset_checked':66,'old_official_original_npz_rehashed_by_root':0,'new_original_capture_files_checked':new_originals,'aggregate':review['aggregate'],'query':review['query'],'adopted_aggregate_input_roots':annex['run_reports'],'parent_stage_records':review['parent_stage_records'],'observation':bind(args.observation),'pipeline_jobs_bounded_artifact_review_accepted':6,'pipeline_jobs_total':7,'T6_completed':False,'limits':list(dict.fromkeys(annex['limits']+review['limits']+review['query']['limits']+['Original parent job exit0 plus later absence is not independent launcher/interpreter dual-handle exit proof. Primary own exit remains unknown.','Pipeline count denotes bounded artifact review; bootstrap CIs and non-margin T4 memberships remain producer-only evidence.','No scientific, recovery, live-state or automation mutation in this adoption.']))}
    out=HERE/'ROOT_POST_ROBUSTNESS_ADOPTION.json'
    with out.open('x',encoding='utf-8',newline='\n') as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps({'report':bind(out),'unique_files':result['unique_files_checked'],'pipeline_bounded_review':'6/7','T6_completed':False}))
if __name__=='__main__': main()
