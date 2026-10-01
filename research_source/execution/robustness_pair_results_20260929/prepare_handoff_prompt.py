from pathlib import Path
import hashlib,json,tomllib
from datetime import datetime
E=Path(__file__).parent.parent; HERE=Path(__file__).parent
F=E/'robustness_full_audit_20260929_1247'
def H(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def J(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
full=J(F/'ROOT_FULL1_ADOPTION.json'); stats=J(HERE/'ROOT_PAIR_STATISTICS_ADOPTION.json')
assert H(F/'ROOT_FULL1_ADOPTION.json')=='ea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5'
assert H(HERE/'ROOT_PAIR_STATISTICS_ADOPTION.json')=='2eaed53c937a4a260be321c18ff100522c601622374153a511388e5c797b1cee'
obsPath=E/'robustness_observation_20260929_0647/snapshot_20260929_130251128/OBSERVATION.json'
assert H(obsPath)=='a1fccfc9fcfed4168e9ca4b0f8ef749c50098b766a6eaef55898b106a45b9dd6'
obs=J(obsPath);science=obs['robustness']; assert science['id']=='sues200/visual/seed_1'
current=f'''最新实查{obs['time']}：只读observer {obsPath.relative_to(E)} SHA{H(obsPath)}，CONTRACT SHA{obs['contract_report']['sha256']}，两次CIM核12身份/精确UTC整数ticks/完整command/parentage。四owner/launcher仍pipeline14420/29784、extensions30388/7584、latest33520/12896、independent7484/21652，四heartbeat新鲜，后三waiting4/2/3pending，四stderr0，三计划/stateIOv2 SHA保持。pipeline当前14420有9组已恢复Win5retry/4770bytes，其他3无retry；历史8992八组为另一批，不能说当前或历史无retry。
当前SUES Visual seed1 launcher24428 parent40780 Creation2026-09-29T12:18:42.9496270+01 UTCticks639262775229496270；interpreter40060 parent24428 Creation12:18:42.9943530+01 ticks639262775229943530。stage24120/40780 ticks639262571000923660/639262571001196180不变。science日志最新：{science['stdout']['tail'][-1]}；science stderr{science['stderr']['bytes']}bytes。baseline/cuda/workers8/evalbatch128/chunk128/AMP/corruptionseed20260727/match-cache/clean-audit64/localfilesonly保持。ledger2completed/1running/1pending仅runtime，SUES未验收；commit{obs['commit_headroom_GiB']:.8f}GiB只是运行快照，26GiB仅新启动准入，绝非停止门限。下轮先实查自然worker/phase变化，任何snapshot均非未来当前身份。
'''
newfull='''最新根实际采用2026-09-29 12:59:00 Europe/London +01：University Full seed1完整扰动结果已独立审核并根采用。新增1run/30条件90扰动task+3clean；累计鲁棒性2/4run=University Visual及Full各seed1，60个run-condition、180扰动task+6clean。两SUES仍未验收、robustness阶段未完成、pipeline整体仍3/7。42fit全部80轮、官方42run231task、T3 12run66task既有采用不变。

新目录execution/robustness_full_audit_20260929_1247：review_full1.py SHAe12125299612df0d68765b0ad744904a22015edd76a85b48a60759f3b3715d96；FULL_FROM_VISUAL_SOURCE_DIFF.patch4502eac7b6bbca3bf0219caa206235686e97c13f76e62057562e1e03499d4090；a1/REVIEW.json a6268401ae9989dd8cfa2eb9394dc9320b108e288ca82b51b5439b35f2478199；a1/METADATA.json bec5d11b18bf79874d4719b622002e18e62db687f58ba31c07e5e7b449cc5763；DELIVERY.json57e80395142f6de19d18048e29daa4638ea41300c7bd0cfa666c66df9ef40b15。首次独立审核exit0、247raw/220artifact真实SHA/size、93NPZ/62CSV/540summary行，8842513断言/9234数值对比。原52AST定义体不改、typed stdlib门issues=[]、406hash请求=1精确Full继承checkpoint+405封存artifact实际hash。Visual附加coverage/CSV顺序唯一/精确dtype/单位语义检查已整合，不重复旧suite。
Full自己的Sep20 FULL_SEED1_COMPLETION.json SHA61b2c2019d33ebcf192fbc73321f8667ef5daee9cd8e02bb87c6b4f862a0dd09及根772133fee742bb3b26825eb8e3c05760cf4ace5e28f22d729c013841be84a018实际边，具体BATCH6官方/T3采用绑定；best.pt SHA581fc1b40e0dc343f3906c8e180bc843a58d37ba97e8fb5833f2c49ac39a9c99/172346411bytes继承，非借Visual初始inventory。Full canonicalc7bfc6c41ccadf0f52cf79609a76ef921bf456c5d06334b78ece284a5b4c9ce1、manifest ea0cf3add63b66efa57120416937c5c894471b98859eafb2df37010299d155a5。当前权重bytes不重核、stat非证明，历史全局SHA边缺口和cache/image继承限制保留。
根完整diff/关键源/合同审读并核544唯一文件/12当前身份后采用 ROOT_FULL1_ADOPTION.json SHAea8c3065092db79c67005b6b6aa1b54a5433ba39ae4b143504f09618f98fd1f5，adopt_full1.ps1 SHAcd92d60813ac915aedafaf8e163730789a68da25bec15237ab321b44903b994c；继承旧Visual根81ec5d80b7370ae5dc79c3f12e0633b88ade73be3422ec155ea11def68713cc6，其原主报告/addendum联合采用保持，详HANDOFF10:02。Full合同FULL_CONTRACT_REVIEW7bb5810fabafb0f771e86e752b077fa9493228fd80d34a9d32b584ac60a8bdcc；稍后独立增量静态报告FULL_AUDIT_SOURCE_STATIC_REVIEW dc419dc464a4cd76569d97fb7fc2ce8a99cb8c12da8621ee333abc18bdc5839d无阻塞，未执行候选或扩测、未改首次DELIVERY/采用。
Full64诊断file47b9e945ddb892048fa1fbcd0c5de69e89a5bb30b4809171ffa12fc5fcfd5c94/payload d8788767a0bd22ef51e0b2a81218b762c5ede896e1668991caa9626b833db10c、最终内嵌及固定样本成员一致。fp16/revision3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268；content MAE0.00010020700574386865/max0.00244140625/exactfraction0.13494318181818182；style MAE0.00008360352512681857/max0.001953125/exactfraction0.1484375。无数值threshold门、不称等价/逐位一致或排名差异可忽略、不归因差异原因。Full clean概率来自cache，corrupted-query同扰动RGB在线CLIP计算；差异包含证据计算路径与扰动，不是纯扰动效应。Visual不走CLIP。未model/fullranking/AP所有正样本名次复算或重建像素/features；保存AP/RR/margin的math.fsum binary64均值容差rel1e-6/abs1e-7非bitwise NumPy，recall按计数。只有seed1，不能三seed鲁棒性SD/显著性。
旧Full40820/43872原父subprocess.run于11:18:40.324610Z return0；stdout14140bytes SHAece2c1911c390b70f50400b5a0e0e3d41b040f02a08297cbcbde3025c4815256，stderr325bytes SHA939bd35cd671fbdb659d92ea4ee845dd030ef5930dbcf00ef8b97d4cd299d146仅原slowprocessorwarning。ROOT_FULL_TRANSITION70967e6f477d24419439c6251601300d7d77056b9682d7c6a963654b53e470f8及后续CIM旧pair缺席，非独立双句柄exit证明。
'''
pair='''University seed1两run的逐任务描述统计已实际完成并根采用：execution/robustness_pair_results_20260929/result_20260929_115922_396070，128个root准入小文件输入、93pair(3clean+90corrupt)/279metric行，producer43899checks，Decimal50直接解析保存值，不跨任务/条件/severity pool、不做SD/CI/显著性。compare_pair.py6e63d5c3a25119089ebc49cfcc39751d71bd63dbd4bf43bd0bf3a523be20fee4，REPORT9c148184cfe60a37ee48b6cd3d72521295639c822bbf0d7e7967f8ec864fe8c6，DELIVERY72e974d5fd3c006abe352d43aa8f7e611b539642cef6854ffe6d2cd7abedc1c4，paired_tasks.json41ab34d2b0dd5d715628c466b109f656506f4059fc9b0cd53dad83f65b43d933，paired_metrics.csvd69f56d65c84b2ce0412507c703e5fdca9ae0f960e15850723f82734ff3a9576。
根完整producer源读审、以独立Fraction精确有理数核全部5022数值字段/CSVJSON对应/93完整键集合，14936checks通过；ROOT_PAIR_STATISTICS_ADOPTION.json2eaed53c937a4a260be321c18ff100522c601622374153a511388e5c797b1cee，根source162ef6a95d2c60efcb418866ae1e7789688a265615b4c185d18ad39a2ca23dde。独立静态源报告a5f96110d3a018ad678e2d4b628b81e98ca7b627d7db0c6a1bf6b0607a6eebe9无阻塞，仅静态未执行；根后续19小文件核验ROOT_STATIC_ADDENDUM9849ed37b9a6d57b072927781ff68a71dc0df897fc40bae412b89d22003b26fd，确认Full和统计源静态报告/首次统计execution与delivery，旧采用字节不改。
新表每任务保留raw Full−Visual及各自clean−corrupt drop、drop差=(Fullclean−Fullcorrupt)−(Visualclean−Visualcorrupt)，正值代表Full绝对降幅更大；更小drop不等于更高扰动准确率，必须连同clean基线解释。R@1/mAP乘100为百分数、差为pp；MRR乘100单位独列。描述符号计数（每任务30条件，不是pool分数/显著性）：drone→sat R@1/mAP各3正27负；sat→drone R@1为3正1平26负、mAP4正26负；street→sat R@1为27正3平、mAP28正2负。clean street→sat R@1仅Visual0.542846%/Full0.930593%，不因相对增益掩盖低绝对值。不能声称Full普遍更鲁棒，亦不能以seed1差异覆盖官方三seed和迁移负结果。Full cache/online路径差异及所有上游继承证据限制保持。
'''
header=(f'\n## {datetime.now().astimezone().isoformat()} — seed1配对统计及后续独立静态复核采用\n\n'+pair+'\n'+current+'\n')
with (HERE/'HANDOFF_STATISTICS.md').open('x',encoding='utf-8',newline='\n') as f:f.write(header)
with (E/'HANDOFF.md').open('a',encoding='utf-8',newline='\n') as f:f.write(header)
old=tomllib.loads(Path(r'C:\Users\17703\.codex\automations\automation\automation.toml').read_text(encoding='utf-8'))['prompt']
intro=old.split('最新根实际采用',1)[0]
t3=old[old.index('既有根采用2026-09-29 07:06:56'):old.index('当前使用execution/robustness_observation')]
observer=old[old.index('当前使用execution/robustness_observation'):old.index('旧Visual launcher27888')]
tail=old[old.index('两张原主结果图完整原生SVG'):]
prompt=intro+newfull+'\n'+pair+'\n'+t3+observer+'\n'+current+'\n'+tail
for required in ('corrected_driver_v3','额外DAC3fit/30eval','6ab9825d2cb870b10bc95589','Root','measure_task_ranking'):
    if required!='Root': assert required in prompt,required
assert '当前University full seed1 worker40820' not in prompt
assert 'currentretryJSONL不存在' not in prompt
target=HERE/'AUTOMATION_PROMPT_1303.txt'
with target.open('x',encoding='utf-8',newline='\n') as f:f.write(prompt)
print(json.dumps({'prompt':str(target),'sha256':H(target),'chars':len(prompt),'handoff_addendum_sha256':H(HERE/'HANDOFF_STATISTICS.md')},ensure_ascii=False))
