# 选股通全链路接入实施记录

日期：2026-03-30
状态：已实现并完成本地冒烟验证

## 目标

- 将 `xuangutong` 作为原生平台源接入项目。
- 覆盖抓取、增量、关键词分组、平台分组、AI 分析、MCP 查询、本地 SQLite、远程 R2/S3 整库同步兼容。
- 保持 RSS 语义与现有 RSS 链路不变。

## 关键决策

- 在 `platforms.sources` 注册 `xuangutong`，保证平台枚举、校验、手动触发抓取、`display_mode=platform` 等现有能力无需分叉。
- 新增顶层 `xuangutong` 配置段，承载 `live/jingxuan` 的页面 URL、详情抓取、限速与正文策略。
- 不把 `选股通` 塞入 `rss`，避免污染 RSS 语义。
- `live` 与 `jingxuan` 内部合并后统一落到公开平台 ID `xuangutong`。
- `summary` 字段存放摘要或正文，`content_type` 标记 `live/jingxuan/newsnow`。
- 旧版 `news` SQLite 库采用在线幂等补列迁移。

## 实现范围

- 配置：
  - `config/config.yaml`
  - `trendradar/core/loader.py`
- 抓取：
  - `trendradar/crawler/fetcher.py`
  - 多驱动分发：`newsnow` + `xuangutong`
  - `xuangutong` 支持 `live` 列表、`jingxuan` 列表、详情正文抓取、相对时间标准化
- 数据模型与存储：
  - `trendradar/storage/base.py`
  - `trendradar/storage/schema.sql`
  - `trendradar/storage/sqlite_mixin.py`
- 数据读取与分析：
  - `trendradar/core/data.py`
  - `trendradar/core/analyzer.py`
  - `trendradar/ai/analyzer.py`
- 主流程与 MCP：
  - `trendradar/__main__.py`
  - `mcp_server/services/parser_service.py`
  - `mcp_server/services/data_service.py`
  - `mcp_server/tools/data_query.py`
  - `mcp_server/tools/search_tools.py`
  - `mcp_server/tools/system.py`
  - `mcp_server/server.py`

## 迁移说明

- `news_items` 新增列：
  - `published_at TEXT DEFAULT ''`
  - `summary TEXT DEFAULT ''`
  - `content_type TEXT DEFAULT ''`
- 无独立迁移脚本，采用在线补列迁移。
- 结论：无迁移脚本，直接替换；运行时会自动补列。

## 验证结果

### 1. 语法与导入

- 执行：`python -m compileall trendradar mcp_server`
- 结果：通过

### 2. 真实抓取冒烟

- 使用原始 YAML 配置形态初始化 `DataFetcher(xuangutong_config=config['xuangutong'])`
- 抓取 `xuangutong`
- 结果：
  - 抓取成功
  - 返回平台：`xuangutong`
  - 样本条目数：41
  - 正文字段已写入 `summary`
  - `published_at` 已标准化为 `YYYY-MM-DD HH:MM:SS`

### 3. 存储与回读冒烟

- 将抓取结果转换为 `NewsData` 后保存至临时 SQLite
- 再调用 `get_latest_crawl_data()`、`DataService.get_latest_news(include_content=True)` 回读
- 结果：
  - `published_at`、`summary`、`content_type` 均可 round-trip
  - `xuangutong` 被当作普通平台源返回

### 4. 旧库迁移

- 人工创建不含新列的旧版 `news_items` 表
- 通过 `LocalStorageBackend._get_connection()` 触发初始化和补列
- 结果：
  - `published_at`
  - `summary`
  - `content_type`
  均自动补齐

### 5. 统一搜索命中正文

- 构造仅在 `summary` 中包含唯一标记的新闻
- 调用 `search_news_unified(query='XYZ123', search_mode='keyword', include_content=True)`
- 结果：可以命中，说明正文搜索链路已打通

## 已知说明

- `选股通` 页面存在相对时间文本，如“刚刚”“3 天前”；当前已在抓取器中标准化为时间字符串，避免排序和增量逻辑受影响。
- 默认通知与 HTML 仍以标题为主，没有自动展开正文，这是刻意保持现有输出长度和行为稳定。
- `summary` 主要用于 AI 分析与可选查询输出。

## 输入来源

- 本仓库源码
- 公开页面：
  - `https://xuangutong.com.cn/live`
  - `https://xuangutong.com.cn/jingxuan`

## 最后验证日期

- 2026-03-30
