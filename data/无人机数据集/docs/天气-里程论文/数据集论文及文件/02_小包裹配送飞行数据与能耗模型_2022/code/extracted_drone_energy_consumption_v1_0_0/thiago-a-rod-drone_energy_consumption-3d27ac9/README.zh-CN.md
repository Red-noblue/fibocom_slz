# 02 论文代码中文说明

## 1. 项目用途

这是论文 `Drone flight data reveal energy and greenhouse gas emissions savings for very small package delivery` 的配套代码包中文说明。

这套代码的核心作用不是重新采集数据，而是：

- 使用 `01_M100飞行位置与能耗数据集_2021` 中的 `flights.csv`
- 将单次飞行切分为 `takeoff / cruise / landing`
- 生成分阶段能耗汇总
- 拟合论文中的线性能耗模型
- 进一步生成能耗、碳排、区域比较等结果图表

## 2. 本地复现所需输入

除代码包自带文件外，还需要以下外部数据：

- `data/flights.csv`
  - 来源：`01_M100飞行位置与能耗数据集_2021/data/extracted_12683453/flights.csv`
- `data/CO₂ equivalent non-baseload output emission rate (lb_MWh), by eGRID subregion, 2020.csv`
  - 本地由 EPA 官方 `eGRID2020_data_metric_v2.xlsx` 转换生成
- `data/eGRID2020_subregions.shp` 及其配套 `.dbf/.shx/.prj/.cpg/.sbn/.sbx`
  - 来源：EPA 官方 `egrid2020_subregions.zip`

## 3. 本地环境

已在当前目录创建独立虚拟环境：

- `.venv/`

已安装的关键依赖包括：

- `pandas`
- `matplotlib`
- `scipy`
- `seaborn`
- `metar`
- `geopandas`
- `openpyxl`

## 4. 复现命令

在当前目录执行：

```bash
. .venv/bin/activate
PYTHONWARNINGS=ignore::DeprecationWarning MPLBACKEND=Agg python main.py
```

其中：

- `MPLBACKEND=Agg` 用于无界面环境下保存图片
- `PYTHONWARNINGS=ignore::DeprecationWarning` 仅用于压制新版库的弃用警告噪音，不影响结果

## 5. 当前已成功复现的流程

已确认可跑通以下完整链路：

1. `pre_processing.py`
2. `regime.py`
3. `energy_summary.py`
4. `energy_model.py`
5. `power_speed.py`
6. `energy_distance.py`
7. `ghg_emission.py`
8. `ghg_subregions.py`
9. `vehicle_comparison.py`
10. `ARE.py`
11. `main.py`

`main.py` 已在本地端到端执行成功，最终输出 `Status: Completed`

## 6. 当前已生成的关键结果

主要中间结果与输出包括：

- `data/flights_processed.csv`
- `data/energy_summary.csv`
- `data/coefficients.csv`
- `data/vehicles.csv`
- `results/table1.csv`
- `results/table2.csv`
- `results/table3.csv`
- `results/tableS2.csv`
- `results/tableS3.csv`
- `results/tableS4.csv`
- `results/figure3.pdf`
- `results/figure4.pdf`
- `results/figure5.pdf`
- `results/figure7.pdf`
- `results/figureS1.pdf`
- `results/figureS2.pdf`
- `results/figureS3.pdf`
- `results/figureS4.pdf`
- `results/figureS5.pdf`
- `results/figureS6.pdf`
- `results/figureS12.pdf`

## 7. 为兼容当前环境所做的最小修复

以下修改仅用于兼容当前 Python 科学计算库版本，不改变论文方法本身：

- `regime.py`
  - 修复旧版 `pandas` 写法在新版本中的报错
- `METAR_KAGC.py`
  - 为相同 URL 增加缓存，减少重复下载气象数据
- `ghg_subregions.py`
  - 修复新版 `matplotlib` 下 `colorbar` 需要显式绑定 `ax` 的问题
- `vehicle_comparison.py`
  - 修复新版 `matplotlib` 的刻度字体设置方式
  - 修复误差条数组中出现负值导致的绘图报错

## 8. 仍需注意的点

- `R-XGBoost-Model/` 对应的是补充机器学习流程，本机当前未安装 `R`，因此未按 R 版本原样复现
- 论文主线 Python 流程已经完整跑通，但补充的 R 训练流程仍是后续可选项
- 代码中仍会出现少量 `FigureCanvasAgg is non-interactive` 提示，这是因为当前采用无界面后端保存图像，不影响结果文件生成
