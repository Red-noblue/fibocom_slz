# 0703 完成 DSP、SNPE 等部署

本目录记录 2026-07-03 在当前 SC171V3 / QCS6490 设备上完成的 radio-map 模型部署成果。这里的“部署成果”只包含真实 radio-map 模型或其转换产物，不包含最小 Conv / Pad 专项模型。

## 阶段状态

技术路线探索阶段已关闭。当前结论是：

- 默认部署主线：`SNPE GPU INT8 DLC`。
- 速度副主线：`SNPE DSP INT8 DLC`。
- 备用验证线：`QNN GPU .so`。
- 继续研究线：`QNN DSP / HTP / CDSP` 图兼容专项；Pad+INT8 改写版完整模型已经可执行，但精度弱于 SNPE DSP INT8。

下一阶段进入：

```text
复现实验固化 + 指标补强 + 可选后端专项
```

50/100 个 test 样本的 INT8 GPU/DSP 批量复现实验属于增强结论可信度的补强工作，不再是技术路线探索是否完成的前置条件。

## 阅读顺序

| 顺序 | 文档 | 作用 |
| --- | --- | --- |
| 1 | `01_成果总结与推荐路线.md` | 总结当前已经跑通的部署链路、主线/副主线判断和关键结论。 |
| 2 | `02_链路参数与复现指令.md` | 给出可复现命令、模型路径、runtime 参数和输入输出约定。 |
| 3 | `03_指标结果与实验产物索引.md` | 汇总本轮关键指标、实验目录和判断依据。 |

全路线命令索引：

```text
../各路线运行示例.md
```

## 一句话结论

当前默认部署路线建议使用 **SNPE GPU INT8**；如果极端优先速度，可以选择 **SNPE DSP INT8** 作为速度副主线，但需要接受更大的输出偏差。

```text
默认主线：radio_map_liteunet INT8 DLC -> Fibo AI Stack -> SNPE GPU -> Adreno GPU
速度副主线：radio_map_liteunet INT8 DLC -> Fibo AI Stack -> SNPE DSP -> Hexagon/CDSP/HTP
备用验证线：radio_map_liteunet QNN .so -> Fibo AI Stack -> QNN GPU -> Adreno GPU
```

## 当前保留的关键实验目录

| 目录 | 内容 |
| --- | --- |
| `modules/radio_map_qcs6490_deploy/outputs/int8_gpu_accuracy_20260703_114758` | FP32 GPU、SNPE INT8 GPU、QAIRT INT8 GPU 的 20 样本精度和速度对比。 |
| `modules/radio_map_qcs6490_deploy/outputs/int8_dsp_accuracy_20260703_120803` | SNPE INT8 DSP 与 GPU/FP32 的 20 样本精度和速度对比。 |
| `modules/radio_map_qcs6490_deploy/outputs/int8_repro_test50_20260703_131335` | FP32 GPU、SNPE INT8 GPU、SNPE INT8 DSP 的 50 样本固化复现实验。 |
| `modules/radio_map_qcs6490_deploy/outputs/int8_gpu_dsp_repro_test100_20260703_133812` | SNPE INT8 GPU、SNPE INT8 DSP 的 100 样本固化复现实验。 |
| `modules/radio_map_qcs6490_deploy/outputs/snpe_dsp_deep_probe_20260703_115139` | SNPE DSP INT8 长重复和 `strace` 证据。 |
| `modules/radio_map_qcs6490_deploy/outputs/int8_backend_probe_permfix_20260703_081242` | INT8 DLC 与 QNN `.so` 后端可用性矩阵。 |
| `modules/radio_map_qcs6490_deploy/outputs/qnn_htp_cdsp_minimal_probe_20260703_115916` | QNN HTP/CDSP 最小 `.so` 模型专项结果。 |
| `modules/radio_map_qcs6490_deploy/outputs/qnn_pad_constant_int8_real10_20260703_143201` | QNN DSP Pad+INT8 改写版完整 radio-map `.so` 的 10 样本真实推理结果。 |

QNN DSP 图改写专项文档：

```text
../HTP_CDSP专项/QNN_DSP图改写首轮结果.md
```
