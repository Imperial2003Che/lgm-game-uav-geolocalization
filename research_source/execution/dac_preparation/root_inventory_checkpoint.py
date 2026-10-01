"""Metadata-only inspection of the verified DAC University release member."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
os.environ['HF_HUB_OFFLINE']='1'
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib,json,sys,traceback

HERE=Path(__file__).resolve().parent
CHECKPOINT=HERE.parent/'latest_author_checkpoints/DAC_University_author_checkpoint.pth'
EXPECTED='404bdc23cc5b490393cb4c51743c26ce0fdc4e5516eeed375520bead9e567fbd'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    if sha(CHECKPOINT)!=EXPECTED:raise RuntimeError('Verified DAC checkpoint bytes changed')
    import torch
    torch.set_num_threads(1)
    state=torch.load(CHECKPOINT,map_location='meta',mmap=True,weights_only=True)
    if not isinstance(state,dict) or not all(isinstance(k,str) and isinstance(v,torch.Tensor) for k,v in state.items()):
        raise RuntimeError('Not a plain string-to-tensor dictionary; inspect container without unsafe loading')
    rows=[dict(key=k,shape=list(v.shape),dtype=str(v.dtype),device=str(v.device),numel=v.numel()) for k,v in state.items()]
    if any(r['device']!='meta' for r in rows) or torch.cuda.is_initialized():raise RuntimeError('Unexpected tensor allocation or CUDA initialization')
    if sha(CHECKPOINT)!=EXPECTED:raise RuntimeError('Checkpoint changed during inspection')
    report=dict(status='tensor_metadata_inspected_not_model_evaluated',created_utc=datetime.now(timezone.utc).isoformat(),
        checkpoint=str(CHECKPOINT),checkpoint_sha256=EXPECTED,checkpoint_bytes=CHECKPOINT.stat().st_size,
        python=sys.executable,torch_version=torch.__version__,cuda_initialized=False,
        loader=dict(weights_only=True,map_location='meta',mmap=True),
        code_sha256=sha(Path(__file__)),download_provenance_sha256=sha(HERE.parent/'latest_author_checkpoints/DAC_University_download.json'),
        tensor_count=len(rows),total_stored_numel=sum(r['numel'] for r in rows),dtype_counts=dict(Counter(r['dtype'] for r in rows)),tensors=rows)
    target=HERE/'author_checkpoint_metadata.json'
    if target.exists():raise FileExistsError('Preserve earlier checkpoint inventory')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='tensors'},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except Exception:
        (HERE/('meta_failure_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.txt')).write_text(traceback.format_exc(),encoding='utf-8')
        raise
