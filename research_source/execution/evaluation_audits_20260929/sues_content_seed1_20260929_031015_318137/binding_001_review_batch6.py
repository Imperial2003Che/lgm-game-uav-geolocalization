"""Fixed six new University visual_style/full evaluation runs. Checkpoint bytes MUST NOT be read."""
import ast
import csv
import hashlib
import importlib.util
import inspect
import io
import json
import math
import os
import struct
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).parent
EX = HERE.parent
ROOT = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PKG = ROOT / 'lgm_game_pytorch'
DATA = Path(r'C:\项目\IMTMN\datasets\University-1652')
STAMP = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
OUT = HERE / ('batch6_' + STAMP)
OUT.mkdir()
bindings = []
queries = []

def now():
    return datetime.now(timezone.utc).isoformat()

def check(value, message):
    if not value:
        raise AssertionError(message)

def stat(path):
    s = Path(path).stat()
    return {'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns, 'device': s.st_dev, 'inode': s.st_ino}

def forbid_checkpoint_open(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        check(Path(os.fsdecode(args[0])).suffix.lower() not in ('.pt', '.pth', '.ckpt'), 'Checkpoint byte access forbidden')

sys.addaudithook(forbid_checkpoint_open)

def sha(path):
    path = Path(path)
    check(path.suffix.lower() not in ('.pt', '.pth', '.ckpt'), 'Checkpoint fresh hash forbidden')
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)
    return path

def snapshot(path, name=None, expected=None):
    path = Path(path)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    check(expected is None or expected == digest, 'Pinned SHA mismatch: ' + str(path))
    dest = save(name or ('binding_%03d_' % len(bindings) + path.name), data)
    row = {'path': str(path), 'snapshot': str(dest), 'bytes': len(data), 'sha256': digest}
    bindings.append(row)
    return data, row

def js(data):
    return json.loads(data.decode('utf-8-sig'))

def canon(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str).encode('utf-8')).hexdigest()

def refs(value):
    if isinstance(value, dict):
        if isinstance(value.get('sha256'), str):
            for key in ('path', 'snapshot'):
                if isinstance(value.get(key), str):
                    yield Path(value[key]), value['sha256']
        for child in value.values():
            yield from refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from refs(child)

def npy(data):
    f = io.BytesIO(data)
    check(f.read(6) == b'\x93NUMPY', 'NPY magic')
    version = f.read(2)
    check(version in (b'\x01\x00', b'\x02\x00'), 'Unsupported NPY version')
    count = struct.unpack('<H' if version[0] == 1 else '<I', f.read(2 if version[0] == 1 else 4))[0]
    header = ast.literal_eval(f.read(count).decode('latin1').strip())
    check(not header['fortran_order'] and len(header['shape']) == 1, 'NPY must be one dimensional')
    n = header['shape'][0]
    dtype = header['descr']
    raw = f.read()
    if dtype.startswith('<U'):
        width = int(dtype[2:]) * 4
        check(len(raw) == n * width, 'Unicode NPY byte size')
        result = [raw[i:i+width].decode('utf-32-le').rstrip('\0') for i in range(0, len(raw), width)]
    else:
        formats = {'<f4': ('f', 4), '<i8': ('q', 8), '|b1': ('?', 1)}
        check(dtype in formats, 'Object/unexpected NPY dtype forbidden: ' + dtype)
        fmt, width = formats[dtype]
        check(len(raw) == n * width, 'Numeric NPY byte size')
        result = list(struct.unpack('<' + str(n) + fmt, raw))
    return result, header

def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

report = {'schema': 'bounded-official-evaluation-audit-v1', 'started_utc': now(), 'review_script': {'path': str(Path(__file__)), 'sha256': sha(__file__)}, 'executable': sys.executable, 'scope': {'dataset': 'university1652', 'targets': [(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)], 'requested_evaluation_runs': 6, 'requested_retrieval_tasks': 18, 'out_of_batch_admitted': 0}, 'fresh_checkpoint_byte_hashes': 0, 'checkpoint_loaded': False, 'scientific_entrypoints_executed': False, 'live_files_modified': False}

try:
    previous_dir = EX / 'evaluation_audits_20260928'
    prior_path = previous_dir / 'ROOT_BATCH10_ADOPTION_20260928.json'
    prior_sha = '155610032a4e1951527206ee47c4366fbb202a7c175006209913cee86902173e'
    prior_eval = js(snapshot(prior_path, expected=prior_sha)[0])
    check(prior_eval['adopted_with_stated_inheritance_limits'] and prior_eval['accepted_total_evaluation_runs'] == 12 and prior_eval['accepted_total_retrieval_tasks'] == 36, 'Prior twelve-run adoption invalid')
    report['previous_eval_adoption'] = {'path':str(prior_path),'sha256':prior_sha,'accepted_runs':12,'accepted_tasks':36,'old_evaluation_artifacts_rehashed':False}
    snapshot(previous_dir / 'review_batch10.py', expected='ef3a63b378d1d7846d87a5faf51a045de98b9b3b7064361c5556603167294c9e')
    snapshot(HERE / 'REVIEW_BATCH6_SOURCE_DIFF.patch')
    root42_path = EX / 'completion_audits_20260928/ROOT_FIT_42_ADOPTION_20260928.json'
    root42_sha = 'ca54f91342f77d7d17f18a932c61681ae6f4d7c14f4ffd917c0c1594fc289e87'
    queue = [(root42_path, root42_sha, None)]
    graph, documents, seen = [], {}, set()
    while queue:
        path, expected, parent = queue.pop(0)
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        data, binding = snapshot(path, expected=expected)
        obj = js(data)
        documents[path.name] = obj
        graph.append({'from_document': parent, 'to_document': key, 'sha256': expected, 'actual_sha256_verified': True})
        for dest, digest in refs(obj):
            if dest.suffix == '.json' and (('ROOT_' in dest.name and 'ADOPTION' in dest.name) or dest.name.startswith('BATCH_COMPLETION') or dest.name == 'FULL_SEED2_COMPLETION.json'):
                queue.append((dest, digest, key))
    required = ['ROOT_FIT_42_ADOPTION_20260928.json', 'ROOT_BATCH_36_ADOPTION_20260922.json', 'BATCH_COMPLETION_0944.json', 'ROOT_BATCH_32_ADOPTION_20260922.json', 'ROOT_BATCH_29_ADOPTION_20260921.json', 'BATCH_COMPLETION_1611.json', 'FULL_SEED2_COMPLETION.json']
    check(all(name in documents for name in required), 'Inherited acceptance chain incomplete')
    batch = documents['BATCH_COMPLETION_0944.json']
    ledger_path = EX / 'completion_audits_20260922/BATCH_0944_LEDGER_RAW.json'
    ledger_sha = '55e5ffe63d9f4c907076552db832e2b4c0647fa10dadea8bcdaf7668c4be8187'
    linked = [(p, s) for obj in (batch, documents['ROOT_BATCH_36_ADOPTION_20260922.json']) for p, s in refs(obj) if p.name == ledger_path.name and s == ledger_sha]
    check(bool(linked), 'Historical ledger is not explicitly bound by adopted report')
    ledger = js(snapshot(ledger_path, expected=ledger_sha)[0])
    report['inherited_training_acceptance_graph'] = graph
    report['inherited_checkpoint_sha_source'] = {'path': str(ledger_path), 'sha256': ledger_sha, 'explicit_adopted_document_edge_verified': True}
    # Specific later-trained fits use actual historical artifact reports, not the initial inventory.
    authority_reports = {}
    authority_rows = {}
    specific_sources = [
        ('visual_style', 1, 'VISUAL_STYLE_SEED1_COMPLETION_20260914.json', 'c899a2c99b0c90b865806eab41556fff4bea6bd56656a71073d5a60b294745f1', None, None),
        ('visual_style', 2, 'status_write_incident_20260920_0138/COMPLETED_FIT_REVIEW_20260920.json', '93890643b3649b7b53951566ed573d494c5f78016954546853bfc416886afb5b', 'state_write_recovery_20260920_0138/ROOT_ADOPTION_20260920.json', '871c6b014a48463af26e1624badad591db191f8a57aedf5687e8636f3ec95f97'),
        ('visual_style', 3, 'completion_audits_20260920/VISUAL_STYLE_SEED3_COMPLETION.json', '1810ff728ca2e09abca49d298d02fd1dfd120ec3186ee3f514dc7c6e8b924cf9', 'completion_audits_20260920/ROOT_SEED3_ADOPTION_20260920.json', '4ea57f0956af59749dd93c151108414f94e749d7ccb10fa8e75834b4c6196e7f'),
        ('full', 1, 'completion_audits_20260920/FULL_SEED1_COMPLETION.json', '61b2c2019d33ebcf192fbc73321f8667ef5daee9cd8e02bb87c6b4f862a0dd09', 'completion_audits_20260920/ROOT_FULL_SEED1_ADOPTION_20260920.json', '772133fee742bb3b26825eb8e3c05760cf4ace5e28f22d729c013841be84a018'),
        ('full', 2, 'completion_audits_20260920/FULL_SEED2_COMPLETION.json', 'ec116f025e590d4392322fcaef04923fa92d40c88afa909ca4ea7f6120594b16', 'completion_audits_20260920/ROOT_FULL_SEED2_ADOPTION_20260921.json', '0474c03baf3170dab96b297b9d426bd6b6ce1e7ad30fe5525cab2651bf6a8437'),
        ('full', 3, 'completion_audits_20260921/BATCH_COMPLETION_1611.json', 'f88259d145316e76b36f63130800f2a47f91c0cbdf863fd9cabb2381bbca0bb2', None, None),
    ]
    for variant, seed, relative, digest, adoption_relative, adoption_sha in specific_sources:
        source_path = EX / relative
        source = js(snapshot(source_path, expected=digest)[0])
        if (variant, seed) == ('full', 3):
            check(source['batch_passed'], 'Specific full3 historical batch rejected')
            entry = next(r for r in source['new_runs'] if r['run_identifier'] == 'formal_main/university1652/full/seed_3/resnet18/dim_512')
            check(any(g['to_document'] == str(source_path) and g['sha256'] == digest for g in graph), 'Full3 report not reached by adopted chain')
        else:
            entry = source
        if (variant, seed) == ('visual_style', 1):
            check(entry['status'] == 'new_complete_fit_artifacts_verified' and entry['epochs_completed'] == 80 and entry['final_epoch_zero_based'] == 79, 'Seed1 original artifact audit not complete')
        else:
            check(entry['original_training_completion_issues'] == [] and entry['epochs_completed'] == 80 and entry['last_epoch'] == 79, 'Specific original training completion issues')
            check((variant, seed) == ('full', 3) or entry['passed'], 'Specific training audit did not pass')
        authority = {'report_path':str(source_path),'report_sha256':digest,'historical_report_checkpoint_hashes_fresh_when_report_created':True,'independent_report': (variant,seed) not in (('visual_style',1),('visual_style',2))}
        if adoption_relative:
            adoption_path = EX / adoption_relative
            adoption = js(snapshot(adoption_path, expected=adoption_sha)[0])
            if variant == 'visual_style' and seed == 2:
                check(any(p == source_path and h == digest for p,h in refs(adoption)), 'Detached completion not bound by recovery adoption')
            else:
                check(adoption['accepted'] and Path(adoption['audit_path']) == source_path and adoption['audit_sha256'] == digest, 'Legacy root adoption exact report edge')
            authority['historical_root_adoption'] = {'path':str(adoption_path),'sha256':adoption_sha,'exact_report_edge_verified':True}
        if (variant,seed) == ('visual_style',1):
            authority['historical_report_sha_edge_found'] = False
            authority['limitation'] = 'Sep14 report is current-SHA-bound matching corroboration; no separate historical whole-report SHA edge found. Accepted ROOT42 identifier and SHA-linked adopted ledger supply inherited checkpoint authority.'
        authority_reports[(variant,seed)] = entry
        authority_rows[(variant,seed)] = authority
    report['specific_training_report_authorities'] = list(authority_rows.values())
    report['initial_inventory_not_used'] = True
    runner_path = PKG / 'experiments/run_frozen_formal_matrix.py'
    snapshot(runner_path, expected='f251e5088b306ddec4769fab06799008d06194bc459282f2432ac3238f4ba59f')
    snapshot(PKG / 'lgm_game_pytorch/formal_retrieval.py', expected='081f327f8f83d79ab078adc61e76070c140f13e0ac9a0d8f423bfad15df59862')
    snapshot(ROOT / 'FORMAL_EXPERIMENT_PROTOCOL.md', expected='29c0502b07f09d45c6fd7d4a5b582fdd9a443acc9e8b818cd9941c18a0ee34f9')
    compat = EX / 'primary_path_repair_20260918'
    snapshot(compat / 'SOURCE_MANIFEST.json', expected='11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1')
    sys.path.insert(0, str(compat))
    import source_contract
    import project_paths
    source_contract.verify('11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1')
    runner = import_file('bounded_eval_original_runner', runner_path)
    runner.Path = project_paths.FrozenProjectPath
    original_sha = runner.sha256_file
    frozen_root = project_paths.FrozenProjectPath(ROOT)
    main = runner.main_run_specs(frozen_root, runner.DATASETS, runner.MAIN_VARIANTS, runner.MAIN_SEEDS)
    sensitivity = runner.sensitivity_run_specs(frozen_root, runner.DATASETS)
    runner.validate_registry(main, sensitivity)
    check(runner.registry_sha256(main + sensitivity) == ledger['registered_registry_sha256'], 'Registry SHA changed')
    report['registered_registry_sha256'] = ledger['registered_registry_sha256']
    targets = {(v, s) for v in ('visual_style', 'full') for s in (1, 2, 3)}
    specs = [s for s in main if s.dataset == 'university1652' and (s.variant, s.seed) in targets]
    check(len(specs) == 6 and {(s.variant, s.seed) for s in specs} == targets, 'Fixed six-run scope')
    accepted = documents['ROOT_FIT_42_ADOPTION_20260928.json']['completed_fit_ids']
    check(all(s.identifier in accepted for s in specs), 'Run not in adopted training IDs')
    parent = js(snapshot(HERE / 'PRE_RECOVERY_PARENT_STATUS_20260929.json', 'PARENT_STATUS_RAW.json', expected='9990d0fe954a55f57673ba1498a30c1250b6c50fd1c4b935fa6f8c1df653bfed')[0])
    live_ledger = js(snapshot(PKG / 'runs/frozen_formal_matrix_ledger.json', 'LIVE_LEDGER_RAW.json')[0])
    check(live_ledger['frozen_inputs'] == ledger['frozen_inputs'], 'Frozen inputs changed')
    check(live_ledger['registered_registry_sha256'] == ledger['registered_registry_sha256'], 'Live registry mismatch')
    frozen = ledger['frozen_inputs']['university1652']
    evidence_path = Path(frozen['evidence_path'])
    dataset = runner.DatasetSpec('university1652', project_paths.FrozenProjectPath(DATA), project_paths.FrozenProjectPath(evidence_path).resolve(), frozen['evidence_sha256'])
    cache_before = stat(evidence_path)
    with zipfile.ZipFile(evidence_path) as z:
        evidence_paths, _ = npy(z.read('paths.npy'))
    check(len(evidence_paths) == len(set(evidence_paths)) == 146520, 'Evidence paths rows/uniqueness')
    roles = ('query_drone', 'gallery_satellite', 'query_satellite', 'gallery_drone', 'query_street')
    by_role, metadata = {}, []
    evidence_set = set(evidence_paths)
    for role in roles:
        files = sorted(p for p in (DATA / 'test' / role).rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp', '.webp'))
        relative = [p.relative_to(DATA).as_posix() for p in files]
        expected_members = sorted(p for p in evidence_paths if p.startswith('test/' + role + '/'))
        check(relative == expected_members, 'Filesystem versus evidence official membership: ' + role)
        by_role[role] = relative
        metadata.extend({'path': r, 'bytes': p.stat().st_size} for r, p in zip(relative, files))
    tasks = []
    for suffix, qr, gr in [('drone_to_satellite', 'query_drone', 'gallery_satellite'), ('satellite_to_drone', 'query_satellite', 'gallery_drone'), ('street_to_satellite', 'query_street', 'gallery_satellite')]:
        tasks.append({'name': 'university1652_' + suffix, 'protocol': 'official test/' + qr + ' -> test/' + gr, 'query': by_role[qr], 'gallery': by_role[gr]})
    membership_sha = canon(tasks)
    member_file = save('OFFICIAL_MEMBERSHIP.json', json.dumps(tasks, ensure_ascii=False, indent=1).encode('utf-8'))
    report['official_membership'] = {'path': str(member_file), 'sha256': sha(member_file), 'canonical_protocol_membership_sha256': membership_sha, 'actual_file_count': len(metadata), 'actual_file_bytes': sum(x['bytes'] for x in metadata), 'filesystem_paths_equal_evidence_paths': True, 'evidence_cache_sha256_inherited': frozen['evidence_sha256'], 'evidence_cache_full_byte_hash_repeated': False, 'evidence_path_array_read_with_standard_library': True, 'cache_stat_before': cache_before, 'cache_stat_after': stat(evidence_path), 'all_image_content_hashes_repeated': False}
    check(cache_before == stat(evidence_path), 'Evidence cache metadata changed during audit')
    allowed, cp_records = {}, {}
    for spec in specs:
        path = Path(spec.run_dir / 'best.pt')
        entry = authority_reports[(spec.variant, spec.seed)]
        artifacts = entry['verified_artifacts'] if (spec.variant,spec.seed) == ('visual_style',1) else entry['artifacts_sha256_verified']
        art = artifacts['best.pt']
        record = ledger['runs'][spec.identifier]
        check(record['checkpoint_sha256'] == art['sha256'], 'Adopted ledger versus specific historical checkpoint SHA disagreement')
        current = stat(path)
        check(current['bytes'] == art['bytes'], 'Checkpoint size changed')
        allowed[os.path.normcase(os.path.abspath(path))] = (path, current, record['checkpoint_sha256'])
        cp_records[spec.identifier] = {'path':str(path),'inherited_sha256':record['checkpoint_sha256'],'specific_historical_artifact':art,'specific_training_authority':authority_rows[(spec.variant,spec.seed)],'inherited_ledger_record':record,'stat_before':current,'limitation':'Current checkpoint metadata stability cannot establish current bytes. Inherited SHA is bound by accepted ledger and matches specific historical training artifact report.'}
        # Rebind small current training artifacts to the actual historical audit values.
        for name in ('run_config.json','history.json','run.log'):
            old_art = artifacts[name]
            snapshot(Path(spec.run_dir) / name, f'{spec.variant}_seed{spec.seed}/training_authority/{name}', expected=old_art['sha256'])
            check((Path(spec.run_dir) / name).stat().st_size == old_art['bytes'], 'Historical small training artifact size mismatch')
        if (spec.variant,spec.seed) == ('visual_style',1):
            manifest_digest = entry['manifest_sha256']
        elif (spec.variant,spec.seed) == ('visual_style',2):
            manifest_digest = entry['run_manifest']['sha256']
        else:
            historical_manifest = entry['manifest_raw_snapshot']
            manifest_digest = historical_manifest['sha256']
            snapshot(historical_manifest['snapshot'], f'{spec.variant}_seed{spec.seed}/historical_manifest.json', expected=manifest_digest)
        manifest_data, _ = snapshot(Path(spec.run_dir) / 'run_manifest.json', f'{spec.variant}_seed{spec.seed}/training_authority/run_manifest.json', expected=manifest_digest)
        historical_match = js(manifest_data)
        if 'manifest_payload_sha256' in entry:
            check(historical_match['payload_sha256'] == entry['manifest_payload_sha256'] and historical_match['run_config_sha256'] == entry['run_config_sha256'], 'Specific historical manifest/config canonical bindings')

    def scoped_sha(path):
        path = Path(path)
        key = os.path.normcase(os.path.abspath(path))
        if path.suffix.lower() in ('.pt', '.pth', '.ckpt'):
            check(key in allowed, 'Unapproved checkpoint hash request: ' + str(path))
            expected_path, before, digest = allowed[key]
            check(os.path.samefile(path, expected_path) and stat(path) == before, 'Checkpoint identity/stat changed')
            mode = 'inherited_adopted_ledger_SHA_NOT_fresh_checkpoint_hash'
        else:
            digest = original_sha(path)
            mode = 'fresh_non_checkpoint_byte_hash'
        queries.append({'requested_path': str(path), 'sha256': digest, 'mode': mode})
        return digest

    report['original_validator_contract'] = {'name': 'evaluation_completion_issues', 'source_function_sha256': hashlib.sha256(inspect.getsource(runner.evaluation_completion_issues).encode()).hexdigest(), 'function_body_changed': False, 'module_Path_binding': 'adopted FrozenProjectPath', 'sha256_file_temporarily_wrapped': True, 'cached_checkpoint_allowlist': list(allowed), 'all_other_checkpoint_requests': 'reject', 'restored_in_finally': False, 'unconditional_fresh_checkpoint_validator_pass_claimed': False}
    results = []
    try:
        runner.sha256_file = scoped_sha
        for spec in specs:
            run = Path(spec.run_dir)
            ev = Path(spec.evaluation_dir)
            manifest = js(snapshot(ev / 'evaluation_manifest.json', f'{spec.variant}_seed{spec.seed}/evaluation_manifest.json')[0])
            config = js(snapshot(run / 'run_config.json', f'{spec.variant}_seed{spec.seed}/run_config.json')[0])
            train_manifest = js(snapshot(run / 'run_manifest.json', f'{spec.variant}_seed{spec.seed}/run_manifest.json')[0])
            history = js(snapshot(run / 'history.json', f'{spec.variant}_seed{spec.seed}/history.json')[0])
            issues = runner.evaluation_completion_issues(spec, dataset)
            check(not issues, 'Original evaluation validator issues: ' + repr(issues))
            for doc in (manifest, train_manifest):
                payload = dict(doc); declared = payload.pop('payload_sha256')
                check(canon(payload) == declared, 'Manifest canonical payload')
            check(canon(config['immutable_config']) == config['run_config_sha256'] == manifest['checkpoint']['training_run_config_sha256'] == train_manifest['run_config_sha256'], 'Canonical run config mismatch')
            check(train_manifest['status'] == 'completed' and train_manifest['epochs_completed'] == 80 and train_manifest['best_epoch'] == 79 and train_manifest['test_protocol_was_evaluated'] is False, 'Training final-epoch protocol')
            check(manifest['protocol_membership_sha256'] == membership_sha, 'Full official membership hash')
            check(manifest['image_inventory']['file_count'] == len(metadata) and manifest['image_inventory']['total_bytes'] == sum(x['bytes'] for x in metadata), 'Image inventory metadata size/count')
            check(manifest['amp'] is True, 'Frozen evaluation AMP')
            artifact_records = []
            for name, declared in manifest['artifacts'].items():
                actual_path = ev / name
                check(actual_path.resolve().is_relative_to(ev.resolve()), 'Artifact path outside evaluation')
                before = stat(actual_path)
                data, binding = snapshot(actual_path, f'{spec.variant}_seed{spec.seed}/artifacts/{name}', declared['sha256'])
                check(len(data) == declared['bytes'] and before == stat(actual_path), 'Evaluation artifact size or stat changed')
                artifact_records.append(binding)
            check(len(artifact_records) == 7, 'Expected all seven evaluation artifacts')
            snapshot(ev / 'run.log', f'{spec.variant}_seed{spec.seed}/evaluation_run.log')
            metrics = js((OUT / f'{spec.variant}_seed{spec.seed}/artifacts/metrics.json').read_bytes())
            rows = list(csv.DictReader((OUT / f'{spec.variant}_seed{spec.seed}/artifacts/metrics.csv').read_text(encoding='utf-8-sig').splitlines()))
            check(set(metrics['results']) == {t['name'] for t in tasks} == {r['task'] for r in rows}, 'Task keys exact')
            task_checks = []
            for task in tasks:
                name = task['name']; m = metrics['results'][name]; row = next(r for r in rows if r['task'] == name)
                for key, value in row.items():
                    if key != 'task':
                        check(value == m[key] if isinstance(m[key], str) else float(value) == m[key], 'CSV/JSON disagreement: ' + key)
                q, g = task['query'], task['gallery']
                check(m['queries'] == len(q) and m['gallery'] == len(g) and m['protocol'] == task['protocol'], 'Official counts/protocol')
                check(m['query_identities'] == len({p.split('/')[2] for p in q}) and m['gallery_identities'] == len({p.split('/')[2] for p in g}), 'Official identity counts')
                scale = manifest['task_scale'][name]
                check(scale == {'queries':len(q),'gallery_images':len(g),'query_identities':m['query_identities'],'gallery_identities':m['gallery_identities'],'protocol':task['protocol']}, 'Manifest task_scale inconsistent')
                with zipfile.ZipFile(OUT / f'{spec.variant}_seed{spec.seed}/artifacts/per_query_arrays/{name}_per_query.npz') as z:
                    arrays = {Path(n).stem: npy(z.read(n))[0] for n in z.namelist()}
                check(len(arrays) == 9 and all(len(v) == len(q) for v in arrays.values()), 'Per-query array shapes')
                check(arrays['query_paths'] == q and arrays['query_labels'] == [p.split('/')[2] for p in q], 'Per-query official query order/labels')
                indices = arrays['top1_gallery_indices']
                check(all(0 <= i < len(g) for i in indices), 'Gallery indices out of range')
                check(arrays['top1_gallery_paths'] == [g[i] for i in indices] and arrays['top1_gallery_labels'] == [g[i].split('/')[2] for i in indices], 'Top1 full-gallery mapping')
                check(arrays['correct'] == [a == b for a,b in zip(arrays['query_labels'], arrays['top1_gallery_labels'])], 'Correct indicator labels')
                for key in ('per_query_official_trapezoid_AP', 'reciprocal_rank'):
                    check(all(math.isfinite(v) and 0 <= v <= 1 for v in arrays[key]), 'Invalid per-query AP/RR')
                check(all(math.isfinite(v) and v >= 0 for v in arrays['margin']), 'Invalid margins')
                ranks = [int(round(1/v)) if v else len(g)+1 for v in arrays['reciprocal_rank']]
                check(all(1 <= r <= len(g) and abs(v - 1/r) <= 1e-7 for r,v in zip(ranks,arrays['reciprocal_rank'])), 'RR integer rank consistency')
                for k in (1,5,10,20):
                    check(abs(sum(r <= k for r in ranks)/len(q) - m['r_at_'+str(k)]) <= 1e-12, 'Recall aggregation mismatch')
                check(abs(sum(arrays['correct'])/len(q) - m['r_at_1']) <= 1e-12, 'R1 correctness aggregation')
                for key, array_key in [('official_trapezoid_mAP','per_query_official_trapezoid_AP'),('MRR','reciprocal_rank'),('mean_top1_margin','margin')]:
                    check(abs(math.fsum(arrays[array_key])/len(q) - m[key]) <= 1e-7, 'Float32 aggregate mismatch: '+key)
                task_checks.append({'task':name,'queries':len(q),'gallery':len(g),'official_membership_and_array_alignment_passed':True,'CSV_JSON_agree':True,'stored_array_aggregates_agree':True,'float32_aggregate_absolute_tolerance':1e-7,'full_ranking_or_AP_from_all_positive_ranks_recomputed':False})
            events = [e for e in parent['events'] if e.get('output_dir') == str(spec.evaluation_dir) and 'evaluate' in e.get('command', [])]
            check(len(events) == 1 and events[0]['status'] == 'completed' and events[0]['exit_code'] == 0, 'Parent Popen completion event')
            cp = cp_records[spec.identifier]
            check(train_manifest['artifacts']['best.pt']['sha256'] == cp['inherited_sha256'] and train_manifest['artifacts']['best.pt']['bytes'] == cp['stat_before']['bytes'], 'Train artifact inherited checkpoint identity')
            cp['stat_after'] = stat(run / 'best.pt')
            check(cp['stat_before'] == cp['stat_after'], 'Checkpoint stat changed during bounded audit')
            results.append({'identifier':spec.identifier,'evaluation_dir':str(ev),'original_evaluation_completion_issues_with_scoped_inherited_checkpoint_SHA':issues,'fresh_evaluation_artifact_verification':artifact_records,'inherited_checkpoint_SHA':cp,'parent_Popen_event':events[0],'tasks':task_checks,'evaluation_manifest_payload_sha256':manifest['payload_sha256'],'run_config_sha256':config['run_config_sha256'],'passed_with_stated_inheritance_limits':True})
    finally:
        runner.sha256_file = original_sha
        report['original_validator_contract']['restored_in_finally'] = runner.sha256_file is original_sha
    launcher_numbers = [r['parent_Popen_event']['pid'] for r in results]
    check(launcher_numbers == [12564,7896,28100,18364,16816,31052], 'Fixed parent launcher event numbers')
    filter_text = ' OR '.join('ProcessId=' + str(int(pid)) for pid in launcher_numbers)
    ps = "$ErrorActionPreference='Stop'; [pscustomobject]@{ sampled_utc=[DateTime]::UtcNow.ToString('o'); processes=@(Get-CimInstance Win32_Process -Filter '" + filter_text + "' | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine) } | ConvertTo-Json -Depth 6 -Compress"
    observed = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],capture_output=True,text=True,check=True)
    cim = json.loads(observed.stdout)
    cim['queried_launcher_pid_numbers'] = launcher_numbers
    cim['current_pid_number_presence_is_not_original_identity_proof'] = True
    cim['pid_numbers_currently_absent'] = sorted(set(launcher_numbers) - {int(p['ProcessId']) for p in cim['processes']})
    report.update({'runs':results,'original_validator_hash_queries':queries,'known_old_launcher_CIM_observation':cim,'independent_windows_exit_handles_held':False,'old_interpreter_identity_known':False,'interpreter_exit_codes_observed':False,'exit_evidence_basis':'Original parent Popen exit0 events and this later CIM observation of known launcher PID numbers only; a reused PID is not proof of original process survival; no original launcher CreationDate or interpreter identity observed by this audit.','accepted_evaluation_run_count':6,'accepted_retrieval_task_count':18,'fresh_evaluation_artifact_count':42,'inherited_previous_evaluation_run_count':12,'inherited_previous_retrieval_task_count':36,'accepted_total_evaluation_run_count_with_this_batch':18,'accepted_total_retrieval_task_count_with_this_batch':54,'all_42_evaluations_accepted':False,'paper_means_or_conclusions_created':False,'evaluation_rerun_or_rank_recomputation':False,'limitations':['Checkpoint SHA inherited from actually SHA-bound adopted ledger, not freshly hashed.','Visual_style seed1 original Sep14 whole-report historical SHA edge was not found; currently bound report is corroboration. Accepted ROOT42 identifier and adopted Sep22 ledger supply inherited checkpoint authority. Other five specific reports have verified historical root/chain edges.','Checkpoint size/mtime/stat stability cannot establish current byte identity.','Evidence cache SHA and full image-content inventory SHA inherited; official path membership and metadata counts independently checked.','Per-query stored arrays checked and aggregate consistency verified; no full distance matrix/reranking or recomputation of AP from all positive ranks.','Exactly six new runs, eighteen new tasks; twelve prior runs/thirty-six prior tasks inherited by adoption SHA, no other evaluation accepted.']})
    forbidden = sorted(name for name in sys.modules if name.split('.')[0] in ('torch','numpy','PIL','torchvision','scipy','matplotlib'))
    report['scientific_modules'] = forbidden
    check(not forbidden, 'Forbidden scientific imports')
    report['passed_with_stated_inheritance_limits'] = True
except Exception as exc:
    report['passed_with_stated_inheritance_limits'] = False
    report['error'] = repr(exc)
    report['traceback'] = traceback.format_exc()
finally:
    report['finished_utc'] = now()
    report['raw_evidence_bindings'] = bindings
    report_path = save('BATCH6_EVALUATION_REVIEW.json', json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8'))
    delivery = {'schema':'bounded-evaluation-delivery-v1','created_utc':now(),'report':{'path':str(report_path),'sha256':sha(report_path)},'source':report['review_script'],'files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.rglob('*') if p.is_file()]}
    delivery_path = save('DELIVERY.json', json.dumps(delivery,ensure_ascii=False,indent=2).encode('utf-8'))
    print(json.dumps({'report':str(report_path),'sha256':sha(report_path),'delivery':str(delivery_path),'delivery_sha256':sha(delivery_path),'passed':report.get('passed_with_stated_inheritance_limits'),'error':report.get('error')},ensure_ascii=True))
sys.exit(0 if report.get('passed_with_stated_inheritance_limits') else 1)
