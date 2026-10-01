"""Preserve the reviewed pre-fix derivative and exact process-identity correction."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
source=HERE/'supervise_independent_comparisons.py'
after=source.read_text(encoding='utf-8')
old="""    if not preceding.get('supervisor_pid') or not preceding.get('supervisor_started_utc'):
        raise RuntimeError('Preceding process identity is missing')
"""
new="""    def require_identity(pid, started, label):
        if type(pid) is not int or pid <= 0 or not isinstance(started, str):
            raise RuntimeError('Missing positive process ID or start time: ' + label)
        try:
            stamp = datetime.datetime.fromisoformat(started)
        except ValueError as error:
            raise RuntimeError('Invalid process start time: ' + label) from error
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise RuntimeError('Process start time must include a timezone: ' + label)
    require_identity(preceding.get('supervisor_pid'), preceding.get('supervisor_started_utc'), 'author supervisor')
    for job in jobs:
        require_identity(job.get('pid'), job.get('started_utc'), job['id'])
"""
assert after.count(new)==1
before=after.replace(new,old)
before=before.replace("                require_identity(pid, started, 'nested child')\n", "                if not started:\n                    raise RuntimeError('Preceding child PID has no recorded start time')\n")
assert hashlib.sha256(before.encode()).hexdigest()=='d53aa0c34fc9d0645d4eccbd9955eddc7531533b9bcebe13f1301b202297568a'
assert hashlib.sha256(after.encode()).hexdigest()=='0b4678df15c4a1d76cb0665038fe3178bc1838f243439b8d81832e6b8ba6b04d'
(HERE/'independent_supervisor_before_identity_fix.py.txt').write_text(before,encoding='utf-8',newline='\n')
(HERE/'independent_supervisor_identity_fix.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='derived_before_identity_fix',tofile=source.name)),encoding='utf-8',newline='\n')
(HERE/'independent_supervisor_identity_fix.json').write_text(json.dumps({'before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':hashlib.sha256(after.encode()).hexdigest(),'finding':'A completed top-level job without a PID could bypass the recursive optional-owner scan.','correction':'Require positive integer, non-boolean supervisor/job PIDs and timezone-aware start times before all process-exit checks.','verification':'36 stdlib gate/lifecycle fixtures passed; 9 new invalid-identity fixtures.'},indent=2),encoding='utf-8')
original=(HERE/'supervise_latest_baselines.py').read_text(encoding='utf-8')
(HERE/'independent_supervisor.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),after.splitlines(True),fromfile='supervise_latest_baselines.py',tofile=source.name)),encoding='utf-8',newline='\n')
derivation_path=HERE/'independent_supervisor_derivation.json'
derivation=json.loads(derivation_path.read_text(encoding='utf-8'))
derivation['initial_derivative_sha256']=hashlib.sha256(before.encode()).hexdigest()
derivation['derived_sha256']=hashlib.sha256(after.encode()).hexdigest()
derivation['identity_correction']='independent_supervisor_identity_fix.json'
derivation['patch_scope']='Complete diff from fixed original latest supervisor to final independent successor.'
derivation_path.write_text(json.dumps(derivation,indent=2),encoding='utf-8')
print('Preserved exact pre-fix derivative and identity-check patch.')
