# Fibo AI Stack 与 Docker 转换环境

## 这篇解决什么问题

这篇解释当前 `modules/fiboaistack_229_env` 目录的作用，以及为什么当前设备上需要用 Docker、amd64 镜像、QEMU 和一个 mutex 兼容层来完成模型转换。

如果只熟悉普通 Python/Docker 项目，这部分最容易混淆：这里的 Docker 不是为了部署服务，而是为了在当前 ARM64 板卡上运行 Fibo AI Stack 2.29 的 x86_64 转换工具。

## 当前转换环境的位置

当前主要转换工作区是：

```text
modules/fiboaistack_229_env
```

这个目录保存：

- 输入模型。
- 转换输出。
- 转换日志。
- Docker 辅助脚本。
- QEMU 兼容 shim。
- QNN 中间产物。

当前目录结构中最重要的部分是：

```text
modules/fiboaistack_229_env/
  inputs/
    radio_map_liteunet.onnx
  outputs/
    radio_map_liteunet.dlc
    radio_map_liteunet.info.txt
    qnn_model/
      radio_map_liteunet_qnn.cpp
      radio_map_liteunet_qnn.bin
      radio_map_liteunet_qnn_net.json
      lib/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_qnn.so
  logs/
  scripts/
  shims/
    qemu_pthread_mutex_compat.c
    qemu_pthread_mutex_compat.so
```

## Docker 镜像和容器在哪里

当前镜像归档文件在：

```text
/home/fibo/fiboaistack_229_env.tar
```

大小约 `9.0GB`。

加载后的 Docker 镜像是：

```text
fiboaistack_229_env:latest
```

镜像大小约 `15.5GB`。

当前运行中的容器是：

```text
fiboaistack_229_env_amd64
```

容器内工作目录是：

```text
/workspace
```

宿主机仓库通过 Docker volume 挂载到容器内：

```text
/home/fibo/fibocom_slz -> /workspace
```

这意味着宿主机路径：

```text
/home/fibo/fibocom_slz/modules/fiboaistack_229_env/inputs/radio_map_liteunet.onnx
```

在容器里对应：

```text
/workspace/modules/fiboaistack_229_env/inputs/radio_map_liteunet.onnx
```

## 容器里的 Fibo AI Stack 工具链

容器内 Fibo AI Stack / SNPE 2.29 目录是：

```text
/opt/2.29.0.241129
```

转换命令目录是：

```text
/opt/2.29.0.241129/bin/x86_64-linux-clang
```

容器内 Python 3.10 环境是：

```text
/opt/python310_env
```

`scripts/common.sh` 会统一设置这些环境变量：

```text
SNPE_ROOT=/opt/2.29.0.241129
QNN_SDK_ROOT=/opt/2.29.0.241129
PATH=/opt/2.29.0.241129/bin/x86_64-linux-clang:$PATH
LD_LIBRARY_PATH=/opt/2.29.0.241129/lib:$LD_LIBRARY_PATH
PYTHONPATH=/opt/2.29.0.241129/lib/python:$PYTHONPATH
```

## 为什么本机 ARM64 要跑 amd64 容器

当前设备是 ARM64/aarch64，但 Fibo AI Stack 2.29 转换镜像里的核心转换工具是 x86_64/amd64 版本。

普通情况下，ARM64 机器不能直接执行 x86_64 程序。Docker 可以通过：

```text
--platform linux/amd64
```

让容器以 amd64 平台运行；底层由 QEMU 用户态模拟器执行 x86_64 程序。

当前启动容器的核心逻辑在：

```text
modules/fiboaistack_229_env/scripts/common.sh
```

其中 `ensure_container_running` 会执行类似下面的 Docker 命令：

```text
docker run \
  --platform linux/amd64 \
  -itd \
  --name fiboaistack_229_env_amd64 \
  --workdir /workspace \
  -v /home/fibo/fibocom_slz:/workspace \
  fiboaistack_229_env:latest \
  bash
```

## QEMU 在这里做什么

QEMU 在这里负责把 x86_64 Linux 用户态程序翻译执行在 ARM64 主机上。它只是在“运行转换工具”这一步发挥作用。

当前路径可以理解为：

```text
ARM64 宿主机
  |
  | Docker --platform linux/amd64
  v
amd64 容器
  |
  | QEMU 用户态模拟
  v
x86_64 Fibo/SNPE 转换工具
```

这使得当前设备即使不是 x86_64 PC，也可以本机完成 `ONNX -> DLC`。

## 当前 QEMU 版本状态

当前设备上同时存在两个 x86_64 QEMU 入口：

```text
/usr/bin/qemu-x86_64-static                  -> 4.2.1
/usr/local/bin/qemu-x86_64-static-8.2.2      -> 8.2.2
```

`binfmt_misc` 里也同时能看到：

```text
qemu-x86_64        -> /usr/bin/qemu-x86_64-static
codex-qemu-x86_64  -> /usr/local/bin/qemu-x86_64-static-8.2.2
```

这会带来一个实际风险：Docker 运行 amd64 容器时如果命中旧的 `qemu-x86_64`，量化阶段可能在 Python 扩展或 QNN quantizer 中触发 `Illegal instruction`。

本模块新增了两个检查和修复入口：

```bash
modules/fiboaistack_229_env/scripts/check_qemu_x86_64.sh
modules/fiboaistack_229_env/scripts/register_qemu82_binfmt.sh
```

前者只读检查当前解释器；后者需要 sudo，会把标准 `qemu-x86_64` 重新注册到已验证的 QEMU 8.2.2。

## 为什么需要 qemu_pthread_mutex_compat.so

当前系统的 QEMU 版本较旧，运行 Fibo AI Stack 2.29 的部分 x86_64 工具时会遇到线程 mutex/futex 兼容问题。早期现象是转换工具甚至 `--help` 都可能崩溃，并出现类似：

```text
hogl::ring: failed to init ring mutex. err 95
```

为绕过这个问题，当前新增了一个轻量兼容层：

```text
modules/fiboaistack_229_env/shims/qemu_pthread_mutex_compat.so
```

它通过 `LD_PRELOAD` 在容器内加载，用于降低部分 pthread mutex 属性要求，让转换工具能启动。

这个 shim 的源码在：

```text
modules/fiboaistack_229_env/shims/qemu_pthread_mutex_compat.c
```

构建脚本是：

```text
modules/fiboaistack_229_env/scripts/build_qemu_mutex_compat.sh
```

`scripts/common.sh` 会在 shim 存在时自动追加：

```text
LD_PRELOAD=/workspace/modules/fiboaistack_229_env/shims/qemu_pthread_mutex_compat.so
```

## ONNX 到 DLC 是怎么执行的

转换脚本是：

```text
modules/fiboaistack_229_env/scripts/convert_onnx_to_dlc.sh
```

它的职责是：

1. 确认 Docker 镜像已经加载。
2. 启动或复用 `fiboaistack_229_env_amd64` 容器。
3. 检查并构建 QEMU mutex shim。
4. 把宿主机 ONNX 路径映射成容器内 `/workspace/...` 路径。
5. 在容器里执行 `snpe-onnx-to-dlc`。
6. 再执行 `snpe-dlc-info` 生成模型信息文件。
7. 把日志保存到 `modules/fiboaistack_229_env/logs/`。

核心转换命令等价于：

```text
snpe-onnx-to-dlc \
  --input_network /workspace/modules/fiboaistack_229_env/inputs/radio_map_liteunet.onnx \
  --output_path /workspace/modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
```

然后生成信息文件：

```text
snpe-dlc-info \
  -i /workspace/modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
```

## 当前已经生成的结果

当前已经成功生成：

```text
modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
modules/fiboaistack_229_env/outputs/radio_map_liteunet.info.txt
```

最近一次成功转换日志是：

```text
modules/fiboaistack_229_env/logs/onnx_to_dlc_20260702_145302.log
```

这说明当前 Docker/QEMU/shim 转换链路可以完成 `ONNX -> DLC`。

## QNN 路线为什么有一部分在本机编译

QNN 路线不是直接生成 DLC，而是先生成：

```text
radio_map_liteunet_qnn.cpp
radio_map_liteunet_qnn.bin
radio_map_liteunet_qnn_net.json
```

这些文件位于：

```text
modules/fiboaistack_229_env/outputs/qnn_model/
```

之后需要编译成当前设备可加载的 aarch64 `.so`：

```text
modules/fiboaistack_229_env/outputs/qnn_model/lib/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_qnn.so
```

因为容器内缺少合适的 aarch64 编译器，所以当前是把 QNN SDK 的必要子集提取出来，在宿主机用本机已有的 `aarch64-linux-gnu-g++` 编译。

## 转换环境与推理环境的边界

这点很重要：

- `modules/fiboaistack_229_env` 负责转换。
- `modules/radio_map_qcs6490_deploy` 负责本机部署验证。
- Docker 容器不代表最终推理环境。
- 最终推理调用的是宿主机 `/usr/local/lib/python3.8/dist-packages/fiboaisdk`。

当前本机推理探针是：

```text
modules/radio_map_qcs6490_deploy/scripts/probe_fibo_dlc_runtime.py
```

它会直接调用：

```python
from fiboaisdk.api_aisdk_py import api_infer_py
```

因此，转换阶段和推理阶段虽然都叫 Fibo AI Stack，但运行位置和目的不同。

## 容易误解的点

### Docker 里能跑转换，不代表 Docker 里能测硬件

Docker 容器主要用于跑 x86_64 转换工具。Adreno GPU、CDSP、HTP 等硬件验证应在宿主机原生 SDK 中完成。

### QEMU 能跑转换工具，不代表适合所有工具

当前 `snpe-onnx-to-dlc` 和非量化 `qnn-onnx-converter` 已经可用。旧 QEMU 4.2.1 下，量化工具 `qairt-quantizer`、`snpe-dlc-quantize` 和 `qnn-onnx-converter --input_list` 都出现过 SIGILL/SIGSEGV。

后续定位显示，QEMU 8.2.2 能让最小 `plain_conv_int8` 的 `qnn-onnx-converter --input_list` 成功生成量化 QNN 产物。因此当前判断从“本机 QEMU 不能量化”更新为：“必须确保命中 QEMU 8.2.2；完整 SNPE/QAIRT 量化还需要在该条件下复测”。

### QNN `.so` 不是普通 Python 扩展

`libradio_map_liteunet_qnn.so` 是 QNN 模型库，供 Fibo AI Stack / QNN 后端加载，不是直接 `import` 的 Python 模块。

## 当前建议

当前阶段建议把 `modules/fiboaistack_229_env` 视为固定的转换工具工作区，不要频繁变动。日常部署测试应主要在：

```text
modules/radio_map_qcs6490_deploy
```

中继续推进。

只有在需要重新导出模型、重新转换 DLC、尝试 QNN `.so` 或继续研究 INT8/HTP 时，才进入 `modules/fiboaistack_229_env`。
