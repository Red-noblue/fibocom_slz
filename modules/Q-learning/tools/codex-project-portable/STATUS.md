# Codex Project Portable Status

当前本机兼容状态以命令输出为准：

```bash
./bin/codex-project status --profile zys
```

当前原则：

- 工具目录以脚本自身位置为准
- 默认项目根优先重算到 `Yansongs_Mickey_Mouse_Clubhouse`
- 默认本地 `CODEX_HOME` 固定使用 `<toolkit_root>/mycodex/sessions`
- 默认运行时优先使用 `<toolkit_root>/runtime/bin/node` 和 `<toolkit_root>/runtime/bin/codex`
- 默认启动会自动附加 `--dangerously-bypass-approvals-and-sandbox`
- 当前有效 profile：`zys`

兼容性检查项：

- `./bin/codex-project where`
- `./bin/codex-project doctor`
- `./bin/codex-project status`
- `./bin/codex-project sessions`
- `./bin/codex-project repair-state`
- `./bin/codex-project selftest --profile zys`
- `./bin/codex-project runtime`
- `./bin/codex-project resume --profile zys <session-id>`
- `./bin/codex-project exec-resume --profile zys <session-id> "<prompt>"`

说明：

- 当前工具包的历史 `session`、`memory`、sqlite 和 shell snapshot 记录已清理。
- 后续运行会从当前本机目录开始重新生成新的状态记录。

当前已验证：

- `codex-project where --profile zys` 能按当前工具位置返回动态路径
- `codex-project status --profile zys` 能返回当前动态路径和关键状态信息
- `codex-project runtime install` 可按当前主机兼容性从官方源安装工具内 runtime
- `codex-project runtime update` 可使用工具内 npm 更新 Codex CLI
- `codex-project runtime` 可交互安装或更新工具内 runtime
- `codex-project selftest --profile zys` 可做本地便携性检查
- `codex-project exec --profile zys` 已成功执行
- `codex-project repair-state` 可用于未来有旧 sqlite 路径残留时的兼容修复
