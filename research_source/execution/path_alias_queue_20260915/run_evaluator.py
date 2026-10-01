"""Use the frozen evaluator with explicit same-file source-path compatibility."""
import argparse
import json
from pathlib import Path
import sys
from compatibility import Addendum, open_evaluator, no_science, require

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', required=True, choices=['camp_author', 'dac_author', 'camp_independent'])
    parser.add_argument('--addendum-sha256', required=True)
    parser.add_argument('--check-sources', action='store_true')
    cli = parser.parse_args()
    addendum = Addendum(cli.addendum_sha256)
    module, args, prepared, guard, job = open_evaluator(addendum, cli.role)
    evidence = {'event': 'same_file_compatibility_preflight', 'role': cli.role,
                'addendum': addendum.snapshot.artifact(), 'prepared': prepared.artifact(),
                'registered_command': job['command'], 'execution_command': list(sys.argv),
                'aliases': guard.latest_aliases, 'check_sources_only': cli.check_sources}
    print(json.dumps(evidence, ensure_ascii=False), flush=True)
    if cli.check_sources:
        no_science()
        return
    require(Path(sys.executable).resolve() == Path(job['command'][0]).resolve(), 'Use the registered native interpreter')
    addendum.verify_sources()
    prepared.unchanged()
    try:
        # Original runtime/resource/completion/release/lock gates remain inside.
        if cli.role == 'camp_independent':
            module.run(args)
        else:
            with module.evaluation_lock():
                module.evaluate(args)
    finally:
        prepared.unchanged()
        addendum.verify_sources()
        guard()
        print(json.dumps({'event': 'same_file_compatibility_postflight', 'role': cli.role,
                          'aliases': guard.latest_aliases, 'addendum_sha256': cli.addendum_sha256},
                         ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
