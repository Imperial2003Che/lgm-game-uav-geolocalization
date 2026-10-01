"""Finite local PDF page reading/rendering only; no scientific source import or PDF hash."""
from pathlib import Path
import csv
import io
import json
import fitz

BASE = Path("C:/OneDrive/文档/LGM-GAME/outputs/paper_evidence_rebuild_20260914/execution")
SAVED = BASE / "citation_camp_dac_review_20260930_0509"
OUT = BASE / "camp_dac_reported_values_review_20260930_2032"
OUT.mkdir(exist_ok=True)
rows = list(csv.DictReader(io.StringIO((SAVED / "AUTHOR_REPORTED_ROWS.csv").read_text(encoding="utf-8-sig"))))
page_specs = sorted({(r["method"], int(r["physical_pdf_page"])) for r in rows})
pages = []
for method in ("CAMP", "DAC"):
    pdf_path = SAVED / (method.lower() + ".pdf")
    with fitz.open(pdf_path) as doc:
        for method_spec, physical_page in page_specs:
            if method_spec != method:
                continue
            page = doc[physical_page - 1]
            png_path = OUT / (method.lower() + "_p" + str(physical_page) + ".png")
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pixmap.save(png_path)
            pages.append({
                "method": method, "pdf_path": str(pdf_path), "physical_pdf_page": physical_page,
                "document_page_count": len(doc), "PDF_file_size_only": pdf_path.stat().st_size,
                "PDF_hash_not_read_or_computed": True, "page_rect": list(page.rect),
                "render": {"path": str(png_path), "bytes": png_path.stat().st_size, "width": pixmap.width, "height": pixmap.height, "scale": 2},
                "actual_page_text": page.get_text("text", sort=False)
            })
result = {"schema": "camp-dac-finite-actual-PDF-page-read.v1",
          "saved_CSV_rows": len(rows), "saved_numeric_cells": len(rows) * 2,
          "requested_unique_pages": len(page_specs), "rendered_pages": len(pages),
          "PDF_full_hash_operations": 0, "scientific_execution": False,
          "fitz_version": fitz.VersionBind, "pages": pages}
(OUT / "PDF_PAGE_READ.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))

