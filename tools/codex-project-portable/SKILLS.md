# Codex Skills 安装清单

本目录记录项目便携 Codex 工具内安装的开源 skills。安装位置为：

```text
codex-project-portable/mycodex/sessions/skills/
```

## 来源

- `openai/skills`：`724cd511c96593f642bddf13187217aa155d2554`
- `feiskyer/codex-settings`：`06025f674c7ab6448855f01fd5459adea24b49f5`
- `jdrhyne/agent-skills`：`6768672b15fc81bcee933e311c14ee04b4a97ecd`
- 安装日期：`2026-04-26`

## 已安装 skills

| Skill | 用途 |
| --- | --- |
| `jupyter-notebook` | 创建、整理和验证实验 Notebook，适合 BER 曲线、消融实验和复盘记录。 |
| `pdf` | 阅读、生成和检查 PDF，适合课程 PDF、论文 PDF 和最终报告排版检查。 |
| `doc` | 阅读、生成和检查 DOCX，适合课程作业报告文档。 |
| `security-best-practices` | 做 Python/脚本安全和工程卫生检查，避免长期项目里埋低级坑。 |
| `cli-creator` | 后期把实验管理沉淀成稳定 CLI，例如 `ofdm-run`、`ofdm-report`。 |
| `gh-fix-ci` | 项目接入 GitHub Actions 后，用于定位和修复 CI 失败。 |
| `autonomous-skill` | 夜间无人值守续跑核心：任务拆解、session 恢复、日志和次日报告。 |
| `deep-research` | 夜间论文、资料、方案调研与报告整合。 |
| `planner` | 把复杂工程目标拆成带依赖、验收标准和风险的计划。 |
| `parallel-task` | 对明确计划中的非重叠任务做并行推进。 |

## 未安装但可选

- `task-orchestrator`：目前暂不安装。它适合 tmux + GitHub issue + 多 worktree 的大规模编排，但当前机器没有 `tmux` / `gh`，而且本项目现阶段还没到需要多 PR 编排的程度。

## 版本管理策略

只允许开源 skills 跟随项目版本管理。以下内容继续忽略：

- `auth.json`
- `config.toml`
- sqlite 状态库
- 历史会话
- memories
- shell snapshots

原因很简单：skills 是可复用工具，认证和历史会话是敏感状态。把后者提交进仓库属于自找麻烦。

## 使用方式

从项目根目录启动便携 Codex：

```bash
cd /home/chenzy/Yansongs_Mickey_Mouse_Clubhouse/哆啦A梦百宝箱/codex-project-portable
./bin/codex-project start --profile zys
```

安装或更新 skills 后，需要重启 Codex 才能让当前会话识别新增 skills。

## 夜间任务入口

项目根目录提供了一个简化入口：

```bash
./scripts/codex_nightly.sh "继续推进案例2 baseline 数据接入和最小训练闭环"
```

继续已有任务：

```bash
./scripts/codex_nightly.sh --task-name case2-baseline --continue --resume-last
```

默认最多跑 `8` 个 Codex session。要调整：

```bash
AUTONOMOUS_MAX_SESSIONS=12 ./scripts/codex_nightly.sh "任务描述"
```
