# Third-party license preservation

This directory preserves existing third-party license terms for the source copies distributed under `research_source`. It does not grant a new license to LGM-GAME's own code or change scientific content.

- The original QDFL MIT license (copyright Shuyu Hu) is restored at `../execution/baseline_preparation/compatibility_v3/work/patched_sources/qdfl-627296d5-adapter-v4/LICENSE`.
- The original DAC scientific-source Apache license is restored at `../execution/dac_training_preparation_v1/scientific_source/LICENSE`.
- `dinov2/LICENSE` applies to the Meta DINOv2 source whose Apache-2.0 headers remain in the QDFL patched source tree, including `model/backbones/dinov2_backbone/`.
- `Swin-Transformer/LICENSE` preserves Microsoft's MIT terms for `model/backbones/swinv2_backbone/swin_transformer_v2.py` and related copied Swin source.
- `ConvNeXt/LICENSE` preserves Meta's MIT terms for ConvNeXt source copied inside the QDFL tree and DAC `scientific_source/sample4geo/hand_convnext/ConvNext/`.

Existing copyright headers remain unchanged. The three upstream license files are exact current official files fetched at the immutable commits listed in LICENSE_PROVENANCE.json; these records do not reconstruct or validate the original scientific source's historical upstream commit. Where root NOTICE was absent at those exact commits, only that exact 404 is recorded; no broader absence claim is made.

This addition only restores distribution license materials. It does not execute the source, approve scientific results, change frozen experiment parameters, or license third-party datasets for redistribution.
