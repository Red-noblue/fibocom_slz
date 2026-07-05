# 本机部署学习笔记

本目录用于记录当前 QCS6490 设备上复现论文模型部署流程时已经探索出的知识、结论和操作边界。重点不是讲 Python 或 Docker 基础，而是解释本板卡、Fibo AI Stack、Qualcomm SNPE/QNN、Adreno GPU、Hexagon/CDSP/HTP 之间的关系。

## 当前一句话结论

当前最可用的本机部署路线是：

```text
论文模型 / PyTorch -> ONNX -> Fibo AI Stack 2.29 转换为 INT8 DLC -> 本机 fiboaisdk 使用 SNPE GPU 推理
```

其中 `ONNX -> DLC / INT8 DLC` 在本机通过 amd64 Docker 镜像和 QEMU 8.2.2 兼容运行转换工具完成；推理测试不在 Docker 里完成，而是在当前设备原生环境中调用 Fibo AI Stack Python SDK。当前 SNPE DSP INT8 已具备速度副主线价值，但默认仍优先推荐 SNPE GPU INT8。

## 建议阅读顺序

| 顺序 | 文档 | 作用 |
| --- | --- | --- |
| 0 | `../当前推荐部署路线.md` | 当前正式部署路线、就绪检查和 HTP/CDSP 边界。 |
| 0.25 | `../各路线运行示例.md` | SNPE GPU、SNPE DSP、QNN、UAV 航线等各条路线的可复制运行命令。 |
| 0.5 | `../0703-完成DSP、SNPE等部署/README.md` | 0703 阶段成果入口，汇总 INT8 GPU、SNPE DSP、QNN GPU、HTP/CDSP 专项结论。 |
| 1 | `01_整体路线总览.md` | 先理解当前方案的整体链路、为什么不是训练环境、为什么要拆成转换和推理两段。 |
| 2 | `02_Fibo_AI_Stack与Docker转换环境.md` | 解释 Docker/QEMU/Fibo AI Stack 2.29 转换环境的作用，以及镜像、容器、挂载目录在哪里。 |
| 3 | `03_模型格式_DLC_QNN_SO_ONNX的关系.md` | 解释 ONNX、DLC、QNN `.so` 等模型格式关系。 |
| 4 | `04_本机硬件后端_Adreno_Hexagon_CDSP_HTP.md` | 解释 Adreno GPU、Hexagon、CDSP、HTP 和设备节点。 |
| 5 | `05_后端实测结论_SNPE_QNN_CPU_GPU_DSP_NPU.md` | 整理 CPU/GPU/DSP/NPU 实测结果和日志证据。 |
| 6 | `06_后续优化路线与决策点.md` | 整理 SNPE GPU 主线、真实样本对齐、HTP/CDSP 专项和后续决策。 |
| 7 | `../HTP_CDSP专项/QNN_DSP图改写首轮结果.md` | 单独查看 QNN DSP Pad+INT8 改写版完整模型的结果、指标和复现命令。 |

## 当前关键目录

| 路径 | 作用 |
| --- | --- |
| `modules/fiboaistack_229_env` | Fibo AI Stack 2.29 转换工作区，保存 Docker 辅助脚本、ONNX、DLC、QNN 产物、日志和 QEMU shim。 |
| `modules/radio_map_qcs6490_deploy` | 当前设备部署验证工作区，保存本机推理探针、配置、部署说明和测试输出。 |
| `/home/fibo/fiboaistack_229_env.tar` | Fibo AI Stack 2.29 Docker 镜像归档，约 9.0GB。 |
| `/usr/local/lib/python3.8/dist-packages/fiboaisdk` | 本机原生 Fibo AI Stack Python SDK 和 Qualcomm 后端库所在位置。 |

## 当前关键产物

| 文件 | 作用 |
| --- | --- |
| `modules/fiboaistack_229_env/inputs/radio_map_liteunet.onnx` | 从论文模型导出的 ONNX 中间模型。 |
| `modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc` | 通过 Fibo AI Stack / SNPE 转换得到的 DLC 模型，目前 SNPE GPU 路线使用它。 |
| `modules/fiboaistack_229_env/outputs/radio_map_liteunet.info.txt` | DLC 模型结构信息，用于确认输入输出名和 shape。 |
| `modules/fiboaistack_229_env/outputs/snpe_quant_qemu82_full_20260703_075537/radio_map_liteunet_quantized.dlc` | QEMU 8.2.2 下通过 `snpe-dlc-quantize` 生成的 INT8 DLC，当前推荐 SNPE GPU / DSP 使用。 |
| `modules/fiboaistack_229_env/outputs/qairt_quant_qemu82_full_20260703_080039/radio_map_liteunet_qairt_quantized.dlc` | QEMU 8.2.2 下通过 `qairt-quantizer` 生成的 INT8 DLC，可作为替代量化产物。 |
| `modules/fiboaistack_229_env/outputs/qnn_model/lib/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_qnn.so` | 未改写 QNN 路线编译出的 aarch64 模型库，目前 QNN GPU 可用，QNN DSP 初始化失败在 Pad / op validation。 |
| `modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/host_build/libs/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_pad_constant_int8_qnn.so` | QNN DSP Pad+INT8 改写版完整模型库，已可执行，当前作为 HTP/CDSP 专项研究线。 |
| `modules/radio_map_qcs6490_deploy/scripts/probe_fibo_dlc_runtime.py` | 本机推理探针，用于测试 SNPE/QNN 与 CPU/GPU/DSP/NPU 后端。 |
| `modules/radio_map_qcs6490_deploy/scripts/run_snpe_gpu_inference.py` | 固化 SNPE GPU 单样本推理入口，读取真实 M2 `.npz` 样本。 |
| `modules/radio_map_qcs6490_deploy/scripts/align_snpe_outputs_with_real_sample.py` | 对齐真实样本上的 SNPE CPU/GPU 输出，并还原到 dBm 统计误差。 |
| `modules/radio_map_qcs6490_deploy/scripts/batch_snpe_gpu_repro.py` | 批量运行真实 test 样本，生成 SNPE GPU 可复现实验 summary。 |
| `modules/radio_map_qcs6490_deploy/outputs/int8_gpu_accuracy_20260703_114758` | INT8 GPU 与 FP32 GPU 的 20 样本精度对齐结果。 |
| `modules/radio_map_qcs6490_deploy/outputs/int8_dsp_accuracy_20260703_120803` | INT8 DSP 的 20 样本速度和精度结果。 |
| `modules/radio_map_qcs6490_deploy/outputs/snpe_dsp_deep_probe_20260703_115139` | SNPE DSP INT8 长 repeat 与 FastRPC/CDSP `strace` 证据。 |

## 当前推荐实践

- 日常本机运行测试优先使用 `framework=snpe`、`runtime=GPU`、`mode=5` 和 INT8 DLC。
- 对速度极敏感时可以测试 `framework=snpe`、`runtime=DSP`、`mode=5` 和 INT8 DLC，但要同时报告精度损失。
- 不要只凭 `Init` 或 `Execute` 返回码判断 DSP/NPU/HTP 成功；必须结合日志、耗时、输出差异和设备侧证据判断。
- 当前 Docker 容器只承担转换工具链职责，不作为最终推理运行环境。
- 当前不建议为了部署测试而强行复刻原论文训练依赖；部署侧应围绕本机 Fibo SDK 和板卡能力适配。
- HTP/CDSP 后续单独在 `modules/radio_map_qcs6490_deploy/docs/HTP_CDSP专项/` 中推进，不阻塞 SNPE GPU 主线。
