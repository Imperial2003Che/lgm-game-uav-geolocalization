# LGM-GAME PyTorch

这是把原来的纯 Python prototype 升级成的第一版可训练 PyTorch 工程。当前目标不是直接冲 SOTA，而是先把论文里的核心创新落成能跑的实验管线：

1. `visual encoder`: ResNet18/ResNet50 提取 UAV/drone 与 satellite 图像特征。
2. `content text encoder`: 编码稳定地物语义 token，例如 campus、building、road、vegetation、stable_layout。
3. `style text encoder`: 编码干扰风格 token，例如 UAV/satellite、height_150/200/250/300、viewpoint_gap、sensor_gap。
4. `matching head`: 用 content token 增强跨视角共享语义，同时从视觉 embedding 中抑制 style 投影，最后做 batch 内对比匹配。
5. `training/evaluation`: 支持 SUES-200 和 University-1652 的第一组可跑实验。

## 目录

```text
lgm_game_pytorch/
  README.md
  commands/
    train_sues_smoke.sh
    train_university_smoke.sh
  lgm_game_pytorch/
    data.py
    evaluate.py
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

SUES-200 使用 `drone_view_512/<id>/<height>` 与 `satellite-view/<id>`。其中 `<height>` 会自动转成 style token，例如 `height_150`。

University-1652 使用官方 `train/drone`、`train/satellite`，测试时使用 `test/query_drone` 与 `test/gallery_satellite`。

## 快速 smoke test

在仓库根目录运行：

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
  --num-workers 0
```

## 注意

当前文本 token 是从数据集元信息自动生成的 pseudo prompt，不等于真正 VLM caption。这样做的作用是先把多模态训练接口跑通。后续论文升级时，可以把 `text_prompts.py` 替换为 BLIP/CLIP/LLaVA/VLGeo 风格的真实内容描述与风格描述，然后保留训练主干不变。
