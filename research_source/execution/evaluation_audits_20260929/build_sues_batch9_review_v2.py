"""Repair only bounded audit output path length; retain rejected source and report."""
from pathlib import Path
import hashlib
import difflib

here = Path(__file__).parent
base_path = here / 'review_sues_batch11.py'
base = base_path.read_text(encoding='utf-8')
old = here / 'review_sues_batch9.py'
prior = old.read_text(encoding='utf-8')
assert hashlib.sha256(base_path.read_bytes()).hexdigest() == 'a1e79940cb32c2ed1e97a7cc87cb9199526ece5bd88ca6674ee7a8a506fe3c65'
assert hashlib.sha256(old.read_bytes()).hexdigest() == '9d00eccdb6afeb0f11f13d2822580b8f9e18a8e9e31a1babbcb544cc12210824'
s = prior.replace("('sues_batch9_' + STAMP)", "('sues_batch9_v2_' + STAMP)")
s = s.replace("snapshot(HERE / 'REVIEW_SUES_BATCH9_SOURCE_DIFF.patch')", "snapshot(HERE / 'REVIEW_SUES_BATCH9_V2_SOURCE_DIFF.patch')")
anchor = "    check(sum(s.family == 'formal_main' for s in specs) == 6 and sum(s.family == 'formal_sensitivity' for s in specs) == 3, 'Exact six main and three sensitivity runs')\n"
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + "    snapshot_tags = {spec.identifier: 'run%02d' % index for index,spec in enumerate(specs, 1)}\n    check(len(set(snapshot_tags.values())) == 9, 'Unique short audit snapshot directories')\n    report['snapshot_subdirectory_to_identifier'] = {tag:identifier for identifier,tag in snapshot_tags.items()}\n")
s = s.replace("f'{spec.identifier}/", "f'{snapshot_tags[spec.identifier]}/")
anchor = "    prior_path = HERE / 'ROOT_SUES_BATCH11_ADOPTION_20260929.json'\n"
assert s.count(anchor) == 1
s = s.replace(anchor, "    rejected_source = snapshot(HERE / 'review_sues_batch9.py', expected='9d00eccdb6afeb0f11f13d2822580b8f9e18a8e9e31a1babbcb544cc12210824')[1]\n    rejected_report = snapshot(HERE / 'sues_batch9_20260929_045040_919667/SUES_BATCH9_EVALUATION_REVIEW.json', expected='ef02d00042da74a9f44a10d040de8f1f2a7ff3dc33998062cb9062e9fdcf68a5')[1]\n    report['previous_rejected_audit_attempt'] = {'source':rejected_source,'report':rejected_report,'reason':'Audit snapshot output exceeded Windows path length; no scientific artifact changed. Only audit output tags shortened in v2.','accepted_from_rejected_attempt':False}\n" + anchor)
assert "f'{spec.identifier}/" not in s
compile(s, '<derived-audit-v2>', 'exec')
new = here / 'review_sues_batch9_v2.py'
with new.open('x', encoding='utf-8', newline='\n') as f:
    f.write(s)
with (here / 'REVIEW_SUES_BATCH9_V2_SOURCE_DIFF.patch').open('x', encoding='utf-8', newline='\n') as f:
    f.write(''.join(difflib.unified_diff(base.splitlines(True),s.splitlines(True),fromfile=str(base_path),tofile=str(new))))
with (here / 'REVIEW_SUES_BATCH9_V1_TO_V2_DIFF.patch').open('x', encoding='utf-8', newline='\n') as f:
    f.write(''.join(difflib.unified_diff(prior.splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new))))
print(new)
print(hashlib.sha256(new.read_bytes()).hexdigest())
