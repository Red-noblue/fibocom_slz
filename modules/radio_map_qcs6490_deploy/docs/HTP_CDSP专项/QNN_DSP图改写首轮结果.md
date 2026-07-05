# QNN DSP 图改写首轮结果

本文记录 2026-07-03 对完整 radio-map 模型进行 QNN DSP / HTP / CDSP 图改写后的首轮结果。结论只面向当前 SC171V3 / QCS6490 设备和本机 Fibo AI Stack 2.29 环境。

## 一句话结论

QNN DSP 完整 radio-map 模型已经从“未改写 `.so` 初始化失败”推进到“Pad+INT8 改写版完整模型可执行”。但该路线 10 个真实 test 样本平均 RMSE 为 `4.571 dB`，弱于当前正式高性能路线 `SNPE DSP INT8 DLC`，因此暂时作为 HTP/CDSP 专项成果和研究线，不替代正式部署路线。

## 改写目标

早期未改写 QNN `.so` 的 DSP 初始化失败点是：

```text
Failed to validate op _enc1_c1__prepad_Pad with error 0xc26
MODEL_GRAPH_OP_VALIDATION_ERROR
```

最小复现实验进一步显示：

- `reflect Pad` 是明确的 HTP/CDSP 兼容风险点。
- FP32 普通 `Conv2d` 和 `DepthWiseConv2d` 在当前 QNN DSP 后端也会校验失败。
- 真正可突破的方向是：消除 `reflect Pad`，并使用 converter 生成的真实 INT8 QNN 图，而不是手写 Q/DQ 伪 INT8 图。

## 已生成产物

Pad 改写脚本：

```text
modules/radio_map_qcs6490_deploy/scripts/rewrite_radio_map_onnx_for_qnn_htp.py
```

推理脚本：

```text
modules/radio_map_qcs6490_deploy/scripts/run_qnn_radio_map_inference.py
```

Pad 改写 ONNX：

```text
modules/fiboaistack_229_env/inputs/qnn_htp_rewrite/radio_map_liteunet_pad_constant.onnx
```

改写报告：

```text
modules/fiboaistack_229_env/inputs/qnn_htp_rewrite/radio_map_liteunet_pad_constant.report.json
```

报告显示共改写 `14` 个 `reflect Pad`，策略是将 `mode=reflect` 改为 `mode=constant`，使用 zero padding。

Pad-only FP32 QNN `.so`：

```text
modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant/host_build/libs/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_pad_constant_qnn.so
```

Pad+INT8 QNN `.so`：

```text
modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/host_build/libs/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_pad_constant_int8_qnn.so
```

QNN INT8 网络 JSON：

```text
modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/radio_map_liteunet_pad_constant_int8_qnn_net.json
```

## 分阶段结果

| 阶段 | 产物 | QNN DSP 结果 | 判断 |
| --- | --- | --- | --- |
| 未改写 FP32 `.so` | `libradio_map_liteunet_qnn.so` | 初始化失败在 `_enc1_c1__prepad_Pad` | 进入 HTP/CDSP，但图校验失败。 |
| Pad-only FP32 `.so` | `libradio_map_liteunet_pad_constant_qnn.so` | 失败点后移到 `_enc1_c1_depth_Conv` / `DepthWiseConv2d` | Pad 改写有效，但 FP32 depthwise 仍不被 HTP 接受。 |
| Pad+INT8 `.so` | `libradio_map_liteunet_pad_constant_int8_qnn.so` | 初始化并执行成功 | 完整 radio-map QNN DSP 首次跑通。 |

## INT8 接口发现

Pad+INT8 `.so` 不能继续使用原来的 float 输入输出路径。

当前正确调用方式是：

- 根据 QNN JSON 中 input `scale` / `offset` 对 float 输入手动量化。
- 调用 `Execute_uint8`，不要调用 `Execute_float`。
- 调用 `FetchOutputs_uint8`，不要调用 `FetchOutputs_float`。
- 根据 QNN JSON 中 output `scale` / `offset` 对 uint8 输出反量化。

如果继续用 float 路径，会出现输出 shape 异常、NaN 或严重数值错误，不能作为有效精度结果。

## 真实样本指标

10 样本批量中的 `166_k0`：

| 项目 | 结果 |
| --- | ---: |
| 输出 shape | `256x256` |
| 平均耗时 | `81.58 ms` |
| RMSE | `4.239 dB` |
| MAE | `2.592 dB` |

10 个真实 test 样本：

```text
modules/radio_map_qcs6490_deploy/outputs/qnn_pad_constant_int8_real10_20260703_143201
```

| 项目 | 结果 |
| --- | ---: |
| 成功样本 | `10/10` |
| 平均耗时 | `90.18 ms` |
| 平均 RMSE | `4.571 dB` |
| 平均 MAE | `2.931 dB` |

对照当前正式路线：

| 路线 | 样本数 | 平均耗时 | RMSE | MAE | 当前定位 |
| --- | ---: | ---: | ---: | ---: | --- |
| SNPE GPU INT8 DLC | 100 | `312.34 ms` | `3.475 dB` | `2.185 dB` | 默认精度模式 |
| SNPE DSP INT8 DLC | 100 | `86.78 ms` | `3.834 dB` | `2.399 dB` | 高性能模式 |
| QNN DSP Pad+INT8 `.so` | 10 | `90.18 ms` | `4.571 dB` | `2.931 dB` | HTP/CDSP 专项研究线 |

## 复现命令

QNN DSP Pad+INT8 单样本推理：

```bash
._envs/radio-map-qcs6490-py38/bin/python \
  modules/radio_map_qcs6490_deploy/scripts/run_qnn_radio_map_inference.py \
  --model modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/host_build/libs/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_pad_constant_int8_qnn.so \
  --qnn-json modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/radio_map_liteunet_pad_constant_int8_qnn_net.json \
  --features-dir modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3 \
  --sample-id 166_k0 \
  --runtime DSP \
  --warmup 1 \
  --repeat 3 \
  --log-level ERROR \
  --output-dir modules/radio_map_qcs6490_deploy/outputs/manual_qnn_pad_constant_int8_dsp
```

注意：如果脚本已内置默认 QNN INT8 产物路径，可省略 `--model` 和 `--qnn-json`，但复现实验建议显式写出路径，避免误用未改写 `.so`。

## 当前判断

这轮专项已经证明：

- 未改写 QNN DSP 完整模型失败不是 runtime 字符串问题，而是 HTP/CDSP 图兼容问题。
- `reflect Pad -> constant zero Pad` 能绕过最早的 Pad 校验失败。
- 仅改 Pad 的 FP32 图仍会卡在 depthwise 相关节点。
- Pad+INT8 改写版完整 radio-map `.so` 能在 QNN DSP 路线执行，并输出完整 `256x256` 结果。
- 当前 QNN DSP Pad+INT8 精度弱于 SNPE DSP INT8，因此不升级为正式部署主线。

后续如果继续推进 QNN DSP，应优先研究结构层面的精度损失，而不是继续反复验证“是否能初始化”。重点包括：

1. 对比 `reflect Pad` 和 zero padding 对 PyTorch / ONNX CPU 输出的影响。
2. 尝试对边界区域单独评估误差，判断 zero padding 是否主要损伤边缘预测。
3. 研究是否能用 HTP 可接受的等价 padding 结构替代 reflect padding。
4. 若要追求 QNN DSP 正式部署，继续补 50/100 样本，并与 SNPE DSP INT8 做同样样本集合的配对输出差异。
