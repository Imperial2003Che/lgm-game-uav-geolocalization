"""Explicit, separately pinned execution addendum to unchanged experiment plans.

The original plan hash always denotes the original registered job contract.
The addendum hash and execution_command denote the actual compatibility launch.
Only source-artifact path spelling may differ, after proving same file identity.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
MANIFEST = HERE / 'EXECUTION_ADDENDUM.json'
_ACTIVE = None

def require(value, message):
    if not value:
        raise RuntimeError(message)

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def no_science():
    require(not [n for n in sys.modules if n.split('.')[0] in
            {'torch', 'numpy', 'PIL', 'cv2', 'timm', 'albumentations', 'sample4geo'}],
            'Use a fresh process; no scientific modules may be imported before admission')

class Snapshot:
    def __init__(self, path, expected):
        self.path = Path(path).resolve(strict=True)
        before = self.path.stat()
        self.raw = self.path.read_bytes()
        after = self.path.stat()
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
                and len(self.raw) == after.st_size, 'File changed during first read')
        require(len(expected) == 64 and hashlib.sha256(self.raw).hexdigest() == expected,
                'Unexpected initial bytes: ' + str(self.path))
        self.digest = expected
        self.value()
    def value(self):
        return json.loads(self.raw.decode('utf-8-sig'))
    def unchanged(self):
        require(self.path.read_bytes() == self.raw, 'File changed after first read: ' + str(self.path))
    def artifact(self):
        return {'path': str(self.path), 'bytes': len(self.raw), 'sha256': self.digest}

def load_module(name, path):
    require(name not in sys.modules, 'Conflicting module name: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == Path(path).resolve(), 'Wrong imported source')
    return module

class Addendum:
    def __init__(self, expected):
        self.snapshot = Snapshot(MANIFEST, expected)
        self.manifest = self.snapshot.value()
        require(self.manifest['schema'] == 'same-file-path-execution-addendum.v1', 'Wrong addendum schema')
        self.verify_sources()
        self.registry = Snapshot(HERE / 'REGISTRY.json', self.manifest['registry_sha256']).value()
    def verify_sources(self):
        self.snapshot.unchanged()
        seen = set()
        for row in self.manifest['files']:
            path = Path(row['path']).resolve(strict=True)
            require(path not in seen, 'Duplicate addendum source')
            seen.add(path)
            require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],
                    'Addendum source changed: ' + str(path))
        self.snapshot.unchanged()
    def plan(self, family):
        row = self.registry['plans'][family]
        return Snapshot(row['path'], row['sha256'])
    def check_plan(self, family, plan, controller):
        self.verify_sources()
        declared = self.plan(family)
        require(plan == declared.value(), 'Original registered plan differs')
        require(Path(controller).resolve() == Path(self.registry['controllers'][family]['path']).resolve(),
                'Wrong compatibility controller')
        declared.unchanged()
    def evidence(self, family):
        return {'addendum': self.snapshot.artifact(),
                'execution_controller': self.registry['controllers'][family]['path'],
                'plan_role': 'unchanged original registered job contract',
                'command_role': 'command preserves registration; execution_command records actual launch'}
    def role_job(self, role):
        row = self.registry['roles'][role]
        plan = self.plan(row['family']).value()
        matches = [j for j in plan['jobs'] if j['id'] == row['job_id']]
        require(len(matches) == 1, 'Missing or duplicate original job')
        return row, matches[0]
    def command(self, family, job):
        self.verify_sources()
        declared = next(j for j in self.plan(family).value()['jobs'] if j['id'] == job['id'])
        require(all(job.get(k) == v for k, v in declared.items() if k != 'status'), 'Registered job fields changed')
        roles = [role for role, row in self.registry['roles'].items()
                 if row['family'] == family and row['job_id'] == job['id']]
        if not roles:
            return list(declared['command'])
        require(len(roles) == 1, 'Ambiguous compatibility role')
        return [declared['command'][0], '-B', str(HERE / 'run_evaluator.py'),
                '--role', roles[0], '--addendum-sha256', self.snapshot.digest]

def configure(expected):
    global _ACTIVE
    require(_ACTIVE is None, 'A controller may bind only one execution addendum')
    _ACTIVE = Addendum(expected)
    return _ACTIVE

def active():
    require(_ACTIVE is not None, 'Exact execution addendum is required')
    return _ACTIVE

def open_evaluator(addendum, role):
    """Import only original code; adapt one source-evidence callback explicitly."""
    no_science()
    row, job = addendum.role_job(role)
    for path, expected in job['source_sha256'].items():
        require(sha(path) == expected, 'Original queued input changed: ' + path)
    command = job['command']
    index = next(i for i, token in enumerate(command) if token.endswith('.py'))
    source = Path(command[index])
    arguments = command[index + 1:]
    prepared_path = Path(arguments[arguments.index('--prepared') + 1])
    prepared = Snapshot(prepared_path, job['source_sha256'][str(prepared_path.resolve())])
    aliases = load_module('explicit_same_file_aliases', Path(addendum.registry['alias_helper']))
    if role == 'camp_independent':
        require('protocol' not in sys.modules and 'run_evaluation' not in sys.modules, 'Conflicting original namespace')
        sys.path.insert(0, str(source.parent))
        protocol = load_module('protocol', source.parent / 'protocol.py')
        module = load_module('run_evaluation', source)
        guard = aliases.stable_source_evidence(protocol.source_evidence, prepared)
        protocol.source_evidence = guard
        module.source_evidence = guard
        args = module.parser().parse_args(arguments)
        require(args.stage == 'run', 'Only registered complete evaluation run is supported')
        require(module.read_prepared(prepared_path) == prepared.value(), 'Original prepared read differs')
    else:
        module = load_module('original_' + role, source)
        guard = aliases.stable_source_evidence(module.verify_sources, prepared)
        module.verify_sources = guard
        module.verify_seal(prepared.value())
        args = module.parse_args(arguments)
        require(args.stage == 'evaluate', 'Author compatibility entry only evaluates')
        guard()
    no_science()
    prepared.unchanged()
    return module, args, prepared, guard, job
