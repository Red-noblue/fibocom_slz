# 02 索引

## 基本信息
- 标题：`Drone flight data reveal energy and greenhouse gas emissions savings for very small package delivery`
- DOI：`10.1016/j.patter.2022.100569`
- 论文方向：小包裹配送四旋翼能耗与碳排模型

## 已下载内容
- `paper/article.pdf`
  - 由 ScienceDirect 正文页打印生成的可读 PDF
- `html/article.html`
  - 文章页 HTML
- `html/article_snapshot.md`
  - 正文页面快照
- `supplement/Document_S1.pdf`
  - 补充实验流程、附图、附表
- `supplement/Document_S2.pdf`
  - 文章加补充信息合并版
- `data/README_共享数据位置说明.md`
  - 原重复数据包已删除，改为保留位置说明
  - 共享数据请直接使用 `../01_M100飞行位置与能耗数据集_2021/data/12683453.zip`
- `code/drone_energy_consumption-v1.0.0.zip`
  - Zenodo 代码包
- `latex/arxiv_source.tar`
  - arXiv 预印本源码包
- `latex/source/`
  - 解包后的 LaTeX 源文件
- `latex/compiled_from_source.pdf`
  - 本地使用 TinyTeX `xelatex + biber` 编译得到的英文 PDF
- `latex/source_zh_manual/`
  - 手工中文翻译工作副本，不改动原英文源码
- `latex/compiled_zh_manual.pdf`
  - 基于中文副本编译得到的完整中文 PDF

## 资源说明
- 页面中明确给出：
  - 数据 DOI：`10.1184/R1/12683453`
  - 代码 DOI：`10.5281/zenodo.6726991`
- 本地去重说明：
  - 原 `02/data/12683453.zip` 与 `01/data/12683453.zip` 的 SHA-256 完全一致
  - 为节省空间，已删除 `02` 目录中的重复副本，仅保留说明文档
- 代码包已验证不是空壳，包含：
  - Python 脚本
  - R/XGBoost 建模脚本
  - 预测结果 CSV
  - README

## LaTeX 源码状态
- 公开可获取：是
- 当前可编译源码来源：
  - `arXiv 2111.11463` 的源码包
  - 根据作者、题名和正文内容判断，这是这篇期刊工作的对应预印本源码
- 本地编译：成功
- 编译说明：
  - 仅靠 `tectonic` 无法完成，因为本机初始环境缺 `biber` 且版本链不匹配
  - 已改用用户目录 TinyTeX 工具链，用 `xelatex + biber` 完成编译
- 中文工作副本：
  - 已创建 `latex/source_zh_manual/`
  - 已完成手工逐句翻译，并编译生成 `latex/compiled_zh_manual.pdf`

## 失败/受限项
- 官方签名 PDF 直链：
  - 浏览器内可打开
  - `curl` 直接下载稳定返回 `403`
- `View Open Manuscript`：
  - 直连 `curl` 返回 `403`
  - 目前仍无法直接拉到出版社页面暴露的开放稿件
  - 但已经通过 arXiv 预印本源码获得可编译 LaTeX 版本

## 对项目的直接价值
- 这篇是 `01` 数据集上的能耗/碳排建模论文。
- 对你的项目最重要的价值在于：
  - 现成的能耗建模代码
  - 对速度、载荷、距离、碳排关系的建模方法
  - 可直接学习其从原始飞行数据到能耗模型的处理流程

## 当前缺口
- 中文逐句翻译主线已完成，当前未发现整段正文英文残留
- 仍需逐文件核对 Zenodo 代码包中哪些脚本可直接迁移到你的项目流程
- 出版社 `View Open Manuscript` 入口依旧受限，但这不影响使用已验证可编译的 arXiv 源码链路
