"""Record only the arrived incomplete AI review; no source/science adoption."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os
HERE=Path(__file__).resolve().parent;EX=HERE.parent
PEER=EX/'newer_native_b1_slot_bridge_review_20260930_1605'
def bind(p):
    b=p.read_bytes();assert len(b)<=256*1024
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,value):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return bind(p)
report=json.loads((PEER/'PARTIAL_REVIEW.json').read_bytes())
assert report['status']=='PARTIAL_INCOMPLETE_NO_PASS_NO_ADOPTION'
assert report['checker_actual_return'] is None and report['ast_execution_count']==0
assert report['independent_source_review_completed'] is False and report['root_source_adopted'] is False
inputs=[bind(PEER/name) for name in ['PARTIAL_REVIEW.json','PARTIAL_REVIEW.md','CHECKER_EXECUTION_STATUS.json','READ_TOOL_TRANSCRIPT.json']]
status=write(HERE/'ROOT_PENDING_BRIDGE_REVIEW_STATUS.json',{'schema':'root-arrived-incomplete-bridge-review-status.v1','utc':datetime.now(timezone.utc).isoformat(),
    'source':bind(Path(__file__).resolve()),'inputs':inputs,'root_read_entire_partial_json_md_checker_status':True,
    'read_tool_transcript_bytes_bound_without_root_complete_source_review':True,'selected_source_SHA_author_declared_not_rehashed_by_peer':True,
    'independent_review_complete':False,'root_source_adopted':False,'execution_released':False,'scientific_result_admitted':False,
    'scope_clue_not_concluded_defect':True,'no_old_suite_or_legacy_source_mutation':True,'parent_journal_record_kept':True})
handoff=EX/'HANDOFF.md';prefix=handoff.read_bytes()
assert len(prefix)==485944 and hashlib.sha256(prefix).hexdigest()=='e690829b582f6c1cd096e3114e56b93833020734e388d0b3b844fbf8307f782e'
text='\n\n'+datetime.now(timezone.utc).isoformat()+' — 同轮后到B1 partial独立AI记录（不通过/不采用）：\n'
text+='EX/newer_native_b1_slot_bridge_review_20260930_1605四文件已实际保存，根完整读PARTIAL_REVIEW JSON/MD与CHECKER_STATUS，仅绑定读工具转录bytes、不代根读完整源码。'
for d in inputs:text+=Path(d['path']).name+' '+str(d['bytes'])+'B/'+d['sha256']+'；'
text+='ROOT_PENDING_BRIDGE_REVIEW_STATUS '+str(status['bytes'])+'B/'+status['sha256']+'。其状态PARTIAL_INCOMPLETE_NO_PASS_NO_ADOPTION，AST/checker未创建/未运行、actualreturn=null；source SHA仅作者metadata非独立freshhash。该报告记三v2源/五patch完整文本读取及delegatedguardian文本旁证，但独立审查未完成、无root/source/science采用；scope字段仅未定论dormant静态线索。后到报告不能将FIRST关闭/None pins/未执行状态变为安全或科学许可。原journal/论文core/106成员ZIP均不回写/重跑，全未完成实验和冻结资源顺序限制/跟进完整保留。\n'
addition=text.encode('utf-8');assert handoff.read_bytes()==prefix
with handoff.open('ab') as f:f.write(addition);f.flush();os.fsync(f.fileno())
after=handoff.read_bytes();assert after==prefix+addition
receipt=write(HERE/'PARTIAL_REVIEW_HANDOFF_RECEIPT.json',{'schema':'cooperative-small-addendum-append.v1','utc':datetime.now(timezone.utc).isoformat(),
    'source':bind(Path(__file__).resolve()),'status':status,'prior_handoff':{'bytes':len(prefix),'sha256':hashlib.sha256(prefix).hexdigest()},
    'append':{'bytes':len(addition),'sha256':hashlib.sha256(addition).hexdigest()},
    'after':{'path':str(handoff),'bytes':len(after),'sha256':hashlib.sha256(after).hexdigest()},'prefix_preserved':True})
print(json.dumps({'status':status,'receipt':receipt},ensure_ascii=False))
