"""Append the concrete local working-draft delivery; cooperative journal only."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os

HERE=Path(__file__).resolve().parent
EX=HERE.parent
OUT=EX.parent
TARGET=OUT/HERE.name

def read(p,limit=262144):
    p=Path(p)
    st=p.stat()
    assert 0 <= st.st_size <= limit
    with p.open('rb') as s:
        b=s.read(limit+1)
    assert len(b)==st.st_size and st.st_size==p.stat().st_size
    return b,dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def create(p,b):
    with p.open('xb') as s:
        s.write(b);s.flush();os.fsync(s.fileno())

raw,root_d=read(TARGET/'ROOT_CAMP_DAC_CONTEXT_ADOPTION.json')
root=json.loads(raw)
assert root['working_draft_adopted'] is True and root['final_manuscript'] is False
assert root['new_scientific_execution_or_result'] is False and root['Overleaf_updated'] is False
zip_d=root['zip']
assert Path(zip_d['path']).stat().st_size==zip_d['bytes']
_,tool_d=read(HERE/'ACTUAL_ADOPTION_TOOL_RETURN.json')
review_d=root['independent_delta_review']
_,actual_review=read(review_d['path'])
assert actual_review==review_d
obs_d=root['readonly_observation']
obs_raw,actual_obs=read(obs_d['path'])
assert actual_obs==obs_d
obs=json.loads(obs_raw)
stamp=datetime.now(timezone.utc).isoformat()
main,supp=root['outputs']
entry=f'''
## {stamp} 续跑交接：CAMP/DAC正式引用与相关工作本地工作稿已实际交付

新 OUT/manuscript_camp_dac_context_20260930_1948，只改变main.tex与refs.bib：新增两句CAMP/DAC视觉相关工作、两句作者权重复评/独立训练仍未完成及原报与项目结果分列；追加两正式2024 IEEE journal条目并沿当前缩写。32必要稿源从最新1538根继承复制核字节，除这两个源外30依赖精确相同；未插原报72值、新实验、比较/优势或协议等价，原484科学显示值及所有负结果/证据缺边/统计限制继承、不重验。

根实际405b51只读两已保存正式PDF第一页文本，支持新方法简介与身份字段，不是整论文/页码/72值第二验收。独立AI先有限评实际缺项，再只核真实delta与新增两BBL显示；没有编译、看图、网络或科学验收。独立具体报告 {review_d['path']}（{review_d['bytes']}B/{review_d['sha256']}），方法及局部实际工具回执同目录；保留此前assessment，不冒人工审稿。

本轮一次main与一次supp各pdflatex-bibtex-pdflatex-pdflatex，共8个实际MiKTeX命令exit0，禁自动安装/禁shellescape。实际辅助tool main f1aefc exit0/3.0459819s，supp08f8cb exit0/2.1448457s；不是科学双held退出。main {main['bytes']}B/{main['sha256']}（17p），supp {supp['bytes']}B/{supp['sha256']}（6p）。根已actual original看完23PNG：无新重叠裁剪/越界/undefined/??/overfull；main4underfullhbox，supp2hbox+3vbox保留。p17仅最后rerank/AQE两条仍为终稿版面待项，不缩字体/额外重编。44正文参考/3补充参考，Bib库54。旧compile helper历史docstring不替代这次共享refs变更后的真实supp命令。ROOT_VISUAL_REVIEW与实际工具记录在EX新目录。

根 ROOT_CAMP_DAC_CONTEXT_ADOPTION.json（{root_d['bytes']}B/{root_d['sha256']}）只采用本地引用/正文delta与实际编译、根视觉；科学接受继承。新ZIP {zip_d['path']}（{zip_d['bytes']}B/{zip_d['sha256']}，{root['zip_member_count']}成员逐CRC/size/SHA核），含原生可编辑TeX/Bib、PDF/BBL、预览、实际编译和有限审查/源；不是60.47GB全科学复现包、最终稿、最终Overleaf或投稿建议。旧16+6与所有旧稿/ZIP保留，既有Overleaf审阅项目未改。

实际只读19:36:28+01：EX/heartbeat_observation_20260930_1936/OBSERVATION_WRAPPER_INCLUDED.json（15692B/a42d15475ce3ae149e53526bc01febf5dd362efedb8dcc988e1e85af3eb8d72d），双广CIM同普通用户VISIO29480/parentexplorer13076、WeChatAppEx17896/parent5000、conhost14420/parentnode13212的当前完整命令/整数ticks，不当历史CPUouter/pipeline身份或旧exit。窄双CIM有conhost14420非空；EX/efficiency_incident_20260929_1448/observation_20260930_193627923/OBSERVATION.json（5767B/24bfd740e0e02036631a324d316196953ed32321978117cbee7340258eaebcf5），GPUquery实际exit0/26rows/gatefalse/T6absent，5state-heartbeat原bytes，同boot639263337875000000与0405当前合同匹配。旧Sep29 contract false只是历史合同，不当当前failure。根只读seal {obs_d['bytes']}B/{obs_d['sha256']}及实际d80542只保存关系/16state-log/carrierb0/三T6+Visioattempt absence，不是新OS/GPU capture/内存测量/未来准入；采用时再核文件原bytes，不推primary独立ownexit0。

无科学release/intent/native训练probe/recovery/retirement/COM/cleanup/锁/state动作，GPU非空不启动等待，既存用户Visio不附加关闭或绕empty门。42fit/官方231task/T3_66task/鲁棒性660+22、70PPTSVG/2main实际Visio/68file-onlyVisio和原完整包保持；file-only全XSD及repair-free应用打开导出编辑重开仍待，未扩大SDK/HH。T6/LOHO24fit192task/真实解释图/后继baseline/额外DAC/全gallery-ranking-parity-timing-onlineCLIP/终稿Visio正文/最终Overleaf投稿建议继续；冻结源/参数、五层+额外DAC、资源限制、全部负结果与证据限制保持，全部实际交付才删除跟进。本次仅新本地相关工作稿通知一次，同一实验阻塞静默。
'''.encode('utf-8')
entry_path=HERE/'HANDOFF_ENTRY.md'
create(entry_path,entry)
_,entry_d=read(entry_path)
handoff=EX/'HANDOFF.md'
old,before=read(handoff,1_048_576)
assert before['bytes']==514132 and before['sha256']=='2950abb94dbe9f5e332dfd896d892cab4ddc84fd9e3cfa60395a740c3523c148'
# This comparison and append is cooperative, not atomic against arbitrary writers.
with handoff.open('r+b') as s:
    assert s.read()==old
    s.seek(0,2);s.write(entry);s.flush();os.fsync(s.fileno())
new,after=read(handoff,1_048_576)
assert new[:len(old)]==old and new[len(old):]==entry
delivery=dict(schema='context-working-draft-concrete-delivery.v1',utc=stamp,root=root_d,zip=zip_d,
    independent_delta_review=review_d,actual_adoption_tool=tool_d,readonly_observation=obs_d,
    main=main,supplementary=supp,working_draft_only=True,scientific_execution=False,
    final_paper=False,Overleaf_updated=False,automatic_followup_retained=True)
create(HERE/'DELIVERY.json',(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
_,delivery_d=read(HERE/'DELIVERY.json')
receipt=dict(schema='cooperative-handoff-append-receipt.v1',utc=stamp,source=read(__file__)[1],
    before=before,after=after,append=entry_d,append_offset_bytes=len(old),
    prefix_byte_identical=True,append_exact=True,delivery=delivery_d,
    note='File-level cooperative append only, no arbitrary-writer atomicity or scientific exit/admission proof.')
create(HERE/'HANDOFF_APPEND_RECEIPT.json',(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
_,receipt_d=read(HERE/'HANDOFF_APPEND_RECEIPT.json')
print(json.dumps(dict(delivery=delivery_d,handoff_receipt=receipt_d,handoff_after=after),ensure_ascii=False))
