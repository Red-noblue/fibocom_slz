# AI端侧部署开发

原始链接：<https://bbs.elecfans.com/jishu_2509049_1_1.html>

| 序号 | 课程名称 | 视频时长 | 视频链接 | 课件/附件 | 工程源码 |
|---:|---|---|---|---|---|
| 1 | [Fibo AI Stack模型转化指南](01_Fibo_AI_Stack模型转化指南/) | 27分19秒 | <https://t.elecfans.com/v/28525.html> | Fibo AI Stack模型转化指南------Docker Desktop环境操作_V2.0.pdf | 未标注 |
| 2 | [Fibo AI Stack模型推理指南](02_Fibo_AI_Stack模型推理指南/) | 11分55秒 | <https://t.elecfans.com/v/28526.html> | Fibo AI Stack模型推理指南_V2.0.pdf | 模型推理指南_V2.0.zip |

## 本项目关注点

- 这是当前无线电地图模型部署的最核心课程类别。
- 后续优先从 PyTorch checkpoint 导出 ONNX，再调查 Fibo AI Stack 是否支持转换到本机可运行格式。
- 推理指南中的输入张量名、输出张量名、运行设备选择和环境脚本应作为本项目部署适配层的参考。
