# -*- coding: utf-8 -*-
# Tube8 蜂蜜影视 Python Spider
# 列表: /newest.html  /cat/{slug}/  /cat/{slug}/2/
# 详情: /porn-video/{id}/
# 播放: mediaDefinition -> /media/hls/?s=... -> 真实 m3u8

import re
import json
import time
from urllib import parse
from urllib.request import Request, urlopen
import ssl

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def __init__(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "Tube8"
        self.host = "https://www.tube8.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.host + "/",
        }
        self._ssl = None
        self.classes = [
            {"type_id": "newest", "type_name": "最新"},
            {"type_id": "suggestions", "type_name": "推荐"},
            {"type_id": "mostviewed", "type_name": "最多观看"},
            {"type_id": "top", "type_name": "排行榜"},
            {"type_id": "longest", "type_name": "时长最长"},
            {"type_id": "country/sg/singapore", "type_name": "新加坡"},
            {"type_id": "cat/amateur", "type_name": "业余"},
            {"type_id": "cat/anal", "type_name": "肛交"},
            {"type_id": "cat/asian", "type_name": "亚洲"},
            {"type_id": "cat/japanese", "type_name": "日本"},
            {"type_id": "cat/latina", "type_name": "拉丁"},
            {"type_id": "cat/indian", "type_name": "印度"},
            {"type_id": "cat/arab", "type_name": "阿拉伯"},
            {"type_id": "cat/ebony", "type_name": "黑人"},
            {"type_id": "cat/brazilian", "type_name": "巴西"},
            {"type_id": "cat/french", "type_name": "法国"},
            {"type_id": "cat/german", "type_name": "德国"},
            {"type_id": "cat/blowjob", "type_name": "口交"},
            {"type_id": "cat/handjob", "type_name": "手交"},
            {"type_id": "cat/bigtits", "type_name": "巨乳"},
            {"type_id": "cat/bigass", "type_name": "大屁股"},
            {"type_id": "cat/bigdick", "type_name": "大鸡巴"},
            {"type_id": "cat/small-tits", "type_name": "贫乳"},
            {"type_id": "cat/blonde", "type_name": "金发"},
            {"type_id": "cat/brunette", "type_name": "棕发"},
            {"type_id": "cat/redhead", "type_name": "红发"},
            {"type_id": "cat/teens", "type_name": "青春"},
            {"type_id": "cat/milf", "type_name": "熟女MILF"},
            {"type_id": "cat/mature", "type_name": "熟女"},
            {"type_id": "cat/youngandold", "type_name": "老少配"},
            {"type_id": "cat/bbw", "type_name": "丰满"},
            {"type_id": "cat/lesbian", "type_name": "女同"},
            {"type_id": "cat/threesome", "type_name": "3P"},
            {"type_id": "cat/gangbang", "type_name": "轮流"},
            {"type_id": "cat/group", "type_name": "群交"},
            {"type_id": "cat/orgy", "type_name": "乱交"},
            {"type_id": "cat/doublepenetration", "type_name": "双插"},
            {"type_id": "cat/creampie", "type_name": "内射"},
            {"type_id": "cat/cumshot", "type_name": "颜射"},
            {"type_id": "cat/bukkake", "type_name": "多人口爆"},
            {"type_id": "cat/squirting", "type_name": "潮吹"},
            {"type_id": "cat/femaleorgasm", "type_name": "女高潮"},
            {"type_id": "cat/masturbation", "type_name": "自慰"},
            {"type_id": "cat/fingering", "type_name": "指交"},
            {"type_id": "cat/fisting", "type_name": "拳交"},
            {"type_id": "cat/pussy-licking", "type_name": "舔阴"},
            {"type_id": "cat/massage", "type_name": "按摩"},
            {"type_id": "cat/pov", "type_name": "第一视角"},
            {"type_id": "cat/public", "type_name": "公开"},
            {"type_id": "cat/reality", "type_name": "真实"},
            {"type_id": "cat/hardcore", "type_name": "重口"},
            {"type_id": "cat/rough", "type_name": "粗暴"},
            {"type_id": "cat/bondage", "type_name": "捆绑"},
            {"type_id": "cat/fetish", "type_name": "恋物"},
            {"type_id": "cat/feet", "type_name": "恋足"},
            {"type_id": "cat/pissing", "type_name": "排尿"},
            {"type_id": "cat/toys", "type_name": "玩具"},
            {"type_id": "cat/strip", "type_name": "脱衣"},
            {"type_id": "cat/striptease", "type_name": "脱衣舞"},
            {"type_id": "cat/casting", "type_name": "试镜"},
            {"type_id": "cat/college", "type_name": "大学"},
            {"type_id": "cat/cosplay", "type_name": "角色扮演"},
            {"type_id": "cat/cuckold", "type_name": "绿帽"},
            {"type_id": "cat/stepfantasy", "type_name": "继亲幻想"},
            {"type_id": "cat/compilation", "type_name": "合集"},
            {"type_id": "cat/parody", "type_name": "恶搞"},
            {"type_id": "cat/party", "type_name": "派对"},
            {"type_id": "cat/celebrity", "type_name": "名人"},
            {"type_id": "cat/cartoon", "type_name": "卡通"},
            {"type_id": "cat/hentai", "type_name": "动漫"},
            {"type_id": "cat/erotic", "type_name": "情色"},
            {"type_id": "cat/funny", "type_name": "搞笑"},
            {"type_id": "cat/hd", "type_name": "高清"},
            {"type_id": "cat/interracial", "type_name": "跨种族"},
            {"type_id": "cat/solomale", "type_name": "男solo"},
            {"type_id": "cat/transgender", "type_name": "跨性别"},
            {"type_id": "cat/verifiedamateurs", "type_name": "认证业余"},
            {"type_id": "cat/vintage", "type_name": "复古"},
            {"type_id": "cat/virtualreality", "type_name": "VR"},
            {"type_id": "cat/webcam", "type_name": "摄像头"},
            {"type_id": "cat/popular-with-women", "type_name": "女性向"},
            {"type_id": "pornstars", "type_name": "女优"},
            {"type_id": "top-channels", "type_name": "频道"},
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
            html = self.fetch(self.host + "/categories.html/")
            if not html:
                html = self.fetch(self.host + "/categories.html")
            extra = self._parse_categories(html)
            if extra:
                known = {c["type_id"] for c in self.classes}
                for e in extra:
                    if e["type_id"] not in known:
                        self.classes.append(e)
                        known.add(e["type_id"])
        except Exception as e:
            print("[t8] home:", e)
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/newest.html"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = (tid or "newest").strip("/")
        try:
            if tid in ("pornstars", "top-channels"):
                return self._folder_list(tid, page)
            if tid.startswith("pornstar/") or tid.startswith("channel/"):
                url = self._list_url(tid, page)
                html = self.fetch(url)
                videos = self._parse_list(html)
                return self._page_result(videos, page)

            url = self._list_url(tid, page)
            html = self.fetch(url)
            videos = self._parse_list(html)
            return self._page_result(videos, page)
        except Exception as e:
            print("[t8] category:", e)
            return {"list": [], "page": page, "pagecount": 1, "pageCount": 1, "limit": 36, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.rstrip("/").endswith(("pornstars", "top-channels", "categories.html")):
            return {"list": []}
        url = self._video_url(raw)
        try:
            html = self.fetch(url)
            if not html:
                return {"list": []}
            title = self._meta(html, "og:title") or self._tag_title(html) or "Tube8"
            pic = self._meta(html, "og:image") or ""
            sources = self._extract_sources(html)
            if not sources:
                sources = [("嗅探", url)]
            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": title[:120],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "Tube8",
                    "vod_play_url": "#".join("%s$%s" % (n, u) for n, u in sources),
                }]
            }
        except Exception as e:
            print("[t8] detail:", e)
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
        # media API token URL
        if "/media/hls/" in id or "/media/mp4/" in id:
            resolved = self._resolve_media(id)
            if resolved:
                return {"parse": 0, "jx": 0, "url": resolved, "header": hj}
        url = self._video_url(id)
        try:
            sources = self._extract_sources(self.fetch(url) or "")
            if sources:
                pick = sources[0][1]
                for n, u in sources:
                    if "1080" in n or "720" in n:
                        pick = u
                        break
                if not self.isVideoFormat(pick) and "/media/" in pick:
                    pick = self._resolve_media(pick) or pick
                return {"parse": 0 if self.isVideoFormat(pick) else 1, "jx": 0, "url": pick, "header": hj}
        except Exception as e:
            print("[t8] play:", e)
        return {"parse": 1, "jx": 0, "url": url, "header": hj}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        q = parse.quote_plus(str(key or "").strip())
        # /search.html?q=
        path = "/search.html?q=%s" % q
        if page > 1:
            path = "/search.html?q=%s&page=%d" % (q, page)
        # 备选
        html = self.fetch(self.host + path)
        videos = self._parse_list(html or "")
        if not videos:
            html = self.fetch(self.host + "/searches.html?q=%s" % q)
            videos = self._parse_list(html or "")
        return self._page_result(videos, page)

    def localProxy(self, param):
        try:
            url = param.get("url") if isinstance(param, dict) else str(param or "")
            for _ in range(3):
                if "%" in url:
                    url = parse.unquote(url)
            url = url.replace("&amp;", "&").strip()
            if not url.startswith("http"):
                return [400, "text/plain", b""]
            body = self._fetch_bytes(url)
            if not body or len(body) < 100:
                return [404, "text/plain", b""]
            ctype = "image/jpeg"
            if body[:8].startswith(b"\x89PNG"):
                ctype = "image/png"
            elif body[:3] == b"GIF":
                ctype = "image/gif"
            elif body[:4] == b"RIFF":
                ctype = "image/webp"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    def _ssl_ctx(self):
        if self._ssl is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl = ctx
        return self._ssl

    def fetch(self, url, retry=2):
        last = None
        for _ in range(retry):
            try:
                req = Request(url, headers=self.headers)
                with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
                    data = resp.read().decode("utf-8", "ignore")
                if data and len(data) > 500:
                    return data
            except Exception as e:
                last = e
                time.sleep(0.12)
        print("[t8] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
            return resp.read() or b""

    def _fetch_json(self, url):
        try:
            req = Request(url, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
                "Accept": "application/json,*/*",
            })
            with urlopen(req, timeout=15, context=self._ssl_ctx()) as resp:
                raw = resp.read().decode("utf-8", "ignore")
            if raw and raw.strip().startswith(("[", "{")):
                return json.loads(raw)
        except Exception as e:
            print("[t8] json:", e)
        return None

    def _list_url(self, tid, page=1):
        tid = (tid or "newest").strip("/")
        page = int(page or 1)
        # 固定列表页
        if tid in ("newest", "suggestions", "mostviewed", "top", "longest"):
            # mostviewed 第1页 mostviewed.html，第2页起 most-viewed/page/N/
            path_map = {
                "newest": ("/newest.html", "/newest/page/%d/"),
                "suggestions": ("/suggestions.html", "/suggestions/page/%d/"),
                "mostviewed": ("/mostviewed.html", "/most-viewed/page/%d/"),
                "top": ("/top.html", "/top/page/%d/"),
                "longest": ("/longest.html", "/longest/page/%d/"),
            }
            first, more = path_map[tid]
            if page <= 1:
                return self.host + first
            return self.host + (more % page)
        if tid.startswith("country/"):
            # /country/sg/singapore/  ?page=2
            base = "/" + tid.strip("/") + "/"
            if page <= 1:
                return self.host + base
            return self.host + base + "?page=%d" % page
        if tid.startswith("cat/"):
            slug = tid[4:].strip("/")
            # 分类分页：?page=2 （/cat/slug/2/ 会回首页）
            if page <= 1:
                return self.host + "/cat/%s/" % slug
            return self.host + "/cat/%s/?page=%d" % (slug, page)
        if tid.startswith("porntags/"):
            tag = tid.split("/", 1)[1]
            if page <= 1:
                return self.host + "/porntags/%s/" % tag
            return self.host + "/porntags/%s/?page=%d" % (tag, page)
        if tid.startswith("pornstar/") or tid.startswith("channel/"):
            base = self.host + "/" + tid.strip("/") + "/"
            if page <= 1:
                return base
            return base + "?page=%d" % page
        if page <= 1:
            return self.host + "/" + tid + "/"
        return self.host + "/%s/?page=%d" % (tid, page)

    def _video_url(self, raw):
        raw = str(raw or "").strip()
        if raw.startswith("http"):
            return raw
        if raw.startswith("/"):
            return self.host + raw
        if re.match(r"^\d+$", raw):
            return self.host + "/porn-video/%s/" % raw
        return self.host + "/" + raw.lstrip("/")

    def _page_result(self, videos, page):
        videos = videos or []
        # 有数据就继续允许上拉；无数据则停在当前页
        if videos:
            pagecount = max(page + 1, 999)
            total = 99999
        else:
            pagecount = page
            total = page * 36
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 36,
            "total": total,
        }

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        pic = pic.replace("&amp;", "&").strip()
        if pic.startswith("//"):
            pic = "https:" + pic
        if pic.startswith("data:"):
            return ""
        # 括号编码，避免客户端解析失败
        try:
            from urllib.parse import urlsplit, urlunsplit
            parts = urlsplit(pic)
            path = parts.path.replace("(", "%28").replace(")", "%29").replace(" ", "%20")
            pic = urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
        except Exception:
            pic = pic.replace("(", "%28").replace(")", "%29")
        # Tube8 列表常用 .mov/.mp4 + /plain/ 出图，扩展名不像图片，追加标记方便客户端识别
        low = pic.lower()
        if any(x in low for x in (".mov/", ".mp4/", "/plain/")) and not low.endswith((".jpg", ".jpeg", ".png", ".webp")):
            if "#" not in pic:
                pic = pic + "#.jpg"
        # 走本地代理，带 Referer 拉 CDN
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    # 去掉 fragment 再代理，# 对 query 不友好
                    real = pic.split("#", 1)[0]
                    return "%s&url=%s" % (base, parse.quote(real, safe=""))
        except Exception:
            pass
        return pic

    def _meta(self, html, prop):
        m = re.search(
            r'property=["\']%s["\'][^>]+content=["\']([^"\']+)' % re.escape(prop),
            html or "", re.I,
        )
        return m.group(1).strip() if m else ""

    def _tag_title(self, html):
        t = re.search(r"<title[^>]*>([^<]+)</title>", html or "", re.I)
        if not t:
            return ""
        return re.sub(r"\s*[-|].*$", "", t.group(1)).strip()

    def _parse_categories(self, html):
        out, seen = [], set()
        for m in re.finditer(r'href="(/cat/([a-z0-9\-]+)/)"', html or ""):
            path, slug = m.group(1), m.group(2)
            if slug in seen:
                continue
            seen.add(slug)
            win = (html or "")[m.start(): m.start() + 900]
            name = slug.replace("-", " ").title()
            nm = re.search(r'class="tm_category_title"\s*>\s*([^<\n]+)', win)
            if not nm:
                nm = re.search(r'alt="([^"]+)"', win)
            if nm:
                name = nm.group(1).strip()
            out.append({"type_id": "cat/" + slug, "type_name": name[:40]})
        return out


    def _folder_list(self, kind, page):
        page = int(page or 1)
        if kind == "pornstars":
            url = self.host + "/pornstars/" if page <= 1 else self.host + "/pornstars/?page=%d" % page
            prefix = "pornstar"
        else:
            url = self.host + "/top-channels/" if page <= 1 else self.host + "/top-channels/?page=%d" % page
            prefix = "channel"
        html = self.fetch(url)
        items, seen = [], set()
        for m in re.finditer(r'href="(/%s/([a-z0-9\-]+)/)"' % prefix, html or ""):
            path, slug = m.group(1), m.group(2)
            if slug in seen:
                continue
            # 频道 logo 可能在 href 后较远处
            win = (html or "")[m.start(): m.start() + 2800]
            pic = ""
            for pm in re.finditer(r'data-src="(https?://[^"]+)"', win):
                u = pm.group(1).replace("&amp;", "&").strip()
                if u.startswith("data:"):
                    continue
                if any(x in u for x in (".jpg", ".jpeg", ".png", ".webp")) or "t8cdn" in u or "phncdn" in u:
                    pic = u
                    break
            if not pic:
                pm = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', win)
                if pm:
                    pic = pm.group(1).replace("&amp;", "&")
            # 规范化双斜杠 CDN
            if pic:
                pic = re.sub(r"(https?://[^/]+)//+", r"\1/", pic)
            name = slug.replace("-", " ").title()
            nm = re.search(r'(?:alt|aria-label)="([^"]{2,80})"', win)
            if nm:
                name = nm.group(1)
                name = re.sub(r"^View\s+", "", name, flags=re.I)
                name = re.sub(r"\s+channel$", "", name, flags=re.I).strip() or name
            hn = re.search(r'class="channel-name"[^>]*>([^<]+)<', win)
            if hn:
                name = hn.group(1).strip()
            seen.add(slug)
            items.append({
                "vod_id": prefix + "/" + slug,
                "vod_name": name[:60],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "频道" if prefix == "channel" else "女优",
                "vod_tag": "folder",
            })
            if len(items) >= 80:
                break
        return self._page_result(items, page)


    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()
        for m in re.finditer(r'href="(/porn-video/(\d+)/)"', html):
            path, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            win = html[max(0, m.start() - 500): m.end() + 1000]
            title = ""
            for pat in [
                r'aria-label="([^"]{3,160})"',
                r'alt="([^"]{3,160})"',
                r'title="([^"]{3,160})"',
            ]:
                tm = re.search(pat, win)
                if tm:
                    title = tm.group(1).strip()
                    title = re.sub(r"&amp;", "&", title)
                    if title.lower().startswith("data:"):
                        continue
                    break
            pic = ""
            cands = []
            for pat in [
                r'data-src="(https?://[^"]+)"',
                r'data-mediumthumb="(https?://[^"]+)"',
                r'data-path="(https?://[^"]+)"',
                r'data-image="(https?://[^"]+)"',
                r'src="(https?://[^"]+)"',
            ]:
                for pm in re.finditer(pat, win, re.I):
                    u = pm.group(1).replace("&amp;", "&").strip()
                    if not u.startswith("http"):
                        continue
                    if u.startswith("data:") or any(x in u for x in ("logo", "icon", "sprite", "ads", "base64", "1x1", "blank")):
                        continue
                    cands.append(u)
            # 优先真实 jpg/png 缩略图，避开 .mov/plain 图片转换链
            def score(u):
                ul = u.lower()
                s = 0
                if any(x in ul for x in (".jpg", ".jpeg", ".png", ".webp")):
                    s += 50
                if "thumb" in ul:
                    s += 20
                if "t8cdn.com" in ul or "phncdn" in ul:
                    s += 10
                if ".mov" in ul or "/plain/" in ul:
                    s -= 40
                if "webm" in ul or ".mp4" in ul:
                    s -= 50
                return s
            cands.sort(key=score, reverse=True)
            pic = cands[0] if cands else ""
            videos.append({
                "vod_id": self.host + path,
                "vod_name": (title or ("Video " + vid))[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })
            if len(videos) >= 48:
                break
        return videos

    def _extract_sources(self, html):
        sources = []
        # mediaDefinition 中的 token URL
        m = re.search(r"mediaDefinition\s*:\s*(\[[\s\S]*?\])\s*,", html or "")
        if m:
            try:
                arr = json.loads(m.group(1).replace("\\/", "/"))
            except Exception:
                arr = []
            for item in arr if isinstance(arr, list) else []:
                if not isinstance(item, dict):
                    continue
                fmt = (item.get("format") or "").lower()
                u = item.get("videoUrl") or ""
                if not u:
                    continue
                u = u.replace("\\/", "/")
                label = fmt.upper() if fmt else "线路"
                # 解析 token API 拿真实地址
                if "/media/" in u:
                    resolved = self._resolve_media(u)
                    if resolved:
                        # resolve 可能返回多清晰度，这里取第一条；完整多清晰度在 _resolve_all
                        all_q = self._resolve_media_all(u)
                        if all_q:
                            sources.extend(all_q)
                            continue
                        sources.append((label, resolved))
                    else:
                        sources.append((label, u))
                elif self.isVideoFormat(u):
                    sources.append((label, u))

        # 直接 m3u8
        for u in re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html or ""):
            u = u.replace("\\/", "/").replace("&amp;", "&")
            if "timeline" in u or "thumb" in u:
                continue
            sources.append(("HLS", u))

        seen, out = set(), []
        for n, u in sources:
            if not u or u in seen:
                continue
            seen.add(u)
            out.append((n, u))
        # 排序：高清优先
        def rank(item):
            n = item[0].upper()
            for i, q in enumerate(["1080", "720", "480", "360", "240"]):
                if q in n:
                    return i
            if "HLS" in n:
                return 1
            return 50
        out.sort(key=rank)
        return out

    def _resolve_media(self, media_url):
        all_q = self._resolve_media_all(media_url)
        if all_q:
            return all_q[0][1]
        return ""

    def _resolve_media_all(self, media_url):
        """请求 /media/hls/?s=token 返回多清晰度 m3u8 列表。"""
        if not media_url:
            return []
        media_url = media_url.replace("\\/", "/").replace("&amp;", "&")
        data = self._fetch_json(media_url)
        out = []
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                u = (item.get("videoUrl") or "").replace("\\/", "/").replace("&amp;", "&")
                if not u or not u.startswith("http"):
                    continue
                q = str(item.get("quality") or item.get("height") or item.get("format") or "HLS")
                if str(q).isdigit():
                    q = q + "P"
                out.append((str(q).upper(), u))
        elif isinstance(data, dict):
            u = data.get("videoUrl") or data.get("url") or ""
            if u:
                out.append(("HLS", u.replace("\\/", "/")))
        return out
