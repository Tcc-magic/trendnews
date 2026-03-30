# 任务日志：手动运行 @sync 失败修复

- 日期：2026-03-30
- 仓库：trendnews
- 关联文件：`.github/workflows/sync-upstream-direct.yml`

## 开始记录
- 问题现象：GitHub Actions 在 `Check if upstream has new commits` 步骤退出，状态码 `exit code 1`。
- 输入来源：用户提供的运行截图与仓库当前工作流文件。
- 数据时效：基于本地仓库当前分支文件快照（访问时间：2026-03-30）。
- 关键假设：
  1. 上游仓库默认分支可能不是 `master`（可能为 `main`）。
  2. 直接 `git merge-base master upstream/master` 在无公共基线时可能返回非零并触发失败。

## 处理过程与结论
- 将 `git fetch upstream master` 改为 `git fetch upstream --prune`，避免固定分支名。
- 在检查步骤增加上游分支探测：优先 `upstream/master`，其次 `upstream/main`。
- 将比较逻辑改为 `git merge-base --is-ancestor`，避免依赖 `BASE=$(git merge-base ...)` 导致脚本被 `-e` 中断。
- 新增“本地领先上游”场景：判定为 `has_changes=false`，避免无意义合并。
- 合并步骤改为使用动态输出 `${{ steps.check.outputs.upstream_ref }}`。

## 不确定性与局限
- 本次未在 GitHub Actions 远端实际回放（本地仅完成静态改动与审阅）。
- 若上游远端未来改为其他分支命名（非 `master/main`），仍会按预期报错并停止。

## 迁移说明
- 无迁移，直接替换。

## 结束记录
- 预期结果：`Check if upstream has new commits` 不再因固定分支或 `merge-base` 非零返回而失败。
- 建议验证：在 Actions 页面手动触发 `Direct sync upstream to master`，观察 `check` 与 `merge` 步骤日志。