#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4KPorno.XXX 爬虫源 —— v20 (TVBox 兼容修复版)
修复内容:
  - SSL 证书验证绕过（TVBox/Android 环境证书不完整）
  - playerContent header 改为字典格式
  - homeContent 返回完整格式
  - 增强错误处理和日志
  - fetch 添加重试机制
"""

import sys
import os
import re
import json
import random
import html as html_module
import gzip
import ssl
from urllib import parse, request

# 创建不验证证书的 SSL 上下文（TVBox/Android 必需）
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

DEBUG = os.environ.get("SPIDER_DEBUG", "0") == "1"


def _log(msg):
    if DEBUG:
        print(f"[4KPorno] {msg}", file=sys.stderr)


class BaseSpider:
    UA_POOL = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        pass

    @classmethod
    def _random_ua(cls):
        return random.choice(cls.UA_POOL)

    @classmethod
    def _build_headers(cls, extra=None):
        h = {
            "User-Agent": cls._random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        if extra:
            h.update(extra)
        return h

    def fetch(self, url, headers=None, timeout=20):
        """带重试的网络请求"""
        h = self._build_headers(headers)
        last_error = None

        for attempt in range(3):
            try:
                req = request.Request(url, headers=h, method="GET")
                # 使用不验证证书的 SSL 上下文
                with request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
                    data = resp.read()
                    ce = resp.headers.get("Content-Encoding", "")
                    if "gzip" in ce:
                        data = gzip.decompress(data)

                    charset = "utf-8"
                    ct = resp.headers.get("Content-Type", "")
                    m = re.search(r"charset=([\w-]+)", ct, re.I)
                    if m:
                        charset = m.group(1)
                    try:
                        text = data.decode(charset)
                    except UnicodeDecodeError:
                        text = data.decode("utf-8", errors="replace")

                    _log(f"fetch success: {url} (attempt {attempt + 1})")
                    return text

            except Exception as e:
                last_error = str(e)
                _log(f"fetch attempt {attempt + 1} failed: {url} - {last_error}")
                if attempt < 2:
                    import time
                    time.sleep(1)

        _log(f"fetch final failed: {url} - {last_error}")
        return ""

    @staticmethod
    def clean_title(title):
        if not title:
            return "未知"
        t = html_module.unescape(title)
        t = re.sub(r"<[^>]+>", "", t)
        return t.strip()

    @staticmethod
    def _proxy_pic_url(pic_url):
        if not pic_url:
            return ""
        return pic_url.replace("@2x", "%402x")

    def homeContent(self, filter=False):
        raise NotImplementedError

    def categoryContent(self, tid, pg, filter, extend):
        raise NotImplementedError

    def detailContent(self, ids):
        raise NotImplementedError

    def playerContent(self, flag, id, vipFlags):
        raise NotImplementedError

    def searchContent(self, key, quick, pg="1"):
        raise NotImplementedError

    def localProxy(self, param):
        return [404, "text/plain", "不支持本地代理"]

    def init(self, extend=""):
        return True

    def isVideoFormat(self, url):
        fmt = [".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi", ".mov", ".webm"]
        return any(f in url.lower() for f in fmt)

    def manualVideoCheck(self):
        return False


class Spider(BaseSpider):
    siteUrl = "https://www.4kporno.xxx"

    SORTS = {
        "latest-updates": "最新更新",
        "top-rated": "最高评分",
        "most-popular": "最受欢迎",
    }

    CATEGORIES = {
        "asian": "亚洲的", "big-ass": "大屁股", "big-tits": "大奶",
        "blonde": "金发女郎", "blowjob": "口交", "brunette": "黑发女郎",
        "creampie": "体内射精", "cumshot": "射精", "anal": "肛门",
        "ebony": "乌木色", "gangbang": "Gangbang", "hardcore": "硬核",
        "interracial": "跨种族", "japanese": "日本人", "korean": "韩国人",
        "lesbian": "女同性恋", "milf": "MILF", "pov": "POV",
        "redhead": "红发女郎", "teen": "青少年", "threesome": "三人行",
    }

    SITES = {
        "my-dirty-uncle": "My Dirty Uncle",
        "new-sensations": "New Sensations",
        "momswapped": "MomSwapped",
        "private": "Private",
    }

    NETWORKS = {}

    RE_ITEM = re.compile(
        r'<div class="item">\s*<a href="(https?://[^"]+/videos/(\d+)/[^"]*/?)"[^>]*title="([^"]*)"[^>]*>'
        r'.*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?</a>',
        re.S
    )

    def _extract_list(self, html):
        if not html:
            _log("_extract_list: empty html")
            return []
        videos = []
        seen = set()
        for match in self.RE_ITEM.finditer(html):
            full_url, vid, title, pic, alt = match.groups()
            if vid in seen:
                continue
            seen.add(vid)
            path = full_url.replace(self.siteUrl, "")
            videos.append({
                "vod_id": path,
                "vod_name": self.clean_title(title or alt),
                "vod_pic": self._proxy_pic_url(pic),
                "vod_remarks": "",
            })
        _log(f"_extract_list: found {len(videos)} videos")
        return videos

    def _build_url(self, path):
        if path.startswith("http"):
            return path
        return f"{self.siteUrl}{path}"

    def homeContent(self, filter=False):
        classes = []
        for sort_id, sort_name in self.SORTS.items():
            classes.append({"type_name": sort_name, "type_id": f"sort:{sort_id}"})
        for cat_id, cat_name in self.CATEGORIES.items():
            classes.append({"type_name": cat_name, "type_id": f"cat:{cat_id}"})
        for site_id, site_name in self.SITES.items():
            classes.append({"type_name": site_name, "type_id": f"site:{site_id}"})
        for net_id, net_name in self.NETWORKS.items():
            classes.append({"type_name": net_name, "type_id": f"net:{net_id}"})

        return {
            "class": classes,
            "filters": {},
            "list": [],
            "page": 1,
            "pagecount": 1,
            "limit": 0,
            "total": 0,
        }

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1
        _log(f"categoryContent: tid={tid}, page={page}")

        if tid.startswith("sort:"):
            sort_id = tid.replace("sort:", "")
            if sort_id == "latest":
                sort_id = "latest-updates"
            path = f"/{sort_id}/{page}/" if page > 1 else f"/{sort_id}/"
        elif tid.startswith("search:"):
            kw = tid.replace("search:", "")
            kw = parse.quote(kw)
            path = f"/search/{kw}/{page}/" if page > 1 else f"/search/{kw}/"
        elif tid.startswith("cat:"):
            cat_id = tid.replace("cat:", "")
            path = f"/categories/{cat_id}/{page}/" if page > 1 else f"/categories/{cat_id}/"
        elif tid.startswith("site:"):
            site_id = tid.replace("site:", "")
            path = f"/sites/{site_id}/{page}/" if page > 1 else f"/sites/{site_id}/"
        elif tid.startswith("net:"):
            net_id = tid.replace("net:", "")
            path = f"/networks/{net_id}/{page}/" if page > 1 else f"/networks/{net_id}/"
        else:
            path = f"/categories/{tid}/{page}/" if page > 1 else f"/categories/{tid}/"

        url = self._build_url(path)
        html = self.fetch(url, timeout=20)
        videos = self._extract_list(html)

        if not videos and page > 1 and tid.startswith("cat:"):
            cat_id = tid.replace("cat:", "")
            path = f"/categories/{cat_id}/latest-updates/{page}/"
            html = self.fetch(self._build_url(path), timeout=20)
            videos = self._extract_list(html)

        has_next = len(videos) >= 20
        return {
            "list": videos,
            "page": page,
            "pagecount": 999 if has_next else page,
            "limit": len(videos),
            "total": 999 * len(videos) if has_next else page * len(videos),
        }

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        if not vid:
            _log("detailContent: empty vid")
            return {"list": []}

        if vid.startswith("/"):
            url = self._build_url(vid)
        elif "/videos/" in vid:
            url = vid if vid.startswith("http") else self._build_url(vid)
        else:
            url = f"{self.siteUrl}/videos/{vid}/"

        _log(f"detailContent: url={url}")
        html = self.fetch(url, timeout=20)
        if not html:
            _log("detailContent: fetch failed")
            return {"list": []}

        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
        title = self.clean_title(title_match.group(1)) if title_match else "未知"

        pic_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.I)
        pic = pic_match.group(1) if pic_match else ""

        desc_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html, re.I)
        desc = desc_match.group(1) if desc_match else ""

        play_url = ""
        video_block = re.search(r'<video[^>]*>.*?</video>', html, re.S | re.I)
        if video_block:
            block = video_block.group(0)
            sources = re.findall(r'<source[^>]*src=['"]([^'"]*)['"][^>]*label=['"]([^'"]*)['"]', block)
            if sources:
                priority = ["2160p", "1080p", "720p", "480p", "360p"]
                sources.sort(key=lambda x: priority.index(x[1]) if x[1] in priority else 99)
                play_parts = []
                for src, label in sources:
                    play_parts.append(f"{label}${src}")
                play_url = "#".join(play_parts)
            else:
                mp4s = re.findall(r'https?://[^\s"'<>]+\.mp4/?', html)
                real_mp4s = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
                if real_mp4s:
                    play_url = f"正片${real_mp4s[0].rstrip('/')}"
        else:
            mp4s = re.findall(r'https?://[^\s"'<>]+\.mp4/?', html)
            real_mp4s = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
            if real_mp4s:
                play_url = f"正片${real_mp4s[0].rstrip('/')}"

        if not play_url:
            play_url = f"正片${url}"

        _log(f"detailContent: play_url={play_url[:100]}...")

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._proxy_pic_url(pic),
                "vod_content": desc,
                "vod_play_from": "4KPorno",
                "vod_play_url": play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "url": "", "header": ""}

        real_url = id
        if "$" in real_url:
            real_url = real_url.split("$")[1]
        if "#" in real_url:
            real_url = real_url.split("#")[0]
        if "$" in real_url:
            real_url = real_url.split("$")[1]

        if not real_url.startswith("http"):
            real_url = self._build_url(real_url)

        _log(f"playerContent: real_url={real_url[:100]}...")

        # 返回字典格式的 header（兼容性更好）
        return {
            "parse": 0,
            "url": real_url,
            "header": {
                "Referer": self.siteUrl + "/",
                "User-Agent": self._random_ua(),
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
            },
            "jx": 0,
        }

    def searchContent(self, key, quick, pg="1"):
        return self.categoryContent(tid=f"search:{key}", pg=pg, filter=False, extend={})

    def localProxy(self, param):
        return [404, "text/plain", "不支持本地代理"]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="4KPorno.XXX 爬虫源 v20")
    parser.add_argument("--test", choices=["home", "category", "detail", "player", "search"], help="测试接口")
    parser.add_argument("--id", default="/zh/videos/93817649/hotel-vixen-season-3-episode-2-unparalleled-customer-service/", help="视频路径")
    parser.add_argument("--cat", default="sort:latest-updates", help="分类ID")
    parser.add_argument("--kw", default="lesbian", help="搜索关键词")
    args = parser.parse_args()

    spider = Spider()

    if args.test == "home" or not args.test:
        result = spider.homeContent()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "category":
        result = spider.categoryContent(tid=args.cat, pg="1", filter=False, extend={})
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "detail":
        result = spider.detailContent([args.id])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "player":
        detail = spider.detailContent([args.id])
        play_url = detail["list"][0]["vod_play_url"] if detail.get("list") else ""
        result = spider.playerContent(flag="4KPorno", id=play_url, vipFlags="")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "search":
        result = spider.searchContent(key=args.kw, quick="1", pg="1")
        print(json.dumps(result, ensure_ascii=False, indent=2))
