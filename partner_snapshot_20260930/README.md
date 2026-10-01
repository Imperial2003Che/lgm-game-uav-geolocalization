# LGM-GAME 合作伙伴快照 · 2026-09-30

[正文 PDF](paper/main.pdf) · [补充 PDF](paper/supplementary.pdf) · [可编辑论文源](paper/) · [可编辑 PPT/SVG](figures/) · [结果和采用报告](evidence/) · [Visio](visio/)

这是用户要求停止进一步修改后的最新本地工作稿和已采用实验材料。正文 16 页、补充 6 页；不是最终投稿稿。此次只是精确字节复制，未重编论文、重算指标或启动科学实验。原稿中的表、图、科学数值、负结果与限制均保留。

70 张科研图对应 70 个 PPT 页和 70 个 SVG，分 main/robustness/transfer/risk/margin/reliability/paired 七组。PPT 和 SVG 的文字与图形为原生对象；图注、源表、嵌入 notes 和已有 provenance 保留。build_source 是已执行绘图源码的历史副本，不是新增实验或自动执行入口；原机器绝对路径及绘图依赖需在接收环境另行配置。

`visio/main_application_scope` 的两张主结果图有原实际保存、关闭、只读重开和 PDF 导出记录；不声称 GUI 编辑往返。`visio/file_xml_only_68` 的 68 个 VSDX 仅文件和原生 XML 范围采用，完整 XSD 和应用无修复打开/渲染/导出/编辑重开仍未验收。这两类不能合并称为全部 Visio 应用验收完成。

已采用 42 次 80 轮训练、官方 42 runs/231 tasks、双向迁移 12 runs/66 tasks、seed 1 鲁棒性 660 corrupt + 22 clean tasks。原流水线只前 6/7 阶段按报告范围接受，T6 未完成。Full 官方 10/11 任务的三种子平均 R@1 和 mAP 同时低于 Visual，T3 全 11 任务的平均 R@1 低于 Visual；不宣称普遍提升。

T6、LOHO、真实解释图、后继作者/独立 baseline 与额外 DAC、独立 B1 与全图库/排名/parity/timing/online CLIP、其余 Visio 完整应用验收、最终稿/Overleaf/投稿建议保持待办。三种子 sample SD 非 SE/CI；鲁棒性仅 seed 1 且 Full 为 cached-clean/online-corrupt 混合证据路径；T4/T5 的成员、掩码、分母、空 bin null 和非 posterior margin 限制及历史 SHA 链缺边保留，未新增 full-ranking/AP/独立 bootstrap 复算。

详细状态见 [PROJECT_STATUS](evidence/closeout/PROJECT_STATUS.json)。本目录是便于 GitHub 浏览的小文件快照；原始数据、模型/缓存、NPZ、历史大包和运行依赖未复制到此目录，完整本地 ZIP 的上传/下载安排应以仓库首页实际说明为准。原 Overleaf 仍是历史 14+4 页审阅稿，不能当本次论文入口。

[STAGING_MANIFEST.json](STAGING_MANIFEST.json) 记录每个复制文件的原路径、实际大小、SHA256 及读取副本验证；此运输一致性不是新的科学验收。未改根 README、Git 或原科学文件。
