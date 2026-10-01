from pathlib import Path
from datetime import datetime, timezone
import hashlib,json
H=Path(__file__).resolve().parent
E=H.parent;O=E.parent
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
r=O/'manuscript_evidence_revision_20260930_0202/ROOT_MANUSCRIPT_ADOPTION.json'
j=json.loads(r.read_text(encoding='utf-8'))
t=datetime.now().astimezone().isoformat()
text=f'''

## {t} — 已采用证据整合为实际编译的本地论文工作稿，16页正文+6页补充

根 ROOT_MANUSCRIPT_ADOPTION.json 在 OUT/manuscript_evidence_revision_20260930_0202，实际UTC {j['utc']}，SHA{pin(r)['sha256']}，208唯一小文件绑定。scope仅本地工作稿/独立AI内容审/根实际编译及看图/新论文ZIP；submission_ready=false，Overleaf未更新，new_scientific_runs=0/new_native_figures=0。新稿是原60.47GB合作伙伴包冻结后的补充交付，不是重建全项目；旧全包未读取、hash、回写或再验证。

新 LGM_GAME_Local_Evidence_Draft_20260930.zip：19645261B/19.65MB，SHA77f3f7b1543a48add1c5696386d9ecb10910ff03650e8a012eef70cd9b18d5b6，185成员。含正文/补充PDF、32源码/依赖文件加本地README、bibliography bbl、五新表、8份实际独立审核来源小表、22最终页预览、作者/独立审/编译记录与包清单；包内manifest排除自身，根报告置包旁避免自引用。原文件的本机绝对路径保留作来源，manifest映射包内副本。root packager首次真实逐成员解压CRC/SHA/size/member-set通过，根采用复核绑定不重复解压。
manuscript/main.pdf：16页/7146587B/f9cc81323a5d70b8442301869e983237c714912b7d80a8fa67b06dea8388dc1a；supplementary.pdf：6页/273353B/5a11c4f53e1090480612820b6f17204a031246fa4c4f02d5a517613ac8bd2c40。新main.tex20b3eb50d7f0583c2c538f1d6c0b5e85ea39b071f2701034024c100822a65092，supp8886ecc95e046284356e74c4f5b7ec9a096fdf0af710ceb010cf3bf643a43a10。

真实基底是 outputs/paper_label_revision_20260914/manuscript 的26依赖，未拿旧PDF冒充新编译。原semantic_results.tex为空注释，原摘要没有Full普遍胜出结论，故本轮是新结果整合而非纠正不存在的旧胜出数字。完整重写摘要/贡献/结果/讨论/结论，五新表覆盖官方全部11任务六配置R1/mAP、T3全部11任务两配置三指标、seed1敏感性全部11任务四设置；484显示scalar由保存数据格式转换，没有重新均值/SD/新统计。Full官方10/11 R1和mAP较低、T3全部11 meanR1较低明确保持；Street2S局部例外和低绝对值不隐藏。
三seed等权sampleSD非SE/CI；敏感性/扰动seed1不造SD。Full cached-clean/online-corrupt混合路径与64图诊断无等价阈值、T4共同Visual mask及132/330范围、T5各自selection及k/N分母/保存全前缀AURC/固定margin非posterior/空bin null/未独立bootstrap重采样均写入正文或补充；旧public-baseline单列，旧十图/文献/历史数值沿用，不新称科学或文献验收。best.pt最终固定epoch语义用训练源码/冻结checker与一份小manifest/config证实，42run整体验收仍继承原root，没有打开权重。

作者 EX/manuscript_revision_scope_20260930_0202：build_working_draft.py20588eba44ed52872190418e9c6b31f69aaeaf651b6e891b7c19bea853962e32；AUTHOR_INTEGRATION2b64fcf23782dee75f90b0d3bc25ee2e5b338f7956b045b1b8d531a85250d46b；TABLE_CELL_TRANSCRIPTIONS4a799ba00ea149d981042dbaf79247b75a53701898880d98f5d20126587c01e3；最终DELIVERY3e00c4bd9cf04881c9a4b6d966014c11ebf2c6100f336dc1ab17cdee8a08dd11。完整old→new和三修订diff/原源保留。应用已安装anti-defensive-writing仅凝练表达；用户冻结比较/必须保留负结果优先于skill不说输/重选口径，不重装skill、不新增用户批准门。
独立 EX/manuscript_evidence_review_20260930_0202：NUMERIC_TRANSCRIPTION_REVIEW b05d920126d3eb23810723a458746aa50828fb387c3173232cc0ff37b35eaabf首次484实际TeXscalar与保存CSV映射/单位/精度核验，不调用producer；QUERY_FRAGMENT_REVIEW4a9fdf25c4435b5df298a707879d79568ed2eed4aa7751045647b776595b0aa5首次16窄语义/保存字段核验。CONTENT_REVIEW b44cee8692d2fd67fe40ade1907c52f49d7aeb79ad2ce2d509f222b88c6f0cd7/50最终字节与窄diffchecks，DELIVERY084c7f3b4490083134b028521b4f8c82bfe4b6b97dd3b9cca9fac07f5b33ac7a，final_text23，未独立编译或看PDF。初始old_main误指另一历史副本，BASELINE_BINDING_ADDENDUMd1c3d776e5a13d22d73f6342cbd5248380930b2e2293117464ea90881f7d847f改正来源，原记录不改；该旧副本仅两caption差异。内容报告Human reading措辞不准确，必须联合REVIEW_METHOD_ADDENDUMe98d14600088d196cbd743d13582bccb4aec82adaa8521751c33741ba21b7f02：实际为独立AI代理读取工具文本，无外部人类审稿，原报告字节保留，不重跑检查。

根 EX/manuscript_compile_20260930_0202：本机MiKTeX禁自动安装/禁shell escape，分别实际pdflatex/bibtex/pdflatex/pdflatex，两次main+supp共16命令各exit0。首次main17页supp6页，真实看完23页发现mainp11 overfullvbox11.30112pt及bibliography留白，独立发现Official重复caption。修订仅历史fusion table !t→!p、bibliography前clearpage、caption去重复，数字/字体/图不变；amend_layout_once.py a2db0118e7e7e0316cdd983b55b635ea8511b870a71bb06b29208659aeb094f6，REVISION eb16a93868e4ee577564f5ed274cc8deda9d01d322f2ec204c76aade63605f35。旧源/旧PDF/日志全部保留。最终attempt_2八命令exit0/输入未变，main16/supp6。根实际通过view_image(original)看完最终22PNG，ROOT_VISUAL_REVIEWa18a3cb4e34d119567c2639edc0411fbb848b9c7395c5642dff48a4209526cfe，未把程序geometry当看图。无Overfull/undefined/??，仍有main4 Underfullhbox，supp2 Underfullhbox+3 Underfullvbox；不称零诊断。使用现有Python311 fitz渲染，新稿实际编译而非旧PDF。一次bundledPython探测无fitz，切换已安装Python311成功，未安装依赖。

最新本轮只读在02:02:48.0842976+01，EX/heartbeat_observation_20260930_020247156/OBSERVATION_WRAPPER_INCLUDED.json58c5e57ccadfa3a91f5baa1b0c5fca0e95e0fadbd1932db5738a8d7e8951b6a8，ROOT_OBSERVATION_SEAL1a41e6bdac5be64378b61d8de971e3e70588296f2040749c84401e83675b31a7。两广CIM仍只有精确AppActions14420与未确认VISIO14932，父2232/整数ticks/完整命令同前；无科学owner，boot639263179115000000。02:02:47 stopped observation_20260930_020247173/OBSERVATION.json ee153cf1adbc146588b6e7ef3cbfa51aa7e0c68768ba05a5552f5cc71ffd95d9，GPUexit0/26rows/gatefalse/T6absent。新boot T6合同匹配，旧contract mismatch为历史预期，两个T6attempt和Visio新attempt均不存在。根稿件采用时再次核16state/log与carrier b0原bytes；未重复科学suite/旧权重/NPZ/cache/image读取、未COM/release/intent/recovery/锁/state动作。已知GPU/未知Visio阻塞不重复通知，snapshot非未来许可。

仅本轮新本地工作稿通知一次。最终Overleaf/投稿稿和建议仍待所有真实实验验收后完成；T6、LOHO24fit192task、真实解释图、其余Visio、后继作者与独立基线/额外DAC/效率仍待推进。原科学计数、70PPT-SVG/两mainVisio、完整60.47GB包及全部冻结协议/五层顺序/资源限制/继承证据缺口保持。不要重复旧suite、重新hash大包或把工作稿当终稿；所有任务交付前保留自动跟进。
'''
p=E/'HANDOFF.md';before=p.read_bytes();beforepin=pin(p)
assert beforepin['sha256']=='bfeef01626ccd5467e4948000b3c0752126667b713371c363624193212152c08'
with p.open('ab') as f: f.write(text.encode('utf-8'))
after=p.read_bytes();assert after[:len(before)]==before
receipt={'schema':'handoff-append-receipt.v1','utc':datetime.now(timezone.utc).isoformat(),'before':beforepin,'after':pin(p),'prefix_preserved':True,'root_adoption':pin(r),'append_bytes':len(text.encode('utf-8')),'source':pin(Path(__file__))}
with (H/'HANDOFF_APPEND_RECEIPT.json').open('x',encoding='utf-8') as f: json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'receipt':pin(H/'HANDOFF_APPEND_RECEIPT.json'),'root':pin(r),'time':t},ensure_ascii=False))
