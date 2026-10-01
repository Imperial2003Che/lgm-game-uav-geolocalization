"""Verify final local adoption records and preserve an exact handoff."""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))

review = read(HERE / 'ADDENDUM_REVIEW.json')
recovery = read(HERE / 'STARTUP_SCRIPT_MOCK_9f9eae81e782_093737472.json')
assert review['test_count'] == 17 and all(row['status'] == 'passed' for row in review['tests'])
assert recovery['count'] == recovery['passed'] == 43 and recovery['failed'] == 0
assert sha(EXECUTION / 'restart_after_memory_incident_1544_path_compat_v1.ps1') == recovery['target_sha256']
files = [HERE / name for name in ('EXECUTION_ADDENDUM.json', 'REGISTRATION.json', 'ADDENDUM_REVIEW.json',
         'ACTUAL_AUTHOR_PATH_AUDIT.json', 'STARTUP_SCRIPT_MOCK_9f9eae81e782_093737472.json',
         'RECOVERY_DERIVATION.json', 'FINAL_MACHINE_SNAPSHOT.json', 'README.md')]
files.append(EXECUTION / 'restart_after_memory_incident_1544_path_compat_v1.ps1')
papers = EXECUTION.parent.parent / 'paper_label_revision_20260914/manuscript'
assert sha(papers / 'main.pdf') == '3f13c14ea66e86cfb1657118991552fbf240b8f39eb8c6163dfd3adb2fe471da'
assert sha(papers / 'supplementary.pdf') == '08b40518fc17adf6a2a7bdef26a004451b07cc1a34d7ee4a2f5b9ed9a8f467f9'
payload = {'status': 'execution_addendum_registered_recovery_reviewed_not_launched',
           'time': datetime.now(timezone.utc).isoformat(), 'source_checks': 17, 'recovery_control_checks': 43,
           'files': [{'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in files],
           'new_scientific_results': False, 'original_plans_and_releases_unchanged': True,
           'browser': '09:38 connection failed; login unknown; no upload or new project',
           'paper_pdf_hashes_verified_unchanged': True, 'open_in_codex': 'queued'}
with (HERE / 'FINAL_ADOPTION.json').open('x', encoding='utf-8') as stream:
    json.dump(payload, stream, ensure_ascii=False, indent=2)
text = '''

## 2026-09-15 09:38：三个评估入口已接入目录联接兼容

本轮补齐07:31遗留的实际队列入口问题。新路径目录 `path_alias_queue_20260915/`，先实际读取第四层作者源发现CAMP、DAC各两条相同文件路径表示差异，报告ACTUAL_AUTHOR_PATH_AUDIT SHA 30b6e2084d47b4a2028c1bba2f345a2b7907e6f945c0b8733d0b5fb5c850b6d6。随后将两个作者入口和CAMP独立评估共三个入口通过明确的执行补充接入，未改原计划、prepared、release、模型、科学源码、数据或用户目录。

EXECUTION_ADDENDUM.json SHA 0c4217fefb33d6550bda2300bc201f1c869da0b8d5ff02d45ae7af45b7ef6d70，11来源；REGISTRATION.json SHA a76004bd031c858fc407cf2faffca87b4e76ed17172dda877c1698d308c5f234。登记前后实际CIM仅登记脚本自身，四故障状态SHA不变，独立v2无status，相关运行结果/日志/启动意图均无；不是重复登记v2。

这是保留原科学合同的显式执行补充：plan_sha256及job.command仍指原登记合同，execution_addendum和job.execution_command另列实际父入口与实际启动命令。两个新父程序为supervise_latest_baselines_path_compat_v1.py、supervise_independent_comparisons_path_compat_v1.py。全部原队列source/runtime核验、前序/进程退出/资源/锁/完成判断保留。child在fresh native进程加载原evaluator，只用已审path_aliases包装source_evidence/verify_sources；原逐字段/大小/SHA/同实际文件核验后保留prepared路径拼写。stdout保存原/实际命令、addendum与alias；作者保留原锁与evaluate，CAMP独立保留原run及其全部门限。

ADDENDUM_REVIEW.json SHA 156f472fa681609e0fd9a73c7729ed5acd752aa88099f498b410cc87c8ff32f3，17/17通过，含三个真实native source/prepared读、两个实际父程序check-plan全部旧队列来源及原生metadata；没有科学导入。新恢复脚本 restart_after_memory_incident_1544_path_compat_v1.ps1 SHA 9f9eae81e78291493cea24206fa0f8f7aed5d941428aa735e9e5caf159c4c398。43项恢复模拟全部通过，报告STARTUP_SCRIPT_MOCK_9f9eae81e782_093737472.json；CIM/Start/Move/Sleep为模拟，不能称实机恢复成功。都是根代理检查，不是独立代理复核。

**后续五层恢复改用上述新恢复脚本。** 它只增加补充/登记/来源SHA校验并把latest和independent定义指向新父程序和精确addendumSHA；原35轮checkpoint、四次26GiB门限、原参数/环境、意图/归档/隐藏启动及前三层命令完全保留。旧1544脚本保留作来源证据，不再用它启动第四第五层。先primary ValidateOnly通过再逐层实际启动并确认owner，已有intent/部分移动仍先审查，不能清除重放。原独立v2 plan SHA a5318f...和原latest plan SHA80acc...始终不变；没有派生新的科学计划或制造末轮权重。

09:38:53最新真实可用commit17.4592056274GiB、无Python，四状态SHA仍原故障值，第五层status无。未运行低于26GiB的ValidateOnly或启动，主实验仍13/42完整、当前35/80、正式评估0。FINAL_MACHINE_SNAPSHOT和FINAL_ADOPTION及README记录最终状态。轻量兼容集成完成；不要再声称旧入口尚未接入，不重复这些通过的测试。下一步优先真实恢复；另有新方法六slot效率worker/全图库/计时/退出汇总仍未完成，参看先前HANDOFF。

09:38浏览器连接仍失败，当前Overleaf登录未知，没有上传或新网址。当前14页主文和4页补充PDF哈希再次一致，open_in_codex仍queued；本轮按用户再次索取交付全文链接，未修改稿件数值。
'''
with (EXECUTION / 'HANDOFF.md').open('a', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps({'final_adoption_sha256': sha(HERE / 'FINAL_ADOPTION.json'),
                  'recovery_report_sha256': sha(HERE / 'STARTUP_SCRIPT_MOCK_9f9eae81e782_093737472.json')}))
