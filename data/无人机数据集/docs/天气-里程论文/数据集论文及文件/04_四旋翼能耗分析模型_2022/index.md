# 04 索引

## 基本信息
- 标题：`Quadrotor Model for Energy Consumption Analysis`
- DOI：`10.3390/en15197136`
- 论文方向：四旋翼动力学与能耗仿真模型

## 已下载内容
- `paper/article.pdf`
  - 由 MDPI 正文页打印生成的可读 PDF
- `html/article_snapshot.md`
  - 正文页面快照
- `supplement/energies-15-07136-s001.zip`
  - 用户手动下载后已归档到本论文目录
- `translation/摘要逐句翻译_第一版.md`
  - 摘要与 Data Availability 的第一版手工逐句翻译
- `translation/附录A与数据可得性逐句翻译_第二版.md`
  - 补充了附录 A 资源说明的手工逐句翻译

## 论文内已确认的重要资源
- 页面显示存在补充材料入口：`ZIP-Document`
- 目录中明确包含：
  - `Supplementary Materials`
  - `Appendix A. Flight Data and MATLAB Scripts`
- PDF 正文明确说明：
  - 补充材料下载地址还出现过 `https://www.mdpi.com/article/10.3390/en15197136/s1`
  - `Supplementary Materials` 中应包含用于生成 Figure 10 到 Figure 21 的飞行数据
  - 附录 A 进一步说明补充目录里应有 `Case 1`、`Case 2` 飞行日志，以及 `Trajectory` MATLAB 脚本
- 当前 ZIP 实际目录核验结果：
  - 已确认存在 `Supplementary materials/Case 1/`
  - 已确认存在 `Supplementary materials/Case 2/`
  - 已确认包含 `.tlog`、`.bin`、`.log`、`.log.param`、`.waypoints`
  - 当前未看到名为 `Trajectory/` 的目录，也未看到明显的 `.m` MATLAB 脚本文件

## 失败/受限项
- MDPI 补充材料下载路径 1：`https://www.mdpi.com/1996-1073/15/19/7136/s1?version=1664371652`
  - 直连 `curl` 返回 `403 Access Denied`
  - 浏览器上下文 `page.context().request.get(...)` 返回 `403`
  - 走 `7890` Clash 代理后仍返回 `403`
- MDPI 补充材料下载路径 2：`https://www.mdpi.com/article/10.3390/en15197136/s1`
  - 直连 `curl` 返回 `403 Access Denied`
  - 浏览器上下文请求同样返回 `403`
- 虽然后续已由用户手动下载到 ZIP，但“附录声称存在的 MATLAB 脚本”目前在压缩包目录中仍未见到

## 对项目的直接价值
- 这篇对你做“天气因素影响能耗”的价值很高：
  - 它不是单纯黑箱回归，而是更偏动力学+电池+任务段能耗分析
  - 适合给你的项目提供一个较强的物理先验基线
