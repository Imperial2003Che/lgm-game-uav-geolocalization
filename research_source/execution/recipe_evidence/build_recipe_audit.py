"""Assemble source-grounded CAMP/DAC recipes without importing model code."""
from pathlib import Path
import ast,datetime,hashlib,json,re
import fitz
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'execution'
EV=OUT/'recipe_evidence'
SPECS={
 'CAMP':{'repo':'Mabel0403/CAMP','commit':'b04a9c856711770ed7a72ebf851838329c5e5b8e','directory':'Mabel0403__CAMP__b04a9c856711','paper':'https://www.skyearth.org/publication/papers/2024_acvglmucampap.pdf','doi':'10.1109/TGRS.2024.3448499'},
 'DAC':{'repo':'SummerpanKing/DAC','commit':'5612a79c3928d8a71939e4e761bb352f805cb51b','directory':'SummerpanKing__DAC__5612a79c3928','paper':'https://skyearth.org/publication/papers/2024_ecvglwdasc.pdf','doi':'10.1109/TCSVT.2024.3443510'}
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def evidence(method,section='IV-B',page=7,printed=None):
    return {'type':'paper','url':SPECS[method]['paper']+'#page='+str(page),'doi':SPECS[method]['doi'],'pdf_page_1_based':page,'section':section,'printed_page':printed}
def comment(method,id):
    obj=json.loads((EV/(method+'_public_issues.json')).read_text(encoding='utf-8'))
    for issue in obj['issues']:
        for c in issue['comments']:
            if str(id) in c['url']:
                assert c['association']=='OWNER'
                return {'type':'maintainer_comment','url':c['url'],'author':c['author'],'association':c['association'],'created_at':c['created_at'],'api_source':f"https://api.github.com/repos/{SPECS[method]['repo']}/issues/comments/{id}"}
    raise ValueError(id)
def field(value,status,source,note=None):return {'value':value,'status':status,'evidence':source,'note':note}
def codeurl(spec,file,line,end=None):return f"https://github.com/{spec['repo']}/blob/{spec['commit']}/{file}#L{line}"+(f'-L{end}' if end else '')
def findline(lines,needle):return next(i+1 for i,x in enumerate(lines) if needle in x)
result={'audited_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Original papers, fixed official sources, and all public issue threads; no model execution, weight loading, GPU use, manuscript or review-package changes.','recipes':{}}
for method,spec in SPECS.items():
    repo=ROOT/'literature/official_repos/snapshots'/spec['directory']
    paperpath=EV/(method+'_author_copy.pdf')
    docs=fitz.open(paperpath)
    keywords={k:[] for k in ['epoch','warmup','warm-up','checkpoint','pretrained','pre-trained']}
    for i,p in enumerate(docs):
        t=p.get_text().lower().replace('\x00','')
        for k in keywords:
            if k in t:keywords[k].append(i+1)
    r={'paper':dict(url=spec['paper'],doi=spec['doi'],pages=len(docs),sha256=sha(paperpath)),
       'official_repo':dict(url='https://github.com/'+spec['repo'],commit=spec['commit']),
       'full_paper_keyword_pages':keywords,'code':{}}
    for name in ['train_university.py','train_sues200.py']:
        path=repo/name;content=path.read_text(encoding='utf-8');tree=ast.parse(content);defaults={}
        for n in ast.walk(tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument' and n.args and isinstance(n.args[0],ast.Constant):
                flag=n.args[0].value
                if flag in ['--epochs','--model','--handcraft_model','--img_size','--batch_size','--warmup_epochs','--lr','--scheduler','--checkpoint_start','--only_test','--nclasses','--altitude','--seed','--eval_every_n_epoch','--lr_decouple','--lr_blockweights']:
                    default=next((x.value for x in n.keywords if x.arg=='default'),None)
                    defaults[flag]={'value':ast.literal_eval(default),'line':n.lineno,'url':codeurl(spec,name,n.lineno)}
        lines=content.splitlines()
        anchors={}
        for key,needle in [('warmup','warmup_steps ='),('final_checkpoint','weights_end.pth'),('best_checkpoint','if r1_test > best_score'),('training_loop','for epoch in range(1, config.epochs + 1)')]:
            hits=[i+1 for i,x in enumerate(lines) if needle in x and not x.lstrip().startswith('#')]
            anchors[key]={'lines':hits,'urls':[codeurl(spec,name,x) for x in hits]}
        r['code'][name]={'sha256':sha(path),'defaults':defaults,'anchors':anchors,
          'warmup_semantics':'0.1 * total_training_steps' if name=='train_university.py' else '0.1 * steps_per_epoch',
          'checkpoint_behavior':'Evaluate the official test loaders every epoch by default, save each newly best test R@1, and also save weights_end.pth after the training loop.'}
    readme=(repo/'README.md').read_text(encoding='utf-8');r['readme']={'sha256':sha(repo/'README.md'),'url':codeurl(spec,'README.md',7),
        'epoch_override_command_found':False,'training_command_summary':'Names the train entry and only_test=False; supplies no epochs, warmup, batch-size, optimizer, seed or checkpoint-selection override.',
        'argparse_bool_issue':'Both official parsers use type=bool. Passing the nonempty string False activates test mode; omit --only_test for training.'}
    paper=evidence(method,printed='13277' if method=='DAC' else '5637614 / PDF page 7')
    fields={
      'backbone':field('ConvNeXt-Base','paper_confirmed',[paper]),
      'input_size':field([384,384],'paper_confirmed',[paper]),
      'standard_training_batch':field(24,'paper_confirmed',[paper], 'DAC explicitly defines 24 pairs = 24 UAV + 24 satellite = 48 images. CAMP says batch24; paired interpretation is additionally supported by its loader/code.'),
      'optimizer':field('AdamW','paper_confirmed',[paper]),
      'initial_learning_rate':field(0.001,'paper_confirmed',[paper]),
      'scheduler':field('cosine','paper_confirmed',[paper]),
      'weight_decay_and_betas':field(None,'not_specified_in_paper',[paper], 'Main default code path constructs torch.optim.AdamW(model.parameters(),lr=config.lr); resolve the installed library defaults in the execution manifest, do not invent paper values.'),
      'cross_dataset_batch':field(48,'paper_confirmed_scope_specific',[evidence(method,'IV-D',8 if method=='CAMP' else 7,'13277' if method=='DAC' else None)],'University-1652 training -> SUES-200 testing. Paper says batch48; it does not explicitly resolve whether that means 48 pairs or 48 images in this separate paragraph. Do not silently equate it with the standard batch24 recipe.'),
      'training_seed':field(None,'not_specified_in_paper',[paper], 'Official entry defaults to seed1; not a paper declaration of multiple seeds.')}
    if method=='CAMP':
        fields['total_epochs']=field(1,'maintainer_confirmed_after_publication',[comment(method,2805600948)],'The paper does not state total epochs. The owner explicitly explains that one epoch suffices for U-1652 and SUES-200; this supports a one-epoch official-code run, not a guaranteed reproduced score or complete paper/code identity.')
        fields['pretraining']=field('ImageNet-22k ConvNeXt-Base','maintainer_confirmed_after_publication',[comment(method,2522232814)],'Paper IV-B names the backbone but does not identify its pretraining dataset. Fixed custom backbone loads convnext_base_22k_1k_224.pth; record this exact checkpoint separately from the CLI model-name string.')
        fields['warmup']=field('one epoch','paper_code_conflict',[paper], 'University code uses 10% of all steps; SUES code uses 0.1 epoch. With total_epochs=1 both are 0.1 epoch, not the paper one epoch. No public maintainer clarification of the discrepancy was found.')
        fields['checkpoint_selection']=field(None,'paper_not_specified',[paper], 'Official code saves test-best checkpoints and the end checkpoint. No inspected owner reply establishes which selection generated every published CAMP number. A prespecified end checkpoint for our rerun is a declared evaluation choice, not an inferred author rule.')
    else:
        fields['total_epochs']=field(None,'unconfirmed_paper_recipe',[paper], 'Both official entries default to1, but the 11-page paper and all12 public issue threads contain no owner confirmation that this is the complete reported training duration. Do not label an unverified1-epoch run complete paper reproduction.')
        fields['pretraining']=field('ImageNet-22k ConvNeXt-Base','paper_confirmed',[paper], 'Fixed custom backbone loads convnext_base_22k_1k_224.pth; paper does not specify the additional1k finetuning stage reflected in that exact filename.')
        fields['warmup']=field('first10% of training','paper_confirmed_with_code_scope_difference',[paper], 'University code computes0.1*total_steps, consistent. SUES code computes0.1*steps_per_epoch; it only equals10% of total when epochs=1. Extending epochs without correcting/logging this changes the paper scheduler.')
        fields['checkpoint_selection']=field('last experimental run, without cross-run averaging or selecting the best run','maintainer_clarification_limited_scope',[comment(method,2889980571)], 'The reply concerns which repeated experiment was reported; it does not establish last-epoch versus test-best checkpoint. Official code stores both. Within-run paper selection remains unspecified.')
        fields['published_weather_checkpoint']=field('README-linked U1652 checkpoint was trained without weather augmentation','maintainer_confirmed',[comment(method,2815293634),comment(method,2819955663)],'The author advises weather training for multi-weather results; satellite weather augmentation should stay disabled. Clean weights cannot be relabelled as the multi-weather-trained model.')
    custom='sample4geo/hand_convnext/ConvNext/backbones/model_convnext.py'
    r['custom_pretraining']={'url':'https://dl.fbaipublicfiles.com/convnext/convnext_base_22k_1k_224.pth',
       'source':codeurl(spec,custom,153,195),'sha256_of_source':sha(repo/custom),
       'note':'Registered custom ConvNeXt-Base has pretrained=True and in_22k=True. The default handcraft branch uses this registered function, not the separate TimmModel CLI string. Check weight compatibility in actual preflight.'}
    r['fields']=fields
    r['launch_policy']='CAMP: author-confirmed one-epoch code recipe may be preflighted and executed with the warmup discrepancy explicitly recorded; do not call the warmup paper-identical. DAC: official pretrained-weight evaluation may proceed after compatibility checks; a new training duration must be explicitly identified as an adapted protocol until independently confirmed.'
    r['issues_read']=len(json.loads((EV/(method+'_public_issues.json')).read_text(encoding='utf-8'))['issues'])
    result['recipes'][method]=r

(OUT/'latest_baseline_recipe_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:{'epochs':v['fields']['total_epochs'],'warmup':v['fields']['warmup'],'issues_read':v['issues_read']} for k,v in result['recipes'].items()},ensure_ascii=True,indent=2))
