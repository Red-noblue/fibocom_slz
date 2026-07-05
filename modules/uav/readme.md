# UAV Modules

当前先围绕 `/home/fibo/uav_cma_realtime_gis_demo` 做两条子项目级拆分：

- `uav-weather-energy-predictor`
  固定航线、固定机型条件下的天气驱动能耗预测 demo 子项目。
- `uav-gis-replay-studio`
  消费预测结果的 GIS 地图与回放展示 demo 子项目。

这两个子项目都属于“从现有 demo 抽取并轻量重构”的第一阶段结果。

## 环境启动

当前工作区提供了项目内自举工具 `tools/env-bootstrap`，用于在
仓库根目录的 `._envs/uav-modules-py310` 下构建共享 Python 环境，而不要求
机器预装 Conda。

当前不再依赖 `modules/uav/.vendor` 或 `modules/uav/.venv` 这类模块内历史环境目录，
统一通过共享环境运行。

常用命令：

```bash
./tools/env-bootstrap/bin/env-bootstrap sync \
  ./tools/env-bootstrap/manifests/uav-modules.env.sh

./tools/env-bootstrap/bin/env-bootstrap run \
  ./tools/env-bootstrap/manifests/uav-modules.env.sh -- \
  python --version
```

这套环境会把下面两个子包都安装进同一个前缀环境：

- `uav-weather-energy-predictor`
- `uav-gis-replay-studio`
