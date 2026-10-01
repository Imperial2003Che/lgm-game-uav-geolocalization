"""Bind the later producer delivery without rerunning the completed focused checks."""
from pathlib import Path
import json,hashlib,datetime
HERE=Path(__file__).parent
PROD=HERE.parent/'t6_new_boot_contract_derivation_20260930_0405'
def b(path):
    path=Path(path);assert path.stat().st_size<500000
    data=path.read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(name,obj):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as f: f.write(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    return b(HERE/name)
review_b=b(HERE/'CONTRACT_SOURCE_REVIEW.json')
assert review_b['sha256']=='26280101e6ff266a5cc69be4564a98026743543d915221022db0b8488b7a19b0'
delivery_b=b(PROD/'DELIVERY.json')
assert delivery_b['sha256']=='3bbea8250916edd9cba8efcc811c0c923b5280c935be821bedb2bffab9715631'
review=load(HERE/'CONTRACT_SOURCE_REVIEW.json');delivery=load(PROD/'DELIVERY.json')
bound={x['path']:x for x in review['bindings']}
sealer_b=b(PROD/'seal_delivery.py')
assert sealer_b['sha256']=='71090b2b9c6f14e7fdd1846a9e4dc3e1a615d9f2fdb8b2ef03a6874cb29ddd2c'
assert len(delivery['artifacts'])==12
for record in delivery['artifacts']:
    assert record==(sealer_b if record['path']==sealer_b['path'] else bound[record['path']])
assert delivery['execution_released'] is False
add=write('PRODUCER_DELIVERY_ADDENDUM.json',{
    'schema':'independent-producer-delivery-binding-addendum.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'contract_review':review_b,'producer_delivery':delivery_b,'producer_sealer_source':sealer_b,'source':b(__file__),
    'review_method':'Independent AI full text read of newly arrived producer DELIVERY and sealer. Eleven artifact binding records matched the independently completed source-review bindings by value; only new sealer/delivery bytes read for this additional binding step.',
    'producer_artifact_count':12,'eleven_prior_binding_records_matched':True,'new_sealer_bytes_checked':True,
    'original_56_checks_rerun':False,'old_suites_or_producer_executed':False,'execution_released':False,
    'limitations':['Producer tool-return exit0 is its reported offline derivation completion; this addendum does not claim independently held process handles or a new runtime/Windows execution.','The original source review remains unchanged and source-only.']})
files=['review_observation.py','OBSERVATION_REVIEW.json','review_contract.py','CONTRACT_SOURCE_REVIEW.json','seal_review.py','PRODUCER_DELIVERY_ADDENDUM.json']
result=write('DELIVERY.json',{'schema':'independent-boot-and-source-contract-review-delivery.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent saved boot observation review plus separately derived T6 source contract delta review; AI static and small-file byte/value checks only.','artifacts':[b(HERE/x) for x in files],'producer_delivery':delivery_b,'execution_released':False,'cleanup_authorized':False,'scientific_result_adopted':False,'observation_checks':42,'contract_delta_checks':56,'limits':['Two focused review scripts executed once each; no existing suite repeated. Later producer delivery bound separately without rerunning those checks.','No independent CIM, science, native probe, COM, recovery, lock acquisition, release, intent, source/state mutation, weights/cache/image/large ZIP access.']})
print(json.dumps({'addendum':add,'delivery':result},ensure_ascii=False))
