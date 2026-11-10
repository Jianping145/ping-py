# -*- coding: utf-8 -*-
# xHamster (zh.xhamster02.com) 蜂蜜影视 Python Spider
# 列表: /newest /best /categories/{slug}
# 详情: /videos/{slug}
# 播放: 详情页 videoModel / initials 中的 hls / mp4

import re
import json
import time
from urllib import parse
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPSHandler
from http.cookiejar import CookieJar
import ssl

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def __init__(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "xHamster"
        self.hosts = [
            "https://zh.xhamster02.com",
            "https://zh.xhamster.com",
            "https://xhamster.com",
        ]
        self.host = self.hosts[0]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.host + "/",
        }
        self._ssl = None
        self._opener = None
        self.classes = [
            {"type_id": "newest", "type_name": "最新"},
            {"type_id": "best", "type_name": "最佳"},
            {"type_id": "4k", "type_name": "4K"},
            {"type_id": "hd", "type_name": "HD"},
            {"type_id": "vr", "type_name": "VR"},
            {"type_id": "categories", "type_name": "分类"},
            {"type_id": "channels", "type_name": "频道"},
            {"type_id": "pornstars", "type_name": "女优"},
            {"type_id": "categories/chinese", "type_name": "中文"},
            {"type_id": "categories/japanese", "type_name": "日本"},
            {"type_id": "categories/korean", "type_name": "韩国"},
            {"type_id": "categories/amateur", "type_name": "业余"},
            {"type_id": "categories/milf", "type_name": "熟女"},
            {"type_id": "categories/teen", "type_name": "青春"},
            {"type_id": "categories/lesbian", "type_name": "女同"},
            {"type_id": "categories/anal", "type_name": "肛交"},
            {"type_id": "categories/blowjob", "type_name": "口交"},
            {"type_id": "categories/creampie", "type_name": "内射"},
            {"type_id": "categories/hardcore", "type_name": "重口"},
            {"type_id": "categories/massage", "type_name": "按摩"},
            {"type_id": "categories/public", "type_name": "公开"},
            {"type_id": "categories/squirt", "type_name": "潮吹"},
            {"type_id": "categories/threesome", "type_name": "3P"},
            {"type_id": "categories/asian", "type_name": "亚洲"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        try:
            html = self.fetch(self.host + "/categories")
            extra = self._parse_categories(html)
            if extra:
                known = {c["type_id"] for c in self.classes}
                for e in extra:
                    if e["type_id"] not in known:
                        self.classes.append(e)
                        known.add(e["type_id"])
        except Exception as e:
            print("[xh] home:", e)
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self._list_url("newest", 1)))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = (tid or "newest").strip("/")
        try:
            if tid in ("categories", "channels", "pornstars", "tags"):
                return self._folder_list(tid, page)

            html = self.fetch(self._list_url(tid, page))
            videos = self._parse_list(html)
            # 频道/女优子页
            if not videos and ("/" in tid):
                html = self.fetch(self._list_url(tid, page))
                videos = self._parse_list(html)
            pagecount = 9999 if videos else page
            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "pageCount": pagecount,
                "limit": 36,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print("[xh] category:", e)
            return {"list": [], "page": page, "pagecount": 1, "pageCount": 1, "limit": 36, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.rstrip("/").endswith(("categories", "channels", "pornstars", "tags")):
            return {"list": []}
        url = self._video_url(raw)
        try:
            html = self.fetch(url)
            if not html:
                return {"list": []}
            info = self._parse_detail(html, url)
            sources = info.get("sources") or []
            lines = ["%s$%s" % (n, u) for n, u in sources]
            if not lines:
                lines = ["嗅探$%s" % url]
            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": info.get("title") or self._slug_title(url),
                    "vod_pic": self._proxy_pic(info.get("pic") or ""),
                    "vod_content": info.get("title") or "",
                    "vod_remarks": info.get("duration") or "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": info.get("actors") or "",
                    "vod_director": "",
                    "type_name": info.get("tags") or "",
                    "vod_play_from": "xHamster",
                    "vod_play_url": "#".join(lines),
                }]
            }
        except Exception as e:
            print("[xh] detail:", e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
        }
        hj = json.dumps(headers)
        if not id:
            return {"parse": 1, "url": self.host, "header": hj}
        if self.isVideoFormat(id):
            return {"parse": 0, "jx": 0, "url": id, "header": hj}
        url = self._video_url(id)
        try:
            info = self._parse_detail(self.fetch(url) or "", url)
            sources = info.get("sources") or []
            if sources:
                # 优先 hls / 高清
                pick = sources[0][1]
                for n, u in sources:
                    if "hls" in n.lower() or "1080" in n or "720" in n:
                        pick = u
                        break
                return {"parse": 0, "jx": 0, "url": pick, "header": hj}
        except Exception as e:
            print("[xh] play:", e)
        return {"parse": 1, "jx": 0, "url": url, "header": hj}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        q = parse.quote(str(key or "").strip())
        # /search/{q}?page=
        path = "/search/%s" % q
        if page > 1:
            path += "?page=%s" % page
        # 备选 /search?q=
        html = self.fetch(self.host + path)
        videos = self._parse_list(html or "")
        if not videos:
            html = self.fetch(self.host + "/search?q=%s&page=%s" % (q, page))
            videos = self._parse_list(html or "")
        return {
            "list": videos,
            "page": page,
            "pagecount": 9999 if videos else page,
            "pageCount": 9999 if videos else page,
            "limit": 36,
            "total": 999999 if videos else 0,
        }

    def localProxy(self, param):
        try:
            url = param.get("url") if isinstance(param, dict) else str(param or "")
            for _ in range(2):
                if "%" in url:
                    url = parse.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b""]
            body = self._fetch_bytes(url)
            ctype = "image/jpeg"
            if body[:8].startswith(b"\x89PNG"):
                ctype = "image/png"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    # ---------- network ----------
    def _ssl_ctx(self):
        if self._ssl is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl = ctx
        return self._ssl

    def _get_opener(self):
        if self._opener is None:
            cj = CookieJar()
            self._opener = build_opener(
                HTTPCookieProcessor(cj),
                HTTPSHandler(context=self._ssl_ctx()),
            )
        return self._opener

    def fetch(self, url, retry=2):
        last = None
        hosts_try = [url]
        # 若主站失败，替换 host 重试
        for alt in self.hosts:
            if url.startswith(self.host):
                hosts_try.append(url.replace(self.host, alt, 1))
        seen = set()
        for u in hosts_try:
            if u in seen:
                continue
            seen.add(u)
            for _ in range(retry):
                try:
                    hdr = dict(self.headers)
                    hdr["Referer"] = self.host + "/"
                    # 年龄确认 cookies
                    hdr["Cookie"] = "age_verified=1; cookie_accept=1; cookie_accept_v2=%7B%22e%22%3A1%2C%22f%22%3A1%2C%22t%22%3A1%2C%22a%22%3A1%7D; parental-control=yes"
                    req = Request(u, headers=hdr)
                    with self._get_opener().open(req, timeout=18) as resp:
                        data = resp.read().decode("utf-8", "ignore")
                        final = resp.geturl()
                    if data and len(data) > 800:
                        # 更新可用 host
                        for h in self.hosts:
                            if final.startswith(h):
                                self.host = h
                                break
                        return data
                except Exception as e:
                    last = e
                    time.sleep(0.12)
        print("[xh] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        with self._get_opener().open(req, timeout=18) as resp:
            return resp.read() or b""

    def _list_url(self, tid, page=1):
        tid = (tid or "newest").strip("/")
        page = int(page or 1)
        # 标准分页: /newest/2  /best/2  /categories/xxx/2  /4k/2
        if tid in ("newest", "best", "hd", "4k", "vr"):
            path = "/%s" % tid if page <= 1 else "/%s/%d" % (tid, page)
        elif tid.startswith("categories/") or tid.startswith("channels/") or tid.startswith("pornstars/") or tid.startswith("tags/"):
            path = "/%s" % tid if page <= 1 else "/%s/%d" % (tid, page)
        else:
            path = "/%s" % tid if page <= 1 else "/%s/%d" % (tid, page)
        return self.host + path

    def _video_url(self, raw):
        raw = str(raw or "").strip()
        if raw.startswith("http"):
            return raw
        if raw.startswith("/"):
            return self.host + raw
        if "videos/" not in raw:
            return self.host + "/videos/" + raw.lstrip("/")
        return self.host + "/" + raw.lstrip("/")

    def _slug_title(self, url):
        m = re.search(r"/videos/([^/?#]+)", url or "")
        if not m:
            return url
        return parse.unquote(m.group(1)).replace("-", " ")[:80]

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    return "%s&url=%s" % (base, parse.quote(pic))
        except Exception:
            pass
        return pic

    def _parse_categories(self, html):
        out, seen = [], set()
        for m in re.finditer(
            r'href="(?:https?://[^"]+)?(/categories/([a-z0-9\-]+))"[^>]*>([^<]{1,40})<',
            html or "",
            re.I,
        ):
            path, slug, name = m.group(1), m.group(2), re.sub(r"\s+", " ", m.group(3)).strip()
            if not name or slug in seen or slug in ("all",):
                continue
            seen.add(slug)
            out.append({"type_id": "categories/" + slug, "type_name": name[:40]})
            if len(out) >= 80:
                break
        return out

    def _folder_list(self, kind, page):
        html = self.fetch(self._list_url(kind, page))
        items, seen = [], set()

        # ---- JSON: 女优 ----
        if kind == "pornstars":
            for m in re.finditer(r'"type"\s*:\s*"pornstar"', html or ""):
                win = (html or "")[max(0, m.start() - 500): m.end() + 700]
                pm = re.search(r'"pageURL"\s*:\s*"([^"]+)"', win)
                if not pm:
                    continue
                page_url = pm.group(1).replace("\\/", "/")
                if "pornstars" not in page_url:
                    continue
                slug = page_url.rstrip("/").split("/")[-1]
                if not slug or slug in seen:
                    continue
                name = ""
                nm = re.search(r'"name"\s*:\s*"((?:\\.|[^"\\])*)"', win)
                if nm:
                    name = nm.group(1)
                    try:
                        if "\\u" in name:
                            name = name.encode("utf-8").decode("unicode_escape")
                    except Exception:
                        pass
                pic = ""
                for key in ("imageThumbUrl", "logoThumbUrl"):
                    im = re.search(r'"%s"\s*:\s*"([^"]+)"' % key, win)
                    if im:
                        pic = im.group(1).replace("\\/", "/")
                        break
                seen.add(slug)
                items.append({
                    "vod_id": "pornstars/" + slug,
                    "vod_name": (name or slug.replace("-", " "))[:60],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "女优",
                    "vod_tag": "folder",
                })

        # ---- JSON: 频道 ----
        if kind == "channels":
            for m in re.finditer(r'"channelURL"\s*:\s*"([^"]+)"', html or ""):
                page_url = m.group(1).replace("\\/", "/")
                if "/channels/" not in page_url and "channels\\/" not in m.group(1):
                    if "channels" not in page_url:
                        continue
                slug = page_url.rstrip("/").split("/")[-1]
                if not slug or slug in seen or slug in ("all",):
                    continue
                win = (html or "")[max(0, m.start() - 300): m.end() + 900]
                name = ""
                nm = re.search(r'"channelName"\s*:\s*"((?:\\.|[^"\\])*)"', win)
                if nm:
                    name = nm.group(1)
                    try:
                        if "\\u" in name:
                            name = name.encode("utf-8").decode("unicode_escape")
                    except Exception:
                        pass
                pic = ""
                im = re.search(r'"thumbURL"\s*:\s*"([^"]+)"', win)
                if im:
                    pic = im.group(1).replace("\\/", "/")
                if not pic:
                    im = re.search(r'"siteLogoURL"\s*:\s*"([^"]+)"', win)
                    if im:
                        pic = im.group(1).replace("\\/", "/")
                seen.add(slug)
                items.append({
                    "vod_id": "channels/" + slug,
                    "vod_name": (name or slug.replace("-", " "))[:60],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "频道",
                    "vod_tag": "folder",
                })

        # ---- 分类：HTML 卡片 + img ----
        if kind == "categories":
            for m in re.finditer(
                r'href="((?:https?://[^"]+)?/categories/([a-z0-9\-]+))"',
                html or "",
                re.I,
            ):
                path, slug = m.group(1), m.group(2)
                if slug in seen or slug in ("all", "rated", "newest"):
                    continue
                win = (html or "")[max(0, m.start() - 400): m.end() + 500]
                pic = ""
                for pat in [
                    r'src="(https?://ic-[^"]+\.xhcdn\.com/[^"]+)"',
                    r'src="(https?://[^"]*xhcdn\.com/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                ]:
                    im = re.search(pat, win, re.I)
                    if im:
                        pic = im.group(1)
                        if any(x in pic.lower() for x in ("logo", "icon", "flag", "avatar", "sprite")):
                            continue
                        break
                # 无图的导航项跳过（只要有图的分类卡片）
                if not pic:
                    continue
                name = slug.replace("-", " ")
                for pat in [r'alt="([^"]{2,60})"', r'title="([^"]{2,60})"', r'>([A-Za-z0-9\u4e00-\u9fff][^<]{1,40})<']:
                    nm = re.search(pat, win)
                    if nm:
                        name = nm.group(1).strip()
                        break
                seen.add(slug)
                items.append({
                    "vod_id": "categories/" + slug,
                    "vod_name": name[:60],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "分类",
                    "vod_tag": "folder",
                })
                if len(items) >= 120:
                    break

        # ---- 通用 HTML 兜底 ----
        if not items:
            pat = r'href="(?:https?://[^"]+)?(/%s/([a-z0-9\-\._%%]+))"' % kind
            for m in re.finditer(pat, html or "", re.I):
                path, slug = m.group(1), m.group(2)
                if slug in seen or slug.isdigit() or slug in ("all", "rated", "newest"):
                    continue
                seen.add(slug)
                win = (html or "")[max(0, m.start() - 400): m.end() + 600]
                name = parse.unquote(slug).replace("-", " ")
                nm = re.search(r'(?:title|alt)="([^"]{2,80})"', win)
                if nm:
                    name = nm.group(1)
                pic = ""
                pm = re.search(
                    r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    win,
                    re.I,
                )
                if pm:
                    pic = pm.group(1)
                items.append({
                    "vod_id": path.lstrip("/"),
                    "vod_name": name[:60],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": kind,
                    "vod_tag": "folder",
                })
                if len(items) >= 100:
                    break

        return {
            "list": items,
            "page": page,
            "pagecount": 999 if items else page,
            "pageCount": 999 if items else page,
            "limit": 40,
            "total": 9999,
        }

    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()

        # 1) 优先从页面 JSON 提取（thumbURL 齐全）
        for item in self._extract_video_items_json(html):
            page = item.get("pageURL") or item.get("link") or ""
            title = item.get("title") or item.get("name") or ""
            pic = (
                item.get("thumbURL")
                or item.get("imageURL")
                or item.get("previewThumbURL")
                or item.get("spriteURL")
                or ""
            )
            if not page or not isinstance(page, str):
                continue
            if "/videos/" not in page:
                continue
            slug = page.rstrip("/").split("/")[-1].split("?")[0]
            if not slug or slug in seen or slug in ("esea", "recommended"):
                continue
            seen.add(slug)
            url = page if page.startswith("http") else (self.host + page)
            if isinstance(pic, str) and pic.startswith("//"):
                pic = "https:" + pic
            # 转义 \/
            if isinstance(pic, str):
                pic = pic.replace("\\/", "/")
            dur = item.get("duration") or item.get("durationText") or ""
            if isinstance(dur, (int, float)) and dur > 0:
                m, s = divmod(int(dur), 60)
                remarks = "%d:%02d" % (m, s)
            else:
                remarks = str(dur) if dur else ""
            videos.append({
                "vod_id": url.replace("\\/", "/"),
                "vod_name": str(title)[:120] if title else slug.replace("-", " "),
                "vod_pic": self._proxy_pic(str(pic) if pic else ""),
                "vod_remarks": remarks,
            })

        # 2) HTML 卡片兜底
        if len(videos) < 8:
            for m in re.finditer(
                r'href="((?:https?://[^"]+)?/videos/([a-zA-Z0-9\-]{6,}))"',
                html,
                re.I,
            ):
                path, slug = m.group(1), m.group(2)
                if slug in seen or slug in ("esea", "recommended"):
                    continue
                seen.add(slug)
                win = html[max(0, m.start() - 800): m.end() + 1000]
                title = ""
                for pat in [r'aria-label="([^"]{2,160})"', r'alt="([^"]{2,160})"', r'title="([^"]{2,160})"']:
                    tm = re.search(pat, win)
                    if tm:
                        title = tm.group(1).strip()
                        break
                pic = self._pick_thumb(win)
                url = path if path.startswith("http") else (self.host + path)
                videos.append({
                    "vod_id": url,
                    "vod_name": (title or slug.replace("-", " "))[:120],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "",
                })
                if len(videos) >= 60:
                    break
        return videos

    def _extract_video_items_json(self, html):
        """从内嵌 JSON 收集 pageURL + thumbURL。"""
        items = []
        if not html:
            return items
        seen = set()
        for m in re.finditer(r'"pageURL"\s*:\s*"([^"]+)"', html):
            page = m.group(1).replace("\\/", "/")
            if "/videos/" not in page:
                continue
            slug = page.rstrip("/").split("/")[-1].split("?")[0]
            if not slug or slug in seen:
                continue
            win = html[max(0, m.start() - 500): m.end() + 1200]
            title = ""
            tm = re.search(r'"title"\s*:\s*"((?:\\.|[^"\\])*)"', win)
            if tm:
                title = tm.group(1).replace("\\/", "/").replace('\\"', '"')
                try:
                    if "\\u" in title:
                        title = title.encode("utf-8").decode("unicode_escape")
                except Exception:
                    pass
            pic = ""
            for key in ("thumbURL", "imageURL", "previewThumbURL"):
                im = re.search(r'"%s"\s*:\s*"([^"]+)"' % key, win)
                if im:
                    pic = im.group(1).replace("\\/", "/")
                    break
            dur = 0
            dm = re.search(r'"duration"\s*:\s*(\d+)', win)
            if dm:
                try:
                    dur = int(dm.group(1))
                except Exception:
                    dur = 0
            seen.add(slug)
            items.append({
                "pageURL": page,
                "title": title,
                "thumbURL": pic,
                "duration": dur,
            })
        return items

    def _pick_thumb(self, html_chunk):
        if not html_chunk:
            return ""
        for pat in [
            r'class="[^"]*thumb-image-container__image[^"]*"[^>]+src="(https?://[^"]+)"',
            r'src="(https?://ic-[^"]+\.xhcdn\.com/[^"]+)"',
            r'src="(https?://[^"]*xhcdn\.com/[^"]+\.(?:webp|jpg|jpeg|png)[^"]*)"',
            r'srcset="(https?://[^"]*xhcdn\.com/[^"\s,]+)',
            r'(?:data-src|src)="(https?://[^"]+\.(?:webp|jpg|jpeg|png)[^"]*)"',
        ]:
            m = re.search(pat, html_chunk, re.I)
            if not m:
                continue
            pic = m.group(1).strip().replace("\\/", "/")
            if any(x in pic.lower() for x in ("logo", "avatar", "icon", "sprite", "promo/message", "flag")):
                continue
            if pic.startswith("//"):
                pic = "https:" + pic
            return pic
        return ""

    def _parse_list_json(self, html, seen):
        out = []
        for item in self._extract_video_items_json(html):
            page = item.get("pageURL") or ""
            if not page:
                continue
            slug = str(page).rstrip("/").split("/")[-1]
            if slug in seen:
                continue
            seen.add(slug)
            pic = item.get("thumbURL") or item.get("imageURL") or ""
            out.append({
                "vod_id": str(page).replace("\\/", "/"),
                "vod_name": str(item.get("title") or slug)[:120],
                "vod_pic": self._proxy_pic(str(pic).replace("\\/", "/")),
                "vod_remarks": "",
            })
        return out

    def _walk_videos(self, obj, acc=None):
        if acc is None:
            acc = []
        if isinstance(obj, dict):
            if ("pageURL" in obj or "link" in obj) and ("title" in obj or "thumbURL" in obj):
                acc.append(obj)
            for v in obj.values():
                self._walk_videos(v, acc)
        elif isinstance(obj, list):
            for v in obj:
                self._walk_videos(v, acc)
        return acc

    def _safe_json(self, text):
        try:
            return json.loads(text)
        except Exception:
            pass
        # 截到最后一个完整 }
        for i in range(len(text), max(0, len(text) - 5000), -1):
            try:
                return json.loads(text[:i])
            except Exception:
                continue
        return None

    def _parse_detail(self, html, url=""):
        info = {"title": "", "pic": "", "duration": "", "actors": "", "tags": "", "sources": []}
        m = re.search(r'property="og:title"\s+content="([^"]+)"', html or "")
        if m:
            info["title"] = m.group(1)
        m = re.search(r'property="og:image"\s+content="([^"]+)"', html or "")
        if m:
            info["pic"] = m.group(1)

        # ---- 从 videoModel / sources 取完整片源（排除预览短片）----
        # HLS
        for m in re.finditer(r'https?:\\?/\\?/(video[^"\\]*xhcdn\.com[^"\\]+\.m3u8[^"\\]*)', html or ""):
            u = ("https://" + m.group(1)).replace("\\/", "/")
            if "thumb-" in u:
                continue
            info["sources"].append(("HLS", u))
        for m in re.finditer(r'"(https://video[^"]+\.m3u8[^"]*)"', html or ""):
            u = m.group(1).replace("\\/", "/")
            if "thumb-" in u:
                continue
            info["sources"].append(("HLS", u))

        # MP4 清晰度：sources.mp4."720p":"url"
        for m in re.finditer(
            r'"(144p|240p|360p|480p|720p|1080p|2160p)"\s*:\s*"(https:[^"]+\.mp4[^"]*)"',
            html or "",
            re.I,
        ):
            quality, u = m.group(1), m.group(2).replace("\\/", "/")
            # 过滤预览/缩略图 CDN
            if any(x in u for x in ("thumb-", "trailer", "preview", ".t.mp4", ".t.av1", "sprite")):
                continue
            if "xhcdn.com" not in u and "xhamster" not in u:
                continue
            info["sources"].append((quality.upper(), u))

        # 无结构化时再扫全页 mp4，但仍排除 thumb 预览
        if len([s for s in info["sources"] if s[0] != "HLS"]) == 0:
            for m in re.finditer(r'(https://video[^"\\]+\.mp4[^"\\]*)', html or ""):
                u = m.group(1).replace("\\/", "/")
                if any(x in u for x in ("thumb-", "trailer", "preview", ".t.mp4", ".t.av1")):
                    continue
                label = "MP4"
                for q in ("2160p", "1080p", "720p", "480p", "360p", "240p", "144p"):
                    if q in u:
                        label = q.upper()
                        break
                info["sources"].append((label, u))

        # title from videoModel
        if not info["title"]:
            m = re.search(r'"title"\s*:\s*"((?:\\.|[^"\\])*)"', html or "")
            if m:
                title = m.group(1).replace("\\/", "/")
                try:
                    if "\\u" in title:
                        title = title.encode("utf-8").decode("unicode_escape")
                except Exception:
                    pass
                info["title"] = title

        # 去重 + 排序：HLS 优先，然后按清晰度
        order = {"HLS": 0, "2160P": 1, "1080P": 2, "720P": 3, "480P": 4, "360P": 5, "240P": 6, "144P": 7, "MP4": 8}
        seen, out = set(), []
        for n, u in info["sources"]:
            if not u or u in seen:
                continue
            seen.add(u)
            out.append((n, u))
        out.sort(key=lambda x: order.get(x[0].upper(), 50))
        info["sources"] = out
        return info
