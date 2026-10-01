"""Record prior actual two-page visual inspection and seal new artifact review.

The script records, rather than performs, visual judgment. No science or prior
checker is called. The only repeat operation is final SHA/size byte-stability.
"""
from pathlib import Path
import datetime
from decimal import Decimal
import hashlib
import json

HERE=Path(__file__).resolve().parent
WORK=HERE.parent.parent/'transfer_native_figures_20260929_1750'
ROOT=HERE.parent/'transfer_results_20260929/ROOT_AGGREGATION_ADOPTION.json'

def bind(path):
    data=Path(path).read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(name,value):
    with (HERE/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
    return bind(HERE/name)

def main():
    assert bind(HERE/'DATA_CONTRACT.json')['sha256']=='89645c62dc3b8cd0710afc78abb3cdef0597dde8f50d94160cd192439e28ea62'
    assert bind(HERE/'ARTIFACT_REVIEW.json')['sha256']=='601eb1ef63e84592d5f33d25630c038643d8cd2f4305866ae56684052eaa4c0f'
    contract=load(HERE/'DATA_CONTRACT.json');artifact=load(HERE/'ARTIFACT_REVIEW.json')
    assert contract['checks']==708 and artifact['checks']==7956
    for rec in artifact['bindings']:
        current=bind(rec['path'])
        assert current['sha256']==rec['sha256'] and current['bytes']==rec['bytes']
    assert bind(ROOT)['sha256']=='a8867a9ebdf01061a55d143b79eff91196571c2275f4379902131a69dd4ce80c'
    assert sum(Decimal(r['MRR_full_minus_visual_x100'])<0 for r in contract['descriptive_contrasts'])==10
    assert [r['task'] for r in contract['descriptive_contrasts'] if Decimal(r['MRR_full_minus_visual_x100'])>0]==['university1652_street_to_satellite']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    sealed=HERE/'sealed';sealed.mkdir(exist_ok=False)
    snapshots=[]
    paths=[ROOT,HERE/'derive_figure_contract.py',HERE/'review_artifacts.py',Path(__file__),
           HERE/'DATA_CONTRACT.json',HERE/'ARTIFACT_REVIEW.json',WORK/'build/build_transfer.mjs',
           WORK/'BUILD_REPORT.json',WORK/'INPUT_PROVENANCE.json']+[Path(f['png']['path']) for f in artifact['figures']]
    for ordinal,path in enumerate(paths,1):
        dest=sealed/f'{ordinal:02d}_{path.name}'
        with dest.open('xb') as stream:stream.write(path.read_bytes())
        actual=bind(path);copied=bind(dest)
        assert actual['sha256']==copied['sha256'] and actual['bytes']==copied['bytes']
        snapshots.append({'original':actual,'snapshot':copied})
    viewed=[]
    for figure in artifact['figures']:
        viewed.append({'ordinal':figure['ordinal'],'direction':figure['direction'],'image':figure['png'],
                       'native_dimensions_px':figure['png_dimensions'],'actually_viewed':True,
                       'method':'tools.view_image(detail=original), full separate final PPT round-trip PNG; both pages displayed in one tool call before artifact checker execution.',
                       'findings':['Training dataset and evaluation dataset are explicit and separate from target retrieval directions/heights.',
                                   'All three metric columns, blue-circle Visual and orange-square Full, means, sample SD and all four visible limitation lines are clear.',
                                   'No apparent cropping, text overlap, missing glyphs or clipped intervals in the actual image.',
                                   'Small street values and zero sample SD remain visible via three-decimal labels on page2; no misleading magnified street scale.'] if figure['ordinal']==2 else
                                  ['All eight retrieval task/height rows are present and distinct, without pooling.',
                                   'Three metric columns, explicit mean/sample SD/seeds1-3 label and four limitation lines are readable.',
                                   'Training/evaluation title, circles/squares and three-decimal labels are clear; no apparent cropping, overlap or clipped interval.']})
    visual=write('VISUAL_REVIEW.json',{'schema':'independent-transfer-native-visual-review.v1','utc':now,
       'status':'passed_two_actual_final_PPT_rendered_pages','reviewer':'/root/sep29_eval_audit',
       'visual_judgment':'Actual images were viewed by the reviewing agent; this sealer only records already made observations and hashes.',
       'pages':viewed,'source':bind(Path(__file__)),
       'limits':['Actual artifact-tool finalized-PPT round-trip renders were viewed, not a Microsoft PowerPoint session or print proof.',
                 'Raster PNGs are previews only; final SVG/PPT native structure/editable text/shapes are separately verified.',
                 'Visual inspection and programmatic geometry/values are distinct evidence.']})
    source_review=write('SOURCE_REVIEW.json',{'schema':'independent-transfer-native-source-review.v1','utc':now,
       'producer_source':bind(WORK/'build/build_transfer.mjs'),
       'read_scope':'Full17961byte builder source read independently; not imported/executed. Actual artifact checks use independently written stdlib source.',
       'findings':['Exact adopted root/delivery table bindings; only small adopted summaries/seed/contrast tables are read by the builder.',
                   'Train/eval dataset direction differs explicitly from retrieval query/gallery direction and target altitude.',
                   'Both mean and sample SD are scaled100; R@1/mAP percentages and MRR scaledrank units are distinct.',
                   'Original adopted means/sampleSD are used directly, without re-estimation, hidden pooling, CI or significance claims.',
                   'All22 task-variant groups and66 metriccells are rendered, including smallstreet/zeroSD and Full-negative results.',
                   'Native PPT objects and SVG text/line/circle/rect mirror each other; physicalwidth181.9mm and actual minfont8pt.',
                   'Complete small summary and seedCSV rows plus scientific limits are in speaker notes; no raw science input read.',
                   'Caption mAP/MRR signs agree with the adopted contrast rows:10negative/one street positive; all11 R1 negative.'],
       'limits':['Static source read does not by itself establish artifact correctness; ARTIFACT_REVIEW verifies actual files.',
                 'Root-adopted aggregation and upstream scientific verification limits remain inherited.'],
       'sealing_source':bind(Path(__file__))})
    limits=[
       'These figures illustrate the existing root-adopted T3 descriptive results, not a new scientific experiment.',
       'Means and sample SD across equal-weight seeds1/2/3 are inherited from the adopted aggregation. SD denominator2 is not SE, confidence interval or significance.',
       'No pooling across tasks/heights/query counts/train-eval directions. All11 retrievaltasks and22 variantgroups are retained.',
       'R@1 and official trapezoidal mAP fractions times100 are percentages; MRR times100 is scaled MRR, not percentageaccuracy. Mean/SD both scale100.',
       'New checks map the six adopted small CSV/JSON tables to final figures; original metrics/NPZ/weights/cache/images were not read and model/fullranking/AP were not rerun.',
       'Checkpoint/cache/image SHA inheritance, University Visual historical SHAchain gap and non-native-NumPy/original-exit limitations remain as stated in the adopted root.',
       'SVG vector primitives and PPT flat native shapes/text are editable; no Excel chart objects/workbooks/grouping are asserted.',
       'Microsoft PowerPoint was not launched. Visual acceptance covers the two actual final artifact-tool PPT renders, not every office suite/printproof.',
       'No original old2699suite was rerun. New708contract and7956artifact checks each passed their first execution; sealing only rechecks byte stability.',
    ]
    metadata=write('METADATA.json',{'schema':'independent-transfer-native-review-metadata.v1','utc':now,
       'root':bind(ROOT),'snapshots':snapshots,'data_contract':bind(HERE/'DATA_CONTRACT.json'),
       'artifact_review':bind(HERE/'ARTIFACT_REVIEW.json'),'visual_review':visual,'source_review':source_review,
       'scope':artifact['totals'],'executions':{'new_contract_exit_code':0,'new_contract_checks':708,
          'new_artifact_exit_code':0,'new_artifact_checks':7956,'old_suite_rerun':False,'scientific_execution':False,
          'actual_PNG_pages_viewed':2,'PowerPoint_opened':False,'producer_or_live_files_modified':False},'limits':limits})
    readme='''# Independent review of two native T3 transfer figures

Accepted within the explicit limits in DELIVERY.json. Two finalized single-page
PPTs and two SVGs include all 11 target retrieval tasks, 22 task/variant groups
and 66 mean/sample-SD metric cells. Each training→evaluation dataset direction
has its own page. Retrieval direction and SUES altitude labels are distinct.

The 708 new contract checks bound six root-adopted small CSV/JSON tables and their
66 seed-task rows; adopted means/SD were not recomputed. The separate7956 actual
artifact checks independently map values into SVG means/errorbars/text, actual
PPT XML geometry/fonts/shape names and exact CSV rows in notes. There are485
native PPT shapes and144 editable texts, including66 means,66 SD lines and132
caps. Font sizes are physically at least8pt. SVG/PPT contain no raster substitutes
or embedded Excel charts/workbooks. New sources/checks each ran once.

Both final PPT-rendered PNGs were actually viewed separately using view_image
with detail=original, before the artifact checker execution. All labels and SD
intervals are clear; no blocking crop/overlap was seen. Small street values and
zeroSD are visible numerically. This is not an Office-app or printed-proof test.
The two exact preview bytes, reviewed builder and reports are sealed here.

R@1 and official trapezoidal mAP are percentages after ×100; MRR×100 is scaled
MRR. SD is sampleSD across seeds1/2/3, not CI/SE/significance. Nothing is pooled
across tasks, directions or heights. All Full-negative and smallstreet results
remain. Original checkpoint/cache/image inheritance and historical evidence
gaps remain. No original metrics,NPZ,weights,cache,images,model or scientific
suite were read/run again. The producer builder was read; neither the builder
nor its checker was executed by this reviewer. Original sources/live state/
HANDOFF/automation were untouched.
'''
    with (HERE/'README.md').open('x',encoding='utf-8') as stream:stream.write(readme)
    delivery=write('DELIVERY.json',{'schema':'independent-transfer-native-review-delivery.v1','utc':now,
       'accepted_with_stated_limits':True,'metadata':metadata,'readme':bind(HERE/'README.md'),
       'data_contract':bind(HERE/'DATA_CONTRACT.json'),'artifact_review':bind(HERE/'ARTIFACT_REVIEW.json'),
       'visual_review':visual,'source_review':source_review,
       'sources':[bind(HERE/name) for name in ('derive_figure_contract.py','review_artifacts.py','seal_review.py')],
       'artifact_bindings':artifact['bindings'],'limits':limits})
    print(json.dumps({'delivery':delivery,'metadata':metadata,'visual_review':visual,'source_review':source_review},ensure_ascii=False))

if __name__=='__main__':main()
