# 任务日志：@sync 忽略 workflow 变更并飞书通知

- 日期：2026-03-30
- 仓库：trendnews
- 关联文件：`.github/workflows/sync-upstream-direct.yml`

## 开始记录
- 问题现象：`Push merged master` 失败，错误为 GitHub App 无 `workflows` 权限，拒绝推送含 `.github/workflows/*` 变更的提交。
- 输入来源：用户提供的 Actions 报错截图与当前工作流文件。
- 数据时效：基于本地仓库快照（访问日期：2026-03-30）。

## 关键假设
1. 同步策略固定为：上游 `.github/workflows/*` 变更不进入本仓库。
2. 非 workflow 变更仍需自动同步。
3. 飞书通知使用现有 `FEISHU_WEBHOOK_URL` Secret；若缺失，任务不应失败。

## 实施内容
- 合并步骤改为 `--no-commit`，先收集变更再决定提交。
- 收集 `.github/workflows` 变更清单（工作区 + staged），去重后写入 `GITHUB_OUTPUT`。
- 若存在 workflow 变更，执行 `git restore --source=HEAD --staged --worktree .github/workflows` 回退。
- 回退后若无有效变更，输出 `effective_changes=false` 并跳过 push。
- 回退后若仍有有效变更，执行 `git commit --no-edit`，再按条件 push。
- 新增飞书通知步骤：仅在忽略了 workflow 文件时触发；Webhook 缺失或请求失败仅 warning。

## 风险与不确定性
- 因忽略 workflow 目录，上游工作流改动不会被自动同步。
- 飞书通知依赖外部网络与 webhook 可用性；本次未在远端流水线实跑验证。

## 迁移说明
- 无迁移，直接替换。

## 结束记录
- 预期结果：不再因 `workflows` 权限不足导致 push 失败；workflow 变更被记录、忽略并通知。
- 建议验证：手动触发 `Direct sync upstream to master`，检查 `merge` 输出与 `Notify ignored workflow changes to Feishu` 步骤。