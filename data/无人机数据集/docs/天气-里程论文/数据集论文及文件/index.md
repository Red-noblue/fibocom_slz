# 数据集论文及文件总索引

更新时间：2026-03-12

## 01_M100飞行位置与能耗数据集_2021
- 论文：`In-flight positional and energy use data set of a DJI Matrice 100 quadcopter for small package delivery`
- DOI：`10.1038/s41597-021-00930-x`
- 当前状态：论文 PDF、补充材料、数据集、arXiv LaTeX 源码、源码编译 PDF、中文手工翻译副本、完整中文 PDF 均已落盘
- 备注：这是目前第一篇完成“英文源码编译 + 手工中文翻译 + 中文 PDF 编译”全链路的论文

## 02_小包裹配送飞行数据与能耗模型_2022
- 论文：`Drone flight data reveal energy and greenhouse gas emissions savings for very small package delivery`
- DOI：`10.1016/j.patter.2022.100569`
- 当前状态：正文可读 PDF、页面快照、S1/S2 补充材料、共享数据位置说明、Zenodo 代码包、arXiv 预印本 LaTeX 源码、源码编译 PDF、中文翻译副本、完整中文 PDF 均已落盘
- 备注：出版社开放稿件入口仍受限，但对应预印本源码已获取，并已完成“英文源码编译 + 手工中文翻译 + 中文 PDF 编译”
  - 本地已去重：原 `02/data/12683453.zip` 与 `01` 目录中的 figshare 数据包相同，重复副本已删除

## 03_多旋翼风估计_2022
- 论文：`Wind Estimation with Multirotor UAVs`
- DOI：`10.3390/atmos13040551`
- 当前状态：正文可读 PDF、页面快照、GitHub 代码仓库、Dataverse 元数据、小文件、`Svalbard` 与 `EPFL` 两个核心数据包均已落盘
- 备注：数据和代码齐全，并已补充确认相关硕士论文 PDF 公开可得；但截至 `2026-03-12` 的窄范围核查仍未找到公开 LaTeX 源码，所以暂时不能按你的标准继续做源码编译版 PDF

## 04_四旋翼能耗分析模型_2022
- 论文：`Quadrotor Model for Energy Consumption Analysis`
- DOI：`10.3390/en15197136`
- 当前状态：正文可读 PDF、页面快照、补充 ZIP 已落盘
- 备注：补充包 `energies-15-07136-s001.zip` 已由用户手动下载并归档；当前压缩包内能确认有 `Case 1`、`Case 2` 的飞行日志、`.waypoints`、`.log.param` 等文件，但暂未看到论文附录里提到的 `Trajectory` MATLAB 脚本目录

## 05_全球无人机天气飞行约束_2021
- 论文：`Weather constraints on global drone flyability`
- DOI：`10.1038/s41598-021-91325-w`
- 当前状态：官方 PDF、3 个补充文件已落盘
- 备注：论文正文声明，若数据不在补充材料中，则需向通讯作者申请；代码也不是公开仓库形式，而是 `on request`

## 06_无人机电池放电在线预测_2022
- 论文：`A data-driven learning method for online prediction of drone battery discharge`
- DOI：`10.1016/j.ast.2022.107921`
- 当前状态：正文可读 PDF、页面快照已落盘
- 备注：`Data availability` 明确写的是 `Data will be made available on request`，当前无公开数据包/代码包

## 当前最关键结论
- 真正最适合本项目直接借用的数据核心，还是 `01 + 02 + 03 + 04` 这四组资源。
- 其中 `01` 与 `02` 现在都已经完成“公开 LaTeX 源 -> 本地编译英文 PDF -> 复制源码目录 -> 手工中文翻译 -> 编译中文 PDF”的完整链路。
- `01` 仍是最完整、最可复现的数据底座；`02` 则是最直接的能耗建模方法参考。
- `03` 对天气/风场建模价值很高，而且现在已经拿到代码仓库和主要数据入口。
- `04` 的补充 ZIP 已突破，但其中 MATLAB 脚本是否缺失，还需要按解压结果继续核对。
