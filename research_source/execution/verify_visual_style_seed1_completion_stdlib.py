"""Read-only audit of the newly completed resumed fit. No tensor imports."""
from pathlib import Path
import datetime,hashlib,json,math,sys
HERE=Path(__file__).resolve().parent
ROOT=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
RUN=ROOT/'lgm_game_pytorch/runs/formal_main/university1652/visual_style/seed_1'
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
manifest=json.loads((RUN/'run_manifest.json').read_text(encoding='utf-8'))
assert manifest['status']=='completed' and manifest['epochs_completed']==80 and manifest['best_epoch']==79
assert manifest['test_protocol_was_evaluated'] is False and manifest['best_validation_mAP'] is None
for name,value in manifest['artifacts'].items():
    assert (RUN/name).stat().st_size==value['bytes'] and sha(RUN/name)==value['sha256']
history=json.loads((RUN/'history.json').read_text(encoding='utf-8'))
assert [r['epoch'] for r in history]==list(range(80))
assert all(r['validation']=={} and r['validation_selection_mAP'] is None for r in history)
assert all(math.isfinite(r['train_loss']) and 0<=r['train_batch_top1']<=1 for r in history)
assert all(r['optimizer_steps']==652 and r['examples_seen']==41728 for r in history)
assert manifest['dependencies_and_device']['packages']=={'numpy':'2.4.4','Pillow':'12.2.0','torch':'2.11.0+cu126','torchvision':'0.26.0+cu126'}
config=json.loads((RUN/'run_config.json').read_text(encoding='utf-8'))
assert config['run_config_sha256']==manifest['run_config_sha256']=='37cd817f16b78c070d8bed229cacbf9ad7c962588e35aa27b6d52cc4bb499549'
completed=[]
for path in (ROOT/'lgm_game_pytorch/runs/formal_main').glob('*/*/seed_*/run_manifest.json'):
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('status')=='completed':completed.append(str(path))
report={'status':'new_complete_fit_artifacts_verified','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_directory':str(RUN),'manifest_sha256':sha(RUN/'run_manifest.json'),'epochs_completed':80,'final_epoch_zero_based':79,'full_formal_fits_with_completed_manifests':len(completed),'completed_fit_paths':completed,'verified_artifacts':manifest['artifacts'],'test_results_produced':False,'actual_tensor_deserialization_performed':False,'scientific_imports':[],
 'timing':{'manifest_total_training_seconds':manifest['total_training_seconds'],'scope':'last resumed process only; must not be reported as total 80-epoch training time','sum_of_80_accepted_epoch_elapsed_seconds':sum(r['elapsed_seconds'] for r in history),'accepted_epoch_sum_scope':'sum of stored complete epochs only; excludes setup and failed/inactive or quarantined work'},
 'optimizer_history_note':'optimizer_steps in the unchanged original history is the planned/attempted batch count; do not describe it as an instrumented count of successful AdamW updates.',
 'progress_display_note':'Main wrapper can retain active_progress from the preceding fit during initialization of the next fit. Cross-check active.output_dir and manifest.updated_utc against active.started_utc.'}
assert not any(n in sys.modules for n in ('torch','numpy','scipy','PIL'))
(HERE/'VISUAL_STYLE_SEED1_COMPLETION_20260914.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'completed_fits':len(completed),'epochs':80,'test_results':False,'accepted_epoch_elapsed_seconds':report['timing']['sum_of_80_accepted_epoch_elapsed_seconds']}))
