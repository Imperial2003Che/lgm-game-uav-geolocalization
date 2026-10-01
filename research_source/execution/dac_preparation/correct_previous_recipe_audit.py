"""Back up then correct only DAC findings in the earlier non-pinned audit."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
import shutil

P = Path(__file__).resolve().parent
E = P.parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    md = E/'latest_baseline_recipe_audit.md'
    js = E/'latest_baseline_recipe_audit.json'
    original_text = md.read_text(encoding='utf-8')
    old = json.loads(js.read_text(encoding='utf-8'))
    assert old['recipes']['DAC']['fields']['total_epochs']['value'] is None, 'Existing correction retained; do not repeat.'
    plan = json.loads((P/'DAC_RECIPE_PLAN.json').read_text(encoding='utf-8'))
    archive = json.loads((P/'archive_recipe_texts.json').read_text(encoding='utf-8'))
    backup = P/'superseded_recipe_audit'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True, exist_ok=False)
    ledger = {'started_utc':datetime.now(timezone.utc).isoformat(),'generator_path':str(Path(__file__).resolve()),'generator_sha256':sha(__file__),'originals':{}}
    for path in (md,js):
        target=backup/path.name
        shutil.copy2(path,target)
        assert sha(path)==sha(target)
        ledger['originals'][str(path)]={'sha256':sha(path),'backup_path':str(target),'backup_sha256':sha(target)}
    changes = [
        ('**CAMP 的一轮训练已有作者本人后续确认；DAC 的一轮仍只有源码默认值支持。** 两篇正文都没有明确总训练轮数。不能把两者混写成“论文均规定一轮”，也不能因为默认值看起来少就自行补成80轮。',
         '**CAMP 的一轮训练已有作者本人后续确认；DAC 的一轮现已由作者答复与官方发布权重日志补齐证据。** 两篇正文都没有明确总训练轮数。DAC 的 University-1652 有 OWNER 后续答复及官方 ZIP 日志，SUES-200 四个高度有官方 ZIP 脚本及完成日志。不能把这些后续证据改称“论文均规定一轮”。'),
        ('| 总epoch | 正文未写；作者2025-04-15在 issue #8 明确U-1652、SUES-200单轮即可，继续训练会过拟合 | 正文未写；未找到公开作者明确确认 |',
         '| 总epoch | 正文未写；作者2025-04-15在 issue #8 明确U-1652、SUES-200单轮即可，继续训练会过拟合 | 正文未写；University单轮由OWNER于2025-04-18确认，且官方ZIP日志佐证；SUES四高度单轮由各自官方ZIP脚本和完成日志佐证 |'),
        ('不能单独证明论文训练时长。',
         '不能单独证明论文训练时长；本次补查已由[University作者答复](https://github.com/SummerpanKing/DAC/issues/5#issuecomment-2814910469)和官方发布权重的五组脚本/完成日志确认一轮设置。SUES归档的DSA系数为0.3，与当前仓库默认0.6不同，应按所选配方显式登记。'),
        ('- DAC可优先核验官方已训练权重。若自行重训，在总时长来源补齐前，应把选定时长标为明确的适配方案；不要称“论文完整配方已经核实”，也不要为了达到原报分数不断用测试集调整训练轮数。',
         '- DAC可按“官方发布权重归档所记录的单轮配方”准备重训：University的DSA系数0.6、SUES四高度0.3，384输入、24对批量、seed1。训练固定最后轮保存，随后完整图库评估；seed2/3属于本机多种子扩展。环境、增强语义和批内采样仍需预检，不通过测试分数调整时长。'),
    ]
    text=original_text
    for before,after in changes:
        assert text.count(before)==1, f'Unexpected occurrence count: {before[:65]}'
        text=text.replace(before,after)
    text += '\n## 2026-09-14 DAC 归档证据补充\n\n'
    text += ('此前“全部公开issue没有作者确认”的结论遗漏了 issue #5 中 OWNER 的单轮回复，本次已纠正。'
             'University答复不能直接外推SUES；SUES结论依据官方README链接ZIP中的150/200/250/300四份train.py与log.txt，均记录并完成Epoch 1。'
             '五份脚本和日志通过HTTP Range读取、ZIP CRC32及本地SHA256核验，原始成员、来源URL和偏移见 `dac_preparation/archive_recipe_texts.json`。'
             'University归档train.py与固定仓库逐行一致；SUES归档weight_dsa=0.3，固定仓库为0.6。'
             '作者日志中的性能数字单独保存在 `dac_preparation/AUTHOR_ARCHIVE_LOG_VALUES.json`，不作为本机复现实测。'
             '完整适配方案与审查在 `dac_preparation/DAC_RECIPE_PLAN.md/.json`；旧审计原件及散列已保存在 `dac_preparation/superseded_recipe_audit/`。CAMP科学结论保持不变。\n')
    new=copy.deepcopy(old)
    dac=new['recipes']['DAC']
    old_epoch=copy.deepcopy(dac['fields']['total_epochs'])
    maintainer={'type':'maintainer_comment','url':'https://github.com/SummerpanKing/DAC/issues/5#issuecomment-2814910469',
        'author':'SummerpanKing','association':'OWNER','created_at':'2025-04-18T08:25:22Z',
        'api_source':'https://api.github.com/repos/SummerpanKing/DAC/issues/comments/2814910469',
        'scope':'Normal and multi-weather University-1652; not directly SUES-200'}
    archive_evidence=[]
    for item in archive['members']:
        path=Path(item['local_path'])
        assert sha(path)==item['sha256']
        content=path.read_text(encoding='utf-8-sig').splitlines()
        anchors=[i for i,line in enumerate(content,1) if ('Train Epochs:' in line or "add_argument('--epochs'" in line or "add_argument('--weight_dsa'" in line or 'weight_dsa:' in line)]
        archive_evidence.append({'type':'official_checkpoint_archive_member','archive_url':archive['archive_source'],
            'member_name':item['name'],'local_path':str(path),'sha256':item['sha256'],'crc32_hex':item['crc32_hex'],'lines':anchors})
    dac['fields']['total_epochs']={'value':1,'status':'maintainer_and_released_checkpoint_archive_confirmed_not_explicit_in_paper',
        'evidence':old_epoch['evidence']+[maintainer]+archive_evidence,
        'by_dataset':{'University-1652':{'value':1,'status':'maintainer_confirmed_after_publication_and_archive_log_confirmed'},
                      'SUES-200':{'value':1,'heights_m':[150,200,250,300],'status':'official_released_checkpoint_script_and_completed_log_confirmed'}},
        'note':'The paper does not explicitly state total epochs. Earlier audit missed OWNER issue #5 confirmation for University. SUES evidence is four separate official ZIP scripts and completed one-epoch logs, not extrapolation from that comment.'}
    dac['fields']['dsa_loss_weight_released_recipe']={'value':{'University-1652':0.6,'SUES-200':0.3},
        'status':'official_checkpoint_archive_confirmed_differs_from_current_SUES_repository_default',
        'pinned_repository_default':{'University-1652':0.6,'SUES-200':0.6},'evidence':archive_evidence,
        'note':'Explicitly choose archive0.3 for SUES released-recipe reproduction. Keep repository default evidence unchanged.'}
    policy_before=old['recipes']['DAC']['launch_policy']
    delimiter=' DAC:'
    assert delimiter in policy_before
    camp_sentence=policy_before.split(delimiter)[0]
    dac_sentence=' DAC: one epoch is supported by University OWNER confirmation and all five released-checkpoint script/log pairs; SUES uses archive DSA0.3 rather than current repository0.6. Prepare an independent environment and train-only final-epoch adapter, preflight complete24-pair optimizer steps, and evaluate the complete gallery after checkpoint freeze. Smaller batches remain a separate resource-adapted protocol.'
    dac['launch_policy']=camp_sentence+dac_sentence
    # This field was a duplicate combined CAMP+DAC policy inside the CAMP object.
    # Preserve its CAMP sentence verbatim; correct only the embedded DAC sentence.
    new['recipes']['CAMP']['launch_policy']=camp_sentence+dac_sentence
    camp_before=copy.deepcopy(old['recipes']['CAMP']);camp_after=copy.deepcopy(new['recipes']['CAMP'])
    assert camp_before.pop('launch_policy').split(delimiter)[0]==camp_after.pop('launch_policy').split(delimiter)[0]
    assert camp_before==camp_after
    new['dac_correction_utc']=datetime.now(timezone.utc).isoformat()
    new['dac_correction_provenance']={'plan_path':str(P/'DAC_RECIPE_PLAN.json'),'plan_sha256':sha(P/'DAC_RECIPE_PLAN.json'),
        'previous_total_epochs_field':old_epoch,'backup_directory':str(backup),
        'CAMP_scientific_fields_unchanged':True,'CAMP_combined_policy_only_DAC_clause_updated':True}
    # Prepare both corrected files completely before replacing their originals.
    md_new=P/'latest_baseline_recipe_audit.corrected.md'
    json_new=P/'latest_baseline_recipe_audit.corrected.json'
    md_new.write_text(text,encoding='utf-8')
    json_new.write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert json.loads(json_new.read_text(encoding='utf-8'))['recipes']['DAC']['fields']['total_epochs']['value']==1
    shutil.copy2(md_new,md)
    shutil.copy2(json_new,js)
    ledger.update(status='corrected_with_verified_backups',finished_utc=datetime.now(timezone.utc).isoformat(),
        updated={str(md):sha(md),str(js):sha(js)},CAMP_scientific_fields_unchanged=True,
        note='CAMP fields unchanged. A combined launch_policy nested in CAMP had its DAC clause corrected; CAMP clause retained verbatim.')
    (P/'RECIPE_AUDIT_CORRECTION.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':ledger['status'],'backup_directory':str(backup),'updated':ledger['updated']},ensure_ascii=False))

if __name__=='__main__':
    main()
