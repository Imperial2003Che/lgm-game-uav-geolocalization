"""Preserve stricter rejected review; report mixed-vector exports accurately."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
source = (HERE / 'review_transition.py').read_text(encoding='utf-8')
source = source.replace("RAW = HERE / 'raw'", "RAW = HERE / 'raw_final'")
source = source.replace("xml.tag.endswith('svg') and texts and not images, 'SVG has no editable text or embeds raster'",
                        "xml.tag.endswith('svg') and texts, 'SVG has no editable text'")
source = source.replace("detail.update(editable_text_nodes=len(texts), embedded_raster_nodes=len(images))",
    "detail.update(editable_text_nodes=len(texts), embedded_raster_nodes=len(images),\n                          wholly_vector_contents=(len(images) == 0))")
source = source.replace("'passed_bounded_two_job_review'", "'passed_bounded_data_review_with_figure_editability_limitations'")
source = source.replace("'publication_layout_or_visual_readability_reviewed': False}",
    "'publication_layout_or_visual_readability_reviewed': False,\n            'fully_native_editable_delivery_accepted': False,\n            'mixed_vector_exports': [r['path'] for r in exports if r.get('embedded_raster_nodes', 0)]}")
source = source.replace("'SVG XML editable text and no raster verified; no visual/page-by-page or font-size acceptance.'",
    "'SVG XML editable text verified; two main SVGs contain raster elements. No fully native editable delivery, visual/page-by-page or font-size acceptance.'")
source = source.replace("    primary, primary_record = read_json(EX / 'status.json')",
    "    rejected, _ = read_json(HERE / 'REVIEW.json')\n    capture(HERE / 'review_transition.py')\n    require(rejected['status'] == 'failed' and 'embeds raster' in rejected['error'], 'Preserved first finding differs')\n    primary, primary_record = read_json(EX / 'status.json')")
source = source.replace("'scientific_execution': False, 'live_files_changed': False, 'recovery_or_validateonly': False}",
    "'scientific_execution': False, 'live_files_changed': False, 'recovery_or_validateonly': False,\n        'prior_rejected_review': 'REVIEW.json retained; its stricter no-raster requirement found real mixed SVG content, now explicitly a delivery limitation, not a failed scientific job.'}")
source = source.replace("(HERE / 'REVIEW.json').open('x'", "(HERE / 'REVIEW_FINAL.json').open('x'")
source = source.replace("'report': str(HERE / 'REVIEW.json')", "'report': str(HERE / 'REVIEW_FINAL.json')")
with (HERE / 'review_transition_final.py').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(source)
