"""Read NPY headers only in exactly two robustness NPZ samples; stdlib only."""
import ast, hashlib, json, struct, zipfile
from pathlib import Path
from datetime import datetime, timezone
HERE=Path(__file__).parent
ROOT=Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\runs\formal_robustness\university1652\visual\seed_1')
SAMPLES=('clean/per_query_arrays/university1652_drone_to_satellite_per_query.npz','conditions/gaussian_noise/severity_01/per_query_arrays/university1652_drone_to_satellite_per_query.npz')
observations=[]
for relative in SAMPLES:
    p=ROOT/relative
    rows=[]
    with zipfile.ZipFile(p) as archive:
        names=archive.namelist()
        assert len(names)==len(set(names)) and all(n.endswith('.npy') and '/' not in n for n in names)
        for info in archive.infolist():
            with archive.open(info) as stream:
                magic=stream.read(6)
                assert magic==b'\x93NUMPY'
                version=tuple(stream.read(2))
                assert version in ((1,0),(2,0))
                width=2 if version==(1,0) else 4
                size=struct.unpack('<H' if width==2 else '<I',stream.read(width))[0]
                header_bytes=stream.read(size)
                header=ast.literal_eval(header_bytes.decode('latin1').strip())
                consumed=6+2+width+size
            assert header['shape']==(37855,) and header['fortran_order'] is False
            rows.append(dict(name=info.filename,version=list(version),descr=header['descr'],fortran_order=header['fortran_order'],shape=list(header['shape']),header_bytes_consumed=consumed,npy_total_bytes=info.file_size,array_body_requested=False))
    observations.append(dict(path=str(p),member_count=len(rows),arrays=rows))
assert [r['member_count'] for r in observations]==[10,18]
report=dict(schema='lgm.robustness-two-sample-npz-header-review.v1',created_utc=datetime.now(timezone.utc).isoformat(),scope='University visual seed1: clean and gaussian_noise severity01, drone_to_satellite only',npz_files_sampled=2,full_93_npz_traversal=False,scientific_imports=False,array_values_examined=False,checkpoint_or_cache_or_image_read=False,observations=observations,decoder_findings=[
'All sampled arrays are one-dimensional non-Fortran NPY1.0. Existing T3 header handling and Unicode/f4/i8/bool decoders support them except signed |i1.',
'Add |i1 as struct format b, byte width 1, dtype.kind i. Do not decode as unsigned B or Boolean: correctness transition needs -1,0,+1 semantics.',
'The exact clean schema has 10 arrays including margin and first_positive_rank_zero_based; corrupted schema has 18 arrays including clean_margin. Do not reuse the T3 nine-array validator schema.',
'Original robustness _metrics_issues invokes np.isfinite on scalar rates. A reused T3 facade must add scalar finite->bool support alongside vector finite->Vec.',
'If reproducing stored corruption-minus-clean AP/RR deltas, preserve float32 output rounding after float32 subtraction. Correctness transition is signed int8 subtraction. These are implementation requirements, not verified array-value conclusions from headers.',
'Continue to reject object, unknown, multidimensional or unsupported endian types unless deliberately added. Header review alone does not establish numeric values, semantic agreement or full artifact integrity.'
],source=dict(path=str(Path(__file__)),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
p=HERE/'TWO_SAMPLE_NPZ_SCHEMA_REVIEW.json'
with p.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
print(json.dumps(dict(report=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source=report['source'],sampled_npz=2),ensure_ascii=True))
