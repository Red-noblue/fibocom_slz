# RCBEVDet MinerU Extract

这是一个整理到 `tools/` 目录下的自包含工具包，用来把 PDF / Word / PPT / 图片 / URL 文件提交给 **MinerU API**，然后把结果规整落盘成稳定目录。

这次重构的重点不是换个地方摆脚本，而是把原来那种“压缩包解出来就开跑”的临时结构收拾干净：

- 去掉了 `__MACOSX`、`.DS_Store`、`__pycache__`、`未命名` 这类垃圾和重复副本
- 把源码、鉴权、输出目录分开，避免代码和运行结果混在一起
- 默认路径不再绑死旧 `RCBEVDet/` 仓库，而是跟着工具包自身走
- 提供固定入口 `bin/rcbevdet-mineru-extract`，从任意工作目录都能调用

## 目录结构

```text
rcbevdet-mineru-extract/
├── bin/
│   └── rcbevdet-mineru-extract      # 主入口
├── conf/
│   ├── README.md                    # 鉴权文件说明
│   ├── keys/
│   │   ├── active.json              # 当前实际 key（敏感）
│   │   └── active.sample.json       # 脱敏示例
│   └── tokens/
│       └── 1.md                     # 兼容旧版单行 JWT（敏感）
├── out/                             # URL 默认输出目录
├── src/
│   └── rcbevdet_mineru_extract/
│       ├── __main__.py
│       ├── cli.py
│       ├── layout.py
│       ├── materialize.py
│       ├── mineru_api.py
│       └── token_util.py
└── tests/
    └── smoke_cli.sh                 # 本地冒烟测试
```

## 默认行为

- `quota`：查询 MinerU 配额
- `paths`：打印工具包路径解析结果
- `extract`：提交本地文件或 URL 给 MinerU，等待结果完成后下载 `full_zip_url`
- 本地文件默认输出到输入文件旁边的 `<stem>__mineru/`
- URL 默认输出到工具包内的 `out/<stem>__mineru/`
- 如果传 `--out-root`，会在目标根目录下新建 `mineru_extract_<时间戳>/`
- 默认优先读取 `conf/keys/active.json`；如果不存在，则回退到 `conf/tokens/1.md`

## 快速开始

查看路径：

```bash
cd /home/user/DeepOFDM-ReceiverLab/tools/rcbevdet-mineru-extract
./bin/rcbevdet-mineru-extract paths
```

查看帮助：

```bash
./bin/rcbevdet-mineru-extract --help
```

查询配额：

```bash
./bin/rcbevdet-mineru-extract quota
```

抽取本地文件：

```bash
./bin/rcbevdet-mineru-extract extract /path/to/a.pdf
```

抽取 URL：

```bash
./bin/rcbevdet-mineru-extract extract --url https://example.com/a.pdf
```

集中输出：

```bash
./bin/rcbevdet-mineru-extract extract \
  --out-root /tmp/mineru_runs \
  /path/to/a.pdf \
  --url https://example.com/b.pdf
```

## 输出结果

每个输入会生成一个独立目录，常见内容如下：

- `meta.json`：MinerU 返回的关键元数据
- `run_meta.json`：本次执行时的本地运行参数
- `raw/`：解压后的原始结果
- `main.md`：主 markdown 文档，图片引用已重写为本地路径
- `text.md`：阅读版文本，图片被替换为图片实体和绝对路径
- `images/`：本地图片实体
- `images_manifest.md`：图片实体映射清单

## 设计约束

- 整个目录可整体移动；入口脚本会按自己的相对位置重新解析根目录
- 敏感 token 不会在错误日志里明文输出
- 代码和输出目录彻底分离，不再往 `src/` 里面写运行产物
