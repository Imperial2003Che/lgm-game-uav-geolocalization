"""CPU-only source/metadata audit. Does not import torch or execute DAC code."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import importlib.metadata as metadata
import json
import re
import sys

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
REPO = ROOT / 'literature/official_repos/snapshots/SummerpanKing__DAC__5612a79c3928'
COMMIT = '5612a79c3928d8a71939e4e761bb352f805cb51b'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(name, obj):
    (P / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def arguments(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != 'add_argument':
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        option = node.args[0].value
        if not isinstance(option, str) or not option.startswith('--'):
            continue
        values = {}
        for kw in node.keywords:
            if kw.arg == 'default':
                try:
                    values['default'] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    values['default_expression'] = ast.unparse(kw.value)
        found[option[2:]] = dict(values, line=node.lineno)
    return found

def evidence(path, start=None, end=None):
    return {'path': str(path), 'sha256': sha(path), 'start_line': start, 'end_line': end}

def main():
    assert REPO.is_dir()
    source_files = sorted(REPO.rglob('*.py'))
    for source_file in source_files:
        ast.parse(source_file.read_text(encoding='utf-8-sig'), filename=str(source_file))
    manifest = {str(f.relative_to(REPO)).replace('\\', '/'): sha(f) for f in source_files}
    for extra in ('README.md', 'LICENSE'):
        if (REPO / extra).is_file():
            manifest[extra] = sha(REPO / extra)
    pinned = {name: arguments(REPO / name) for name in ('train_university.py', 'train_sues200.py')}
    archive = json.loads((P / 'archive_recipe_texts.json').read_text(encoding='utf-8'))
    configurations = []
    author_log_values = []
    for entry in archive['members']:
        path = Path(entry['local_path'])
        assert sha(path) == entry['sha256']
        if not entry['name'].endswith('/train.py'):
            continue
        protocol = 'University-1652' if '/U1652/' in entry['name'] else 'SUES-200'
        height = None if protocol == 'University-1652' else int(entry['name'].split('/')[-2])
        current_name = 'train_university.py' if height is None else 'train_sues200.py'
        config = arguments(path)
        changes = {k: {'archive': config.get(k), 'pinned_repository': pinned[current_name].get(k)}
                   for k in sorted(set(config) | set(pinned[current_name]))
                   if {t: v for t, v in config.get(k, {}).items() if t != 'line'} !=
                      {t: v for t, v in pinned[current_name].get(k, {}).items() if t != 'line'}}
        log_path = path.with_name(path.name.replace('__train.py', '__log.txt'))
        log_text = log_path.read_text(encoding='utf-8')
        epoch_match = re.search(r'Train Epochs:\s+(\d+)\s+- Train Steps:\s+(\d+)', log_text)
        sample_match = re.search(r'Original Length:\s+(\d+)\s+- Length after Shuffle:\s+(\d+)', log_text)
        metric_match = re.search(r'Recall@1:\s+([0-9.]+).*?Recall@5:\s+([0-9.]+).*?Recall@10:\s+([0-9.]+).*?Recall@top1:\s+([0-9.]+).*?AP:\s+([0-9.]+)', log_text)
        assert epoch_match and sample_match and metric_match
        assert int(epoch_match[1]) == config['epochs']['default'] == 1
        config_record = {
            'dataset': protocol, 'height_m': height, 'training_duration_status': 'official_released_checkpoint_log_confirmed',
            'paper_total_epochs_explicit': False, 'epochs': int(epoch_match[1]), 'batch_size_pairs': config['batch_size']['default'],
            'seed': config['seed']['default'], 'input_hw': [config['img_size']['default']] * 2,
            'nclasses': config['nclasses']['default'], 'weight_dsa': config['weight_dsa']['default'],
            'weight_cls': config['weight_cls']['default'], 'weight_infonce': config['weight_infonce']['default'],
            'lr': config['lr']['default'], 'warmup_argument': config['warmup_epochs']['default'],
            'scheduled_steps_logged': int(epoch_match[2]), 'original_pair_count_logged': int(sample_match[1]),
            'post_shuffle_pair_count_logged': int(sample_match[2]),
            'full_batches_inferred_from_logged_samples': int(sample_match[2]) // config['batch_size']['default'],
            'actual_optimizer_steps_measured_locally': None,
            'script': evidence(path), 'log': evidence(log_path), 'archive_member': entry['name'],
            'all_archive_cli_defaults': config, 'differences_vs_pinned_cli_defaults': changes,
        }
        configurations.append(config_record)
        author_log_values.append({'source_type': 'official_author_checkpoint_archive_log_not_local_measurement',
            'dataset': protocol, 'height_m': height, 'direction': 'drone_to_satellite',
            'metrics_percent': dict(zip(('R@1','R@5','R@10','author_Recall@top1','AP'), map(float, metric_match.groups()))),
            'protocol': 'author_evaluator_with_nonquery_gallery_IDs_relabelled_minus1_then_removed',
            'log': evidence(log_path)})
        delta = ''.join(difflib.unified_diff((REPO/current_name).read_text(encoding='utf-8-sig').splitlines(True),
                     path.read_text(encoding='utf-8-sig').splitlines(True), fromfile=f'pinned/{current_name}', tofile=entry['name']))
        (P / (path.stem + '.diff')).write_text(delta, encoding='utf-8')
    configs_by_key = {(x['dataset'], x['height_m']): x for x in configurations}
    assert configs_by_key[('University-1652',None)]['weight_dsa'] == 0.6
    assert all(configs_by_key[('SUES-200',h)]['weight_dsa'] == 0.3 for h in (150,200,250,300))
    names = ['torch','torchvision','timm','numpy','Pillow','albumentations','opencv-python','opencv-python-headless','imgaug','transformers','tensorboard','tqdm','scipy']
    versions = {}
    for name in names:
        try: versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError: versions[name] = None
    import numpy as np
    runtime = {'python': sys.executable, 'python_version': sys.version, 'versions': versions,
        'numpy_in1d_exists': hasattr(np,'in1d'), 'numpy_sctypes_exists': hasattr(np,'sctypes'),
        'numpy_isin_fixture': np.isin([1,2,3],[2]).tolist(), 'torch_imported': 'torch' in sys.modules,
        'cuda_initialized': False, 'cuda_statement_basis': 'torch was not imported by this audit',
        'source_python_files_ast_parsed': len(source_files)}
    assert runtime['torch_imported'] is False
    plan = {
        'status': 'source_grounded_recipe_prepared_adapter_and_runtime_pending',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'generator': evidence(Path(__file__)),
        'source': {'repository': 'https://github.com/SummerpanKing/DAC','commit':COMMIT,'local_path':str(REPO),'license':'Apache-2.0','files_sha256':manifest},
        'paper': {'title':'Enhancing Cross-View Geo-Localization With Domain Alignment and Scene Consistency',
                  'doi':'10.1109/TCSVT.2024.3443510','url':'https://skyearth.org/publication/papers/2024_ecvglwdasc.pdf','implementation_details_pdf_page':7},
        'recipe_correction': {
            'supersedes_statement_only': 'execution/latest_baseline_recipe_audit.md and HANDOFF.md: DAC total epochs unconfirmed',
            'University_1652': 'One epoch supported by official issue #5 OWNER comment and released checkpoint log.',
            'SUES_200': 'One epoch supported by four released checkpoint scripts/logs; not a claim that paper explicitly states it.',
            'SUES_weight_dsa': 'Use archive-grounded 0.3 for released-recipe reproduction; pinned GitHub default is 0.6.'},
        'author_sources': [
            {'url':'https://github.com/SummerpanKing/DAC/issues/5#issuecomment-2814910469','claim':'Normal and multi-weather University settings use one epoch','scope':'University-1652'},
            {'url':'https://github.com/SummerpanKing/DAC/issues/5#issuecomment-2815293634','claim':'Shared University weights do not use weather augmentation'},
            {'url':'https://github.com/SummerpanKing/DAC/issues/5#issuecomment-2819955663','claim':'Satellite weather augmentation remains off; seed default one'},
            {'url':'https://github.com/SummerpanKing/DAC/issues/7#issuecomment-2889980571','claim':'Last experiment rather than best/average across repeats; does not independently define final-epoch policy'}],
        'official_archive_recipes': configurations,
        'model': {
            'entry':'sample4geo.hand_convnext.model.two_view_net','backbone':'custom registered ConvNeXt-Base',
            'depths':[3,3,27,3],'dims':[128,256,512,1024],'inference_descriptor':'L2-normalized 1024-dimensional GAP returned as model(img)[-2]',
            'pretrained_url':'https://dl.fbaipublicfiles.com/convnext/convnext_base_22k_1k_224.pth',
            'pretrained_status':'Official backbone URL in source and archive logs; not downloaded by this task',
            'pretraining_description':'ImageNet-22k, then 1k finetuning as indicated by official filename; training crop is separately 384x384',
            'constructing_official_model_attempts_network':True,'required_eval_adapter_change':'Construct without pretrained backbone fetch when loading a complete pinned author checkpoint; verify every model key and shape.',
            'CAMP_reuse_boundary':'Can share RGB decoding, complete-gallery ranking and compatible ConvNeXt code. Never substitute CAMP checkpoint or ignore DAC DSA/classifier keys.'},
        'runtime_audit':runtime,
        'runtime_plan':{
            'existing_pinned_environments_modified':False,'independent_environment_required':True,
            'official_lockfile_available':False,
            'pending_packages':['albumentations with original argument semantics','opencv-python-headless','imgaug if weather module retained','tensorboard if official import retained'],
            'issues':[
                'NumPy 2.4.4 actually lacks np.in1d: official evaluator lines 88/93 fail. Derived adapter may use equivalent np.isin on flat rank indices with tiny parity fixture.',
                'Official dataset imports imgaug unconditionally and builds weather augmenters at import; numpy.sctypes is absent. imgaug compatibility must be checked in an isolated candidate environment, not patched into the primary environment.',
                'Albumentations API versions may alter old ImageCompression/CoarseDropout arguments. Pin and verify actual transforms; do not accept ignored-argument warnings.',
                'Official trainer non-AMP branch does not compute classification/DSA and references undefined monitoring variables. Preserve single-GPU AMP recipe; any CPU/full-precision training adapter must implement all original losses.',
                'Official trainer multi-GPU branch does not define loss_cls/loss_DSA. Restrict first reproduction to one GPU.',
                'Bool CLI uses type=bool; never pass --only_test False expecting training.',
                'timm custom model registration/pretrained signature requires CPU static/meta check in the final independent environment before resource probe.'
            ]},
        'data_protocol':{
            'University_test_root':r'C:\项目\IMTMN\datasets\University-1652\test',
            'SUES_root':r'C:\项目\IMTMN\datasets\SUES-200',
            'SUES_train_manifest':r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\manifests\sues200_official_train_ids.yaml',
            'training':'Use only official train locations; University 701 train location classes; SUES 120 train locations and 80 evaluation locations, height-specific runs.',
            'SUES_classifier_outputs':200,'SUES_classifier_explanation':'Archive uses nclasses=200 while train loader remaps its 120 train IDs to contiguous labels. Preserve this architecture for strict released-recipe/checkpoint parity; do not silently change to 120.',
            'source_loader':'Both train entrypoints import sample4geo.dataset.university, not dataset/sues-200.py.',
            'source_pairing':'One satellite paired with each train drone frame, class-unique custom batch shuffle, synchronized horizontal flips; no test images needed.',
            'ordering':'Record resolved paths, ID mapping, native traversal order, sampled list and omitted samples. Sorting changes native stochastic input order and must be explicit.',
            'full_gallery':'Keep every gallery image and its original location ID in D2S and S2D. Do not convert nonquery IDs to -1 or discard them.',
            'complete_gallery_counts':'Determine from frozen original manifests and verify files; no hardcoded count substitute.',
            'author_metric_caveat':'Native loader relabels nonquery IDs as -1, and evaluator removes them. Author log scores are not full-gallery local results.',
            'metrics':'Frozen common per-query CMC/AP protocol, stable declared tie handling, no junk-removal of distractors. Report R@1/R@5/R@10/R@1%/mAP with explicit AP integration definition.',
            'top1_percent_caveat':'Author evaluator computes round(G*.01) then CMC[index], producing rank index+1; do not call this identical to a corrected common R@1% definition.'},
        'training_adapter_plan':{
            'selection_rule':'Final epoch fixed at one before any test evaluation; all training branches train-only.',
            'seeds':[1,2,3],'seed_status':'Three-seed local extension; author script/log evidence is seed1 only.',
            'optimizer':'AdamW lr0.001; archive default decay_exclue_bias=False uses model.parameters and runtime-default betas/eps/weight_decay. Record effective values after construction.',
            'losses':'1.0 InfoNCE + 0.1 sum of both-view classification loss + DSA loss (U0.6, SUES0.3). Keep learnable InfoNCE temperature and DSA MLP.',
            'loss_details':'InfoNCE uses CrossEntropyLoss(label_smoothing=0.1); classification uses unsmoothed CrossEntropyLoss. DSA_loss.if_infoNCE=False: transpose/flatten aligned tensors per sample, then 1 minus mean cosine similarity. The source name mse_loss does not mean squared-error MSE here. Triplet and blocks InfoNCE objects are constructed but not included in the active total loss. Keep unused parameter keys for checkpoint parity.',
            'return_features_flag':'Official make_model passes triplet_loss=0.3 as truthy return_f; do not set return_f=False in training or the five-output branch disappears.',
            'precision':'Native single-GPU CUDA AMP with GradScaler(init_scale=1024), clip_grad_value_=100, optimizer/scaler/scheduler complete step.',
            'warmup':'Official University 0.1*total scheduled steps; SUES0.1*steps_per_epoch. One epoch makes these equal; retain source schedule and record actual post-shuffle optimizer steps.',
            'sampler':'Retain original class-unique 24-pair batching and original discard behavior; record each sampled ID and number of omitted pairs.',
            'resource_probe':'After GPU release only: train-sample construction and two complete optimizer steps with 24 pairs; record peak allocated/reserved memory, weights/env/source hashes. If OOM, do not equate accumulated microbatches with original batch mining.',
            'resource_adapted_branch':'Any smaller training batch or accumulation goes in a separately registered resource-adapted protocol, not author-recipe replication.',
            'checkpoint':'Save final weights plus optimizer, scheduler, scaler, Python/NumPy/Torch/CUDA RNG, configuration, sampler state, epoch/step and manifest hashes; atomic update and preserve failures.',
            'native_test_code_to_remove_in_derived_adapter':'Do not construct test loaders during training; no initial eval, per-epoch test eval, R1 tracking or test-best saves. Test only after final checkpoint hash is frozen.',
            'expected_scope':'U seed1/2/3 plus SUES heights150/200/250/300 each seed1/2/3 =15 independent one-epoch fits. Separate from one author-checkpoint reevaluation.'},
        'execution_readiness':{'registered_gpu_job':False,'gpu_started':False,'author_checkpoint_loaded':False,
            'ready_now':['source-grounded recipe audit','exact official University checkpoint retrieval via bounded validated Range'],
            'before_evaluation':['complete checkpoint byte/CRC/SHA verification','restricted checkpoint metadata/key verification','independent environment and adapter provenance freeze','tiny complete-gallery metric fixture and preprocessing parity','serial GPU resource probe after active queue'],
            'before_independent_training':['train-only adapter','actual dependency imports and train augmentation fixtures','train manifest/ID/order hash','complete loss/optimizer step resource profile','15-fit final-epoch registration']},
        'not_equivalent_protocols':['Original six-corruption by five-severity matrix is not DAC multi-weather University protocol.','Released University weight is normal-weather training; separate weather training is required for weather-trained comparison.','University-to-SUES transfer is separate from per-height SUES training. Cross-domain paper batch48 unit is not re-specified; do not silently reassign pairs.']
    }
    dump('DAC_RECIPE_PLAN.json',plan)
    dump('AUTHOR_ARCHIVE_LOG_VALUES.json',author_log_values)
    dump('CPU_RUNTIME_AUDIT.json',runtime)
    dump('SOURCE_SHA256.json',{'repository':str(REPO),'commit':COMMIT,'files':manifest})
    print(json.dumps({'status':plan['status'],'recipes':len(configurations),'source_files':len(manifest),'torch_imported':runtime['torch_imported'],'output':str(P/'DAC_RECIPE_PLAN.json')},ensure_ascii=False))

if __name__=='__main__':
    main()
