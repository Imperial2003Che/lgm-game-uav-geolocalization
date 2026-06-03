# LGM-GAME Prototype

这是一个轻量代码骨架，对应前面提出的论文思路：

`Language- and Vector-Map-Guided Geometric Sparse Transformer for UAV-View Geo-Localization`

它不是完整可训练模型，而是一个方便后续扩展的研究原型。当前版本用纯 Python 模拟核心流程：

1. UAV / satellite visual tokens
2. VLM semantic anchors
3. vector map topology tokens
4. language-map-geometry guided sparse attention
5. Sinkhorn + dustbin matching
6. greedy clique-style consistency selection

## 文件结构

```text
lgm_game_prototype/
  README.md
  lgm_game_prototype.code-workspace
  run_demo.py
  lgm_game/
    __init__.py
    config.py
    tokens.py
    prototype.py
```

## 快速运行

在 VS Code 终端中进入本文件夹：

```bash
cd /Users/chenche/Documents/New\ project/lgm_game_prototype
python3 run_demo.py
```

你会看到一个模拟输出：Top-k sparse attention 边、Sinkhorn 匹配结果、以及最终自洽候选。

## 后续可以怎么改

- 把 `prototype.py` 中的 `encode_visual_tokens` 替换为 ResNet/FPN/ViT 特征提取。
- 把 `build_semantic_anchors` 替换为真实 VLM prompt 生成与文本编码。
- 把 `build_map_tokens` 接入 OSM / shapefile / vector tile。
- 把 `language_map_geometry_score` 换成 PyTorch attention logits。
- 把 `sinkhorn_match` 改成可微最优传输匹配头。
- 把 `greedy_consistency_clique` 替换为 maximal clique 或图优化模块。

