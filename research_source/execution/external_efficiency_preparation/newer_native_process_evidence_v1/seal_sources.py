"""Create source-only review inputs; AST parsing only, never import candidate code."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
NAMES = ('windows_process_evidence.py', 'benign_fixture.py', 'README.md')


def record(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(name, value):
    with (HERE / name).open('xb') as f:
        f.write((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def main():
    assert not (HERE / 'runtime_attempt_v1').exists(), 'Actual attempt exists; this sealer is source-only'
    changes = []
    parsed = []
    for name in NAMES:
        old = (HERE / 'draft_before_independent_fixes' / name).read_bytes()
        new = (HERE / name).read_bytes()
        # splitlines(keepends=True) on decoded bytes preserves actual line endings.
        changes.extend(difflib.unified_diff(old.decode('utf-8').splitlines(keepends=True),
                                           new.decode('utf-8').splitlines(keepends=True),
                                           fromfile='draft_before_independent_fixes/' + name,
                                           tofile=name))
        if name.endswith('.py'):
            ast.parse(new.decode('utf-8'), filename=name)
            parsed.append(name)
    diff = ''.join(changes).encode('utf-8')
    with (HERE / 'COMPLETE_DIFF_FROM_PRESERVED_DRAFT.patch').open('xb') as f:
        f.write(diff)
    predecessor = HERE.parent / 'newer_native_b1_worker_v1'
    closed_source = record(predecessor / 'reference_worker.py')
    assert closed_source['sha256'] == 'eed9b25b1204edbcf5172ea2fb24e272b7ff39103f98448e554a3dae779b7f46'
    context = [closed_source, record(predecessor / 'README.md'),
               record(predecessor / 'SOURCE_MANIFEST.json'), record(predecessor / 'ROOT_SOURCE_ADOPTION.json')]
    write('REVIEW_INPUTS.json', {
        'schema': 'newer-native-process-evidence-source-inputs.v1',
        'created_unix_ns': time.time_ns(), 'scope': 'Candidate read/synchronize helper and ordinary Python311 benign CPU fixture; no execution',
        'scientific_predecessor_context': context,
        'candidate_sources': [record(HERE / name) for name in NAMES],
        'preserved_pre_fix_snapshot': [record(HERE / 'draft_before_independent_fixes' / name) for name in NAMES],
        'diff': record(HERE / 'COMPLETE_DIFF_FROM_PRESERVED_DRAFT.patch'),
        'snapshot_limit': 'Preserved snapshot precedes the independent catch-code/alignment fixes, but already contains the earlier unsealed epoch and case-name edits. It is not claimed to preserve every earlier in-progress version.',
        'changed_after_snapshot': ['Reset child/launcher exception return intentions to 92/93',
                                   'Validate UTF16 pointer alignment before dereference',
                                   'Close transferred fd if fdopen fails',
                                   'Reject empty/invalid image path length',
                                   'Clarify README exception/closure/scope wording and spacing'],
        'syntax_only': {'ast_parsed': parsed, 'candidate_imported': False, 'candidate_executed': False,
                        'windows_api_called': False, 'fixture_launched': False},
        'required_independent_review': ['Nt class60 status/length/evenness/alignment/buffer bounds and current-host-only scope',
                                        'Actual held creation identity, current parentage scope, complete command lines',
                                        'Wait signaled before actual DWORD exit; integer FILETIME versus .NET epochs',
                                        'Closed-stream hashing, failure and resource closure branches',
                                        'Two benign cases, ACK before task, isolated ordinary Python and separate Popen handle scope'],
        'execution_released': False, 'runtime_validated': False,
        'scientific_admission': False, 'runtime_attempt_absent_observed': True,
        'no_old_control_or_scientific_suite_run': True,
        'old_B1_gates_unmodified': True,
        'remaining_scientific_requirements': 'Current boot/release/resource/shared locks and real predecessor exits; six scientific workers and fresh ranking/T6 remain separate, unresolved requirements.'})
    members = [HERE / n for n in NAMES] + [HERE / 'seal_sources.py', HERE / 'REVIEW_INPUTS.json',
               HERE / 'COMPLETE_DIFF_FROM_PRESERVED_DRAFT.patch']
    members += [HERE / 'draft_before_independent_fixes' / n for n in NAMES]
    write('SOURCE_MANIFEST.json', {'schema': 'newer-native-process-evidence-source-manifest.v1',
                                  'source_prepared': True, 'execution_released': False,
                                  'runtime_validated': False, 'scientific_admission': False,
                                  'files': [record(p) for p in members]})
    write('DELIVERY.json', {'schema': 'newer-native-process-evidence-source-delivery.v1',
                           'source_manifest': record(HERE / 'SOURCE_MANIFEST.json'),
                           'review_inputs': record(HERE / 'REVIEW_INPUTS.json'),
                           'execution_released': False, 'runtime_validated': False,
                           'scientific_execution': False,
                           'review_kind': 'Producer source preparation and AST syntax parse only; independent review pending'})
    print(json.dumps({'status': 'source_only', 'manifest': record(HERE / 'SOURCE_MANIFEST.json'),
                      'delivery': record(HERE / 'DELIVERY.json'), 'ast_parsed': parsed}, ensure_ascii=False))


if __name__ == '__main__':
    main()
