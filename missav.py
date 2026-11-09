# -*- coding: utf-8 -*-
# MissAV 蜂蜜影视 Spider（分类对齐官网真实路径）
# 入口: https://www.missav09.com/dm247/cn

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
        self.name = "MissAV"
        self.host = "https://www.missav09.com"
        self.lang = "cn"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.cdn = "https://spic2-147.vcwinford.cc"
        self._ssl = None
        # 官网真实路径（含 dm 前缀）
        # 部分栏目必须带 dm 前缀，裸 /cn/xxx 会跳到空页
        self.classes = [
            {"type_id": "dm539/cn/new", "type_name": "最近更新"},
            {"type_id": "dm635/cn/release", "type_name": "新作上市"},
            {"type_id": "dm817/cn/uncensored-leak", "type_name": "无码流出"},
            {"type_id": "cn/actresses", "type_name": "女优一览"},
            {"type_id": "cn/actresses/ranking", "type_name": "女优排行"},
            {"type_id": "cn/genres", "type_name": "类型"},
            {"type_id": "cn/makers", "type_name": "发行商"},
            {"type_id": "cn/genres/VR", "type_name": "VR"},
            {"type_id": "dm301/cn/today-hot", "type_name": "今日热门"},
            {"type_id": "dm170/cn/weekly-hot", "type_name": "本周热门"},
            {"type_id": "dm273/cn/monthly-hot", "type_name": "本月热门"},
            {"type_id": "dm36/cn/siro", "type_name": "素人·SIRO"},
            {"type_id": "dm34/cn/luxu", "type_name": "素人·LUXU"},
            {"type_id": "dm35/cn/gana", "type_name": "素人·GANA"},
            {"type_id": "dm1004/cn/maan", "type_name": "素人·PRESTIGE"},
            {"type_id": "dm38/cn/scute", "type_name": "素人·S-CUTE"},
            {"type_id": "dm34/cn/ara", "type_name": "素人·ARA"},
            {"type_id": "dm597/cn/fc2", "type_name": "无码·FC2"},
            {"type_id": "dm2020563/cn/heyzo", "type_name": "无码·HEYZO"},
            {"type_id": "dm42/cn/tokyohot", "type_name": "无码·东京热"},
            {"type_id": "dm4551182/cn/1pondo", "type_name": "无码·一本道"},
            {"type_id": "dm6840813/cn/caribbeancom", "type_name": "无码·Caribbeancom"},
            {"type_id": "dm78420/cn/caribbeancompr", "type_name": "无码·Caribbeancompr"},
            {"type_id": "dm6238706/cn/10musume", "type_name": "无码·10musume"},
            {"type_id": "dm3240472/cn/pacopacomama", "type_name": "无码·pacopacomama"},
            {"type_id": "dm150/cn/gachinco", "type_name": "无码·Gachinco"},
            {"type_id": "dm42/cn/xxxav", "type_name": "无码·XXX-AV"},
            {"type_id": "dm37/cn/marriedslash", "type_name": "无码·人妻斩"},
            {"type_id": "dm33/cn/naughty4610", "type_name": "无码·顽皮4610"},
            {"type_id": "dm37/cn/naughty0930", "type_name": "无码·顽皮0930"},
            {"type_id": "dm278/cn/chinese-subtitle", "type_name": "中文字幕"},
        ]
        # 无 dm 时的兜底映射
        self.dm_map = {
            "cn/new": "dm539/cn/new",
            "cn/release": "dm635/cn/release",
            "cn/uncensored-leak": "dm817/cn/uncensored-leak",
            "cn/today-hot": "dm301/cn/today-hot",
            "cn/weekly-hot": "dm170/cn/weekly-hot",
            "cn/monthly-hot": "dm273/cn/monthly-hot",
            "cn/siro": "dm36/cn/siro",
            "cn/luxu": "dm34/cn/luxu",
            "cn/gana": "dm35/cn/gana",
            "cn/maan": "dm1004/cn/maan",
            "cn/scute": "dm38/cn/scute",
            "cn/ara": "dm34/cn/ara",
            "cn/fc2": "dm597/cn/fc2",
            "cn/heyzo": "dm2020563/cn/heyzo",
            "cn/tokyohot": "dm42/cn/tokyohot",
            "cn/1pondo": "dm4551182/cn/1pondo",
            "cn/caribbeancom": "dm6840813/cn/caribbeancom",
            "cn/caribbeancompr": "dm78420/cn/caribbeancompr",
            "cn/10musume": "dm6238706/cn/10musume",
            "cn/pacopacomama": "dm3240472/cn/pacopacomama",
            "cn/gachinco": "dm150/cn/gachinco",
            "cn/xxxav": "dm42/cn/xxxav",
            "cn/marriedslash": "dm37/cn/marriedslash",
            "cn/naughty4610": "dm33/cn/naughty4610",
            "cn/naughty0930": "dm37/cn/naughty0930",
            "cn/chinese-subtitle": "dm278/cn/chinese-subtitle",
        }

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self._url("cn/new")))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = (tid or "dm539/cn/new").strip("/")
        # 兼容旧 type_id（无 dm 前缀）
        if hasattr(self, "dm_map") and tid in self.dm_map:
            tid = self.dm_map[tid]
        try:
            # 女优总览 / 排行 → 女优文件夹
            if tid in ("cn/actresses", "cn/actresses/ranking"):
                return self._actress_folder(tid, page)
            # 类型、发行商总览 → 分类文件夹
            if tid == "cn/genres":
                return self._link_folder("genres", page)
            if tid == "cn/makers":
                return self._link_folder("makers", page)

            # 点进某个女优 / 厂商 / 类型 → 该页作品网格
            # 例: cn/actresses/瀬户环奈  cn/makers/S1  cn/genres/人妻
            html = self.fetch(self._url(tid, page))
            videos = self._parse_list(html)
            if not videos:
                # 裸路径空页时，尝试 dm247 前缀
                slug = tid
                if slug.startswith("cn/"):
                    alt = "dm247/" + slug
                    html = self.fetch(self._url(alt, page))
                    videos = self._parse_list(html)
                if not videos and slug.startswith("cn/") and hasattr(self, "dm_map"):
                    mapped = self.dm_map.get(slug)
                    if mapped:
                        html = self.fetch(self._url(mapped, page))
                        videos = self._parse_list(html)
            # 女优页有时编码不同，再试 unquote 路径
            if not videos and "/actresses/" in tid:
                parts = tid.split("actresses/", 1)
                if len(parts) == 2:
                    alt = "cn/actresses/" + parse.quote(parse.unquote(parts[1]))
                    if alt != tid:
                        html = self.fetch(self._url(alt, page))
                        videos = self._parse_list(html)
            pagecount = 9999 if videos else page
            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "pageCount": pagecount,
                "limit": 24,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print("[missav] category:", e)
            return {"list": [], "page": page, "pagecount": 1, "pageCount": 1, "limit": 24, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        # 文件夹
        if any(raw.rstrip("/").endswith(x) for x in ("actresses", "genres", "makers", "ranking")):
            return {"list": []}
        if "/actresses/" in raw or "/makers/" in raw or "/genres/" in raw:
            # 可能是子分类列表被当详情：返回空，让客户端走 category
            if not re.search(r"[a-z]{2,}-\d|ppv-\d|fc2-", raw, re.I):
                # actress/maker detail page is still a list of videos - treat as no single vod
                pass

        url = self._video_url(raw)
        # 若是女优/厂商页，把该页视频列表当“详情”不合适；仍尝试解析播放
        if re.search(r"/cn/(actresses|makers|genres)/", url) and not re.search(r"[a-z0-9]+-\d", url, re.I):
            return {"list": []}

        try:
            html = self.fetch(url)
            if not html:
                return {"list": []}
            title = self._meta(html, "og:title") or self._tag_title(html) or self._vid_id(url)
            pic = self._meta(html, "og:image") or ("%s/%s/cover-t.jpg" % (self.cdn, self._vid_id(url)))
            sources = self._extract_sources(html)
            lines = ["%s$%s" % (n, u) for n, u in sources] or ["嗅探$%s" % url]
            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "日本",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "MissAV",
                    "vod_play_url": "#".join(lines),
                }]
            }
        except Exception as e:
            print("[missav] detail:", e)
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
            sources = self._extract_sources(self.fetch(url) or "")
            if sources:
                pick = sources[0][1]
                for n, u in sources:
                    if "720" in n or "1080" in n:
                        pick = u
                        break
                return {"parse": 0, "jx": 0, "url": pick, "header": hj}
        except Exception as e:
            print("[missav] play:", e)
        return {"parse": 1, "jx": 0, "url": url, "header": hj}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        q = parse.quote(str(key or "").strip())
        url = "%s/cn/search?q=%s" % (self.host, q)
        if page > 1:
            url += "&page=%s" % page
        videos = self._parse_list(self.fetch(url) or "")
        return {
            "list": videos,
            "page": page,
            "pagecount": 9999 if videos else page,
            "pageCount": 9999 if videos else page,
            "limit": 24,
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

    # ---------- network / url ----------
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
                m = re.search(r"return\s*`?(https?://spic[^`$\'\"]+)", data)
                if m:
                    self.cdn = m.group(1).rstrip("/")
                if data and len(data) > 400:
                    return data
            except Exception as e:
                last = e
                time.sleep(0.12)
        print("[missav] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
            return resp.read() or b""

    def _url(self, tid, page=1):
        tid = (tid or "").strip("/")
        if tid.startswith("http"):
            base = tid
        else:
            # 女优名含日文，必须对每个 path 段做 quote
            parts = []
            for seg in tid.split("/"):
                if not seg:
                    continue
                # 已编码则不再编
                if "%" in seg:
                    parts.append(seg)
                else:
                    parts.append(parse.quote(seg, safe=""))
            base = "%s/%s" % (self.host, "/".join(parts))
        if int(page or 1) > 1:
            sep = "&" if "?" in base else "?"
            base = "%s%spage=%s" % (base, sep, page)
        return base

    def _video_url(self, raw):
        raw = str(raw or "").strip()
        if raw.startswith("http"):
            return raw
        if raw.startswith("/"):
            return self.host + raw
        if re.match(r"^[\w\-]+$", raw):
            return "%s/cn/%s" % (self.host, raw)
        return self.host + "/" + raw.lstrip("/")

    def _vid_id(self, url):
        m = re.search(r"/(?:cn|en|ja|zh)/([\w\-]+)/?$", url.rstrip("/"))
        if m:
            return m.group(1)
        m = re.search(r"/([\w\-]+)/?$", url.rstrip("/"))
        return m.group(1) if m else url

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

    def _meta(self, html, prop):
        m = re.search(
            r'property=["\']%s["\'][^>]+content=["\']([^"\']+)' % re.escape(prop),
            html or "",
            re.I,
        )
        if not m:
            m = re.search(
                r'content=["\']([^"\']+)["\'][^>]+property=["\']%s["\']' % re.escape(prop),
                html or "",
                re.I,
            )
        return m.group(1).strip() if m else ""

    def _tag_title(self, html):
        t = re.search(r"<title[^>]*>([^<]+)</title>", html or "", re.I)
        if not t:
            return ""
        return t.group(1).split("|")[0].strip()

    # ---------- folders ----------
    def _actress_folder(self, tid, page):
        html = self.fetch(self._url(tid, page))
        items, seen = [], set()
        # ranking: img src + name
        for m in re.finditer(
            r'href="(https?://[^"]+/cn/actresses/([^"]+))"[^>]*>[\s\S]{0,400}?<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"',
            html or "",
            re.I,
        ):
            path, slug, pic, name = m.group(1), parse.unquote(m.group(2)), m.group(3), m.group(4)
            if "ranking" in slug or slug in seen:
                continue
            seen.add(slug)
            items.append({
                "vod_id": "cn/actresses/%s" % slug,
                "vod_name": name or parse.unquote(slug).replace("-", " "),
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "作品集",
                "vod_tag": "folder",
                "style": {"type": "rect", "ratio": 1.0},
            })
        if not items:
            for m in re.finditer(r'href="https?://[^"]+/cn/actresses/([^"/]+)"', html or ""):
                slug = m.group(1)
                if slug in seen or slug == "ranking":
                    continue
                seen.add(slug)
                name = parse.unquote(slug).replace("-", " ")
                items.append({
                    "vod_id": "cn/actresses/%s" % slug,
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_remarks": "女优",
                    "vod_tag": "folder",
                })
        # 女优一览若几乎为空，自动改用排行
        if tid == "cn/actresses" and len(items) < 3:
            return self._actress_folder("cn/actresses/ranking", page)
        return {
            "list": items,
            "page": page,
            "pagecount": 999 if items else page,
            "pageCount": 999 if items else page,
            "limit": 40,
            "total": 9999,
        }

    def _link_folder(self, kind, page):
        """类型 genres / 发行商 makers — 禁止混入 VR 以外的错误解析"""
        html = self.fetch(self._url("cn/%s" % kind, page))
        items, seen = [], set()
        # 优先：带中文名的链接
        pat = r'href="https?://[^"]+/cn/%s/([^"]+)"[^>]*class="[^"]*text-nord13[^"]*"[^>]*>\s*([^<]+)\s*<' % kind
        for m in re.finditer(pat, html or "", re.I):
            slug = m.group(1)
            name = re.sub(r"\s+", " ", m.group(2)).strip()
            name = re.sub(r"&#039;", "'", name)
            if not name or slug in seen:
                continue
            seen.add(slug)
            items.append({
                "vod_id": "cn/%s/%s" % (kind, slug),
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "类型" if kind == "genres" else "厂商",
                "vod_tag": "folder",
            })
        if len(items) < 5:
            for m in re.finditer(r'href="https?://[^"]+/cn/%s/([^"]+)"' % kind, html or "", re.I):
                slug = m.group(1)
                if slug in seen:
                    continue
                seen.add(slug)
                name = parse.unquote(slug).replace("-", " ")
                # 跳过明显非分类
                if slug.lower() in ("vr",) and kind == "makers":
                    continue
                items.append({
                    "vod_id": "cn/%s/%s" % (kind, slug),
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_remarks": "类型" if kind == "genres" else "厂商",
                    "vod_tag": "folder",
                })
        return {
            "list": items,
            "page": page,
            "pagecount": 50 if items else page,
            "pageCount": 50 if items else page,
            "limit": 60,
            "total": len(items) * 2,
        }

    # ---------- list / play ----------
    def _parse_list(self, html):
        if not html:
            return []
        m = re.search(r"return\s*`?(https?://spic[^`$\'\"]+)", html)
        if m:
            self.cdn = m.group(1).rstrip("/")

        skip = {
            "genres", "actresses", "playlists", "search", "history", "login", "register",
            "makers", "new", "release", "uncensored-leak", "today-hot", "weekly-hot",
            "monthly-hot", "siro", "luxu", "gana", "ara", "scute", "maan", "fc2", "heyzo",
            "tokyohot", "1pondo", "caribbeancom", "caribbeancompr", "10musume",
            "pacopacomama", "gachinco", "xxxav", "marriedslash", "naughty4610",
            "naughty0930", "chinese-subtitle", "clive", "klive", "saved", "ranking",
        }
        videos, seen = [], set()

        for m in re.finditer(
            r'href="(https?://(?:www\.)?missav[^"]*?/(?:dm\d+/)?(?:cn|en)/([\w\-]+))"[^>]*?(?:alt="([^"]*)")?[\s\S]{0,900}?data-src="(https?://[^"]+cover[^"]+)"',
            html,
            re.I,
        ):
            url, vid, alt, pic = m.group(1), m.group(2), m.group(3) or "", m.group(4)
            if vid in seen or vid in skip or "/" in vid:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": url,
                "vod_name": (alt.strip() or vid)[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })

        if len(videos) < 5:
            for m in re.finditer(
                r'href="(https?://[^"]+?/(?:dm\d+/)?cn/([\w\-]+))"',
                html,
                re.I,
            ):
                url, vid = m.group(1), m.group(2)
                if vid in seen or vid in skip or "/" in vid:
                    continue
                if not re.search(r"[\-]|\d", vid):
                    continue
                # 排除 actresses/makers 路径误伤
                if any(x in url for x in ["/actresses/", "/makers/", "/genres/"]):
                    continue
                seen.add(vid)
                win = html[max(0, m.start() - 20): m.end() + 700]
                title = ""
                am = re.search(r'alt="([^"]{2,160})"', win)
                if am:
                    title = am.group(1)
                pic = ""
                pm = re.search(r'data-src="(https?://[^"]+cover[^"]+)"', win)
                if pm:
                    pic = pm.group(1)
                if not pic:
                    pic = "%s/%s/cover-t.jpg" % (self.cdn, vid)
                videos.append({
                    "vod_id": url,
                    "vod_name": (title or vid)[:120],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "",
                })
        return videos

    def _extract_sources(self, html):
        sources = []
        m = re.search(
            r"eval\(function\(p,a,c,k,e,d\).*?'([^']+)'\.split\('\|'\)",
            html or "",
            re.S,
        )
        if m:
            keys = m.group(1).split("|")
            try:
                parts = [k for k in keys if re.match(r"^[0-9a-f]{4,12}$", k)]
                if len(parts) >= 5 and "surrit" in keys:
                    uuid = "%s-%s-%s-%s-%s" % (parts[4], parts[3], parts[2], parts[1], parts[0])
                    base = "%s/jmpres/surrit.com/%s" % (self.host, uuid)
                    sources.append(("线路", "%s/playlist.m3u8" % base))
                    sources.append(("720P", "%s/720p/video.m3u8" % base))
                    sources.append(("1080P", "%s/1080p/video.m3u8" % base))
            except Exception as e:
                print("[missav] packer:", e)
        if not sources:
            for u in re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html or ""):
                u = u.replace("\\/", "/")
                if "surrit.com" in u and "jmpres" not in u:
                    u = re.sub(r"https://([^/]+)/", self.host + r"/jmpres/\1/", u, count=1)
                sources.append(("直连", u))
        seen, out = set(), []
        for n, u in sources:
            if u in seen:
                continue
            seen.add(u)
            out.append((n, u))
        return out
