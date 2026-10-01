"""Execute unchanged formal science with the original checked project spelling."""
import argparse
import importlib
import json
from pathlib import Path
import sys
from project_paths import FrozenProjectPath, LOGICAL, require
from source_contract import verify

def load_core():
    package = LOGICAL / 'lgm_game_pytorch'
    sys.path.insert(0, str(package))
    core = importlib.import_module('lgm_game_pytorch.formal_retrieval')
    require(Path(core.__file__).resolve() == (package / 'lgm_game_pytorch/formal_retrieval.py').resolve(), 'Wrong formal core imported')
    core.Path = FrozenProjectPath
    return core

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--path-compat-sha256', required=True)
    options, original_args = parser.parse_known_args()
    evidence = verify(options.path_compat_sha256)
    require(original_args and original_args[0] in ('train', 'evaluate'), 'Expected original train/evaluate arguments')
    print(json.dumps({'event': 'primary_path_compatibility', 'source': evidence,
                      'execution_command': list(sys.argv), 'original_arguments': original_args}, ensure_ascii=False), flush=True)
    core = load_core()
    verify(options.path_compat_sha256)
    core.main(original_args)

if __name__ == '__main__': main()
