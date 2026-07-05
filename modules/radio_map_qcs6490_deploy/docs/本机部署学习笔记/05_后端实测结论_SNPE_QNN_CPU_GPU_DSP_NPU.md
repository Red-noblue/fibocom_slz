# 后端实测结论 SNPE QNN CPU GPU DSP NPU

## 0703 阶段更新

本篇原始内容记录的是 FP32 DLC 和随机输入探针阶段的后端判断。0703 阶段已经补充完整模型量化、真实样本对齐、SNPE DSP INT8 长 repeat 与 `strace` 证据，因此当前结论以 `../0703-完成DSP、SNPE等部署/README.md` 为准。

更新后的可用路线：

| 路线 | 当前判断 |
| --- | --- |
| SNPE GPU FP32 DLC | 稳定基线，100 个 test 样本平均约 `331 ms`。 |
| SNPE GPU INT8 DLC | 默认部署主线，20 个真实 test 样本平均约 `302 ms`，对 FP32 GPU 差异约 `0.184 dB RMSE`。 |
| QAIRT GPU INT8 DLC | 可替代 INT8 GPU 路线，20 个真实 test 样本平均约 `306 ms`。 |
| SNPE DSP INT8 DLC | 速度副主线，20 个真实 test 样本平均约 `83 ms`；已有 FastRPC/CDSP 证据，但精度弱于 GPU INT8。 |
| QNN GPU `.so` | 备选验证路线，可运行但速度不如 SNPE GPU INT8。 |
| SNPE HTP/NPU | 仍按疑似 CPU fallback 处理。 |
| QNN DSP 未改写 `.so` | 进入 HTP/CDSP 后失败在模型图校验，不是当前可部署路线。 |
| QNN DSP Pad+INT8 改写 `.so` | 完整模型已能执行，10 样本平均 `90.18 ms`，RMSE `4.571 dB`，作为 HTP/CDSP 专项研究线。 |

需要注意：下面保留的 FP32 SNPE DSP/NPU 结论只适用于未量化 DLC 阶段，不能再用于否定 SNPE DSP INT8 路线。
同理，下面保留的 QNN DSP 失败分析主要适用于未改写 FP32 `.so`；Pad+INT8 图改写后的最新结果见 `../HTP_CDSP专项/QNN_DSP图改写首轮结果.md`。

## 这篇解决什么问题

这篇整理当前已经完成的 Fibo AI Stack 本机后端测试结果，重点回答：哪些后端真的可用，哪些只是返回成功，哪些明确失败，以及为什么当前推荐 SNPE GPU。

当前结论基于以下探针和日志：

```text
modules/radio_map_qcs6490_deploy/scripts/probe_fibo_dlc_runtime.py
modules/radio_map_qcs6490_deploy/outputs/fibo_runtime_device_probe_20260702_153101.log
modules/radio_map_qcs6490_deploy/outputs/fibo_backend_matrix_20260702_151018.log
modules/radio_map_qcs6490_deploy/outputs/fibo_qnn_modelso_probe_20260702_152605.log
```

## 当前测试模型

SNPE 路线使用 DLC：

```text
modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
```

QNN 路线使用 QNN 模型库：

```text
modules/fiboaistack_229_env/outputs/qnn_model/lib/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_qnn.so
```

当前探针输入输出：

```text
input  -> [1, 256, 256, 7] float32
output -> [1, 256, 256, 1] float32
```

当前测试使用随机输入，因此它主要验证后端可用性、耗时和输出稳定性；后续真实任务质量还需要接入论文项目实际样本。

## 总体结果表

| 路线 | 模型格式 | 状态 | 平均执行耗时 | 当前判断 |
| --- | --- | --- | --- | --- |
| SNPE CPU | DLC | 可用 | 约 1077 ms | CPU 基线。 |
| SNPE GPU | DLC | 可用 | 约 292 ms | 当前首选，真实加速证据最充分。 |
| SNPE DSP | DLC | 返回成功 | 约 1115 ms | 疑似 CPU fallback 或未完整使用 CDSP。 |
| SNPE NPU | DLC | 返回成功 | 约 1101 ms | 更像 CPU 路线，没有真实 NPU 加速证据。 |
| QNN CPU | QNN `.so` | 可用 | 约 1003 ms | QNN CPU 基线。 |
| QNN GPU | QNN `.so` | 可用 | 约 419 ms | 真实 GPU 路线，可作为备用。 |
| QNN DSP | QNN `.so` | 初始化失败 | 无 | 确实尝试 HTP/CDSP，但模型未通过校验。 |

## SNPE CPU

SNPE CPU 是当前 DLC 的基础可用性验证。

关键日志：

```text
Set cpu_float32 runtime succeeded
NodeManager::GetNodeCreator, attempt node_name = all_all_infer_snpe_cpu_1.0.0
```

当前实测结果：

```text
ok=true
execute_ms_avg=1077.2920925010112
output_mean=-1.171022653579712
```

SNPE CPU 的价值是作为正确性和耗时基线。它不是目标加速路径。

## SNPE GPU

SNPE GPU 是当前推荐路线。

关键日志：

```text
Set gpu_float32_16_hybrid runtime succeeded
Set cpu_float32 runtime succeeded
NodeManager::GetNodeCreator, attempt node_name = all_all_infer_snpe_gpu_1.0.0
```

这里同时出现 CPU runtime 并不一定表示完全回退，因为 SNPE 可以构建 runtime list 或保留 CPU 作为 fallback。更关键的是它明确设置了 `gpu_float32_16_hybrid`，节点创建也是 `snpe_gpu`，并且耗时明显下降。

当前实测结果：

```text
ok=true
execute_ms_avg=292.06361950127757
output_mean=-1.1697732210159302
```

与 CPU 相比：

```text
SNPE CPU: ~1077 ms
SNPE GPU: ~292 ms
```

输出均值也和 CPU 有轻微差异，符合 GPU 混合精度路径的特征。

当前判断：SNPE GPU 是当前本机部署最可靠、最快的路径。

## SNPE DSP

SNPE DSP 表面上返回成功，但不能认定为真实 CDSP/HTP 加速。

关键日志：

```text
Set dsp_fixed8_tf runtime succeeded
Set cpu_float32 runtime succeeded
The SocModel doesn't support FP16
NodeManager::GetNodeCreator, attempt node_name = all_all_infer_snpe_dsp_1.0.0
```

当前实测结果：

```text
ok=true
execute_ms_avg=1115.263188499739
output_mean=-1.171022653579712
```

它的耗时和 CPU 非常接近，输出均值也和 CPU 完全一致：

```text
SNPE CPU output_mean=-1.171022653579712
SNPE DSP output_mean=-1.171022653579712
```

这说明至少当前模型和当前 DLC 下，不能凭返回码认定它真的完成了 Hexagon/CDSP 加速推理。

当前判断：SNPE DSP 可能尝试设置 DSP runtime，但当前表现不具备真实加速证据。

## SNPE NPU

SNPE NPU 同样返回成功，但实际证据更弱。

关键日志：

```text
Set cpu_float32 runtime succeeded
NodeManager::GetNodeCreator, attempt node_name = all_all_infer_snpe_npu_1.0.0
```

当前实测结果：

```text
ok=true
execute_ms_avg=1101.0598100001516
output_mean=-1.171022653579712
```

耗时和输出均值都接近 CPU。日志中没有看到类似 GPU 的明确硬件 runtime 设置。

当前判断：SNPE NPU 当前更像 CPU 路径或无有效加速，不作为推荐路线。

## QNN CPU

QNN CPU 使用 QNN `.so` 模型库。

关键日志：

```text
Init lib_backend_file:/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnCpu.so
Loaded backend library: /usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnCpu.so
QnnInferPriv::OnInit ... "run_backend":"cpu","run_framework":"qnn"
```

当前实测结果：

```text
ok=true
execute_ms_avg=1002.9121980005584
output_mean=-1.171022653579712
```

当前判断：QNN CPU 可用，主要作为 QNN 路线基线。

## QNN GPU

QNN GPU 使用 QNN `.so` 模型库，并加载 GPU backend。

关键日志：

```text
Init lib_backend_file:/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnGpu.so
Loaded backend library: /usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnGpu.so
QnnInferPriv::OnInit ... "run_backend":"gpu","run_framework":"qnn"
QnnInferPriv::Process success to execute graph
```

设备侧 KGSL 也出现 GPU 忙碌信号：

```text
kgsl_gpu_busy_percentage=85 %
kgsl_gpubusy=854330 1001698
```

当前实测结果：

```text
ok=true
execute_ms_avg=418.5922324995772
output_mean=-1.1709520816802979
```

当前判断：QNN GPU 是真实可用的 GPU 路线，但当前速度慢于 SNPE GPU。

## QNN DSP

QNN DSP 是最能说明“进入 CDSP/HTP 后仍可能因为模型图不兼容而失败”的案例。下面记录的是未改写 FP32 `.so` 阶段的失败；0703 后续的 Pad+INT8 改写版已经可以执行完整模型。

关键日志：

```text
Init lib_backend_file:/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnHtp.so
Loaded backend library: /usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnHtp.so
The SocModel doesn't support FP16
Failed to validate op _enc1_c1__prepad_Pad with error 0xc26
MODEL_GRAPH_OP_VALIDATION_ERROR
```

`strace` 还确认它读取了 HTP 配置和 CDSP 相关库：

```text
/usr/local/lib/python3.8/dist-packages/fiboaisdk/htp_backend_ext_config.json
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnHtpNetRunExtensions.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/hexagon-v68/libQnnHtpV68Skel.so
/usr/lib/libcdsprpc.so
/dev/adsprpc-smd-secure
```

当前实测结果：

```text
ok=false
init_code=1
```

当前判断：未改写 FP32 QNN `.so` 确实进入 HTP/CDSP 初始化路径，但没有通过 HTP 后端校验，因此没有完成 DSP 推理。Pad+INT8 改写版已在后续专项中跑通，不能再把这段旧结论扩展为“QNN DSP 完整模型一定不可执行”。

## 为什么不能只看返回码

当前最容易误判的是 SNPE DSP/NPU。

如果只看：

```text
Init=0
Execute=0
```

会以为 DSP/NPU 都可用。但结合耗时、输出和日志后可以看到：

- SNPE DSP 和 SNPE NPU 都在 1 秒级，接近 CPU。
- 输出均值和 CPU 完全一致。
- SNPE DSP 有大量 `The SocModel doesn't support FP16`。

## 当前 CPU fallback 硬性判据

当前已经把判据固化到脚本：

```text
modules/radio_map_qcs6490_deploy/scripts/judge_backend_fallback.py
```

判定不再只依赖返回码，而是同时检查：

1. 后端日志证据：例如 `gpu_float32_16_hybrid`、`dsp_fixed8_tf`、`libQnnHtp.so`。
2. 相对 CPU 加速：默认要求目标 runtime 至少比 CPU 快 `1.5x`。
3. 输出特征：如果耗时接近 CPU 且输出均值与 CPU 完全一致，按 fallback 风险处理。
4. 设备侧计数：GPU 必须看到 KGSL 活动，例如 `kgsl_gpubusy` 增量或 `kgsl_gpu_busy_percentage` 大于 0；DSP/HTP 方向则看 FastRPC/CDSP 计数和库加载证据。

当前重新判定结果：

```text
outputs/snpe_backend_judgement_20260703_044730/fallback_judgement_GPU.json
outputs/snpe_backend_judgement_20260703_044730/fallback_judgement_DSP.json
outputs/snpe_backend_judgement_20260703_044730/fallback_judgement_NPU.json
```

结论：

| runtime | 判定 | 关键证据 |
| --- | --- | --- |
| SNPE GPU | `hardware_backend_confirmed` | 约 `3.82x` 加速，日志有 GPU runtime，`kgsl_gpubusy` 从 `0 0` 增加到 `744424 1004452`，GPU busy 为 `74%`。 |
| SNPE DSP | `backend_loaded_no_acceleration_evidence` | 日志有 DSP runtime，但耗时慢于 CPU，输出均值差异为 `0.0`，FastRPC 计数无增长。 |
| SNPE NPU | `suspected_cpu_fallback` | 无明确硬件 runtime 日志，耗时接近 CPU，输出均值差异为 `0.0`，KGSL/FastRPC 计数无增长。 |
- SNPE NPU 主要显示 CPU runtime 被设置成功。

因此后端判断必须使用多重证据。

## 当前推荐命令

当前推荐路线是 SNPE GPU：

```bash
source ._envs/radio-map-qcs6490-py38/bin/activate
python modules/radio_map_qcs6490_deploy/scripts/probe_fibo_dlc_runtime.py \
  --model modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc \
  --framework snpe \
  --runtime GPU \
  --mode 5 \
  --repeat 5 \
  --warmup 1 \
  --log-level info \
  --sample-device
```

QNN GPU 可作为备用验证：

```bash
source ._envs/radio-map-qcs6490-py38/bin/activate
python modules/radio_map_qcs6490_deploy/scripts/probe_fibo_dlc_runtime.py \
  --model modules/fiboaistack_229_env/outputs/qnn_model/lib/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_qnn.so \
  --framework qnn \
  --runtime GPU \
  --mode 5 \
  --repeat 5 \
  --warmup 1 \
  --log-level info \
  --sample-device
```

## 当前工程建议

短期建议：

- 固化 SNPE GPU 路线。
- 接入真实论文样本，比较 PyTorch/ONNX/SNPE GPU 输出误差。
- 把随机输入探针升级为真实输入评估脚本。

中期如果继续追求 CDSP/HTP：

- 研究 INT8 量化路线。
- 解决当前 QEMU 量化工具 SIGILL/SIGSEGV 问题。
- 检查并改造 HTP 不支持的模型算子，当前第一个明确失败点是 `Pad`。
- 尝试在 x86_64 PC 上完成量化和 HTP 目标转换，再回本机验证。

当前不建议把 SNPE DSP/NPU 当作已经成功的加速路径写入最终部署结论。
