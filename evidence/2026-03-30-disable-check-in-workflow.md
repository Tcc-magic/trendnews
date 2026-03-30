# 禁用 Check In 工作流机制记录

日期：2026-03-30
状态：已完成

## 目标

- 去除 `crawler.yml` 中的 7 天倒计时与自我禁用逻辑。
- 保留现有 `workflow_dispatch` 触发方式。
- 从 Actions 界面移除 `Check In` 续期入口。

## 实施内容

- 重写 `.github/workflows/crawler.yml`
  - 保留 `workflow_dispatch`
  - 删除 `Check Expiration` 步骤
  - 删除 `permissions.actions: write`
  - 保留原有抓取运行步骤与通知、AI、S3 相关环境变量
- 删除 `.github/workflows/clean-crawler.yml`

## 结果

- 后续通过 `workflow_dispatch` 或 Google Cloud 代调 `workflow_dispatch` 触发时，不再检查试用期。
- `crawler.yml` 不再拥有自我禁用 workflow 的权限。
- GitHub Actions 页面不再显示 `Check In` workflow。

## 迁移说明

- 无迁移，直接替换。

## 最后验证日期

- 2026-03-30
