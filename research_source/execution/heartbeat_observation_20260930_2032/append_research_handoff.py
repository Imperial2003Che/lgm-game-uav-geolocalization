"""Append new finite research and observation; preserve the prior journal prefix."""
from pathlib import Path
import json, hashlib, datetime, os

EX = Path(r"C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution")
BASE = EX / "heartbeat_observation_20260930_2032"
LIT = EX / "camp_dac_reported_values_review_20260930_2032"
READER = EX / "local_chm_reader_feasibility_20260930_2030"
H = EX / "HANDOFF.md"
def bounded(path, limit=131072, expected_sha=None):
    path = Path(path)
    size = path.stat().st_size
    assert 0 <= size <= limit, (path, size)
    raw = path.read_bytes()
    assert len(raw) == size
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None:
        assert sha == expected_sha, path
    return raw, {"path": str(path), "bytes": size, "sha256": sha}

receipt = BASE / "HANDOFF_APPEND_RECEIPT.json"
assert not receipt.exists()
core_paths = [
    (BASE / "ROOT_OBSERVATION_SEAL.json", "171a746438f6c4c44227adff244a55b8c0831c5d6a917a42138547ce694b4bb3"),
    (BASE / "ACTUAL_OBSERVATION_TOOLS.json", "e12f4b2caded934b8012afe81785b9f703f1c25f24e6f092caf89a8c09cfc049"),
    (LIT / "ROOT_LITERATURE_CORRECTION_ADOPTION.json", "e6bf56a6c6637db1ad0b3c618b507f7f227932207cdba6f7189d34579b61242f"),
    (LIT / "ACTUAL_ROOT_ADOPTION_TOOL.json", None),
    (READER / "LOCAL_READER_FEASIBILITY_REVIEW.json", "3727ef7c60bdbe2197f25c9db343f60f3c7da3761dc76ebc0f6f485bb4334987"),
    (READER / "seal_reader_research.py", "4fe1a91c73f61b9786f3930249901818fe1e78c3af141bc197f603370c198d0b"),
    (READER / "ROOT_ACTUAL_TAR_FORMAT_PROBE.json", None),
    (BASE / "append_research_handoff.py", None),
]
inputs = []
for path, expected in core_paths:
    raw, descriptor = bounded(path, expected_sha=expected)
    inputs.append(descriptor)
    if path.name == "ROOT_OBSERVATION_SEAL.json":
        seal = json.loads(raw)
    if path.name == "ROOT_LITERATURE_CORRECTION_ADOPTION.json":
        literature = json.loads(raw)
    if path.name == "ROOT_ACTUAL_TAR_FORMAT_PROBE.json":
        tar = json.loads(raw)
assert tar["actual_tool"]["result"]["chunk_id"] == "0edfa5"
assert tar["actual_tool"]["result"]["exit_code"] == 1
assert "Unrecognized archive format" in tar["actual_tool"]["result"]["output"]
assert literature["literature_only_source_adopted"] is True
assert literature["not_adopted"]["scientific_execution_released"] is False
current_files = []
for expected in seal["unchanged_state_and_closed_log_files"]:
    raw, actual = bounded(expected["path"], expected_sha=expected["sha256"])
    assert actual == expected
    current_files.append(actual)
carrier_raw, carrier = bounded(seal["carrier"]["path"], expected_sha=seal["carrier"]["sha256"])
assert carrier_raw == b"0" and carrier["bytes"] == 1
for path in seal["attempts_absent_at_file_seal"]:
    assert not Path(path).exists(), path
assert not Path(r"C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\analysis\transactions_t6_formal").exists()
utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
reader_probe = next(x for x in inputs if x["path"].endswith("ROOT_ACTUAL_TAR_FORMAT_PROBE.json"))
text = f"""
## {utc} — 原报单格转录修正采用与有限CHM读取研究；无新科学/稿件/用户处理事项

本轮先读最新19:13:28 UTC HANDOFF及所引DELIVERY/receipt，最新磁盘优先旧heartbeat。前缀518681B/SHA26786df068f595fea78b6571d56ce1f85dfc0f396e0e7f8bb51797a638f86b19保留。未重新编译/发送此前已交付17+6 CAMP/DAC相关工作稿，未读hash旧大ZIP/权重/NPZ/cache/image。原五层+额外DAC、冻结源/参数、科学负结果、统计分母/来源缺边及资源/退出/共享锁门完整继承。

新 EX/camp_dac_reported_values_review_20260930_2032：独立AI只实际读取并以已装fitz一次render CAMP p7/p8/p9和DAC p7/p8/p9六正式PDF原页（cf677c exit0/0.8619184s），六original看图后手录36行72个own-method R@1/AP显示值；表数值无法由fitz文本直接抽取，非自动OCR/人工审稿。71与旧CSV一致、1真实转录差异、0unknown：旧CSV第31行（data row30）DAC University→SUES、D→S、200m AP为89.90；正式DAC p9/印刷13279 Table IV DAC(Ours)行200m/AP实际89.00。另新candidate writer0c6ee2 exit0/0.187315s，只改offset5280 byte57→48；旧CSV6440B/8982e329fdd88035a726b9276cdd2cc80523037525e0a243dc4941283e123e0a及旧报告/根不回写。新 AUTHOR_REPORTED_ROWS_CORRECTED_CANDIDATE.csv6440B/1f690930e88987a6c81f379957c814e300d2bebe3e6a411ab9e5d08a43704202 只作未来文献原报表源。EXACT_CORRECTION_BYTE_DELTA1710B/a4ebd6b4ced58e447ce861adc583491a71eb9d3ee68939423803fa06d3148b10；72逐项 VALUE_COMPARISON.csv7730B/71b3f03ad98a532f3212770afdfc9b7a9779a9f964c932a553801bc72e8d4fbe；独立 REPORTED_VALUES_REVIEW.json98464B/3ceb4892ac88dae93b11c53f3b326eefc63c5e8c421dc1abdfcc36c0e2dd1dca/MD/DELIVERY及真实回执联合，14新小文本一次seal95f5fb，不重跑比较。

根独立actual original看完同六原页，并逐项读旧CSV、新72比较/literal/method、reader/candidate writer源；根也确认71+1。ROOT_LITERATURE_CORRECTION_ADOPTION.json10764B/e6bf56a6c6637db1ad0b3c618b507f7f227932207cdba6f7189d34579b61242f 唯一5e62ab实际exit0/0.1911127s，25绑定（19小文本+6新文献页PNG）、精确one-byte与metadata计数；不是再跑独立比较或SCI/control suite。根未声称完整语义读98464B明细报告，仅完整小比较/字面/方法/source及实际六视觉。原PDF完整SHA仍历史继承，未fresh整PDF hash；新PNG字节封存不是dataset imagebyte审核。只literature source adopted，作者权重复评/独立训练/AP-evaluator/gallery/pretraining/protocol parity/不确定性/全bibliography/科学release全未采用；原72值没插最新稿，所有原科学结果/正文/图件/Overleaf保持。

新 EX/local_chm_reader_feasibility_20260930_2030/LOCAL_READER_FEASIBILITY_REVIEW.json11748B/3727ef7c60bdbe2197f25c9db343f60f3c7da3761dc76ebc0f6f485bb4334987：有限PATH/安装根/registry/Python包名调查，没有已验证CHM reader，非全机无工具证明。实际存在system tar/libarchive3.8.8及Anaconda bsdtar3.8.2；后者local ffi/header/man声明不含CHM，raw只是任意stream单entry，不代CHM目录/LZX。其报告/9749B sealer完整根读；普通metadata seal fd454d与actual工具/参数保留。根随后决定仅一次精确system tar.exe -tf原VISSDK.CHM识别；0edfa5实际exit1/0.1450839s，Unrecognized archive format，实际返回单列 ROOT_ACTUAL_TAR_FORMAT_PROBE.json {reader_probe["bytes"]}B/{reader_probe["sha256"]}。无-x/SDK copy/hash/thirdHH/rawfallback/install/download/HTMLJS/DLL API/COM/cleanup。新有限读取失败只属本读取器能力，非科学新故障，不能说CHM无XSD或68file-only Visio通过fullXSD。旧两HH已消费不重放，full官方main+九part依赖及应用repair-free打开/导出/编辑/重开仍缺。两普通Get-Content误猜路径错误保留在真实read回执，仅定位读取错误、不属SCI failure；后按实际manifest路径读取，不补造成成功。

实际只读广扫描19:31:12.7276074Z/19:31:13.3806620Z：EX/heartbeat_observation_20260930_2032/OBSERVATION_WRAPPER_INCLUDED.json15692B/bc1b2d9fdd7b747d920962df378b4e39b6a1d9a7fbcc091f02b0de5dceaef526，两次仍同普通用户VISIO29480/parentexplorer13076/原完整命令和birthticks639263338233256210、WeChatAppEx17896/parent5000/currentGPU完整命令与birth639263535469540740、conhost14420/parentnode13212/cua-repl命令birth639263776238715890；完整父当前ticks命令见保存报告，不当历史CPUouter17896/pipeline14420/旧父或完整历史祖先。没有识别原科学owner仅限保存筛选；普通Visio不附加关闭，不绕empty门。

stopped实际20:31:12.8337655+01：EX/efficiency_incident_20260929_1448/observation_20260930_203112314/OBSERVATION.json5767B/eafd8b84ecef3a8cba6f227678398c925ad71e51cff72789ed57b19dfacf3213，窄双CIM有当前conhost14420非空，5state-heartbeat不变，GPUquery实际exit0/26rows/gatefalse、T6outputabsent；raw2108B/1802557ae5ce7f7f266cd0a0e5693889412156316b91e026e7609c5deeae3d3e。相同boot639263337875000000与0405当前合同匹配，旧Sep29 flag false不当当前合同failure。ROOT_OBSERVATION_SEAL21851B/171a746438f6c4c44227adff244a55b8c0831c5d6a917a42138547ce694b4bb3 唯一11846c exit0只是保存关系/16state-log/carrierb0/三T6+Visioattempt absence；ACTUAL_OBSERVATION_TOOLS38223B/e12f4b2caded934b8012afe81785b9f703f1c25f24e6f092caf89a8c09cfc049联合。交接此脚本仅再核16文件及carrier原bytes/attempt/T6absence，不新采OS/GPU或available_commit，不当未来准入；primary独立ownexit仍未知，不补exit0。

本轮无科学release/intent/native训练probe/recovery/retirement/COM/cleanup/锁/live科学state动作，GPU非空不启动等待；普通文献read/render与tar识别不是SCI或双held控制。42fit/官方42run231task/T3_12run66task/鲁棒性660+22、70PPTSVG/2main实际Visio/68file-only Visio、最新17+6稿/旧60.47GB包/原Overleaf均保持。T6/LOHO24fit192task/真实解释图/后继作者及独立baseline/额外DAC/完整gallery-ranking-parity-timing-onlineCLIP/终稿图件正文/最终Overleaf投稿建议仍待真实完成。此内部文献单格纠正未影响已交付论文科学数字，有限reader拒绝未改变既有Visio条件；无用户处理事项，本轮静默。全部实际交付才删除跟进。
"""
append = text.replace("\n", "\r\n").encode("utf-8")
expected_size = 518681
expected_sha = "26786df068f595fea78b6571d56ce1f85dfc0f396e0e7f8bb51797a638f86b19"
assert H.stat().st_size == expected_size
with H.open("r+b") as handle:
    before = handle.read(1048577)
    assert len(before) == expected_size and hashlib.sha256(before).hexdigest() == expected_sha
    assert H.stat().st_size == expected_size
    handle.seek(0, 2)
    handle.write(append)
    handle.flush()
    os.fsync(handle.fileno())
after = H.read_bytes()
assert after == before + append
result = {
    "schema": "root-heartbeat-research-handoff-append-receipt.v1", "utc": utc,
    "source": next(x for x in inputs if x["path"].endswith("append_research_handoff.py")),
    "before": {"path": str(H), "bytes": len(before), "sha256": hashlib.sha256(before).hexdigest()},
    "append": {"bytes": len(append), "sha256": hashlib.sha256(append).hexdigest()},
    "after": {"path": str(H), "bytes": len(after), "sha256": hashlib.sha256(after).hexdigest()},
    "prefix_preserved": True, "inputs": inputs,
    "file_only_current_checks": current_files + [carrier],
    "science_release": False, "new_scientific_result": False,
    "method_limit": "Cooperative expected-prefix guard, not atomic CAS against arbitrary writers; no new OS/GPU/memory admission or historical exit proof",
    "notification_decision": "DONT_NOTIFY", "automation_retained": True
}
raw = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
with receipt.open("xb") as handle:
    handle.write(raw)
print(json.dumps({"receipt": str(receipt), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "append_bytes": len(append), "handoff": result["after"], "inputs": len(inputs), "file_only_state_log_carrier_checks": len(current_files) + 1, "notification_decision": "DONT_NOTIFY"}, ensure_ascii=False))
