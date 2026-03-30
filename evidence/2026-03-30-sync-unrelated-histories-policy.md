# 任务日志：@sync 无共同历史合并策略落地

- 日期：2026-03-30
- 仓库：trendnews
- 关联文件：`.github/workflows/sync-upstream-direct.yml`

## 开始记录
- 问题现象：手动运行 `@sync` 在合并步骤报错：`fatal: refusing to merge unrelated histories`（exit code 128）。
- 输入来源：用户提供的 Actions 报错截图 + 仓库当前工作流。
- 数据时效：本地仓库快照（2026-03-30）。

## 本次决策与实现
- 无共同历史处理：允许合并（`--allow-unrelated-histories`）。
- 冲突处理策略：本地优先（`-X ours`）。
- 合并命令：
  - `git merge "${{ steps.check.outputs.upstream_ref }}" --no-edit --allow-unrelated-histories -X ours`
- 保持既有门控：仅在 `has_changes == true` 时执行合并与推送。
- 稳健性修复：上游分支缺失提示改为 ASCII 英文，避免编码导致脚本异常。
- 可读性修复：步骤名称改为 `Merge upstream into local master`。

## 风险与影响
- 因采用 `-X ours`，冲突文件将默认保留本地版本，可能覆盖上游同路径变更。
- 该策略符合“优先保持当前仓库稳定可运行”的既定目标，但会降低上游冲突变更的自动引入概率。

## 迁移说明
- 无迁移，直接替换。

## 结束记录
- 预期结果：`@sync` 不再因无共同历史直接失败；冲突场景可非交互完成并继续推送。
- 建议验证：手动触发 workflow，检查 `check` 输出 `upstream_ref`，并确认 `merge` 步骤成功。