"""Adopt a local source-contract research note, never an execution adjudication."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

EX = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution')
HERE = Path(__file__).resolve().parent
NOTE = EX / 'predecessor_exit_contract_note_20260930_1647'
CAP = 262144
cache = {}
bindings = []
checks = []

def require(name, value):
    if value is not True:
        raise ValueError(name)
    checks.append({'name': name, 'pass': True})

def read(path, expected=None):
    path = Path(path)
    require('fixed_execution_scope:' + path.name, path.resolve().is_relative_to(EX.resolve()))
    key = str(path.resolve()).casefold()
    if key not in cache:
        before = path.stat()
        require('bounded_input:' + path.name, 0 < before.st_size <= CAP)
        with path.open('rb') as stream:
            raw = stream.read(CAP + 1)
        after = path.stat()
        require('stable_saved_read:' + path.name,
                len(raw) == before.st_size == after.st_size and
                before.st_mtime_ns == after.st_mtime_ns and before.st_ino == after.st_ino)
        desc = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        cache[key] = (raw, desc)
        bindings.append(desc)
    raw, desc = cache[key]
    if expected:
        require('expected_byte_binding:' + path.name,
                expected == desc and type(expected['bytes']) is int)
    return raw

def desc(path):
    read(path)
    return cache[str(Path(path).resolve()).casefold()][1]

note = json.loads(read(NOTE / 'PREDECESSOR_EXIT_CONTRACT_NOTE.json', {
    'path': str(NOTE / 'PREDECESSOR_EXIT_CONTRACT_NOTE.json'), 'bytes': 59670,
    'sha256': 'c820362a29d8fcc6e725c3a30ca0f52fec5df30ac341483fefc9c5c0da19d946'}))
read(NOTE / 'PREDECESSOR_EXIT_CONTRACT_NOTE.md', {
    'path': str(NOTE / 'PREDECESSOR_EXIT_CONTRACT_NOTE.md'), 'bytes': 3213,
    'sha256': '7d77d06e7eabc2448bb21added292d87a5ea699b41131e04646d85eaa38ef27c'})
require('seventeen_necessary_small_inputs', len(note['input_bindings']) == 17)
for binding in note['input_bindings']:
    path = Path(binding['path'])
    require('source_or_small_control_record_only:' + path.name, path.suffix in ('.py', '.json'))
    read(path, binding)
quoted_line_count = 0
for reference in note['exact_source_references']:
    for excerpt in reference['excerpts']:
        lines = read(excerpt['path']).decode('utf-8-sig').splitlines()
        require('quoted_range:' + reference['id'],
                [item['line'] for item in excerpt['lines']] ==
                list(range(excerpt['start_line'], excerpt['end_line'] + 1)))
        for item in excerpt['lines']:
            require('exact_saved_quote:' + reference['id'] + ':' + str(item['line']),
                    lines[item['line'] - 1] == item['text'])
            quoted_line_count += 1
require('scope_is_contract_research_only',
        note['finding']['original_operational_contract_requires_primary_top_level_independent_DWORD0'] is False and
        note['finding']['that_route_proves_historical_primary_exit0'] is False and
        note['finding']['current_B1_inherited_executable_adjudication_or_waiver_exists_in_read_sources'] is False and
        note['performed']['execution_adjudication_adopted'] is False and
        note['performed']['B1_or_SCI_execution_authorized'] is False)
require('primary_own_exit_stays_unknown',
        note['saved_current_primary_fields']['top_level_exit_code_present'] is False and
        note['saved_current_primary_fields']['top_level_exit_code'] is None)
official = note['official_root_limited_text_read']
require('official_root_inherited_sha_not_rehash',
        official['sha256_inherited_from_HANDOFF_not_new_hash'] ==
        '3b2bb1629f5b769fcd956c08068fa8ab2c947c9b36898a4bec2742e21110c17e' and
        Path(official['path']).stat().st_size == official['bytes_from_stat'] == 677924 and
        official['primary_exit_code_observed'] is False)
actual = json.loads(read(NOTE / 'ACTUAL_NOTE_SAVE_TOOL_RETURN.json', {
    'path': str(NOTE / 'ACTUAL_NOTE_SAVE_TOOL_RETURN.json'), 'bytes': 2317,
    'sha256': '998adf18fe7057054edb90e6ce712541d96808bf183b8156bebf022e26208119'}))
require('actual_note_save_completed',
        actual['actual_return']['chunk_id'] == 'c8dfa7' and
        actual['actual_return']['exit_code'] == 0)
read(HERE / 'adopt_predecessor_research.py')

report = {
    'schema': 'root-predecessor-contract-research-adoption.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'research_note_adopted': True,
    'scope': 'AI read-source historical requirement finding and exact quotation binding only',
    'note': desc(NOTE / 'PREDECESSOR_EXIT_CONTRACT_NOTE.json'),
    'findings': note['finding'],
    'method': 'Root complete note/producer-source/excerpt reading; fresh bounded saved bytes and exact excerpt lines. No candidate import, AST execution, API, scientific or old-suite rerun.',
    'quoted_line_count': quoted_line_count,
    'official_large_root_selected_scope_inherited': official,
    'actual_note_save': desc(NOTE / 'ACTUAL_NOTE_SAVE_TOOL_RETURN.json'),
    'bindings': bindings,
    'local_saved_file_checks': checks,
    'primary_own_independent_exit': 'unknown; no receipt fabricated',
    'scientific_adoption_changed': False,
    'new_role_scoped_predecessor_policy_implemented': False,
    'execution_adjudication_adopted': False,
    'current_OS_GPU_memory_admission': False,
    'release_or_intent_or_attempt_created': False,
    'state_or_shared_lock_modified': False,
    'B1_or_scientific_execution_authorized': False,
    'next_policy_scope': note['minimal_future_review_path'],
    'actual_scientific_predecessors_complete': False,
    'automation_retained': True,
}
raw = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
require('bounded_new_research_report', len(raw) <= CAP)
target = HERE / 'ROOT_PREDECESSOR_CONTRACT_RESEARCH_ADOPTION.json'
with target.open('xb') as stream:
    stream.write(raw)
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps({'report': {'path': str(target), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                  'unique_small_bindings': len(bindings), 'quoted_lines': quoted_line_count,
                  'research_note_adopted': True, 'execution_adjudication_adopted': False}, ensure_ascii=False))
