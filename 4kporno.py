#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4KPorno.XXX 调试版 -- v23
==========================
带完整 TVBox 日志输出，用于定位加载失败原因
==========================
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

# 强制开启调试，输出到 stderr（TVBox 日志可见）
DEBUG = True

def _log(msg):
    try:
        sys.stderr.write("[4KPorno] " + str(msg) + "\n")
        sys.stderr.flush()
    except Exception as e:
        pass

_log("=== 4KPorno v23 模块加载 ===")
_log("Python版本: " + sys.version)
_log("当前工作目录: " + os.getcwd())

# SSL 上下文
_SSL_CTX = None
def _get_ssl_ctx():
    global _SSL_CTX
    if _SSL_CTX is None:
        try:
            _SSL_CTX = ssl.create_default_context()
            _SSL_CTX.check_hostname = False
            _SSL_CTX.verify_mode = ssl.CERT_NONE
            _log("SSL上下文创建成功")
        except Exception as e:
            _log("SSL上下文创建失败: " + str(e))
            _SSL_CTX = ssl._create_unverified_context()
    return _SSL_CTX

class BaseSpider:
    UA_POOL = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    ]

    def __init__(self, extend=""):
        _log("BaseSpider.__init__ 开始, extend=" + str(extend))
        self.extend = extend
        _log("BaseSpider.__init__ 完成")

    @classmethod
    def _random_ua(cls):
        return cls.UA_POOL[0]

    @classmethod
    def _build_headers(cls, extra=None):
        h = {
            "User-Agent": cls._random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if extra:
            h.update(extra)
        return h

    def fetch(self, url, headers=None, timeout=20, retries=2):
        _log("fetch开始: " + url[:80])
        h = self._build_headers(headers)
        last_err = ""
        for attempt in range(retries + 1):
            try:
                req = request.Request(url, headers=h, method="GET")
                ctx = _get_ssl_ctx()
                with request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    data = resp.read()
                    ce = resp.headers.get("Content-Encoding", "")
                    _log("fetch响应: status=" + str(resp.status) + " encoding=" + ce + " len=" + str(len(data)))
                    if "gzip" in ce:
                        data = gzip.decompress(data)
                        _log("gzip解压后: " + str(len(data)))
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        text = data.decode("utf-8", errors="replace")
                        _log("解码使用replace模式")
                    _log("fetch成功, html长度=" + str(len(text)))
                    # 检查关键标记
                    if "class=\"item\"" in text:
                        _log("HTML包含item标记")
                    else:
                        _log("HTML不包含item标记!")
                    if "<video" in text:
                        _log("HTML包含video标记")
                    return text
            except Exception as e:
                last_err = str(e)
                _log("fetch尝试" + str(attempt+1) + "失败: " + last_err)
                if attempt < retries:
                    time.sleep(1)
        _log("fetch最终失败: " + last_err)
        return ""

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

    def init(self, extend=""):
        _log("init()被调用, extend=" + str(extend))
        return True

    def isVideoFormat(self, url):
        fmt = [".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi", ".mov", ".webm"]
        return any(f in url.lower() for f in fmt)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [404, "text/plain", "Not Supported".encode("utf-8")]


class Spider(BaseSpider):
    realm_name = "4KPorno"
    siteUrl = "https://www.4kporno.xxx"

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

    def __init__(self, extend=""):
        _log("Spider.__init__ 开始")
        super().__init__(extend)
        _log("Spider.__init__ 完成")

    def _extract_list(self, html):
        _log("_extract_list开始, html长度=" + str(len(html)))
        videos = []
        seen = set()
        try:
            # 使用更宽松的正则
            pattern = re.compile(
                r'<div class="item">\s*<a href="(https?://[^"]+/videos/(\d+)/[^"]*/?)"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?</a>',
                re.S
            )
            matches = list(pattern.finditer(html))
            _log("正则匹配到 " + str(len(matches)) + " 个结果")
            for match in matches:
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
            _log("_extract_list异常: " + str(e))
        _log("_extract_list返回 " + str(len(videos)) + " 个视频")
        return videos

    def _build_url(self, path):
        if path.startswith("http"):
            return path
        return self.siteUrl + path

    def homeContent(self, filter=False):
        _log("homeContent()被调用")
        try:
            classes = []
            for sort_id, sort_name in self.SORTS.items():
                classes.append({"type_name": sort_name, "type_id": "sort:" + sort_id})
            for cat_id, cat_name in self.CATEGORIES.items():
                classes.append({"type_name": cat_name, "type_id": "cat:" + cat_id})
            for site_id, site_name in self.SITES.items():
                classes.append({"type_name": site_name, "type_id": "site:" + site_id})

            filters = {}
            for c in classes:
                filters[c["type_id"]] = []

            result = {"class": classes, "filters": filters}
            _log("homeContent返回 " + str(len(classes)) + " 个分类")
            return result
        except Exception as e:
            _log("homeContent异常: " + str(e))
            return {"class": [], "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        _log("categoryContent()被调用 tid=" + str(tid) + " pg=" + str(pg))
        try:
            page = int(pg) if str(pg).isdigit() else 1

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
            else:
                path = "/categories/" + tid + "/" + str(page) + "/" if page > 1 else "/categories/" + tid + "/"

            url = self._build_url(path)
            html = self.fetch(url, timeout=20)
            videos = self._extract_list(html)

            has_next = len(videos) >= 20
            result = {
                "list": videos,
                "page": page,
                "pagecount": 999 if has_next else page,
                "limit": len(videos),
                "total": 999 * len(videos) if has_next else page * len(videos),
            }
            _log("categoryContent返回 " + str(len(videos)) + " 个视频")
            return result
        except Exception as e:
            _log("categoryContent异常: " + str(e))
            import traceback
            _log(traceback.format_exc())
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def detailContent(self, ids):
        _log("detailContent()被调用 ids=" + str(ids))
        try:
            vid = ids[0] if isinstance(ids, list) else ids

            if vid.startswith("/"):
                url = self._build_url(vid)
            elif "/videos/" in vid:
                url = vid if vid.startswith("http") else self._build_url(vid)
            else:
                url = self.siteUrl + "/videos/" + vid + "/"

            html = self.fetch(url, timeout=20)
            if not html:
                _log("detailContent html为空")
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
            _log("detailContent返回: " + title)
            return result
        except Exception as e:
            _log("detailContent异常: " + str(e))
            import traceback
            _log(traceback.format_exc())
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        _log("playerContent()被调用")
        try:
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

            return {
                "parse": 0,
                "url": real_url,
                "header": json.dumps({
                    "Referer": self.siteUrl + "/",
                    "User-Agent": self._random_ua(),
                }),
            }
        except Exception as e:
            _log("playerContent异常: " + str(e))
            return {"parse": 1, "url": "", "header": ""}

    def searchContent(self, key, quick, pg="1"):
        _log("searchContent()被调用 key=" + str(key))
        try:
            return self.categoryContent(tid="search:" + key, pg=pg, filter=False, extend={})
        except Exception as e:
            _log("searchContent异常: " + str(e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", choices=["home", "category", "detail", "player", "search"])
    parser.add_argument("--id", default="/zh/videos/93817649/hotel-vixen-season-3-episode-2-unparalleled-customer-service/")
    parser.add_argument("--cat", default="sort:latest-updates")
    parser.add_argument("--kw", default="lesbian")
    args = parser.parse_args()

    spider = Spider()

    if args.test == "home" or not args.test:
        print(json.dumps(spider.homeContent(), ensure_ascii=False, indent=2))
    elif args.test == "category":
        print(json.dumps(spider.categoryContent(tid=args.cat, pg="1", filter=False, extend={}), ensure_ascii=False, indent=2))
    elif args.test == "detail":
        print(json.dumps(spider.detailContent([args.id]), ensure_ascii=False, indent=2))
    elif args.test == "player":
        detail = spider.detailContent([args.id])
        play_url = detail["list"][0]["vod_play_url"] if detail.get("list") else ""
        print(json.dumps(spider.playerContent(flag="4KPorno", id=play_url, vipFlags=""), ensure_ascii=False, indent=2))
    elif args.test == "search":
        print(json.dumps(spider.searchContent(key=args.kw, quick="1", pg="1"), ensure_ascii=False, indent=2))
