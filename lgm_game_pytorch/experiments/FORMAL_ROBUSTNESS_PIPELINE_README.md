# 四任务正式鲁棒性编排、聚合与论文图表

本流程只处理以下四个冻结运行：

1. University-1652 / `visual` / seed 1；
2. University-1652 / `full` / seed 1；
3. SUES-200 / `visual` / seed 1；
4. SUES-200 / `full` / seed 1。

正式图像级 evaluator 及扰动定义见
`run_image_level_robustness.py` 和 `IMAGE_LEVEL_ROBUSTNESS_README.md`。

## 1. 可恢复顺序编排

脚本：`run_frozen_robustness_matrix.py`

它会先使用冻结训练矩阵 runner 的完整门禁，同时验证四个 checkpoint：

- seed 1；
- 正式 ResNet-18、512 维主矩阵配置；
- 80 个完整 epoch；
- 无 validation/test 选择；
- `best.pt` 为预先规定的第 80 epoch；
- checkpoint、训练 manifest、history、evidence、数据与正式代码哈希一致。

四个 checkpoint 没有全部通过前，任何 robustness evaluator 都不会启动。通过后，
四个真实运行严格串行执行，避免四个 evaluator 互相争用 GPU。中断或单个 evaluator
失败时，已有 artifact 会保留；用完全相同的命令重新启动即可继续。不同源码、输入、
输出路径或运行配置不能复用旧 ledger。

只读状态检查：

```powershell
$python = "C:\项目\.venvs\lgm-baselines\Scripts\python.exe"
$delivery = "C:\项目\LGM-GAME-Partner-Delivery-20260724"

& $python "$delivery\lgm_game_pytorch\experiments\run_frozen_robustness_matrix.py" `
  --stage status
```

正式顺序运行：

```powershell
& $python "$delivery\lgm_game_pytorch\experiments\run_frozen_robustness_matrix.py" `
  --stage run `
  --device cuda `
  --eval-batch-size 128 `
  --eval-chunk-size 128 `
  --image-workers 8 `
  --clip-precision match-cache `
  --clip-local-files-only
```

应在其余正式训练 GPU 作业结束后再启动正式鲁棒性编排器。编排器自身保证四个目标
checkpoint 全部完成，并保证四个 robustness 运行彼此串行，但不会擅自终止其他进程。

ledger：

```text
lgm_game_pytorch/runs/frozen_robustness_matrix_ledger.json
```

wrapper stdout/stderr 位于 ledger 同目录的
`frozen_robustness_orchestrator_logs/`，不会进入 evaluator 的 artifact 树并造成
“运行中日志被提前哈希”的不一致。

## 2. 严格聚合与 Python 论文图表

脚本：`aggregate_formal_robustness.py`

只有四个 `robustness_manifest.json` 全部为 `completed`，且全部通过以下检查后，
聚合器才会创建任何结果文件：

- 四个数据集/模型键精确为 2 × 2，没有缺项或重复项；
- 每个运行有完整 6 类扰动 × 5 强度；
- University-1652 的 3 个官方任务、SUES-200 的 8 个官方任务全部存在；
- 每个 task 的官方 query/gallery 数量正确；
- 每个 condition 为全 query、clean full gallery、原始 RGB 扰动；
- `full` 的受扰 query 明确记录为重新计算 CLIP evidence；
- clean 与每个 condition 的 per-query NPZ 数量、字段、路径顺序及哈希一致；
- condition、artifact、checkpoint、数据、源码、环境、协议和最终 manifest 哈希正确；
- 四个运行共享同一 evaluator、`formal_retrieval.py`、冻结协议和 corruption matrix。

任一检查失败时，聚合器在写出 CSV、LaTeX 或图像之前退出，不输出部分结果。

正式聚合：

```powershell
& $python "$delivery\lgm_game_pytorch\experiments\aggregate_formal_robustness.py" `
  --png-dpi 600
```

默认输出：

```text
lgm_game_pytorch/results/formal_robustness_aggregate/
```

主要 artifact：

- `source_data/robustness_all_tasks_source.csv`：完整 task-separated 源数据；
- `robustness_all_tasks.json`：按 dataset/variant/task 嵌套的完整结果；
- `tables/robustness_r_at_1_task_tables.tex`；
- `tables/robustness_official_trapezoid_map_task_tables.tex`；
- `figures/<dataset>/<task>/...pdf|svg|png`；
- `figures/source_data/*.csv`：每张图一份 source CSV；
- `figure_index.json`：图、数据与格式映射；
- `aggregation_manifest.json`：最终输入和输出 artifact 审计。

图表使用 Python/matplotlib 独占工作流。默认对 11 个官方任务分别生成 Recall@1 和
official trapezoidal mAP 图，共 22 张；每张为 2 × 3 六面板 severity 曲线，分别对应
六类扰动。纵轴为相对该模型自身 clean baseline 的性能保留率，从 0 开始；不进行
University/SUES task 宏平均，也不伪造 seed-1 鲁棒性误差条。每张图同时输出：

- 可编辑文本的 SVG；
- 矢量 PDF；
- 600 dpi PNG；
- 完整 source CSV。

## 3. CPU 合成结构测试

```powershell
$env:CUDA_VISIBLE_DEVICES = ""
& $python "$delivery\lgm_game_pytorch\experiments\test_formal_robustness_pipeline.py"
```

测试会在临时目录创建完整的 30-condition 合成 artifact 树，验证：

- 完整树能够通过门禁；
- 删除任一 condition 后必定 fail-closed；
- 四运行 registry 和命令参数正确；
- 结果保持 11 个 task 分开；
- LaTeX 表数量正确；
- Python 能输出 PDF/SVG/PNG，并保留 SVG 文本。

合成数据和合成图仅用于结构与版式测试，不能作为论文实验结果。
