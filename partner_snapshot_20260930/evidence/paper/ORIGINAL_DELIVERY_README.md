# LGM-GAME reference-layout working draft, 2026-09-30

This local working draft has a newly compiled 16-page main PDF and the unchanged,
previously adopted six-page supplement. All scientific text, numbers, fonts,
figures and negative-result limitations inherit the adopted 1948 working draft.
It is not the final submission manuscript; pending experiments are still pending.
Overleaf has not been updated, and the previous delivered archives are preserved.

The main bibliography keeps the 44 references and their order. Six current IEEE
journal references with more than six authors display the first author and et al.
The complete author metadata remains in refs.bib. Other references, including
CLIP, Mixed Precision Training and MobileGeo, retain their original author display.
The derived IEEEtran_lgm_display.bst preserves the original copyright and differs
only by a three-line six-key guard. This is an explicit current-key list, not a
general publication classifier. New reference keys need a separate format review.
Include ieee_controls.bib and the derived BST when rebuilding main.tex; the
supplement continues to use the original style. No smaller fonts were introduced.

Installed MiKTeX compiled main.tex with pdflatex-bibtex-pdflatex-pdflatex: all four
commands returned 0, automatic installation and shell escape were disabled.
The final main log has four underfull hbox diagnostics and no overfull or undefined
reference diagnostics. This is not a zero-diagnostic claim. Supplement diagnostics
and the prior independent evidence limitations are inherited, not rerun.

All 16 new main previews were rendered. The first 15 exactly match the saved
adopted-parent PNG hashes and inherit its visual review; the changed last page was
actually inspected at original resolution by the root AI. The six supplement
pages inherit the adopted visual review. This does not claim new human review.
The independent AI review checks source and bibliography differences; it did not
independently compile, render or inspect PDFs.

The clearpage-removal trial remained 17 pages with poor column balance and was
not adopted. The global author-shortening trial reached 16 pages but included
non-IEEE references and was not adopted. The final scoped derivation first failed
on a nested-brace field parser after writing partial files; that source and
failure are retained. A different continuation parsed those six protected fields
and finalized the candidate. No used derivation or passing suite was replayed.

The current observation is a historical snapshot, not scientific execution
permission. No release, intent, native scientific probe, GPU measurement,
COM automation, cleanup, lock or scientific-state mutation occurred. T6, LOHO,
explanation figures, later baseline experiments and complete efficiency results
still require real execution under the unchanged original admission contracts.

This ZIP contains editable sources, PDFs, previews and bounded evidence. The
external ROOT_REFERENCE_LAYOUT_ADOPTION.json binds the ZIP and its members;
the root report is outside the ZIP to avoid circular self-binding.
