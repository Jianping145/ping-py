#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4KPorno.XXX FongMi兼容版 v28
模仿 javfree.py 结构，继承 base.spider.Spider
"""

import sys
import re
import json

sys.path.append("..")
from base.spider import Spider


class _4KPorno(Spider):
    siteUrl = "https://www.4kporno.xxx"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"

    categories = [
        {"type_id": "sort:latest-updates", "type_name": "\u6700\u65b0\u66f4\u65b0"},
        {"type_id": "sort:top-rated", "type_name": "\u6700\u9ad8\u8bc4\u5206"},
        {"type_id": "sort:most-popular", "type_name": "\u6700\u53d7\u6b22\u8fce"},
        {"type_id": "cat:asian", "type_name": "\u4e9a\u6d32\u7684"},
        {"type_id": "cat:big-ass", "type_name": "\u5927\u5c41\u80a1"},
        {"type_id": "cat:big-tits", "type_name": "\u5927\u5976"},
        {"type_id": "cat:blonde", "type_name": "\u91d1\u53d1\u5973\u90ce"},
        {"type_id": "cat:blowjob", "type_name": "\u53e3\u4ea4"},
        {"type_id": "cat:brunette", "type_name": "\u9ed1\u53d1\u5973\u90ce"},
        {"type_id": "cat:creampie", "type_name": "\u4f53\u5185\u5c04\u7cbe"},
        {"type_id": "cat:cumshot", "type_name": "\u5c04\u7cbe"},
        {"type_id": "cat:anal", "type_name": "\u809b\u95e8"},
        {"type_id": "cat:japanese", "type_name": "\u65e5\u672c\u4eba"},
        {"type_id": "cat:korean", "type_name": "\u97e9\u56fd\u4eba"},
        {"type_id": "cat:lesbian", "type_name": "\u5973\u540c\u6027\u604b"},
        {"type_id": "cat:milf", "type_name": "MILF"},
        {"type_id": "cat:teen", "type_name": "\u9752\u5c11\u5e74"},
        {"type_id": "site:my-dirty-uncle", "type_name": "My Dirty Uncle"},
        {"type_id": "site:new-sensations", "type_name": "New Sensations"},
        {"type_id": "site:momswapped", "type_name": "MomSwapped"},
        {"type_id": "site:private", "type_name": "Private"},
    ]

    def __init__(self):
        self.session = None

    def getName(self):
        return "4KPorno"

    def init(self, extend=""):
        return True

    def isVideoFormat(self, url):
        return any(url.lower().endswith(x) for x in [".m3u8", ".mp4", ".ts"])

    def manualVideoCheck(self):
        return False

    def _fetch(self, url, headers=None):
        h = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }
        if headers:
            h.update(headers)
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            return ""

    def _clean(self, s):
        if not s:
            return ""
        try:
            s = s.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
            s = re.sub(r"<[^>]+>", "", s)
            return s.strip()
        except:
            return s

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
                path = full_url.replace(self.siteUrl, "")
                videos.append({
                    "vod_id": path,
                    "vod_name": self._clean(title or alt),
                    "vod_pic": pic.replace("@2x", "%402x") if pic else "",
                    "vod_remarks": "",
                })
        except:
            pass
        return videos

    def homeContent(self, filter):
        return {"class": self.categories}

    def homeVodContent(self):
        try:
            html = self._fetch(self.siteUrl + "/latest-updates/")
            videos = self._extract(html)
            return {"list": videos}
        except:
            return {"list": []}

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
                import urllib.parse
                kw = urllib.parse.quote(kw)
                path = "/search/" + kw + "/" + str(page) + "/" if page > 1 else "/search/" + kw + "/"
            elif tid.startswith("cat:"):
                cid = tid.replace("cat:", "")
                path = "/categories/" + cid + "/" + str(page) + "/" if page > 1 else "/categories/" + cid + "/"
            elif tid.startswith("site:"):
                sid = tid.replace("site:", "")
                path = "/sites/" + sid + "/" + str(page) + "/" if page > 1 else "/sites/" + sid + "/"
            else:
                path = "/categories/" + tid + "/" + str(page) + "/" if page > 1 else "/categories/" + tid + "/"

            url = self.siteUrl + path if not path.startswith("http") else path
            html = self._fetch(url)
            videos = self._extract(html)

            if not videos:
                videos.append({
                    "vod_id": "empty",
                    "vod_name": "\u6682\u65e0\u5185\u5bb9",
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
                url = self.siteUrl + vid
            elif "/videos/" in vid:
                url = vid if vid.startswith("http") else self.siteUrl + vid
            else:
                url = self.siteUrl + "/videos/" + vid + "/"

            html = self._fetch(url)
            if not html:
                return {"list": []}

            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
            title = self._clean(title_match.group(1)) if title_match else "\u672a\u77e5"

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
                real_url = self.siteUrl + real_url
            return {
                "parse": 0,
                "url": real_url,
                "header": json.dumps({
                    "Referer": self.siteUrl + "/",
                    "User-Agent": self.ua,
                }),
            }
        except:
            return {"parse": 1, "url": "", "header": ""}

    def searchContent(self, key, quick, pg="1"):
        try:
            return self.categoryContent(tid="search:" + key, pg=pg, filter=False, extend="")
        except:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def localProxy(self, param):
        return [200, "text/plain", ""]


class Spider(_4KPorno):
    pass
