"""Preserve pre-execution schema assumption and seal final bounded audit."""
from pathlib import Path
import hashlib, difflib
here=Path(__file__).parent
path=here/'review_university_sensitivity3.py'
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='58075d374ed54055f98628d3216b5f1df1971ef6384d0ed5fc4c5d9a8e85f55b'
with (here/'review_university_sensitivity3_PREEXEC_STATUS_ASSUMPTION_58075.py').open('xb') as f:f.write(raw)
diff_path=here/'REVIEW_UNIVERSITY_SENSITIVITY3_SOURCE_DIFF.patch'
with (here/'REVIEW_UNIVERSITY_SENSITIVITY3_PREEXEC_STATUS_ASSUMPTION_DIFF.patch').open('xb') as f:f.write(diff_path.read_bytes())
text=raw.decode('utf-8').replace("check(parent['status'] == 'completed' and parent['exit_code'] == 0, 'Primary is not recorded completed')", "check(parent['status'] == 'completed', 'Primary is not recorded completed')\n    # Primary status has no exit_code field; this audit claims only each exact\n    # child parent-Popen event below, not an independently observed parent exit.")
text=text.replace("    results = []\n", "    check(report['original_validator_contract']['source_function_sha256'] == 'a553c2f641453d640833f3d50d1916d4f795a360e6a75d8aaaeb983410198978', 'Original completion validator changed')\n    results = []\n")
compile(text,str(path),'exec')
path.write_text(text,encoding='utf-8',newline='\n')
base=here/'review_batch6.py'
diff_path.write_text(''.join(difflib.unified_diff(base.read_text(encoding='utf-8').splitlines(True),text.splitlines(True),fromfile=str(base),tofile=str(path))),encoding='utf-8',newline='\n')
print(hashlib.sha256(path.read_bytes()).hexdigest())
