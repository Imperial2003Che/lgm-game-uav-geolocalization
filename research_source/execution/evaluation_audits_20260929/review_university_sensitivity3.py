"""Fixed three new University sensitivity evaluation runs. Checkpoint bytes MUST NOT be read."""
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
OUT = HERE / ('university_sensitivity3_' + STAMP)
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

report = {'schema': 'bounded-official-evaluation-audit-v1', 'started_utc': now(), 'review_script': {'path': str(Path(__file__)), 'sha256': sha(__file__)}, 'executable': sys.executable, 'scope': {'dataset': 'university1652', 'targets': [(label, 1) for label in ('backbone_resnet50', 'embed_dim_256', 'embed_dim_1024')], 'requested_evaluation_runs': 3, 'requested_retrieval_tasks': 9, 'out_of_batch_admitted': 0}, 'fresh_checkpoint_byte_hashes': 0, 'checkpoint_loaded': False, 'scientific_entrypoints_executed': False, 'live_files_modified': False}

try:
    prior_path = HERE / 'ROOT_SUES_BATCH11_ADOPTION_20260929.json'
    prior_sha = '657968ef1cf457bdc0b052c45cd0b2fd4f22dc687dc012d6f8482286e1fb052b'
    prior_eval = js(snapshot(prior_path, expected=prior_sha)[0])
    check(prior_eval['adopted_with_stated_inheritance_limits'] and prior_eval['accepted_total_evaluation_runs'] == 30 and prior_eval['accepted_total_retrieval_tasks'] == 150, 'Prior thirty-run adoption invalid')
    report['previous_eval_adoption'] = {'path':str(prior_path),'sha256':prior_sha,'accepted_runs':30,'accepted_tasks':150,'old_evaluation_artifacts_rehashed':False}
    snapshot(HERE / 'review_batch6.py', expected='80bbbaf3f3f1c36ae9b6dfcf149bc2bb3ff64aede5c4e1bcb5275e37658d41f0')
    snapshot(HERE / 'REVIEW_UNIVERSITY_SENSITIVITY3_SOURCE_DIFF.patch')
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
        # Only traverse the exact six later-fit roots to ROOT37; old main-fit
        # attachments are outside this new sensitivity evaluation audit.
        for dest, digest in refs(obj):
            if dest.name.startswith('ROOT_FIT_') and 'ADOPTION' in dest.name and dest.suffix == '.json':
                queue.append((dest, digest, key))
    required = ['ROOT_FIT_42_ADOPTION_20260928.json', 'ROOT_FIT_41_ADOPTION_20260928.json', 'ROOT_FIT_40_ADOPTION_20260928.json', 'ROOT_FIT_39_ADOPTION_20260928.json', 'ROOT_FIT_38_ADOPTION_20260928.json', 'ROOT_FIT_37_ADOPTION_20260927.json']
    check(all(name in documents for name in required), 'Inherited ROOT42-to-ROOT37 acceptance chain incomplete')
    check(all(documents[name]['adopted'] is True for name in required), 'Training root was not adopted')
    report['inherited_training_acceptance_graph'] = graph
    authority_reports, authority_rows, authority_ledgers = {}, {}, {}
    specific_sources = [
        ('formal_sensitivity/university1652/full/seed_1/resnet50/dim_512', 'ROOT_FIT_37_ADOPTION_20260927.json', 'completion_audits_20260927/BACKBONE_RESNET50_SEED1_COMPLETION.json', '140e3d91bd72b410874f6573b3d1ff21511801857d3b6043159d35d4c751f30d'),
        ('formal_sensitivity/university1652/full/seed_1/resnet18/dim_256', 'ROOT_FIT_38_ADOPTION_20260928.json', 'completion_audits_20260928/EMBED_DIM_256_SEED1_COMPLETION.json', 'a2652bf21befcf705152dead686d26dcb72be08f59857f724bc3d89a2f340324'),
        ('formal_sensitivity/university1652/full/seed_1/resnet18/dim_1024', 'ROOT_FIT_39_ADOPTION_20260928.json', 'completion_audits_20260928/EMBED_DIM_1024_SEED1_COMPLETION.json', 'f81c3eaa40918f630914b2d2c42f14eafa6abbadaed743f22711b10bfe0b14a3'),
    ]
    for identifier, root_name, relative, digest in specific_sources:
        source_path = EX / relative
        adoption = documents[root_name]
        check(adoption['independent_report']['path'] == str(source_path) and adoption['independent_report']['sha256'] == digest, 'Exact specific completion report edge missing')
        source = js(snapshot(source_path, expected=digest)[0])
        check(source['batch_passed'] and source['requested_new_fit_count'] == 1 and source['new_fits_fully_artifact_verified'] == 1, 'Specific training report not passed')
        matching = [r for r in source['new_runs'] if r['run_identifier'] == identifier]
        check(len(matching) == 1 and len(source['new_runs']) == 1, 'Specific training authority scope differs')
        entry = matching[0]
        check(entry['original_training_completion_issues'] == [] and entry['epochs_completed'] == 80 and entry['last_epoch'] == 79, 'Specific original training completion issues')
        check(identifier in adoption['completed_fit_ids'] and identifier in documents['ROOT_FIT_42_ADOPTION_20260928.json']['completed_fit_ids'], 'Training ID not in specific and final adopted roots')
        ledger_item = source['ledger_raw_snapshot']
        specific_ledger = js(snapshot(ledger_item['snapshot'], expected=ledger_item['sha256'])[0])
        check(source['registered_registry_sha256'] == specific_ledger['registered_registry_sha256'] and source['frozen_inputs_match'] is True, 'Specific source/registry/frozen binding invalid')
        record = specific_ledger['runs'][identifier]
        check(record['checkpoint_sha256'] == entry['artifacts_sha256_verified']['best.pt']['sha256'], 'Specific adopted ledger checkpoint differs from original artifact audit')
        authority_reports[identifier] = entry
        authority_ledgers[identifier] = specific_ledger
        authority_rows[identifier] = {'report_path':str(source_path),'report_sha256':digest,'historical_report_checkpoint_hashes_fresh_when_report_created':True,'independent_report':True,'root_adoption_document':root_name,'exact_root_report_edge_verified':True,'ledger_snapshot':ledger_item,'ledger_record':record}
    ledger = next(iter(authority_ledgers.values()))
    check(all(item['frozen_inputs'] == ledger['frozen_inputs'] and item['registered_registry_sha256'] == ledger['registered_registry_sha256'] for item in authority_ledgers.values()), 'Three adopted ledgers disagree on frozen inputs/registry')
    report['specific_training_report_authorities'] = list(authority_rows.values())
    report['inherited_checkpoint_sha_source'] = 'Each exact ROOT37/38/39 adopted independent report and that report SHA-bound ledger; all reached by final ROOT42 adoption chain'
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
    targets = {row[0] for row in specific_sources}
    specs = [s for s in sensitivity if s.dataset == 'university1652' and s.identifier in targets]
    check(len(specs) == 3 and {s.identifier for s in specs} == targets, 'Fixed three sensitivity-run scope')
    accepted = documents['ROOT_FIT_42_ADOPTION_20260928.json']['completed_fit_ids']
    check(all(s.identifier in accepted for s in specs), 'Run not in adopted training IDs')
    parent = js(snapshot(EX / 'status.json', 'PARENT_STATUS_RAW.json')[0])
    check(parent['status'] == 'completed', 'Primary is not recorded completed')
    # Primary status has no exit_code field; this audit claims only each exact
    # child parent-Popen event below, not an independently observed parent exit.
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
        label = Path(spec.run_dir).parent.name
        path = Path(spec.run_dir / 'best.pt')
        entry = authority_reports[spec.identifier]
        artifacts = entry['artifacts_sha256_verified']
        art = artifacts['best.pt']
        record = authority_ledgers[spec.identifier]['runs'][spec.identifier]
        check(record['checkpoint_sha256'] == art['sha256'], 'Specific adopted ledger versus historical checkpoint SHA disagreement')
        check(Path(art['path']) == path, 'Specific checkpoint path differs')
        current = stat(path)
        check(current['bytes'] == art['bytes'], 'Checkpoint size changed')
        allowed[os.path.normcase(os.path.abspath(path))] = (path, current, art['sha256'])
        cp_records[spec.identifier] = {'path':str(path),'inherited_sha256':art['sha256'],'specific_historical_artifact':art,'specific_training_authority':authority_rows[spec.identifier],'inherited_ledger_record':record,'stat_before':current,'limitation':'Current checkpoint metadata stability cannot establish current bytes. Inherited SHA is bound by exact ROOT37/38/39 report and its adopted ledger, reached by ROOT42.'}
        for name in ('run_config.json','history.json','run.log'):
            old_art = artifacts[name]
            snapshot(Path(spec.run_dir) / name, f'{label}_seed{spec.seed}/training_authority/{name}', expected=old_art['sha256'])
            check((Path(spec.run_dir) / name).stat().st_size == old_art['bytes'], 'Historical small training artifact size mismatch')
        historical_manifest = entry['manifest_raw_snapshot']
        manifest_digest = historical_manifest['sha256']
        snapshot(historical_manifest['snapshot'], f'{label}_seed{spec.seed}/historical_manifest.json', expected=manifest_digest)
        manifest_data, _ = snapshot(Path(spec.run_dir) / 'run_manifest.json', f'{label}_seed{spec.seed}/training_authority/run_manifest.json', expected=manifest_digest)
        historical_match = js(manifest_data)
        check(historical_match['payload_sha256'] == entry['manifest_payload_sha256'] and historical_match['run_config_sha256'] == entry['run_config_sha256'], 'Specific historical manifest/config canonical bindings')

    def scoped_sha(path):
        path = Path(path)
        key = os.path.normcase(os.path.abspath(path))
        if path.suffix.lower() in ('.pt', '.pth', '.ckpt'):
            check(key in allowed, 'Unapproved checkpoint hash request: ' + str(path))
            expected_path, before, digest = allowed[key]
            check(os.path.samefile(path, expected_path) and stat(path) == before, 'Checkpoint identity/stat changed')
            mode = 'inherited_exact_adopted_training_report_and_ledger_SHA_NOT_fresh_checkpoint_hash'
        else:
            digest = original_sha(path)
            mode = 'fresh_non_checkpoint_byte_hash'
        queries.append({'requested_path': str(path), 'sha256': digest, 'mode': mode})
        return digest

    report['original_validator_contract'] = {'name': 'evaluation_completion_issues', 'source_function_sha256': hashlib.sha256(inspect.getsource(runner.evaluation_completion_issues).encode()).hexdigest(), 'function_body_changed': False, 'module_Path_binding': 'adopted FrozenProjectPath', 'sha256_file_temporarily_wrapped': True, 'cached_checkpoint_allowlist': list(allowed), 'all_other_checkpoint_requests': 'reject', 'restored_in_finally': False, 'unconditional_fresh_checkpoint_validator_pass_claimed': False}
    check(report['original_validator_contract']['source_function_sha256'] == 'a553c2f641453d640833f3d50d1916d4f795a360e6a75d8aaaeb983410198978', 'Original completion validator changed')
    results = []
    try:
        runner.sha256_file = scoped_sha
        for spec in specs:
            label = Path(spec.run_dir).parent.name
            run = Path(spec.run_dir)
            ev = Path(spec.evaluation_dir)
            manifest = js(snapshot(ev / 'evaluation_manifest.json', f'{label}_seed{spec.seed}/evaluation_manifest.json')[0])
            config = js(snapshot(run / 'run_config.json', f'{label}_seed{spec.seed}/run_config.json')[0])
            train_manifest = js(snapshot(run / 'run_manifest.json', f'{label}_seed{spec.seed}/run_manifest.json')[0])
            history = js(snapshot(run / 'history.json', f'{label}_seed{spec.seed}/history.json')[0])
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
                data, binding = snapshot(actual_path, f'{label}_seed{spec.seed}/artifacts/{name}', declared['sha256'])
                check(len(data) == declared['bytes'] and before == stat(actual_path), 'Evaluation artifact size or stat changed')
                artifact_records.append(binding)
            check(len(artifact_records) == 7, 'Expected all seven evaluation artifacts')
            snapshot(ev / 'run.log', f'{label}_seed{spec.seed}/evaluation_run.log')
            metrics = js((OUT / f'{label}_seed{spec.seed}/artifacts/metrics.json').read_bytes())
            rows = list(csv.DictReader((OUT / f'{label}_seed{spec.seed}/artifacts/metrics.csv').read_text(encoding='utf-8-sig').splitlines()))
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
                with zipfile.ZipFile(OUT / f'{label}_seed{spec.seed}/artifacts/per_query_arrays/{name}_per_query.npz') as z:
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
            expected_command = runner.evaluation_command(project_paths.FrozenProjectPath(PKG / 'lgm_game_pytorch/formal_retrieval.py'), dataset, spec)
            expected_compat = [expected_command[0], str(compat / 'run_formal_worker.py'), '--path-compat-sha256', '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1'] + expected_command[2:]
            check(events[0]['command'] == expected_compat, 'Original frozen evaluation command differs')

            cp = cp_records[spec.identifier]
            check(train_manifest['artifacts']['best.pt']['sha256'] == cp['inherited_sha256'] and train_manifest['artifacts']['best.pt']['bytes'] == cp['stat_before']['bytes'], 'Train artifact inherited checkpoint identity')
            cp['stat_after'] = stat(run / 'best.pt')
            check(cp['stat_before'] == cp['stat_after'], 'Checkpoint stat changed during bounded audit')
            results.append({'identifier':spec.identifier,'evaluation_dir':str(ev),'original_evaluation_completion_issues_with_scoped_inherited_checkpoint_SHA':issues,'fresh_evaluation_artifact_verification':artifact_records,'inherited_checkpoint_SHA':cp,'parent_Popen_event':events[0],'tasks':task_checks,'evaluation_manifest_payload_sha256':manifest['payload_sha256'],'run_config_sha256':config['run_config_sha256'],'passed_with_stated_inheritance_limits':True})
    finally:
        runner.sha256_file = original_sha
        report['original_validator_contract']['restored_in_finally'] = runner.sha256_file is original_sha
    launcher_numbers = [r['parent_Popen_event']['pid'] for r in results]
    check(launcher_numbers == [35132,34416,36576], 'Fixed parent launcher event numbers')
    filter_text = ' OR '.join('ProcessId=' + str(int(pid)) for pid in launcher_numbers)
    ps = "$ErrorActionPreference='Stop'; [pscustomobject]@{ sampled_utc=[DateTime]::UtcNow.ToString('o'); processes=@(Get-CimInstance Win32_Process -Filter '" + filter_text + "' | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine) } | ConvertTo-Json -Depth 6 -Compress"
    observed = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],capture_output=True,text=True,check=True)
    cim = json.loads(observed.stdout)
    cim['queried_launcher_pid_numbers'] = launcher_numbers
    cim['current_pid_number_presence_is_not_original_identity_proof'] = True
    cim['pid_numbers_currently_absent'] = sorted(set(launcher_numbers) - {int(p['ProcessId']) for p in cim['processes']})
    check(len([q for q in queries if q['mode'].startswith('inherited_')]) == 3 and len([q for q in queries if q['mode'] == 'fresh_non_checkpoint_byte_hash']) == 6, 'Original validator hash query counts differ')
    report.update({'runs':results,'original_validator_hash_queries':queries,'known_old_launcher_CIM_observation':cim,'independent_windows_exit_handles_held':False,'old_interpreter_identity_known':False,'interpreter_exit_codes_observed':False,'exit_evidence_basis':'Original parent Popen exit0 events and this later CIM observation of known launcher PID numbers only; a reused PID is not proof of original process survival; no original launcher CreationDate or interpreter identity observed by this audit.','accepted_evaluation_run_count':3,'accepted_retrieval_task_count':9,'fresh_evaluation_artifact_count':21,'inherited_previous_evaluation_run_count':30,'inherited_previous_retrieval_task_count':150,'accepted_total_evaluation_run_count_with_this_batch':33,'accepted_total_retrieval_task_count_with_this_batch':159,'all_42_evaluations_accepted':False,'paper_means_or_conclusions_created':False,'evaluation_rerun_or_rank_recomputation':False,'limitations':['Checkpoint SHA inherited from each exact ROOT37/38/39 adopted independent completion report and its explicitly SHA-bound ledger, all reached through ROOT42; not freshly hashed.','Checkpoint size/mtime/stat stability cannot establish current byte identity.','Evidence cache SHA and full image-content inventory SHA inherited; official path membership and metadata counts independently checked.','Per-query stored arrays checked and aggregate consistency verified; no full distance matrix/reranking or recomputation of AP from all positive ranks.','Exactly three new sensitivity runs and nine new tasks; thirty prior runs/150 prior tasks inherited by adoption SHA without rereading old attachments. Other concurrent audit batches are not included or accepted here.']})
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
    report_path = save('UNIVERSITY_SENSITIVITY3_EVALUATION_REVIEW.json', json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8'))
    delivery = {'schema':'bounded-evaluation-delivery-v1','created_utc':now(),'report':{'path':str(report_path),'sha256':sha(report_path)},'source':report['review_script'],'files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.rglob('*') if p.is_file()]}
    delivery_path = save('DELIVERY.json', json.dumps(delivery,ensure_ascii=False,indent=2).encode('utf-8'))
    print(json.dumps({'report':str(report_path),'sha256':sha(report_path),'delivery':str(delivery_path),'delivery_sha256':sha(delivery_path),'passed':report.get('passed_with_stated_inheritance_limits'),'error':report.get('error')},ensure_ascii=True))
sys.exit(0 if report.get('passed_with_stated_inheritance_limits') else 1)
