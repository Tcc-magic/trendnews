# coding=utf-8
"""
数据获取器模块

支持两类数据源：
- NewsNow API 平台热榜
- 选股通网页源（live / jingxuan）
"""

import json
import random
import re
import time
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import requests


class _XuanGuTongListParser(HTMLParser):
    """解析选股通列表页。"""

    def __init__(self, page_type: str):
        super().__init__()
        self.page_type = page_type
        self.items: List[Dict[str, str]] = []
        self._li_depth = 0
        self._current_item: Optional[Dict[str, str]] = None
        self._capture_field: Optional[str] = None
        self._capture_href = ""
        self._capture_text: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "") or ""

        if tag == "li":
            self._li_depth += 1
            if self._li_depth == 1:
                self._current_item = {
                    "title": "",
                    "url": "",
                    "summary": "",
                    "time": "",
                }

        if self._li_depth == 0 or self._current_item is None:
            return

        if tag == "a":
            href = attrs_dict.get("href", "") or ""
            title = attrs_dict.get("title", "") or ""
            if href.startswith("/article/"):
                self._capture_field = "title"
                self._capture_href = href
                self._capture_text = []
                if title and not self._current_item["title"]:
                    self._current_item["title"] = self._clean_text(title)
                    self._current_item["url"] = href
        elif tag == "time" and "time_" in class_name:
            self._capture_field = "time"
            self._capture_text = []
        elif self.page_type == "live" and tag == "pre":
            self._capture_field = "summary"
            self._capture_text = []
        elif self.page_type == "jingxuan" and tag == "div" and "intro_" in class_name:
            self._capture_field = "summary"
            self._capture_text = []

    def handle_endtag(self, tag: str) -> None:
        if self._capture_field and tag in {"a", "time", "pre", "div"}:
            text = self._clean_text("".join(self._capture_text))
            if self._current_item is not None and text:
                if self._capture_field == "title":
                    self._current_item["title"] = self._current_item["title"] or text
                    self._current_item["url"] = self._current_item["url"] or self._capture_href
                elif self._capture_field == "summary":
                    self._current_item["summary"] = self._current_item["summary"] or text
                elif self._capture_field == "time":
                    self._current_item["time"] = self._current_item["time"] or text
            self._capture_field = None
            self._capture_href = ""
            self._capture_text = []

        if tag == "li" and self._li_depth > 0:
            if self._li_depth == 1 and self._current_item:
                if self._current_item.get("title") and self._current_item.get("url"):
                    self.items.append(self._current_item)
                self._current_item = None
            self._li_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_field is not None:
            self._capture_text.append(data)

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", unescape(text)).strip()


class _XuanGuTongArticleParser(HTMLParser):
    """解析选股通文章正文。"""

    def __init__(self):
        super().__init__()
        self._capture_depth = 0
        self._text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "") or ""
        if "article-content" in class_name:
            self._capture_depth = 1
            return
        if self._capture_depth > 0:
            self._capture_depth += 1
            if tag in {"p", "br", "li"}:
                self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._capture_depth > 0:
            self._capture_depth -= 1
            if tag in {"p", "div", "li"}:
                self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._capture_depth > 0:
            self._text_parts.append(data)

    def get_text(self) -> str:
        text = unescape("".join(self._text_parts))
        text = re.sub(r"\n\s*\n+", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()


class DataFetcher:
    """数据获取器。"""

    DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    XUANGUTONG_BASE_URL = "https://xuangutong.com.cn"

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        api_url: Optional[str] = None,
        xuangutong_config: Optional[Dict[str, Any]] = None,
    ):
        self.proxy_url = proxy_url
        self.api_url = api_url or self.DEFAULT_API_URL
        self.xuangutong_config = xuangutong_config or {}

    def _build_proxies(self, proxy_url: Optional[str] = None) -> Optional[Dict[str, str]]:
        real_proxy = proxy_url if proxy_url is not None else self.proxy_url
        if not real_proxy:
            return None
        return {"http": real_proxy, "https": real_proxy}

    def _normalize_platform(self, platform_info: Union[str, Tuple[str, str], Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(platform_info, dict):
            platform = dict(platform_info)
            platform.setdefault("id", "")
            platform.setdefault("name", platform.get("id", ""))
            platform.setdefault("driver", "newsnow")
            return platform
        if isinstance(platform_info, tuple):
            return {"id": platform_info[0], "name": platform_info[1], "driver": "newsnow"}
        return {"id": platform_info, "name": platform_info, "driver": "newsnow"}

    def fetch_data(
        self,
        platform_info: Union[str, Tuple[str, str], Dict[str, Any]],
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Tuple[Optional[str], str, str]:
        """抓取 NewsNow API 平台数据。"""
        platform = self._normalize_platform(platform_info)
        id_value = platform["id"]
        alias = platform["name"]
        url = f"{self.api_url}?id={id_value}&latest"

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url,
                    proxies=self._build_proxies(),
                    headers=self.DEFAULT_HEADERS,
                    timeout=10,
                )
                response.raise_for_status()

                data_text = response.text
                data_json = json.loads(data_text)
                status = data_json.get("status", "unknown")
                if status not in ["success", "cache"]:
                    raise ValueError(f"响应状态异常: {status}")

                status_info = "最新数据" if status == "success" else "缓存数据"
                print(f"获取 {id_value} 成功（{status_info}）")
                return data_text, id_value, alias
            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    print(f"请求 {id_value} 失败: {e}. {wait_time:.2f} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"请求 {id_value} 失败: {e}")
                    return None, id_value, alias

        return None, id_value, alias

    def _fetch_webpage(self, url: str, timeout: int, proxy_url: Optional[str] = None) -> str:
        response = requests.get(
            url,
            headers=self.DEFAULT_HEADERS,
            proxies=self._build_proxies(proxy_url),
            timeout=timeout,
        )
        response.raise_for_status()
        return response.text

    def _get_xuangutong_runtime_config(self) -> Dict[str, Any]:
        config = self.xuangutong_config or {}
        if "SOURCES" in config or "ENABLED" in config:
            sources = config.get("SOURCES", {})
            live = sources.get("LIVE", {
                "ENABLED": True,
                "URL": f"{self.XUANGUTONG_BASE_URL}/live",
                "MAX_ITEMS": 50,
            })
            jingxuan = sources.get("JINGXUAN", {
                "ENABLED": True,
                "URL": f"{self.XUANGUTONG_BASE_URL}/jingxuan",
                "MAX_ITEMS": 50,
            })
            return {
                "enabled": config.get("ENABLED", False),
                "request_interval": config.get("REQUEST_INTERVAL", 1500),
                "timeout": config.get("TIMEOUT", 15),
                "use_proxy": config.get("USE_PROXY", False),
                "proxy_url": config.get("PROXY_URL", ""),
                "detail_fetch": config.get("DETAIL_FETCH", True),
                "detail_timeout": config.get("DETAIL_TIMEOUT", 15),
                "summary_max_length": config.get("SUMMARY_MAX_LENGTH", 4000),
                "live": live,
                "jingxuan": jingxuan,
            }

        sources = config.get("sources", {})
        return {
            "enabled": config.get("enabled", False),
            "request_interval": config.get("request_interval", 1500),
            "timeout": config.get("timeout", 15),
            "use_proxy": config.get("use_proxy", False),
            "proxy_url": config.get("proxy_url", ""),
            "detail_fetch": config.get("detail_fetch", True),
            "detail_timeout": config.get("detail_timeout", 15),
            "summary_max_length": config.get("summary_max_length", 4000),
            "live": {
                "ENABLED": sources.get("live", {}).get("enabled", True),
                "URL": sources.get("live", {}).get("url", f"{self.XUANGUTONG_BASE_URL}/live"),
                "MAX_ITEMS": sources.get("live", {}).get("max_items", 50),
            },
            "jingxuan": {
                "ENABLED": sources.get("jingxuan", {}).get("enabled", True),
                "URL": sources.get("jingxuan", {}).get("url", f"{self.XUANGUTONG_BASE_URL}/jingxuan"),
                "MAX_ITEMS": sources.get("jingxuan", {}).get("max_items", 50),
            },
        }

    def _normalize_xuangutong_time(self, time_text: str, crawl_date: Optional[str]) -> str:
        text = re.sub(r"\s+", " ", time_text).strip()
        if not text:
            return ""
        base_time = datetime.now()
        if crawl_date:
            try:
                crawl_dt = datetime.strptime(crawl_date, "%Y-%m-%d")
                now_time = datetime.now()
                base_time = crawl_dt.replace(
                    hour=now_time.hour,
                    minute=now_time.minute,
                    second=now_time.second,
                    microsecond=0,
                )
            except ValueError:
                pass
        if text in {"刚刚", "刚才"}:
            return base_time.strftime("%Y-%m-%d %H:%M:%S")
        minute_match = re.fullmatch(r"(\d+)\s*分钟前", text)
        if minute_match:
            return (base_time - timedelta(minutes=int(minute_match.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
        hour_match = re.fullmatch(r"(\d+)\s*小时前", text)
        if hour_match:
            return (base_time - timedelta(hours=int(hour_match.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
        day_match = re.fullmatch(r"(\d+)\s*天前", text)
        if day_match:
            return (base_time - timedelta(days=int(day_match.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
        if text == "昨天":
            return (base_time - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        if crawl_date:
            for fmt in ("%H:%M", "%H:%M:%S"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    return f"{crawl_date} {parsed.strftime('%H:%M:%S')}"
                except ValueError:
                    continue
        return text

    def _parse_xuangutong_list(
        self,
        html_text: str,
        page_type: str,
        crawl_date: Optional[str],
        max_items: int,
    ) -> List[Dict[str, str]]:
        parser = _XuanGuTongListParser(page_type)
        parser.feed(html_text)
        parsed_items: List[Dict[str, str]] = []
        for item in parser.items:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            if not title or not url:
                continue
            parsed_items.append(
                {
                    "title": title,
                    "url": urljoin(self.XUANGUTONG_BASE_URL, url),
                    "summary": item.get("summary", "").strip(),
                    "published_at": self._normalize_xuangutong_time(item.get("time", ""), crawl_date),
                    "content_type": page_type,
                }
            )
            if len(parsed_items) >= max_items:
                break
        return parsed_items

    def _fetch_xuangutong_article(
        self,
        url: str,
        timeout: int,
        proxy_url: Optional[str],
        summary_max_length: int,
    ) -> str:
        try:
            html_text = self._fetch_webpage(url, timeout=timeout, proxy_url=proxy_url)
            parser = _XuanGuTongArticleParser()
            parser.feed(html_text)
            summary = parser.get_text()
            if summary_max_length > 0:
                summary = summary[:summary_max_length].strip()
            return summary
        except Exception as e:
            print(f"抓取选股通详情失败: {url} -> {e}")
            return ""

    def _summary_richness(self, item: Dict[str, str]) -> Tuple[int, int]:
        priority = {"jingxuan": 3, "live": 2}.get(item.get("content_type", ""), 1)
        return priority, len(item.get("summary", "") or "")

    def _merge_xuangutong_items(self, raw_items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        merged: Dict[str, Dict[str, str]] = {}
        for item in raw_items:
            key = item.get("url") or item.get("title")
            if key not in merged:
                merged[key] = dict(item)
                continue
            existing = merged[key]
            if self._summary_richness(item) > self._summary_richness(existing):
                existing["summary"] = item.get("summary", existing.get("summary", ""))
                existing["content_type"] = item.get("content_type", existing.get("content_type", ""))
                existing["title"] = item.get("title", existing.get("title", ""))
            if not existing.get("published_at") and item.get("published_at"):
                existing["published_at"] = item["published_at"]
            if not existing.get("url") and item.get("url"):
                existing["url"] = item["url"]

        merged_items = list(merged.values())

        def sort_key(item: Dict[str, str]) -> Tuple[int, str]:
            published_at = item.get("published_at", "")
            if published_at:
                try:
                    return (1, datetime.strptime(published_at, "%Y-%m-%d %H:%M:%S").isoformat())
                except ValueError:
                    return (1, published_at)
            return (0, "")

        merged_items.sort(key=sort_key, reverse=True)
        return merged_items

    def _crawl_xuangutong(
        self,
        platform: Dict[str, Any],
        crawl_date: Optional[str],
        request_interval: int,
    ) -> Tuple[Dict[str, Dict[str, Any]], str]:
        runtime = self._get_xuangutong_runtime_config()
        if not runtime["enabled"]:
            raise ValueError("选股通数据源未启用")

        proxy_url = runtime["proxy_url"] if runtime["use_proxy"] and runtime["proxy_url"] else self.proxy_url
        timeout = runtime["timeout"]
        detail_timeout = runtime["detail_timeout"]
        summary_max_length = runtime["summary_max_length"]
        raw_items: List[Dict[str, str]] = []

        for page_type, page_config in [("live", runtime["live"]), ("jingxuan", runtime["jingxuan"])]:
            if not page_config.get("ENABLED", True):
                continue
            html_text = self._fetch_webpage(page_config["URL"], timeout=timeout, proxy_url=proxy_url)
            raw_items.extend(
                self._parse_xuangutong_list(
                    html_text=html_text,
                    page_type=page_type,
                    crawl_date=crawl_date,
                    max_items=page_config.get("MAX_ITEMS", 50),
                )
            )
            time.sleep(max(request_interval, 50) / 1000)

        if runtime["detail_fetch"]:
            for item in raw_items:
                if item.get("content_type") != "jingxuan":
                    continue
                detail_summary = self._fetch_xuangutong_article(
                    url=item["url"],
                    timeout=detail_timeout,
                    proxy_url=proxy_url,
                    summary_max_length=summary_max_length,
                )
                if detail_summary and len(detail_summary) >= len(item.get("summary", "")):
                    item["summary"] = detail_summary
                time.sleep(max(request_interval, 50) / 1000)

        merged_items = self._merge_xuangutong_items(raw_items)
        results: Dict[str, Dict[str, Any]] = {platform["id"]: {}}
        for rank, item in enumerate(merged_items, 1):
            title = item.get("title", "").strip()
            if not title:
                continue
            results[platform["id"]][title] = {
                "ranks": [rank],
                "url": item.get("url", ""),
                "mobileUrl": item.get("url", ""),
                "publishedAt": item.get("published_at", ""),
                "summary": item.get("summary", ""),
                "contentType": item.get("content_type", ""),
            }

        return results, platform["name"]

    def crawl_websites(
        self,
        ids_list: List[Union[str, Tuple[str, str], Dict[str, Any]]],
        request_interval: int = 100,
        crawl_date: Optional[str] = None,
    ) -> Tuple[Dict, Dict, List]:
        """抓取多个网站数据。"""
        results: Dict[str, Dict[str, Any]] = {}
        id_to_name: Dict[str, str] = {}
        failed_ids: List[str] = []
        normalized_platforms = [self._normalize_platform(item) for item in ids_list]

        for index, platform in enumerate(normalized_platforms):
            id_value = platform["id"]
            id_to_name[id_value] = platform.get("name", id_value)
            driver = platform.get("driver", "newsnow") or "newsnow"

            try:
                if driver == "xuangutong":
                    platform_results, platform_name = self._crawl_xuangutong(
                        platform=platform,
                        crawl_date=crawl_date,
                        request_interval=request_interval,
                    )
                    results.update(platform_results)
                    id_to_name[id_value] = platform_name
                else:
                    response, _, alias = self.fetch_data(platform)
                    id_to_name[id_value] = alias
                    if not response:
                        failed_ids.append(id_value)
                        continue

                    data = json.loads(response)
                    results[id_value] = {}
                    for rank, item in enumerate(data.get("items", []), 1):
                        title = item.get("title")
                        if title is None or isinstance(title, float) or not str(title).strip():
                            continue
                        title = str(title).strip()
                        if title in results[id_value]:
                            results[id_value][title]["ranks"].append(rank)
                        else:
                            results[id_value][title] = {
                                "ranks": [rank],
                                "url": item.get("url", ""),
                                "mobileUrl": item.get("mobileUrl", ""),
                                "publishedAt": "",
                                "summary": "",
                                "contentType": "newsnow",
                            }
            except json.JSONDecodeError:
                print(f"解析 {id_value} 响应失败")
                failed_ids.append(id_value)
            except Exception as e:
                print(f"处理 {id_value} 数据出错: {e}")
                failed_ids.append(id_value)

            if index < len(normalized_platforms) - 1:
                actual_interval = request_interval + random.randint(-10, 20)
                actual_interval = max(50, actual_interval)
                time.sleep(actual_interval / 1000)

        print(f"成功: {list(results.keys())}, 失败: {failed_ids}")
        return results, id_to_name, failed_ids
