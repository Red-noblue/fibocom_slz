# Codex Project Portable

这是一个放在项目内使用的 `codex-cli` 便携工具包。

它的目标不是继续依赖机器级 `~/.codex`，而是把：

- `node` / `codex` 运行时，放进工具包自己的 `runtime/`
- 可切换的账号与配置，放进当前 `configs_root/<profile>/`
- 当前工具包的会话、sqlite、memories、shell snapshots 等状态，放进当前 `local_codex_home/`

这样同一个项目里的 Codex 状态、配置切换和恢复入口都集中到工具同级的 `.codex-portable/`。

如果你是把这个工具复制到一个全新的项目里，先看：

- [INIT_NEW_PROJECT.md](/home/chenzy/Yansongs_Mickey_Mouse_Clubhouse/哆啦A梦百宝箱/codex-project-portable/INIT_NEW_PROJECT.md)

## GitHub 认证建议

如果这个工具后续要单独建 GitHub 仓库，当前更推荐使用：

- `HTTPS` 远端
- `gh auth login --web --git-protocol https`
- `gh auth setup-git`

这样 Git 的 `clone` / `pull` / `push` 会通过 GitHub CLI 的浏览器授权 token 完成认证，不需要手工生成和上传 SSH 公钥。

典型流程：

```bash
git remote set-url origin https://github.com/<owner>/<repo>.git
gh auth login --web --git-protocol https
gh auth setup-git
git push -u origin main
```

如果服务器位于中国、直连 `github.com` 不稳定，可配合同目录下的 `proxy-tunnel`，只对单次 Git 命令走代理。

## 当前目录结构

```text
codex-project-portable/
├── bin/
├── runtime/
├── shell/
├── skill/
├── state/
├── INIT_NEW_PROJECT.md
├── README.md
└── USER_GUIDE_ZYS.md

同级默认状态目录：
../.codex-portable/
├── configs/
└── sessions/
```

- `bin/`：主命令与快捷包装命令
- `runtime/`：工具内自带的 `node` / `codex` 运行时
- `../.codex-portable/configs/<profile>/`：默认 profile 配置目录
- `../.codex-portable/sessions/`：默认会话、sqlite、memories 等状态目录
- `shell/`：给你自己快速启用别名与 PATH
- `skill/`：给 agent 看的简版说明
- `state/`：旧版状态目录，只保留兼容迁移用途
- `mycodex/`：仅保留给显式 `--internal-state` 的兼容模式，不再默认创建

## 当前默认行为

脚本默认会：

1. 从当前 `configs_root/` 发现可用 profile
2. 如果只有一个有效 profile，就直接使用它
3. 如果有多个有效 profile，优先默认 `zys`，并在交互启动时允许你选择
4. 默认优先使用 `runtime/bin/node` 和 `runtime/bin/codex`
5. 把选中 profile 的 `auth.json` / `config.toml` 复制到当前 `local_codex_home/`
6. 用当前 `local_codex_home/` 作为 `CODEX_HOME` 启动 `codex`
7. 让 `sessions/`、sqlite、memories、shell snapshots 都写入当前状态根目录
8. `codex` 退出后默认删除运行时复制出的 `auth.json` / `config.toml`
9. 如果当前 `local_codex_home/` 为空且旧版 `state/codex-home/` 有数据，会自动迁移进去

## 路径原则

```text
toolkit_root:
  当前这个 codex-project-portable 目录

configs_root:
  默认取工具同级 .codex-portable/configs；
  显式要求旧模式时，回退到 <toolkit_root>/mycodex/configs

local_codex_home:
  默认取工具同级 .codex-portable/sessions；
  显式要求旧模式时，回退到 <toolkit_root>/mycodex/sessions

project_root:
  默认优先向上查找名为 Yansongs_Mickey_Mouse_Clubhouse 的目录；
  未命中时，如果工具位于 <project>/tools/ 下，默认取上一级项目根；
  否则默认取工具目录的上一级目录。

workspace_dir:
  默认等于 project_root，也就是当前默认会落到 Yansongs_Mickey_Mouse_Clubhouse；
  可通过 -C / --workspace-dir 临时改成其他工作空间目录。
```

## 兼容性

- Shell: `bash 3.2+`（macOS 默认）和常见 `bash 4+` Linux
- 依赖: `python3`、`curl`
- `runtime install` 和 `pack` 会用到 `tar`，但解压步骤有 Python 兜底
- 已避免 `mapfile`、`find -printf`、`readlink -f` 这类 GNU-only 写法
- 支持 Linux `x86_64` / `arm64` 和 macOS `x86_64` / `arm64`

当前配置目录里已有 3 个 profile：

- `fyx/`
- `nzr/`
- `zys/`

当前有效 profile 通常是：

```text
configs_root/zys
```

注意：

- `bin/codex-project` 不依赖固定外部绝对路径；移动整个工具目录后，会按新位置重新解析 `toolkit_root`、`project_root` 和 `local_codex_home`。
- 默认优先走工具目录内的 `runtime/bin/node` 和 `runtime/bin/codex`，不再依赖宿主机全局 `codex`。
- `repair-state` 会修复 sqlite 里旧机器残留的 `rollout_path`，用于后续确有迁移历史时的兼容修复。
- 当前工具包已清理旧 `session`、`memory`、sqlite 和 shell snapshot 历史；后续会从新的运行状态重新生成。
- 需要确认当前实际使用的路径时，以 `codex-project where`、`codex-project doctor` 或 `codex-project status` 的输出为准。

## 最常用命令

直接启动：

```bash
./bin/codex-project start
```

指定 profile 启动：

```bash
./bin/codex-project start --profile zys
```

指定工作空间目录启动：

```bash
./bin/codex-project start --profile zys -C /tmp
```

从官方源安装工具内运行时：

```bash
./bin/codex-project runtime install
```

打开交互式运行时管理器：

```bash
./bin/codex-project runtime
```

使用工具内 npm 更新 Codex CLI：

```bash
./bin/codex-project runtime update
```

初始化为新项目内模块：

```bash
./bin/codex-project init
```

把 `configs/` 和 `sessions/` 固定到工具同级的 `.codex-portable/`，但仍直接运行工具：

```bash
./bin/codex-project init --state-root ../.codex-portable
```

如果还想把当前工具内已有 `mycodex` 状态一并迁过去：

```bash
./bin/codex-project init --state-root ../.codex-portable --import-existing-state
```

一键打包便携工具包：

```bash
./bin/codex-project pack
```

直接生成轻量新项目包：

```bash
./bin/codex-project pack clean-online
```

按目标平台生成离线可用包：

```bash
./bin/codex-project pack clean-offline --target linux-x64
```

迁移旧项目并保留历史状态：

```bash
./bin/codex-project pack migrate-full
```

默认权限：

```text
codex-project 默认会自动附加 --dangerously-bypass-approvals-and-sandbox
profile 配置内也设置了 sandbox_mode = "danger-full-access"
```

兼容旧习惯的 `--yolo` 启动：

```bash
./bin/codex-project start --profile zys --yolo
```

临时禁用默认危险模式：

```bash
./bin/codex-project start --profile zys --safe
```

说明：

- 该工具包默认会带 `--dangerously-bypass-approvals-and-sandbox`
- `--yolo` 会被映射为当前 `codex-cli` 的 `--dangerously-bypass-approvals-and-sandbox`
- `--safe` / `--no-yolo` / `--no-danger` 可关闭本次默认危险模式参数
- 除 `--profile` 外，其它参数默认继续透传给 `codex`
- 如果不想使用默认工作目录 `Yansongs_Mickey_Mouse_Clubhouse`，直接用 `-C /你的/目录`
- `runtime install` 会按当前服务器兼容性推荐官方 Node 版本；需要手动指定时也可写成 `runtime install v16.20.2` 这类形式
- `init` 会生成根目录下的 `portable-init.env`，把项目名、相对 project_root、相对 workspace_dir 和默认 profile 固化到工具内；它适合你把工具复制到新项目后先执行一次
- `init` 默认会把 `configs/` 和 `sessions/` 固定到工具同级的 `.codex-portable/`；后续仍可直接运行 `./bin/codex-project`
- 该默认初始化不会自动搬运已有 `mycodex/`；如需导入旧状态，请显式加 `--import-existing-state`
- 如需改到其他目录，可在初始化时加 `--state-root <目录>`；如需继续沿用工具内 `mycodex/`，可加 `--internal-state`
- `pack` 提供 3 种模式：
  `clean-offline` 适合新项目且目标平台已知，会自动下载并打包对应平台 runtime；
  `clean-online` 适合新项目且目标平台不确定，只保留工具骨架与 configs；
  `migrate-full` 适合旧项目迁移，保留 runtime、sessions、state_5.sqlite、memories、skills、history.jsonl

查看有哪些 profile：

```bash
./bin/codex-project profiles
```

查看当前工具包内已有 session：

```bash
./bin/codex-project sessions
```

`sessions` 表里的 `timestamp` 现在表示该 session 日志里的最新事件时间，也就是最近使用时间，不是创建时间。

按 session id 恢复：

```bash
./bin/codex-project resume --profile zys <session-id>
```

恢复最近一条：

```bash
./bin/codex-project last --profile zys
```

在指定工作空间目录恢复：

```bash
./bin/codex-project resume --profile zys -C /tmp <session-id>
```

查看路径解析结果：

```bash
./bin/codex-project where
```

健康检查：

```bash
./bin/codex-project doctor
```

查看当前状态：

```bash
./bin/codex-project status
```

修复历史 sqlite 里的旧路径：

```bash
./bin/codex-project repair-state
```

本地便携性自检：

```bash
./bin/codex-project selftest --profile zys
```

非交互执行一轮：

```bash
./bin/codex-project exec --profile zys "帮我总结当前项目"
```

在指定工作空间目录里非交互执行：

```bash
./bin/codex-project exec --profile zys -C /tmp "帮我总结当前目录"
```

## 快捷命令

如果你用 `zsh`：

```bash
source ./shell/use.zsh
```

如果你用 `bash`：

```bash
source ./shell/use.bash
```

加载后有两个关键行为：

- 直接输入 `codex --profile try`、`codex resume <session-id>` 这类命令，会自动转发到当前工具包的 `codex-project`
- 转发到原始 `codex` 的兜底分支，也会主动剥离继承的 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_API_BASE`

这不是花活，是为了避免你机器上的全局 `~/.codex` 和 `OPENAI_*` 环境变量把当前 profile 串脏。

启用后可直接使用：

- `cdx`：启动当前项目的 Codex
- `cdxr <session-id>`：按 session id 恢复
- `cdxl`：恢复最近一条
- `cdxp`：打开 resume picker
- `cdxs`：列出本工具包里的 session
- `cdxd`：环境检查
- `cdxst`：查看当前状态
- `cdxfix`：修复历史状态里的旧路径
- `cdxcheck`：做本地便携性自检
- `cdxrt`：打开 runtime 管理器
- `cdxh`：打印帮助

## 日常使用

如果你平时主要使用 `zys`，最短启动路径通常是：

```bash
source ./shell/use.zsh
cdx --profile zys
```

如果不想加载快捷命令，直接运行：

```bash
./bin/codex-project start --profile zys
```

如果你已经执行过 `./bin/codex-project init`，当前状态目录通常会落在工具同级的 `.codex-portable/`；但这不是死规则，最终以：

```bash
./bin/codex-project where --profile zys
```

里的 `configs_root`、`local_codex_home` 为准。

最常用的恢复方式是：

- `cdxs` 或 `./bin/codex-project sessions`
- `cdxl --profile zys`
- `cdxr --profile zys <session-id>`
- `cdxp --profile zys`

如果你要排查“到底用了哪套路径、哪套 profile、哪套 runtime”，最有用的是：

- `./bin/codex-project where --profile zys`
- `./bin/codex-project doctor --profile zys`
- `./bin/codex-project status --profile zys`
- `./bin/codex-project repair-state`
- `./bin/codex-project selftest --profile zys`

重点看这些字段：

- `selected_profile`
- `toolkit_root`
- `project_root`
- `workspace_dir`
- `configs_root`
- `local_codex_home`
- `node_bin`
- `codex_bin`

有几个行为边界需要记住：

- 默认会主动剥离继承进 shell 的 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_API_BASE`
- 运行结束后，复制到运行态目录的 `auth.json` / `config.toml` 默认会被清掉
- 但 `session`、sqlite、`memories`、`shell_snapshots` 这类状态会保留在当前状态根目录里
- 如果历史 session 因目录迁移出现旧路径残留，优先先跑 `repair-state`

## 环境变量

```bash
export CODEX_PORTABLE_PROFILE=zys
```

固定使用某个 profile。

```bash
export CODEX_PORTABLE_CONFIGS_ROOT=/你的/配置目录
```

覆盖 profile 根目录。

```bash
export CODEX_PORTABLE_HOME=/你的/本地状态目录
```

覆盖运行时 `CODEX_HOME`。

```bash
export CODEX_PORTABLE_WORKSPACE_DIR=/你的/工作空间目录
```

覆盖默认工作空间目录；若未设置，则默认使用 `project_root`。

```bash
export CODEX_PORTABLE_KEEP_SOURCE_FILES=1
```

保留运行时复制到 `local_codex_home/` 的 `auth.json` / `config.toml`。

```bash
export CODEX_PORTABLE_NO_PROFILE_PROMPT=1
```

有多个有效 profile 时不弹交互选择，直接用默认 profile。

```bash
export CODEX_PORTABLE_DEFAULT_YOLO=0
```

关闭默认自动添加的危险模式参数。

```bash
export CODEX_PORTABLE_WORKSPACE_ROOT_NAME=MyProject
```

覆盖默认向上查找的工作空间根目录名。

如果你不想每次手工导出这些环境变量，直接执行一次：

```bash
./bin/codex-project init
```

它会在工具根目录生成 `portable-init.env`，并把这些默认值随项目一起保存下来。

## 对 agent 的建议

优先让 agent 读取：

- `./skill/SKILL.md`

需要命令细节再看：

- `./README.md`

如果是你自己日常使用，优先看：
- 本文的“最常用命令”“快捷命令”“日常使用”“注意事项”

## 注意事项

- 当前真正的本地状态根目录，以 `where` 输出的 `local_codex_home` 为准；默认初始化后通常是工具同级的 `.codex-portable/sessions/`。
- 当前真正的 profile 根目录，以 `where` 输出的 `configs_root` 为准；若仍沿用旧模式，则可能还是工具内 `mycodex/configs/`。
- `auth.json` 和 `config.toml` 属于敏感配置，应自行保管。
- `state/` 仍然保留，但现在只作为旧版状态迁移兼容目录，不再是默认工作目录。
