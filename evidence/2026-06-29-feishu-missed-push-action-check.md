# 2026-06-29 飞书漏推与 Actions 绿灯失败排查记录

## 前置说明
- 任务目标：排查 2026-06-28 晚间 GitHub Actions 跑完但未向飞书推送新闻的问题，并确认修复后是否仍有阻断性 bug。
- 输入来源：本地配置、GitHub Actions 只读日志、本地代码。
- 数据时效：最后验证日期为 2026-06-29（Asia/Shanghai）。
- 工具降级：Serena MCP 与 Sequential-Thinking MCP 本轮未作为可调用工具暴露，因此使用 `rg`、`sed`、`git`、`gh`、`python3.11` 完成排查与验证。

## Sequential-Thinking 分析摘要
1. 当前配置 `schedule.preset` 为 `tcc_custom`；2026-06-28 是周日，命中 `weekend` 日计划。
2. 周末唯一推送窗口是 `weekend_free`，时间为 `19:30-20:00`，`push: true`，`report_mode: daily`。
3. GitHub Actions 运行记录中，`28321155332` 于 2026-06-28 11:45 UTC 创建，折合北京时间 2026-06-28 19:45，理论上应处于推送窗口内。
4. 该 run 日志显示飞书环境变量已配置，但程序在配置加载后立即报错：`name 'fetch_with_fallback' is not defined`。
5. `trendradar/__main__.py` 从 `trendradar.commands` 导入了版本检查函数，但随后又定义了同名旧函数覆盖导入；旧函数调用 `fetch_with_fallback` 却没有导入该符号。
6. `main()` 捕获普通异常后只打印错误，没有返回非 0，导致 GitHub Actions 显示 success，但实际没有进入采集、分析和推送流程。

## 变更内容
- 在 `trendradar/__main__.py` 补充 `from trendradar.core.cdn import fetch_with_fallback`，修复当前被覆盖的版本检查路径。
- 在 `main()` 的 `FileNotFoundError` 与普通 `Exception` 处理后抛出 `SystemExit(1)`，避免运行失败时 Actions 仍显示成功。
- 无迁移，直接替换。

## 风险与不确定性
- 本修复不触发真实飞书推送，不验证 webhook 可达性。
- 当前 `.github/workflows/crawler.yml` 只有 `workflow_dispatch`，没有 `schedule` 定时配置；昨天的每小时运行是外部或手动触发的 `workflow_dispatch`，不是该 workflow 文件自身的 cron。
- 若未来希望 GitHub Actions 自己定时运行，需要另行恢复或新增 `on.schedule`。

## 验证结果
- GitHub Actions 只读日志：run `28321155332`（2026-06-28 11:45 UTC / 北京时间 19:45）命中周末推送窗口，但日志显示 `❌ 程序运行错误: name 'fetch_with_fallback' is not defined`。
- 固定时间调度解析：`2026-06-28 19:45:17` 解析为 `weekend/weekend_free`，`push=True`，`report_mode=daily`，`ai_mode=daily`。
- 固定时间调度解析：`2026-06-28 20:45:17` 未命中时间段，`push=False`，符合配置。
- `_fetch_remote_version` 在 monkeypatch 的 `fetch_with_fallback` 下返回正常：通过。
- `main()` 注入异常后返回 `SystemExit(1)`：通过，后续 Actions 不会再假成功。
- `python3.11 -m py_compile trendradar/__main__.py`：通过。
- `uv run --frozen python -m trendradar --show-schedule`：通过。
- `git diff --check`：通过。
- 隔离验证环境与 `__pycache__` 已清理。
