# QCS6490 无线电地图部署适配

本模块用于在当前 SC171V3/QCS6490 设备上部署和验证无线电地图估计模型。它不承担训练任务，也不直接修改论文项目源码。

## 目标

- 复用论文项目中的模型权重、特征样本和历史评测结果。
- 在本机完成 PyTorch CPU、ONNX CPU、Fibo AI Stack / Qualcomm 后端等部署路线验证。
- 记录本机推理延迟、内存占用、输出一致性和误差指标。

## 目录

```text
configs/   部署配置模板和本机路径配置
scripts/   后续放置一键导出、推理、验证脚本
src/       部署适配 Python 包
tests/     部署侧测试
outputs/   本模块生成的本机部署产物
docs/      部署路线、设备资源和验证记录
```

## 上游资产

默认上游项目：

```text
../radio-map-estimation-workbench
```

建议只通过配置文件引用上游路径，不使用软链接，不复制大体积训练产物。

## 初始部署路线

1. PyTorch CPU 加载历史 checkpoint，复核单样本和小批量输出。
2. 导出固定输入形状 ONNX：`[1, 7, 256, 256] -> [1, 1, 256, 256]`。
3. ONNX Runtime CPU 与 PyTorch 输出做数值对齐。
4. 调查并接入 Fibo AI Stack / Qualcomm QNN 或 TFLite 路线。

## 本机 Fibo AI Stack 流程

- [当前推荐部署路线](docs/当前推荐部署路线.md)
- [Fibo AI Stack 本机部署流程](docs/Fibo_AI_Stack本机部署流程.md)
- [本机部署学习笔记](docs/本机部署学习笔记/README.md)
- [0703 完成 DSP、SNPE 等部署成果总结](docs/0703-完成DSP、SNPE等部署/README.md)

当前状态：技术路线探索已关闭，后续进入“复现实验固化 + 指标补强 + 可选后端专项”阶段。

## 当前可运行入口

部署就绪检查：

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/check_deploy_readiness.py
```

SNPE GPU 单样本推理：

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/run_snpe_gpu_inference.py \
  --sample-id 166_k0 \
  --runtime GPU
```

真实样本 CPU/GPU 输出对齐：

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/align_snpe_outputs_with_real_sample.py \
  --sample-id 166_k0
```

批量 test 样本复现实验：

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/batch_snpe_int8_repro.py \
  --limit 50 \
  --warmup 1 \
  --repeat 1 \
  --output-dir modules/radio_map_qcs6490_deploy/outputs/int8_repro_test50_$(date +%Y%m%d_%H%M%S)
```

当前基准：

| 样本数 | 成功数 | SNPE CPU 平均耗时 | SNPE GPU 平均耗时 | 平均加速比 | CPU/GPU dBm RMSE | GPU 对标签 RMSE |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 20 | `1339.92 ms` | `335.89 ms` | `3.99x` | `0.0158 dB` | `3.279 dB` |
| 50 | 50 | `1290.16 ms` | `332.48 ms` | `3.89x` | `0.0158 dB` | `3.549 dB` |
| 100 | 100 | `1278.57 ms` | `331.16 ms` | `3.87x` | `0.0155 dB` | `3.473 dB` |

结论：SNPE GPU 在 100 个 test 样本上可重复运行，且相对 CPU 有稳定约 `3.9x` 加速；CPU/GPU 输出差异远小于标签误差，适合作为当前本机部署主线。

0703 新增 INT8 / DSP 结果：

| 路线 | 样本数 | 平均耗时 | 标签 RMSE | 标签 MAE | 对 FP32 GPU 差异 | 当前定位 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| SNPE GPU FP32 DLC | 100 | `331.16 ms` | `3.473 dB` | - | - | 稳定基线 |
| SNPE GPU INT8 DLC | 20 | `302.10 ms` | `3.299 dB` | `2.040 dB` | `0.184 dB RMSE` | 默认主线 |
| QAIRT GPU INT8 DLC | 20 | `306.39 ms` | `3.299 dB` | `2.040 dB` | `0.184 dB RMSE` | 可替代 INT8 GPU |
| SNPE DSP INT8 DLC | 20 | `83.09 ms` | `3.649 dB` | `2.241 dB` | `1.633 dB RMSE` | 速度副主线 |
| QAIRT DSP INT8 DLC | 20 | `82.74 ms` | `3.649 dB` | `2.241 dB` | `1.633 dB RMSE` | 速度副主线 |
| SNPE GPU FP32 DLC | 50 | `320.10 ms` | `3.549 dB` | `2.203 dB` | - | 50 样本基线 |
| SNPE GPU INT8 DLC | 50 | `316.16 ms` | `3.553 dB` | `2.199 dB` | `0.175 dB RMSE` | 默认主线，已补强 |
| SNPE DSP INT8 DLC | 50 | `88.41 ms` | `3.868 dB` | `2.398 dB` | `1.728 dB RMSE` | 速度副主线，已补强 |
| SNPE GPU INT8 DLC | 100 | `312.34 ms` | `3.475 dB` | `2.185 dB` | 未重跑 FP32 配对差异 | 默认主线，100 样本通过 |
| SNPE DSP INT8 DLC | 100 | `86.78 ms` | `3.834 dB` | `2.399 dB` | 对 INT8 GPU `1.715 dB RMSE` | 速度副主线，100 样本通过 |

结论更新：当前默认部署路线建议使用 `SNPE GPU INT8 DLC`；如果关注速度且接受 100 样本中 DSP 相对 GPU 约 `1.715 dB RMSE` 的输出差异，可以把 `SNPE DSP INT8 DLC` 作为高性能模式使用，并继续保留 FastRPC/CDSP 证据复核。

HTP/CDSP 专项说明：

```text
docs/HTP_CDSP专项/README.md
docs/HTP_CDSP专项/QNN_DSP图改写首轮结果.md
```

当前 HTP/CDSP 结论：

- SNPE GPU FP32 / INT8 已确认是真实 Adreno GPU 路线。
- SNPE DSP INT8 已通过 `strace` 看到 `/dev/adsprpc-smd-secure`、`/dsp/cdsp`、`libSnpeHtpV68Stub.so`、`libSnpeHtpV68Skel.so` 和 FastRPC DMA 分配证据，当前不再按 CPU fallback 处理。
- SNPE HTP / NPU 初始化虽然可返回成功，但耗时接近 CPU，仍按疑似 CPU fallback 处理。
- QNN GPU `.so` 可运行，可作为备选验证路线。
- QNN DSP 未改写完整 radio-map `.so` 确实进入 HTP/CDSP 初始化路径，但失败在 `_enc1_c1__prepad_Pad` 等图校验节点。
- QNN DSP Pad+INT8 改写版完整 radio-map `.so` 已经可执行，10 个真实 test 样本平均 `90.18 ms`，RMSE `4.571 dB`，MAE `2.931 dB`；当前作为 HTP/CDSP 专项研究线，不替代 SNPE DSP INT8 高性能模式。
- QNN DSP 最小 INT8 `.so` 已跑通普通 Conv 和 DepthWiseConv2d，对 full radio-map HTP/CDSP 改写有参考价值。

## 当前约束

- 本模块不使用项目中面向昇腾 310B1 的 M6 文档和脚本。
- 本模块不训练模型。
- 所有失败或中断的无意义部署产物应及时从 `outputs/` 清理。
