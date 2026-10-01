"""Seal the two new post-robustness outputs; stdlib only, no job replay."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EX = HERE.parent
PKG = Path(r'C:\项目\LGM\02_代码与实验\正式实验工程\lgm_game_pytorch')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    out = HERE / 'a1'
    out.mkdir(exist_ok=False)
    bindings = []
    def capture(path, relative, expected=None):
        path = Path(path).resolve(strict=True)
        before = path.stat(); raw = path.read_bytes(); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        digest = sha(raw)
        if expected is not None:
            assert digest == expected, (str(path), digest, expected)
        saved = out / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        with saved.open('xb') as handle:
            handle.write(raw)
        bindings.append({'path': str(path), 'snapshot': str(saved), 'sha256': digest, 'bytes': len(raw)})
        return raw
    capture(EX / 'pipeline_status.json', 'pipeline_status.json')
    capture(EX / 'supervise_pipeline.py', 'source/supervise_pipeline.py')
    for job in ('robustness_aggregate', 'query_analysis'):
        for suffix in ('stdout', 'stderr'):
            capture(EX / f'stage_logs/{job}.{suffix}.log', f'logs/{job}.{suffix}.log')
    sources = {
        'experiments/aggregate_formal_robustness.py': '1a3328aaf4aa6bbb55da567e4cac7bc59d3c491928e6b998000353545b699ebb',
        'experiments/run_transactions_query_analysis.py': '0592c3c1859d38b3cea542d6a5afd8e27bc2b5836dcc83103f4f239db363f561',
        'experiments/formal_robustness_common.py': '58bc704cb8c00ceac356c338978e5b3a2324f8743b3a0bff1009b90c9327d01e',
        'experiments/transactions_query_analysis.py': None,
        'experiments/aggregate_frozen_formal_results.py': '4e6be8fb2dc8c07127b025cf19ce00c87f968ad9d4ad19e6a3e760fa24d301c5',
    }
    for rel, expected in sources.items():
        capture(PKG / rel, 'source/' + Path(rel).name, expected)
    capture(PKG.parent / 'TRANSACTIONS_EXTENSION_PROTOCOL.md', 'source/TRANSACTIONS_EXTENSION_PROTOCOL.md')
    for directory, label in ((PKG / 'results/formal_robustness_aggregate', 'aggregate'),
                             (PKG / 'analysis/transactions_t4_t5', 'query')):
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                capture(path, label + '/' + path.relative_to(directory).as_posix())
    roots = {
        'official': ('evaluation_audits_20260929/ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json',
                     '3b2bb1629f5b769fcd956c08068fa8ab2c947c9b36898a4bec2742e21110c17e'),
        'university_visual': ('robustness_audit_20260929_0946/ROOT_VISUAL1_ADOPTION.json',
                              '81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6'),
        'university_full': ('robustness_full_audit_20260929_1247/ROOT_FULL1_ADOPTION.json',
                            'ea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5'),
        'sues_visual': ('robustness_sues_visual_audit_20260929_1351/ROOT_SUES_VISUAL1_ADOPTION.json',
                       'a6795283cb384c77732bdb1e63af93d582d7844879f415e45ef38c8861d3af74'),
    }
    for label, (rel, expected) in roots.items():
        capture(EX / rel, 'authority/' + label + '.json', expected)
    cfg = json.loads((out / 'query/transactions_query_analysis_config.json').read_bytes())
    assert len(cfg['input_artifacts']) == 66
    for n, row in enumerate(cfg['input_artifacts']):
        capture(row['path'], f'query_inputs/{n:03d}.npz', row['sha256'])
        assert bindings[-1]['bytes'] == row['bytes']
    manifest = {'schema': 'post-robustness-new-output-capture.v1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'bindings': bindings,
        'source': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())},
        'scientific_modules': [], 'weights_cache_images_read': False,
        'new_query_npz_inputs': 66, 'sues_full_root_adoption_pending_at_capture': True,
        'new_output_capture_only_not_scientific_acceptance': True}
    target = out / 'CAPTURE.json'
    with target.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False); handle.write('\n')
    print(json.dumps({'capture': str(target), 'sha256': sha(target.read_bytes()), 'bindings': len(bindings)}))


if __name__ == '__main__':
    main()
