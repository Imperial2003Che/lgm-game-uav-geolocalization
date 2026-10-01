"""Verify source/audit provenance and downloaded checkpoint bytes without torch."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import zlib

P=Path(__file__).resolve().parent
E=P.parent

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()

def main():
    record_path=E/'latest_author_checkpoints/DAC_University_download.json'
    record=json.loads(record_path.read_text(encoding='utf-8'))
    assert record['status']=='completed_verified_not_loaded'
    path=Path(record['target_path'])
    assert path.stat().st_size==record['member']['uncompressed_bytes']==record['checkpoint_bytes']==386193190
    assert sha(path)==record['checkpoint_sha256']
    crc=0
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):
            crc=zlib.crc32(block,crc)
    assert f'{crc&0xffffffff:08x}'==record['crc32_hex']==record['member']['crc32_hex']=='86b42450'
    offset=record['compressed_data_start']
    for ran in record['ranges']:
        assert ran['status']=='completed' and ran['start']==offset
        assert ran['bytes_read']==ran['end']-ran['start']+1
        assert ran['content_range']==f"bytes {ran['start']}-{ran['end']}/{record['archive_bytes']}"
        assert ran['last_modified']==record['remote_identity']['last_modified']
        offset=ran['end']+1
    assert offset==record['compressed_data_end']+1
    assert sum(x['bytes_read'] for x in record['ranges'])==record['checkpoint_bytes_transferred']==358152154
    assert Path(record['compressed_part_path']).stat().st_size==record['checkpoint_bytes_transferred']
    assert sha(record['compressed_part_path'])==record['compressed_member_sha256']
    assert sha(record['extractor_path'])==record['extractor_sha256']
    assert sha(record['central_directory_metadata_path'])==record['central_directory_metadata_sha256']
    source=json.loads((P/'SOURCE_SHA256.json').read_text(encoding='utf-8'))
    for relative,expected in source['files'].items():
        assert sha(Path(source['repository'])/relative)==expected
    correction=json.loads((P/'RECIPE_AUDIT_CORRECTION.json').read_text(encoding='utf-8'))
    for current,meta in correction['originals'].items():
        assert sha(meta['backup_path'])==meta['sha256']==meta['backup_sha256']
        assert sha(current)==correction['updated'][current]
    audit=json.loads((E/'latest_baseline_recipe_audit.json').read_text(encoding='utf-8'))
    old=json.loads(Path(correction['originals'][str(E/'latest_baseline_recipe_audit.json')]['backup_path']).read_text(encoding='utf-8'))
    camp_old=old['recipes']['CAMP'];camp_new=audit['recipes']['CAMP']
    assert camp_old.pop('launch_policy').split(' DAC:')[0]==camp_new.pop('launch_policy').split(' DAC:')[0]
    assert camp_old==camp_new
    assert audit['recipes']['DAC']['fields']['total_epochs']['value']==1
    provenance=audit['dac_correction_provenance']
    assert sha(provenance['plan_path'])==provenance['plan_sha256']
    handoff={
        'status':'verified_checkpoint_bytes_and_source_recipe_ready_for_restricted_metadata_review',
        'verified_utc':datetime.now(timezone.utc).isoformat(),
        'checkpoint_path':str(path),'checkpoint_bytes':path.stat().st_size,'checkpoint_sha256':record['checkpoint_sha256'],'checkpoint_crc32':record['crc32_hex'],
        'official_member':record['member']['name'],'source_url':record['url'],'official_readme_url':record['official_readme_url'],
        'zip_directory_path':record['central_directory_metadata_path'],'zip_directory_sha256':record['central_directory_metadata_sha256'],
        'remote_etag':record['remote_identity_final']['etag'],'remote_last_modified':record['remote_identity_final']['last_modified'],
        'download_record_path':str(record_path),'download_record_sha256':sha(record_path),
        'range_count':len(record['ranges']),'member_transfer_bytes':record['checkpoint_bytes_transferred'],'download_metadata_transfer_bytes':record['metadata_bytes_transferred'],
        'earlier_directory_metadata_transfer_bytes':2349,'earlier_recipe_metadata_transfer_bytes':26022,
        'compressed_member_retained_path':record['compressed_part_path'],'compressed_member_sha256':record['compressed_member_sha256'],
        'extractor_path':record['extractor_path'],'extractor_sha256':record['extractor_sha256'],
        'verifier_path':str(Path(__file__).resolve()),'verifier_sha256':sha(__file__),
        'recipe_plan_path':str(P/'DAC_RECIPE_PLAN.json'),'recipe_plan_sha256':sha(P/'DAC_RECIPE_PLAN.json'),
        'recipe_report_path':str(P/'DAC_RECIPE_PLAN.md'),'recipe_report_sha256':sha(P/'DAC_RECIPE_PLAN.md'),
        'source_file_count':len(source['files']),'all_source_hashes_match':True,'CAMP_scientific_fields_unchanged':True,
        'checkpoint_loaded':False,'torch_imported':'torch' in sys.modules,'gpu_executed':False,
        'next_action':'Root performs restricted checkpoint metadata/key inspection. Adapter, independent runtime and GPU execution registration remain separate next steps.',
        'no_other_model_members_downloaded':True,
    }
    assert handoff['torch_imported'] is False
    output=P/'CHECKPOINT_HANDOFF.json'
    output.write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':handoff['status'],'checkpoint_sha256':handoff['checkpoint_sha256'],'range_count':handoff['range_count'],'source_files_verified':handoff['source_file_count'],'torch_imported':False},indent=2))

if __name__=='__main__':
    main()
