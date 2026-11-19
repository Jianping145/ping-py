# -*- coding: utf-8 -*-
# JAVDAY https://javday.app  蜂蜜影视(FongMi) Spider

import re
import json
import time
from urllib import parse
from urllib.request import Request, urlopen
import ssl
import html as html_lib

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def __init__(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "JAVDAY"
        self.host = "https://javday.app"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://javday.app/",
        }
        self._ssl = None
        self.classes = [
            {"type_id": "label:new", "type_name": "最近更新"},
            {"type_id": "label:hot", "type_name": "人气系列"},
            {"type_id": "category:censored", "type_name": "有码"},
            {"type_id": "category:new-release", "type_name": "新作上市"},
            {"type_id": "category:uncensored-leaked", "type_name": "无修正流出"},
            {"type_id": "category:chinese-av", "type_name": "国产AV"},
            {"type_id": "category:aiav", "type_name": "AI短剧"},
            {"type_id": "category:hot-issue", "type_name": "热门事件"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        classes = list(self.classes)
        try:
            html = self.fetch(self.host + "/")
            known = {c["type_id"] for c in classes}
            for m in re.finditer(
                r'href="(?:https://javday\.app)?/(category|label)/([a-z0-9\-]+)/"[^>]*>([^<]+)',
                html or "",
            ):
                kind, slug, name = m.group(1), m.group(2), html_lib.unescape(m.group(3)).strip()
                if not name or slug in ("terms", "2257", "groups"):
                    continue
                tid = "%s:%s" % (kind, slug)
                if tid in known:
                    continue
                known.add(tid)
                classes.append({"type_id": tid, "type_name": name})
        except Exception as e:
            print("[javday] home:", e)
        self.classes = classes
        return {"class": classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            html = self.fetch(self.host + "/label/new/")
            return {"list": self._parse_list(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = str(tid or "label:new").strip()
        videos = []
        try:
            if ":" in tid:
                kind, slug = tid.split(":", 1)
            else:
                kind, slug = "label", tid
            if kind == "category":
                path = "/category/%s/" % slug
                if page > 1:
                    path = "/category/%s/page/%d/" % (slug, page)
            else:
                path = "/label/%s/" % slug
                if page > 1:
                    path = "/label/%s/page/%d/" % (slug, page)
            html = self.fetch(self.host + path)
            videos = self._parse_list(html)
        except Exception as e:
            print("[javday] category:", e)
        pagecount = page + 1 if len(videos) >= 20 else page
        # 有码等分类页码很大，尽量给足
        if len(videos) >= 20 and page < 50:
            pagecount = max(pagecount, page + 10)
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        raw = str(raw).strip()
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = self.host + "/videos/%s/" % raw.strip("/")
        try:
            html = self.fetch(url)
        except Exception as e:
            print("[javday] detail:", e)
            return {"list": []}
        if not html:
            return {"list": []}

        title = ""
        m = re.search(r"<title[^>]*>([^<]+)</title>", html)
        if m:
            title = html_lib.unescape(m.group(1)).replace(" - JAVDAY", "").strip()
        if not title:
            m = re.search(r'class="title"[^>]*>([^<]+)', html)
            if m:
                title = html_lib.unescape(m.group(1)).strip()
        title = title or "JAVDAY"

        pic = ""
        m = re.search(r'property="og:image" content="([^"]+)"', html)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'background-image:\s*url\(([^)]+)\)', html)
            if m:
                pic = m.group(1).strip().strip("'\"").strip()

        # 播放地址：
        #   Ep1~6$url#Ep7$url
        #   1$url#2$url#3$url
        #   单链 m3u8
        play_parts = []
        blob = ""
        for pat in [
            r"url\s*:\s*'([^']+?\.m3u8[^']*)'",
            r'url\s*:\s*"([^"]+?\.m3u8[^"]*)"',
        ]:
            m = re.search(pat, html)
            if m:
                blob = m.group(1).strip()
                break
        if not blob:
            m = re.search(
                r"((?:(?:Ep[\d~]+|\d+)\$https?://[^\"'\s#]+\.m3u8[^\"'\s#]*(?:#|$))+)",
                html,
            )
            if m:
                blob = m.group(1).strip()

        if blob and "$" in blob and ".m3u8" in blob:
            # Ep1~6 / Ep7 / 1 / 2 / 3 等
            eps = re.findall(
                r"((?:Ep[\d~]+|\d+))\s*\$\s*(https?://[^#\s'\"<>]+\.m3u8[^#\s'\"<>]*)",
                blob,
            )
            seen = set()
            for name, u in eps:
                u = re.sub(r"\?line=[^&]*", "", u).strip().rstrip("&")
                if not u or u in seen:
                    continue
                seen.add(u)
                # 纯数字显示为 第N集，更清晰
                if name.isdigit():
                    disp = "第%s集" % name
                else:
                    disp = name
                play_parts.append("%s$%s" % (disp, u))
        elif blob and ".m3u8" in blob:
            u = blob.split("#")[0].strip()
            if not u.startswith("http"):
                mm = re.search(r"(https?://\S+\.m3u8\S*)", u)
                u = mm.group(1).split("#")[0] if mm else ""
            u = re.sub(r"\?line=[^&]*", "", u).strip()
            if u.startswith("http"):
                play_parts.append("正片$%s" % u)

        if not play_parts:
            # 按钮 data-url
            btns = re.findall(
                r'data-url="(https?://[^"]+\.m3u8[^"]*)"[^>]*data-name="([^"]+)"',
                html,
            )
            if not btns:
                btns = re.findall(
                    r'data-name="([^"]+)"[^>]*data-url="(https?://[^"]+\.m3u8[^"]*)"',
                    html,
                )
                btns = [(u, n) for n, u in btns]
            seen = set()
            for u, name in btns:
                u = re.sub(r"\?line=[^&]*", "", u).strip()
                if not u or u in seen:
                    continue
                seen.add(u)
                disp = ("第%s集" % name) if str(name).isdigit() else str(name)
                play_parts.append("%s$%s" % (disp, u))

        if not play_parts:
            urls = re.findall(r"https?://[^\"'\s]+\.m3u8[^\"'\s]*", html)
            seen = set()
            for u in urls:
                u = re.sub(r"\?line=[^&]*", "", u.split("#")[0]).strip()
                if not u or u in seen:
                    continue
                seen.add(u)
                play_parts.append("正片$%s" % u)
                if len(play_parts) >= 5:
                    break
        if not play_parts:
            play_parts.append("正片$%s" % url)

        content = ""
        m = re.search(r'property="og:description" content="([^"]*)"', html)
        if m:
            content = html_lib.unescape(m.group(1))

        return {
            "list": [{
                "vod_id": url,
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_content": content[:500],
                "vod_remarks": "",
                "vod_year": "",
                "vod_area": "",
                "vod_actor": "",
                "vod_director": "",
                "type_name": "JAVDAY",
                "vod_play_from": "JAVDAY",
                "vod_play_url": "#".join(play_parts),
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
        }
        url = (id or "").strip()
        if not url:
            return {"parse": 1, "url": self.host, "header": json.dumps(headers)}
        if self.isVideoFormat(url) or url.startswith("http"):
            try:
                pu = parse.urlparse(url)
                headers["Referer"] = self.host + "/"
                headers["Origin"] = self.host
                if "javday.homes" in (pu.netloc or ""):
                    headers["Referer"] = self.host + "/"
            except Exception:
                pass
            return {
                "parse": 0,
                "jx": 0,
                "url": url,
                "header": json.dumps(headers),
            }
        return {"parse": 1, "jx": 0, "url": url, "header": json.dumps(headers)}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        key = str(key or "").strip()
        videos = []
        try:
            q = parse.quote(key)
            url = self.host + "/search/?wd=%s" % q
            if page > 1:
                url = self.host + "/search/page/%d/?wd=%s" % (page, q)
            html = self.fetch(url)
            videos = self._parse_list(html)
        except Exception as e:
            print("[javday] search:", e)
        pagecount = page + 1 if len(videos) >= 20 else page
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
        }

    def localProxy(self, param):
        try:
            url = param.get("url") if isinstance(param, dict) else str(param or "")
            for _ in range(2):
                if "%" in (url or "") and ("http%" in url.lower() or url.startswith("%")):
                    url = parse.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b"bad url"]
            body = self._fetch_bytes(url)
            if not body:
                return [500, "text/plain", b"empty"]
            ctype = "image/jpeg"
            if body[:8].startswith(b"\x89PNG"):
                ctype = "image/png"
            elif body[:4] == b"RIFF":
                ctype = "image/webp"
            elif body[:3] == b"GIF":
                ctype = "image/gif"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    # ---------- helpers ----------
    def _ssl_ctx(self):
        if self._ssl is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl = ctx
        return self._ssl

    def fetch(self, url):
        last = None
        for _ in range(2):
            try:
                req = Request(url, headers=self.headers)
                with urlopen(req, timeout=20, context=self._ssl_ctx()) as resp:
                    return resp.read().decode("utf-8", "ignore")
            except Exception as e:
                last = e
                time.sleep(0.2)
        print("[javday] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
            return resp.read() or b""

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        pic = html_lib.unescape(pic).strip().strip("'\"").strip()
        try:
            pu = parse.urlsplit(pic)
            path = parse.quote(pu.path, safe="/:@")
            pic = parse.urlunsplit((pu.scheme, pu.netloc, path, pu.query, pu.fragment))
        except Exception:
            pic = pic.replace(" ", "%20")
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    return "%s&url=%s" % (base, parse.quote(pic, safe=""))
        except Exception:
            pass
        return pic

    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()
        for m in re.finditer(
            r'<a href="(/videos/([A-Za-z0-9_-]+)/)" class="videoBox">([\s\S]*?)</a>',
            html,
        ):
            path, vid, block = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            title = ""
            tm = re.search(r'class="title"[^>]*>([^<]+)', block)
            if tm:
                title = html_lib.unescape(tm.group(1)).strip()
            if not title:
                title = vid
            pic = ""
            pm = re.search(r'background-image:\s*url\(([^)]+)\)', block)
            if pm:
                pic = pm.group(1).strip().strip("'\"").strip()
            remarks = ""
            vm = re.search(r'class="number"[^>]*>([^<]+)', block)
            if vm:
                remarks = vm.group(1).strip() + "播放"
            videos.append({
                "vod_id": self.host + path,
                "vod_name": title[:100],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": remarks[:40],
            })
            if len(videos) >= 48:
                break
        return videos
