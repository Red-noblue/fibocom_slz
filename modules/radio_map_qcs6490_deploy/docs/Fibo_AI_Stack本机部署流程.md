# Fibo AI Stack 本机部署流程

本文档整理当前 QCS6490 / SC171V3 设备上部署 `radio-map-estimation-workbench` 无线电地图估计模型的可执行流程。目标是只做部署、推理和测试，不训练模型，也不修改论文项目源码。

## 当前结论

- 本机已经具备 Fibo AI Stack 板端推理运行库：`/usr/local/lib/python3.8/dist-packages/fiboaisdk`。
- 本机系统 Python 是 `Python 3.8.10`，`fiboaisdk` 是 `cpython-38-aarch64` 二进制扩展，优先使用系统 `python3` 运行 Fibo AI Stack 推理。
- `._envs/uav-modules-py310` 不能直接运行 `fiboaisdk`，因为当前 SDK 不是 Python 3.10 ABI。
- 当前已经加载 Fibo AI Stack 2.29 转换镜像，并在 `modules/fiboaistack_229_env` 中完成 ONNX -> DLC 转换。
- 当前 DLC 模型位于 `modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc`。
- 当前设备最推荐的实际部署路线是：本机原生 `python3` + Fibo AI Stack SDK + `framework=snpe` + `runtime=GPU` + INT8 DLC。
- 如果极端关注速度，可以把 SNPE DSP INT8 作为副主线；它已有 FastRPC/CDSP 证据，但精度相对 GPU INT8 更差。
- SNPE HTP/NPU 与 QNN DSP 完整模型仍作为 HTP/CDSP 专项研究，不作为当前主线部署前置条件。
- 0703 阶段成果、指标和复现指令已汇总到 `docs/0703-完成DSP、SNPE等部署/README.md`。

## 参考资料

- 模型转化课件：`docs/广和通课程资源/04_AI端侧部署开发/01_Fibo_AI_Stack模型转化指南/课件/Fibo AI Stack模型转化指南------Docker Desktop环境操作_V2.0.pdf`
- 模型推理课件：`docs/广和通课程资源/04_AI端侧部署开发/02_Fibo_AI_Stack模型推理指南/课件/Fibo AI Stack模型推理指南_V2.0.pdf`
- 课程推理源码包：`docs/广和通课程资源/04_AI端侧部署开发/02_Fibo_AI_Stack模型推理指南/工程源码/模型推理指南_V2.0.zip`
- 论文项目：`modules/radio-map-estimation-workbench`
- 本部署模块：`modules/radio_map_qcs6490_deploy`

## 模型和数据口径

论文项目当前主模型为 M4 的 `LiteUNet`：

- 输入：`[1, 7, 256, 256]`
- 输出：`[1, 1, 256, 256]`
- 输入张量名：`input`
- 输出张量名：`output`
- 上游特征目录：`modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3`
- 推荐 checkpoint 来源：`modules/radio-map-estimation-workbench/modules/m4/runs/datas/m4-1_aspp_base48_focus_bg_edge_losaware_y133p129_3k_s17_cleanproto`
- 最优 checkpoint：`checkpoints/ep10_val3.4675.pt`

M2 样本 `.npz` 中包含：

- `X`：`float32`，形状 `[7, 256, 256]`
- `y`：`float32`，形状 `[1, 256, 256]`，单位 dBm
- `valid_mask`：`bool`，形状 `[256, 256]`

模型训练时使用标签标准化，ONNX/DLC 原始输出仍需按以下参数反归一化回 dBm：

```text
pred_dbm = pred_raw * 12.813038764458584 + (-122.58401346206665)
```

## 推荐部署路线

### 1. 先做 PyTorch / ONNX 基线

目的：确认导出的 ONNX 与原 PyTorch checkpoint 数值一致。该步骤需要能运行 `torch==2.1.0` 的 Python 环境；当前系统 Python 和 `._envs/uav-modules-py310` 都没有安装 torch。

论文项目已有 ONNX 导出脚本：

```bash
cd /home/fibo/fibocom_slz/modules/radio-map-estimation-workbench
python modules/m4/tools/export_onnx.py \
  m4-1_aspp_base48_focus_bg_edge_losaware_y133p129_3k_s17_cleanproto \
  ../radio_map_qcs6490_deploy/outputs/radio_map_liteunet.onnx
```

导出后要记录：

- ONNX 文件路径。
- 输入输出张量名是否仍为 `input` / `output`。
- 小样本 PyTorch 输出与 ONNX 输出最大绝对误差、平均绝对误差。

### 2. 转换 ONNX 到 DLC

课程中的 Fibo AI Stack 2.29 转化流程使用 Docker 镜像 `fiboaistack_229_env.tar`，核心命令是：

```bash
docker load -i fiboaistack_229_env.tar
docker run -itd --name my_work fiboaistack_229_env:latest
docker cp /path/to/radio_map_liteunet.onnx my_work:/project/
docker exec -it my_work bash
```

容器内执行：

```bash
snpe-onnx-to-dlc \
  --input_network /project/radio_map_liteunet.onnx \
  --output_path /project/radio_map_liteunet.dlc

snpe-dlc-info -i /project/radio_map_liteunet.dlc
```

导出 `.dlc`：

```bash
docker cp my_work:/project/radio_map_liteunet.dlc /path/to/radio_map_liteunet.dlc
```

当前已经完成基础 ONNX -> DLC 转换，DLC 位于：

```text
modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
```

注意：当前 DLC 是 FP32 模型，`snpe-dlc-info` 显示 `Quantizer command: N/A`。它适合作为 SNPE GPU 主线模型，但不是 DSP/HTP 专用量化模型。

0703 更新：QEMU 8.2.2 下已经完成完整 radio-map 模型量化，产物如下：

```text
modules/fiboaistack_229_env/outputs/snpe_quant_qemu82_full_20260703_075537/radio_map_liteunet_quantized.dlc
modules/fiboaistack_229_env/outputs/qairt_quant_qemu82_full_20260703_080039/radio_map_liteunet_qairt_quantized.dlc
```

当前默认运行建议优先使用 INT8 DLC；FP32 DLC 保留为基线对照。

### 3. 板端 Fibo AI Stack 推理

本机可用的 SDK 检查命令：

```bash
python3 - <<'PY'
from fiboaisdk.api_aisdk_py import api_infer_py
print(hasattr(api_infer_py, "InferAPI"))
print(hasattr(api_infer_py, "InferParams"))
PY
```

课程源码包中的 `api_infer.py` 是可复用的包装参考，核心参数如下：

```python
inference_config = {
    "model": "modules/radio_map_qcs6490_deploy/outputs/radio_map_liteunet.dlc",
    "platform": "qualcomm",
    "framework": "snpe",
    "runtime": "CPU",
    "log_level": "INFO",
    "profile_level": 0,
}
```

运行后端建议按顺序验证：

1. `CPU`：先确认功能正确。
2. `GPU`：验证 Adreno 路径可用性和延迟。
3. `DSP`：只作为 HTP/CDSP 专项验证。当前 SDK 目录中有 `hexagon-v68` 与 `libSnpeHtpV68*`，但当前 FP32 DLC 在 DSP/NPU 上没有表现出真实加速证据。

SNPE 路线要求输入为 `float32`。本项目单样本预处理应保持：

```python
sample = np.load(sample_npz)
x = sample["X"].astype(np.float32)[None, ...]
input_feed = {"input": x}
output_names = ["output"]
```

Fibo AI Stack 包装层当前使用 `Execute_float({"input": list[float]})` 传入展平后的 float 列表。输出需要按 `[256, 256]` 重塑，并反归一化回 dBm。

## 当前可复现实验

### 单样本 SNPE GPU 推理

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/run_snpe_gpu_inference.py \
  --sample-id 166_k0 \
  --runtime GPU \
  --warmup 1 \
  --repeat 2 \
  --output-dir modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_smoke
```

输出：

```text
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_smoke/166_k0_gpu_snpe.npy
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_smoke/166_k0_gpu_snpe_summary.json
```

### 单样本 CPU/GPU 对齐

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/align_snpe_outputs_with_real_sample.py \
  --sample-id 166_k0 \
  --warmup 1 \
  --repeat 2 \
  --output-dir modules/radio_map_qcs6490_deploy/outputs/snpe_alignment_real_sample
```

当前 `166_k0` 结果：

- SNPE CPU 平均推理约 `1132.70 ms`。
- SNPE GPU 平均推理约 `304.30 ms`。
- CPU/GPU 输出差异：dBm 空间 RMSE 约 `0.0147 dB`。
- GPU 对真实标签：RMSE 约 `2.462 dB`，MAE 约 `1.492 dB`。

### 20 个 test 样本复现实验

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/batch_snpe_gpu_repro.py \
  --limit 20 \
  --warmup 1 \
  --repeat 1 \
  --output-dir modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test20
```

当前 20 样本结果：

- 样本数：`20`
- 成功数：`20`
- 失败数：`0`
- SNPE CPU 平均推理：约 `1339.92 ms`
- SNPE GPU 平均推理：约 `335.89 ms`
- CPU/GPU 平均加速比：约 `3.99x`
- CPU/GPU 输出差异：dBm 空间平均 RMSE 约 `0.0158 dB`
- SNPE GPU 对真实标签：平均 RMSE 约 `3.279 dB`，平均 MAE 约 `2.026 dB`

结果文件：

```text
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test20/summary.csv
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test20/summary.json
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test20/raw_results.json
```

### 50/100 个 test 样本复现实验

50 样本：

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/batch_snpe_gpu_repro.py \
  --limit 50 \
  --warmup 1 \
  --repeat 1 \
  --output-dir modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test50
```

100 样本：

```bash
python3 modules/radio_map_qcs6490_deploy/scripts/batch_snpe_gpu_repro.py \
  --limit 100 \
  --warmup 1 \
  --repeat 1 \
  --output-dir modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test100
```

当前批量结果：

| 样本数 | 成功数 | 失败数 | CPU 平均耗时 | GPU 平均耗时 | CPU/GPU 平均加速 | CPU/GPU dBm RMSE | GPU 对标签 RMSE | GPU 对标签 MAE |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 20 | 0 | `1339.92 ms` | `335.89 ms` | `3.99x` | `0.0158 dB` | `3.279 dB` | `2.026 dB` |
| 50 | 50 | 0 | `1290.16 ms` | `332.48 ms` | `3.89x` | `0.0158 dB` | `3.549 dB` | `2.203 dB` |
| 100 | 100 | 0 | `1278.57 ms` | `331.16 ms` | `3.87x` | `0.0155 dB` | `3.473 dB` | `2.189 dB` |

结果文件：

```text
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test50/summary.csv
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test50/summary.json
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test100/summary.csv
modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test100/summary.json
```

结论：SNPE GPU 的 50/100 样本复现实验已经形成稳定证据。100 样本下 GPU 平均约 `331 ms`，CPU 平均约 `1279 ms`，平均加速约 `3.87x`；CPU/GPU 之间 dBm RMSE 约 `0.0155 dB`，远小于模型对真实标签的误差。

### 4. 结果校验

部署侧最小校验集建议从 `samples.csv` 中选择少量 test 样本，例如 `166_k0`、`166_k1`、`373_k0`。

每个样本至少记录：

- Fibo AI Stack 输出是否能生成。
- 输出形状是否为 `[1, 1, 256, 256]`。
- `pred_dbm` 的最小值、最大值、均值是否落在合理区间。
- 与 PyTorch / ONNX 基准输出的 `max_abs_diff` 和 `mean_abs_diff`。
- 在 `valid_mask` 内的 RMSE / MAE。
- CPU/GPU/DSP 各后端延迟。

### 5. 转化失败时的处理分支

`LiteUNet` 的 ONNX 里可能包含 SNPE 转化不完全支持的算子组合，例如 `ReflectionPad`、`GroupNorm` 展开的 reshape/normalization 子图、`Resize` 或 ASPP 空洞卷积。若 `snpe-onnx-to-dlc` 失败，按以下顺序处理：

1. 先保存完整错误日志，不直接改论文项目。
2. 在 `modules/radio_map_qcs6490_deploy` 中建立部署专用导出脚本或模型包装。
3. 优先尝试固定输入尺寸、静态 batch、opset 降级或图简化。
4. 如果是 padding 问题，再评估部署专用零填充变体；这会带来边界输出差异，必须和原 PyTorch 输出做误差对齐。
5. 如果是归一化问题，再评估是否需要替换为 SNPE 支持的子图；该改动必须通过小样本数值回归。

## 当前剩余问题

- 论文侧 PyTorch/历史预测可做参考对齐，但当前主线不要求严格复刻论文训练环境版本。
- SNPE DSP FP32 / NPU 返回成功不等价于真实 CDSP/HTP 加速；但 SNPE DSP INT8 已通过耗时和 FastRPC/CDSP 证据确认具备速度副主线价值。
- QNN DSP 未改写 FP32 `.so` 会失败在 HTP 后端模型校验阶段。最小复现显示 reflect Pad 会明确失败在 `_pad_Pad`，但 constant padding 和 Conv 内置 padding 的最小模型也会失败在 `DepthWiseConv2d`，因此问题不只是一处 reflect Pad。
- 完整 `snpe-dlc-quantize` / `qairt-quantizer` 已在 QEMU 8.2.2 下恢复，可生成 radio-map INT8 DLC；QNN DSP Pad+INT8 改写版完整模型已可执行，但精度弱于 SNPE DSP INT8，当前仍作为 HTP/CDSP 专项研究线。

## HTP/CDSP 与量化探测记录

当前专项探测产物：

```text
modules/radio_map_qcs6490_deploy/outputs/htp_cdsp_probe_20260703_024038
modules/radio_map_qcs6490_deploy/outputs/toolchain_stability_probe_abs_20260703_024245
modules/fiboaistack_229_env/outputs/snpe_quant_probe_20260703_024315
modules/fiboaistack_229_env/outputs/qairt_quant_probe_20260703_024344
```

已确认：

- SNPE DSP 会打开 HTP/CDSP 相关库和 `/dev/adsprpc-smd-secure`；FP32 DLC 没有真实加速证据，但 INT8 DLC 已有约 `80 ms` 长 repeat 和 FastRPC/CDSP 证据。
- SNPE NPU 未看到类似 SNPE DSP 的 HTP/CDSP 库加载证据，当前更像 CPU 路线。
- QNN DSP 会打开 `libQnnHtp.so` 和 CDSP/FastRPC 通道；未改写 FP32 `.so` 会在 reflect Pad 相关节点校验失败，Pad+INT8 改写版已能执行完整模型。
- `snpe-dlc-info`、`snpe-dlc-quantize --help`、`qairt-quantizer --help`、`qnn-context-binary-generator --help`、`qnn-net-run --help` 都可以在容器内通过绝对路径运行。
- 旧 QEMU `4.2.1` 下真实量化会触发 `Illegal instruction`；切换到 QEMU `8.2.2` 后，完整 `snpe-dlc-quantize` 和 `qairt-quantizer` 已成功生成 radio-map INT8 DLC。
- 当前已定位到一个关键环境因素：系统标准 `/usr/bin/qemu-x86_64-static` 曾是 `4.2.1`，而 `/usr/local/bin/qemu-x86_64-static-8.2.2` 可用于恢复完整量化链路；最小 `plain_conv_int8` 也已在 QEMU `8.2.2` 下成功完成 `qnn-onnx-converter --input_list` 量化转换。
- reflect Pad 最小复现已经完成：QNN CPU/GPU 可运行三种最小模型；QNN DSP 对 reflect Pad 失败在 `_pad_Pad`，对 constant padding 和 Conv 内置 padding 失败在 `DepthWiseConv2d`。

因此，当前建议：

- 主线继续使用 SNPE GPU，优先使用 INT8 DLC。
- HTP/CDSP 如需继续推进，先执行 `modules/fiboaistack_229_env/scripts/check_qemu_x86_64.sh`；若标准 binfmt 仍指向旧 QEMU，则执行 `modules/fiboaistack_229_env/scripts/register_qemu82_binfmt.sh` 后再跑量化或 QNN 相关转换。
- 完整 SNPE / QAIRT INT8 DLC 已可用；QNN DSP Pad+INT8 full `.so` 已完成首轮跑通，后续应从 padding 替代表达、边界误差和 QNN context 生成继续推进。
