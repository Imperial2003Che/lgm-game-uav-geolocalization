"""CPU fixture only. No real dataset, trained model, or figure is accessed."""
from pathlib import Path
import hashlib,inspect,json,os,sys
os.environ.update(CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg',PYTHONDONTWRITEBYTECODE='1')
P=Path(__file__).resolve().parent
assert Path(sys.prefix).resolve()==Path(r'C:\项目\.venvs\lgm-paper-analysis').resolve()
import numpy as np
import sklearn
import matplotlib
matplotlib.use('Agg')
from sklearn.manifold import TSNE
from threadpoolctl import threadpool_limits
assert 'max_iter' in inspect.signature(TSNE).parameters
rng=np.random.default_rng(127)
fixture=rng.normal(size=(12,5)).astype(np.float32)
with threadpool_limits(limits=1):
 transformed=TSNE(n_components=2,perplexity=3,max_iter=300,init='random',random_state=127,method='exact',n_jobs=1).fit_transform(fixture)
assert transformed.shape==(12,2) and np.isfinite(transformed).all()
assert 'torch' not in sys.modules
result={'status':'passed','python':sys.executable,'numpy':np.__version__,'sklearn':sklearn.__version__,'matplotlib':matplotlib.__version__,
        'tsne_supports_max_iter':True,'fixture_shape':list(fixture.shape),'output_shape':list(transformed.shape),'finite_output':True,
        'fixture_input_sha256':hashlib.sha256(fixture.tobytes()).hexdigest(),'fixture_output_sha256':hashlib.sha256(transformed.tobytes()).hexdigest(),
        'fixture_only':True,'paper_figure_created':False,'torch_imported':False,'cuda_initialized':False,'gpu_executed':False}
(P/'cpu_fixture_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
