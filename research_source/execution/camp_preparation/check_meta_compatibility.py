"""Validate full official CAMP architecture against author tensor metadata only."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['HF_HUB_OFFLINE']='1'
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,sys,traceback

HERE=Path(__file__).resolve().parent
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    import torch
    from camp_model import build_camp_model,validate_checkpoint_state,SOURCE_ROOT
    torch.set_num_threads(1)
    model=build_camp_model(device='meta')
    checkpoint=HERE.parent/'latest_author_checkpoints/CAMP_University_author_checkpoint.pth'
    original=sha(checkpoint)
    assert original=='6bc5b21310c9698588567a52f54c423e9e8f9c7a4473e85e5e462fea1898869b'
    state=torch.load(checkpoint,map_location='meta',weights_only=True,mmap=True)
    proof=validate_checkpoint_state(model,state)
    assert all(v.device.type=='meta' for v in model.state_dict().values())
    assert all(v.device.type=='meta' for v in state.values())
    assert not torch.cuda.is_initialized()
    assert sha(checkpoint)==original
    report=dict(status='strict_meta_compatibility_passed_not_evaluated',created_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.executable,torch_version=torch.__version__,cuda_initialized=False,
        checkpoint_sha256=original,official_source_root=str(SOURCE_ROOT),
        adapter_sha256=sha(HERE/'camp_model.py'),check_code_sha256=sha(Path(__file__)),proof=proof)
    target=HERE/'strict_meta_compatibility.json'
    if target.exists(): raise FileExistsError('Preserve existing check')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    try: main()
    except Exception:
        target=HERE/('meta_failure_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.txt')
        target.write_text(traceback.format_exc(),encoding='utf-8')
        raise
