#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4KPorno.XXX TVBox专用兼容版 -- v22
====================================
【v22 关键修复】
  - Accept-Encoding 去掉 br，避免 Brotli 压缩导致无 brotli 模块时乱码
  - 其余同 v21
====================================
"""

import sys
import os
import re
import json
import random
import html as html_module
import gzip
import ssl
import time
from urllib import parse, request

DEBUG = True


def _log(msg):
    try:
        print("[4KPorno] " + str(msg), file=sys.stderr, flush=True)
    except Exception:
        pass


_SSL_CTX = None

def _get_ssl_ctx():
    global _SSL_CTX
    if _SSL_CTX is None:
        _SSL_CTX = ssl.create_default_context()
        _SSL_CTX.check_hostname = False
        _SSL_CTX.verify_mode = ssl.CERT_NONE
    return _SSL_CTX


class BaseSpider:
    UA_POOL = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    ]

    def __init__(self, extend=""):
        self.extend = extend
        _log("BaseSpider init, extend=" + str(extend))

    @classmethod
    def _random_ua(cls):
        return random.choice(cls.UA_POOL)

    @classmethod
    def _build_headers(cls, extra=None):
        # v22 关键修复：去掉 br，避免 Brotli 压缩导致乱码
        h = {
            "User-Agent": cls._random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip",  # 只接受 gzip，不接受 br
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
        if extra:
            h.update(extra)
        return h

    def fetch(self, url, headers=None, timeout=20, retries=2):
        h = self._build_headers(headers)
        last_err = ""
        for attempt in range(retries + 1):
            try:
                req = request.Request(url, headers=h, method="GET")
                ctx = _get_ssl_ctx()
                with request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    data = resp.read()
                    ce = resp.headers.get("Content-Encoding", "")
                    if "gzip" in ce:
                        data = gzip.decompress(data)
                    # 不再处理 br，因为请求头已禁止服务器返回 br
                    charset = "utf-8"
                    ct = resp.headers.get("Content-Type", "")
                    m = re.search(r"charset=([\w-]+)", ct, re.I)
                    if m:
                        charset = m.group(1)
                    try:
                        text = data.decode(charset)
                    except UnicodeDecodeError:
                        text = data.decode("utf-8", errors="replace")
                    _log("fetch success: " + url[:60] + "... len=" + str(len(text)))
                    return text
            except Exception as e:
                last_err = str(e)
                _log("fetch attempt " + str(attempt + 1) + " failed: " + last_err)
                if attempt < retries:
                    time.sleep(1)
        _log("fetch final error for " + url[:60] + ": " + last_err)
        return ""

    def fetch_binary(self, url, headers=None, timeout=20):
        h = self._build_headers(headers)
        try:
            req = request.Request(url, headers=h, method="GET")
            ctx = _get_ssl_ctx()
            with request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
                ce = resp.headers.get("Content-Encoding", "")
                if "gzip" in ce:
                    data = gzip.decompress(data)
                ct = resp.headers.get("Content-Type", "application/octet-stream")
                return resp.status, ct, data
        except Exception as e:
            _log("fetch_binary error: " + str(e))
            return 404, "text/plain", b""

    @staticmethod
    def clean_title(title):
        try:
            t = html_module.unescape(title or "")
            t = re.sub(r"<[^>]+>", "", t)
            return t.strip()
        except Exception:
            return title or ""

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
        return [404, "text/plain", "Not Supported".encode("utf-8")]

    def init(self, extend=""):
        _log("init called with extend=" + str(extend))
        return True

    def isVideoFormat(self, url):
        fmt = [".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi", ".mov", ".webm"]
        return any(f in url.lower() for f in fmt)

    def manualVideoCheck(self):
        return False


class Spider(BaseSpider):
    realm_name = "4KPorno"
    realm_level = 1
    defense_level = 0

    siteUrl = "https://www.4kporno.xxx"
    lang = ""

    SORTS = {
        "latest-updates": "\u6700\u65b0\u66f4\u65b0",
        "top-rated": "\u6700\u9ad8\u8bc4\u5206",
        "most-popular": "\u6700\u53d7\u6b22\u8fce",
    }

    CATEGORIES = {
        "asian": "\u4e9a\u6d32\u7684", "big-ass": "\u5927\u5c41\u80a1", "big-tits": "\u5927\u5976",
        "blonde": "\u91d1\u53d1\u5973\u90ce", "blowjob": "\u53e3\u4ea4", "brunette": "\u9ed1\u53d1\u5973\u90ce",
        "creampie": "\u4f53\u5185\u5c04\u7cbe", "cumshot": "\u5c04\u7cbe", "anal": "\u809b\u95e8",
        "ebony": "\u4e4c\u6728\u8272", "gangbang": "Gangbang", "hardcore": "\u786c\u6838",
        "interracial": "\u8de8\u79cd\u65cf", "japanese": "\u65e5\u672c\u4eba", "korean": "\u97e9\u56fd\u4eba",
        "lesbian": "\u5973\u540c\u6027\u604b", "milf": "MILF", "pov": "POV",
        "redhead": "\u7ea2\u53d1\u5973\u90ce", "teen": "\u9752\u5c11\u5e74", "threesome": "\u4e09\u4eba\u884c",
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

    def __init__(self, extend=""):
        super().__init__(extend)
        _log("Spider initialized")

    def _extract_list(self, html):
        videos = []
        seen = set()
        try:
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
        except Exception as e:
            _log("_extract_list error: " + str(e))
        return videos

    def _build_url(self, path):
        if path.startswith("http"):
            return path
        return self.siteUrl + path

    def homeContent(self, filter=False):
        try:
            classes = []
            for sort_id, sort_name in self.SORTS.items():
                classes.append({"type_name": sort_name, "type_id": "sort:" + sort_id})
            for cat_id, cat_name in self.CATEGORIES.items():
                classes.append({"type_name": cat_name, "type_id": "cat:" + cat_id})
            for site_id, site_name in self.SITES.items():
                classes.append({"type_name": site_name, "type_id": "site:" + site_id})
            for net_id, net_name in self.NETWORKS.items():
                classes.append({"type_name": net_name, "type_id": "net:" + net_id})

            filters = {}
            for c in classes:
                filters[c["type_id"]] = []

            result = {"class": classes, "filters": filters}
            _log("homeContent return " + str(len(classes)) + " classes")
            return result
        except Exception as e:
            _log("homeContent error: " + str(e))
            return {"class": [], "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            _log("categoryContent tid=" + str(tid) + " pg=" + str(page))

            if tid.startswith("sort:"):
                sort_id = tid.replace("sort:", "")
                if sort_id == "latest":
                    sort_id = "latest-updates"
                path = "/" + sort_id + "/" + str(page) + "/" if page > 1 else "/" + sort_id + "/"
            elif tid.startswith("search:"):
                kw = tid.replace("search:", "")
                kw = parse.quote(kw)
                path = "/search/" + kw + "/" + str(page) + "/" if page > 1 else "/search/" + kw + "/"
            elif tid.startswith("cat:"):
                cat_id = tid.replace("cat:", "")
                path = "/categories/" + cat_id + "/" + str(page) + "/" if page > 1 else "/categories/" + cat_id + "/"
            elif tid.startswith("site:"):
                site_id = tid.replace("site:", "")
                path = "/sites/" + site_id + "/" + str(page) + "/" if page > 1 else "/sites/" + site_id + "/"
            elif tid.startswith("net:"):
                net_id = tid.replace("net:", "")
                path = "/networks/" + net_id + "/" + str(page) + "/" if page > 1 else "/networks/" + net_id + "/"
            else:
                path = "/categories/" + tid + "/" + str(page) + "/" if page > 1 else "/categories/" + tid + "/"

            url = self._build_url(path)
            html = self.fetch(url, timeout=20)
            videos = self._extract_list(html)

            if not videos and page > 1 and tid.startswith("cat:"):
                cat_id = tid.replace("cat:", "")
                path = "/categories/" + cat_id + "/latest-updates/" + str(page) + "/"
                html = self.fetch(self._build_url(path), timeout=20)
                videos = self._extract_list(html)

            has_next = len(videos) >= 20
            result = {
                "list": videos,
                "page": page,
                "pagecount": 999 if has_next else page,
                "limit": len(videos),
                "total": 999 * len(videos) if has_next else page * len(videos),
            }
            _log("categoryContent return " + str(len(videos)) + " videos")
            return result
        except Exception as e:
            _log("categoryContent error: " + str(e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            _log("detailContent vid=" + str(vid))

            if vid.startswith("/"):
                url = self._build_url(vid)
            elif "/videos/" in vid:
                url = vid if vid.startswith("http") else self._build_url(vid)
            else:
                url = self.siteUrl + "/videos/" + vid + "/"

            html = self.fetch(url, timeout=20)
            if not html:
                _log("detailContent html empty")
                return {"list": []}

            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
            title = self.clean_title(title_match.group(1)) if title_match else "\u672a\u77e5"

            pic_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.I)
            pic = pic_match.group(1) if pic_match else ""

            desc_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html, re.I)
            desc = desc_match.group(1) if desc_match else ""

            play_url = ""
            video_block = re.search(r'<video[^>]*>.*?</video>', html, re.S | re.I)
            if video_block:
                block = video_block.group(0)
                sources = re.findall(r'<source[^>]*src=[\'"]([^\'"]*)[\'"][^>]*label=[\'"]([^\'"]*)[\'"]', block)
                if sources:
                    priority = ["2160p", "1080p", "720p", "480p", "360p"]
                    sources.sort(key=lambda x: priority.index(x[1]) if x[1] in priority else 99)
                    play_parts = []
                    for src, label in sources:
                        play_parts.append(label + "$" + src)
                    play_url = "#".join(play_parts)
                else:
                    mp4s = re.findall(r'https?://[^\s"\'<>]+\.mp4/?', html)
                    real_mp4s = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
                    if real_mp4s:
                        play_url = "\u6b63\u7247$" + real_mp4s[0].rstrip("/")
            else:
                mp4s = re.findall(r'https?://[^\s"\'<>]+\.mp4/?', html)
                real_mp4s = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
                if real_mp4s:
                    play_url = "\u6b63\u7247$" + real_mp4s[0].rstrip("/")

            if not play_url:
                play_url = "\u6b63\u7247$" + url

            result = {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._proxy_pic_url(pic),
                    "vod_content": desc,
                    "vod_play_from": "4KPorno",
                    "vod_play_url": play_url,
                }]
            }
            _log("detailContent return title=" + title)
            return result
        except Exception as e:
            _log("detailContent error: " + str(e))
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            _log("playerContent flag=" + str(flag) + " id=" + (id[:60] if id else "empty"))
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

            result = {
                "parse": 0,
                "url": real_url,
                "header": json.dumps({
                    "Referer": self.siteUrl + "/",
                    "User-Agent": self._random_ua(),
                    "Accept": "*/*",
                    "Accept-Encoding": "identity",
                    "Connection": "keep-alive",
                }),
            }
            _log("playerContent return url=" + real_url[:60])
            return result
        except Exception as e:
            _log("playerContent error: " + str(e))
            return {"parse": 1, "url": "", "header": ""}

    def searchContent(self, key, quick, pg="1"):
        try:
            _log("searchContent key=" + str(key) + " pg=" + str(pg))
            return self.categoryContent(tid="search:" + key, pg=pg, filter=False, extend={})
        except Exception as e:
            _log("searchContent error: " + str(e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def localProxy(self, param):
        try:
            _log("localProxy param=" + str(param))
            return [404, "text/plain", "Not Supported".encode("utf-8")]
        except Exception as e:
            _log("localProxy error: " + str(e))
            return [404, "text/plain", b"error"]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="4KPorno.XXX TVBox兼容版 v22")
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
