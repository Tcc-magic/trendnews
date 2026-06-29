# 2026-06-29 与上游兼容合并修复记录

## 前置说明
- 任务目标：基于本仓库与上游 `sansan0/TrendRadar` 的完整比对，修复持续出现的半合并错误，做一次更兼容的上游合并。
- 输入来源：本地仓库、`upstream/master`、用户提供的 Actions 截图。
- 数据时效：最后验证日期为 2026-06-29（Asia/Shanghai），上游引用为 `upstream/master`。
- 工具降级：Serena MCP 与 Sequential-Thinking MCP 本轮未作为可调用工具暴露，因此使用 `git`、`rg`、`sed`、`python3.11`、`uv` 完成排查与验证。

## Sequential-Thinking 分析摘要
1. 截图中的 `name 're' is not defined` 来自旧的半合并 `trendradar/__main__.py`：本地保留了旧版内联版本检查函数，却缺少 `import re`。
2. 上游最新版 `__main__.py` 已移除这段重复旧逻辑，改为使用 `trendradar.commands.version`，因此采用上游主程序比继续补单点导入更稳。
3. 上游已迁移到 Python 3.12 + `uv sync --frozen`，并删除 `requirements.txt`；本地 workflow 仍用 Python 3.10 + pip requirements，会与上游依赖体系不兼容。
4. 本仓库存在本地定制：选股通数据源、`tcc_custom` 时间线、同步上游 workflow 与审计 evidence。这些不应被上游覆盖。

## 变更内容
- 运行代码整体对齐上游最新版：`trendradar/`、`mcp_server/`、`docker/`、`docs/assets/script.js`、`pyproject.toml`、`version`、`version_mcp`。
- 保留并恢复本地选股通扩展：`trendradar/crawler/fetcher.py`、`trendradar/core/loader.py`。
- 在上游版 `trendradar/__main__.py` 中补入 `xuangutong_config=self.ctx.config.get("XUANGUTONG", {})`，确保选股通配置仍能传入抓取器。
- 保留 GitHub Actions 友好的异常退出：配置缺失或运行异常时继续 `SystemExit(1)`，避免错误被打印后 job 仍显示成功。
- 调整 `.github/workflows/crawler.yml`：保留本地 `workflow_dispatch` 策略，但运行环境改为 Python 3.12 + uv，与上游依赖体系一致。
- 调整 `.github/workflows/sync-upstream-direct.yml`：自动合并后的冒烟检查改为 Python 3.12 + uv，避免继续引用已删除的 `requirements.txt`。
- 删除过时 `requirements.txt`，使用 `uv.lock` 与 `pyproject.toml` 作为依赖真值。
- 保留本地 `config/`、`.github/workflows/sync-upstream-direct.yml`、`evidence/` 记录和本地 README 内容。

## 验证结果
- `git diff --check`：通过。
- `UV_PROJECT_ENVIRONMENT=/tmp/trendnews-compatible-uv uv sync --frozen --no-dev`：通过，使用 CPython 3.12.13。
- `UV_PROJECT_ENVIRONMENT=/tmp/trendnews-compatible-uv uv run --frozen python -m compileall -q trendradar mcp_server`：通过。
- `UV_PROJECT_ENVIRONMENT=/tmp/trendnews-compatible-uv uv run --frozen python -m trendradar --help`：通过。
- `UV_PROJECT_ENVIRONMENT=/tmp/trendnews-compatible-uv uv run --frozen python - <<'PY' ...`：通过，确认 `check_all_versions` 可导入、`DataFetcher(..., xuangutong_config={})` 可初始化、`tcc_custom` 在 2026-06-28 19:45:17 返回 `push=True` 与 `report_mode=daily`。
- `.github/workflows/*.yml` 使用 PyYAML 解析：通过。
- `rg` 检查 `requirements.txt`、`pip install -r`、Python 3.10、旧 `fetch_with_fallback` 断言、`name 're'`/`NamedTuple` 残留：未命中。

## 2026-06-29 追加修复：`domain_rules` 接口不兼容
- 用户反馈：Actions 运行到爬取阶段时报错 `DataFetcher.crawl_websites() got an unexpected keyword argument 'domain_rules'`。
- 根因：`trendradar/__main__.py` 已按上游新版传入 `domain_rules`，但为保留本地选股通扩展而恢复的 `trendradar/crawler/fetcher.py` 函数签名仍是旧版；同时域名安全校验依赖的 `urlparse` 导入也缺失。
- 修复：`DataFetcher.crawl_websites` 增加可选 `domain_rules` 参数并默认 `{}`，域名安全日志改用当前平台名；补入 `urlparse` 导入。
- 兼容修复：主程序构造抓取列表时，对 `driver != newsnow` 的平台保留完整配置 dict，避免选股通被压缩成 `(id, name)` 后丢失 driver；同时继续向抓取器传入 `crawl_date`。
- 验证：模拟 NewsNow 平台通过域名校验、模拟域名不匹配被拒绝、模拟选股通 driver 保留、模拟主程序 `_crawl_data` 传参、`compileall`、`python -m trendradar --help`、workflow YAML 解析均通过。

## 风险与不确定性
- 本修复未触发真实 GitHub Actions、未推送、未真实调用飞书 webhook。
- 当前 crawler workflow 仍只有 `workflow_dispatch`，不会自行定时；如需 GitHub 原生定时，需要单独恢复 `on.schedule`。
- 选股通为本地扩展，上游未包含；后续上游若大改抓取器仍需人工检查该扩展。
- 无迁移，直接替换。
