"""Seal only three bibliographic field comparisons; no network or manuscript writes."""
from pathlib import Path
from datetime import datetime, timezone
import base64, csv, hashlib, io, json, os, re

OUT = Path(r'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914')
HERE = OUT / 'execution' / 'citation_iclr_open_fields_20260930_1212'
REFS = OUT / 'manuscript_citation_revision_20260930_0520' / 'manuscript' / 'refs.bib'
PRIOR = OUT / 'execution' / 'citation_foundations_review_20260930_0405'
KEYS = ['adamw2019', 'sgdr2017', 'mixedprecision2018']
NOW = datetime.now(timezone.utc).isoformat()
INPUTS = []

def read_small(path, cap=96 * 1024):
    size = path.stat().st_size
    if not 0 <= size <= cap:
        raise RuntimeError(f'input exceeds named small bound: {path}')
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    if len(raw) != size or len(raw) > cap:
        raise RuntimeError(f'input size changed or exceeds bound: {path}')
    desc = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    INPUTS.append(desc)
    return raw, desc

def descriptor(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def create_new(name, raw, cap=256 * 1024):
    if not isinstance(raw, bytes) or len(raw) > cap:
        raise RuntimeError(f'output size rejected before CreateNew: {name}')
    path = HERE / name
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return descriptor(path, raw)

def json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

refs_raw, refs_desc = read_small(REFS)
prior_raw, prior_desc = read_small(PRIOR / 'FOUNDATION_CITATION_REVIEW.json')
if prior_desc['sha256'] != '1fc0add81a24d08395cfe99ba8aa653e5b1fdd0842c55b086ecc63d89be4a1ca':
    raise RuntimeError('exact prior field review binding changed')
prior_review_raw, prior_review_desc = read_small(PRIOR / 'REVIEW.md')
direct_raw, direct_desc = read_small(HERE / 'DIRECT_PUBLIC_METADATA_ACCESS.json')
direct = json.loads(direct_raw)
fetch_source_raw, fetch_source_desc = read_small(HERE / 'fetch_public_metadata.py')
self_raw, self_desc = read_small(Path(__file__))
prior = json.loads(prior_raw)
prior_entries = {item['key']: item for item in prior['entries'] if item['key'] in KEYS}
if sorted(prior_entries) != sorted(KEYS):
    raise RuntimeError('exactly three requested prior entries required')

sources = [
 {'id': 'iclr2017_archive', 'url': 'https://iclr.cc/archive/www/2017.html', 'source_role': 'official conference', 'access': 'direct_web_text', 'tool_clock_after_read_utc': '2026-09-30T11:25:09Z', 'observed_lines': [20, 60, 62], 'observed_field_facts': {'conference_ordinal': 5, 'conference_name': 'International Conference on Learning Representations', 'conference_track_link_host': 'OpenReview'}, 'scope': 'Official ordinal and conference-track link; not publisher-role proof.'},
 {'id': 'iclr2018_official', 'url': 'https://iclr.cc/Conferences/2018', 'source_role': 'official conference', 'access': 'direct_web_text', 'tool_clock_after_read_utc': '2026-09-30T11:25:09Z', 'observed_lines': [107, 109], 'observed_field_facts': {'conference_ordinal': 6, 'conference_name': 'International Conference on Learning Representations'}, 'scope': 'Official ordinal/name only; no paper author metadata inferred from conference homepage.'},
 {'id': 'iclr2019_official', 'url': 'https://iclr.cc/Conferences/2019', 'source_role': 'official conference', 'access': 'direct_web_text', 'tool_clock_after_read_utc': '2026-09-30T11:25:09Z', 'observed_lines': [139], 'observed_field_facts': {'conference_ordinal': 7, 'conference_name': 'International Conference on Learning Representations'}, 'scope': 'Official ordinal/name only.'},
 {'id': 'adamw_author_institution', 'url': 'https://ellis.cs.uni-freiburg.de/research/key-publications', 'source_role': 'author institution publication list', 'access': 'direct_web_text', 'tool_clock_after_read_utc': '2026-09-30T11:25:09Z', 'observed_lines': [42], 'observed_field_facts': {'authors_in_order': ['Ilya Loshchilov', 'Frank Hutter'], 'venue': 'International Conference on Learning Representations (ICLR)', 'publication_context': '2019 conference publication'}, 'scope': 'Complete two-author order and formal conference association; no publisher declaration.'},
 {'id': 'sgdr_author_submitted_metadata', 'url': 'https://arxiv.org/abs/1608.03983', 'source_role': 'author-submitted primary metadata, current v5', 'access': 'direct_web_text', 'tool_clock_after_read_utc': '2026-09-30T11:25:43Z', 'observed_lines': [8, 11, 18, 25], 'observed_field_facts': {'authors_in_order': ['Ilya Loshchilov', 'Frank Hutter'], 'publication_context': 'Author metadata identifies an ICLR 2017 conference paper.'}, 'scope': 'Author order and author-stated conference-paper status; not current OpenReview Cite export.'},
 {'id': 'mixed_author_submitted_metadata', 'url': 'https://arxiv.org/abs/1710.03740', 'source_role': 'author-submitted primary metadata, current v3', 'access': 'direct_web_text', 'tool_clock_after_read_utc': '2026-09-30T11:25:51Z', 'observed_lines': [8, 11, 19, 26], 'observed_field_facts': {'authors_in_order': ['Paulius Micikevicius', 'Sharan Narang', 'Jonah Alben', 'Gregory Diamos', 'Erich Elsen', 'David Garcia', 'Boris Ginsburg', 'Michael Houston', 'Oleksii Kuchaiev', 'Ganesh Venkatesh', 'Hao Wu'], 'publication_context': 'Author metadata identifies publication as an ICLR 2018 conference paper.'}, 'scope': 'Complete eleven-author linear order and author-stated final conference association. Affiliation-grouped PDF blocks do not supersede this order. No preprint-year substitution or automatic preprint DOI addition.'},
]
source_map = {s['id']: s for s in sources}
paper_ids = [('adamw2019', 'Bkg6RiCqY7'), ('sgdr2017', 'Skq89Scxx'), ('mixedprecision2018', 'r1gs9JgRZ')]
blocked = []
for key, paper_id in paper_ids:
    blocked.extend([
      {'key': key, 'url': f'https://openreview.net/forum?id={paper_id}', 'method': 'web direct open', 'observed_response': 'challenge redirect', 'access_window_utc': '2026-09-30T11:16:48Z to 2026-09-30T11:18:08Z', 'metadata_obtained': False},
      {'key': key, 'url': f'https://openreview.net/pdf?id={paper_id}', 'method': 'web direct open', 'observed_response': 'challenge redirect', 'access_window_utc': '2026-09-30T11:18:08Z', 'metadata_obtained': False},
      {'key': key, 'url': f'https://api.openreview.net/notes?id={paper_id}', 'method': 'web direct open', 'observed_response': 'web Internal Error; HTTP status not returned by this tool', 'access_window_utc': '2026-09-30T11:17:26Z', 'metadata_obtained': False},
    ])
for year in [2017, 2018, 2019]:
    blocked.append({'url': f'https://openreview.net/group?id=ICLR.cc/{year}/' + ('conference' if year == 2017 else 'Conference'), 'method': 'web direct open then expanded text', 'observed_response': 'Loading framework and footer only', 'access_window_utc': '2026-09-30T11:18:08Z to 2026-09-30T11:20:22Z', 'paper_or_ordinal_metadata_obtained': False})
access = {
 'schema': 'lgm.three-iclr-open-field-primary-access.v1', 'created_utc': NOW,
 'method': 'Independent AI reads of primary web tool text plus once-only public urllib metadata access. This file is a derived access/fact record, not a byte capture of complete remote HTML/PDF. Web clock values are post-call or access windows; exact urllib start/end times are separately preserved.',
 'successful_sources': sources, 'blocked_or_content_incomplete_access': blocked,
 'direct_public_metadata_access': direct_desc,
 'direct_urllib_results': direct['results'],
 'indexed_only_auxiliary_observation': {'urls': ['https://openreview.net/pdf?id=Skq89Scxx', 'https://openreview.net/pdf?id=r1gs9JgRZ'], 'facts': 'Official PDF search index showed conference-publication headings and author blocks; direct PDF access did not succeed. These snippets are not needed for the final matches, which use the direct author primary metadata and direct conference sites.', 'mixed_layout_note': 'The indexed first page groups Baidu/NVIDIA affiliation blocks and marks equal contribution; block reading order is not a proved correction to the linear bibliographic list.'},
 'excluded_evidence': 'Secondary papers citing these entries, DBLP citation exports, and incomplete author blog reference lists were not used as original formal metadata authority.',
 'no_challenge_bypass_or_credentials': True,
 'publisher_role_established': False,
}

config = {
 'adamw2019': ('adamw_author_institution', 'iclr2019_official', 7),
 'sgdr2017': ('sgdr_author_submitted_metadata', 'iclr2017_archive', 5),
 'mixedprecision2018': ('mixed_author_submitted_metadata', 'iclr2018_official', 6),
}
blocks, entries, rows = [], [], []
for key in KEYS:
    matches = list(re.finditer(rb'(?m)^@inproceedings\{' + key.encode('ascii') + rb',\r?$[\s\S]*?^\}', refs_raw))
    if len(matches) != 1:
        raise RuntimeError('one actual scoped BibTeX block required: ' + key)
    match = matches[0]
    raw = match.group()
    text = raw.decode('utf-8')
    fields = {}
    for field in ['author', 'booktitle', 'publisher']:
        found = re.search(r'(?ms)^\s*' + field + r'\s*=\s*\{(.*?)\}\s*,?\s*$', text)
        if found is None:
            raise RuntimeError('missing exact scoped field: ' + key + '/' + field)
        fields[field] = {'raw_value': found.group(1), 'normalized_value': re.sub(r'\s+', ' ', found.group(1)).strip()}
    author_id, conference_id, ordinal = config[key]
    original_authors = fields['author']['normalized_value'].split(' and ')
    observed_authors = source_map[author_id]['observed_field_facts']['authors_in_order']
    if original_authors != observed_authors:
        raise RuntimeError('a current author difference requires explicit new review, not silent correction')
    if fields['booktitle']['normalized_value'] != f'{ordinal}th International Conference on Learning Representations':
        raise RuntimeError('current booktitle different from observed exact ordinal/name')
    if fields['publisher']['normalized_value'] != 'OpenReview.net':
        raise RuntimeError('unexpected current publisher field value')
    blocks.append({'key': key, 'start_byte_offset': match.start(), 'end_byte_offset_exclusive': match.end(), 'start_line_1based': refs_raw[:match.start()].count(b'\n') + 1, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'raw_block_utf8': text, 'raw_block_base64': base64.b64encode(raw).decode('ascii'), 'line_endings': {'CRLF': raw.count(b'\r\n'), 'LF_not_CRLF': raw.count(b'\n') - raw.count(b'\r\n')}})
    current_fields = {
      'author': {'local': fields['author'], 'status': 'complete_author_order_match_in_direct_primary_metadata', 'authors_count': len(original_authors), 'sources': [author_id], 'confirmed_difference': False},
      'booktitle': {'local': fields['booktitle'], 'status': 'conference_name_and_ordinal_match_direct_official_site_with_primary_paper_association', 'sources': [conference_id, author_id], 'confirmed_difference': False},
      'publication_type': {'local_value': '@inproceedings', 'status': 'conference_paper_context_supported_by_direct_primary_publication_metadata', 'sources': [author_id], 'literal_OpenReview_Cite_export_read': False, 'confirmed_difference': False},
      'publisher': {'local': fields['publisher'], 'status': 'publisher_role_unknown_not_separately_established', 'sources': [], 'hosting_consistency_does_not_prove_publisher_role': True, 'confirmed_difference': False},
    }
    previous = {field: prior_entries[key]['fields'].get(field) for field in ['author', 'booktitle', 'publisher']}
    entries.append({'key': key, 'current_fields': current_fields, 'prior_requested_fields': previous, 'OpenReview_formal_Cite_and_venue_id': {'status': 'not_obtained_current_challenge_and_API_failures', 'no_fabricated_export': True}, 'known_title_and_year_reverification': False, 'missing_DOI_pages_volume_number_addition_proposed': False, 'confirmed_correction_required': False})
    for field, finding in current_fields.items():
        local = finding.get('local', {})
        rows.append({'key': key, 'field': field, 'actual_local_value': local.get('normalized_value', finding.get('local_value')), 'status': finding['status'], 'primary_urls': ' | '.join(source_map[x]['url'] for x in finding['sources']), 'confirmed_difference': 'false'})

assert len(rows) == 12 and len(blocks) == 3
access_out = create_new('PRIMARY_ACCESS.json', json_bytes(access))
blocks_out = create_new('LOCAL_SCOPED_BIBTEX_BLOCKS.json', json_bytes({'schema': 'lgm.three-iclr-exact-local-bibtex-blocks.v1', 'current_refs': refs_desc, 'three_blocks': blocks, 'scope': 'Only actual three blocks copied and bound; no changes to original bytes.'}))
table_stream = io.StringIO(newline='')
writer = csv.DictWriter(table_stream, fieldnames=['key', 'field', 'actual_local_value', 'status', 'primary_urls', 'confirmed_difference'])
writer.writeheader()
writer.writerows(rows)
csv_out = create_new('FIELD_TABLE.csv', table_stream.getvalue().encode('utf-8'))
review = {'schema': 'lgm.three-iclr-open-field-review.v1', 'created_utc': NOW, 'reviewer': 'Independent AI sub-agent /root/b1_integration_scope_0912; no human review', 'scope_keys': KEYS, 'scope_field_rows': len(rows), 'local_input_bindings': INPUTS, 'primary_access_record': access_out, 'exact_local_blocks': blocks_out, 'field_table': csv_out, 'entries': entries, 'result': {'confirmed_field_errors': 0, 'complete_author_lists_match_primary_evidence': 3, 'conference_ordinal_gaps_closed': 3, 'conference_publication_context_supported': 3, 'publisher_role_unknown': 3, 'all_fields_verified': False, 'all_bibliography_verified': False, 'scientific_validation': False, 'manuscript_modified': False, 'new_manuscript_delivered': False}, 'method_limits': ['Direct arXiv author metadata is author submitted and version explicit; it is not a current OpenReview Cite/venue-ID export.', 'The conference homepage proves ordinal/name, not a particular paper association by itself; author publication metadata supplies the association.', 'OpenReview hosting does not establish its bibliographic publisher role. Access failure does not prove the current publisher field wrong.', 'No formulas, optimizer code, AMP precision, scientific outcomes, old suite, statistics, model, weights, NPZ/cache/image or large ZIP were accessed or executed.', 'Previously checked title/year values are inherited, not re-certified; absent DOI/page/volume/number fields are not filled.']}
review_out = create_new('FIELD_REVIEW.json', json_bytes(review))
markdown = f'''# 三个 ICLR 条目开放字段局部审核

本轮只核当前 refs.bib 的 adamw2019、sgdr2017、mixedprecision2018 完整作者顺序、会议序号/正式 venue 和 conference-publication 类型。结论：未发现确证字段错误；三个作者列表与直接主源一致，三个会议序号缺口已关闭。OpenReview.net 的 bibliographic publisher 角色仍未单独证明；OpenReview 当前 Cite export/venue-ID 均未取得。没有修改 Bib、TeX、PDF、ZIP 或 Overleaf，没有新稿交付。

当前本地原文件：{refs_desc['bytes']} bytes，SHA256 {refs_desc['sha256']}。LOCAL_SCOPED_BIBTEX_BLOCKS.json 保存三段实际原字节的 UTF-8/base64、byte offset、行号、行尾和各自 SHA；不是从旧指针重建当前原文。FIELD_TABLE.csv 的 12 行为每条 author、booktitle、publication_type、publisher 四项，不代表 12 个独立科学检查。

| key | 完整作者顺序 | 当前正式会议字段 | publication 类型 | publisher |
|---|---|---|---|---|
| adamw2019 | 两人顺序与作者机构正式 publication list 相同 | 7th；官网 Seventh 与 ICLR publication list 联合支持 | conference context 支持 @inproceedings | OpenReview.net 角色 unknown |
| sgdr2017 | 两人顺序与作者提交的 arXiv v5 metadata 相同 | 5th；官网 archive 与作者 conference-paper metadata 联合支持 | conference context 支持 @inproceedings | OpenReview.net 角色 unknown |
| mixedprecision2018 | 十一人线性顺序与作者提交的 arXiv v3 metadata 相同 | 6th；官网 Sixth 与作者正式发表说明联合支持 | conference context 支持 @inproceedings | OpenReview.net 角色 unknown |

主源与实际读取范围：

- [ICLR 2017 官方 archive](https://iclr.cc/archive/www/2017.html)：直接正文 line 20 给 5th，会议 track 链接只证 hosting。
- [ICLR 2018 官网](https://iclr.cc/Conferences/2018)：直接正文 lines 107/109 给 Sixth。
- [ICLR 2019 官网](https://iclr.cc/Conferences/2019)：直接正文 line 139 给 Seventh。
- [Freiburg ELLIS 作者机构 Key Publications](https://ellis.cs.uni-freiburg.de/research/key-publications)：直接正文 line 42 给 AdamW 双作者顺序和 ICLR 正式 conference association。
- [SGDR 作者提交元数据](https://arxiv.org/abs/1608.03983)：直接正文 line 11 双作者顺序、line 18 conference-paper status；使用当前 v5，不把 preprint 年份替换正式发表字段。
- [Mixed Precision 作者提交元数据](https://arxiv.org/abs/1710.03740)：直接正文 line 11 给完整十一人顺序，line 19 给 ICLR conference publication status；使用当前 v3。按机构分组的 PDF 作者块不是应改线性顺序的证据。

访问受限分开记录：三个 paper forum 和 PDF 直接请求返回 challenge；三个 public metadata API 在 web 工具返回 Internal Error，普通 urllib 一次读取各为 HTTP 403，精确时刻在 DIRECT_PUBLIC_METADATA_ACCESS.json。OpenReview group 直接正文展开后只有 Loading 框架，不能据此声称读到了会议 metadata；会议序号采用以上 ICLR 官网直接正文。这纠正先前进度消息把 group 可直接读取误当 ordinal 内容已取得的措辞。官方 PDF 索引只作为辅助访问观察，最终作者/发表判断不依赖这些索引。没有绕过 challenge 或使用凭据。

publisher unknown 不等于 publisher 错误，也不授权删除或新增字段；没有官方明确 publisher 宣告时不从域名或托管平台推出该角色。未读取到的 OpenReview Cite export/venue ID 不补造。未重新核 title/year、公式/统计或任何科学实现，也未补 DOI/pages/volume/number。

本报告是独立 AI 的局部文献元数据读审，非人工审稿、全部 bibliography 审核、科学验收或 root adoption。保留 prior FOUNDATION_CITATION_REVIEW 的其余限制；本轮只关闭上述有限缺口。远程访问记录为工具返回文本的派生事实记录，不称完整网页/PDF 字节封存。
'''
markdown_out = create_new('REVIEW.md', markdown.encode('utf-8'))
payload_files = [self_desc, fetch_source_desc, direct_desc, access_out, blocks_out, csv_out, review_out, markdown_out]
delivery = {'schema': 'lgm.three-iclr-open-field-delivery.v1', 'created_utc': NOW, 'reviewer': review['reviewer'], 'input_scope': 'Three current BibTeX entries and small prior field/access evidence only', 'files': payload_files, 'local_input_bindings': INPUTS, 'new_review_field_rows': 12, 'confirmed_corrections': 0, 'changes_to_existing_manuscript_or_sources': False, 'all_bibliography_or_science_validation': False, 'root_adoption_pending': True, 'output_safety': 'All output bytes bounded before exclusive xb creation and fsync; DELIVERY does not bind itself.'}
delivery_out = create_new('DELIVERY.json', json_bytes(delivery))
print(json.dumps({'report': review_out, 'review': markdown_out, 'delivery': delivery_out, 'refs': refs_desc, 'result': review['result'], 'new_field_rows': len(rows), 'local_input_bindings': len(INPUTS)}, ensure_ascii=False))
