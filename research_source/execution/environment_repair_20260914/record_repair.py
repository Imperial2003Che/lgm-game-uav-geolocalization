"""Record the quarantined wrong-environment attempt and the verified rollback."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
BACKUP = EXEC / 'resume_backups/20260914_110612/lgm_game_pytorch/runs/formal_main/university1652/visual_style/seed_1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    discarded = HERE / 'rejected_mixed_environment_seed1'
    evidence = {p.relative_to(discarded).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                for p in discarded.rglob('*') if p.is_file()}
    backup = json.loads((BACKUP / 'backup_manifest.json').read_text(encoding='utf-8'))
    for name, artifact in backup['artifacts'].items():
        if sha(BACKUP / name) != artifact['sha256']:
            raise RuntimeError('Original accepted checkpoint evidence changed')
    restored_manifest = json.loads((BACKUP / 'run_manifest.json').read_text(encoding='utf-8'))
    rejected_manifest = json.loads((discarded / 'run_manifest.json').read_text(encoding='utf-8'))
    runtime = json.loads((HERE / 'verified_original_runtime.json').read_text(encoding='utf-8'))
    state = json.loads((EXEC / 'status.json').read_text(encoding='utf-8'))
    if state['python'] != runtime['executable'] or state['runtime_provenance']['packages'] != runtime['packages']:
        raise RuntimeError('The relaunched primary is not using the verified original environment')
    record = {'status': 'rolled_back_and_restarted_from_verified_original_checkpoint',
              'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'error': 'The assistant selected the Transactions baseline interpreter for the initial 2026-09-14 resume; its NumPy and Pillow versions did not match the original formal experiment.',
              'rejected_runtime': {'executable': r'C:\项目\.venvs\lgm-transactions\Scripts\python.exe',
                                   'numpy': '2.2.4', 'Pillow': '11.2.1'},
              'accepted_original_runtime': runtime, 'restored_original_backup': str(BACKUP),
              'restored_files_sha256': backup['artifacts'],
              'accepted_start_epoch_count': restored_manifest['history_rows'],
              'rejected_attempt_epoch_count': rejected_manifest['history_rows'],
              'rejected_outputs_used_for_paper_or_further_training': False,
              'quarantined_artifacts': evidence,
              'new_launch_id': state['launch_id'], 'new_launch_started_utc': state['started_utc'],
              'controller_sha256': sha(EXEC / 'continue_formal_matrix.py'),
              'restore_verification': 'All six original backup hashes were checked before and after copying, before the corrected process was launched. The restarted run can now update its own live files.',
              'process_scope': 'Only the assistant-owned controller/training process trees were stopped. Process identities were captured before and after.'}
    (HERE / 'repair_receipt.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': record['status'], 'accepted_start_epoch_count': record['accepted_start_epoch_count'],
                      'rejected_attempt_epoch_count': record['rejected_attempt_epoch_count'],
                      'quarantined_files': len(evidence), 'new_launch_id': state['launch_id']}))


if __name__ == '__main__':
    main()
