# 给 zys 的当前项目使用说明

这份文档只针对当前这台设备和当前项目。

## 当前使用原则

- 不依赖固定绝对路径：

```text
工具移动到哪里，就以哪里作为新的 toolkit_root
```

- 默认目录推导：

```text
默认优先向上查找名为 Yansongs_Mickey_Mouse_Clubhouse 的目录
命中后 project_root 默认解析为该目录
```

- 默认工作空间目录：

```text
workspace_dir 默认等于 project_root；
当前默认就是 Yansongs_Mickey_Mouse_Clubhouse；
可通过 -C / --workspace-dir 改成其他目录
```

- 默认运行时目录：

```text
<toolkit_root>/runtime
```

- 运行状态目录：

```text
<toolkit_root>/mycodex/sessions
```

这里的含义是：

- `node` 默认从 `runtime/bin/node` 启动
- `codex` 默认从 `runtime/bin/codex` 启动
- `auth.json` 从 `mycodex/configs/zys/auth.json` 读取
- `config.toml` 从 `mycodex/configs/zys/config.toml` 读取
- 会话、sqlite、memories、shell snapshot 等都写入 `mycodex/sessions/`

## 你最常用的启动方式

### 方式 1：进入工具目录后直接用相对命令

```bash
cd /你的/当前/codex-project-portable
source ./shell/use.zsh
cdx --profile zys
```

说明：

- 第一条命令切到工具目录
- 第二条命令加载快捷函数
- 第三条命令会按 `zys` profile 启动当前项目的交互式 Codex
- 加载后直接输入 `codex --profile zys`、`codex resume <session-id>` 也会自动走当前工具包，而不是掉回机器级 `~/.codex`
- 同时会主动隔离继承到 shell 里的 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_API_BASE`

### 方式 2：不加载快捷命令，直接启动

```bash
./bin/codex-project start --profile zys
```

如果你想在别的目录里开当前工具包下的 Codex：

```bash
./bin/codex-project start --profile zys -C /tmp
```

如果你刚换服务器，先直接从官方源安装工具内 runtime：

```bash
./bin/codex-project runtime install
```

如果你明确知道当前服务器只能跑较老的 Node，也可以手动指定：

```bash
./bin/codex-project runtime install v16.20.2
```

如果你想交互式选择安装或更新，直接打开运行时管理器：

```bash
./bin/codex-project runtime
```

如果你想按老习惯直接开 `yolo`：

```bash
./bin/codex-project start --profile zys --yolo
```

这里的 `--yolo` 会被工具包自动转换成当前 `codex-cli` 的危险模式参数。

默认情况下，即使不写 `--yolo`，这个工具也会自动附加：

```text
--dangerously-bypass-approvals-and-sandbox
```

如果某次想临时关闭这个默认危险模式参数：

```bash
./bin/codex-project start --profile zys --safe
```

## 你平时最常用的恢复方式

### 查看当前工具包里有哪些 session

```bash
./bin/codex-project sessions
```

如果你已经 `source use.zsh` 了，也可以直接：

```bash
cdxs
```

### 按 session id 恢复

```bash
./bin/codex-project resume --profile zys <session-id>
```

如果你已经 `source use.zsh` 了，也可以直接：

```bash
cdxr --profile zys <session-id>
```

### 恢复最近一条

```bash
cdxl --profile zys
```

### 打开 picker 自己选

```bash
cdxp --profile zys
```

## 当前状态说明

当前 `mycodex/sessions/` 已清理旧 `session`、`memory`、sqlite 和 shell snapshot 历史。

这意味着：

- 后续新启动出来的会话会从干净状态开始写入
- 如果你之后需要恢复，会使用你在当前工具包里新生成出来的 `session-id`
- `repair-state` 仍然保留，用于以后确实发生目录迁移时修复 sqlite 内的旧路径

## 多配置怎么用

先看有哪些 profile：

```bash
./bin/codex-project profiles
```

如果以后 `fyx` 或 `nzr` 也补齐了 `auth.json` 和 `config.toml`，启动时会自动识别为有效 profile。

如果同时有多个有效 profile：

- 交互启动时会提示你选择
- 不想被提示，可以显式传 `--profile <name>`
- 工作空间目录不想用默认项目根，可以显式传 `-C <目录>`
- 或者提前设置环境变量 `CODEX_PORTABLE_PROFILE=<name>`
- 除工具包自己的 `--profile` 外，其它参数会继续传给 `codex`
- `--yolo` 已做兼容映射，可直接继续使用

当前你应优先使用：

```text
zys
```

## 你需要知道的行为边界

- 这个工具默认不再依赖机器级 `~/.codex/auth.json` 或 `~/.codex/config.toml`
- 它会直接读取 `mycodex/configs/<profile>/` 下的配置
- 然后把真正运行时的状态写到 `mycodex/sessions/`
- 默认情况下，运行结束后，复制到 `mycodex/sessions/` 的 `auth.json` / `config.toml` 会被清掉
- 但 session、sqlite、memory、shell snapshot 都会保留

## 当你想确认当前到底用了哪套路径

运行：

```bash
./bin/codex-project where --profile zys
```

或者：

```bash
./bin/codex-project doctor --profile zys
```

或者更直接：

```bash
./bin/codex-project status --profile zys
```

如果历史 session 报旧路径错误，可以先运行：

```bash
./bin/codex-project repair-state
```

如果你要做本地便携性检查：

```bash
./bin/codex-project selftest --profile zys
```

你应该重点看这几项：

- `selected_profile=zys`
- `toolkit_root=<当前工具目录>`
- `project_root=<当前工具推导出来的项目根>`
- `workspace_dir=<当前实际启动使用的工作空间目录>`
- `node_bin=<当前工具目录>/runtime/bin/node`
- `codex_bin=<当前工具目录>/runtime/lib/node_modules/@openai/codex/bin/codex.js`
- `selected_profile_dir=<当前工具目录>/mycodex/configs/zys`
- `local_codex_home=<当前工具目录>/mycodex/sessions`

## 你最短可以怎么启动

如果你已经在工具目录，并且今天只想最快启动：

```bash
source ./shell/use.zsh
cdx --profile zys
```

如果你要在别的目录里启动：

```bash
source ./shell/use.zsh
cdx --profile zys -C /tmp
```

如果你今天只想最快恢复最近一次：

```bash
source ./shell/use.zsh
cdxl --profile zys
```

如果你今天只想恢复某个 session id：

```bash
source ./shell/use.zsh
cdxr --profile zys <session-id>
```
