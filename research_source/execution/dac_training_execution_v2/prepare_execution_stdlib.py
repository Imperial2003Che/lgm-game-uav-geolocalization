"""Create a non-active fixed six-stage specification; never creates a release."""
import json
from pathlib import Path
import sys
import dac6_contracts as d

def main():
    d.require(not (d.HERE/'PREPARATION_MANIFEST.json').exists(),'Executor is already sealed; do not overwrite')
    inputs=d.pin_package(d.INPUTS,d.INPUT_SHA);jobs=[]
    for item in inputs['seeds']:
        plan=d.c.Bound.load(item['plan_path'],item['plan_sha256'])
        for stage in ('profile','train'):
            config=plan.value
            jobs.append({'id':f"seed_{item['seed']}_{stage}",'seed':item['seed'],'stage':stage,
                'plan_path':str(plan.path),'plan_sha256':plan.sha256,
                'output_directory':config['profile_directory' if stage=='profile' else 'output_directory'],
                'control_receipt_path':str(Path(config['profile_receipt_directory' if stage=='profile' else 'training_receipt_directory'])/'lifecycle.json')})
    spec={'schema':'dac-six-stage-execution-spec.v2','status':'prepared_not_registered',
        'control_manifest_sha256':d.CONTROL_SHA,'input_manifest_sha256':d.INPUT_SHA,
        'process_environment':d.c.PROCESS_ENV,'jobs':jobs,
        'status_path':str(d.HERE/'runtime/status.json'),'completion_path':str(d.HERE/'runtime/completion_manifest.json'),
        'recovery_policy':'Preserve existing partial/failed/completed runs; no automatic rerun or resume.',
        'resource_policy':'Native 24 pairs, 384 pixels, AMP; two actual AdamW updates; never lower batch or reuse profile state.',
        'future_values_not_created':['root serial release','actual profile hashes','actual weights','process receipts','runtime status']}
    path=d.HERE/'execution_spec.json';d.c.write(path,spec);d.spec_bound(path,d.sha(path))
    d.require(not (d.HERE/'runtime').exists(),'Preparation created active runtime state')
    print(json.dumps({'status':'prepared_not_registered','spec_path':str(path),'spec_sha256':d.sha(path),
        'scientific_modules_loaded':[x for x in sys.modules if x.split('.')[0] in {'torch','numpy','PIL','scipy','timm','cv2'}]},ensure_ascii=False))

if __name__=='__main__':main()
