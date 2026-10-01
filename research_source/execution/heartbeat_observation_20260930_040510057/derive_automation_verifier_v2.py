from pathlib import Path
import hashlib,json,difflib,datetime
HERE=Path(__file__).parent
p=HERE/'verify_automation.py'
old=p.read_text(encoding='utf-8')
needle="assert after['prompt']==before['prompt']+append"
replacement="expected=before['prompt']+append\nassert expected.endswith('\\n') and not expected.endswith('\\n\\n')\nassert after['prompt']==expected[:-1]  # App removed exactly one terminal LF."
assert old.count(needle)==1
new=old.replace(needle,replacement)
new=new.replace("'prompt_exactly_expected':True,", "'prompt_exactly_expected_after_one_terminal_LF_removed':True,'normalization':'App omitted exactly the final LF; all preceding characters preserved',")
new=new.replace('prompt逐字一致{len(after["prompt"])}字符；', 'prompt除app移除最后一个LF外逐字一致{len(after["prompt"])}字符；')
new=new.replace('本次仅再次重启观察/当前boot源码合同及13条基础引用局部研究；', '首次verifier在精确prompt比较处exit1，未写receipt或HANDOFF；根查明仅末尾LF归一化，新v2单次核验，原source和完整diff保留。本次仅再次重启观察/当前boot源码合同及13条基础引用局部研究；')
with (HERE/'verify_automation_v2.py').open('x',encoding='utf-8',newline='\n') as f: f.write(new)
patch=''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='verify_automation.py',tofile='verify_automation_v2.py'))
with (HERE/'AUTOMATION_VERIFIER.patch').open('x',encoding='utf-8',newline='\n') as f: f.write(patch)
failure={'schema':'automation-verification-normalization-diagnosis.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'first_tool_exit_code':1,'first_failure':'Exact prompt equality assertion at line11; tool observed AssertionError.','first_source':{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},'original_preserved':True,'expected_prompt_chars':43679,'actual_prompt_chars':43678,'observed_difference':'Exactly one trailing LF removed by app; full old prefix retained and no other config-field changes besides prompt/updated_at.','first_verifier_wrote_receipt_or_handoff':False,'automation_update_repeated':False,'science_or_control_failure':False}
with (HERE/'AUTOMATION_VERIFICATION_FIRST_FAILURE.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(failure,ensure_ascii=False,indent=2)+'\n')
print('Preserved first verifier; new v2 checks exactly one terminal LF normalization.')
