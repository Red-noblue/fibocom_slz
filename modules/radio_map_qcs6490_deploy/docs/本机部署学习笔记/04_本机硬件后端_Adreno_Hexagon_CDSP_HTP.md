# 本机硬件后端 Adreno Hexagon CDSP HTP

## 这篇解决什么问题

这篇解释当前板卡上几个容易混淆的硬件和软件概念：Adreno GPU、KGSL、Hexagon、CDSP、HTP、FastRPC、SNPE runtime、QNN backend。它们不是同一层的东西，理解层级关系后，才能判断日志里“用了 GPU/DSP”到底意味着什么。

## 当前设备侧已经观察到的硬件线索

当前本机可以观察到以下设备和服务：

```text
/dev/kgsl-3d0
/dev/adsprpc-smd
/dev/ion
/sys/class/kgsl/kgsl-3d0
/sys/class/fastrpc/adsprpc-smd
/sys/class/subsys/subsys_cdsp
/usr/bin/adsprpcd
/usr/bin/cdsprpcd
```

Fibo SDK 中也存在 Qualcomm 后端库：

```text
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnCpu.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnGpu.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libQnnHtp.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/libSNPE.so
/usr/local/lib/python3.8/dist-packages/fiboaisdk/hexagon-v68/
```

这些说明当前系统确实具备 Qualcomm GPU 和 CDSP/HTP 相关运行环境。但具备环境不等于某个模型一定能跑在这些硬件上。

## Adreno GPU 是什么

Adreno 是 Qualcomm SoC 上的图形 GPU。当前设备上 KGSL 暴露的 GPU 型号是：

```text
Adreno643v1
```

KGSL 是 Linux/Android 系统中 Qualcomm GPU 的内核驱动接口。常见节点和状态路径包括：

```text
/dev/kgsl-3d0
/sys/class/kgsl/kgsl-3d0/gpu_model
/sys/class/kgsl/kgsl-3d0/gpuclk
/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage
/sys/class/devfreq/3d00000.qcom,kgsl-3d0/cur_freq
```

当前 SNPE GPU 和 QNN GPU 测试中，都能看到 GPU 路线显著快于 CPU，QNN GPU 还观测到 KGSL 忙碌状态。因此 GPU 是当前最可信的本机加速后端。

## Hexagon 是什么

Hexagon 是 Qualcomm 的 DSP 架构。它不是一个 Linux 进程，也不是 Python 包，而是 SoC 内部的 DSP 计算核心架构。

当前 SDK 目录中存在：

```text
/usr/local/lib/python3.8/dist-packages/fiboaisdk/hexagon-v68/
```

这里的 `v68` 表示 SDK 携带了面向 Hexagon v68 相关 DSP/HTP 侧库的支持文件，例如：

```text
libQnnHtpV68Skel.so
libSnpeHtpV68Skel.so
```

这些 skel 库通常用于通过 FastRPC 把主机侧请求发给 DSP/CDSP 侧执行。

## CDSP 是什么

CDSP 可以理解为 Compute DSP 子系统，是 Qualcomm SoC 中用于计算任务的 DSP 子系统。和它相关的服务和设备包括：

```text
cdsp.service
cdsprpcd.service
/usr/bin/cdsprpcd
/sys/class/subsys/subsys_cdsp
```

当前系统中 `cdsprpcd.service` 是运行状态，说明 CDSP RPC 服务存在。

但是，某个服务存在只说明系统具备 CDSP 通道，不代表当前模型已经在 CDSP 上成功执行。模型还必须满足后端支持、算子支持、量化格式、精度配置等要求。

## HTP 是什么

HTP 可以理解为 Qualcomm 面向 AI 推理的高性能张量处理后端能力。它通常依托 Hexagon/CDSP，并通过 QNN HTP 或 SNPE HTP/DSP 路线暴露给上层工具。

当前 QNN DSP 路线会加载：

```text
libQnnHtp.so
libQnnHtpNetRunExtensions.so
htp_backend_ext_config.json
hexagon-v68/libQnnHtpV68Skel.so
```

这说明当我们请求：

```text
framework=qnn
runtime=DSP
```

时，Fibo SDK 确实尝试进入 QNN HTP/CDSP 路径。

但当前模型最终没有完成 HTP 推理，因为初始化失败在：

```text
The SocModel doesn't support FP16
Failed to validate op _enc1_c1__prepad_Pad
MODEL_GRAPH_OP_VALIDATION_ERROR
```

这说明“尝试加载 HTP 后端”和“模型完整跑在 HTP 上”是两回事。

## FastRPC 是什么

FastRPC 是应用处理器和 DSP/CDSP 之间通信的机制。主机侧程序通过 FastRPC 调用 DSP 侧库。

当前可见节点包括：

```text
/dev/adsprpc-smd
/dev/adsprpc-smd-secure
/sys/class/fastrpc/adsprpc-smd
/sys/class/fastrpc/adsprpc-smd-secure
```

QNN DSP 路线的 `strace` 已经看到它打开了：

```text
/dev/adsprpc-smd-secure
/usr/lib/libcdsprpc.so
hexagon-v68/libQnnHtpV68Skel.so
```

这进一步证明 QNN DSP 路线确实尝试进入 CDSP/HTP 通道。

## SNPE runtime 和 QNN backend 的区别

SNPE 的接口更偏 runtime 选择。当前 Fibo SDK 中，SNPE 路线通过 `runtime` 字符串选择目标：

```text
CPU
GPU
DSP
NPU
```

QNN 的接口更偏 backend 库选择。当前实测对应关系是：

| Fibo 参数 | 实际后端库 |
| --- | --- |
| `framework=qnn, runtime=CPU` | `libQnnCpu.so` |
| `framework=qnn, runtime=GPU` | `libQnnGpu.so` |
| `framework=qnn, runtime=DSP` | `libQnnHtp.so` |

当前 `framework=qnn` 下，`runtime=HTP/NPU/AIP` 会被 SDK 报为不支持；可用字符串主要还是 `CPU/GPU/DSP`。

## NPU 在当前 SDK 中的含义

当前课程封装里提到 runtime 支持 `NPU`，但实测在 SNPE NPU 路线中主要看到 CPU runtime 被设置成功：

```text
Set cpu_float32 runtime succeeded
```

同时速度和输出都接近 CPU。因此当前不能把 `runtime=NPU` 理解成一定使用了独立 NPU。至少对当前模型和当前 SDK 来说，NPU 没有表现出真实加速证据。

## 怎么判断是否真的用了硬件加速

不能只看返回码。更可靠的判断要同时看：

- 后端选择日志。
- 加载了哪些库。
- 创建了什么节点。
- 推理耗时是否明显变化。
- 输出是否出现符合精度变化的差异。
- KGSL 或 FastRPC/CDSP 侧是否有可观察活动。

例如当前 SNPE GPU 的证据组合是：

```text
Set gpu_float32_16_hybrid runtime succeeded
NodeManager::GetNodeCreator ... all_all_infer_snpe_gpu_1.0.0
推理耗时明显快于 CPU
输出和 CPU 有轻微差异
```

当前 QNN DSP 的证据组合是：

```text
加载 libQnnHtp.so
读取 htp_backend_ext_config.json
打开 CDSP/FastRPC 相关库和设备
未改写 FP32 模型初始化失败
Pad+INT8 改写版完整模型可执行
```

因此 QNN DSP 当前可以分两层看：未改写 FP32 `.so` 只能说“进入了 HTP 初始化路径但图校验失败”；Pad+INT8 改写版已经完成推理，但精度弱于 SNPE DSP INT8，仍不作为正式主线。

## 当前最重要的硬件结论

当前板卡上最实用的部署结论是：

- Adreno GPU 路径已经可用，是当前首选。
- CDSP/HTP 运行环境存在，SNPE DSP INT8 已作为速度副主线跑通；QNN DSP Pad+INT8 改写版也已跑通完整模型，但精度仍需专项优化。
- SNPE DSP FP32 和 SNPE HTP/NPU 返回成功不能直接视为真实加速；SNPE DSP INT8 已有 FastRPC/CDSP 证据，应单独看待。
- QNN DSP 证明确实尝试使用 HTP/CDSP；未改写模型失败在模型/算子/精度支持阶段，Pad+INT8 改写版则进入“可执行但精度较弱”的阶段。

因此，当前工程推进应优先固化 GPU 部署；HTP/CDSP 应作为后续专项优化，而不是当前部署工作的前置条件。
