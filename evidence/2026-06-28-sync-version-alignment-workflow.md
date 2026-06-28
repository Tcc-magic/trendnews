# 2026-06-28 上游同步版本标识对齐修复记录

## 前置说明
- 任务目标：修复自动同步上游后本地版本标识仍停留在旧版本，导致新闻推送持续提示“发现新版本”的问题。
- 输入来源：用户截图、本地 Git 历史、`.github/workflows/sync-upstream-direct.yml`、版本检查代码与配置。
- 数据时效：最后验证日期为 2026-06-28（Asia/Shanghai）。
- 工具降级：Serena MCP 与 Sequential-Thinking MCP 本轮未作为可调用工具暴露，因此使用本地 `rg`、`sed`、`git`、`python3.11` 完成排查与验证。

## Sequential-Thinking 分析摘要
1. 推送提示的远程版本来自 `config/config.yaml` 中的上游 `version_check_url`。
2. 推送提示的当前版本来自 `trendradar.__version__`，即 `trendradar/__init__.py`。
3. 自动同步提交 `af97406` 合入上游 `4df2318` 后，代码已部分进入 6.10.0，但 `trendradar/__init__.py`、`version`、`pyproject.toml` 和 README 徽章仍保持 6.5.2。
4. 现有同步脚本只尝试对齐 `trendradar/__init__.py`，覆盖范围不足，且 shell/sed 文本处理不利于审计与扩展。

## 变更内容
- 将同步 workflow 中的单文件版本对齐逻辑替换为内嵌 Python 脚本。
- 从上游 `version` 文件优先解析主程序版本，失败时回退到上游 `trendradar/__init__.py`。
- 同步对齐本地 `version`、`trendradar/__init__.py`、`pyproject.toml`、`README.md`、`README-EN.md` 中的版本标识。
- 保留本地文件其他内容，仅替换版本号文本。
- 无迁移，直接替换。

## 风险与不确定性
- 本变更只影响未来自动同步上游时的版本标识对齐，不会主动触发当前 Actions。
- 若上游未来移除 `version` 且 `trendradar/__init__.py` 中也不存在语义化版本号，脚本会跳过对齐并输出告警。
- 当前仓库已有上一步 Actions 导入期修复的未提交变更，本次仅追加 workflow 与证据记录。

## 验证结果
- `git diff --check`：通过。
- 内嵌 Python 脚本 AST 解析：通过。
- `/tmp` 临时 worktree 复现 `af97406^1` 合并上游 `4df2318` 后运行新脚本：通过，`version`、`trendradar/__init__.py`、`pyproject.toml`、`README.md`、`README-EN.md` 均对齐到 `6.10.0`。
- `actionlint`：本机未安装，未执行；未触发 GitHub Actions。
- 临时 worktree 已清理。
