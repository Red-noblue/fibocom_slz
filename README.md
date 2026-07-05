# fibocom_slz 工作区说明

当前 UAV 虚拟验证相关内容已经按模块平铺到 `modules/` 下，避免在 `modules/UAVs_sim/projects/` 中再次嵌套子项目。

## 关键目录

```text
fibocom_slz/
  modules/
    uav_virtual_validation/   UAV 真实城市虚拟验证 Web 工作台
    web_automation_checks/    Web/3D 页面自动化检查
  use_scripts/
    start_uav_virtual_validation.sh
```

## 启动 UAV 虚拟验证工作台

```bash
./use_scripts/start_uav_virtual_validation.sh
```

查看状态：

```bash
./use_scripts/start_uav_virtual_validation.sh status
```

停止服务：

```bash
./use_scripts/start_uav_virtual_validation.sh stop
```

默认访问地址由脚本输出，例如：

```text
http://<开发板IP>:8090/
```

## 详细文档

```text
modules/uav_virtual_validation/docs/README.md
modules/uav_virtual_validation/docs/操作/开发板启动.md
modules/uav_virtual_validation/docs/操作/启动访问.md
```
