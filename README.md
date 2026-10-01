# LGM-GAME · 合作伙伴项目交付

**最新快照：2026-09-30；公开整理：2026-10-01。**

[最新正文 PDF（16页）](partner_snapshot_20260930/paper/main.pdf) · [补充材料 PDF（6页）](partner_snapshot_20260930/paper/supplementary.pdf) · [可编辑 LaTeX/BibTeX](partner_snapshot_20260930/paper/) · [下载交付版本](https://github.com/Imperial2003Che/lgm-game-uav-geolocalization/releases/tag/partner-20260930)

这是当前论文工作稿、真实已采用实验材料和代码的合作伙伴交接版本。本次上传没有修改论文科学内容、重算指标或启动实验。最新本地稿不是最终投稿稿，旧 `lgm_game_paper_latex/` 与早期 demo 为历史材料。

## 从这里开始

| 内容 | 入口 |
|---|---|
| 最新论文、完整作者元数据与图表依赖 | [paper](partner_snapshot_20260930/paper/) |
| 当前 PyTorch 代码、实验脚本与保存的小结果 | [lgm_game_pytorch](lgm_game_pytorch/) |
| 正式协议与依赖清单 | [research_protocols](research_protocols/) |
| 工作区脚本、控制/审查源码、外部适配器 | [research_source](research_source/) |
| 70页原生可编辑 PPT、70个 SVG、源 CSV 与图注 | [figures](partner_snapshot_20260930/figures/) |
| 两个已有应用范围记录的 Visio，以及68个仅文件/XML范围通过的 Visio | [visio](partner_snapshot_20260930/visio/) |
| 已保存结果表、采用报告和关闭工作时的待项 | [evidence](partner_snapshot_20260930/evidence/) |

普通文件可直接浏览；通过 **Code → Download ZIP** 下载浏览版本。Release提供交付附件；大型实验附件按单附件限制分片，合并说明和校验值同页提供。仓库不自动运行训练或历史恢复脚本。

## 实验状态

- 已采用42次训练（每次80轮），官方42 runs / 231 tasks，T3双向迁移12 runs / 66 tasks。
- seed 1鲁棒性：4 runs、120运行条件、660扰动 tasks + 22 clean tasks。
- 原流水线前6/7阶段按各自报告范围采用；**T6未完成**。
- Full在官方11个任务中10个任务的三种子平均R@1与mAP同时低于Visual；T3全部11个任务的平均R@1低于Visual。结果不支持“普遍提升”。

三种子sample SD不是SE/CI；鲁棒性只有seed 1且Full的cached-clean / online-corrupt属于混合证据路径。T4/T5保留各自掩码、成员、分母、空bin null和非posterior margin限制；历史SHA链缺边、未新增full-ranking/AP/独立bootstrap复算等限制不因上传而改变。

T6、额外LOHO 24 fit / 192 tasks、真实解释图、后继作者权重与独立baseline、额外DAC、完整B1及fresh图库/排名/parity/timing/online CLIP、68个Visio的完整应用验收、最终稿/最终Overleaf/投稿建议仍未完成。用户已要求完结当前工作；待项如实留档，没有以准备或上传代替科学完成。[完整状态](partner_snapshot_20260930/evidence/closeout/PROJECT_STATUS.json)

## 原数据与大文件

本地完整项目ZIP为60,861,508,543字节，SHA256为 `f327b99141094e927d4ff38ce194244883c0eb9e9711563af01d2451b645c1c1`；已保留在所有者的下载文件夹。**该本地完整包没有原封公开上传。**

University-1652作者的数据说明明确禁止原数据或其部分再分发，并允许发布派生模型、代码和评估结果。因此公开仓库/附件提供项目论文、代码、派生模型和结果，原始图像由接收方从作者取得：[University-1652项目](https://github.com/layumi/University1652-Baseline)、[当前数据条款](https://huggingface.co/datasets/layumi/university-1652/blob/main/README.md?code=true)。SUES-200通过[作者项目](https://github.com/Reza-Zhu/SUES-200-Benchmark)获取并遵守其条款。本仓库不赋予第三方数据的新许可。

运行依赖、虚拟环境、模型下载缓存、历史Git目录和抓取的第三方网页不放进Git树。大型正式实验附件保存既有checkpoint、逐运行日志/JSON/NPZ和结果；文件是否存在不代表其科学结果已验收，失败/早期运行按原目录与状态区分。原机器绝对路径需要接收方按冻结协议配置；不能直接重放旧release/intent/runtime_attempt或一次性恢复入口。

公开不等于授予新的开源许可。本项目尚未新增开源许可证；原第三方软件版权及许可应继续遵守。科学代码和图表来源字节继承，复制/运输校验不修复历史科学证据缺边。

## 论文编译与历史项目

编译当前论文时在 `partner_snapshot_20260930/paper/` 运行 `pdflatex main`、`bibtex main`、再两次 `pdflatex main`；补充材料同理。保留 `ieee_controls.bib`、`IEEEtran_lgm_display.bst`。本次上传未重新编译，继承已采用正文16页与补充6页的编译/视觉记录。

原Overleaf审阅项目仍是历史14+4页版本，本次16+6页以此仓库论文目录为准。早期概念原型的模拟输出不属于上述正式实验计数。
