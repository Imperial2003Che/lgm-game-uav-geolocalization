"""CAMP/DAC B=1 request and candidate-artifact contract; public admission closed.

This stdlib-only module does not execute the original encoder or launch workers.
Consistency of saved artifacts is not independently captured execution evidence.
"""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
PREPARATION = HERE.parent
EXECUTION = PREPARATION.parent
REGISTRY = {
    'CAMP': ('camp_independent_evaluation_v3',
             '6212c4b317b0a7d097a65ce9946eaa0de357d042e15c16c0a7afe0a458ef32ee',
             '81724bf96c01bb030efc1e2b10b3ebcd5a92935b975f729174a2677c11b8fc19',
             'camp_independent_model.py', 395),
    'DAC': ('dac_independent_evaluation_v2',
            'adb5521285ca50cb21db0c235c1a476c634643b44489ffb7692b500623a8cfe0',
            '300714f02b21b3f038bb6364a31f80250ac7bfce771c1ced2ee5b8ab455710f8',
            'dac_independent_model.py', 402),
}
LIMITS = [
    'B=1 is an efficiency-reference in-memory derivative of the exact original prepared contract. Its only configuration difference is /settings/batch_size: 16 -> 1. Original prepared bytes and original encode_seed AST remain unchanged.',
    'Only the first query in each of the ten frozen tasks is selected, deduplicated in first-task occurrence order. This reference covers that measured query subset only, not every query or any fresh complete-gallery encoding.',
    'An original-image-to-full-ranking admission must additionally require independently fresh-encoded full galleries with exact frozen membership/order and full parity. Cached completed gallery descriptors cannot satisfy that requirement.',
    'Candidate result consistency, a caller array, a boolean, an existing parent-proof filename or a worker self-report cannot prove independent execution. Actual launcher and interpreter identities/creation ticks/command/parentage and separate OS-handle exit observations must be captured by a separately reviewed parent controller after streams close.',
    'The six method/seed references require separate released fresh workers; predecessor completion/exits, exact release, resources, shared byte lock and immutable plan bindings remain unimplemented here. No public execution or measurement admission is exposed.',
    'No scientific result, full-dataset online accuracy, full-gallery B=1 parity, timing, full FLOPs, T6 completion or manuscript readiness is claimed by this module.',
]


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def parse(raw):
    def pairs(items):
        out = {}
        for name, value in items:
            require(name not in out, 'Duplicate JSON object key')
            out[name] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(RuntimeError('Nonfinite JSON')))


def read_bound(record):
    require(set(record) == {'path', 'sha256', 'bytes'}, 'Exact artifact descriptor required')
    require(type(record['bytes']) is int and record['bytes'] >= 0, 'Invalid artifact size')
    require(isinstance(record['sha256'], str) and len(record['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in record['sha256']), 'Invalid artifact digest')
    path = Path(record['path']).resolve(strict=True)
    require(path == Path(record['path']), 'Use resolved absolute artifact path')
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Artifact changed while reading')
    require(len(raw) == record['bytes'] and sha(raw) == record['sha256'], 'Actual artifact differs')
    return raw


def artifact(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    result = {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}
    read_bound(result)
    return result


def source_recipe(method):
    """Read only pinned original source metadata; no original module import."""
    require(method in REGISTRY, 'Only the six CAMP/DAC method/seed slots are supported')
    directory, manifest_sha, encoder_sha, loader, states = REGISTRY[method]
    root = EXECUTION / directory
    manifest_record = artifact(root / 'PREPARATION_MANIFEST.json')
    require(manifest_record['sha256'] == manifest_sha, 'Pinned original manifest changed')
    manifest = parse(read_bound(manifest_record))
    bound = {}
    for item in manifest['files']:
        path = Path(item['path'])
        if not path.is_absolute():
            path = root / path
        resolved = str(path.resolve(strict=True))
        require(resolved not in bound, 'Duplicate original source path')
        bound[resolved] = dict(item, path=resolved)
    sources = []
    for filename in ('run_evaluation.py', 'protocol.py', loader):
        actual = artifact(root / filename)
        require(actual == bound[actual['path']], 'Original source differs from pinned manifest')
        sources.append(actual)
    require(sources[0]['sha256'] == encoder_sha, 'Unexpected original encoder')
    tree = ast.parse(read_bound(sources[0]).decode('utf-8-sig'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'encode_seed']
    require(len(nodes) == 1, 'Unique original encode_seed required')
    require(any(isinstance(n, ast.Assign) and ast.dump(n) == ast.dump(ast.parse(
        "batch_size=prepared['settings']['batch_size']").body[0]) for n in ast.walk(nodes[0])),
        'Original encoder must take prepared batch size')
    return {'method': method, 'manifest': manifest_record, 'sources': sources,
            'encoder_ast_sha256': sha(ast.dump(nodes[0]).encode()),
            'entrypoint': 'run_evaluation.encode_seed', 'original_state_count': states}


def derive_b1_prepared(prepared):
    require(type(prepared['settings']['batch_size']) is int and prepared['settings']['batch_size'] == 16,
            'Original native batch16 required')
    derived = copy.deepcopy(prepared)
    derived['settings']['batch_size'] = 1
    reverse = copy.deepcopy(derived)
    reverse['settings']['batch_size'] = 16
    require(reverse == prepared, 'Only the declared batch-size difference is allowed')
    return derived, {'json_pointer': '/settings/batch_size', 'original': 16, 'derived': 1,
        'original_canonical_sha256': sha(canonical(prepared)),
        'derived_canonical_sha256': sha(canonical(derived)),
        'original_prepared_file_modified': False,
        'scope': 'efficiency_reference_query_subset_only_not_a_new_scientific_evaluation_protocol'}


def select_queries(inventory, tasks):
    require(isinstance(inventory, list) and inventory, 'Frozen inventory is required')
    require(len({r['key'].casefold() for r in inventory}) == len(inventory), 'Duplicate normalized image key')
    require(len(tasks) == 10 and len({t['name'] for t in tasks}) == 10, 'Ten distinct frozen tasks required')
    selected, mapping = [], []
    for task in tasks:
        for field in ('query_indices', 'gallery_indices'):
            values = task[field]
            require(isinstance(values, list) and values and
                    all(type(i) is int and 0 <= i < len(inventory) for i in values) and
                    len(values) == len(set(values)), 'Malformed frozen task index list')
        idx = task['query_indices'][0]
        require(idx not in task['gallery_indices'], 'Cross-view query cannot be in its gallery')
        require(any(inventory[i]['label'] == inventory[idx]['label'] for i in task['gallery_indices']),
                'First query needs a positive in its complete gallery')
        if idx not in selected:
            selected.append(idx)
        mapping.append({'task': task['name'], 'query_index': idx, 'reference_row': selected.index(idx),
                        'full_gallery_indices': task['gallery_indices']})
    return selected, mapping


def request_from_completed(inputs, seed):
    """Future stdlib preparation from real CompletedInputs; no launch/release.

    It deliberately reuses the accepted completion binder, not caller summaries.
    This has not been run on future scientific inputs during source preparation.
    """
    module = sys.modules.get(type(inputs).__module__)
    expected = PREPARATION / 'newer_native_loader_v1/source_bindings.py'
    require(module is not None and Path(module.__file__).resolve() == expected and
            isinstance(inputs, module.CompletedInputs), 'Pinned CompletedInputs required')
    require(type(seed) is int and seed in (1, 2, 3), 'Registered seed required')
    module.no_scientific_modules()
    confirmed = module.bind_completed(inputs.method, inputs.binding.path, inputs.binding.artifact()['sha256'],
                                     inputs.completion.path, inputs.completion.artifact()['sha256'])
    require(confirmed == inputs, 'Completed binding changed')
    prepared = inputs.prepared.value()
    inventory_record = prepared['membership']['inventory']
    task_record = prepared['membership']['tasks']
    inventory = parse(read_bound(inventory_record))
    tasks = parse(read_bound(task_record))
    indices, task_map = select_queries(inventory, tasks)
    completed = inputs.completion.value()
    completion_records = {}
    for name, record in completed['artifacts'].items():
        name = name.replace('\\', '/')
        require(name not in completion_records, 'Duplicate completion artifact')
        completion_records[name] = record
    relative = f'seed_{seed}/image_content_sha256.jsonl'
    content_record = completion_records[relative]
    require(Path(content_record['path']).resolve() == inputs.completion.path.parent / relative,
            'Original content ledger escaped completion directory')
    content = [parse(line) for line in read_bound(content_record).splitlines()]
    require(len(content) == len(inventory), 'Content ledger coverage')
    for row, original in zip(content, inventory):
        require(row['key'] == original['key'] and row['bytes'] == original['bytes'] and
                len(row['sha256']) == 64 and all(c in '0123456789abcdef' for c in row['sha256']),
                'Original image-content key/order/size/digest')
    _, derivation = derive_b1_prepared(prepared)
    result = {'schema': 'newer-native-b1-request.v1', 'method': inputs.method, 'seed': seed,
        'source_recipe': source_recipe(inputs.method), 'prepared': inputs.prepared.artifact(),
        'binding': inputs.binding.artifact(), 'completion': inputs.completion.artifact(),
        'inventory': inventory_record, 'tasks': task_record, 'original_image_content': content_record,
        'seed_binding': inputs.seed_binding(seed), 'derivation': derivation,
        'selected_inventory_indices': indices, 'selected_rows': [inventory[i] for i in indices],
        'selected_content': [content[i] for i in indices], 'task_map': task_map,
        'reference_scope': 'first_query_per_frozen_task_deduplicated_only',
        'fresh_full_gallery_required_for_ranking_admission': True,
        'original_encoder_ast_modified': False, 'execution_authorized': False, 'limits': LIMITS}
    inputs.unchanged()
    return result


def decode_npy_fp32(raw, rows):
    """Read only bounded B1 descriptors, without NumPy or pickle."""
    require(type(rows) is int and 1 <= rows <= 10, 'Only ten-task query subset NPY allowed')
    require(raw[:6] == b'\x93NUMPY' and raw[6:8] in (b'\x01\x00', b'\x02\x00'), 'NPY version')
    width = 2 if raw[6] == 1 else 4
    require(len(raw) >= 8 + width, 'NPY header prefix')
    size = int.from_bytes(raw[8:8 + width], 'little')
    require(0 < size <= 16384 and len(raw) >= 8 + width + size, 'NPY header length')
    header = ast.literal_eval(raw[8 + width:8 + width + size].decode('latin1').strip())
    require(set(header) == {'descr', 'fortran_order', 'shape'} and header['descr'] == '<f4' and
            header['fortran_order'] is False and header['shape'] == (rows, 1024), 'NPY dtype/order/shape')
    payload = raw[8 + width + size:]
    require(len(payload) == rows * 1024 * 4, 'NPY exact payload length')
    values = struct.unpack('<' + str(rows * 1024) + 'f', payload)
    require(all(math.isfinite(v) for v in values), 'Descriptor nonfinite')
    for start in range(0, len(values), 1024):
        norm = math.sqrt(math.fsum(v * v for v in values[start:start + 1024]))
        require(abs(norm - 1) <= 2e-3, 'Original descriptor normalization bound')
    return {'shape': [rows, 1024], 'dtype': '<f4', 'payload_sha256': sha(payload),
            'normalization_check': 'stdlib binary64 norm within original 2e-3; no native NumPy parity claim'}


def check_candidate_artifacts(request, candidate, directory):
    """Check structural consistency only; intentionally returns no admitted array.

    request must ultimately be rebuilt with request_from_completed and bound to
    immutable launch bytes by the missing parent. Calling this pure candidate
    checker with fabricated dictionaries cannot unlock any measurement.
    """
    require(candidate['schema'] == 'newer-native-b1-candidate.v1', 'Candidate schema')
    require(candidate['method'] == request['method'] and candidate['seed'] == request['seed'], 'Method/seed binding')
    require(candidate['request_canonical_sha256'] == sha(canonical(request)), 'Exact request binding')
    require(candidate['source_recipe'] == request['source_recipe'] and candidate['derivation'] == request['derivation'],
            'Original source/config derivation binding')
    directory = Path(directory).resolve(strict=True)
    expected = {'descriptors.npy', 'image_content_sha256.jsonl', 'strict_complete_final_load.json', 'runtime_actual.json'}
    require(set(candidate['artifacts']) == expected, 'Exact original encoder artifact set')
    contents = {}
    for name, record in candidate['artifacts'].items():
        require(Path(record['path']).resolve(strict=True) == directory / name, 'Candidate artifact identity escaped')
        contents[name] = read_bound(record)
    rows = request['selected_rows']
    require(len(rows) == len(request['selected_content']) == len(request['selected_inventory_indices']), 'Selected row counts')
    content = [parse(line) for line in contents['image_content_sha256.jsonl'].splitlines()]
    require(content == request['selected_content'], 'Executed query content must match exact selected original content/order')
    summary = decode_npy_fp32(contents['descriptors.npy'], len(rows))
    proof = parse(contents['strict_complete_final_load.json'])
    for field in ('strict', 'assign', 'weights_only', 'mmap'):
        require(proof[field] is True, 'Original strict-load flag')
    require(proof['seed'] == request['seed'] and
            proof['complete_and_end_tensors_byte_equal'] == REGISTRY[request['method']][4], 'Original complete state count/seed')
    checkpoints = request['seed_binding']['checkpoints']
    require(proof['final_checkpoint_sha256'] == checkpoints['weights_end.pth']['sha256'] and
            proof['complete_checkpoint_sha256'] == checkpoints['checkpoint_complete.pth']['sha256'], 'Actual final/full checkpoint provenance')
    if request['method'] == 'CAMP':
        require(proof['learned_pos_scale_preserved'] is True and proof['model_factory_author_checkpoint_schema'] is False,
                'CAMP independent395 learned pos_scale')
    else:
        require(proof['three_classifier_heads_and_DSA_projection_retained'] is True and
                proof['author_checkpoint_values_loaded'] is False, 'DAC402 complete heads/DSA')
    runtime = parse(contents['runtime_actual.json'])
    prepared = parse(read_bound(request['prepared']))
    _, derivation = derive_b1_prepared(prepared)
    require(derivation == request['derivation'], 'Original prepared bytes and sole derived diff')
    require(Path(runtime['python']).resolve() == Path(prepared['python']).resolve() and
            runtime['thread_environment'] == prepared['settings']['thread_environment'] and
            runtime['amp'] is True and runtime['cuda_initialized'] is True and
            runtime['torch_cpu_threads'] == runtime['opencv_cpu_threads'] == 1, 'Original runtime settings')
    return {'candidate_artifact_consistency': True, 'descriptor_summary': summary,
            'independent_execution_proven': False, 'measurement_admitted': False,
            'fresh_gallery_proven': False, 'full_dataset_online_accuracy_proven': False,
            'full_t6_complete': False, 'manuscript_result': False, 'limits': LIMITS}


def execute_reference(*args, **kwargs):
    raise NotImplementedError('Fresh reference worker admission and actual external parent process collection are not integrated')


def admit_reference(*args, **kwargs):
    raise NotImplementedError('Candidate artifacts do not establish independent process execution or fresh full-gallery evidence; public admission remains closed')


def measure_task_ranking(*args, **kwargs):
    raise NotImplementedError('Original ranking public gate remains closed; no reference or ranking admission is exposed here')
