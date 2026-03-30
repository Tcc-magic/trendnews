# 任务日志：修正 @sync 在 Actions 中的显示名称

- 日期：2026-03-30
- 仓库：trendnews
- 关联文件：`.github/workflows/sync-upstream-direct.yml`

## 开始记录
- 问题现象：Actions 页面左侧与顶部显示 `.github/workflows/sync-upstream-direct.yml`，运行列表还出现 `debug` 等不符合预期的名称。
- 输入来源：用户提供的 Actions 页面截图与当前 workflow 文件。
- 数据时效：基于本地仓库快照与远端 `master` 原始 workflow 文件（2026-03-30）。

## 处理结论
- GitHub Actions 左侧工作流名称与页面顶部标题主要取自 workflow 顶层 `name`。
- 单次运行标题优先取自 `run-name`；历史运行不会因为后续改名而回写。
- 本次将 workflow 顶层名称统一调整为 `Sync Upstream to Master`，保留运行名称 `Sync upstream to master`。

## 不确定性
- 已存在的历史运行名称不会被这次修改追溯更新。
- 若页面仍显示旧名称，通常需要等待新一次运行生成后才能完全刷新展示。

## 迁移说明
- 无迁移，直接替换。
