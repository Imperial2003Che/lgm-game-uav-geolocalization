"""Preserve failed first annex verbatim; create only same-file path fix v2."""
from pathlib import Path
import difflib
import hashlib
import json

root = Path(__file__).resolve().parent
source = root / 'review_adopted_aggregate_inputs.py'
before = source.read_text(encoding='utf-8')
after = before.replace('import json\n', 'import json\nimport os\n', 1)
after = after.replace("OUT = HERE / 'adopted_inputs'", "OUT = HERE / 'adopted_inputs_v2'", 1)
after = after.replace("    run_reports = []\n", "    run_reports = []\n    alias_checks = []\n", 1)
old = """        production_manifest = index[norm(declared['path'])]
        require(production_manifest['sha256'] == declared['sha256'] == digest(manifest_raw) and
                production_manifest['bytes'] == len(manifest_raw), 'original path and snapshot manifest binding')"""
new = """        declared_path = Path(declared['path'])
        expected_declared = Path(r'C:\项目\LGM\02_代码与实验\正式实验工程\lgm_game_pytorch\runs\formal_robustness') / dataset / variant / 'seed_1/robustness_manifest.json'
        expected_alias = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_robustness') / dataset / variant / 'seed_1/robustness_manifest.json'
        require(norm(declared_path) == norm(expected_declared), 'exact producer manifest path')
        production_manifest = index[norm(expected_alias)]
        require(os.path.samefile(declared_path, expected_alias), 'junction alias must be same file, not same bytes')
        alias_checks.append({'declared_path': str(declared_path), 'adopted_original_path': str(expected_alias),
                             'actual_samefile': True, 'current_bytes_rehashed': False})
        require(production_manifest['sha256'] == declared['sha256'] == digest(manifest_raw) and
                production_manifest['bytes'] == len(manifest_raw), 'original path and snapshot manifest binding')"""
assert before.count(old) == 1
after = after.replace(old, new, 1)
after = after.replace("'input_bindings': BINDINGS, 'prior_official_input_authority_mandatory_gate': authority,",
    "'input_bindings': BINDINGS, 'actual_junction_identity_checks': alias_checks,\n        'prior_official_input_authority_mandatory_gate': authority,", 1)
target = root / 'review_adopted_aggregate_inputs_v2.py'
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(after)
with (root / 'ANNEX_V2_FROM_REJECTED_V1.patch').open('x', encoding='utf-8', newline='\n') as stream:
    stream.writelines(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile=source.name, tofile=target.name))
record = {'reason': 'V1 direct path lookup rejected the existing same-file junction alias before numerical reconciliation; no scientific failure.',
    'v1_source': {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
    'v2_source': {'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()},
    'retained_first_execution': ['first_annex.stdout.log', 'first_annex.stderr.log', 'adopted_inputs/'],
    'change': 'Only fixed exact producer-to-adopted alias path with os.path.samefile, new output location and explicit alias record.'}
with (root / 'ANNEX_PREPARATION_REJECTION.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2); stream.write('\n')
print(json.dumps(record))
