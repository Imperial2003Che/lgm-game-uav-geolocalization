# LGM-GAME PyTorch

这是把原来的纯 Python prototype 升级成的第一版可训练 PyTorch 工程。当前目标不是直接冲 SOTA，而是先把论文里的核心创新落成能跑的实验管线：

1. `visual encoder`: ResNet18/ResNet50 提取 UAV/drone 与 satellite 图像特征。
2. `content text encoder`: 编码由 VLGeo/BLIP/CLIP/LLaVA 生成的稳定地物语义描述。
3. `style text encoder`: 编码由 VLM 生成或打分得到的视角、传感器、高度、光照、季节等风格描述。
4. `matching head`: 用 content token 增强跨视角共享语义，同时从视觉 embedding 中抑制 style 投影，最后做 batch 内对比匹配。
5. `training/evaluation`: 支持 SUES-200 和 University-1652 的第一组可跑实验。

## 目录

```text
lgm_game_pytorch/
  README.md
  commands/
    train_sues_smoke.sh
    train_university_smoke.sh
    generate_sues_clip_prompts.sh
    train_sues_clip_first.sh
    generate_sues_vlgeo_prompts.sh
    train_sues_vlgeo_smoke.sh
  lgm_game_pytorch/
    data.py
    evaluate.py
    build_prompts.py
    losses.py
    metrics.py
    model.py
    text_prompts.py
    train.py
    utils.py
```

## 已适配的数据集路径

```text
/Users/chenche/Documents/dataset/SUES-200
/Users/chenche/Documents/dataset/University-1652
```

SUES-200 使用 `drone_view_512/<id>/<height>` 与 `satellite-view/<id>`。其中 `<height>` 会作为 style cue 进入 VLM style description，例如 `height_150`。

University-1652 使用官方 `train/drone`、`train/satellite`，测试时使用 `test/query_drone` 与 `test/gallery_satellite`。

## 真实 VLM Prompt

`text_prompts.py` 已经从固定 token 替换为 VLM prompt provider。现在支持：

- `vlgeo`: BLIP caption + CLIP content/style label scoring，输出 VLGeo-style content/style 描述。
- `blip`: BLIP 生成 UAV/satellite caption，再转成 content/style prompt。
- `clip`: CLIP 对候选内容/风格标签打分，输出 top labels。
- `llava`: 调用本地 Ollama/LLaVA 接口生成描述。
- `cache`: 只读取已生成的 JSONL prompt cache。
- `metadata`: 仅作为快速调试 fallback。

先生成 SUES-200 的 CLIP prompt cache：

```bash
cd /Users/chenche/Documents/New\ project
bash lgm_game_pytorch/commands/generate_sues_clip_prompts.sh
```

缓存位置：

```text
/Users/chenche/Documents/New project/lgm_game_pytorch/prompt_cache/
```

用真实 CLIP content/style prompt 做第一组小实验：

```bash
bash lgm_game_pytorch/commands/train_sues_clip_first.sh
```

本地已跑出的第一组结果：SUES-200 32 个训练地点、16 个评估地点、ResNet18、1 epoch，metadata prompt baseline 为 R@1=0.2500 / R@5=0.8125 / R@10=1.0000，CLIP prompt 为 R@1=0.8125 / R@5=1.0000 / R@10=1.0000。

## 快速训练链路 Smoke Test

这个命令用 `metadata` prompt，只用于验证数据读取、forward/backward、checkpoint 和 eval 链路：

```bash
cd /Users/chenche/Documents/New\ project
bash lgm_game_pytorch/commands/train_sues_smoke.sh
```

或者直接运行：

```bash
PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.train \
  --dataset sues200 \
  --data-root /Users/chenche/Documents/dataset/SUES-200 \
  --output-dir lgm_game_pytorch/runs/sues200_first \
  --epochs 1 \
  --batch-size 4 \
  --image-size 128 \
  --max-classes 32 \
  --eval-max-classes 16 \
  --max-steps 10 \
  --prompt-backend vlgeo \
  --prompt-cache lgm_game_pytorch/prompt_cache/sues200_vlgeo_train.jsonl \
  --num-workers 0
```

训练输出会在：

```text
/Users/chenche/Documents/New project/lgm_game_pytorch/runs/
```

里面包含：

- `run_config.json`: 数据集扫描结果、参数、首个样本路径
- `metrics.json`: 每个 epoch 的 loss 和 recall
- `checkpoint_last.pt`: 模型权重

## 第一组正式一点的实验

SUES-200：

```bash
PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.train \
  --dataset sues200 \
  --data-root /Users/chenche/Documents/dataset/SUES-200 \
  --output-dir lgm_game_pytorch/runs/sues200_resnet18_e10 \
  --epochs 10 \
  --batch-size 16 \
  --image-size 224 \
  --max-classes 160 \
  --eval-max-classes 40 \
  --samples-per-class 1 \
  --prompt-backend vlgeo \
  --prompt-cache lgm_game_pytorch/prompt_cache/sues200_vlgeo_train.jsonl \
  --num-workers 0
```

University-1652：

```bash
PYTHONPATH=lgm_game_pytorch python3 -m lgm_game_pytorch.train \
  --dataset university1652 \
  --data-root /Users/chenche/Documents/dataset/University-1652 \
  --output-dir lgm_game_pytorch/runs/university1652_resnet18_e10 \
  --epochs 10 \
  --batch-size 16 \
  --image-size 224 \
  --max-classes 500 \
  --eval-max-classes 200 \
  --samples-per-class 1 \
  --prompt-backend vlgeo \
  --prompt-cache lgm_game_pytorch/prompt_cache/university1652_vlgeo_train.jsonl \
  --num-workers 0
```

## 注意

第一次运行 `vlgeo` / `blip` / `clip` backend 时，`transformers` 会下载对应 Hugging Face 模型。后续会读取 JSONL cache，不需要重复生成。
