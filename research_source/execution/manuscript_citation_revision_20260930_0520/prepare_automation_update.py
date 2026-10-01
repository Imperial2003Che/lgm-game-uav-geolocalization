from pathlib import Path
import json,tomllib,hashlib
HERE=Path(__file__).resolve().parent
AUTO=Path(r'C:\Users\17703\.codex\automations\automation\automation.toml')
def save(p,d):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
d=tomllib.loads(AUTO.read_text(encoding='utf-8'))
save(HERE/'AUTOMATION_BEFORE.json',d)
append="""

最新追加：2026-09-30本轮新增引用修订本地工作稿；详HANDOFF最新记录及EX/manuscript_citation_revision_20260930_0520/HANDOFF_APPEND_RECEIPT.json 69afec0467aaf75ab4455d7059b365d4723712f1202ab9a0e0d8a95bb800041d。不是新科学、图件、最终稿或Overleaf。
OUT/manuscript_citation_revision_20260930_0520/ROOT_MANUSCRIPT_CITATION_ADOPTION.json 8e6f290cfa7943b1b60ac7a919beb29cf9a1669af6fad9464925ec86cf6c1c63首次exit0/89局部绑定；须联合外置ROOT_RESEARCH_BINDING_ADDENDUM a1d755bb96bd0b07260f2ee9653a626cbc0c6deee2274c9ae5642992440ae5d5，补核dataset/CAMP两不同清单键的23新小边，不改封存根/ZIP。新ZIP LGM_GAME_Citation_Revised_Working_Draft_20260930.zip 19033688B/129成员SHAcfb5817ebc2c8acbfbf2f26881bcceca6eb44efe7b0774511caa4826df58fb37，逐CRC/size/SHA完成；main.pdf17p/7147607B/76bd42fbe1d53f9e4e65e5f4fafa6baa2c391ac4c8f4fa65852fe23d86e44894，supp6p/273353B/8c985d3a77d425fa367418f210f7c5a66cfcb9255b9e70e18180118b7d51a8cb。旧16+6及所有旧包保留未回写/读旧ZIP或权重。
只main.tex和refs.bib改变：Holm当前不解析DOI改官方JSTOR URL，McNemar保留1947并加Fay2010exact公式来源，brightness明确darkening/family adaptations。其余30源依赖/科学数字表图参数/全部负结果及证据缺边继承。独立EX/manuscript_citation_delta_review_20260930_0520/DELTA_REVIEW cb4f4592fb132f721610ca4e92a6b95a88bad83af8e71467d59af396e3087634首次53，DELIVERY7e36ee2cfe982d2c66a6c6f75a4913720f9fea86dde69a4e3df4df7b1a95a6bb。原producer差异因read_text行尾比较放大44244B，实际原refs571CRLF保持且只添12LF；独立实际byte diff2316B/33053dfa6bda11e3a73542f62c25a56c88063ac9f71a24fb8f3ccc7f0c050809，原文件不改。
根实际MiKTeX禁安装/禁shellescape一次8命令全exit0。首bundled renderer缺fitz在import前exit1，改用已装Python311/fitz同脚本成功，无安装。23PNG中14与旧final精确相同，9改变页+另p15共10根实际original看完；ROOT_VISUAL_REVIEW e46666964c60ee52742ce7ac7f5274ff03de8374fbbc67c9ca541e6b995ff1fe。无overfull/undefined/??/越界，main4underfullhbox/supp2hbox3vbox保留。p17只有最后AQE一条，明确终稿排版待项，不缩字体/额外重编。独立只源差异未编译/视觉/web/484，非人工审稿。
文献局部：EX/citation_open_fields_20260930_0509 OPEN_FIELDS_REVIEW f64db78c12686f6850fd81d0b92d662f3c116c88756cfa6abed4ffd8177ba09a须联合DELIVERY_ADDENDUMc2f0792a35d5767f311d06c4d414dbabd852434a5bd598f05b5df7e58b4846f7（一句漏non，原证据一直非解析）。AQE页码/Efron DOI/完整名原值确认；Holm当前不存在不证明历史never；Fay原PDF/根HTML支持条件binomial双倍较小单尾上限1，非项目统计实现验收。root DOI RA访问失败不冒agent成功。
dataset报告4a1f3a4cefa2bbe0c74a9646db7cf71695b9ff31d125e6c5943518850ebb7f5f：16字段10文中事实无已证错误；University50218−41214=9004与当地excluded8944差60仅未同版本/同范围算术，非缺图/科学失败，冻结数字不改。CAMP/DAC报告99d268c7c5831d9a571a1fc6c4e06bc8992896b1ec03b746b7451232a5972c9d两作者托管正式PDF与agent六表页36原报行72值只未来研究；当前稿无条目，建议Bib未插入。CAMP纸面oneepoch/源码0.1总steps及24/48批量、预训练/AP差异分开，不能改冻结协议；原报SUES同域/受控迁移/本项目待作者权重和独立训练分别。root未独立复核72值。预印本报告025e1b911b2b84ce79f9870122a536423d6e97af998218d59cd9a8aa766ece30根MGSv2/InfoGeov5共20原报显示值与表一致；Mobile主源失败未新核验；无全bibliography验收或科学执行。
本轮05:09只读EX/heartbeat_observation_20260930_050928509/OBSERVATION_WRAPPER_INCLUDED68200ad77bf354cb25e6e0615eced44395fb784d530bf233223b2abb4f99ab46/ROOT_OBSERVATION_SEAL385e7b38418c23185ac3e84152a177c7ac61e72d612ac8c969d42aff0569ac32；同boot639263337875000000，同普通VISIO29480,parentexplorer13076/原完整命令和ticks，无科学匹配。stopped observation_20260930_050929887/OBSERVATIONa227a3818c8247c36bb6e4a12aac15bff16eaf47aefb1386a3bb80e79c594f93 GPUexit0/23rows/gatefalse/T6absent。根采用再核16state/log/carrierb0和3T6+Visioattempt全无，无release/intent/native科学probe/COM/cleanup/锁/state动作；文件再核非新的OS/GPU准入。原broadobserver针对Sep29合同false不当0405当前合同失败；root当前boot匹配。0405源码候选仍未执行，既存Visio不关/附加，GPU非空不启动等待。
本次仅新引用工作稿通知一次，其后相同阻塞静默。所有科学计数/70PPTSVG/2mainVisio/旧完整包/Overleaf保持；T6/LOHO24fit192task/真实解释图/其他Visio/作者和独立baseline/额外DAC/完整效率/终稿排版正文/最终Overleaf投稿建议继续。五层顺序、当前boot三attempt、三次资源门/六锁/native/15minrelease/退出闭流、全部负结果/证据限制/资源授权完整保留，全部实际交付才删除跟进。
"""
newprompt=(d['prompt']+append).rstrip('\n')
args={'mode':'update','id':d['id'],'kind':d['kind'],'name':d['name'],'prompt':newprompt,'status':d['status'],'rrule':d['rrule'],'targetThreadId':d['target_thread_id']}
if 'notification_policy' in d:args['notificationPolicy']=d['notification_policy']
save(HERE/'AUTOMATION_UPDATE_REQUEST.json',args)
print(json.dumps({'before_chars':len(d['prompt']),'after_chars':len(newprompt)},ensure_ascii=False))

