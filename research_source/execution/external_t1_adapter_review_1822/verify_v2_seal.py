"""Independent post-seal standard-library hash verification; no adapter imports."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
EP = OUT.parent / 'external_efficiency_preparation'
V1 = EP / 'external_t1_adapter_v1'
V2 = EP / 'external_t1_adapter_v2'
EXPECTED_MANIFEST = '1e6fd42b5b8777712e4283a48425bfc3f367fe58467118bf09567f59dbb11464'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def file_checks(manifest):
    result = []
    for entry in manifest['files']:
        path = Path(entry['path'])
        result.append({
            'path': str(path),
            'exists': path.is_file(),
            'size_matches': path.is_file() and path.stat().st_size == entry['bytes'],
            'hash_matches': path.is_file() and sha(path) == entry['sha256'],
        })
    return result

manifest = read_json(V2 / 'SOURCE_MANIFEST.json')
v1_manifest = read_json(V1 / 'SOURCE_MANIFEST.json')
checks2 = file_checks(manifest)
checks1 = file_checks(v1_manifest)
code_report = read_json(OUT / 'V2_RECHECK.json')
index = {str(Path(e['path']).resolve()).casefold(): e for e in manifest['files']}
reviewed_source_binding = {}
for name, expected in code_report['source_hashes'].items():
    path = V2 / name
    entry = index.get(str(path.resolve()).casefold())
    reviewed_source_binding[name] = {
        'reviewed_sha256': expected,
        'current_sha256': sha(path),
        'manifest_sha256': None if entry is None else entry['sha256'],
        'matches': entry is not None and sha(path) == expected == entry['sha256'],
    }
checks = {
    'expected_v2_manifest_sha': sha(V2 / 'SOURCE_MANIFEST.json') == EXPECTED_MANIFEST,
    'v2_has_188_files': len(checks2) == 188,
    'v2_unique_paths': len(index) == len(checks2),
    'all_v2_files_hash_size_exist': all(x['exists'] and x['size_matches'] and x['hash_matches'] for x in checks2),
    'reviewed_three_sources_bound_to_sealed_manifest': all(x['matches'] for x in reviewed_source_binding.values()),
    'v1_manifest_sha_unchanged': sha(V1 / 'SOURCE_MANIFEST.json') == '932dde425f4cc53db1c6c5d3e0844adcfff90dbdf4343d18407bdd3f6257311b',
    'all_173_v1_files_hash_size_exist': len(checks1) == 173 and all(x['exists'] and x['size_matches'] and x['hash_matches'] for x in checks1),
    'code_replay_report_14_passes': code_report['pass_count'] == code_report['check_count'] == 14,
    'no_scientific_modules_imported': not any(n in sys.modules for n in ['torch', 'numpy', 'scipy', 'PIL', 'timm', 'transformers', 'torchvision']),
}
report = {
    'schema': 'external-t1-adapter-v2-independent-seal-check.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'reviewer': 'memory_failure_1544_review',
    'checks': checks,
    'check_count': len(checks),
    'pass_count': sum(checks.values()),
    'v2_manifest_sha256': sha(V2 / 'SOURCE_MANIFEST.json'),
    'v2_files_count': len(checks2),
    'v2_files': checks2,
    'v1_manifest_sha256': sha(V1 / 'SOURCE_MANIFEST.json'),
    'v1_files_count': len(checks1),
    'v1_files': checks1,
    'reviewed_source_binding': reviewed_source_binding,
    'code_replay_report_sha256': sha(OUT / 'V2_RECHECK.json'),
    'verification_script_sha256': sha(__file__),
    'execution_scope': 'Standard-library file hashes and JSON only; no scientific imports, adapter import, model, GPU, active plan, queue, release or source writes.',
    'conclusion': 'No remaining blocker in the bounded v1 P2 fix and sealed-source binding review; not a scientific or live-model parity/timing result.' if all(checks.values()) else 'Independent verification failed; inspect checks.',
}
destination = OUT / 'V2_SEAL_CHECK.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'passed': report['pass_count'], 'total': report['check_count'], 'failed': [n for n, passed in checks.items() if not passed], 'v2_manifest_sha256': report['v2_manifest_sha256'], 'report_sha256': sha(destination)}, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
