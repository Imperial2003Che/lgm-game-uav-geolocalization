"""Compile only the newly changed main bibliography; unchanged supplement inherited."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, subprocess

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def record(p):
    b = p.read_bytes()
    return {'path': str(p.resolve()), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft', required=True)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    draft = Path(args.draft).resolve()
    attempt = Path(args.attempt).resolve()
    attempt.mkdir(parents=True, exist_ok=False)
    source_paths = sorted([*draft.rglob('*.tex'), *draft.rglob('*.bib')])
    before = [record(p) for p in source_paths]
    report = {'schema': 'lgm-local-manuscript-compile.v1', 'started_utc': stamp(),
              'draft': str(draft), 'input_texts': before, 'commands': [],
              'scope': 'Actual local compilation only; no final manuscript or scientific adoption.',
              'compiler_installer_disabled': True, 'shell_escape_disabled': True}
    def save():
        (attempt/'COMPILE.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    save()
    texbin = Path(r'C:\Users\17703\AppData\Local\Programs\MiKTeX\miktex\bin\x64')
    try:
        for name in ('main',):
            pdf = draft/(name+'.pdf')
            if pdf.exists():
                shutil.copy2(pdf, attempt/(name+'.before.pdf'))
            latex = [str(texbin/'pdflatex.exe'), '-disable-installer', '-disable-write18',
                     '-interaction=nonstopmode', '-halt-on-error', '-file-line-error', name+'.tex']
            commands = [latex, [str(texbin/'bibtex.exe'), '-disable-installer', name], latex, latex]
            for index, command in enumerate(commands, 1):
                stdout = attempt/f'{name}.{index}.stdout.txt'
                item = {'document': name, 'pass': index, 'args': command, 'cwd': str(draft),
                        'started_utc': stamp(), 'stdout': str(stdout)}
                report['commands'].append(item)
                save()
                with stdout.open('xb') as stream:
                    result = subprocess.run(command, cwd=draft, stdin=subprocess.DEVNULL,
                                            stdout=stream, stderr=subprocess.STDOUT, timeout=180)
                item.update(finished_utc=stamp(), exit_code=result.returncode, log=record(stdout))
                for suffix in ('.log', '.blg'):
                    source = draft/(name+suffix)
                    if source.exists():
                        shutil.copy2(source, attempt/f'{name}.{index}{suffix}')
                save()
                if result.returncode:
                    raise RuntimeError(f'{name} pass {index}: exit {result.returncode}; preserved logs')
            report.setdefault('outputs', []).append(record(pdf))
            save()
        after = [record(p) for p in source_paths]
        if after != before:
            raise RuntimeError('Manuscript input texts changed during compilation')
        report.update(status='compiled', finished_utc=stamp(), input_texts_unchanged=True)
        save()
        print(json.dumps({'status': report['status'], 'report': str(attempt/'COMPILE.json'),
                          'outputs': report['outputs']}, ensure_ascii=False))
    except BaseException as exc:
        report.update(status='failed', finished_utc=stamp(), error=repr(exc))
        save()
        raise

if __name__ == '__main__':
    main()
