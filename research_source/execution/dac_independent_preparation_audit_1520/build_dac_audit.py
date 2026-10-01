"""Source-only DAC independent-training gap audit; no scientific imports."""
import ast
import copy
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXECUTION=HERE.parent
DAC=EXECUTION.parent/'literature/official_repos/snapshots/SummerpanKing__DAC__5612a79c3928'
CAMP=EXECUTION.parent/'literature/official_repos/snapshots/Mabel0403__CAMP__b04a9c856711'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def tree(p):
    return ast.parse(p.read_text(encoding='utf-8'))

def named(p,name):
    return next(n for n in tree(p).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)

def ref(p,start=None,end=None):
    return {'path':str(p),'sha256':sha(p),'line_start':start,'line_end':end}

def main():
    pin=json.loads((EXECUTION/'dac_preparation/source_pins.json').read_text(encoding='utf-8'))
    all_source=[]
    for name,row in pin['official_source_files'].items():
        p=DAC/name
        assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'], name
        all_source.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
    train=DAC/'train_university.py'
    dataset=DAC/'sample4geo/dataset/university.py'
    trainer=DAC/'sample4geo/trainer.py'
    model=DAC/'sample4geo/hand_convnext/ConvNext/make_model.py'
    common={}
    for name in ('get_data','U1652DatasetTrain','get_transforms'):
        left=named(dataset,name)
        right=named(CAMP/'sample4geo/dataset/university.py',name)
        left_dump=ast.dump(left,include_attributes=False)
        right_dump=ast.dump(right,include_attributes=False)
        same=left_dump==right_dump
        common[name]={'ast_identical':same,'DAC':ref(dataset,left.lineno,left.end_lineno),
            'CAMP':ref(CAMP/'sample4geo/dataset/university.py',right.lineno,right.end_lineno)}
        if not same:
            left_text=ast.unparse(left).splitlines(True)
            right_text=ast.unparse(right).splitlines(True)
            (HERE/(name+'_CAMP_to_DAC_AST.diff')).write_text(''.join(difflib.unified_diff(
                right_text,left_text,fromfile='CAMP AST',tofile='DAC AST')),encoding='utf-8')
            common[name]['AST_diff']=str(HERE/(name+'_CAMP_to_DAC_AST.diff'))
    backbone='sample4geo/hand_convnext/ConvNext/backbones/model_convnext.py'
    common['backbone_file_byte_identical']={'equal':sha(DAC/backbone)==sha(CAMP/backbone),
        'sha256':sha(DAC/backbone)}
    common['utils_file_byte_identical']={'equal':sha(DAC/'sample4geo/utils.py')==sha(CAMP/'sample4geo/utils.py'),
        'sha256':sha(DAC/'sample4geo/utils.py')}
    def strip_docstrings(node):
        node=copy.deepcopy(node)
        for part in ast.walk(node):
            if isinstance(part,(ast.ClassDef,ast.FunctionDef)) and part.body and isinstance(part.body[0],ast.Expr) and isinstance(part.body[0].value,ast.Constant) and isinstance(part.body[0].value.value,str):
                part.body.pop(0)
        return node
    d=strip_docstrings(named(dataset,'U1652DatasetTrain'))
    c=strip_docstrings(named(CAMP/'sample4geo/dataset/university.py','U1652DatasetTrain'))
    assert ast.dump(d,include_attributes=False)==ast.dump(c,include_attributes=False)
    common['U1652DatasetTrain']['only_AST_difference']='docstring indentation; all executable AST nodes identical'
    d=copy.deepcopy(named(dataset,'get_transforms'))
    c=copy.deepcopy(named(CAMP/'sample4geo/dataset/university.py','get_transforms'))
    weather=d.body.pop(0)
    assert ast.unparse(weather)=='weather_id = 0'
    assert not any(isinstance(n,ast.Name) and n.id=='weather_id' for n in ast.walk(d))
    assert ast.dump(d,include_attributes=False)==ast.dump(c,include_attributes=False)
    common['get_transforms']['only_AST_difference']='unused weather_id=0 local assignment; all actual augmentation operators and arguments identical'
    archived=EXECUTION/'dac_preparation/official_archive_metadata/pretrained_models__U1652__train.py'
    assert sha(train)==sha(archived)
    defaults={}
    for n in ast.walk(tree(train)):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument':
            flag=ast.literal_eval(n.args[0])
            default=next(k.value for k in n.keywords if k.arg=='default')
            try: value=ast.literal_eval(default)
            except (ValueError,TypeError): value={'expression':ast.unparse(default)}
            defaults[flag.removeprefix('--')]={'value':value,'line':n.lineno}
    recipe=[
        ('inputs','384x384, two shared views; training satellite and drone only; classes701',ref(train,35,50),ref(train,130,139)),
        ('native_training','batch24 pairs (48 images), one full epoch, seed1; seeds2/3 are local repeated-seed extension',ref(train,59,65)),
        ('loss','InfoNCE + 0.1*(CE_satellite + CE_drone) + 0.6*DSA; CE label smoothing only InfoNCE0.1',ref(train,295,309),ref(trainer,31,76)),
        ('DSA','1 minus mean cosine of flattened concatenated feature/projection; not squared MSE; if_infoNCE False',ref(DAC/'sample4geo/loss/DSA_loss.py',19,42),ref(model,245,282)),
        ('optimizer','All parameters AdamW lr0.001 with installed defaults; original value clipping100; AMP scaler init1024; scheduler advances after every attempt including skip',ref(train,311,368),ref(trainer,76,92)),
        ('schedule','cosine,10% of pre-shuffle total steps warmup; original scheduler constructed before unique-ID shuffle',ref(train,376,424)),
        ('input_order','701 sorted identities; os.walk file order retained; each drone matched to first satellite; unique-place batches and stop counter512',ref(dataset,15,168)),
        ('augmentations','original paired horizontal flip0.5; compression90-100; exact-linear resize; color jitter; blur/sharpen; grid/coarse dropout; satellite rotate90',ref(dataset,68,90),ref(dataset,358,424)),
        ('pretrained','local original ConvNeXt Base344-state initialization,22k->1k224 source; data size384 separately set; constructor defaults preserved',ref(DAC/backbone,156,196),ref(model,209,220)),
        ('model_schema','402 states:395 float32 +7 int64;96,499,052 parameter elements; includes unused projection/heads; no pos_scale patch',ref(EXECUTION/'dac_preparation/strict_meta_compatibility.json')),
        ('classification_and_unused','3 heads; triplet_loss0.3 acts as return_f truthy; Triplet/blocks objects constructed but not part of selected loss',ref(DAC/'sample4geo/hand_convnext/model.py',92,98),ref(model,222,282),ref(trainer,43,69)),
        ('seeding','Python,NumPy,TorchCPU+CUDA seeds; requested cudnn_benchmark defaultTrue is assigned to nonstandard benchmark_enabled spelling; record actual backend state without silent protocol repair',ref(DAC/'sample4geo/utils.py',33,48),ref(train,117,120)),
        ('source_reported_steps','author log37854 pre-shuffle pairs ->37848 sampled ->1577 full batches; scheduler1578,warmup157.8. These are author log/inferred counts; independently record exact sampled counts and actual optimizer updates',ref(EXECUTION/'dac_preparation/official_archive_metadata/pretrained_models__U1652__log.txt',22,33))
    ]
    remove=[
        {'item':'Test import/path/CLI', 'sources':[ref(train,15,18),ref(train,53,56),ref(train,67,71),ref(train,104,108),ref(train,130,139)]},
        {'item':'Test Dataset and DataLoaders/count prints created even when zero_shot=False', 'sources':[ref(train,233,260)]},
        {'item':'Only-test checkpoint mode deletes six classifier keys and strict=False loads', 'sources':[ref(train,265,290)]},
        {'item':'Optional starting checkpoint strict=False and zero-shot call', 'sources':[ref(train,192,196),ref(train,409,418)]},
        {'item':'Per-epoch test score and test-best checkpoint', 'sources':[ref(train,435,477)]},
        {'item':'Replace plain last-weight-only save with full final state, no new scientific update', 'sources':[ref(train,479,489)]}
    ]
    evidence_names=['dac_preparation/DAC_RECIPE_PLAN.json','dac_preparation/RECIPE_AUDIT_CORRECTION.json',
        'dac_preparation/issue5.json','dac_preparation/issue5_comments.json','dac_preparation/archive_recipe_texts.json',
        'dac_preparation/strict_meta_compatibility.json','dac_preparation/author_checkpoint_metadata.json',
        'camp_training_preparation/PRETRAINED_META_VALIDATION.json',
        'camp_training_inputs/university_train_content_manifest.json','camp_training_preparation/REAL_PAIR_CPU_adapter_reader.json',
        'camp_training_preparation_v2/PREPARATION_MANIFEST.json']
    record={'status':'audit_complete_DAC_adapter_not_created', 'created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Source-only University DAC independent-training preparation; no live repository refresh, scientific imports, tensors, image decoding, training, resource profile, evaluation, queue registration or release creation.',
        'source':{'repo':pin['repository'],'commit':pin['source_commit'],'root':str(DAC),'files':all_source},
        'archive_university_script_identical':{'equal':True,'current':ref(train),'archive':ref(archived)},
        'configuration_defaults':defaults,
        'recipe':[{'name':r[0],'finding':r[1],'sources':list(r[2:])} for r in recipe],
        'remove_for_independent_training':remove,'CAMP_reuse_AST_comparison':common,
        'evidence_files':[ref(EXECUTION/name) for name in evidence_names],
        'reusable_after_separate_pinning':[
            'CAMP full University train content manifest and original os.walk order: actual DAC get_data/pair/shuffle AST equality checked separately.',
            'Existing local original ConvNeXt pretrain file, historical344-state meta proof, identical backbone source; new runtime still strictly loads its own actual DAC backbone.',
            'CAMP v2 scalar observation/count/finite-loss/complete-state/RNG/Unicode-read concepts; source pins, schemas, paths and module ownership must be DAC-specific.',
            'Full-gallery task inventory and original metrics can be shared as immutable data/math; DAC independent checkpoint binding must be new and actual.',
            'Native2-actual-update profile and later owner/exit0/release/shared-lock lifecycle contracts can be independently derived.'
        ],
        'new_DAC_specific_work_required':[
            'New DAC train-only AST adapter from exact official entry; retain original4loss objects and original full singleGPU AMP trainer; never import CAMP trainer.',
            'New normally augmented training loader which omits unused imgaug weather object construction. Preserve get_data/U1652DatasetTrain/get_transforms operators; test AST and later real-pair/seeded operators.',
            'New DAC model factory +402-state strict schema. Author-eval factory only suppresses pretraining and therefore cannot be used unchanged for independent initialization.',
            'Own metadata/runtime dependency proof in stable independent environment, including actual regular augmentation operators. No installation into current frozen environments.',
            'Own full train manifest binding,seed1/2/3 plans,source/environment/metadata SHA,positive optimizer state/profile proof,training status and actual final-checkpoint evaluator.',
            'New serial binding after every currently registered prior queue; reject missing/invalid owner PID/start, incomplete jobs, concurrent GPU,unmeasured profiles. Do not copy old active release.',
            'Resource profile on native24pairs/384/singleGPUAMP must actually pass2realAdamW updates; OOM retains evidence and stops with no batch fallback.',
            'Final independent results must separate full-gallery metrics/3seed stats from author-checkpoint and author-paper scores.'
        ],
        'CAMP_observer_bug_found_and_fixed_in_new_v2':{'report':ref(HERE/'CAMP_OBSERVER_SIGNATURE_COUNTEREXAMPLE.json'),
            'fix_handoff':ref(HERE/'CAMP_V2_HANDOFF.json'),'old_frozen_source_modified':False},
        'future_SUES_distinction':'University-to-SUES10-task transfer after University training is not SUES in-domain reproduction. SUES4height x3seeds would add12independentfits; archivedDSAweight0.3 differs currentrepo0.6; not registered or implemented here.'}
    (HERE/'DAC_INDEPENDENT_GAP_AUDIT.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(HERE/'DAC_INDEPENDENT_GAP_AUDIT.json'),'sha256':sha(HERE/'DAC_INDEPENDENT_GAP_AUDIT.json'),
        'official_source_files_verified':len(all_source),'CAMP_AST_reuse':common}))

if __name__=='__main__':
    main()
