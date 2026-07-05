/home/fibo/fibocom_slz/tools/codex-project-portable/bin/codex-project start --profile aix
/home/fibo/fibocom_slz/tools/codex-project-portable/bin/codex-project resume --profile aix 


# 01-迁移hyh代码
0510-zys-初步查看hyh代码，
0511-zys-继续查看代码，完成迁移工作，准备验证效果
0511-zys-输出不错的一个文档，作为母对话，发展其他项目
019e11e4-3ed7-78e0-ab17-ef98b8f88776

- a-new-环境构建和管理
0511-zys-‘环境+迁移+依赖’、‘env-bootstrap’
019e15b5-f936-78a3-bce2-360e98765fa3
- b-new-vscode压力降低、
0514-清理垃圾
019e1608-a77b-78b0-8ce7-7cfdbd6b34f6

- c-fork-f-01-复现论文
0511-zys-学习以及复现论文 https://www.sciencedirect.com/science/article/pii/S0952197624017548
0514-zys-推进模型拟合工作
0516-zys-通用多数据集误差来到5%以下
019e16d0-9e19-7b33-8367-472828256c51
0517-hyh-调研整合确定2D  3D 视角大致界面样式模块

https://www.sciencedirect.com/science/article/pii/S019126152030360X
https://arxiv.org/abs/2105.15189
https://github.com/castacks/cvar-energy-risk-deep-model





- d-ff-01-服务器联合仿真方案设计
0512-暂时服务器繁忙，再说
019e16d6-9292-7612-bfb6-9b5cd4fe3c04

硬件安装，风速仪、温湿度记等

cwc和zys讨论，说气象不止包含鸟瞰图，对于无人机，不同高度的天气是不一样的
1，尝试获取不同高度的天气信息
2，尝试确定气象局给出的信息是大约多少高度的，那么我们可以根据物理原理，风速随高度到地面非线性变化，温度是线性变化，由此，其他参数呢？找论文确定一下
3，地面通过硬件测试出了地面的气象信息，是否可以和气象局的空中的信息结合？预测中间不同高度的信息的情况？进行插值计算？数据重整合一下

我们要展示，是使用网页还是显示器，3d的世界，目前hyh做的是鸟瞰尺度上的无人机路线

和无线电热力强度预测的项目结合，预测无人机什么时候接收不到信号

如果无人机能联网了，那么地面的板子就可以随无人机的运动而实时纠正预测



可视化界面要多个界面，以及调查一下，目前低空无人机控制/调度使用的前端界面的样式

需要一个仿真3d世界用于无人机模拟器

调查目前上广深的无人机低空经济的网络链接方式，是无人机经常/偶尔/很少联网吗？会不会存在飞行过程中断网或高延迟情况？我需要了解前沿信息

找不到信号的时候，是一定全功率发射进行寻找吗？那可能你的功耗就会增加吗？

前端3d构建任务 yu 后端系统输入输出系统 yu 学术性研究预测模型或机器学习



