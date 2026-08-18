#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 4KPorno.XXX FongMi终极兼容版 v25

import sys
import os
import re
import json
import random
import time

# 兼容导入 urllib
try:
    import urllib.request
    import urllib.parse
    HAS_URLLIB = True
except:
    HAS_URLLIB = False

try:
    import ssl
    HAS_SSL = True
except:
    HAS_SSL = False

try:
    import gzip
    HAS_GZIP = True
except:
    HAS_GZIP = False

# 不用 html 模块，自己实现 unescape
HTML_ENTITIES = {
    "&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&nbsp;": " ", "&apos;": "'",
}

def _unescape(s):
    if not s:
        return ""
    try:
        for k, v in HTML_ENTITIES.items():
            s = s.replace(k, v)
        return s
    except:
        return s

def _clean(s):
    if not s:
        return ""
    s = _unescape(s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"

SITE = "https://www.4kporno.xxx"

class Spider:
    def __init__(self):
        pass

    def init(self, extend=""):
        return True

    def homeContent(self, filter):
        classes = []
        sorts = {
            "latest-updates": "\u6700\u65b0\u66f4\u65b0",
            "top-rated": "\u6700\u9ad8\u8bc4\u5206",
            "most-popular": "\u6700\u53d7\u6b22\u8fce",
        }
        cats = {
            "asian": "\u4e9a\u6d32\u7684", "big-ass": "\u5927\u5c41\u80a1", "big-tits": "\u5927\u5976",
            "blonde": "\u91d1\u53d1\u5973\u90ce", "blowjob": "\u53e3\u4ea4", "brunette": "\u9ed1\u53d1\u5973\u90ce",
            "creampie": "\u4f53\u5185\u5c04\u7cbe", "cumshot": "\u5c04\u7cbe", "anal": "\u809b\u95e8",
            "ebony": "\u4e4c\u6728\u8272", "gangbang": "Gangbang", "hardcore": "\u786c\u6838",
            "interracial": "\u8de8\u79cd\u65cf", "japanese": "\u65e5\u672c\u4eba", "korean": "\u97e9\u56fd\u4eba",
            "lesbian": "\u5973\u540c\u6027\u604b", "milf": "MILF", "pov": "POV",
            "redhead": "\u7ea2\u53d1\u5973\u90ce", "teen": "\u9752\u5c11\u5e74", "threesome": "\u4e09\u4eba\u884c",
        }
        sites = {
            "my-dirty-uncle": "My Dirty Uncle",
            "new-sensations": "New Sensations",
            "momswapped": "MomSwapped",
            "private": "Private",
        }
        for k, v in sorts.items():
            classes.append({"type_name": v, "type_id": "sort:" + k})
        for k, v in cats.items():
            classes.append({"type_name": v, "type_id": "cat:" + k})
        for k, v in sites.items():
            classes.append({"type_name": v, "type_id": "site:" + k})
        return {"class": classes}

    def _fetch(self, url, timeout=20):
        if not HAS_URLLIB:
            return ""
        try:
            headers = {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip",
                "Connection": "keep-alive",
            }
            req = urllib.request.Request(url, headers=headers, method="GET")
            if HAS_SSL:
                try:
                    ctx = ssl._create_unverified_context()
                except:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            else:
                resp = urllib.request.urlopen(req, timeout=timeout)
            data = resp.read()
            ce = resp.headers.get("Content-Encoding", "")
            if HAS_GZIP and "gzip" in ce:
                try:
                    data = gzip.decompress(data)
                except:
                    pass
            try:
                return data.decode("utf-8")
            except:
                return data.decode("utf-8", errors="replace")
        except Exception as e:
            return ""

    def _extract(self, html):
        videos = []
        seen = set()
        try:
            pat = re.compile(
                r'<div class="item">\s*<a href="(https?://[^"]+/videos/(\d+)/[^"]*/?)"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?</a>',
                re.S
            )
            for m in pat.finditer(html):
                full_url, vid, title, pic, alt = m.groups()
                if vid in seen:
                    continue
                seen.add(vid)
                path = full_url.replace(SITE, "")
                videos.append({
                    "vod_id": path,
                    "vod_name": _clean(title or alt),
                    "vod_pic": pic.replace("@2x", "%402x") if pic else "",
                    "vod_remarks": "",
                })
        except:
            pass
        return videos

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            if tid.startswith("sort:"):
                sid = tid.replace("sort:", "")
                if sid == "latest":
                    sid = "latest-updates"
                path = "/" + sid + "/" + str(page) + "/" if page > 1 else "/" + sid + "/"
            elif tid.startswith("search:"):
                kw = tid.replace("search:", "")
                kw = urllib.parse.quote(kw) if HAS_URLLIB else kw
                path = "/search/" + kw + "/" + str(page) + "/" if page > 1 else "/search/" + kw + "/"
            elif tid.startswith("cat:"):
                cid = tid.replace("cat:", "")
                path = "/categories/" + cid + "/" + str(page) + "/" if page > 1 else "/categories/" + cid + "/"
            elif tid.startswith("site:"):
                sid = tid.replace("site:", "")
                path = "/sites/" + sid + "/" + str(page) + "/" if page > 1 else "/sites/" + sid + "/"
            else:
                path = "/categories/" + tid + "/" + str(page) + "/" if page > 1 else "/categories/" + tid + "/"

            url = SITE + path if not path.startswith("http") else path
            html = self._fetch(url)
            videos = self._extract(html)

            # 如果提取为空，返回诊断信息
            if not videos:
                videos.append({
                    "vod_id": "diag",
                    "vod_name": "\u6682\u65e0\u5185\u5bb9 - \u7f51\u7edc\u6216\u89e3\u6790\u5f02\u5e38",
                    "vod_pic": "",
                    "vod_remarks": "",
                })

            has_next = len(videos) >= 20
            return {
                "list": videos,
                "page": page,
                "pagecount": 999 if has_next else page,
                "limit": len(videos),
                "total": 999 * len(videos) if has_next else page * len(videos),
            }
        except Exception as e:
            return {
                "list": [{"vod_id": "err", "vod_name": "\u9519\u8bef: " + str(e)[:50], "vod_pic": "", "vod_remarks": ""}],
                "page": 1, "pagecount": 1, "limit": 1, "total": 1,
            }

    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            if vid.startswith("/"):
                url = SITE + vid
            elif "/videos/" in vid:
                url = vid if vid.startswith("http") else SITE + vid
            else:
                url = SITE + "/videos/" + vid + "/"

            html = self._fetch(url)
            if not html:
                return {"list": []}

            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
            title = _clean(title_match.group(1)) if title_match else "\u672a\u77e5"

            pic_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.I)
            pic = pic_match.group(1) if pic_match else ""

            desc_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html, re.I)
            desc = desc_match.group(1) if desc_match else ""

            play_url = ""
            vb = re.search(r'<video[^>]*>.*?</video>', html, re.S | re.I)
            if vb:
                block = vb.group(0)
                sources = re.findall(r'<source[^>]*src=[\'"]([^\'"]*)[\'"][^>]*label=[\'"]([^\'"]*)[\'"]', block)
                if sources:
                    priority = ["2160p", "1080p", "720p", "480p", "360p"]
                    sources.sort(key=lambda x: priority.index(x[1]) if x[1] in priority else 99)
                    parts = []
                    for src, label in sources:
                        parts.append(label + "$" + src)
                    play_url = "#".join(parts)
                else:
                    mp4s = re.findall(r'https?://[^\s"\'<>]+\.mp4/?', html)
                    real = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
                    if real:
                        play_url = "\u6b63\u7247$" + real[0].rstrip("/")
            else:
                mp4s = re.findall(r'https?://[^\s"\'<>]+\.mp4/?', html)
                real = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
                if real:
                    play_url = "\u6b63\u7247$" + real[0].rstrip("/")

            if not play_url:
                play_url = "\u6b63\u7247$" + url

            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic.replace("@2x", "%402x") if pic else "",
                    "vod_content": desc,
                    "vod_play_from": "4KPorno",
                    "vod_play_url": play_url,
                }]
            }
        except:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
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
                real_url = SITE + real_url
            return {
                "parse": 0,
                "url": real_url,
                "header": json.dumps({
                    "Referer": SITE + "/",
                    "User-Agent": UA,
                }),
            }
        except:
            return {"parse": 1, "url": "", "header": ""}

    def searchContent(self, key, quick, pg="1"):
        try:
            return self.categoryContent(tid="search:" + key, pg=pg, filter=False, extend={})
        except:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def localProxy(self, param):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        return False


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
