# 冻结图像级鲁棒性评估

脚本：`run_image_level_robustness.py`

该脚本执行 `FORMAL_EXPERIMENT_PROTOCOL.md` 中冻结的完整鲁棒性矩阵：

- 6 类扰动 × 5 个强度，共 30 个条件；
- University-1652 的全部 3 个官方任务；
- SUES-200 的 4 个高度、双向共 8 个官方任务；
- 仅扰动 query 的原始 RGB 像素，gallery 在所有条件下保持干净；
- 仅接受正式主矩阵中 seed 1 的 `visual` 或 `full` ResNet-18、512 维、
  80 epoch 最终 checkpoint；
- 每个条件都重新编码全部官方 query，不抽样，不缩减 gallery。

## 完整性设计

扰动发生在图片解码之后、模型预处理之前。脚本没有接收“待扰动特征”的接口，
因此不能用 feature-level 噪声代替图像扰动。

`full` 模型的 content/style 分支来自冻结 CLIP 图像证据。对于受扰 query，脚本
会用受扰后的 RGB 图片重新运行与干净 evidence cache 完全相同的 CLIP 模型、
固定候选文本、logit scale 和 softmax；不会读取该 query 的干净 content/style
值。干净 gallery 继续使用完整、已校验哈希的干净 evidence cache。

Gaussian noise 的随机流和 rotation 的正负方向由固定全局 seed、扰动名、强度及
相对图片路径共同经过 SHA-256 派生。其他扰动没有随机量。每个结果都会记录：

- checkpoint、训练 manifest、evidence cache、数据图片、冻结协议和源代码哈希；
- 扰动参数、随机 seed、官方任务成员哈希；
- query/gallery 完整覆盖；
- clean 指标、受扰指标、绝对下降、百分点下降和相对下降；
- 每个 query 的 AP、rank、top-1、margin 及其相对 clean 的变化。

任一图片读取失败、query 缺失、cache 不完整、checkpoint 不符合冻结配置或哈希
不一致都会使进程失败，不会跳过样本。

## 正式运行

先等待对应的 80 epoch seed-1 checkpoint 和同目录 `run_manifest.json` 完成。
以下命令均应使用项目的 CUDA 环境：

```powershell
$python = "C:\项目\.venvs\lgm-baselines\Scripts\python.exe"
$script = "C:\项目\LGM-GAME-Partner-Delivery-20260724\lgm_game_pytorch\experiments\run_image_level_robustness.py"
$delivery = "C:\项目\LGM-GAME-Partner-Delivery-20260724"
```

University-1652 / visual：

```powershell
& $python $script `
  --dataset university1652 `
  --data-root "C:\项目\IMTMN\datasets\University-1652" `
  --evidence "$delivery\lgm_game_pytorch\evidence_cache\university1652_clip_image_evidence.npz" `
  --checkpoint "$delivery\lgm_game_pytorch\runs\formal_main\university1652\visual\seed_1\best.pt" `
  --output-dir "$delivery\lgm_game_pytorch\runs\formal_robustness\university1652\visual\seed_1" `
  --device cuda --eval-batch-size 128 --eval-chunk-size 128 --image-workers 8
```

University-1652 / full：

```powershell
& $python $script `
  --dataset university1652 `
  --data-root "C:\项目\IMTMN\datasets\University-1652" `
  --evidence "$delivery\lgm_game_pytorch\evidence_cache\university1652_clip_image_evidence.npz" `
  --checkpoint "$delivery\lgm_game_pytorch\runs\formal_main\university1652\full\seed_1\best.pt" `
  --output-dir "$delivery\lgm_game_pytorch\runs\formal_robustness\university1652\full\seed_1" `
  --device cuda --eval-batch-size 128 --eval-chunk-size 128 --image-workers 8 `
  --clip-precision match-cache --clip-local-files-only
```

SUES-200 / visual：

```powershell
& $python $script `
  --dataset sues200 `
  --data-root "C:\项目\IMTMN\datasets\SUES-200" `
  --evidence "$delivery\lgm_game_pytorch\evidence_cache\sues200_clip_image_evidence.npz" `
  --checkpoint "$delivery\lgm_game_pytorch\runs\formal_main\sues200\visual\seed_1\best.pt" `
  --output-dir "$delivery\lgm_game_pytorch\runs\formal_robustness\sues200\visual\seed_1" `
  --device cuda --eval-batch-size 128 --eval-chunk-size 128 --image-workers 8
```

SUES-200 / full：

```powershell
& $python $script `
  --dataset sues200 `
  --data-root "C:\项目\IMTMN\datasets\SUES-200" `
  --evidence "$delivery\lgm_game_pytorch\evidence_cache\sues200_clip_image_evidence.npz" `
  --checkpoint "$delivery\lgm_game_pytorch\runs\formal_main\sues200\full\seed_1\best.pt" `
  --output-dir "$delivery\lgm_game_pytorch\runs\formal_robustness\sues200\full\seed_1" `
  --device cuda --eval-batch-size 128 --eval-chunk-size 128 --image-workers 8 `
  --clip-precision match-cache --clip-local-files-only
```

输出目录已绑定 immutable configuration hash。中断后可原命令重启：脚本会逐个验证
已完成条件的 manifest 与 artifact 哈希，只跳过验证通过的条件。配置不同必须使用
新的输出目录，脚本不会删除或混合旧结果。

主要输出：

- `clean/metrics.json`：干净基线；
- `conditions/<corruption>/severity_XX/metrics.json`：单条件指标及相对下降；
- `conditions/.../per_query_arrays/*.npz`：完整 per-query 数组；
- `robustness_summary.csv` / `.json`：30 条件汇总；
- `robustness_manifest.json`：最终覆盖、来源与 artifact 审计；
- `clip_clean_reproduction_audit.json`：`full` 模型的 CLIP 干净证据复现审计。

## 轻量 CPU 验证

该验证只使用临时生成的小图片和 mock encoder，不读取真实测试集，也不占用正式
GPU：

```powershell
& $python "$delivery\lgm_game_pytorch\experiments\test_image_level_robustness.py"
```

正式论文只能使用四个完整真实数据运行生成且最终 manifest 为 `completed` 的结果；
轻量测试输出不能作为论文实验数据。
