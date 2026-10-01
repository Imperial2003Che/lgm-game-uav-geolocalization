"""Derive only DAC's normal University training import closure using stdlib."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'literature/official_repos/snapshots/SummerpanKing__DAC__5612a79c3928'
TARGET = HERE / 'scientific_source'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def subset(relative, keep_definitions, keep_import):
    original = (SOURCE / relative).read_text(encoding='utf-8')
    tree = ast.parse(original)
    kept = [node for node in tree.body if
        (isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in keep_definitions)
        or (isinstance(node, (ast.Import, ast.ImportFrom)) and keep_import(node))]
    output = '\n\n'.join(ast.get_source_segment(original, node) for node in kept) + '\n'
    generated = ast.parse(output)
    expected = {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in keep_definitions}
    actual = {n.name: ast.dump(n, include_attributes=False) for n in generated.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    if actual != expected:
        raise RuntimeError('Executable scientific AST changed: ' + relative)
    destination = TARGET / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(output, encoding='utf-8', newline='\n')
    diff = ''.join(difflib.unified_diff(original.splitlines(True), output.splitlines(True),
        fromfile='DAC-official/' + relative, tofile='DAC-train-only/' + relative))
    (HERE / (Path(relative).stem + '_training_subset.patch')).write_text(diff, encoding='utf-8')
    return {'path': relative, 'original_sha256': sha(SOURCE / relative), 'derived_sha256': sha(destination),
        'definitions_preserved_exact_ast': sorted(expected), 'change': 'Remove unused evaluation/weather definitions and imports only'}

def main():
    pin = json.loads((HERE / 'SOURCE_PIN.json').read_text(encoding='utf-8'))
    for row in pin['files']:
        if sha(SOURCE / row['path']) != row['sha256']:
            raise RuntimeError('Official DAC source changed: ' + row['path'])
    selected = [r['path'] for r in pin['files'] if
        r['path'].startswith(('sample4geo/hand_convnext/', 'sample4geo/Utils/')) or
        r['path'] in {'sample4geo/utils.py', 'sample4geo/loss/__init__.py', 'sample4geo/loss/loss.py',
                     'sample4geo/loss/triplet_loss.py', 'sample4geo/loss/blocks_infoNCE.py',
                     'sample4geo/loss/DSA_loss.py', 'sample4geo/loss/cal_loss.py', 'LICENSE'}]
    rows = []
    for relative in selected:
        target = TARGET / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, target)
        rows.append({'path': relative, 'original_sha256': sha(SOURCE / relative), 'derived_sha256': sha(target), 'change': 'byte-identical'})
    def normal_import(node):
        text = ast.unparse(node)
        return 'imgaug' not in text and 'ImageOnlyTransform' not in text
    rows.append(subset('sample4geo/dataset/university.py', {'get_data', 'U1652DatasetTrain', 'get_transforms'}, normal_import))
    rows.append(subset('sample4geo/trainer.py', {'train'}, lambda node: True))
    report = {'schema': 'dac-training-scientific-source.v1', 'official_commit': pin['commit_sha'],
        'source_root': str(SOURCE), 'derived_root': str(TARGET), 'files': rows,
        'model_source': 'Official DAC only; DSA projection and three classifier heads preserved',
        'model_state_count_required': 402, 'scientific_imports_executed': False}
    (HERE / 'SCIENTIFIC_SOURCE_MANIFEST.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    meta_path = HERE.parent / 'dac_preparation/strict_meta_compatibility.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    tensors = {row['key']: {'shape': row['shape'], 'dtype': row['dtype']} for row in meta['tensor_comparisons']}
    if len(tensors) != 402 or not all(row['matches'] for row in meta['tensor_comparisons']):
        raise RuntimeError('The existing DAC schema evidence is not complete')
    (HERE / 'DAC_EXPECTED_MODEL_SCHEMA.json').write_text(json.dumps({'schema': 'dac-university-model-schema.v1',
        'source_report_path': str(meta_path), 'source_report_sha256': sha(meta_path),
        'provenance': 'Existing author-checkpoint schema inspection only; no author tensor values or weights reused for initialization',
        'tensor_count': 402, 'tensors': tensors, 'this_preparation_ran_model': False}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'copied_or_derived_files': len(rows), 'DAC_state_schema': len(tensors), 'scientific_imports': False}))

if __name__ == '__main__':
    main()
