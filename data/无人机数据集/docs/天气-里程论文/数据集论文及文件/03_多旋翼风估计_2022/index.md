# 03 索引

## 基本信息
- 标题：`Wind Estimation with Multirotor UAVs`
- DOI：`10.3390/atmos13040551`
- 数据 DOI：`10.18710/AFDYLS`
- 代码仓库：`https://github.com/meierkilian/WEMUAV`
- 论文方向：多旋翼风速/风向估计

## 已下载内容
- `paper/article.pdf`
  - 由 MDPI 正文页打印生成的可读 PDF
- `html/article_snapshot.md`
  - 正文页面快照
- `code/WEMUAV/`
  - GitHub 仓库已完整克隆
- `data/dataverse_export.json`
  - Dataverse 元数据导出
- `data/00_README.txt`
- `data/01_DATA_OVERVIEW.csv`
- `data/01_DATA_OVERVIEW.xlsx`
- `data/03_SVALBARD_FLIGHTS.zip`

## 大文件数据包
- `data/02_EPFL_FLIGHTS.zip`
  - 数据源明确存在
  - 已下载完成
  - 本地文件大小：`6468142762 bytes`
  - 已用 `zipinfo -1` 验证可正常读取压缩包目录
  - 压缩包中可见 `EPFL20210419/FLIGHT/`、`EPFL20210419/WEATHER/` 等目录结构

## LaTeX 源码状态
- 公开可获取：当前未找到
- 已做的精准核查：
  - 精确题名查询 arXiv，返回 `0` 条结果
  - 本地克隆的 `code/WEMUAV/` 中未发现 `.tex/.bib/.cls/.sty` 论文源码文件
  - `meierkilian` 的公开 GitHub 仓库窄范围核查中，仅发现 `WEMUAV` 一个相关仓库
  - `WEMUAV` 远端仅有 `main` 分支和 `v1.0`、`v1.1` 两个 tag；tag 内容中同样未发现 `.tex/.bib/.cls/.sty` 文件
  - `WEMUAV` 仓库内附带 `Master_Thesis_KilianMeier.pdf`，且作者合作者公开目录 `https://richahan.folk.ntnu.no/Publications/` 也能看到 `2021_Meier_Thesis.pdf`，但目录公开内容只有 PDF，没有源码压缩包
  - 浏览器态核查 MDPI 实时页面时，当前公开可见入口只有 `Download PDF`、`Version Notes`、`Order Reprints`，未见 `LaTeX/XML/source/zip` 入口
  - Crossref/MDPI 元数据只暴露了正式论文页面与数据/代码入口，没有公开 LaTeX 源码入口
- 当前结论：
  - 这篇论文的数据和代码是公开且很有价值的
  - 公开可获取的“相关文稿”目前能确认有期刊页 PDF 和硕士论文 PDF
  - 但按你要求的“必须由公开 LaTeX 源码编译 PDF”的标准，目前仍不能算处理完成

## 对项目的直接价值
- 这是天气/风场方向最关键的论文之一。
- 它对你的价值不只是“风估计”本身，而是：
  - 提供飞行日志与对应气象数据
  - 给出多旋翼风估计建模思路
  - 提供现成代码仓库，便于复现与改造

## 失败/受限项
- `html/article.html` 是早期 `curl` 抓取到的 MDPI `Access Denied` 页面，不能作为正文真相源
- 官方 PDF 直链被 MDPI/Akamai 拦截，当前使用页面打印版代替
- 截至 `2026-03-12` 的窄范围核查中，仍未发现公开 LaTeX 源码
