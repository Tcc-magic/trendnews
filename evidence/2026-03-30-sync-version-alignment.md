# 任务日志：@sync 自动对齐 __version__

- 日期：2026-03-30
- 仓库：trendnews
- 关联文件：`.github/workflows/sync-upstream-direct.yml`

## 开始记录
- 问题现象：推送消息提示“发现新版本 6.6.0，当前 6.5.2”，即使用户已在推送前执行过上游合并。
- 输入来源：用户截图 + 本地代码检索结果 + 上游仓库 `trendradar/__init__.py` 内容。
- 数据时效：2026-03-30 当日检查结果。

## 关键分析
- 版本提示逻辑在运行时比较本地 `__version__` 与远端版本接口返回值。
- 同步流程使用 `git merge ... -X ours`，冲突时会偏向本地，可能导致 `trendradar/__init__.py` 中版本号被保留为旧值。
- 因此“已同步上游但版本提示仍旧”可持续出现。

## 处理内容
- 在 `Merge upstream with workflow filtering` 步骤中新增版本对齐逻辑：
  - 从 `${{ steps.check.outputs.upstream_ref }}` 读取上游 `trendradar/__init__.py`。
  - 解析上游与本地 `__version__`。
  - 若不一致，仅替换本地 `__version__ = "x.y.z"` 行为上游值。
- 若上游文件不存在或解析失败，仅输出 warning，不中断同步主流程。

## 风险与局限
- 版本号真值来源改为上游 `trendradar/__init__.py`，本地手工版本维护会被后续同步覆盖。
- 当前策略仅自动对齐 `x.y.z` 三段版本格式。

## 迁移说明
- 无迁移，直接替换。
