from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,os
D=Path(__file__).resolve().parent
EX=D.parent
def descriptor(p):
    r=Path(p).read_bytes()
    return {'path':str(p),'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()}
vpath=D/'AUTOMATION_UPDATE_VERIFICATION.json'
v=json.loads(vpath.read_bytes())
assert v['status']=='ACTIVE' and v['exact_prior_prefix_preserved'] is True
receipt=json.loads((D/'HANDOFF_APPEND_RECEIPT.json').read_bytes())
p=EX/'HANDOFF.md'
prior=p.read_bytes()
assert descriptor(p)==receipt['after']
stamp=datetime.now(timezone(timedelta(hours=1))).isoformat()
vbind=descriptor(vpath)
text=('\n\n### 当前宿主CPU控制交付后的跟进同步 — '+stamp+'\n\n'
'原automation经automation_update保持ACTIVE/每小时/名称/目标thread及其它字段，仅prompt/updated_at改变；原47154字符完整前缀保存。回读51267字符与提交仅末尾一个LF由app修剪。第一次严格全等读验exit1在写验证文件前发生，后续只核这一个差异和原前缀/其它字段，没有再次修改automation。AUTOMATION_UPDATE_VERIFICATION.json '+vbind['sha256']+'明确该范围，不称提交尾LF逐字一致。\n\n'
'本轮新的真实进程CPU控制已联合根报告/另finalizer/独立runtime+finalization scope交付，原v1失败与所有已用attempt/首根exit1保留；不重跑已过控制，不把普通Python CPU通过当原科学venv/B1/T6或后继release。原HANDOFF全部prefix与本轮append按字节验证，五层+额外DAC/冻结门/负结果/证据缺边/不关app不减参不消费额度完整保留；全部真实科研/终稿图件Visio/最终Overleaf/投稿建议完成前持续每小时跟进。\n').encode('utf-8')
with (D/'AUTOMATION_HANDOFF_APPEND.md').open('xb') as f:f.write(text)
with p.open('r+b') as f:
    assert f.read()==prior
    f.seek(0,2);f.write(text);f.flush();os.fsync(f.fileno())
assert p.read_bytes()==prior+text
out={'schema':'automation-sync-handoff-append.v1','utc':datetime.now(timezone.utc).isoformat(),'before':receipt['after'],'append':descriptor(D/'AUTOMATION_HANDOFF_APPEND.md'),'after':descriptor(p),'automation_verification':vbind,'source':descriptor(__file__),'exact_prior_prefix':True}
q=D/'AUTOMATION_HANDOFF_APPEND_RECEIPT.json'
with q.open('xb') as f:f.write((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps({'receipt':descriptor(q),'handoff_after':out['after']},ensure_ascii=False))

