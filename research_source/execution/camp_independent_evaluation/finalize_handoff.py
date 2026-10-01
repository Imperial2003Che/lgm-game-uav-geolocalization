"""Write only handoff metadata; never register a queue or invoke experiments."""
from pathlib import Path
import json
from protocol import *
from run_evaluation import read_prepared

path=HERE/'preparations/frozen_three_seed_final_v2/manifest.json'
prepared=read_prepared(path)
if sha(path)!='318c96493396d01d75866751c99c794d984db0ef989c22a6b7ccbe1fa96da02e':raise RuntimeError('Final prepared contract differs')
template={'schema':CONTROLLER_RELEASE_SCHEMA,'allow_cuda':False,'prepared_sha256':sha(path),
          'latest_baseline_plan_sha256':prepared['latest_baseline_plan']['sha256'],
          'training_execution_plan_sha256':prepared['training_execution_plan']['sha256'],
          'binding_policy':BINDING_POLICY,'seeds':list(SEEDS),'task_count':30}
save(HERE/'controller_release_template.json',template)
source_paths=[Path(item['path']) for item in prepared['sources']['files']]
source_paths.extend([path,Path(prepared['training_execution_plan']['path']),Path(prepared['latest_baseline_plan']['path'])])
source_paths.extend(Path(item['plan']['path']) for item in prepared['training_plans'])
source_paths.extend(Path(prepared['membership'][key]['path']) for key in ('source_manifest','inventory','tasks'))
source_paths.extend([HERE/'check_lightweight.py',HERE/'LIGHTWEIGHT_REVIEW.json'])
command=[prepared['python'],'-B',str(HERE/'run_evaluation.py'),'run','--prepared',str(path),
         '--training-completion',str(EXECUTION/'camp_training_execution/status.json'),
         '--controller-release',str(HERE/'controller_release.json'),
         '--output-directory',str(HERE/'runs/registered_three_seed_final')]
job={'id':'camp_independent_3seed_full_gallery_30tasks','command':command,'cwd':str(HERE),
     'source_sha256':{str(p.resolve()):sha(p) for p in source_paths}}
handoff={'schema':'camp-independent-evaluation-handoff.v1','status':'prepared_not_registered','created_utc':utc(),
         'prepared':artifact(path),'job':job,'missing_release_to_create_and_pin':str(HERE/'controller_release.json'),
         'template':artifact(HERE/'controller_release_template.json'),
         'checkpoint_hashes':'No future weight hashes assigned; run computes actual files only after all three completed training runs and exited owners are verified',
         'execution_gate':'After both latest author jobs and three independent training jobs complete and every prior owner exits',
         'scientific_imports_during_preparation':[],'GPU_executed':False,'evaluation_results_created':False}
save(HERE/'QUEUE_HANDOFF.json',handoff)
save(HERE/'preparations/frozen_three_seed_final/SUPERSEDED_NOTE.json',{
    'status':'superseded_before_registration','original_manifest_sha256':'8b6135e4a56ea4d14109f252ab79d4e6f1a37a5503764cc69960f54a841a91cd',
    'replacement':artifact(path),'reason':'Complete/end verification strengthened from tensor-value equality to uint8 byte equality; prepared again without overwriting earlier evidence.'})
names=('protocol.py','camp_independent_model.py','run_evaluation.py','check_lightweight.py','review_outer_supervisor.py',
       'finalize_handoff.py','README.md','LIGHTWEIGHT_REVIEW.json','OUTER_SUPERVISOR_REVIEW_0b4678df15c4.json',
       'controller_release_template.json','QUEUE_HANDOFF.json')
freeze=seal({'schema':'camp-independent-evaluation-source-freeze.v1','created_utc':utc(),'status':'prepared_not_registered',
             'files':[artifact(HERE/name) for name in names],'prepared':artifact(path),
             'source_evidence':source_evidence(),'check_count':53,'scientific_imports':[],'GPU_executed':False})
save(HERE/'PREPARATION_MANIFEST.json',freeze)
print(json.dumps({'prepared_sha256':sha(path),'handoff_sha256':sha(HERE/'QUEUE_HANDOFF.json'),
                  'preparation_manifest_sha256':sha(HERE/'PREPARATION_MANIFEST.json'),
                  'source_sha256':{name:sha(HERE/name) for name in ('protocol.py','camp_independent_model.py','run_evaluation.py')}}))
