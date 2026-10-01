"""Derive DAC's evaluator from a specifically confirmed CAMP runner/test pair.

This is a source-only transformation. It never imports scientific libraries or
executes the evaluator, and it preserves the exact source and unified diff.
"""
import argparse
import ast
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path

P=Path(__file__).resolve().parent
C=P.parent/'camp_preparation'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def replace_once(text,before,after):
    if text.count(before)!=1:raise RuntimeError('Unexpected source context: '+before[:100])
    return text.replace(before,after)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner-sha',required=True)
    parser.add_argument('--test-sha',required=True)
    args=parser.parse_args()
    source=C/'run_camp_author_evaluation.py';test=C/'test_camp_cpu.py'
    assert sha(source)==args.runner_sha and sha(test)==args.test_sha
    out=P/'run_dac_author_evaluation.py';out_test=P/'test_dac_cpu.py'
    if out.exists() or out_test.exists():raise RuntimeError('Derived DAC files already exist; inspect before replacement')
    snapshot=P/'evaluator_derivation';snapshot.mkdir(exist_ok=True)
    for path in (source,test):
        (snapshot/path.name).write_bytes(path.read_bytes())
    original=source.read_text(encoding='utf-8')
    text=original.replace('CAMP','DAC').replace('camp','dac')
    text=text.replace('Mabel0403__DAC__b04a9c856711','SummerpanKing__DAC__5612a79c3928')
    text=text.replace('6bc5b21310c9698588567a52f54c423e9e8f9c7a4473e85e5e462fea1898869b','404bdc23cc5b490393cb4c51743c26ce0fdc4e5516eeed375520bead9e567fbd')
    text=text.replace('365745130','386193190')
    text=text.replace(r'C:\项目\.venvs\lgm-dac\Scripts\python.exe',r'C:\项目\.venvs\lgm-camp\Scripts\python.exe')
    before="""    if meta.get('status')!='strict_meta_compatibility_passed_not_evaluated' or meta.get('checkpoint_sha256')!=CHECKPOINT_SHA or meta.get('adapter_sha256')!=sha(HERE/'dac_model.py'):
        raise RuntimeError('Strict metadata compatibility proof is absent or stale')
    if meta['proof'].get('tensor_count')!=394 or meta['proof'].get('missing_keys') or meta['proof'].get('unexpected_keys') or meta['proof'].get('shape_or_dtype_mismatches'):
        raise RuntimeError('Author checkpoint schema proof differs')"""
    after="""    if meta.get('status')!='strict_meta_compatible_no_schema_adaptation' or meta.get('checkpoint_sha256_after')!=CHECKPOINT_SHA or meta.get('factory_sha256')!=sha(HERE/'dac_model.py'):
        raise RuntimeError('Strict DAC metadata compatibility proof is absent or stale')
    proof=meta.get('schema_comparison',{})
    if proof.get('tensor_count')!=402 or proof.get('schema_adaptation')!='none' or proof.get('missing_keys') or proof.get('unexpected_keys') or proof.get('shape_or_dtype_mismatches'):
        raise RuntimeError('DAC author checkpoint schema proof differs')"""
    text=replace_once(text,before,after)
    before="""    if Path(semantic.get('python','')).resolve()!=args.python.resolve() or semantic.get('validation_transform',{}).get('status')!='passed' or semantic.get('pos_scale_real_official_forward_fixture',{}).get('status')!='passed':
        raise RuntimeError('Independent DAC runtime needs both transform and official-forward CPU fixtures')"""
    after="""    if Path(semantic.get('python','')).resolve()!=args.python.resolve() or semantic.get('validation_transform',{}).get('status')!='passed' or semantic.get('strict_DAC_schema',{}).get('status')!='passed':
        raise RuntimeError('DAC runtime needs official transform parity and its own strict 402-tensor schema proof')"""
    text=replace_once(text,before,after)
    before="""                               'checkpoint_schema':'394 tensors matched strictly after explicit unused-pos_scale auxiliary adaptation; current original architecture has 395',
                               'absent_auxiliary_constant':'pos_scale=0.6 is the current official default, not an inferred author learned value; does not affect selected GAP descriptor',"""
    after="""                               'checkpoint_schema':'402 tensors match the unmodified official DAC model strictly; no schema adaptation or auxiliary replacement',
                               'model_config':{'views':2,'nclasses':701,'block':2,'triplet_loss':0.3,'resnet':False},"""
    text=replace_once(text,before,after)
    before="""    from dac_model import load_author_model,no_network
    torch.set_num_threads(1);cv2.setNumThreads(1)
    model,loading=load_author_model(CHECKPOINT,SOURCE)"""
    after="""    from dac_model import build_dac_model,validate_checkpoint_state,no_network
    torch.set_num_threads(1);cv2.setNumThreads(1)
    with no_network():
        model=build_dac_model(SOURCE,device='meta')
        author_state=torch.load(CHECKPOINT,map_location='cpu',weights_only=True,mmap=True)
        loading=validate_checkpoint_state(model,author_state)
        incompatible=model.load_state_dict(author_state,strict=True,assign=True)
        if incompatible.missing_keys or incompatible.unexpected_keys:
            raise RuntimeError('Strict DAC checkpoint assignment returned incompatible keys')
        if any(t.device.type!='cpu' for t in model.state_dict().values()):
            raise RuntimeError('DAC model state did not materialize completely on CPU')
        loading['load_state_dict']={'strict':True,'assign':True,'map_location':'cpu','weights_only':True,'mmap':True}
        del author_state"""
    text=replace_once(text,before,after)
    text=replace_once(text,"'source_training_dataset':'University-1652; author-provided checkpoint; training/selection details not inferred from filename',",
                      "'method':'DAC','source_training_dataset':'University-1652; one-epoch final author checkpoint from the official archive; no local training',")
    text=replace_once(text,"score.update(result_type='author-checkpoint re-evaluation',task_type=item['task_type'],source_training_dataset='University-1652',",
                      "score.update(method='DAC',result_type='author-checkpoint re-evaluation',task_type=item['task_type'],source_training_dataset='University-1652',")
    text=replace_once(text,"snapshot['environment_type']='locally adapted evaluation environment; official repository provides no dependency lock'",
                      "snapshot['environment_type']='shared locked lgm-camp adaptation environment for serial CAMP/DAC evaluation; official repositories provide no dependency lock'")
    text=replace_once(text,"'adapter_sources':{p.name:artifact(p) for p in [Path(__file__),HERE/'dac_model.py']}",
                      "'adapter_sources':{p.name:artifact(p) for p in [Path(__file__),HERE/'dac_model.py']},\n            'DAC_model_source_manifest':artifact(HERE/'SOURCE_SHA256.json'),\n            'derivation_record':artifact(HERE/'evaluator_derivation.json')")
    ast.parse(text)
    test_original=test.read_text(encoding='utf-8')
    check=test_original.replace('CAMP','DAC').replace('camp','dac')
    check=replace_once(check,"parser.add_argument('--with-torch-stub',action='store_true')\n",'')
    check=check.replace('(args.with_torch_stub or args.with_transform)','args.with_transform')
    start=check.index('if args.with_torch_stub:\n')
    end=check.index('if args.with_transform:\n',start)
    check=check[:start]+check[end:]
    check=check.replace('not args.with_transform and not args.with_torch_stub','not args.with_transform')
    check=check.replace('args.with_transform or args.with_torch_stub','args.with_transform')
    marker="if args.full_path_inventory:\n"
    addition="""schema=r.load(HERE/'strict_meta_compatibility.json')
assert schema['status']=='strict_meta_compatible_no_schema_adaptation'
assert schema['schema_comparison']['tensor_count']==402
assert schema['schema_comparison']['schema_adaptation']=='none'
assert schema['factory_sha256']==r.sha(HERE/'dac_model.py')
report['strict_DAC_schema']={'status':'passed','tensor_count':402,'schema_adaptation':'none',
                             'proof_sha256':r.sha(HERE/'strict_meta_compatibility.json'),
                             'scope':'Existing independent meta proof; no checkpoint or model loaded by this semantic check'}

"""
    check=replace_once(check,marker,addition+marker)
    ast.parse(check)
    assert 'pos_scale' not in text and 'pos_scale' not in check and '394' not in text
    assert 'camp-author' not in text and 'camp_model' not in text
    out.write_text(text,encoding='utf-8');out_test.write_text(check,encoding='utf-8')
    record={'created_utc':datetime.now(timezone.utc).isoformat(),'status':'derived_for_DAC_CPU_validation',
        'generator_path':str(Path(__file__).resolve()),'generator_sha256':sha(__file__),
        'upstream_runner':{'path':str(source),'sha256':sha(source),'preserved_copy':str(snapshot/source.name)},
        'upstream_test':{'path':str(test),'sha256':sha(test),'preserved_copy':str(snapshot/test.name)},
        'derived_runner':{'path':str(out),'sha256':sha(out)},'derived_test':{'path':str(out_test),'sha256':sha(out_test)},
        'changes':['DAC source/checkpoint/schema/release names','exact 402-key DAC proof without auxiliary adaptation',
                   'meta construction then complete CPU weights_only assignment inside released encode stage',
                   'DAC method labels and University-trained SUES transfer scope','reuse the shared locked lgm-camp environment',
                   'remove CAMP-specific pos_scale forward fixture; require existing exact DAC meta proof and official validation-transform parity'],
        'CAMP_files_modified':False,'GPU_executed':False}
    (P/'evaluator_derivation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for source_text,result,name in [(original,text,'runner.patch'),(test_original,check,'semantic_test.patch')]:
        (snapshot/name).write_text(''.join(difflib.unified_diff(source_text.splitlines(True),result.splitlines(True),fromfile='confirmed_CAMP_source',tofile='derived_DAC_source')),encoding='utf-8')
    pins=json.loads((P/'SOURCE_SHA256.json').read_text(encoding='utf-8'))
    src=Path(pins['repository'])
    files={relative:{'bytes':(src/relative).stat().st_size,'sha256':expected} for relative,expected in pins['files'].items()}
    for relative in ['.gitignore','sample4geo/dataset/SUES-200/indexs.yaml']:
        if (src/relative).is_file():files[relative]={'bytes':(src/relative).stat().st_size,'sha256':sha(src/relative)}
    (P/'source_pins.json').write_text(json.dumps({'source_commit':pins['commit'],'repository':'https://github.com/SummerpanKing/DAC','official_source_files':files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
