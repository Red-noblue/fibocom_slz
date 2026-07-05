# 附录 A 与数据可得性逐句翻译（第二版）

## Data Availability Statement
- 原文：`Flight data are available as Supplementary Materials.`
- 译文：飞行数据以补充材料的形式提供。

- 原文：`Simulation information will be available on request to the corresponding author’s email with appropriate justification.`
- 译文：仿真相关信息在给出合理说明后，可通过联系通讯作者邮箱申请获取。

## Appendix A. Flight Data and MATLAB Scripts
- 原文：`Appendix A. Flight Data and MATLAB Scripts`
- 译文：附录 A. 飞行数据与 MATLAB 脚本。

- 原文：`The folder “Supplementary Materials” includes the two subfolders “Case 1” and “Case 2” with flight data logs in “TLOG” and “BIN” formats.`
- 译文：`Supplementary Materials` 文件夹中包含两个子文件夹：`Case 1` 和 `Case 2`，其中存放的是 `TLOG` 与 `BIN` 格式的飞行数据日志。

- 原文：`These data could be viewed using UAV Log Viewer online service that is available at:`
- 译文：这些数据可以通过下面这个在线 `UAV Log Viewer` 服务查看：

- 原文：`https://plot.ardupilot.org/#/ (accessed on 13 September 2022).`
- 译文：`https://plot.ardupilot.org/#/`（作者访问日期为 `2022-09-13`）。

- 原文：`and Mission Planner software:`
- 译文：也可以使用 `Mission Planner` 软件查看：

- 原文：`https://ardupilot.org/copter/docs/common-downloading-and-analyzing-data-logs-in-mission-planner.html (accessed on 13 September 2022).`
- 译文：`https://ardupilot.org/copter/docs/common-downloading-and-analyzing-data-logs-in-mission-planner.html`（作者访问日期为 `2022-09-13`）。

- 原文：`Additionally, files with “*.log” extension includes data about quadrotor configuration.`
- 译文：此外，扩展名为 `*.log` 的文件中还包含四旋翼构型配置相关的数据。

- 原文：`Files with “*.waypoints” extension include the coordinates of trajectory waypoints.`
- 译文：扩展名为 `*.waypoints` 的文件包含轨迹航点的坐标信息。

- 原文：`In “Trajectory” there are MATLAB scripts that could be used to reproduce similar trajectory as presented in “Case 2” (the user could change some parameters).`
- 译文：在 `Trajectory` 目录中，作者提供了 MATLAB 脚本，可用于复现与 `Case 2` 中展示的轨迹相似的飞行轨迹，使用者也可以自行修改其中部分参数。

## 这部分对项目的直接意义
- 这段附录最关键的价值，不是“它说自己有补充材料”，而是它把补充材料里大致会有什么说清楚了：
  - 有原始飞行日志
  - 有航点文件
  - 有可复现轨迹的 MATLAB 脚本
- 如果后续能突破下载，这批材料会直接补上你做“天气/风场扰动下能耗分析”的实验输入链路。
