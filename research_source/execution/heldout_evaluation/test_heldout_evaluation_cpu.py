"""CPU-only protocol and arithmetic tests; fixtures never become experiment output."""
from pathlib import Path
import ast
from collections import defaultdict
import dataclasses
import importlib.util
import io
import json
import math
import sys
from types import SimpleNamespace
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('t2_eval_review',HERE/'run_heldout_evaluation.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
args=r.parse_args(['--stage','plan','--scope','all'])
r.pinned_sources(args)
matrix=r.load(args.delivery_root/'lgm_game_pytorch/experiments/transactions_t2_heldout_matrix.json')
try:r.pre_gate_presence(SimpleNamespace(delivery_root=HERE/'never_created_test_fixture'),matrix)
except RuntimeError as exc:assert '24 pending' in str(exc)
else:raise AssertionError('Missing T2 fits passed the pre-import gate')
source=args.delivery_root/'lgm_game_pytorch/lgm_game_pytorch/formal_retrieval.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
# Execute only these actual pure-Python/NumPy functions, never importing torch.
names={'EvidenceRecord','RetrievalTask','_group_by_label','_assert_task',
       'build_official_evaluation_tasks','rank_task','official_trapezoid_ap'}
nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
nodes.insert(0,ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0))
module=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]))
namespace={'dataclass':dataclasses.dataclass,'defaultdict':defaultdict,'np':np,'math':math,
           'SUES_ALTITUDES':r.HEIGHTS,'__name__':__name__}
exec(compile(module,str(source),'exec'),namespace)
Record=namespace['EvidenceRecord'];Task=namespace['RetrievalTask']
assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUES_OFFICIAL_TRAIN_IDS' for t in n.targets))
train_ids=ast.literal_eval(assignment.value)
records=[]
for identity in range(1,201):
    label=f'{identity:04d}'
    records.append(Record(len(records),f'satellite/{label}.jpg',Path('unopened'),label,'all','satellite','satellite_all',''))
    for height in r.HEIGHTS:
        for index in range(50):
            records.append(Record(len(records),f'uav/{height}/{label}/{index:03d}.jpg',Path('unopened'),label,'all','drone','drone_all',height))
tasks=namespace['build_official_evaluation_tasks'](records,'sues200',train_ids)
for height in r.HEIGHTS:
    assert len(r.select_tasks(tasks,height,'all',train_ids))==8
    selected=r.select_tasks(tasks,height,'heldout',train_ids)
    assert len(selected)==2 and all(r.task_height(t.name)==height for t in selected)
    assert [(len(t.query),len(t.gallery)) for t in selected]==[(4000,200),(80,10000)]
    assert all(len({x.label for x in t.gallery})==200 for t in selected)
# Deliberate removal of distractors and wrong heights must fail the gate.
bad=[dataclasses.replace(tasks[0],gallery=tuple(x for x in tasks[0].gallery if x.label not in train_ids))]+tasks[1:]
try:r.select_tasks(bad,'150','all',train_ids)
except RuntimeError:pass
else:raise AssertionError('Truncated gallery accepted')

# Exact frozen ranking and AP arithmetic on in-memory toy descriptors.
# No NPZ is written to the filesystem and no scientific result is generated.
def rec(path,label,view):return Record(0,path,Path('unopened'),label,'test',view,view,'150')
query=(rec('q/a','a','drone'),rec('q/b','b','drone'))
gallery=(rec('g/a1','a','satellite'),rec('g/b','b','satellite'),rec('g/a2','a','satellite'))
task=Task('unit_fixture',query,gallery,'unit test only')
encoded={'q/a':np.array([1.,0.],np.float32),'q/b':np.array([.8,.6],np.float32),
         'g/a1':np.array([1.,0.],np.float32),'g/b':np.array([0.,1.],np.float32),'g/a2':np.array([-1.,0.],np.float32)}
metrics,arrays=namespace['rank_task'](task,encoded,1)
stream=io.BytesIO();np.savez_compressed(stream,**arrays);stream.seek(0)
derived=r.read_query_metrics(stream,task)
for key,value in derived.items():assert abs(metrics[key]-value)<2e-7,(key,value)
assert abs(namespace['official_trapezoid_ap'](np.array([0,2]))-19/24)<1e-12
altered={**arrays,'query_paths':arrays['query_paths'][::-1]}
stream=io.BytesIO();np.savez_compressed(stream,**altered);stream.seek(0)
try:r.read_query_metrics(stream,task)
except RuntimeError:pass
else:raise AssertionError('Reordered query output accepted')

rows=[]
for seed,value in [(1,.1),(2,.2),(3,.3)]:
    rows.append({'heldout_altitude_m':'150','variant':'visual','seed':seed,'task':'sues200_uav_150m_to_satellite','queries':4000,'gallery':200,**dict.fromkeys(r.METRICS,value)})
summary=r.aggregate(rows)[0]
assert abs(summary['r_at_1_mean']-.2)<1e-12 and abs(summary['r_at_1_sd']-.1)<1e-12
assert summary['evaluation_height_role']=='heldout'
seen=r.aggregate([{**x,'task':'sues200_uav_200m_to_satellite'} for x in rows])[0]
assert seen['evaluation_height_role']=='seen'
try:r.aggregate(rows[:2])
except RuntimeError:pass
else:raise AssertionError('Incomplete seed aggregation accepted')
try:r.aggregate([rows[0],rows[0],rows[2]])
except RuntimeError:pass
else:raise AssertionError('Duplicate seed aggregation accepted')
sealed=r.sealed({'x':1});r.validate_seal(sealed)
try:r.validate_seal({**sealed,'x':2})
except RuntimeError:pass
else:raise AssertionError('Tampered manifest accepted')
assert 'torch' not in sys.modules
report={'status':'passed','scope':'Pure CPU task-membership and NumPy arithmetic tests; no model, checkpoint, GPU or real experiment output',
        'checks':['Seven original source pins','24-fit pre-import missing-prerequisite gate','Actual original SUES task builder gives 4000/200 and 80/10000 with all 200 gallery IDs',
                  'All four heldout and all-height selections','Truncated gallery rejection','Exact frozen ranking/AP parity',
                  'Query ordering corruption rejection','Three-seed sample SD and separate seen/heldout labels',
                  'Missing/duplicate seed rejection','Manifest tamper rejection','Torch never imported'],
        'new_runner_sha256':r.sha(HERE/'run_heldout_evaluation.py'),'source_core_sha256':r.sha(source)}
r.save(HERE/'cpu_validation.json',report)
print(json.dumps(report,indent=2))
