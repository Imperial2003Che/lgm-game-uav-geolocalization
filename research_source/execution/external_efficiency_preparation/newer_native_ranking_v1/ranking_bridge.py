"""Future CAMP/DAC sample ranking bridge; no CLI, launches or scientific imports.

This closes only the native descriptor-to-full-gallery and raw-image-to-ranking
measurement interface. A released fresh worker, real original B=1 reference,
full-gallery re-encoding/parity and actual process exits remain caller duties.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
PREPARATION = HERE.parent
DEPENDENCIES = {
    'newer_native_ops_v1': 'c1c6bab09912c26779917fc0875824fd1e26203cfc2ba55a4d77940e8b51af8d',
    'newer_native_loader_v1': '1a5c34aac80187bda88eaffd24ba9756399d77b741d928047f40c5b3efe1d7c5',
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def artifact(path):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            'Artifact changed during hashing')
    return {'path': str(path), 'bytes': after.st_size, 'sha256': digest}


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return artifact(path)


def save_array(np, path, value):
    with Path(path).open('xb') as stream:
        np.save(stream, value, allow_pickle=False)
    return artifact(path)


def save_arrays(np, path, values):
    with Path(path).open('xb') as stream:
        np.savez_compressed(stream, **values)
    return artifact(path)


def verify_dependency_sources():
    """Verify existing immutable manifests, without reopening any checkpoints."""
    checked = []
    for name, expected in DEPENDENCIES.items():
        manifest_path = PREPARATION / name / 'SOURCE_MANIFEST.json'
        binding = artifact(manifest_path)
        require(binding['sha256'] == expected, 'Pinned native dependency manifest changed')
        manifest = json.loads(manifest_path.read_bytes())
        for filename in (('native_ops.py',) if name.endswith('ops_v1') else
                         ('native_load.py', 'source_bindings.py', 'path_aliases.py')):
            path = (PREPARATION / name / filename).resolve(strict=True)
            rows = [row for row in manifest['files'] if Path(row['path']).resolve() == path]
            require(len(rows) == 1 and artifact(path) == rows[0], 'Pinned native dependency source changed')
            checked.append(rows[0])
        require(artifact(manifest_path) == binding, 'Dependency manifest changed after reading')
        checked.append(binding)
    return checked


@dataclass(frozen=True)
class TaskSelection:
    task_name: str
    query_index: int
    gallery_indices: tuple
    query_row: dict
    gallery_rows: tuple


def select_first_query(inventory, tasks, task_name):
    require(isinstance(inventory, list) and inventory, 'Complete inventory required')
    keys = [row['key'].casefold() for row in inventory]
    require(len(set(keys)) == len(keys), 'Duplicate normalized image key')
    require(isinstance(tasks, list) and len(tasks) == 10 and
            len({row['name'] for row in tasks}) == 10, 'Exactly ten distinct frozen tasks required')
    matches = [row for row in tasks if row['name'] == task_name]
    require(len(matches) == 1, 'Task is not in the exact frozen task registry')
    task = matches[0]
    for name in ('query_indices', 'gallery_indices'):
        indices = task[name]
        require(isinstance(indices, list) and indices and
                all(type(i) is int and 0 <= i < len(inventory) for i in indices) and
                len(indices) == len(set(indices)), 'Invalid or duplicate task image indices')
    query_index = task['query_indices'][0]
    gallery = tuple(task['gallery_indices'])
    query = inventory[query_index]
    gallery_rows = tuple(inventory[i] for i in gallery)
    require(query_index not in gallery, 'Cross-view query must not overwrite a gallery descriptor')
    require(any(row['label'] == query['label'] for row in gallery_rows),
            'Selected query lacks a positive in the entire official gallery')
    return TaskSelection(task_name, query_index, gallery, query, gallery_rows)


def completion_artifact(completed, completion_path, relative):
    """Normalize serialized separators only; actual file identity stays checked."""
    rows = {}
    for key, value in completed['artifacts'].items():
        key = key.replace('\\', '/')
        require(key not in rows, 'Duplicate normalized completion artifact')
        rows[key] = value
    require(relative in rows, 'Required completed descriptor artifact missing')
    item = rows[relative]
    root = Path(completion_path).resolve(strict=True).parent
    target = (root / relative).resolve(strict=True)
    require(target.is_relative_to(root) and target == Path(item['path']).resolve(strict=True),
            'Descriptor artifact escaped or has a different file identity')
    require(artifact(target) == item, 'Actual completed descriptor bytes changed')
    return item


def completed_query_content(completed, completion_path, seed, inventory, query_index):
    """Bind this exact query to the bytes used by original completed encoding."""
    item = completion_artifact(completed, completion_path,
                               f'seed_{seed}/image_content_sha256.jsonl')
    selected = None
    count = 0
    with Path(item['path']).open('r', encoding='utf-8') as stream:
        for index, line in enumerate(stream):
            require(index < len(inventory), 'Completed content inventory has extra rows')
            row = json.loads(line)
            expected = inventory[index]
            require(isinstance(row, dict) and row.get('key') == expected['key'] and
                    type(row.get('bytes')) is int and row['bytes'] >= 0 and
                    row['bytes'] == expected['bytes'],
                    'Completed content key/order/size differs from exact inventory')
            digest = row.get('sha256')
            require(isinstance(digest, str) and len(digest) == 64 and
                    all(char in '0123456789abcdef' for char in digest),
                    'Invalid completed image content SHA256')
            if index == query_index:
                selected = row
            count += 1
    require(count == len(inventory) and selected is not None,
            'Completed content inventory is incomplete or query missing')
    require(artifact(item['path']) == item, 'Completed content inventory changed while reading')
    return selected, item


def full_stable_ranking(np, descriptor, gallery):
    """Same FP32 CPU inner product and stable full sort as the pinned helpers."""
    return np.argsort(-(descriptor @ gallery.T), axis=1, kind='stable')


def preserve_failure(np, output, error):
    arrays = {}
    for attribute, filename in (('actual_descriptor_array', 'failure_actual_descriptor.npy'),
                                ('expected_descriptor_array', 'failure_reference_descriptor.npy')):
        if hasattr(error, attribute):
            arrays[attribute] = save_array(np, output / filename, getattr(error, attribute))
    return write_json(output / 'failure.json', {'status': 'failed', 'error': str(error),
        'traceback': traceback.format_exc(), 'evidence': getattr(error, 'evidence', None),
        'actual_arrays': arrays, 'scientific_completion_claimed': False})


def _measure_ranking_paths(slot, selection, gallery, reference_b1, output, native_ops):
    """Called after actual completed input/source checks; no admission shortcut."""
    ops = slot.operations
    np, components, runtime = ops.runtime.numpy, ops.components, ops.runtime
    helper = slot.original_package.protocol.helpers()
    prepared = slot.inputs.prepared.value()
    image = helper.record_path(selection.query_row, prepared['membership']['roots'])
    image_before = artifact(image)
    require(image_before['bytes'] == selection.query_row['bytes'], 'Selected image size changed')
    require(all(image_before[key] == selection.expected_image_content[key]
                for key in ('bytes', 'sha256')),
            'Selected image bytes differ from completed original encoding')
    measured, arrays = native_ops.measure_sample(ops, image, reference_b1,
        completed_batch_descriptor=selection.completed_batch_descriptor)
    for name, value in arrays.items():
        if value is not None:
            save_array(np, output / (name + '.npy'), value)
    reference_rank = full_stable_ranking(np, reference_b1, gallery)
    save_array(np, output / 'original_B1_full_ranking.npy', reference_rank)

    def raw_operation():
        return full_stable_ranking(np, ops.raw_descriptor_cpu(image), gallery)

    before = components._checked_call(runtime, raw_operation)
    save_array(np, output / 'raw_full_ranking_before.npy', before)
    require(bool(np.array_equal(before, reference_rank)), 'Raw ranking differs from original B=1 ranking before timing')
    residents = {'independent_native_model': ops.model}
    ranking = components.measure_operation(runtime,
        lambda: full_stable_ranking(np, reference_b1, gallery), clock='synchronized_wall',
        scope='resident CPU FP32 B=1 descriptor -> CPU FP32 scores against entire original gallery -> complete stable argsort; CUDA synchronization overhead included; no decode/forward/AP bookkeeping',
        resident_models=residents)
    ranking['runtime_flags'] = dict(ranking['runtime_flags'])
    ranking['runtime_flags'].pop('native_formal_autocast', None)
    ranking['runtime_flags'].pop('native_clip_autocast', None)
    ranking['ranking_precision'] = 'CPU NumPy FP32; no model forward or AMP in this scope'
    raw = components.measure_operation(runtime, raw_operation, clock='synchronized_wall',
        scope='warm-file B=1 bytes -> original OpenCV/RGB/384 transform -> blocking H2D -> native FP16 forward/normalization -> CPU FP32 descriptor -> CPU FP32 full-gallery scores and complete stable argsort; excludes gallery encoding/model loading/AP bookkeeping',
        resident_models=residents)
    after = components._checked_call(runtime, raw_operation)
    save_array(np, output / 'raw_full_ranking_after.npy', after)
    require(bool(np.array_equal(after, reference_rank)), 'Raw ranking changed after timing')

    # Independent original helper retains all positive ranks/AP for this ONE
    # online query. This is never represented as full-dataset online accuracy.
    query = helper.Record(selection.query_row['key'], selection.query_row['label'])
    records = tuple(helper.Record(row['key'], row['label']) for row in selection.gallery_rows)
    task = helper.Task(selection.task_name, (query,), records)
    encoded = {row['key'].casefold(): gallery[i] for i, row in enumerate(selection.gallery_rows)}
    encoded[query.relative_path.casefold()] = arrays['raw_B1'][0]
    online_metrics, online_arrays = helper.rank_with_query_evidence(task, encoded, prepared['settings']['ranking_chunk_size'])
    require(int(online_arrays['top1_gallery_indices'][0]) == int(reference_rank[0, 0]),
            'Timed complete ranking differs from original online helper top1')
    labels = np.asarray([row['label'] for row in selection.gallery_rows])
    timed_positive_ranks = np.flatnonzero(labels[reference_rank[0]] == query.label) + 1
    require(bool(np.array_equal(timed_positive_ranks, online_arrays['positive_ranks_1based'])),
            'Timed full ranking positive positions differ from original helper')
    query_file = output / 'original_online_one_query_arrays.npz'
    save_arrays(np, query_file, online_arrays)
    validation = helper.validate_query_arrays(query_file, task, online_metrics)
    require(artifact(image) == image_before, 'Selected image changed during ranking measurements')
    measured.update({'descriptor_to_full_gallery_ranking': ranking,
        'raw_file_to_full_gallery_ranking': native_ops.measurement_metadata(raw),
        'ranking_measured': True, 'ranking_score_type': 'CPU FP32 inner_product',
        'ranking_sort': 'all gallery rows, stable descending', 'gallery_rows': int(gallery.shape[0]),
        'gallery_provenance': 'actual completed same-seed original descriptor artifact; not freshly re-encoded here',
        'online_one_query_metrics': online_metrics, 'online_one_query_array_validation': validation,
        'sampling_rule': 'first query in exact frozen task order',
        'full_gallery_metrics_recomputed_here': False, 'full_gallery_descriptors_reencoded_here': False,
        'full_dataset_online_accuracy_measured': False, 'full_t6_complete': False,
        'original_B1_provenance_verified_here': False, 'scientific_acceptance': False,
        'manuscript_result': False})
    return measured


def measure_task_ranking(slot, task_name, original_b1, output_directory):
    """Fail closed until an independently executed B=1 evidence gate is bound.

    A caller-supplied array or boolean is not independent reference evidence.
    This version is source preparation only and cannot admit a measurement.
    """
    raise NotImplementedError('Independent original B=1 execution evidence contract is not integrated; '
                              'this source-preparation interface cannot admit measurements')


def _measure_task_ranking_unreleased(slot, task_name, original_b1, output_directory):
    """Unreleased internal primitive; caller would hold admission/GPU lock.

    original_b1 is the separately executed original B=1 descriptor of the exact
    first query. Its future executor and immutable provenance remain an explicit
    missing prerequisite. Do not call this primitive to bypass the public gate.
    This function adds no CLI or release/launch path.
    """
    dependencies = verify_dependency_sources()
    loader_module = sys.modules.get(type(slot).__module__)
    require(loader_module is not None and Path(loader_module.__file__).resolve() ==
            (PREPARATION / 'newer_native_loader_v1/native_load.py').resolve() and
            isinstance(slot, loader_module.LoadedSlot), 'Use the pinned strict LoadedSlot')
    native_ops = sys.modules.get('_newer_native_fixed_operations')
    require(native_ops is not None and Path(native_ops.__file__).resolve() ==
            (PREPARATION / 'newer_native_ops_v1/native_ops.py').resolve(), 'Use the pinned native operations')
    require(slot.method in ('CAMP', 'DAC') and type(slot.seed) is int and slot.seed in (1, 2, 3),
            'Only one original independent CAMP/DAC seed per worker')
    require(id(slot.operations.model) == slot.provenance['actual_model_object_id'] and
            slot.provenance['strict_complete_final_load']['strict'] is True and
            len(slot.operations.model.state_dict()) == (395 if slot.method == 'CAMP' else 402),
            'Strict complete native model identity changed')
    slot.inputs.unchanged()
    source_before = native_ops.verify_source_recipe(slot.method)
    prepared = slot.inputs.prepared.value()
    b = sys.modules[loader_module.b.__name__]
    inventory_item, tasks_item = prepared['membership']['inventory'], prepared['membership']['tasks']
    inventory = b.FrozenJson.read(inventory_item['path'], inventory_item['sha256'])
    tasks = b.FrozenJson.read(tasks_item['path'], tasks_item['sha256'])
    selection = select_first_query(inventory.value(), tasks.value(), task_name)
    completed = slot.inputs.completion.value()
    descriptor_record = completion_artifact(completed, slot.inputs.completion.path,
                                          f'seed_{slot.seed}/descriptors.npy')
    expected_image_content, content_record = completed_query_content(completed,
        slot.inputs.completion.path, slot.seed, inventory.value(), selection.query_index)
    require(slot.inputs.seed_binding(slot.seed)['checkpoints']['weights_end.pth'] ==
            slot.provenance['checkpoint'], 'Loaded checkpoint differs from completed seed')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    np = slot.operations.runtime.numpy
    mapped = None
    try:
        mapped = np.load(descriptor_record['path'], mmap_mode='r', allow_pickle=False)
        require(mapped.shape == (len(inventory.value()), 1024) and mapped.dtype == np.dtype('float32'),
                'Completed native descriptor shape/type differs')
        gallery = mapped[list(selection.gallery_indices)].copy()
        require(gallery.shape == (len(selection.gallery_indices), 1024) and bool(np.isfinite(gallery).all()),
                'Complete gallery descriptors are invalid')
        # Keep the frozen membership selection immutable while attaching the
        # actual completed-batch row for the existing diagnostic-only comparison.
        from types import SimpleNamespace
        selected = SimpleNamespace(**selection.__dict__,
            expected_image_content=expected_image_content,
            completed_batch_descriptor=mapped[selection.query_index:selection.query_index + 1].copy())
        write_json(output / 'selected_query_and_gallery.json', {'method': slot.method, 'seed': slot.seed,
            'task': task_name, 'query': selection.query_row, 'gallery_indices': selection.gallery_indices,
            'inventory': inventory.artifact(), 'tasks': tasks.artifact(),
            'completed_image_content': content_record, 'expected_query_content': expected_image_content,
            'descriptors': descriptor_record, 'prepared': slot.inputs.prepared.artifact(),
            'binding': slot.inputs.binding.artifact(), 'completion': slot.inputs.completion.artifact(),
            'model_load_provenance': slot.provenance, 'dependencies': dependencies,
            'original_B1_executor_provenance_required_from_caller': True})
        with slot.no_network(), slot.operations.runtime.torch.no_grad():
            result = _measure_ranking_paths(slot, selected, gallery, original_b1, output, native_ops)
        slot.inputs.unchanged(); inventory.unchanged(); tasks.unchanged()
        require(artifact(descriptor_record['path']) == descriptor_record and
                artifact(content_record['path']) == content_record and
                native_ops.verify_source_recipe(slot.method) == source_before and
                verify_dependency_sources() == dependencies, 'Input/source changed during ranking measurement')
        write_json(output / 'measurements.json', result)
        return result
    except BaseException as error:
        preserve_failure(np, output, error)
        raise
    finally:
        if mapped is not None and getattr(mapped, '_mmap', None) is not None:
            mapped._mmap.close()
