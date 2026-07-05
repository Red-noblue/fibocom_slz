# fiboaistack_229_env 本机转换模块

本模块用于在当前 QCS6490 / SC171V3 设备上，以 `amd64` Docker 镜像兼容运行的方式执行 `ONNX -> DLC` 转换，并集中保存相关脚本、输入、输出与日志。

## 当前事实

- 本机架构：`aarch64`
- 官方转换镜像归档：`/home/fibo/fiboaistack_229_env.tar`
- 镜像架构：`linux/amd64`
- 当前方案：`docker.io + qemu-user-static + binfmt_misc`

## 目录

```text
scripts/   运行、加载、转换脚本
inputs/    待转换的 ONNX 文件
outputs/   生成的 DLC 与检查结果
logs/      docker load、转换过程日志
```

## 常用命令

检查镜像架构：

```bash
modules/fiboaistack_229_env/scripts/check_image_arch.sh
```

加载镜像：

```bash
modules/fiboaistack_229_env/scripts/load_image.sh
```

启动转换容器：

```bash
modules/fiboaistack_229_env/scripts/run_container.sh
```

检查 x86_64 QEMU/binfmt：

```bash
modules/fiboaistack_229_env/scripts/check_qemu_x86_64.sh
```

如果量化阶段遇到 `Illegal instruction`，先把标准 `qemu-x86_64` 注册到已验证的 QEMU 8.2.2：

```bash
modules/fiboaistack_229_env/scripts/register_qemu82_binfmt.sh
```

导出无线电地图 ONNX：

```bash
modules/fiboaistack_229_env/scripts/export_radio_map_onnx.sh
```

执行 ONNX -> DLC：

```bash
modules/fiboaistack_229_env/scripts/convert_onnx_to_dlc.sh \
  modules/fiboaistack_229_env/inputs/radio_map_liteunet.onnx \
  modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc
```

## 说明

- 本模块默认通过 `sudo docker` 工作；如果后续把当前用户加入 `docker` 组，脚本也可直接复用。
- 由于镜像是 `amd64`，启动与转换速度会慢于原生 `arm64` 容器。
- 若转换失败，优先查看 `logs/` 下的最近日志。

## 当前状态

- 已完成本机 `docker.io + qemu-user-static` 搭建。
- 已成功加载 `fiboaistack_229_env:latest` 并以 `linux/amd64` 兼容模式启动容器。
- 已成功在本模块导出 `inputs/radio_map_liteunet.onnx`。
- 已通过 `qemu_pthread_mutex_compat.so` 规避早期 `hogl::ring: failed to init ring mutex. err 95` 问题。
- 已完成基础 `ONNX -> DLC`：`outputs/radio_map_liteunet.dlc`。
- 当前仍需注意：系统标准 `/usr/bin/qemu-x86_64-static` 是 `4.2.1`，量化阶段可能触发 `Illegal instruction`。
- 已验证 QEMU `8.2.2` 可让最小 `plain_conv_int8` 的 `qnn-onnx-converter --input_list` 量化转换成功，产物位于 `outputs/v2_plain_conv_int8_qemu82/`。
