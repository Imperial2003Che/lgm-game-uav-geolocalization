"""Freeze only already-existing scientific and input sources, no execution."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;EX=HERE.parent
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=set()
for dirname,manifest in [('dac_training_preparation_v1','PREPARATION_MANIFEST.json'),('dac_training_control_v2','PREPARATION_MANIFEST.json'),('dac_training_inputs_v2','INPUT_PREPARATION_MANIFEST.json')]:
    folder=EX/dirname;files.add(folder/manifest)
    data=read(folder/manifest)
    for row in data['files']:
        path=folder/row['path'];assert path.is_file() and sha(path)==row['sha256'];files.add(path)
author=EX/'dac_preparation'
for name in ('run_dac_author_evaluation.py','dac_model.py','SOURCE_SHA256.json','source_pins.json','preparations/20260914T045232800767Z/manifest.json'):
    files.add(author/name)
official=read(author/'SOURCE_SHA256.json')
for rel,digest in official['files'].items():
    p=Path(official['repository'])/rel;assert sha(p)==digest;files.add(p)
import ast
node=ast.parse((author/'run_dac_author_evaluation.py').read_text('utf-8'))
namespace={'Path':Path};selected=[]
for n in node.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ROOT','CORE','SPLIT','CORE_SHA','SPLIT_SHA') for t in n.targets):selected.append(n)
exec(compile(ast.Module(body=selected,type_ignores=[]),'pinned-path-constants-only','exec'),namespace)
for key in ('CORE','SPLIT'):
    p=namespace[key];assert sha(p)==namespace[key+'_SHA'];files.add(p)
data={'schema':'dac-independent-evaluation-source-pins.v1','files':{str(p.resolve()):sha(p) for p in sorted(files)},'no_author_checkpoint_values_bound':True,'no_training_final_checkpoint_exists_or_bound':True,'scope':'Pinned existing sources and frozen input plans; future execution package/spec are separately externally SHA-admitted at prepare.'}
(HERE/'SOURCE_PINS.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'file_count':len(files),'source_pins_sha256':sha(HERE/'SOURCE_PINS.json')}))
