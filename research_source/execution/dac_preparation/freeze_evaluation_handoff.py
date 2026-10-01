"""Standard-library final provenance check and DAC serial-queue handoff."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
sys.dont_write_bytecode=True
import run_dac_author_evaluation as r


def main():
    prepared=P/'preparations/20260914T045232800767Z/manifest.json'
    manifest=r.load(prepared);r.verify_seal(manifest)
    assert manifest['status']=='prepared_not_evaluated' and manifest['schema']==r.SCHEMA
    assert manifest['method']=='DAC'
    assert manifest['sources']==r.verify_sources()
    assert manifest['runtime']==r.runtime_snapshot(Path(manifest['python']))
    assert len(manifest['runtime']['distributions'])==70
    for key in ('inventory','tasks','semantic_cpu_validation'):
        assert r.artifact(manifest[key]['path'])==manifest[key]
    inventory=r.load(manifest['inventory']['path']);tasks=r.load(manifest['tasks']['path'])
    assert len(inventory)==131062 and len(tasks)==10
    proof=r.load(manifest['semantic_cpu_validation']['path'])
    assert proof['full_path_inventory']['stat_inventory_sha256']==r.canonical(inventory)
    assert proof['full_path_inventory']['task_manifest_sha256']==r.canonical(tasks)
    assert proof['code_sha256']==r.sha(Path(r.__file__))
    assert proof['dac_model_sha256']==r.sha(P/'dac_model.py')
    assert proof['validation_transform']['adapter_equals_official_byte_for_byte'] is True
    assert proof['validation_transform']['cuda_initialized'] is False
    assert proof['strict_DAC_schema']['tensor_count']==402
    assert proof['strict_DAC_schema']['schema_adaptation']=='none'
    assert proof['environment_controls']['CUDA_VISIBLE_DEVICES']==''
    assert [t['distractor_identity_count'] for t in tasks]==[250,250]+[120]*8
    upstream=r.load(P/'evaluator_derivation.json')
    assert r.sha(upstream['upstream_runner']['path'])==upstream['upstream_runner']['sha256']
    assert r.sha(upstream['upstream_test']['path'])==upstream['upstream_test']['sha256']
    assert r.sha(upstream['upstream_runner']['preserved_copy'])==upstream['upstream_runner']['sha256']
    assert r.sha(upstream['upstream_test']['preserved_copy'])==upstream['upstream_test']['sha256']
    assert r.sha(upstream['derived_runner']['path'])==upstream['derived_runner']['sha256']
    assert r.sha(upstream['derived_test']['path'])==upstream['derived_test']['sha256']
    assert not any(name in sys.modules for name in ('torch','numpy','cv2','albumentations'))
    pinned={str(prepared):r.sha(prepared)}
    for relative,item in r.load(P/'source_pins.json')['official_source_files'].items():
        pinned[str((r.SOURCE/relative).resolve())]=item['sha256']
    for path in [Path(r.__file__),P/'dac_model.py',P/'source_pins.json',P/'SOURCE_SHA256.json',P/'evaluator_derivation.json',
                 P/'strict_meta_compatibility.json',P/'cpu_semantic_validation.json',P/'test_dac_cpu.py',
                 r.CORE,r.SPLIT,r.CHECKPOINT,r.EXECUTION/'latest_author_checkpoints/DAC_University_download.json',
                 Path(manifest['inventory']['path']),Path(manifest['tasks']['path'])]:
        pinned[str(path.resolve())]=r.sha(path)
    release_path=prepared.parent/'release.json'
    result={'status':'prepared_for_root_registration_not_executed','created_utc':datetime.now(timezone.utc).isoformat(),
        'id':'dac_author_checkpoint_full_gallery_10tasks',
        'command':[manifest['python'],'-B',str(Path(r.__file__).resolve()),'--stage','evaluate','--prepared',str(prepared),'--release-file',str(release_path)],
        'cwd':str(P),'source_sha256':pinned,
        'manifest_path':str(prepared),'manifest_sha256':r.sha(prepared),'manifest_payload_sha256':manifest['payload_sha256'],
        'release_schema':'dac-author-checkpoint-release.v1','release_file_path':str(release_path),
        'release_template':r.artifact(prepared.parent/'release_template.json'),
        'runtime':{'python':manifest['python'],'package_count':70,'fingerprint':r.canonical(manifest['runtime']),
                   'shared_with_CAMP':True,'packages_modified_by_this_task':False},
        'settings':manifest['settings'],
        'task_counts':[{k:t[k] for k in ('name','task_type','query_count','gallery_count','distractor_identity_count')} for t in tasks],
        'method':'DAC','result_type':'author-checkpoint re-evaluation',
        'scientific_scope':'Fixed University-trained author final checkpoint; U1652 in-domain and four-height SUES cross-dataset transfer. No independent training or target-test model selection.',
        'release_requirements':'All original primary, seven-stage pipeline and four-extension queues complete and processes exit; release binds this exact manifest and original extension plan; shared latest_baseline_gpu.lock acquired.',
        'evaluation_environment_note':'Do not inherit CUDA_VISIBLE_DEVICES empty from CPU checks into the authorized CUDA evaluation process. Evaluation enforces one-thread BLAS/OMP/OpenCV/Torch CPU pools.',
        'complete_npz_evidence':'All positive ranks, query/gallery IDs and paths, top1 records, both per-query AP definitions and recalls; validated again from saved NPZ.',
        'final_checker':r.artifact(Path(__file__)),'scientific_imports_in_final_checker':[],'GPU_executed':False}
    r.save(P/'queue_handoff.json',result)
    r.save(P/'FINAL_EVALUATION_FREEZE.json',{'status':'CPU_validated_and_prepared_no_evaluation',
        'created_utc':result['created_utc'],'handoff':r.artifact(P/'queue_handoff.json'),
        'prepared_manifest':r.artifact(prepared),'source_file_count':len(pinned),
        'source_sha256':pinned,'CAMP_files_unchanged':True,'scientific_imports':[]})
    print(json.dumps({k:result[k] for k in ('status','manifest_path','manifest_sha256','release_schema')},ensure_ascii=True,indent=2))


if __name__=='__main__':main()
