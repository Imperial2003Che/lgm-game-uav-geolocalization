"""Read only three final PDF pages for pagination geometry; no rendering or compilation."""
from pathlib import Path
import json
import fitz

DOC = Path("C:/OneDrive/文档/LGM-GAME/outputs/paper_evidence_rebuild_20260914/manuscript_camp_dac_context_20260930_1948/manuscript/main.pdf")
OUT = Path("C:/OneDrive/文档/LGM-GAME/outputs/paper_evidence_rebuild_20260914/execution/manuscript_reference_layout_diagnosis_20260930_2130")
OUT.mkdir(exist_ok=True)
pages = []
with fitz.open(DOC) as document:
    for index in range(max(0, len(document)-3), len(document)):
        page = document[index]
        spans = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    spans.append({"text": span["text"], "bbox": list(span["bbox"]), "font": span["font"], "size": span["size"]})
        pages.append({"physical_page": index+1, "page_rect": list(page.rect), "actual_text": page.get_text("text"), "text_spans": spans})
    result = {"schema": "finite-tail-PDF-layout-geometry-read.v1", "source": str(DOC), "page_count": len(document),
              "physical_pages_read": [p["physical_page"] for p in pages], "whole_PDF_hash": False,
              "render_or_compile": False, "pages": pages}
(OUT / "TAIL_PDF_GEOMETRY.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))

