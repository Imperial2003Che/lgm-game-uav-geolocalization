# LGM-GAME PyTorch

该目录是可训练的 PyTorch 工程，包含：

- ResNet18/ResNet50 视觉编码器；
- 内容文本与风格文本编码；
- 风格抑制匹配头；
- SUES-200 和 University-1652 数据加载；
- 训练、checkpoint 与 Recall@K 评估；
- metadata、cache、BLIP、CLIP、VLGeo 和 LLaVA prompt 后端。

## 数据目录

`--data-root` 指向单个数据集根目录。

SUES-200：

```text
<SUES200_ROOT>/
├── drone_view_512/<id>/<height>/...
└── satellite-view/<id>/...
```

University-1652：

```text
<UNIVERSITY1652_ROOT>/
├── train/drone/...
├── train/satellite/...
├── test/query_drone/...
└── test/gallery_satellite/...
```

## 安装

从交付包根目录运行：

```bash
python -m pip install -r requirements.txt
```

BLIP、CLIP 或 VLGeo 后端还需要：

```bash
python -m pip install -r requirements-vlm.txt
```

## 训练

PowerShell：

```powershell
$env:PYTHONPATH = "$PWD\lgm_game_pytorch"
python -m lgm_game_pytorch.train `
  --dataset sues200 `
  --data-root "D:\datasets\SUES-200" `
  --output-dir "lgm_game_pytorch\runs\sues200_smoke" `
  --epochs 1 `
  --max-steps 2 `
  --prompt-backend metadata `
  --device cpu
```

Bash：

```bash
PYTHONPATH=lgm_game_pytorch python -m lgm_game_pytorch.train \
  --dataset sues200 \
  --data-root "/path/to/SUES-200" \
  --output-dir "lgm_game_pytorch/runs/sues200_smoke" \
  --epochs 1 \
  --max-steps 2 \
  --prompt-backend metadata \
  --device cpu
```

也可以先设置 `SUES200_ROOT` 或 `UNIVERSITY1652_ROOT`，再运行 `commands/*.sh`。

## Prompt 后端

- `metadata`：无需额外模型，适合链路检查。
- `cache`：读取预先生成的 JSONL。
- `blip` / `clip` / `vlgeo`：需要 `transformers`，首次运行通常需要获取相应模型。
- `llava`：通过 HTTP 调用接收方配置的本地 LLaVA/Ollama 服务。

smoke test 只验证数据读取、前向/反向、checkpoint 和评估链路，不代表标准 benchmark 成绩。

