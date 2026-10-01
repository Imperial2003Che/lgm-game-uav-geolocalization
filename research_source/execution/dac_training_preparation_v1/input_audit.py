"""Exact inherited stdlib/input helpers; scientific imports only inside runtime_environment."""
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
from common_runtime import sha_file,write_json

def environment():
    return {'executable': str(Path(sys.executable).resolve()), 'python': platform.python_version(),
            'prefix': str(Path(sys.prefix).resolve()), 'platform': platform.platform(),
            'packages': {d.metadata['Name'].lower(): d.version for d in importlib.metadata.distributions()}}

def runtime_environment(output):
    """Verify actual imported module origins/versions before the first CUDA query."""
    mapping = {'torch':'torch', 'torchvision':'torchvision', 'timm':'timm', 'numpy':'numpy',
               'PIL':'pillow', 'cv2':'opencv-python-headless', 'albumentations':'albumentations',
               'sklearn':'scikit-learn', 'transformers':'transformers', 'tensorboard':'tensorboard'}
    report = {}
    for module_name, distribution in mapping.items():
        module = importlib.import_module(module_name)
        origin = Path(module.__file__).resolve()
        if not origin.is_relative_to(Path(sys.prefix).resolve()):
            raise RuntimeError(f'Runtime module escaped the registered environment: {module_name}: {origin}')
        version = str(getattr(module, '__version__', ''))
        if module_name == 'cv2':
            try:
                expected = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                distribution = 'opencv-python'
                expected = importlib.metadata.version(distribution)
            consistent = expected == version or expected.startswith(version + '.')
        else:
            expected = importlib.metadata.version(distribution)
            consistent = expected == version
        if not consistent:
            raise RuntimeError(f'Runtime / metadata version mismatch: {module_name}: {version} vs {expected}')
        report[module_name] = {'version': version, 'distribution': distribution,
                               'distribution_version': expected, 'origin': str(origin)}
    write_json(output / 'runtime_environment.json', report)
    return report

def data_manifest(root):
    root = Path(root).resolve()
    if root.name.lower() != 'train' or not root.is_dir():
        raise RuntimeError('--train-root must be the explicit University train directory')
    rows, enumeration = [], {}
    id_sets = []
    for view in ('satellite', 'drone'):
        folder = root / view
        if not folder.is_dir():
            raise RuntimeError(f'Missing train view: {view}')
        ids = [p.name for p in folder.iterdir() if p.is_dir()]
        if len(ids) != 701 or not all(i.isdigit() for i in ids):
            raise RuntimeError('Expected the complete 701-ID University training split')
        id_sets.append(set(ids))
        # Preserve OS traversal order: the official get_data intentionally does not sort files.
        enumeration[view] = []
        for current, dirs, files in os.walk(folder, topdown=False):
            enumeration[view].append({'directory': Path(current).relative_to(root).as_posix(),
                                      'directories': dirs[:], 'files': files[:]})
        for identity in ids:
            files = list((folder / identity).iterdir())
            if not files or (view == 'satellite' and len(files) != 1):
                raise RuntimeError('Each training ID needs one satellite and at least one drone image')
            for image in files:
                if not image.is_file() or not image.resolve().is_relative_to(root) or image.suffix.lower() not in {'.jpg','.jpeg','.png'}:
                    raise RuntimeError(f'Unexpected file in training split: {image}')
                rows.append({'path': image.relative_to(root).as_posix(), 'bytes': image.stat().st_size,
                             'sha256': sha_file(image)})
    if id_sets[0] != id_sets[1]:
        raise RuntimeError('Training identity sets differ between views')
    return {'dataset': 'University-1652', 'split': 'train', 'identity_count': 701,
            'train_root': str(root), 'files': sorted(rows, key=lambda r:r['path']),
            'official_os_walk_order': enumeration}
