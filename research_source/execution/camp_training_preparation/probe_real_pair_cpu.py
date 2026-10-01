"""One genuine University training pair, official transforms, CPU only."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['NO_ALBUMENTATIONS_UPDATE'] = '1'
import argparse
import ast
from contextlib import nullcontext
import importlib.abc
import json
from pathlib import Path
import random
import sys
import tempfile
import traceback
from camp_train_runtime import HERE, TrainRun, no_network, sha_file, write_json

class NoModelImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith('sample4geo.hand_convnext') or fullname == 'sample4geo.model':
            raise RuntimeError('The CPU data probe must not import or construct a model')
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-adapter-reader', action='store_true')
    args = parser.parse_args()
    label = 'adapter_reader' if args.use_adapter_reader else 'official_reader'
    report_path = HERE / f'REAL_PAIR_CPU_{label}.json'
    report = {'status':'starting','device':'cpu','gpu_execution':False,'model_imported':False,
              'source_entry':'train_university_train_only.py','source_entry_sha256':sha_file(HERE/'train_university_train_only.py'),
              'adapter_reader':args.use_adapter_reader, 'python':sys.executable,
              'sys_prefix':sys.prefix, 'sys_executable':sys.executable,
              'CUDA_VISIBLE_DEVICES':os.environ['CUDA_VISIBLE_DEVICES']}
    sys.dont_write_bytecode=True
    sys.meta_path.insert(0,NoModelImport())
    try:
        pin=json.loads((HERE/'SOURCE_PIN.json').read_text(encoding='utf-8'))
        sys.path.insert(0,pin['source_directory'])
        with no_network():
            import prepare_or_train
            report['runtime_environment']=prepare_or_train.runtime_environment(HERE)
            import torch
            torch.set_num_threads(1)
            torch.random.default_generator.manual_seed(1)
            import numpy as np
            import cv2
            random.seed(1)
            np.random.seed(1)
            from sample4geo.dataset.university import U1652DatasetTrain,get_transforms
            # Execute imports only, not Configuration or __main__; no model branch.
            parsed=ast.parse((HERE/'train_university_train_only.py').read_text(encoding='utf-8'))
            imports=ast.Module(body=[n for n in parsed.body if isinstance(n,(ast.Import,ast.ImportFrom))],type_ignores=[])
            exec(compile(imports,'<official-training-imports-only>','exec'),{})
            report['all_training_imports_passed']=True
            root=Path(r'C:\项目\IMTMN\datasets\University-1652\train')
            _,sat_transform,drone_transform=get_transforms((384,384),mean=(0.485,0.456,0.406),std=(0.229,0.224,0.225))
            dataset=U1652DatasetTrain(str(root/'satellite'),str(root/'drone'),
                transforms_query=sat_transform,transforms_gallery=drone_transform,prob_flip=0.5,shuffle_batch_size=24)
            sample=dataset.samples[0]
            report['identity_count']=len(dataset.ids)
            report['pair_count']=len(dataset.pairs)
            report['pair']={'id':sample[0],'label':sample[1],'satellite':sample[2],'drone':sample[3]}
            report['input_sha256']={view:sha_file(path) for view,path in [('satellite',sample[2]),('drone',sample[3])]}
            report['original_cv2_imread']={view:cv2.imread(path) is not None for view,path in [('satellite',sample[2]),('drone',sample[3])]}
            if args.use_adapter_reader:
                decode_checks={}
                with tempfile.TemporaryDirectory(prefix='camp_ascii_decode_') as temporary:
                    assert Path(temporary).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
                    for view,filename in [('satellite',sample[2]),('drone',sample[3])]:
                        encoded=Path(filename).read_bytes()
                        ascii_file=Path(temporary)/(view+Path(filename).suffix)
                        ascii_file.write_bytes(encoded)
                        ascii_image=cv2.imread(str(ascii_file))
                        decoded=cv2.imdecode(np.frombuffer(encoded,dtype=np.uint8),cv2.IMREAD_COLOR)
                        identical=ascii_image is not None and np.array_equal(ascii_image,decoded)
                        assert identical
                        decode_checks[view]={'encoded_sha256_unchanged':sha_file(ascii_file)==sha_file(filename),
                                             'imread_ascii_equals_imdecode_unicode_bytes':identical,
                                             'decoded_shape':list(decoded.shape),'decoded_dtype':str(decoded.dtype)}
                report['unicode_decode_equivalence']=decode_checks
            run=TrainRun({'output_directory':str(HERE),'train_root':str(root),
                'source_directory':pin['source_directory'],'pretrained':{'path':str(HERE/'unused.pth')}},HERE/'unused_plan.json',HERE/'unused_profile.json')
            with run.image_boundary() if args.use_adapter_reader else nullcontext():
                satellite,drone,identity,target=dataset[0]
            report['output']={view:{'shape':list(value.shape),'dtype':str(value.dtype),
                'device':str(value.device),'finite':bool(torch.isfinite(value).all()),
                'min':float(value.min()),'max':float(value.max())}
                for view,value in [('satellite',satellite),('drone',drone)]}
            assert all(value['shape']==[3,384,384] and value['device']=='cpu' and value['finite'] for value in report['output'].values())
            report['status']='passed'
            report['cuda_initialized']=bool(torch.cuda._initialized)
            assert report['cuda_initialized'] is False
    except BaseException as error:
        report['status']='failed'
        report['error']=repr(error)
        report['traceback']=traceback.format_exc()
        raise
    finally:
        write_json(report_path,report)
        print(json.dumps({'report':str(report_path),'status':report['status'],'gpu_execution':False}))

if __name__=='__main__':
    main()
