"""Strict six-fit completion and original per-query checks, all stdlib."""
import ast
import math
from pathlib import Path
import statistics
import struct
import zipfile
import matched_runtime as r


def audit_config(spec,plan):
    config=r.read(spec.run_dir/'run_config.json');immutable=config['immutable_config']
    if config['run_config_sha256']!=r.canonical(immutable):raise RuntimeError('Invalid configuration hash')
    if immutable['code_sha256']!=r.sha(r.DERIVED) or immutable['dataset']!='university1652' or immutable['seed']!=spec.seed:raise RuntimeError('Wrong immutable source/dataset/seed')
    if immutable['model']['variant']!=spec.variant:raise RuntimeError('Wrong immutable variant')
    if immutable['protocol']!=plan['training_protocol_by_seed'][str(spec.seed)]:raise RuntimeError('Two-view protocol differs from prepared membership')
    if r.canonical(immutable['train_ids'])!=r.ID_SHA or immutable['validation_ids']:raise RuntimeError('Training identities or validation changed')
    steps=immutable['optimization']['steps_per_epoch_actual']
    if steps!=plan['steps_per_epoch'] or immutable['optimization']['sampler_step_count_schedule_sha256']!=r.canonical([steps]*80):raise RuntimeError('Original sampler schedule differs')
    if immutable['image_inventory']['file_count']!=38555 or immutable['image_inventory']['mode']!='content':raise RuntimeError('Training inventory must contain exactly 38555 content-hashed images')
    if config['cli']['workers']!=8 or config['cli']['eval_batch_size']!=128:raise RuntimeError('Reviewed native resource settings changed')
    if immutable['model']['pretrained_initialization']!=plan['settings']['model']['pretrained_initialization']:raise RuntimeError('Pretrained source or bytes changed')
    return config


def hash_artifacts(folder,manifest):
    for name,item in manifest.get('artifacts',{}).items():
        path=(Path(folder)/name).resolve()
        if not path.is_relative_to(Path(folder).resolve()):raise RuntimeError('Artifact path escapes run')
        if not path.is_file() or path.stat().st_size!=item['bytes'] or r.sha(path)!=item['sha256']:raise RuntimeError('Artifact bytes differ: '+str(path))


def origin(spec,plan_path):
    path=spec.run_dir/'training_origin.json'
    value=r.read(path);r.verify_seal(value)
    if value.get('prepared_sha256')!=r.sha(plan_path) or value.get('id')!=spec.identifier or value.get('run_dir')!=str(spec.run_dir):raise RuntimeError('Run does not originate in this prepared independent registry')
    return value


def train_complete(spec,plan,plan_path):
    api=r.original_api();issues=api.training_completion_issues(spec,r.dataset_spec(),r.sha(r.DERIVED))
    if issues:raise RuntimeError('; '.join(issues))
    origin(spec,plan_path);config=audit_config(spec,plan)
    manifest=r.read(spec.run_dir/'run_manifest.json');hash_artifacts(spec.run_dir,manifest)
    history=r.read(spec.run_dir/'history.json')
    for row in history:
        for key in ('train_loss','train_batch_top1','elapsed_seconds'):
            if not math.isfinite(float(row[key])):raise RuntimeError('Nonfinite training history')
    proof_path=spec.run_dir/'checkpoint_proof.json';proof=r.read(proof_path);r.verify_seal(proof)
    if proof['status']!='strict_final_checkpoint_verified' or proof['prepared_sha256']!=r.sha(plan_path) or proof['epoch']!=79 or proof['history_rows']!=80:
        raise RuntimeError('Final checkpoint audit absent or wrong epoch')
    if proof['checkpoint_artifacts']!={name:r.artifact(spec.run_dir/name) for name in ('last.pt','best.pt')}:raise RuntimeError('Checkpoint bytes changed since actual tensor audit')
    if proof['config_sha256']!=config['run_config_sha256']:raise RuntimeError('Checkpoint/config mismatch')
    return {'id':spec.identifier,'manifest':r.artifact(spec.run_dir/'run_manifest.json'),'checkpoint_proof':r.artifact(proof_path),
            'last':r.artifact(spec.run_dir/'last.pt'),'best':r.artifact(spec.run_dir/'best.pt')}


def npy_vector(archive,name):
    """Read original numerical/string vectors without importing NumPy."""
    with archive.open(name+'.npy') as stream:
        if stream.read(6)!=b'\x93NUMPY':raise RuntimeError('Bad NPY magic')
        version=stream.read(2)
        if version not in (b'\x01\x00',b'\x02\x00',b'\x03\x00'):raise RuntimeError('Unsupported NPY version')
        fmt='<H' if version==b'\x01\x00' else '<I';length=struct.unpack(fmt,stream.read(struct.calcsize(fmt)))[0]
        header=ast.literal_eval(stream.read(length).decode('utf-8' if version==b'\x03\x00' else 'latin1').strip())
        shape=header['shape'];dtype=header['descr']
        if len(shape)!=1 or header['fortran_order']:raise RuntimeError('Expected one-dimensional original query evidence')
        if dtype.startswith('<U'):
            width=int(dtype[2:])*4;values=[stream.read(width).decode('utf-32-le').rstrip('\0') for _ in range(shape[0])]
        else:
            formats={'<f4':'f','<f8':'d','<i8':'q','<i4':'i','|b1':'?','|u1':'B'}
            if dtype not in formats:raise RuntimeError('Unsupported numeric query dtype '+str(dtype))
            item='<'+formats[dtype];size=struct.calcsize(item);payload=stream.read()
            if len(payload)!=shape[0]*size:raise RuntimeError('Truncated query evidence')
            values=[row[0] for row in struct.iter_unpack(item,payload)]
        return values


def verify_queries(spec,task,metrics,inventory):
    path=spec.evaluation_dir/'per_query_arrays'/(task+'_per_query.npz')
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:raise RuntimeError('NPZ CRC failure')
        arrays={key:npy_vector(archive,key) for key in ('correct','reciprocal_rank','per_query_official_trapezoid_AP','query_paths','query_labels','top1_gallery_indices','top1_gallery_paths','top1_gallery_labels')}
    qrole,grole=('query_drone','gallery_satellite') if task.endswith('drone_to_satellite') else ('query_satellite','gallery_drone')
    queries=sorted((x for x in inventory if x['role']==qrole),key=lambda x:x['path'])
    gallery=sorted((x for x in inventory if x['role']==grole),key=lambda x:x['path'])
    if arrays['query_paths']!=[x['path'] for x in queries] or arrays['query_labels']!=[x['label'] for x in queries]:raise RuntimeError('Saved query membership/order differs')
    if any(len(values)!=len(queries) for values in arrays.values()):raise RuntimeError('Truncated query vector')
    first=[]
    for i,rr in enumerate(arrays['reciprocal_rank']):
        if not math.isfinite(rr) or not 0<rr<=1:raise RuntimeError('Invalid reciprocal rank')
        rank=round(1/rr)
        if rank<1 or rank>len(gallery) or abs(rr-1/rank)>1e-6:raise RuntimeError('Unrecoverable first-positive rank')
        first.append(rank)
        top=arrays['top1_gallery_indices'][i]
        if not 0<=top<len(gallery) or arrays['top1_gallery_paths'][i]!=gallery[top]['path'] or arrays['top1_gallery_labels'][i]!=gallery[top]['label']:raise RuntimeError('Saved retrieval path/label/index differs')
        if bool(arrays['correct'][i])!=(rank==1) or bool(arrays['correct'][i])!=(queries[i]['label']==gallery[top]['label']):raise RuntimeError('Saved R@1 evidence differs')
    for k in (1,5,10,20):
        if abs(sum(x<=k for x in first)/len(first)-metrics['r_at_'+str(k)])>1e-7:raise RuntimeError('Query-level recall differs from metrics')
    aps=arrays['per_query_official_trapezoid_AP']
    if any(not math.isfinite(x) or not 0<=x<=1 for x in aps) or abs(statistics.fmean(aps)-metrics['official_trapezoid_mAP'])>1e-6:raise RuntimeError('Query AP mean differs')
    return {'task':task,'npz':r.artifact(path),'queries':len(queries),'gallery':len(gallery),
            'recalls_recomputed_from_saved_reciprocal_rank':True,'AP_mean_recomputed':True,
            'limitation':'Original NPZ stores AP and first-positive rank, not all positive ranks; per-query AP formula is inherited unchanged, not independently reranked here.'}


def evaluation_complete(spec,plan,plan_path):
    train_proof=train_complete(spec,plan,plan_path)
    api=r.original_api();issues=api.evaluation_completion_issues(spec,r.dataset_spec())
    if issues:raise RuntimeError('; '.join(issues))
    manifest=r.read(spec.evaluation_dir/'evaluation_manifest.json');hash_artifacts(spec.evaluation_dir,manifest)
    if manifest['checkpoint']['training_run_config_sha256']!=r.read(spec.run_dir/'run_config.json')['run_config_sha256']:raise RuntimeError('Evaluation uses another training configuration')
    metrics=r.read(spec.evaluation_dir/'metrics.json')['results']
    if list(metrics)!=list(r.TASKS):raise RuntimeError('Expected only two original retrieval directions')
    inventory=r.read(r.HERE/'path_inventory.json');proofs=[]
    for name,expected in r.TASKS.items():
        row=metrics[name]
        if (row['queries'],row['gallery'],row['query_identities'],row['gallery_identities'])!=(*expected,701,951):raise RuntimeError('Gallery/query scope differs')
        for key in ('r_at_1','r_at_5','r_at_10','r_at_20','official_trapezoid_mAP'):
            if not math.isfinite(float(row[key])) or not 0<=row[key]<=1:raise RuntimeError('Invalid task metric')
        proofs.append(verify_queries(spec,name,row,inventory))
    return {'id':spec.identifier,'training':train_proof,'evaluation':r.artifact(spec.evaluation_dir/'evaluation_manifest.json'),'per_query':proofs},metrics
