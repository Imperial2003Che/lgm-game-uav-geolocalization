"""Bind the new requirements research; no journal submission or scientific action."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE = Path(__file__).resolve().parent
pins = {
    'REQUIREMENTS_REVIEW_zh.md': 'db9fafab3365e33dbb64afff447805b399b6b91f9623f4395f17dda79f4cc9cf',
    'WEB_ACCESS.json': 'baa15dcba8f14155b0bb53af0815aa7b71ff9d7ec7ee4d7ae52351128fc7850f',
    'LOCAL_INPUTS.json': '69b476fb9fb4ab1fb7eab58bedf4593e12d3c03c73c69a99dd5f0881b301dad3',
    'DELIVERY.json': 'c35070ca2b64e25f679b47a288a53156af7ee167e084efe398065e5db7a39a4a',
}
bindings = []
for name, sha in pins.items():
    p = HERE / name
    raw = p.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha, name
    bindings.append(dict(path=str(p), bytes=len(raw), sha256=sha))
delivery = json.loads((HERE / 'DELIVERY.json').read_bytes())
for row in delivery['files']:
    item = next(x for x in bindings if Path(x['path']).name == row['name'])
    assert item['bytes'] == row['bytes'] and item['sha256'] == row['sha256']
local = json.loads((HERE / 'LOCAL_INPUTS.json').read_bytes())
assert local['inherited_manuscript']['page_counts'] == [16, 6]
assert local['inherited_manuscript']['submission_ready'] is False
access = json.loads((HERE / 'WEB_ACCESS.json').read_bytes())
mdpi = next(x for x in access['sources'] if x['id'] == 'remote_apc')
assert mdpi['live_fee_confirmation'] is False and mdpi['current_confirmed_apc'] is None
source_raw = Path(__file__).read_bytes()
report = {
    'schema': 'submission-requirements-root-research-adoption.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Current official-source requirements research for later final advice. Not final venue selection or submission-ready acceptance.',
    'research_adopted': True,
    'bindings': bindings,
    'root_source': dict(path=str(Path(__file__).resolve()), bytes=len(source_raw), sha256=hashlib.sha256(source_raw).hexdigest()),
    'root_read_scope': 'Complete new research report, WEB_ACCESS, LOCAL_INPUTS and DELIVERY; prior manuscript adoption scope inherited, no PDFs/ZIPs/scientific assets reread.',
    'root_web_confirmation': {
        'tgrs': {
            'url': 'https://www.grss-ieee.org/publications/author-resources/tgrs-information-for-authors/',
            'direct_read_success': True,
            'new_submissions_2026_overlength_from_printed_page': 11,
            'overlength_usd_per_page': 230,
            'grss_member_overlength_usd_per_page': 200,
            'optional_OA_APC_2026_usd': 2800,
            'traditional_route_OA_APC': False,
            'additional_optional_sustaining_charge': 'Page also requests an optional US$110 per printed page for the first eleven pages. This is separate from mandatory overlength and optional OA charges.',
            'discounts': 'Page lists IEEE 5% and society 20% APC discounts, not combined; eligibility and institutional arrangements were not checked for this user.',
            'hard_page_maximum_confirmed': False,
        },
        'jstars': 'Agent records successful direct journal-page access; root repeat direct request was restricted. Root does not claim its own successful direct JSTARS access.',
        'remote_sensing': 'Agent used official indexed content with approximately two-month crawl age after direct failure. Root direct instructions request also returned 429; live APC and live policy confirmation remain open.',
    },
    'unresolved': ['Venue-format final page count', 'JSTARS hard maximum and overlength details', 'Journal-specific supplement page/file limits and billing', 'Live MDPI requirements and APC', 'Final scientific completion and venue-fit decision'],
    'manuscript_modified': False, 'overleaf_modified': False, 'submitted': False,
    'purchased': False, 'scientific_execution': False, 'final_recommendation': False,
}
out = HERE / 'ROOT_REQUIREMENTS_RESEARCH_ADOPTION.json'
with out.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(out), bytes=out.stat().st_size, sha256=hashlib.sha256(out.read_bytes()).hexdigest()), ensure_ascii=True))
