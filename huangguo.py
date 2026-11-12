# -*- coding: utf-8 -*-
# 黄果短剧 huangguo04.net 蜂蜜影视 Spider
# 分页: /asian/zh-CN/videos/recent/page/2  (data-max-page)
# 类型: /asian/zh-CN/videos/genre/{name}
# 详情: /asian/zh-CN/video/cid/{id}

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
        self.name = "黄果短剧"
        self.host = "https://huangguo04.net"
        self.prefix = "/asian/zh-CN"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.cdn = "https://spic2-110.vcwinford.cc"
        self._ssl = None
        # 与官网菜单一致 + 常用类型（videos/genre）
        self.classes = [
            {"type_id": "videos/recent", "type_name": "最近更新"},
            {"type_id": "videos/new-releases", "type_name": "新作上市"},
            {"type_id": "videos/hot/today", "type_name": "今日热门"},
            {"type_id": "videos/hot/week", "type_name": "本周热门"},
            {"type_id": "videos/hot/month", "type_name": "本月热门"},
            {"type_id": "videos/tag/中文字幕", "type_name": "中文字幕"},
            {"type_id": "videos/tag/无码流出", "type_name": "无码流出"},
            {"type_id": "actors", "type_name": "女优一览"},
            {"type_id": "genres", "type_name": "类型"},
            {"type_id": "domestic", "type_name": "国产专区"},
            # 官网类型页主要项
            {"type_id": "videos/genre/高清", "type_name": "高清"},
            {"type_id": "videos/genre/单体作品", "type_name": "单体作品"},
            {"type_id": "videos/genre/独家", "type_name": "独家"},
            {"type_id": "videos/genre/中出", "type_name": "中出"},
            {"type_id": "videos/genre/巨乳", "type_name": "巨乳"},
            {"type_id": "videos/genre/人妻", "type_name": "人妻"},
            {"type_id": "videos/genre/无码流出", "type_name": "类型·无码流出"},
            {"type_id": "videos/genre/素人", "type_name": "素人"},
            {"type_id": "videos/genre/熟女", "type_name": "熟女"},
            {"type_id": "videos/genre/美少女", "type_name": "美少女"},
            {"type_id": "videos/genre/口交", "type_name": "口交"},
            {"type_id": "videos/genre/自拍", "type_name": "自拍"},
            {"type_id": "videos/genre/痴女", "type_name": "痴女"},
            {"type_id": "videos/genre/多人运动", "type_name": "多人运动"},
            {"type_id": "videos/genre/4K", "type_name": "4K"},
            {"type_id": "videos/genre/NTR", "type_name": "NTR"},
            {"type_id": "videos/genre/中文字幕", "type_name": "类型·中文字幕"},
            {"type_id": "videos/genre/女高中生", "type_name": "女高中生"},
            {"type_id": "videos/genre/剧情", "type_name": "剧情"},
            {"type_id": "videos/genre/乱伦", "type_name": "乱伦"},
            {"type_id": "videos/genre/制服", "type_name": "制服"},
            {"type_id": "videos/genre/角色扮演", "type_name": "角色扮演"},
            {"type_id": "videos/genre/OL", "type_name": "OL"},
            {"type_id": "videos/genre/女大学生", "type_name": "女大学生"},
            {"type_id": "videos/genre/丝袜", "type_name": "丝袜"},
            {"type_id": "videos/genre/捆绑", "type_name": "捆绑"},
            {"type_id": "videos/genre/女教师", "type_name": "女教师"},
            {"type_id": "videos/genre/SM", "type_name": "SM"},
            {"type_id": "videos/genre/野外露出", "type_name": "野外露出"},
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
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self._list_url("videos/recent", 1)))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = (tid or "videos/recent").strip("/")
        try:
            if tid in ("genres",):
                return self._genre_folder(page)
            if tid in ("actors",):
                return self._actor_folder(page)
            if tid == "domestic" or tid.startswith("domestic/"):
                path = "videos/recent" if tid == "domestic" else tid.split("domestic/", 1)[-1]
                base = "/domestic/zh-CN/" + path.lstrip("/")
                if page > 1 and "/page/" not in base:
                    base = base.rstrip("/") + "/page/%d" % page
                html = self.fetch(self._abs(base))
                videos = self._parse_list(html)
                max_page = 20
                m = re.search(r'data-max-page="(\d+)"', html or "")
                if m:
                    max_page = int(m.group(1))
                return self._page_result(videos, page, max_page=max_page)

            html = self.fetch(self._list_url(tid, page))
            videos = self._parse_list(html)
            # 从页面读取 max-page
            max_page = 20
            m = re.search(r'data-max-page="(\d+)"', html or "")
            if m:
                max_page = max(1, int(m.group(1)))
            # 女优子页
            if not videos and tid.startswith("actors/"):
                html = self.fetch(self._list_url(tid, page))
                videos = self._parse_list(html)
            return self._page_result(videos, page, max_page=max_page)
        except Exception as e:
            print("[huangguo] category:", e)
            return {"list": [], "page": page, "pagecount": 1, "pageCount": 1, "limit": 24, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.rstrip("/").endswith(("genres", "actors")):
            return {"list": []}
        url = self._video_url(raw)
        try:
            html = self.fetch(url)
            if not html:
                return {"list": []}
            title = self._meta(html, "og:title") or self._tag_title(html) or self._cid(url)
            pic = self._meta(html, "og:image") or ("%s/%s/cover-t.jpg" % (self.cdn, self._cid(url)))
            sources = self._extract_sources(html, url)
            lines = ["%s$%s" % (n, u) for n, u in sources] or ["嗅探$%s" % url]
            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "黄果",
                    "vod_play_url": "#".join(lines),
                }]
            }
        except Exception as e:
            print("[huangguo] detail:", e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + self.prefix + "/",
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
            sources = self._extract_sources(self.fetch(url) or "", url)
            if sources:
                return {"parse": 0, "jx": 0, "url": sources[0][1], "header": hj}
        except Exception as e:
            print("[huangguo] play:", e)
        return {"parse": 1, "jx": 0, "url": url, "header": hj}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        q = parse.quote(str(key or "").strip())
        path = "%s/videos/search/%s" % (self.prefix, q)
        if page > 1:
            path += "/page/%d" % page
        videos = self._parse_list(self.fetch(self._abs(path)) or "")
        return self._page_result(videos, page, max_page=20)

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
                m = re.search(r"https://spic\d+[^/\"']+\.vcwinford\.cc", data)
                if m:
                    self.cdn = m.group(0)
                if data and len(data) > 400 and "站点维护中" not in data:
                    return data
            except Exception as e:
                last = e
                time.sleep(0.12)
        print("[huangguo] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
            return resp.read() or b""

    def _abs(self, path):
        if not path:
            return self.host
        if path.startswith("http"):
            return path
        return self.host + (path if path.startswith("/") else "/" + path)

    def _list_url(self, tid, page=1):
        tid = (tid or "").strip("/")
        if tid.startswith("asian/") or tid.startswith("domestic/"):
            path = "/" + tid
        else:
            path = "%s/%s" % (self.prefix, tid)

        # 编码每段（保留已有 %）
        parts = []
        for seg in path.split("/"):
            if not seg:
                continue
            if "%" in seg:
                parts.append(seg)
            else:
                parts.append(parse.quote(seg, safe=""))
        path = "/" + "/".join(parts)

        # 官网分页: .../page/N
        page = int(page or 1)
        if page > 1:
            path = path.rstrip("/") + "/page/%d" % page
        return self._abs(path)

    def _video_url(self, raw):
        raw = str(raw or "").strip()
        if raw.startswith("http"):
            return raw
        if raw.startswith("/"):
            return self._abs(raw)
        if re.match(r"^[\w\-]+$", raw):
            return self._abs("%s/video/cid/%s" % (self.prefix, raw))
        return self._abs(raw)

    def _cid(self, url):
        m = re.search(r"/video/cid/([\w\-]+)", url or "")
        if m:
            return m.group(1)
        m = re.search(r"/([\w\-]+)/?$", (url or "").rstrip("/"))
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
            html or "", re.I,
        )
        return m.group(1).strip() if m else ""

    def _tag_title(self, html):
        t = re.search(r"<title[^>]*>([^<]+)</title>", html or "", re.I)
        if not t:
            return ""
        return re.sub(r"^.*?\|\s*", "", t.group(1)).strip() or t.group(1).strip()

    def _page_result(self, videos, page, max_page=20):
        videos = videos or []
        if videos:
            pagecount = max(int(max_page or 20), int(page or 1))
        else:
            pagecount = page
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 24,
            "total": pagecount * 24 if videos else 0,
        }

    def _genre_folder(self, page):
        html = self.fetch(self._abs(self.prefix + "/genres"))
        items, seen = [], set()
        for m in re.finditer(
            r'href="(/asian/zh-CN/videos/genre/([^"]+))"[^>]*title="([^"]*)"',
            html or "",
        ):
            path, slug, name = m.group(1), m.group(2), m.group(3).strip()
            name = name or parse.unquote(slug)
            if not name or name == "----" or slug in seen:
                continue
            seen.add(slug)
            items.append({
                "vod_id": "videos/genre/" + parse.unquote(slug),
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "类型",
                "vod_tag": "folder",
            })
        return self._page_result(items, page, max_page=1)

    def _actor_folder(self, page):
        html = self.fetch(self._list_url("actors", page))
        items, seen = [], set()
        # 官网女优作品列表入口是 /videos/actor/{name}
        for m in re.finditer(
            r'href="(/asian/zh-CN/videos/actor/([^"]+))"[^>]*>',
            html or "",
            re.I,
        ):
            path, slug = m.group(1), m.group(2)
            key = parse.unquote(slug)
            if key in seen or key.startswith("page"):
                continue
            seen.add(key)
            win = (html or "")[max(0, m.start() - 100): m.end() + 600]
            pic = ""
            pm = re.search(r'(?:data-src|src)="(https?://[^"]+)"', win)
            if pm and not any(x in pm.group(1) for x in ("flag", "user/", "logo", "ad-provider")):
                pic = pm.group(1)
            name = key
            # 去掉括号日文名可保留
            items.append({
                "vod_id": "videos/actor/" + key,
                "vod_name": name[:40],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "作品集",
                "vod_tag": "folder",
            })
        # items 为空时不再二次兜底

        max_page = 50
        m = re.search(r'data-max-page="(\d+)"', html or "")
        if m:
            max_page = int(m.group(1))
        # 分页链接到 page/2000 时取较小值
        pages = re.findall(r'/actors/page/(\d+)', html or "")
        if pages:
            nums = [int(x) for x in pages if int(x) < 5000]
            if nums:
                max_page = max(max_page, max(nums) if max(nums) < 500 else max_page)
        return self._page_result(items, page, max_page=max_page)

    def _parse_list(self, html):
        if not html:
            return []
        m = re.search(r"https://spic\d+[^/\"']+\.vcwinford\.cc", html)
        if m:
            self.cdn = m.group(0)

        videos, seen = [], set()
        # 亚洲: /video/cid/{id}
        for m in re.finditer(
            r'href="((?:https://[^"]+)?/(?:asian|domestic)/zh-CN/video/cid/([\w\-]+))"',
            html,
            re.I,
        ):
            path, cid = m.group(1), m.group(2)
            if cid in seen or cid == "__STREAMIT_VCODE__":
                continue
            seen.add(cid)
            win = html[max(0, m.start() - 40): m.end() + 900]
            title = ""
            tm = re.search(r'alt="([^"]{2,160})"', win)
            if tm:
                title = tm.group(1)
            if not title:
                tm = re.search(r'title="([^"]{2,160})"', win)
                if tm:
                    title = tm.group(1)
            pic = ""
            pm = re.search(r'(?:data-src|src)="(https?://[^"]+(?:cover|thumb)[^"]*)"', win)
            if pm:
                pic = pm.group(1)
            if not pic:
                pic = "%s/%s/cover-t.jpg" % (self.cdn, cid)
            url = path if path.startswith("http") else self._abs(path)
            videos.append({
                "vod_id": url,
                "vod_name": (title or cid)[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })

        # 国产: /video/vid/{uid}
        for m in re.finditer(
            r'href="((?:https://[^"]+)?/domestic/zh-CN/video/vid/([a-f0-9]+))"',
            html,
            re.I,
        ):
            path, uid = m.group(1), m.group(2)
            if uid in seen or uid == "__STREAMIT_VUID__":
                continue
            seen.add(uid)
            win = html[max(0, m.start() - 80): m.end() + 1000]
            title = ""
            tm = re.search(r'(?:alt|title)="([^"]{2,160})"', win)
            if tm:
                title = tm.group(1)
            if not title:
                tm = re.search(r'streamit-video-card__title[^>]*>([^<]+)', win)
                if tm:
                    title = tm.group(1).strip()
            pic = ""
            pm = re.search(r'(?:data-src|src)="(https?://[^"]+(?:thumb|cover)[^"]*)"', win)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', win)
                if pm and "flag" not in pm.group(1) and "user/" not in pm.group(1):
                    pic = pm.group(1)
            url = path if path.startswith("http") else self._abs(path)
            videos.append({
                "vod_id": url,
                "vod_name": (title or uid)[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "国产",
            })
        return videos

    def _extract_sources(self, html, page_url=""):
        sources = []
        uid = ""
        m = re.search(r'"videoUid"\s*:\s*"([^"]+)"', html or "")
        if m:
            uid = m.group(1)
        if not uid:
            m = re.search(r'data-streamit-page-video-uid="([^"]+)"', html or "")
            if m:
                uid = m.group(1)
        if not uid:
            m = re.search(r'/video/vid/([a-f0-9]{8,})', page_url or html or "", re.I)
            if m:
                uid = m.group(1)
        if uid:
            for culture in ("asian/zh-CN", "domestic/zh-CN"):
                api = "%s/%s/api/video/stream?videoUid=%s" % (self.host, culture, uid)
                try:
                    data = self._fetch_json(api)
                    if not data:
                        continue
                    pl = data.get("playlist") or []
                    for i, item in enumerate(pl):
                        if not isinstance(item, dict):
                            continue
                        u = item.get("url") or ""
                        if not u or not u.startswith("http"):
                            continue
                        label = "线路%d" % (i + 1)
                        low = u.lower()
                        if "1080" in low:
                            label = "1080P"
                        elif "720" in low:
                            label = "720P"
                        elif "480" in low:
                            label = "480P"
                        sources.append((label, u))
                    if sources:
                        break
                except Exception as e:
                    print("[huangguo] stream api:", e)
        for u in re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html or ""):
            u = u.replace("\\/", "/")
            sources.append(("直连", u))
        seen, out = set(), []
        for n, u in sources:
            if u in seen:
                continue
            seen.add(u)
            out.append((n, u))
        return out

    def _fetch_json(self, url):
        last = None
        for _ in range(2):
            try:
                req = Request(url, headers={
                    "User-Agent": self.headers["User-Agent"],
                    "Accept": "application/json,*/*",
                    "Referer": self.host + self.prefix + "/",
                })
                with urlopen(req, timeout=15, context=self._ssl_ctx()) as resp:
                    raw = resp.read().decode("utf-8", "ignore")
                if not raw or raw.strip().startswith("<"):
                    return None
                return json.loads(raw)
            except Exception as e:
                last = e
                time.sleep(0.1)
        print("[huangguo] json fail", url, last)
        return None
