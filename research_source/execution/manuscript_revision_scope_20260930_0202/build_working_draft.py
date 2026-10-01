"""Offline manuscript integration; CSV formatting only, never scientific execution."""
from pathlib import Path
import csv
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import difflib
import hashlib
import io
import json
import re

HERE = Path(__file__).absolute().parent
EX = HERE.parent
OUT = EX.parent
WORKSPACE = OUT.parent.parent
BASE = WORKSPACE / 'outputs/paper_label_revision_20260914/manuscript'
DELIVERY = OUT / 'manuscript_evidence_revision_20260930_0202'
NEW = DELIVERY / 'manuscript'
PKG = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch')
inputs = {}
cell_records = []

def read(path):
    path = Path(path)
    assert path.suffix.lower() not in {'.pt', '.pth', '.npz', '.npy', '.zip', '.jpg', '.png'}
    data = path.read_bytes()
    inputs[str(path)] = dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return data

def load(path):
    return json.loads(read(path).decode('utf-8-sig'))

def rows(path):
    return list(csv.DictReader(io.StringIO(read(path).decode('utf-8-sig'))))

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)

def text_bytes(value):
    return value.replace('\r\n', '\n').encode('utf-8')

def normalized(path):
    return read(path).decode('utf-8-sig').replace('\r\n', '\n')

def binding(path):
    data = Path(path).read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def replace_once(text, old, new):
    assert text.count(old) == 1, 'Unexpected source anchor: ' + old[:80]
    return text.replace(old, new, 1)

def format_value(value, scale=1):
    x = Decimal(value) * Decimal(scale)
    rounded = x.quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
    if x > 0 and rounded == 0:
        return '<0.001'
    return str(rounded)

def cell(source, row, column, scale=1):
    value = format_value(row[column], scale)
    cell_records.append(dict(source=str(source), task=row['task'], variant=row.get('variant'),
        setting=row.get('setting'), column=column, source_value=row[column], display_scale=scale,
        formatted=value))
    return value

task_order = ['university1652_drone_to_satellite', 'university1652_satellite_to_drone',
    'university1652_street_to_satellite']
for height in (150, 200, 250, 300):
    task_order += [f'sues200_uav_{height}m_to_satellite', f'sues200_satellite_to_uav_{height}m']
labels = {
    'university1652_drone_to_satellite': r'University D2S',
    'university1652_satellite_to_drone': r'University S2D',
    'university1652_street_to_satellite': r'University Street2S'}
for height in (150, 200, 250, 300):
    labels[f'sues200_uav_{height}m_to_satellite'] = f'SUES U{height}$\\to$S'
    labels[f'sues200_satellite_to_uav_{height}m'] = f'SUES S$\\to$U{height}'

assert not DELIVERY.exists(), 'New working draft directory already exists; do not overwrite'
package = load(BASE / 'SOURCE_PACKAGE_MANIFEST.json')
assert package['file_count'] == 26
original = {item['path']: read(BASE / item['path']) for item in package['files']}
for item in package['files']:
    assert inputs[str(BASE / item['path'])]['sha256'] == item['sha256']
assert not {'main.pdf', 'supplementary.pdf'} & original.keys()

official_root = load(EX / 'evaluation_audits_20260929/ROOT_OFFICIAL42_AND_PIPELINE2_ADOPTION_20260929.json')
assert official_root['accepted_total_evaluation_runs'] == 42
assert official_root['accepted_total_retrieval_tasks'] == 231
primary = load(OUT / 'formal_results_native_20260929/PRIMARY_CLAIM_REVIEW.json')
assert primary['task_count'] == 11 and primary['full_lower_R1_and_mAP_task_count'] == 10
official_sources = [OUT / 'formal_results_native_20260929/v2' / f'formal_main_{dataset}_variants_source.csv'
    for dataset in ('university1652', 'sues200')]
official_rows = []
official_lookup = {}
figure_root = load(OUT / 'formal_results_native_20260929/ROOT_NATIVE_SVG_REVIEW.json')
for source in official_sources:
    values = rows(source)
    accepted = next(item['source'] for item in figure_root['figures'] if item['source']['path'] == str(source))
    assert binding(source) == accepted
    for row in values:
        assert row['n_seeds'] == '3' and row['seeds'] == '1|2|3' and row['complete_seed_triplet'] == 'true'
        key = (row['task'], row['variant'])
        assert key not in official_lookup
        official_lookup[key] = (source, row)
    official_rows += values
assert len(official_rows) == 66
transfer_root = load(EX / 'transfer_results_20260929/ROOT_AGGREGATION_ADOPTION.json')
assert transfer_root['scope']['accepted_runs'] == 12
assert transfer_root['descriptive_findings']['full_mean_R1_below_visual_tasks'] == 11
t3_path = OUT / 'transfer_native_figures_20260929_1750/output/source_data/THREE_SEED_SUMMARY.csv'
t3_delta = OUT / 'transfer_native_figures_20260929_1750/output/source_data/FULL_MINUS_VISUAL.csv'
t3_rows = rows(t3_path)
rows(t3_delta)
for path in (t3_path, t3_delta):
    declared = next(x for x in transfer_root['bindings'] if x['path'].endswith('\\' + path.name))
    assert binding(path)['sha256'] == declared['sha256'] and binding(path)['bytes'] == declared['bytes']
assert len(t3_rows) == 22 and all(row['n_seeds'] == '3' for row in t3_rows)
t3_lookup = {(row['task'], row['variant']): row for row in t3_rows}
aggregate_dir = PKG / 'results/formal_matrix_aggregate'
aggregate_manifest = load(aggregate_dir / 'aggregate_manifest.json')
assert binding(aggregate_dir / 'aggregate_manifest.json')['sha256'] == official_root['pipeline_aggregate']['manifest']['sha256']
sens_path = aggregate_dir / 'sensitivity_with_main_reference.csv'
sens_rows = rows(sens_path)
sens_declared = next(x for x in aggregate_manifest['output_artifacts'] if x['path'] == sens_path.name)
assert binding(sens_path)['sha256'] == sens_declared['sha256'] and len(sens_rows) == 44
assert all(row['seed'] == '1' for row in sens_rows)
sens_lookup = {(row['task'], row['setting']): row for row in sens_rows}
post = load(EX / 'pipeline_post_robustness_audit_20260929_1448/ROOT_POST_ROBUSTNESS_ADOPTION.json')
assert post['accepted_with_stated_limits'] and post['query']['task_seed_pairs'] == 33
assert post['query']['T4_margin_strata_recomputed'] == 132 and post['query']['T5_native_query_recomputed'] == 66
assert not post['query']['bootstrap_CI_recomputed'] and post['T6_completed'] is False
read(Path(post['mandatory_annex']['path']))

# Read the existing small plot tables, not the underlying per-query arrays.
diagnostics = [
    OUT / 'robustness_native_figures_20260929_1650/output/source_data/university1652_drone_to_satellite__r_at_1.csv',
    OUT / 'query_t4_margin_native_figures_20260929_1952/output/source_data/MARGIN_STRATA_132.csv',
    OUT / 'query_t5_native_figures_20260929_1856/output_v2/source_data/NATIVE_POINTS_660.csv',
    OUT / 'query_t5_reliability_native_figures_20260929_2054/output/source_data/RELIABILITY_BINS_990.csv',
    OUT / 'query_t5_paired_native_figures_20260929_2157/output/source_data/PAIRED_SUCCESS_132.csv']
expected_rows = (60, 132, 660, 990, 132)
for path, count in zip(diagnostics, expected_rows):
    assert len(rows(path)) == count
readmes = [
    'robustness_native_figures_20260929_1650/output/README.md',
    'transfer_native_figures_20260929_1750/output/README.md',
    'query_t4_margin_native_figures_20260929_1952/output/README.md',
    'query_t5_native_figures_20260929_1856/output_v2/README.md',
    'query_t5_reliability_native_figures_20260929_2054/output/README.md',
    'query_t5_paired_native_figures_20260929_2157/output/README.md']
for path in readmes:
    read(OUT / path)

# Check the actual checkpoint naming semantics without opening any checkpoint.
train_source = PKG / 'lgm_game_pytorch/formal_retrieval.py'
runner_source = PKG / 'experiments/run_frozen_formal_matrix.py'
train_text = normalized(train_source)
runner_text = normalized(runner_source)
assert 'best.pt intentionally tracks the' in train_text and 'pre-specified final epoch (no validation selection)' in train_text
assert 'best_epoch is not the pre-specified final epoch' in runner_text
example_dir = PKG / 'runs/formal_main/university1652/visual/seed_1'
example_manifest = load(example_dir / 'run_manifest.json')
example_config = load(example_dir / 'run_config.json')
assert example_manifest['epochs_completed'] == 80 and example_manifest['best_epoch'] == 79
assert example_manifest['best_validation_mAP'] is None and example_manifest['test_protocol_was_evaluated'] is False
assert example_config['immutable_config']['validation_ids'] == []
assert example_config['immutable_config']['selection']['patience'] == 0

main = original['main.tex'].decode('utf-8-sig').replace('\r\n', '\n')
main = replace_once(main, '% Manuscript revision: 20260914; language draft with fixed numerical sources',
    '% Local evidence-integration working draft: 20260930; original 20260914 source retained')
notice = r'''\markboth{Local working draft --- 30 September 2026}{Independent Content and Style Evidence}
\begin{center}\footnotesize\itshape
Local working draft: completed-result integration; remaining experiments and final review are pending.
\end{center}'''
main = replace_once(main, '\\maketitle\n', '\\maketitle\n' + notice + '\n')
abstract = r'''\begin{abstract}
Fixed semantic vocabularies offer a compact way to compare content and
acquisition-style information in UAV--satellite retrieval. We study an
interface with independent per-image encoding: a frozen vision--language model scores
each image against both vocabularies and separate probability encoders fuse
the resulting vectors with a learned visual descriptor. A common
multi-positive training protocol evaluates six input configurations on
University-1652 and SUES-200. Across the 11 official retrieval tasks, the
Full configuration has lower three-seed mean Recall@1 and official
trapezoidal mAP than Visual on 10 tasks; the Street2S exception has low
absolute accuracy. In bidirectional cross-dataset transfer, Full has lower
mean Recall@1 in all 11 target tasks. Seed-1 corruption measurements and
clean-query margin diagnostics characterize these results under explicit
metric and membership definitions. A separate historical study of four
public visual baselines analyzes ranking and score fusion. The completed
comparisons do not support a general accuracy advantage from this frozen
semantic-fusion design and delimit the claims that its conditional
diagnostics can support.
\end{abstract}'''
main, count = re.subn(r'\\begin\{abstract\}.*?\\end\{abstract\}', lambda _: abstract, main, count=1, flags=re.S)
assert count == 1
contributions = r'''The contributions of this work are summarized as follows:
\begin{itemize}
  \item We define fixed content and acquisition-style input vectors that are
  constructed separately for each image and can be cached for independent
  query and gallery encoding.
  \item We evaluate six input configurations under one multi-positive
  training protocol, retaining all official tasks and all three seeds.
  The Full-versus-Visual comparison is negative on 10 of 11 official tasks
  for both mean R@1 and mAP, and on all 11 transfer tasks for mean R@1.
  \item We distinguish seed-1 corruption retention from absolute accuracy,
  and shared-query margin strata from variant-specific selective retrieval.
  These diagnostics define the comparison being made without assigning a
  causal explanation or a calibrated-probability interpretation.
  \item We retain a separate analysis of four public visual baselines on
  University-1652, covering ranking rules, gallery size and retrospective
  score fusion under their own trained feature sources.
\end{itemize}'''
start = main.index('The contributions of this work are summarized as follows:')
end = main.index('\\end{itemize}', start) + len('\\end{itemize}')
main = main[:start] + contributions + main[end:]
main = replace_once(main, 'experimental protocol, followed by the public-baseline analysis in\nSection~\\ref{sec:public}.',
    'experimental protocol. Section~\\ref{sec:semantic-results} reports the\nsemantic-model results, followed by the separate historical public-baseline\nanalysis in Section~\\ref{sec:public}.')
main = replace_once(main, 'fixed feature sources.\n\n\\subsection{Datasets and Retrieval Tasks}',
    'fixed feature sources. The completed semantic-model evidence comprises\n42 fits and 231 official run--task evaluations, followed by transfer,\nseed-1 corruption and clean-query diagnostics. Later external-comparison\nand efficiency results are not represented as completed experiments here.\n\n\\subsection{Datasets and Retrieval Tasks}')
main = replace_once(main, 'The predetermined final epoch is evaluated without early stopping or\ntest-based checkpoint selection.',
    'The predetermined final epoch is evaluated without early stopping or\ntest-based checkpoint selection. In this no-validation protocol, the\ntraining code names the final completed checkpoint \\texttt{best.pt}; the\nfilename does not denote selection by validation or test performance.')
main = replace_once(main, 'three seeds, giving 36 fits. Six further full-model fits vary the backbone',
    'three seeds, giving 36 completed fits. Six further seed-1 full-model fits vary the backbone')
main = replace_once(main, 'QDFL, FSRA, SDPL, CCR, and MCCG provide visual comparators\n\\cite{qdfl2025,fsra2022,sdpl2024,ccr2024,mccg2024}.',
    'QDFL, FSRA, SDPL, CCR, and MCCG remain external visual-comparison targets\n\\cite{qdfl2025,fsra2022,sdpl2024,ccr2024,mccg2024}; this working draft does\nnot report those pending comparisons as completed results.')
main = replace_once(main, 'and sample standard deviation.\n\nFor completed public-baseline comparisons,',
    'and sample standard deviation. The integrated semantic main and transfer\ntables are descriptive and do not infer significance from SD. The query\ndiagnostic audit did not independently resample the retained bootstrap\nintervals, which are not used here as new inferential evidence.\n\nFor the separate completed public-baseline comparisons,')
main = replace_once(main, 'clean-reference evaluations. It measures the change in retrieval after\npixel-level perturbation of the query.',
    'clean-reference evaluations. Full uses cached CLIP evidence for clean\nqueries and online CLIP evidence for corrupted queries, so its observed\nchange combines pixel perturbation with a change in evidence path. The\n64-image clean diagnostic had no numerical equivalence gate. Results are\nseed-1 descriptive comparisons, not multi-seed robustness estimates.')
main = replace_once(main, '% Insert only measured semantic-model results through the following module.\n% This module is empty until aggregate and per-query artifacts are checked.',
    '% Completed adopted summaries only; new tables format stored values without scientific recomputation.')
main = replace_once(main, '\\section{Visual Baselines and Retrieval Analysis}',
    '\\section{Historical Visual-Baseline Retrieval Analysis}')
main = replace_once(main, 'We evaluate four public visual baselines on University-1652, beginning\nwith full-gallery reproduction and then examining ranking rules, gallery\nsize, and score combination. Each comparison uses the same four trained\nfeature sources.',
    'This separate historical analysis evaluates four public visual baselines\non University-1652, beginning with full-gallery reproduction and then\nexamining ranking rules, gallery size and score combination. Its trained\nfeature sources and retrospective fusion are distinct from the semantic\nconfigurations in Section~\\ref{sec:semantic-results}; their gains are not\nresults of the proposed semantic fusion. Within this block, each comparison\nuses the same four trained feature sources.')
discussion_intro = r'''The fixed vocabulary supplies a repeatable input interface, and separate
branches preserve the content/style grouping through descriptor construction.
The completed comparisons show that this design does not yield a general
accuracy advantage under the frozen protocol: Full is lower than Visual in
10 of 11 official tasks for mean R@1 and mAP, and in every transfer task for
mean R@1. Street2S provides a small official exception at low absolute
accuracy. These are observations about the evaluated configurations; they
do not isolate a causal failure mechanism or establish a compensating
efficiency, robustness or calibration advantage.

The corruption and query diagnostics need their own interpretation.
Retention is normalized by each model's clean performance, shared Visual
margin masks condition the T4 comparison, and T5 variants can select
different query members. A favorable conditional value cannot replace the
full-task comparison. Independent per-image encoding still permits gallery
descriptors to be computed in advance, but a deployment benefit requires
corresponding measurements.

'''
start = main.index('The framework gives content and style scores separate roles in descriptor\nlearning.')
end = main.index('This design also defines concrete modeling trade-offs.', start)
main = main[:start] + discussion_intro + main[end:]
main = replace_once(main, 'a useful complement to the branch comparisons when attributing a measured\ngain to semantic information.',
    'a useful complement to the branch comparisons when attributing an observed\neffect to semantic information.')
main = replace_once(main, 'Likewise, controlled corruptions isolate sensitivity to a known pixel\ntransformation, while adverse-weather flights combine weather, motion,',
    'Here, the controlled-corruption comparison also changes Full\'s evidence\npath, so it does not isolate only a pixel transformation. Adverse-weather\nflights further combine weather, motion,')
conclusion = r'''\section{Conclusion}

We evaluated fixed content and acquisition-style probability inputs within
a shared UAV--satellite retrieval framework. The completed official and
transfer matrices retain the full task set and three training seeds. Full
has lower mean R@1 and mAP than Visual on 10 of 11 official tasks and lower
mean R@1 on all 11 transfer tasks; the low-accuracy Street2S exception does
not support a general fusion advantage. Seed-1 corruption and clean-query
diagnostics describe relative retention and conditional retrieval under
different evidence and query-membership definitions. Together, the results
provide a measured assessment of this fixed semantic interface, while the
separate public-baseline analysis retains its own ranking and post-hoc
fusion conclusions.

'''
start = main.index('\\section{Conclusion}')
end = main.index('\\FloatBarrier', start)
main = main[:start] + conclusion + main[end:]
main = replace_once(main, '% Balanced against the final 14-page working draft; revisit after adding results.\n\\IEEEtriggeratref{25}',
    '% Bibliography balancing must be reviewed after compiling this expanded local draft.')

supp = original['supplementary.tex'].decode('utf-8-sig').replace('\r\n', '\n')
supp = replace_once(supp, '% Supplementary editorial revision: 20260914', '% Supplementary local evidence-integration working draft: 20260930')
supp = replace_once(supp, '\\maketitle\n', '\\maketitle\n' + notice + '\n')
supp = replace_once(supp, '\\section{Public-Baseline Query Alignment}', '\\input{results/supplementary_evidence.tex}\n\n\\section{Historical Public-Baseline Query Alignment}')
supp = replace_once(supp, 'the numerical values behind the visual result summaries in the main paper.',
    'the numerical values behind the separate historical public-baseline\nresult summaries in the main paper.')
supp = replace_once(supp, 'The protocol comprises two datasets, six input configurations, and three\nseeds, for 36 independent 80-epoch fits.',
    'The completed main protocol comprises two datasets, six input configurations,\nand three seeds, for 36 independent 80-epoch fits.')
supp = replace_once(supp, 'Six additional full-model fits\nchange ResNet-18', 'Six additional seed-1 full-model fits\nchange ResNet-18')
supp = replace_once(supp, 'The full matrix contains 42 fits. QDFL, FSRA, SDPL,\nCCR, and MCCG define the external visual-comparison targets.',
    'The completed matrix contains 42 fits. QDFL, FSRA, SDPL,\nCCR, and MCCG define pending external visual-comparison targets; no completed\nresults for those comparisons are asserted in this working draft.')
supp = replace_once(supp, 'family. The semantic-model protocol defines a 33-test family across three seeds\nand 11 official tasks.',
    'family. The official semantic-model protocol defines a 33-test family\nacross three seeds and 11 official tasks. It is distinct from the T4/T5\ndiagnostic records described above; the retained semantic bootstrap\nintervals have not been independently resampled.')

outputs = dict(original)
outputs['main.tex'] = text_bytes(main)
outputs['supplementary.tex'] = text_bytes(supp)
outputs['results/semantic_results.tex'] = read(HERE / 'semantic_results.tex')
outputs['results/supplementary_evidence.tex'] = read(HERE / 'supplementary_evidence.tex')
outputs['README_OVERLEAF.md'] = text_bytes('# Local working draft only\n\nThis copy integrates accepted September 29 result summaries into the September 14 source project. It has not been uploaded to Overleaf. The September 27 online review draft and its source remain unchanged. Use README_LOCAL_WORKING_DRAFT.md and the sidecar provenance for scope; final submission and remaining experiments are pending. Do not treat any inherited review-copy delivery statement as a new compilation or publication claim.\n')

precision = r'Values are rounded to three decimals; a positive value that would round to zero is shown as $<0.001$. An actual zero remains 0.000.'
variants = ['visual', 'content', 'style', 'visual_content', 'visual_style', 'full']
def start_table(caption, label, spec, size='footnotesize'):
    return '\n'.join([r'\begin{table*}[!t]', r'\centering', '\\caption{' + caption + '}',
        '\\label{' + label + '}', '\\' + size, r'\setlength{\tabcolsep}{3pt}',
        '\\begin{tabular}{' + spec + '}', r'\toprule']) + '\n'
end_table = '\n'.join([r'\bottomrule', r'\end{tabular}', r'\end{table*}', ''])
for metric, short, title in [('r_at_1', 'r1', r'R@1 (\%)'), ('official_trapezoid_mAP', 'map', r'official trapezoidal mAP (\%)')]:
    table = start_table('Official ' + title + r' for all six input configurations. Cells show equally weighted seed-1/2/3 mean $\pm$ sample SD. V+C and V+S denote visual-plus-content and visual-plus-style. SD is descriptive, not a confidence interval. ' + precision,
        'tab:semantic-' + short, 'lrrrrrr')
    table += r'Task & Visual & Content & Style & V+C & V+S & Full \\' + '\n' + r'\midrule' + '\n'
    for index, task in enumerate(task_order):
        if index == 3:
            table += r'\midrule' + '\n'
        values = []
        for variant in variants:
            source, row = official_lookup[(task, variant)]
            values.append('$' + cell(source, row, metric + '_mean_pct') + r'\pm' + cell(source, row, metric + '_sample_sd_pct') + '$')
        table += labels[task] + ' & ' + ' & '.join(values) + r' \\' + '\n'
    outputs[f'tables/evidence_20260930/official_{short}.tex'] = text_bytes(table + end_table)

table = start_table(r'Cross-dataset transfer: all target tasks, with Visual (V) and Full (F) shown separately. Cells are three-seed mean $\pm$ sample SD. R@1 and official mAP are percentages; MRR$\times100$ is scaled reciprocal rank, not accuracy percent. SD is not a confidence interval. Training-dataset direction is given by the group headings. ' + precision,
    'tab:semantic-transfer', 'lrrrrrr')
table += r'& \multicolumn{2}{c}{R@1 (\%)} & \multicolumn{2}{c}{mAP (\%)} & \multicolumn{2}{c}{MRR$\times100$} \\' + '\n'
table += r'Target task & V & F & V & F & V & F \\' + '\n'
for tasks, heading in ((task_order[:3], r'SUES-200-trained $\to$ University-1652'), (task_order[3:], r'University-1652-trained $\to$ SUES-200')):
    table += r'\midrule' + '\n' + r'\multicolumn{7}{l}{\textit{' + heading + r'}} \\' + '\n'
    for task in tasks:
        values = []
        for metric in ('r_at_1', 'official_trapezoid_mAP', 'MRR'):
            for variant in ('visual', 'full'):
                row = t3_lookup[(task, variant)]
                values.append('$' + cell(t3_path, row, metric + '_mean', 100) + r'\pm' + cell(t3_path, row, metric + '_sample_sd', 100) + '$')
        table += labels[task] + ' & ' + ' & '.join(values) + r' \\' + '\n'
outputs['tables/evidence_20260930/transfer_all_tasks.tex'] = text_bytes(table + end_table)

settings = ['full', 'backbone_resnet50', 'embed_dim_256', 'embed_dim_1024']
for metric, short, title in [('r_at_1_pct', 'r1', r'R@1 (\%)'), ('official_trapezoid_mAP_pct', 'map', r'official trapezoidal mAP (\%)')]:
    table = start_table('Seed-1 Full sensitivity results: ' + title + '. The first column is the existing main Full seed-1 reference, not a three-seed mean. Each other setting uses one fit per dataset. No SD or significance is inferred. ' + precision,
        'tab:sensitivity-' + short, 'lrrrr', 'small')
    table += r'Task & R18/512 reference & R50/512 & R18/256 & R18/1024 \\' + '\n' + r'\midrule' + '\n'
    for index, task in enumerate(task_order):
        if index == 3:
            table += r'\midrule' + '\n'
        values = [cell(sens_path, sens_lookup[(task, setting)], metric) for setting in settings]
        table += labels[task] + ' & ' + ' & '.join(values) + r' \\' + '\n'
    outputs[f'tables/evidence_20260930/sensitivity_{short}.tex'] = text_bytes(table + end_table)

# A local source sidecar carries audit details; no operational audit is inserted in the paper.
for path in (EX / 't6_recovery_preparation_20260930_0104/ROOT_SOURCE_ADOPTION.json',
             EX / 't6_new_boot_contract_review_20260930_0104/adopt_new_boot_root.py',
             OUT / 'transfer_native_visio_candidate_20260930_0104/ROOT_SOURCE_ADOPTION.json',
             OUT / 'transfer_native_visio_candidate_20260930_0104/adopt_candidate_root.py'):
    read(path)
read(HERE / 'build_working_draft.py')
for relative, data in outputs.items():
    write(NEW / relative, data)
assert not (NEW / 'main.pdf').exists() and not (NEW / 'supplementary.pdf').exists()
patches = []
changes = []
for relative, data in outputs.items():
    previous = original.get(relative)
    if previous == data:
        continue
    assert Path(relative).suffix in {'.tex', '.md'}
    before = previous or b''
    patch = b''.join(difflib.diff_bytes(difflib.unified_diff, before.splitlines(keepends=True),
        data.splitlines(keepends=True), fromfile=('base/' + relative if previous is not None else '/dev/null').encode(),
        tofile=('working/' + relative).encode()))
    patch_name = relative.replace('/', '__') + '.patch'
    write(HERE / 'diffs' / patch_name, patch)
    patches.append(patch)
    changes.append(dict(relative_path=relative, kind='modified' if previous is not None else 'new',
        old=inputs.get(str(BASE / relative)), new=binding(NEW / relative), diff=binding(HERE / 'diffs' / patch_name)))
write(HERE / 'COMPLETE_MANUSCRIPT_DIFF.patch', b''.join(patches))
write(HERE / 'TABLE_CELL_TRANSCRIPTIONS.json', json_bytes(dict(
    schema='stored-summary-to-tex-formatting.v1', operation='Decimal display rounding and optional fraction-times-100 only',
    computed_new_means_sd_ci_pvalues=False, entries=cell_records)))
report = dict(schema='local-manuscript-evidence-integration.v1', utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    status='author_source_preparation_not_compiled_not_final', base_directory=str(BASE), working_directory=str(NEW),
    base_dependency_count=26, old_compiled_main_or_supp_pdf_copied=False, source_files=len(outputs),
    changes=changes, inputs=list(inputs.values()),
    complete_diff=binding(HERE / 'COMPLETE_MANUSCRIPT_DIFF.patch'),
    numeric_transcriptions=binding(HERE / 'TABLE_CELL_TRANSCRIPTIONS.json'),
    official_rows=66, transfer_rows=22, sensitivity_rows_with_reference=44,
    table_cells_mean_sd_and_sensitivity_scalars=len(cell_records),
    source_dependencies=[binding(NEW / relative) for relative in outputs],
    scientific_execution=False, native_or_COM_execution=False, compilation_performed=False,
    overleaf_updated=False, original_manuscript_or_state_modified=False,
    limitations=['Stored summaries formatted only; no query arrays or scientific libraries read or executed.',
        'Root compilation, page preview, independent content review and later experiments remain pending.',
        'All inherited numerical, statistical and provenance limits remain; full hashes and operations are sidecar only.'])
write(HERE / 'AUTHOR_INTEGRATION.json', json_bytes(report))
print(json.dumps(dict(status=report['status'], files=len(outputs), changed=len(changes),
    numeric_scalars=len(cell_records), report=binding(HERE / 'AUTHOR_INTEGRATION.json')), ensure_ascii=True))
