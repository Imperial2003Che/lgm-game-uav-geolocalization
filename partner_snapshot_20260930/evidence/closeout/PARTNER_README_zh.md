# LGM-GAME 合作伙伴完整项目交付 · 2026-09-30

按用户最新要求，本次完成当前论文局部修订后停止继续修改与实验推进，交付完整项目快照。最新论文是已采用的 **16 页正文 + 6 页补充材料本地工作稿**；其余尚未完成的实验如实保留为待办。本次完结是工作交接，不表示全部科学实验或投稿终稿已经完成。压缩包校验通过后停止自动跟进，实际停止回执与运输校验报告放在 ZIP 旁。

## 先看最新论文

- `latest_paper/manuscript/main.pdf`：16 页正文。
- `latest_paper/manuscript/supplementary.pdf`：6 页补充材料。
- `latest_paper/manuscript/`：可编辑 LaTeX、完整 BibTeX、图表、原 IEEEtran 和派生显示 BST；重建正文需保留 `ieee_controls.bib` 与 `IEEEtran_lgm_display.bst`。
- `latest_paper/LGM_GAME_Reference_Layout_Working_Draft_20260930.zip`：此前已采用的小工作稿包。
- `latest_paper/ROOT_REFERENCE_LAYOUT_ADOPTION.json`：该稿采用范围与字节绑定。

最新稿已整合已采用的主实验、迁移、敏感性和相应限制。最后一部分仅调整六条当前 IEEE 期刊参考文献的作者显示与末页排版，没有缩小字号；完整作者元数据、科学数字与负结果保留。正文实际四条编译命令成功，仍有四处 underfull hbox；补充材料继承原成功版本及诊断。本次完整打包不再编译或改稿。

`LGM/00_最新论文/`、旧 README、旧“定稿”文件名、旧交付目录均为历史材料，请以本文件和 `latest_paper/` 为本次论文入口。`delivery_docs/historical_20260929/` 中原交付说明仅供追溯，已不代表当前论文版本或工作指令。

## 内容与入口

| 包内路径 | 内容 |
|---|---|
| `LGM/01_当前工作区/` | 整个当前工作区：全部 outputs、论文迭代、审查与执行记录、图表源、隐藏文件、历史与临时目录 |
| `LGM/02_代码与实验/正式实验工程/` | 正式代码、冻结协议、原实验脚本、环境资料 |
| `LGM/02_代码与实验/正式实验工程/lgm_game_pytorch/` | PyTorch 工程、训练权重、runs、evaluations、analysis、results 与证据缓存 |
| `LGM/02_代码与实验/外部基线资源/` | 已有外部基线代码、适配器、权重和来源记录 |
| `LGM/03_历史版本/` 至 `LGM/06_历史材料/` | 历史交付、专利材料、日志脚本与早期仓库 |
| `assets/datasets/University-1652/`、`assets/datasets/SUES-200/` | 数据集原始文件 |
| `assets/model_cache/` | 所用 CLIP 与 Torch 模型缓存 |
| `assets/baselines/` | 纳入原完整范围的 LPN、CA-HRS、IMTMN 权重、代码、日志与文档 |
| `assets/figure_runtime/node_modules/` | 已有绘图运行依赖 |
| `delivery_docs/PROJECT_STATUS.json` | 当前已采用结果、明确待办、论文与图件的证据限制 |
| `delivery/MANIFEST.jsonl`、`delivery/SCOPE.json`、`delivery/JUNCTIONS.json` | 逐成员大小/CRC、完整归档范围与原路径链接映射 |

项目树内所有普通文件与目录均纳入，不筛除旧版、失败尝试、`.git`、项目 `.venv` 或临时资料。相关外部依赖按此前完整交付的明确范围纳入；无关外部项目实验、系统级 Python/Conda/Node 安装、用户账户会话及自动化配置不属于项目包。Windows junction 不递归复制目标多次，已存在目标各有实体归档路径；一处原已损坏的历史诊断链接只记录事实，不造文件。源码中原机器绝对路径与虚拟环境未伪称可直接跨机运行，接收方应按协议及 `JUNCTIONS.json` 配置本机路径。

## 实验结果与未完成范围

| 范围 | 已采用结果 |
|---|---|
| 训练 | 42/42 次，每次 80 轮；36 主实验、6 敏感性 |
| 官方完整评估 | 42 次运行、231 个任务 |
| T3 双向迁移 | 12 次运行、66 个任务 |
| seed 1 鲁棒性 | 4 次运行、120 个运行条件、660 扰动任务、22 clean 任务 |
| 原 7 阶段流水线 | 前 6 阶段按各自报告范围采用；原 T6 尚未完成 |

以上是登记运行和任务数，不是独立数据集或统计样本数。主结果在工程 `results/formal_matrix_aggregate/`，鲁棒性在 `results/formal_robustness_aggregate/`；逐运行结果和全部审核原件保持。权威状态记录位于 `LGM/01_当前工作区/outputs/paper_evidence_rebuild_20260914/execution/HANDOFF.md`。

关闭工作时仍未完成：T6；LOHO 额外 24 次训练及 192 个评估任务；真实 descriptor/t-SNE/Grad-CAM；后继作者权重复评与独立 baseline 训练/评估、额外 DAC；六个 fresh B1 worker 的真实执行与不可变准入/双句柄退出闭流证据；全图库重新编码/排名/parity、完整原图到排名计时及全数据 online CLIP；其余 Visio 的完整 XSD 与应用验收；最终投稿稿、最终 Overleaf 更新和最终投稿建议。这些项目没有在本包中被补造完成。普通 CPU 控制、源准备或内部局部计时不是 T6/B1 结果。

Full 在官方 11 个任务中 10 个任务的三种子平均 R@1 与 mAP 同时低于 Visual；T3 所有 11 个任务的平均 R@1 低于 Visual，不能宣称普遍提升。三种子样本 SD 不是 SE/CI；不跨方向、任务或高度合并。鲁棒性只有 seed 1，Full 的 cached-clean 与 online-corrupt 是混合证据路径。T4/T5 的掩码、成员、分母、空 bin null、非 posterior margin 等限制及历史 SHA 链缺边保留；没有新增模型/全排名/AP/独立 bootstrap 验收。

## 原生可编辑图件

下列目录接在 `LGM/01_当前工作区/outputs/paper_evidence_rebuild_20260914/` 后，各含源表、图注、代码和审核记录。

| 图件 | 目录 |
|---|---|
| 两张主实验 PPT（选 v2） | `formal_main_native_ppt_20260929_1548/output/` |
| 两张实测主结果 Visio、PNG/PDF | `formal_main_native_visio_20260929_2258/output_v2/` |
| 22 张鲁棒性 PPT/SVG | `robustness_native_figures_20260929_1650/output/` |
| 2 张双向迁移 PPT/SVG | `transfer_native_figures_20260929_1750/output/` |
| 11 张风险-coverage PPT/SVG | `query_t5_native_figures_20260929_1856/output_v2/` |
| 11 张 margin 分层 PPT/SVG | `query_t4_margin_native_figures_20260929_1952/output/` |
| 11 张 reliability/ECE PPT/SVG | `query_t5_reliability_native_figures_20260929_2054/output/` |
| 11 张 paired PPT/SVG | `query_t5_paired_native_figures_20260929_2157/output/` |
| 其余 68 个原生 VSDX 文件与源 | `offline_native_visio_20260930_1030/` |

70 张 PPT/SVG 已按各自范围采用。两张主结果 Visio 有实际保存、关闭、只读重开和 PNG/PDF 导出记录；另外 68 个仅文件及原生 XML 范围通过，完整 XSD、实际无修复打开/渲染/导出/编辑往返仍未验收，不把两类混称全部 Visio 已通过。原生单对象编辑不表示分组、Excel 自动链接或 GUI 编辑往返实测。

## Overleaf 与接收后运行

原审阅项目 https://www.overleaf.com/project/6ab9825d2cb870b10bc95589 仍是历史 14+4 页稿，未上传本次 16+6 页工作稿。在线下载原件保留在 `assets/overleaf_roundtrip/` 和原执行目录；最新可编辑论文以本地 `latest_paper/` 为准。包内投稿要求研究只是已保存资料，不冒称最终投稿建议或已投稿。

用户本次要求结束工作，旧 HANDOFF 中“持续推进直到全部实验完成”的指令只作历史记录。此次交付没有启动、恢复、调参或操作用户应用。旧 release/intent、runtime_attempt、失败日志和一次性恢复脚本原样留档，不可直接重放；原 GPU 独占、资源、boot、来源与共享锁准入条件没有被打包取消。若合作伙伴以后另行恢复实验，应先读最新交接和冻结协议，按其当时环境另作准入，而不是运行历史入口。

运输完整性以 ZIP 旁的 `VERIFICATION.json` 和 `.sha256` 为准：新 ZIP 全部成员读取到 EOF 核 CRC/大小、清单精确匹配，并独立读取整个新 ZIP 比对 SHA256。本检查不重跑科学实验，也不把传输 CRC 当作历史科学 SHA 链修复。原 60.47 GB 完整包保留未读取、覆盖或重新哈希。
