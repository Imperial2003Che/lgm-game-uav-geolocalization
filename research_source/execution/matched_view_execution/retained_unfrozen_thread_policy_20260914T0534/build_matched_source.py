"""Construct an auditable standalone two-view derivative; standard library only."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
SOURCE = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\lgm_game_pytorch\formal_retrieval.py')
SOURCE_SHA = '081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862'
TARGET = HERE / 'formal_retrieval_two_view.py'


def derive():
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise RuntimeError('Original frozen formal source differs')
    text = raw.decode('utf-8-sig')
    before = text
    condition = 'record.role in {"train_drone", "train_street"}'
    if text.count(condition) != 2:
        raise RuntimeError('Expected exactly two University training-role conditions')
    text = text.replace(condition, 'record.role == "train_drone"')
    guard = '''    if dataset != "university1652" or val_fraction != 0:
        raise RuntimeError("This independent control admits University two-view final-fit training only.")
'''
    text = text.replace(') -> TrainingProtocol:\n', ') -> TrainingProtocol:\n' + guard, 1)
    metadata = '''    if (len(train_queries), sum(map(len, train_gallery.values())), len(train_ids)) != (37854, 701, 701):
        raise RuntimeError("The reviewed two-view training membership changed.")
    if canonical_sha256(train_ids) != "7b2528d2920f7062f337b884825dd2de1de967810cac67ec516b10e5f995057e":
        raise RuntimeError("The 701 training identity list changed.")
    if validation_ids or any(record.role != "train_drone" for record in train_queries):
        raise RuntimeError("Unexpected query role or validation identity in two-view training.")
    summary.update(comparison_family="university_two_view_matched_v1",
                   training_query_roles=["train_drone"], positive_gallery_role="train_satellite",
                   parent_training_query_roles=["train_drone", "train_street"], removed_street_queries=2659)
'''
    text = text.replace('    return TrainingProtocol(\n', metadata + '    return TrainingProtocol(\n', 1)
    marker = '    tasks = build_official_evaluation_tasks(records, dataset, sues_train_ids)\n'
    if text.count(marker) != 1:
        raise RuntimeError('Unexpected evaluation task construction')
    evaluation = '''    if dataset != "university1652":
        raise RuntimeError("This control evaluates University UAV/satellite directions only.")
    expected = {"university1652_drone_to_satellite": (37855, 951),
                "university1652_satellite_to_drone": (701, 51355)}
    tasks = [task for task in tasks if task.name in expected]
    if [task.name for task in tasks] != list(expected):
        raise RuntimeError("Missing or reordered two-direction official evaluation task.")
    for task in tasks:
        if (len(task.query), len(task.gallery)) != expected[task.name]:
            raise RuntimeError("Full query/gallery count differs from the reviewed protocol.")
        query_ids = {record.label for record in task.query}
        gallery_ids = {record.label for record in task.gallery}
        if (len(query_ids), len(gallery_ids), len(gallery_ids - query_ids)) != (701, 951, 250):
            raise RuntimeError("Official gallery distractors were changed or removed.")
'''
    text = text.replace(marker, marker + evaluation)
    # This admission guard is before all scientific imports and runs in spawned
    # DataLoader workers as well. Only the reviewed wrapper creates its lease.
    text = text.replace('import numpy as np\n',
                        'from matched_runtime import child_gate\nchild_gate()\n\nimport numpy as np\n', 1)
    original = ast.parse(before)
    changed = ast.parse(text)
    nodes_before = {n.name: n for n in original.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    nodes_after = {n.name: n for n in changed.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    differences = [name for name in nodes_before
                   if ast.dump(nodes_before[name], include_attributes=False) != ast.dump(nodes_after[name], include_attributes=False)]
    if differences != ['build_training_protocol', 'run_evaluate']:
        raise RuntimeError('Unexpected changed algorithm definitions: ' + repr(differences))
    return text, ''.join(difflib.unified_diff(before.splitlines(True), text.splitlines(True),
                        fromfile='frozen/formal_retrieval.py', tofile='independent/formal_retrieval_two_view.py')), differences


def main():
    text, diff, changes = derive()
    if TARGET.exists() and TARGET.read_text(encoding='utf-8') != text:
        raise RuntimeError('Existing derivative differs; preserve it before an explicitly reviewed revision')
    HERE.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding='utf-8', newline='\n')
    (HERE / 'formal_two_view.patch').write_text(diff, encoding='utf-8', newline='\n')
    print(json.dumps({'status':'derived_not_executed', 'source_sha256':SOURCE_SHA,
                      'derived_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),
                      'changed_functions':changes, 'scientific_imports':False}))


if __name__ == '__main__':
    main()
