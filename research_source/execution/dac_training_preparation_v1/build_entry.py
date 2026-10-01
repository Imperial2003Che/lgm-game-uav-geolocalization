"""CPU-only, AST-located line edits to the pinned official DAC entry point."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'literature/official_repos/snapshots/SummerpanKing__DAC__5612a79c3928'
COMMIT = '5612a79c3928d8a71939e4e761bb352f805cb51b'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    gap = json.loads((HERE.parent / 'dac_independent_preparation_audit_1520/DAC_INDEPENDENT_GAP_AUDIT.json').read_text(encoding='utf-8'))
    audit = {'repo': 'SummerpanKing/DAC', 'commit_sha': gap['source']['commit'], 'files': [dict(path=Path(r['path']).relative_to(SOURCE).as_posix(), sha256=r['sha256'], bytes=r['bytes']) for r in gap['source']['files']]}
    assert audit['commit_sha'] == COMMIT
    for row in audit['files']:
        assert sha(SOURCE / row['path']) == row['sha256'], row['path']
    original = (SOURCE / 'train_university.py').read_text(encoding='utf-8')
    tree = ast.parse(original)
    lines = original.splitlines(keepends=True)
    edits = []
    def replace(node, text, reason):
        indent = ' ' * node.col_offset
        body = ''.join(indent + line + '\n' if line else '\n' for line in text.splitlines())
        edits.append((node.lineno - 1, node.end_lineno, body, reason))
    def expr(node):
        return ast.unparse(node)
    config_class = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    init = next(n for n in config_class.body if isinstance(n, ast.FunctionDef))
    drop_flags = {'--only_test','--only_draw_heat','--ckpt_path','--batch_size_eval',
                  '--eval_every_n_epoch','--eval_gallery_n','--zero_shot','--checkpoint_start',
                  '--data_folder'}
    for node in init.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            c = node.value
            if isinstance(c.func, ast.Attribute) and c.func.attr == 'add_argument':
                name = ast.literal_eval(c.args[0])
                if name in drop_flags:
                    replace(node, '', 'remove evaluation / alternate checkpoint CLI')
                elif name == '--device':
                    replace(node, "parser.add_argument('--device', default='cuda', type=str)",
                            'no CUDA probing during configuration construction')
        elif isinstance(node, ast.Assign) and expr(node.targets[0]) == 'args':
            replace(node, 'args = parser.parse_args([], namespace=self)',
                    'fixed official defaults; wrapper only exposes seed and declared input artifacts')
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module == 'sample4geo.dataset.university':
                replace(node, 'from sample4geo.dataset.university import U1652DatasetTrain, get_transforms',
                        'training imports no evaluation dataset')
            elif node.module == 'sample4geo.evaluate.university' or node.module == 'sample4geo.model':
                replace(node, '', 'no evaluation import or alternate backbone')
            elif node.module == 'sample4geo.utils':
                replace(node, 'from sample4geo.utils import setup_system', 'wrapper owns append-only stdout/stderr logs')
        if isinstance(node, ast.If) and expr(node.test).startswith('config.dataset =='):
            replace(node, 'DAC_RUN.configure(config)', 'explicit train roots; no test paths')
    block = next(n for n in tree.body if isinstance(n, ast.If) and '__name__' in expr(n.test))
    for node in block.body:
        text = expr(node)
        if isinstance(node, ast.Assign):
            target = expr(node.targets[0])
            if target == 'model_path':
                replace(node, 'model_path = str(DAC_RUN.output)', 'fixed isolated output directory')
            elif target == 'sys.stdout':
                replace(node, '', 'wrapper owns logging without closing parent stdout')
            elif target in {'query_dataset_test','query_dataloader_test','gallery_dataset_test','gallery_dataloader_test','best_score','start_epoch'}:
                replace(node, '', 'remove test dataset/loaders and test-selected state')
            elif target == 'train_dataloader':
                replacement = ast.get_source_segment(original, node) + '\ntrain_dataloader = DAC_RUN.wrap_loader(train_dataloader)'
                # get_source_segment carries continuation indentation; only first line needs dedent here.
                replace(node, replacement, 'observe batches without changing the official DataLoader')
            elif target == 'train_steps_per':
                replace(node, 'DAC_RUN.observe_optimizer(optimizer, model, scaler)\n' +
                        ast.get_source_segment(original, node),
                        'observe actual AdamW updates with a post-step hook; optimizer math unchanged')
        elif isinstance(node, ast.Expr):
            if 'shutil.copyfile' in text:
                replace(node, '', 'source manifest replaces cwd-dependent source copy')
            elif any(s in text for s in ['query_dataset_test', 'gallery_dataset_test']):
                replace(node, '', 'remove test-count logging')
        elif isinstance(node, ast.If):
            test = expr(node.test)
            if test == 'config.handcraft_model is not True':
                replace(node, 'model = DAC_RUN.make_model(config)',
                        'official architecture with strict local pretrained loading; no timm registry ambiguity')
            elif test in {'config.checkpoint_start is not None','config.only_test','config.zero_shot'}:
                replace(node, '', 'remove alternate checkpoint / evaluation entry')
            elif test == 'config.record':
                replace(node, "writer = SummaryWriter(str(DAC_RUN.output / 'tensorboard')) if config.record else None",
                        'isolated TensorBoard output; recording setting preserved')
            elif any(isinstance(c, ast.Call) and expr(c.func) == 'torch.save' for c in ast.walk(node)):
                replace(node, 'DAC_RUN.save_complete(globals())', 'last epoch only; full resumable state and plain weights')
        elif isinstance(node, ast.For):
            for inner in node.body:
                if isinstance(inner, ast.If) and 'config.eval_every_n_epoch' in expr(inner.test):
                    replace(inner, '', 'remove test evaluation and best-checkpoint selection')
                elif isinstance(inner, ast.Assign) and expr(inner.targets[0]) == 'train_loss':
                    replacement = 'DAC_RUN.before_epoch(epoch, train_dataloader)\n' + ast.get_source_segment(original, inner)
                    replace(inner, replacement, 'capture actual post-shuffle sample order and step count')
    edits.sort()
    for left, right in zip(edits, edits[1:]):
        assert left[1] <= right[0], (left, right)
    output = lines[:]
    for start, end, text, reason in reversed(edits):
        output[start:end] = [text]
    generated = "if 'DAC_RUN' not in globals():\n    raise RuntimeError('Use the separately admitted DAC training session; direct model import is disabled')\n\n" + ''.join(output)
    ast.parse(generated)
    target = HERE / 'train_university_train_only.py'
    target.write_text(generated, encoding='utf-8', newline='\n')
    (HERE / 'official_to_train_only.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), generated.splitlines(True),
        fromfile=f'DAC@{COMMIT}/train_university.py', tofile=target.name)), encoding='utf-8')
    pin = {k: audit[k] for k in ('repo','commit_sha','files')}
    pin['official_source_directory'] = str(SOURCE)
    pin['source_directory'] = str(HERE / 'scientific_source')
    pin['source_audit_sha256'] = sha(HERE.parent / 'dac_independent_preparation_audit_1520/DAC_INDEPENDENT_GAP_AUDIT.json')
    pin['license'] = 'Apache-2.0; original LICENSE copied with scientific source'
    (HERE / 'SOURCE_PIN.json').write_text(json.dumps(pin, ensure_ascii=False, indent=2), encoding='utf-8')
    (HERE / 'ADAPTER_EDITS.json').write_text(json.dumps([
        {'official_line_start': s + 1, 'official_line_end': e, 'reason': r}
        for s, e, t, r in edits], ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'source_files_verified': len(audit['files']), 'edits': len(edits),
                      'generated_sha256': sha(target), 'gpu_execution': False}))

if __name__ == '__main__':
    main()
