# 2026-06-29 上游同步脚本加固记录

## 前置说明
- 任务目标：审查并优化自动合并上游脚本，降低项目自身因自动合并产生导入期、语法期或半合并 bug 的概率。
- 输入来源：本地 `.github/workflows/sync-upstream-direct.yml`、既有 `evidence/` 事故记录、Git 历史。
- 数据时效：最后验证日期为 2026-06-29（Asia/Shanghai）。
- 工具降级：Serena MCP 与 Sequential-Thinking MCP 本轮未作为可调用工具暴露，因此使用 `rg`、`sed`、`git`、`python3.11` 与临时 worktree 完成排查和验证。

## Sequential-Thinking 分析摘要
1. 既有同步脚本使用 `git merge ... -X ours`，会在冲突或重叠修改时倾向保留本地片段。
2. 近期 `NamedTuple`、飞书 formatter 裸文本、`fetch_with_fallback` 缺失均符合“上游新代码被部分合入，但配套上下文缺失”的半合并特征。
3. 自动同步的目标应从“尽量合进去”改为“能干净合并且通过冒烟验证才推送”；冲突或冒烟失败时应停止并通知。
4. 上游 workflow 目录仍按既定策略忽略，避免 GitHub App 缺少 workflows 权限导致 push 失败。

## 变更内容
- 移除自动合并命令中的 `-X ours`，保留 `--allow-unrelated-histories`。
- 合并冲突时输出冲突文件、终止同步并 `git merge --abort`，不再提交半合并结果。
- 提交前新增冒烟检查：
  - `python3 -m pip install -r requirements.txt`
  - `python3 -m compileall -q trendradar mcp_server`
  - `python3 -m trendradar --help`
  - Python 脚本检查 `trendradar.__main__.fetch_with_fallback` 已导入，并固定时间验证 `tcc_custom` 周末推送窗口。
- 新增同步失败飞书通知步骤；合并冲突或冒烟检查失败时不改 master，并提示人工处理。
- 无迁移，直接替换。

## 风险与不确定性
- 自动同步会比过去更保守：出现冲突或冒烟失败时会失败等待人工处理，而不是强行推送。
- 冒烟检查需要安装依赖，会增加同步 workflow 运行时间。
- 本次未触发远端 GitHub Actions，不验证真实飞书通知可达性。

## 验证结果
- `git diff --check`：通过。
- workflow 内嵌 Python 脚本 AST 解析：通过，共 2 个 heredoc 脚本。
- 历史事故复现：从 `878f7b1` 合并上游 `4df2318` 时，去掉 `-X ours` 后产生显式冲突并退出，冲突文件包括 `trendradar/__main__.py`、`trendradar/ai/analyzer.py`、`trendradar/ai/formatter.py` 等；不会再自动提交半合并结果。
- 本地冒烟脚本：通过，确认 `fetch_with_fallback` 已导入，且固定时间 `2026-06-28 19:45:17` 下 `tcc_custom` 周末窗口为 `push=True`、`report_mode=daily`。
- `uv run --frozen python -m compileall -q trendradar mcp_server`：通过。
- `uv run --frozen python -m trendradar --help`：通过。
- 临时 worktree、隔离验证环境与 `__pycache__` 已清理。
