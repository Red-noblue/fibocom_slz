# 01 索引

## 基本信息
- 标题：`In-flight positional and energy use data set of a DJI Matrice 100 quadcopter for small package delivery`
- 正式 DOI：`10.1038/s41597-021-00930-x`
- arXiv：`2103.13313`
- 论文方向：四旋翼飞行位置与能耗数据集

## 已下载内容
- `paper/article.pdf`
  - Nature 官方 PDF
- `supplement/supplementary_information.pdf`
  - 官方补充材料
- `data/12683453.zip`
  - 用户手动下载的 figshare 数据集压缩包
- `latex/arxiv_source.tar`
  - arXiv 源码包
- `latex/source/`
  - 解包后的 LaTeX 源文件
- `latex/compiled_from_source.pdf`
  - 本地使用 `tectonic` 编译得到的 PDF
- `latex/source_zh_manual/`
  - 手工中文翻译工作副本，不改动原英文源码
- `latex/compiled_zh_manual.pdf`
  - 基于中文副本编译得到的完整中文 PDF，已覆盖正文、图表题注与附录
- `code/castacks_DOE/`
  - 从论文给出的 Bitbucket 项目页 `https://bitbucket.org/castacks/workspace/projects/DOE` 拉取的 15 个公开仓库

## LaTeX 源码状态
- 公开可获取：是
- 本地编译：成功
- 编译说明：
  - 原始源码里的 `breakurl` 与当前 `tectonic/xetex` 组合不兼容
  - 已做最小兼容修复：仅在 `\ifpdf` 条件下加载 `breakurl`
- 中文工作副本：
  - 已创建 `latex/source_zh_manual/`
  - 已完成手工逐句翻译，并用用户目录 TinyTeX 的 `xelatex` 编译出完整中文 PDF
  - 当前正式中文产物为 `latex/compiled_zh_manual.pdf`

## 对项目的直接价值
- 这是当前最完整的基础数据论文。
- 直接提供四旋翼飞行轨迹、能耗、风、载荷、速度、海拔等高分辨率原始数据。
- 可作为你后续“天气因素对能耗影响”项目的数据底座和训练/验证底座。

## 关联代码状态
- 代码来源：论文 LaTeX/HTML 中给出的 Bitbucket 项目页 `castacks/DOE`
- 本地拉取：成功
- 仓库数量：15 个
- 与本项目最相关的目录：
  - `doe_ws`
  - `dji_doe`
  - `doe_pi_record`
  - `environmental_sensor`
  - `anemometer`
  - `wind_query_ros`

## 当前缺口
- 中文逐句翻译主线已完成，当前未发现整段正文英文残留
- 仍可继续细修个别专有名词、品牌名、参考文献题名的中英文保留策略
- 尚未逐仓库核对哪些脚本可直接复现论文中的采集与处理流程
