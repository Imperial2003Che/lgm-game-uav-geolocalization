"""Freeze this preparation after review; does not register or execute anything."""
import ast
import json
import sys
import dac6_contracts as d

def main():
    manifest=d.HERE/'PREPARATION_MANIFEST.json'
    d.require(not manifest.exists(),'Preparation already sealed; do not overwrite')
    d.require(not (d.HERE/'runtime').exists(),'Unexpected active runtime during preparation seal')
    report=d.c.read(d.HERE/'EXECUTION_VALIDATION.json')
    d.require(report['fixture_only'] is True and report['scientific_imports'] is False and report['gpu_execution'] is False,'Validation crossed preparation boundary')
    d.require(report['tests_passed']==len(report['tests']) and all(x['passed'] for x in report['tests']),'CPU fixture check failed')
    for path in d.HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'))
        d.require(report['source_files_sha256'].get(path.name)==d.sha(path),'Source changed after recorded CPU validation')
    d.spec_bound(d.HERE/'execution_spec.json',report['spec_sha256'])
    paths=[p for p in d.HERE.iterdir() if p.is_file()]
    rows=[{'path':p.name,'sha256':d.sha(p),'bytes':p.stat().st_size} for p in sorted(paths)]
    d.c.write(manifest,{'schema':'dac-six-stage-execution-preparation.v2','status':'prepared_not_registered',
        'prepared_utc':d.c.utc(),'control_manifest_sha256':d.CONTROL_SHA,'input_manifest_sha256':d.INPUT_SHA,
        'spec_sha256':report['spec_sha256'],'files':rows,'payload_files':len(rows),
        'payload_bytes':sum(x['bytes'] for x in rows),'scientific_imports':False,'gpu_execution':False,
        'source_review_scope':'See HANDOFF.md; no real resource profile or training has been executed.'})
    d.own_manifest()
    print(json.dumps({'manifest_sha256':d.sha(manifest),'payload_files':len(rows),'payload_bytes':sum(x['bytes'] for x in rows)}))

if __name__=='__main__':main()
