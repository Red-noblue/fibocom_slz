# HTP CDSP 专项

本专项用于单独研究当前 QCS6490 设备上的 Hexagon/CDSP/HTP 路线。它不阻塞 SNPE GPU 主线部署。

## 0703 更新结论

- SNPE DSP INT8 已经不再按 CPU fallback 处理：`strace` 看到 `/dev/adsprpc-smd-secure`、`/dsp/cdsp`、`libSnpeHtpV68Stub.so`、`libSnpeHtpV68Skel.so` 和 FastRPC DMA 分配，长 repeat 平均耗时约 `80 ms`。
- SNPE DSP INT8 当前定位为速度副主线：20 个真实 test 样本平均约 `83 ms`，但标签 RMSE/MAE 弱于 SNPE GPU INT8。
- SNPE HTP/NPU 初始化返回成功不代表真实加速，目前仍按疑似 CPU fallback 处理。
- QNN DSP 未改写完整 radio-map `.so` 不是 fallback，而是进入 HTP/CDSP 后在模型图校验阶段失败，典型失败点仍包括 `_enc1_c1__prepad_Pad`。
- QNN DSP Pad+INT8 改写版完整 radio-map `.so` 已经可执行，10 个真实 test 样本平均 `90.18 ms`，RMSE `4.571 dB`，MAE `2.931 dB`；当前作为专项研究线，不替代 SNPE DSP INT8 高性能模式。
- QNN DSP 最小 INT8 `.so` 已跑通普通 Conv 与 DepthWiseConv2d，对后续 full 模型图改写有参考价值。
- 阶段成果、指标和复现指令见 `../0703-完成DSP、SNPE等部署/README.md`。
- 图改写首轮结果见 `QNN_DSP图改写首轮结果.md`。

## 专项目标

把下面两个现象拆成可验证问题：

1. SNPE DSP/NPU 返回成功，但速度和输出表现接近 CPU。
2. QNN DSP 确实进入 HTP/CDSP 初始化路径，但未改写模型初始化失败；进一步验证 Pad+INT8 改写后是否能执行完整模型。

## 当前设备证据

本机基础信息：

| 项目 | 值 |
| --- | --- |
| device-tree model | Qualcomm Technologies, Inc. Yupik IoT Open Dev Kit + HDMI |
| machine | YUPIKP-IOT |
| soc_id | 498 |
| family | Snapdragon |
| GPU | Adreno643v1 |

关键设备节点：

```text
/dev/kgsl-3d0
/dev/adsprpc-smd
/dev/adsprpc-smd-secure
/dev/ion
```

Fibo SDK 关键库：

```text
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libSNPE.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnHtp.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnHtpV68Stub.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libSnpeHtpV68Stub.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/hexagon-v68/libQnnHtpV68Skel.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/hexagon-v68/libSnpeHtpV68Skel.so
```

这些说明本机具备 CDSP/HTP 运行环境，但不等价于当前模型已经跑通 CDSP/HTP。

## 问题 1: SNPE DSP/NPU 是否真实使用硬件

当前判断：

- SNPE DSP 会设置 `dsp_fixed8_tf`，但同时也设置 `cpu_float32`。
- `strace` 已确认 SNPE DSP 会打开 `libSnpeHtpV68Stub.so`、`/usr/lib/libcdsprpc.so`、`/dev/adsprpc-smd-secure` 和 `hexagon-v68/libSnpeHtpV68Skel.so`。
- SNPE DSP 日志中有大量 `The SocModel doesn't support FP16`。
- SNPE DSP/NPU 速度接近 CPU。
- SNPE DSP/NPU 输出与 CPU 完全一致或非常接近。
- SNPE NPU 当前没有看到类似 SNPE DSP 的 HTP/CDSP 库加载证据，主要表现仍接近 CPU。
- 当前 DLC 是 FP32，未量化。

结论：

- 不能把 SNPE DSP/NPU 的返回成功视为真实硬件加速成功。
- 当前推荐只把 SNPE DSP/NPU 作为待研究对象，不作为部署主线。

需要补充的证据：

- 对比 CPU/DSP/NPU 的 FastRPC 计数器变化。
- 对比更长 repeat 下的稳定耗时。
- 若后续生成量化 DLC，再重新验证 SNPE DSP 是否具备真实加速。

## 问题 2: QNN DSP 为什么失败

未改写完整 `.so` 的失败特征：

```text
The SocModel doesn't support FP16
QnnBackend_validateOpConfig failed 3110
Failed to validate op _enc1_c1__prepad_Pad with error 0xc26
MODEL_GRAPH_OP_VALIDATION_ERROR
```

未改写模型结构证据：

- ONNX 中存在多个 `Pad` 节点。
- 第一个失败节点对应 `/enc1/c1/_prepad/Pad`。
- 该节点来自 reflect padding。
- 当前 QNN 模型库是 FP32 路线。

早期工作假设：

QNN DSP 失败主要由以下组合导致：

```text
FP32/FP16 路线 + reflect Pad + HTP 后端算子限制
```

Pad 最小复现后的修正判断：

- reflect Pad 是明确阻塞点之一，因为 `reflect_pad_conv` 的 QNN DSP 失败在 `_pad_Pad`。
- reflect Pad 不是唯一阻塞点，因为 `constant_pad_conv` 和 `builtin_pad_conv` 的 QNN DSP 也失败，但失败点变成 `DepthWiseConv2d`。
- 当前更准确的判断是：`FP32/FP16 路线 + HTP 后端算子限制` 是底层约束，reflect Pad 只是原始模型最早暴露出来的失败节点。

新增证据：

- `strace` 已确认 QNN DSP 会打开 `libQnnHtp.so`、`libQnnHtpV68Stub.so`、`/usr/lib/libcdsprpc.so`、`/dev/adsprpc-smd-secure` 和 `hexagon-v68/libQnnHtpV68Skel.so`。
- 因此 QNN DSP 不是没有进入 HTP/CDSP 路线，而是进入后在模型图校验阶段失败。
- 未改写完整 `.so` 的失败日志继续指向第一个 `Pad` 节点：`_enc1_c1__prepad_Pad`。
- Pad+INT8 改写版已经绕过该失败点并完成真实样本推理，说明“未改写失败”不能再等同于“QNN DSP 完整模型永远不可执行”。

## 实验拆分

### 实验 A: 后端证据复核

目标：

- 确认每个 runtime 实际加载的库和打开的设备节点。

命令模板：

```bash
strace -f -e openat python3 modules/radio_map_qcs6490_deploy/scripts/probe_fibo_dlc_runtime.py \
  --framework snpe \
  --runtime DSP \
  --mode 5 \
  --repeat 1
```

关注：

- 是否打开 `libSnpeHtpV68Stub.so`。
- 是否打开 `libcdsprpc.so`。
- 是否打开 `/dev/adsprpc-smd-secure`。
- 是否读取 `hexagon-v68/*Skel.so`。

### 实验 B: Pad 最小复现

目标：

- 构造最小模型，只包含输入、reflect Pad、Conv。
- 转成 QNN `.so` 后跑 QNN DSP。
- 如果仍失败在 Pad，说明问题可定位到 Pad scheme。

可选对照：

- reflect Pad + Conv。
- zero Pad + Conv。
- Conv 内置 padding。

成功标准：

- 至少找到一个 HTP 可接受的 padding 表达。
- 或明确证明当前 HTP 后端不接受该 Pad 配置。

当前结果：

| 最小模型 | QNN CPU | QNN GPU | QNN DSP |
| --- | --- | --- | --- |
| `reflect_pad_conv` | 通过，约 `5.01 ms` | 通过，约 `1.26 ms` | 失败在 `_pad_Pad` |
| `constant_pad_conv` | 通过，约 `0.13 ms` | 通过，约 `2.08 ms` | 失败在 `_conv_Conv` / `DepthWiseConv2d` |
| `builtin_pad_conv` | 通过，约 `0.12 ms` | 通过，约 `1.10 ms` | 失败在 `_conv_Conv` / `DepthWiseConv2d` |

关键日志：

```text
reflect_pad_conv + QNN DSP:
QnnBackend_validateOpConfig failed 3110
Failed to validate op _pad_Pad with error 0xc26
MODEL_GRAPH_OP_VALIDATION_ERROR

constant_pad_conv / builtin_pad_conv + QNN DSP:
QnnBackend_validateOpConfig failed 3110
Failed to validate op _conv_Conv with error 0xc26
DepthWiseConv2d ... MODEL_GRAPH_OP_VALIDATION_ERROR
```

产物路径：

```text
modules/fiboaistack_229_env/inputs/pad_minimal/
modules/fiboaistack_229_env/outputs/pad_minimal/
modules/fiboaistack_229_env/outputs/pad_minimal_qnn/
modules/radio_map_qcs6490_deploy/outputs/pad_minimal_qnn_runtime_20260703_031822/
```

结论：

- reflect Pad 最小复现已经证实 Pad scheme 在 QNN DSP 上有兼容风险。
- 但是仅把 reflect Pad 换成 zero padding 或 Conv 内置 padding，仍不能保证 QNN DSP 跑通，因为当前最小 depthwise conv 本身也不被 HTP 后端接受。
- 后续已继续拆分普通 Conv、DepthWiseConv2d 和 INT8 最小模型，见实验 C。

### 实验 C: Conv 与 INT8 最小模型

目标：

- 分别验证普通 `Conv2d`、`DepthWiseConv2d`、Q/DQ 伪 INT8 图和真实 converter 量化图在 QNN CPU/GPU/DSP 上的表现。
- 判断 QNN DSP 失败是否只由 reflect Pad 引起，还是 FP32/FP16 卷积本身也不满足 HTP 要求。

生成脚本：

```bash
/home/fibo/fibocom_slz/._envs/radio-map-qcs6490-py38/bin/python \
  modules/radio_map_qcs6490_deploy/scripts/build_htp_cdsp_minimal_onnx.py \
  --output-dir modules/fiboaistack_229_env/inputs/htp_cdsp_minimal
```

生成模型：

| 模型 | ONNX 结构 | 输入形状 |
| --- | --- | --- |
| `plain_conv` | 普通 `Conv`，3 输入通道、5 输出通道 | `[1,3,8,8]` |
| `depthwise_conv` | `Conv`，groups=4，经 QNN 转换为 `DepthWiseConv2d` | `[1,4,8,8]` |
| `qdq_int8_conv` | `QuantizeLinear -> DequantizeLinear -> Conv` | `[1,3,8,8]` |

产物路径：

```text
modules/fiboaistack_229_env/inputs/htp_cdsp_minimal/
modules/fiboaistack_229_env/outputs/htp_cdsp_minimal_qnn/
modules/radio_map_qcs6490_deploy/outputs/htp_cdsp_minimal_qnn_runtime_20260703_042755/
```

当前运行矩阵：

| 最小模型 | QNN CPU | QNN GPU | QNN DSP |
| --- | --- | --- | --- |
| `plain_conv` | 通过，约 `18.78 ms` | 通过，约 `1.20 ms` | 失败在 `Conv2d` |
| `depthwise_conv` | 通过，约 `0.20 ms` | 通过，约 `1.19 ms` | 失败在 `DepthWiseConv2d` |
| `qdq_int8_conv` | 失败在 `Conv2d` 校验 | 失败，`GPU_ERROR_INVALID_TYPE(10012)` | 失败在 `Conv2d` 校验 |

关键日志：

```text
plain_conv + QNN DSP:
QnnBackend_validateOpConfig failed 3110
Failed to validate op _conv_Conv with error 0xc26
Conv2d ... MODEL_GRAPH_OP_VALIDATION_ERROR

depthwise_conv + QNN DSP:
QnnBackend_validateOpConfig failed 3110
Failed to validate op _conv_Conv with error 0xc26
DepthWiseConv2d ... MODEL_GRAPH_OP_VALIDATION_ERROR

qdq_int8_conv:
QNN_CPU: OpConfig validation failed for Conv2d
QNN_GPU: GPU_ERROR_INVALID_TYPE(10012)
QNN_DSP: Failed to validate op qdq_conv with error 0xc26
```

结论：

- QNN DSP 失败不是只由 reflect Pad 引起；即使最小普通 `Conv2d` 也在 HTP 后端图校验阶段失败。
- 当前 FP32 QNN CPU/GPU 路线能跑普通 Conv 和 DepthWiseConv2d；QNN DSP 路线不能接受这些 FP32 最小卷积图。
- 手工 Q/DQ 伪 INT8 图没有形成可用 INT8 后端图。默认转换会把 Q/DQ 折回 float `Conv2d`；使用 `--keep_quant_nodes` 时又失败在 Quantize 节点类型校验。
- 当前最可能的后续突破点是真正的 converter 量化产物，而不是手写 Q/DQ 图。

### 实验 D: INT8 量化

前置：

- 从真实 `.npz` 样本生成 representative input list。
- 输入 layout 必须与 DLC/QNN 转换要求一致。

风险：

- 当前本机 Docker/QEMU 下量化工具存在崩溃记录。
- 如果继续在本机做，需要先修转换工具稳定性。

当前实测：

- `snpe-dlc-quantize --help` 可运行。
- `qairt-quantizer --help` 可运行。
- 旧 QEMU 4.2.1 阶段，使用 5 个真实 test 样本生成 raw input list 后，实际运行 `snpe-dlc-quantize` 触发 `qemu: uncaught target signal 4 (Illegal instruction)`；该结果仅说明旧 QEMU 不适合作为完整量化依据。
- 旧 QEMU 4.2.1 阶段，同样输入下实际运行 `qairt-quantizer` 也触发 `Illegal instruction`；0703 阶段切换 QEMU 8.2.2 后，`snpe-dlc-quantize` 和 `qairt-quantizer` 均已成功生成完整 radio-map INT8 DLC。
- 使用最小 `plain_conv` 的 4 个校准 raw 样本运行 `qnn-onnx-converter --input_list`，仍在 `qnn_quantizer.py` 的 `quantize` 阶段触发 `Illegal instruction`。
- 去掉 per-channel、把 bias bitwidth 改为 8 后仍触发同一类 `Illegal instruction`。
- 进一步定位后发现，系统标准 `qemu-x86_64` binfmt 指向 QEMU `4.2.1`，同时本机已有 `/usr/local/bin/qemu-x86_64-static-8.2.2`。
- 使用 QEMU `8.2.2` 后，最小 `plain_conv_int8` 的 `qnn-onnx-converter --input_list` 已成功生成 QNN `.cpp/.bin/.json`，产物在 `modules/fiboaistack_229_env/outputs/v2_plain_conv_int8_qemu82/`。
- 相关 core 文件已按项目规则清理。

结论：

- 当前 Docker/QEMU 路线可以支持基础 ONNX -> DLC / QNN `.cpp` 转换。
- `Illegal instruction` 至少有一部分来自旧 QEMU `4.2.1`，不是完整论文模型复杂度导致。
- 最小 QNN INT8 量化转换已在 QEMU `8.2.2` 下通过；完整 `snpe-dlc-quantize` / `qairt-quantizer` 也已在同一 QEMU `8.2.2` 条件下生成可运行 INT8 DLC。
- 如果继续本机量化，先运行 `modules/fiboaistack_229_env/scripts/check_qemu_x86_64.sh`，必要时运行 `modules/fiboaistack_229_env/scripts/register_qemu82_binfmt.sh`。

### 实验 E: 转换工具稳定性

目标：

- 解决 `snpe-dlc-quantize`、`qairt-quantizer`、`qnn-context-binary-generator` 等工具在 QEMU 下 core 的问题。

备选方案：

- 更新 QEMU 或调整兼容 shim。
- 使用真正的 x86_64 Linux/PC 完成量化和 context 生成。
- 本机只负责最终推理验证。

当前工具可用性矩阵：

| 工具 | help 是否可运行 | 实际任务状态 |
| --- | --- | --- |
| `snpe-dlc-info` | 可运行 | 基础 DLC info 已可用。 |
| `snpe-dlc-quantize` | 可运行 | 旧 QEMU 4.2.1 下实际量化触发 illegal instruction；QEMU 8.2.2 下已成功生成完整 radio-map INT8 DLC。 |
| `qairt-quantizer` | 可运行 | 旧 QEMU 4.2.1 下实际量化触发 illegal instruction；QEMU 8.2.2 下已成功生成完整 radio-map INT8 DLC。 |
| `qnn-context-binary-generator` | 可运行 | Pad+INT8 改写版已解决完整模型执行问题；context 生成仍未作为正式部署前置项。 |
| `qnn-onnx-converter --input_list` | 可运行 | 最小 `plain_conv_int8` 在 QEMU 8.2.2 下已成功量化转换。 |
| `qnn-net-run` | 可运行 | 可作为后续 QNN CPU/GPU/HTP 直接验证工具，但需要匹配架构的模型库和 input list。 |

### 实验 F: 完整 radio-map Pad+INT8 图改写

目标：

- 将完整 ONNX 中的 `reflect Pad` 改为 HTP/CDSP 更容易接受的 constant zero Pad。
- 使用 converter 真实量化生成 QNN INT8 `.so`。
- 验证完整 radio-map 模型能否在 QNN DSP 上初始化、执行并输出 `256x256` 结果。

关键脚本：

```text
modules/radio_map_qcs6490_deploy/scripts/rewrite_radio_map_onnx_for_qnn_htp.py
modules/radio_map_qcs6490_deploy/scripts/run_qnn_radio_map_inference.py
```

关键产物：

```text
modules/fiboaistack_229_env/inputs/qnn_htp_rewrite/radio_map_liteunet_pad_constant.onnx
modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/host_build/libs/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_pad_constant_int8_qnn.so
modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/radio_map_liteunet_pad_constant_int8_qnn_net.json
```

阶段结果：

| 模型 | QNN DSP 结果 | 判断 |
| --- | --- | --- |
| 未改写 FP32 完整 `.so` | 失败在 `_enc1_c1__prepad_Pad` | 进入 HTP/CDSP，但图校验失败。 |
| Pad-only FP32 完整 `.so` | 失败点后移到 `_enc1_c1_depth_Conv` / `DepthWiseConv2d` | Pad 改写有效，但 FP32 depthwise 仍不被接受。 |
| Pad+INT8 完整 `.so` | 10 个真实样本 `10/10` 成功 | 完整模型可执行，但精度弱于 SNPE DSP INT8。 |

10 样本指标：

| 平均耗时 | RMSE | MAE | 实验目录 |
| ---: | ---: | ---: | --- |
| `90.18 ms` | `4.571 dB` | `2.931 dB` | `modules/radio_map_qcs6490_deploy/outputs/qnn_pad_constant_int8_real10_20260703_143201` |

关键接口修正：

- QNN INT8 输入必须根据 JSON 中的 input `scale` / `offset` 手动量化，并调用 `Execute_uint8`。
- QNN INT8 输出必须调用 `FetchOutputs_uint8` 后按 output `scale` / `offset` 反量化。
- 继续调用 float 输入输出接口会得到无效结果，不能用于精度评估。

结论：

- QNN DSP 完整模型已经从“初始化失败”推进到“Pad+INT8 改写版可执行”。
- 当前瓶颈从“能不能跑通”转为“为什么精度弱于 SNPE DSP INT8”。
- 专项详情见 `QNN_DSP图改写首轮结果.md`。

## 当前不建议做的事

- 不建议继续盲试 `HTP`、`AIP`、`DSP_FIXED8_TF`、`DSP_FLOAT32_16_HYBRID` 等字符串。
- 不建议把 `runtime=NPU` 解释为独立 NPU 硬件证据。
- 不建议在未量化、未改 Pad 的情况下反复跑同一个 QNN DSP 模型；该路径已经被证明会卡在 HTP op validation。
- 不建议继续使用旧 QEMU 4.2.1 跑完整量化命令；当前应固定 QEMU 8.2.2，并把重点转向 QNN DSP 图兼容和 context 生成。

## 避免 CPU fallback 的当前策略

Fibo AI Stack Python SDK 当前公开封装主要只有：

```text
model_path
platform
framework
device_unit(runtime)
log_level
mode(profile_level)
```

当前未发现类似 `disable_cpu_fallback=true` 或 `force_dsp_only=true` 的强制参数。因此避免误判 fallback 的方法不是依赖单个开关，而是建立验证闭环：

1. 明确 runtime 字符串只使用课程封装和 SDK 可识别的 `CPU/GPU/DSP/NPU`。
2. SNPE GPU 必须同时满足：日志出现 GPU runtime、耗时显著快于 CPU、输出与 CPU 有小幅混合精度差异。
3. SNPE DSP/NPU 不能只看 `Init=0`、`Execute=0`；如果耗时接近 CPU、输出完全等同 CPU、FastRPC 证据不足，就按疑似 fallback 处理。
4. QNN DSP 如果返回模型图校验失败，说明进入过 HTP/CDSP 后端但当前图不可执行，这不是 fallback 成功；Pad+INT8 改写版已经能执行完整模型。
5. 后续若要真正避免 DSP fallback，必须给 DSP/HTP 提供可执行模型：通常需要 INT8/定点量化、HTP 支持的算子组合和可生成 context 的转换链。

对当前本机部署，最可靠的避免 CPU fallback 方案是继续使用已经实测稳定的 `framework=snpe`、`runtime=GPU`，并把 HTP/CDSP 作为专项优化路线。

## 与主线的关系

SNPE GPU 主线已经可用，应继续用于当前设备部署验证。

HTP/CDSP 专项的价值是：

- 判断当前模型是否值得为 DSP/HTP 改结构。
- 判断是否需要 INT8 量化。
- 判断是否值得引入 x86_64 PC 作为转换设备。

如果专项没有明显突破，不影响当前本机用 SNPE GPU 完成部署测试。
