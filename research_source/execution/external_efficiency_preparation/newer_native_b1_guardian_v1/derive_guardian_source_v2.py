"""One offline byte-source derivation; never import the guardian or call APIs."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = '1ec7630ee4797e2d2162c11b59ef318d8815dfc4fd1a72c5966af2320663f744'


def replacement(text, before, after):
    if text.count(before) != 1:
        raise RuntimeError('Unique exact source block not found')
    return text.replace(before, after, 1)


def main():
    raw = (HERE / 'guardian.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('Initial author source bytes changed')
    source = raw.decode('utf-8')
    value = source
    value = replacement(value, "PROPOSED_B1_TTL_SECONDS = 900\n", "PROPOSED_B1_TTL_SECONDS = 900\nPREPARED_PINS = {\n    'CAMP': {'path': str(EX / 'camp_independent_evaluation_v3' / 'preparations' / 'frozen_three_seed_final_v3' / 'manifest.json'),\n             'bytes': 18480, 'sha256': '305c2b9b56fb6bde1781f459467a6718b9f7ed1df9779bcc7d4a209ca2244317'},\n    'DAC': {'path': str(EX / 'dac_independent_evaluation_v2' / 'preparations' / 'fixed_three_seed' / 'manifest.json'),\n            'bytes': 50947, 'sha256': '9923839dbc3c2504588fed791ef0489047d30c585f3efefd40dfc3da07da64ca'},\n}\n")
    value = replacement(value, "require(type(value) is dict and value['identity'] == identity and value['wait_result'] == 0,", "require(type(value) is dict and value['identity'] == identity and\n            type(value['wait_result']) is int and value['wait_result'] == 0,")
    value = replacement(value, "    integer(value['exit_code_unsigned_dword'])\n", "    for key in ('pid', 'creation_filetime_100ns', 'creation_utc_ticks'):\n        integer(value[key], 1)\n        require(value[key] == identity[key], 'Saved outer exit PID/creation differs')\n    integer(value['exit_code_unsigned_dword'])\n")
    value = replacement(value, "        descriptor(slot['prepared'])\n", "        descriptor(slot['prepared'])\n        require(slot['prepared'] == PREPARED_PINS[slot['method']], 'Exact original prepared descriptor required')\n")
    value = replacement(value, "    bootstrap = parse(_read_bound(slot['bootstrap']))\n    for key in ('launcher', 'interpreter'):\n", "    bootstrap = parse(_read_bound(slot['bootstrap']))\n    _confirm_actor(context, controller, bootstrap['controller_complete_command'], bootstrap['controller_image'], context.me)\n    for key in ('launcher', 'interpreter'):\n")
    value = replacement(value, "        if context is None:\n            # No scientific spawn has been reached, but this cannot assert an OS\n", "        if context is None:\n            _new_record(initial_dir / 'guardian_setup_partial_failure.json', {\n                'schema': 'newer-native-b1-guardian-setup-partial-failure.v1',\n                'error': str(error), 'traceback': traceback.format_exc(),\n                'scientific_spawn_reached': False, 'actual_lock_acquired': lock.locked,\n                'shared_lock_release_authorized': False, 'actual_guardian_exit_unknown': True})\n            # No scientific spawn has been reached, but this cannot assert an OS\n")
    # Exact old text retained; this new file and full delta do not mutate v1.
    written = value.encode('utf-8')
    patch = ''.join(difflib.unified_diff(source.splitlines(True), value.splitlines(True),
                    fromfile='guardian.py', tofile='guardian_v2.py')).encode('utf-8')
    outputs = ((HERE / 'guardian_v2.py', written), (HERE / 'guardian_v1_to_v2.patch', patch))
    for path, body in outputs:
        with path.open('xb') as stream:
            stream.write(body)
            stream.flush()
    result = {'schema': 'guardian-offline-source-derivation.v1',
              'source_executed_or_imported': False, 'OS_or_science_called': False,
              'inputs': [{'path': str(HERE / 'guardian.py'), 'bytes': len(raw), 'sha256': EXPECTED}],
              'outputs': [{'path': str(path), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()} for path, body in outputs]}
    with (HERE / 'SOURCE_DERIVATION.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
