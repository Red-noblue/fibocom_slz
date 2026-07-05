# 模型格式 DLC QNN SO ONNX 的关系

## 这篇解决什么问题

这篇解释当前部署链路里出现的几种模型格式：PyTorch checkpoint、ONNX、DLC、QNN `.cpp/.bin/.json` 和 QNN `.so`。理解这些格式的边界后，就能看清为什么同一个模型会产生多个文件，以及为什么 SNPE 和 QNN 的加载方式不同。

## 当前格式流转总览

当前已经跑通或部分跑通的格式链路有两条。

第一条是当前推荐的 SNPE DLC 路线：

```text
PyTorch 模型
  -> ONNX
  -> DLC
  -> fiboaisdk + framework=snpe
  -> SNPE CPU/GPU/DSP/NPU
```

第二条是 QNN 模型库路线：

```text
PyTorch 模型
  -> ONNX
  -> QNN cpp/bin/json
  -> QNN aarch64 so
  -> fiboaisdk + framework=qnn
  -> QNN CPU/GPU/DSP
```

两条路线的共同输入是 ONNX，但最终加载格式不同。

## PyTorch checkpoint 是什么

论文项目中的模型最初来自 PyTorch。PyTorch checkpoint 通常保存：

- 模型权重。
- 训练状态。
- 优化器状态。
- 训练配置或实验记录。

这类文件适合训练和研究复现，但 Fibo AI Stack / Qualcomm SNPE/QNN 后端通常不能直接加载 PyTorch checkpoint。

因此部署前需要先导出 ONNX。

## ONNX 是什么

ONNX 是一种跨框架模型交换格式。它把模型计算图、权重、输入输出信息保存成一个通用文件，使模型可以交给厂商转换工具继续处理。

当前 ONNX 文件是：

```text
modules/fiboaistack_229_env/inputs/radio_map_liteunet.onnx
```

在本项目里，ONNX 的角色是“中间格式”，不是最终在板卡上高性能运行的格式。

## DLC 是什么

DLC 是 SNPE 使用的模型容器格式。SNPE 可以把 DLC 加载到不同 runtime 上执行，例如 CPU、GPU、DSP、NPU。

当前 DLC 文件是：

```text
modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
```

配套信息文件是：

```text
modules/fiboaistack_229_env/outputs/radio_map_liteunet.info.txt
```

当前 `fiboaisdk` 的 SNPE 路线可以直接加载 DLC：

```text
model=modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
framework=snpe
runtime=GPU
```

这是目前最推荐的本机部署方式。

## QNN cpp/bin/json 是什么

QNN 路线不是直接把 ONNX 变成 DLC，而是先通过 `qnn-onnx-converter` 生成一组 QNN 模型源文件和参数文件。

当前生成的 QNN 中间产物是：

```text
modules/fiboaistack_229_env/outputs/qnn_model/radio_map_liteunet_qnn.cpp
modules/fiboaistack_229_env/outputs/qnn_model/radio_map_liteunet_qnn.bin
modules/fiboaistack_229_env/outputs/qnn_model/radio_map_liteunet_qnn_net.json
```

它们的作用可以这样理解：

| 文件 | 作用 |
| --- | --- |
| `.cpp` | QNN 模型图的 C++ 表达，包含节点、张量和算子配置。 |
| `.bin` | 模型权重和常量数据。 |
| `_net.json` | 模型图和张量的结构描述，便于工具链记录和调试。 |

这些文件本身还不是最终推理时加载的模型。它们需要编译成当前设备可加载的共享库。

## QNN so 是什么

QNN `.so` 是把 QNN C++ 模型编译成的共享库。Fibo AI Stack 的 QNN 后端会动态加载这个 `.so`，查找其中的 QNN 模型接口函数，然后交给 `libQnnCpu.so`、`libQnnGpu.so` 或 `libQnnHtp.so` 执行。

当前 QNN 模型库是：

```text
modules/fiboaistack_229_env/outputs/qnn_model/lib/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_qnn.so
```

它是 aarch64 架构，因此适合当前 ARM64 设备原生加载。

注意：这个 `.so` 不是 Python 扩展，不应该通过 `import` 使用。它是给 Fibo AI Stack / QNN 后端加载的模型库。

## 为什么 framework=qnn 不能直接用 DLC

当前实测发现：

```text
framework=qnn + model=radio_map_liteunet.dlc
```

会失败，日志中出现：

```text
QNN not support using modeldlc now
```

这说明当前本机安装的 Fibo AI Stack QNN 路线没有把 DLC 当作可直接加载的 QNN 模型格式。它期望的是 QNN 模型库 `.so`，而不是 SNPE DLC。

因此当前结论是：

- `framework=snpe` 使用 `.dlc`。
- `framework=qnn` 使用 QNN 编译出的 `.so`。

## 为什么同一个模型会有两个部署产物

这是因为 SNPE 和 QNN 是两套不同的 Qualcomm 推理接口和工具链。

SNPE 更像上层统一运行时，使用 DLC 容器，runtime 字符串可以选择 CPU/GPU/DSP/NPU。当前 Fibo SDK 对 SNPE DLC 的支持比较直接。

QNN 更接近底层后端接口，明确加载后端库，例如：

```text
libQnnCpu.so
libQnnGpu.so
libQnnHtp.so
```

它对模型格式、算子支持和编译方式要求更直接。因此 QNN 路线生成 `.so` 后才能被当前 SDK 加载。

## 当前实测格式兼容性

| 路线 | 模型文件 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| SNPE CPU | `.dlc` | 可用 | 速度约 1 秒级，作为基线。 |
| SNPE GPU | `.dlc` | 推荐 | 当前最快、最可靠。 |
| SNPE DSP | `.dlc` | 返回成功但疑似回退 | 日志有 FP16/SoC 警告，速度和输出接近 CPU。 |
| SNPE NPU | `.dlc` | 返回成功但疑似 CPU | 日志主要显示 CPU runtime。 |
| QNN CPU | `.so` | 可用 | 速度约 1 秒级，作为 QNN 基线。 |
| QNN GPU | `.so` | 可用 | 可确认加载 `libQnnGpu.so`。 |
| QNN DSP | `.so` | 初始化失败 | 加载 HTP 后端，但失败于 `Pad` 节点和 FP16/SoC 支持。 |
| QNN 任意后端 | `.dlc` | 不支持 | 当前 SDK 日志明确提示 QNN 不支持 model DLC。 |

## 当前推荐理解方式

可以把当前部署文件分成三层：

```text
研究层：PyTorch checkpoint
交换层：ONNX
部署层：DLC 或 QNN so
```

对当前目标来说，最重要的是部署层是否能被当前设备真实加速执行。模型文件生成成功只是第一步，真正要看的是本机 SDK 加载、后端日志、推理耗时和输出一致性。

