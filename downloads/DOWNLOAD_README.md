# 合作伙伴下载说明

项目首页和最新版论文/代码/图表可以直接公开浏览，下载 `LGM_GAME_Public_Project_20260930.zip` 可取得浏览版本。

正式实验附件为约10.90GB的ZIP，按顺序拆为6个文件（每个小于2GiB）：`LGM_GAME_Formal_Experiments_20260930.zip.part001` 至 `part006`。包含正式PyTorch工程的源/配置、86个现存checkpoint、979个NPZ以及逐运行日志/结果；包含早期与失败运行，86个文件不表示86次已验收训练。科学已验收范围为42训练/官方231任务/迁移66任务及seed1鲁棒660+22，T6和后继待项不变。

下载全部6片、`EXPERIMENTS_MANIFEST.json` 和 `merge_experiments.py` 到同一空文件夹，然后运行：

```
python merge_experiments.py
```

脚本逐片和整包核SHA256后生成普通ZIP，随后正常解压。脚本只合并下载文件，不安装依赖或执行模型。需要约22GB可用磁盘完成分片与合并ZIP，解压还需额外空间。`SHA256SUMS.txt` 也提供手动校验值。打包时已经完整读取新ZIP成员核CRC；运输校验不代表重新科学验收。

此公开附件不含University-1652/SUES-200原始图像、CLIP/prompt证据缓存、系统运行依赖或历史Git。University-1652作者禁止原始数据再分发；请接收方从作者申请/下载数据并遵守条款：

- https://github.com/layumi/University1652-Baseline
- https://huggingface.co/datasets/layumi/university-1652/blob/main/README.md?code=true
- https://github.com/Reza-Zhu/SUES-200-Benchmark

原60.86GB完整项目包继续保留在所有者本地下载文件夹，没有原封发布到此公开仓库。最新论文为16+6页工作稿；不是最终投稿稿。不要重放原一次性恢复脚本、release/intent或runtime_attempt。
