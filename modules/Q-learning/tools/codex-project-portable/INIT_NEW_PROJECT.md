# 新项目初始化指导

这份文档给第一次接触 `codex-project-portable` 的人用。

适用场景：

- 你把整个 `codex-project-portable/` 复制到了另一个项目里
- 目标机器没有全局 `node`、`npm`、`codex`
- 你希望 Codex 配置、会话、记忆跟着项目一起走

这份文档按最稳妥、最容易照着做的方式来写。

## 先理解这个工具在做什么

这个工具把 `codex` 运行所需的核心内容，尽量都收进自己目录里：

- `runtime/`
  工具自己的 `node`、`npm`、`codex`
- 工具同级 `.codex-portable/configs/`
  账号配置、模型配置、profile 配置
- 工具同级 `.codex-portable/sessions/`
  会话正文、线程索引、记忆、技能等本地状态

这样做的目的很简单：

- 工具跟着项目走
- 会话跟着项目走
- 换机器后不用依赖宿主机全局环境

## 推荐放置位置

最推荐这样放：

```text
<你的项目>/
├── tools/
│   └── codex-project-portable/
└── 其他项目文件
```

原因：

- 当前脚本对 `<project>/tools/codex-project-portable` 这种位置有专门兼容
- 这样通常不用额外改路径，默认就能把项目根识别对

如果你不想放在 `tools/` 下，也能用，但后面启动时最好加 `-C <项目根目录>`。

## 第 1 步：复制整个工具目录

把整个 `codex-project-portable/` 原样复制到新项目里，不要只复制其中一部分。

复制后建议先确认目录大致长这样：

```text
codex-project-portable/
├── bin/
├── runtime/
├── shell/
├── skill/
├── state/
├── README.md
└── INIT_NEW_PROJECT.md

../.codex-portable/
├── configs/
└── sessions/
```

## 第 2 步：执行一次初始化

更推荐先执行一次：

```bash
./bin/codex-project init
```

这个命令会交互式询问：

- 当前项目名称
- 当前项目根目录
- 默认工作目录
- 默认 profile
- 是否立即安装工具内 runtime

然后在工具根目录生成：

```text
portable-init.env
```

这份文件建议随项目一起提交。它保存的是“相对工具目录”的路径，所以项目迁移到另一台服务器后仍然能继续工作。

如果你已经明确知道这些值，也可以直接写成：

```bash
./bin/codex-project init --project-root ../.. --workspace-dir ../.. --profile zys
```

`init` 默认会把状态目录放到工具同级的 `.codex-portable/`。
例如如果工具放在 `<项目>/tools/codex-project-portable` 下，
默认状态目录就是 `<项目>/tools/.codex-portable/`。
如果你希望显式写出来，可以初始化成：

```bash
./bin/codex-project init --project-root ../.. --workspace-dir ../.. --profile zys --state-root ../.codex-portable
```

这样后续工具会自动使用：

```text
<项目根>/tools/.codex-portable/configs/
<项目根>/tools/.codex-portable/sessions/
```

默认不会自动搬运工具内已有的 `mycodex/`。
如果你确实要把旧状态一起导过去，可显式执行：

```bash
./bin/codex-project init --state-root ../.codex-portable --import-existing-state
```

如果你不想启用这个外部状态目录，改回工具内 `mycodex/`，可以执行：

```bash
./bin/codex-project init --internal-state
```

再继续看下面的 profile 说明。

## 第 3 步：准备 profile 配置

进入工具目录后，先看已有 profile：

```bash
./bin/codex-project profiles
```

如果你是从旧项目整体复制过来的，工具同级 `.codex-portable/configs/` 往往已经有配置了。

如果要新建一个 profile，最少要准备：

```text
.codex-portable/configs/<profile>/
├── auth.json
└── config.toml
```

可选：

```text
version.json
```

例如：

```text
.codex-portable/configs/zys/
├── auth.json
├── config.toml
└── version.json
```

当前这个工具按私有项目使用来处理，所以 `.codex-portable/configs/` 应视为项目状态的一部分。

下面文档里的 `zys` 只是示例名，你可以替换成你自己的 profile 名称。

## 第 4 步：如果要带上旧对话，把哪些文件一起复制

这是最关键的一步。

### 最小必带集合

如果你只想确保“已有对话能继续恢复”，至少要保留：

```text
mycodex/sessions/sessions/
mycodex/sessions/state_5.sqlite
```

原因：

- `sessions/` 里是真正的会话 JSONL 正文
- `state_5.sqlite` 里有线程和 `rollout_path` 的索引关系

少了 `state_5.sqlite`，对话文本不一定丢，但标准恢复和线程索引会变差。

### 推荐一起保留

如果你希望迁移后体验更完整，建议再保留：

```text
mycodex/sessions/memories/
mycodex/sessions/skills/
mycodex/sessions/history.jsonl
```

含义：

- `memories/`：长期记忆
- `skills/`：当前本地安装或缓存的技能
- `history.jsonl`：命令与交互历史，体积通常不大，可以一起保留

### 可以忽略的内容

下面这些我建议忽略，不作为跨项目复制的核心状态：

```text
mycodex/sessions/.tmp/
mycodex/sessions/tmp/
mycodex/sessions/log/
mycodex/sessions/logs_2.sqlite
mycodex/sessions/installation_id
mycodex/sessions/.personality_migration
mycodex/sessions/shell_snapshots/
```

这些大多属于：

- 临时文件
- 诊断日志
- 本机安装痕迹
- 可重建缓存
- shell 环境快照

## 第 5 步：安装或更新工具内 runtime

这个工具现在支持完全自举，不依赖宿主机全局 `node` / `npm` / `codex`。

直接执行：

```bash
./bin/codex-project runtime install
```

它会做这几件事：

1. 自动判断当前机器适合的官方 Node 版本
2. 下载官方 Node 包到工具自己的 `runtime/`
3. 用工具内 npm 安装 `@openai/codex`
4. 整理成工具固定使用的 runtime 结构

安装完成后，检查状态：

```bash
./bin/codex-project runtime status
```

你应该重点看这几项：

- `node_exists: yes`
- `npm_exists: yes`
- `codex_wrapper_exists: yes`
- `codex_js_exists: yes`

如果你是旧工具升级过来的，也可以直接运行：

```bash
./bin/codex-project runtime update
```

## 第 6 步：确认当前路径是否识别正确

执行：

```bash
./bin/codex-project where --profile zys
```

重点看：

- `toolkit_root`
- `project_root`
- `workspace_dir`
- `local_codex_home`

如果你的工具放在：

```text
<项目>/tools/codex-project-portable
```

通常 `project_root` 会自动识别到 `<项目>`。

如果识别不对，最简单的修正方式不是改代码，而是启动时直接加：

```bash
-C <你的项目根目录>
```

例如：

```bash
./bin/codex-project start --profile zys -C /你的/项目目录
```

## 第 7 步：做一次健康检查

执行：

```bash
./bin/codex-project doctor --profile zys
```

重点看：

- `has_profile_auth: yes`
- `has_profile_config: yes`
- `node_bin: .../runtime/bin/node`
- `codex_bin: .../runtime/lib/node_modules/@openai/codex/bin/codex.js`

如果你还带了旧会话，也可以再执行：

```bash
./bin/codex-project sessions
```

能列出旧会话，就说明迁移基本成功了。

## 第 8 步：开始第一次启动

最常用启动方式：

```bash
./bin/codex-project start --profile zys
```

如果当前项目根没被自动识别对：

```bash
./bin/codex-project start --profile zys -C /你的/项目目录
```

如果你已经有旧会话，恢复方式：

```bash
./bin/codex-project sessions
./bin/codex-project resume --profile zys <session-id>
```

## 第 9 步：可选，启用快捷命令

如果你用 `bash`：

```bash
source ./shell/use.bash
```

如果你用 `zsh`：

```bash
source ./shell/use.zsh
```

之后常用命令会更短，例如：

```bash
cdx --profile zys
cdxs
cdxl --profile zys
```

## 新手最容易遇到的几个问题

### 1. 工具复制过去了，但启动不到正确项目目录

优先用：

```bash
./bin/codex-project start --profile zys -C /你的项目根目录
```

先跑通，再考虑要不要改长期放置位置。

### 2. 旧对话文件明明还在，但恢复效果不对

先确认这两个东西是不是都保留了：

```text
mycodex/sessions/sessions/
mycodex/sessions/state_5.sqlite
```

然后执行：

```bash
./bin/codex-project repair-state
```

这个命令会修复旧路径残留。

### 3. 机器上没有全局 node/npm/codex，能不能直接用？

可以。

先执行：

```bash
./bin/codex-project runtime install
```

这个工具设计目标就是不依赖宿主机全局环境。

### 4. `history.jsonl` 要不要一起提交？

可以保留。

它不是完整对话正文，不能替代 `sessions/`，但它体积通常不大，保留也不会带来明显负担。

如果你的目标是：

- 给全新项目做一个干净包：可以不带
- 给团队内部迁移旧项目：建议一起带上

### 5. `shell_snapshots/` 要不要一起提交？

一般不需要。

它更像运行时 shell 快照，不是对话核心数据。

## 一次成功初始化的最短流程

如果你只想照着做，不想理解太多，就按下面走：

1. 把整个 `codex-project-portable/` 复制到新项目的 `tools/` 下。
2. 确认 `mycodex/configs/<profile>/auth.json` 和 `config.toml` 存在。
3. 如果要保留旧对话，把 `mycodex/sessions/sessions/` 和 `mycodex/sessions/state_5.sqlite` 一起带过去。
4. 执行 `./bin/codex-project init`。
5. 如果刚才没安装 runtime，就执行 `./bin/codex-project runtime install`。
6. 执行 `./bin/codex-project doctor --profile zys`。
7. 执行 `./bin/codex-project start --profile zys`。
8. 如果目录不对，就改用 `./bin/codex-project start --profile zys -C /你的项目目录`。

做到这里，基本就能用了。
