"""Read paths, distribution metadata and package version-source text only."""
from pathlib import Path
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import os
import re
import sys

result={'executable':sys.executable,'version':sys.version,'isolated':bool(sys.flags.isolated),'sys_path':sys.path,
        'PYTHONPATH':os.environ.get('PYTHONPATH'),'PYTHONHOME':os.environ.get('PYTHONHOME'),
        'packages':{},'scientific_modules_imported':[]}
for name,distribution in [('numpy','numpy'),('PIL','Pillow'),('torch','torch'),('torchvision','torchvision')]:
    spec=importlib.util.find_spec(name)
    dist=metadata.distribution(distribution)
    row={'metadata_version':dist.version,'distribution_metadata_path':str(dist._path),'module_origin':spec.origin if spec else None}
    if name in ('numpy','PIL') and spec:
        root=Path(spec.origin).parent
        files={}
        for relative in ('version.py','_version.py','__init__.py'):
            path=root/relative
            if path.is_file():
                content=path.read_text(encoding='utf-8')
                lines=[line.strip() for line in content.splitlines() if re.search(r'__version__\s*=|["\x27]version["\x27]\s*:|^version\s*=|^short_version\s*=',line)]
                files[relative]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'version_lines':lines[:12]}
        row['version_source_files']=files
    result['packages'][distribution]=row
result['scientific_modules_imported']=[name for name in ('numpy','PIL','torch','torchvision') if name in sys.modules]
print(json.dumps(result,ensure_ascii=True,indent=2))
