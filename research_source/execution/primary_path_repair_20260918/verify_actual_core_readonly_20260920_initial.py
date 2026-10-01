"""Real CPU import/cache/Windows-spawn verification, never a training result."""
from pathlib import Path
import dataclasses
import hashlib
import json
import multiprocessing
import os
import sys
import time
from project_paths import FrozenProjectPath, LOGICAL, NativePath
from source_contract import verify, sha
from run_formal_worker import load_core

EXPECTED = '11de17bd611431e4471eec1b8ac072a2159fbd02e4eb2cb041b4f3b0f00012a1'
HERE = Path(__file__).resolve().parent

def tensor_fingerprint(row):
    return {k: {'shape': list(v.shape), 'dtype': str(v.dtype),
                'sha256': hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest()}
            for k, v in row.items()}

def spawned_read(dataset, connection):
    # Unpickling the actual original dataset imports bare formal_retrieval.
    import formal_retrieval as core
    connection.send({'pid': os.getpid(), 'core_file': core.__file__,
                     'cuda_initialized': core.torch.cuda.is_initialized(),
                     'sample': tensor_fingerprint(dataset[0]),
                     'global_path_is_native': core.Path is NativePath})
    connection.close()

def main():
    provenance = verify(EXPECTED)
    ledger_path = LOGICAL / 'lgm_game_pytorch/runs/frozen_formal_matrix_ledger.json'
    config_path = LOGICAL / 'lgm_game_pytorch/runs/formal_main/university1652/visual_style/seed_2/run_config.json'
    unchanged = {str(p): sha(p) for p in (ledger_path, config_path)}
    ledger = json.loads(ledger_path.read_bytes())
    config = json.loads(config_path.read_bytes())['immutable_config']
    core = load_core()
    assert not any(n == 'lgm_game_pytorch' or n.startswith('lgm_game_pytorch.') for n in sys.modules)
    assert not core.torch.cuda.is_initialized()
    cache_reports = []
    for name, inputs in ledger['frozen_inputs'].items():
        cache = FrozenProjectPath(inputs['evidence_path'])
        store = core.EvidenceStore.load([cache])
        descriptors = [dataclasses.asdict(d) for d in store.cache_descriptors]
        assert descriptors[0]['cache_sha256'] == inputs['evidence_sha256']
        assert descriptors[0]['cache_path'] == str(cache)
        if name == 'university1652':
            assert descriptors == config['evidence_caches']
            records = core.derive_all_records(store, FrozenProjectPath(inputs['data_root']), name)
            protocol = core.build_training_protocol(records, name, 0.0, 2, [])
            assert protocol.protocol_summary == config['protocol']
            _, eval_transform = core.build_transforms(256, 224)
            query = protocol.train_queries[0]
            tiny = core.PairTrainingDataset([query], {query.label: protocol.train_gallery_by_label[query.label]},
                                            store, eval_transform, 'visual_style', 2)
            expected = tensor_fingerprint(tiny[0])
            context = multiprocessing.get_context('spawn')
            receiver, sender = context.Pipe(duplex=False)
            child = context.Process(target=spawned_read, args=(tiny, sender))
            child.start()
            sender.close()
            if not receiver.poll(90):
                child.terminate(); child.join(15)
                raise RuntimeError('CPU spawned dataset read timed out')
            spawn_result = receiver.recv()
            receiver.close()
            child.join(30)
            if child.is_alive():
                child.terminate(); child.join(15)
                raise RuntimeError('CPU spawned dataset did not exit')
            assert child.exitcode == 0 and spawn_result['sample'] == expected
            assert spawn_result['cuda_initialized'] is False and spawn_result['global_path_is_native'] is True
            spawn_result['actual_exit_code'] = child.exitcode
            spawn_result['same_actual_tensors'] = True
            del tiny, records, protocol
        cache_reports.append({'dataset': name, 'rows': len(store.paths), 'descriptors': descriptors})
        del store
    assert not core.torch.cuda.is_initialized()
    assert all(sha(Path(p)) == value for p, value in unchanged.items())
    verify(EXPECTED)
    result = {'scope': 'Original baseline CPU cache validation and one actual Windows spawned original dataset sample; no model/GPU/training/evaluation',
              'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'python': sys.executable,
              'source': provenance, 'caches': cache_reports, 'spawn': spawn_result,
              'frozen_config_cache_and_protocol_exact': True, 'unchanged_files': unchanged,
              'cuda_initialized': False, 'scientific_result': False}
    output = HERE / 'ACTUAL_CORE_CPU_READONLY_20260920.json'
    with output.open('x', encoding='utf-8') as stream: json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'report': str(output), 'sha256': sha(output), 'status': 'passed_no_training'}, ensure_ascii=False))

if __name__ == '__main__': main()
