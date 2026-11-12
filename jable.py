# -*- coding: utf-8 -*-
# Jable 分页修复：第2页起强制 ?from=N（已验证与第1页内容不同）
import html as html_lib
import re
import urllib.parse
import urllib.request
import http.cookiejar

from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    name = "Jable新版"
    # jable.sbs 可直连；jable.tv 常被 Cloudflare 拦
    BASE_URL = "https://jable.sbs"
    FALLBACK_URLS = ["https://jable.sbs", "https://jable.my", "https://jable.tv"]
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://jable.sbs/",
    }
    TIMEOUT = 15

    def __init__(self):
        super().__init__()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def getName(self):
        return self.name

    def init(self, extend=""):
        return None

    def isVideoFormat(self, url):
        return ".m3u8" in (url or "") or ".mp4" in (url or "")

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        try:
            if isinstance(param, dict):
                url = param.get("url") or param.get("target") or ""
            else:
                url = str(param or "")
            if not url:
                return [400, "text/plain", b""]
            for _ in range(2):
                if "%" in url:
                    url = urllib.parse.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b""]
            headers = {
                "User-Agent": self.HEADERS["User-Agent"],
                "Referer": self.BASE_URL + "/",
            }
            req = urllib.request.Request(url, headers=headers)
            with self._opener.open(req, timeout=self.TIMEOUT) as resp:
                body = resp.read() or b""
            ctype = "image/jpeg"
            if body[:3] == b"\xff\xd8\xff":
                ctype = "image/jpeg"
            elif body[:8].startswith(b"\x89PNG"):
                ctype = "image/png"
            elif body[:4] == b"RIFF":
                ctype = "image/webp"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]


    def _classes(self):
        return [
            {"type_id": "latest-updates", "type_name": "最近更新"},
            {"type_id": "hot", "type_name": "热门影片"},
            {"type_id": "categories/chinese-subtitle", "type_name": "中文字幕"},
            {"type_id": "new-release", "type_name": "全新上市"},
            {"type_id": "categories", "type_name": "主题&标签"},
        ]

    def homeContent(self, filter):
        # 首页只返回分类，列表交给 category / homeVideo，避免客户端不走翻页
        return {"class": self._classes(), "list": [], "filters": {}}

    def homeVideoContent(self):
        return {"list": self._parse_list(self._fetch(self._page_url("latest-updates", 1)) or "")}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        path = str(tid or "latest-updates").strip("/")

        if path == "categories":
            return self._categories_folder()

        url = self._page_url(path, page)
        print("[Jable] page=%s url=%s" % (page, url))
        html = self._fetch(url)

        # 失败时换备用域名重试同一 from 参数
        if (not html or self._is_gate(html)) and page >= 1:
            for host in self.FALLBACK_URLS:
                alt = self._page_url(path, page, host=host)
                if alt == url:
                    continue
                print("[Jable] retry", alt)
                html = self._fetch(alt)
                if html and not self._is_gate(html):
                    break

        data = self._parse_list(html or "") if html and not self._is_gate(html) else []
        print("[Jable] page=%s count=%s" % (page, len(data)))

        # 关键：只要本页有片，就告诉客户端还有很多页，否则上滑不会请求 page=2
        if data:
            pagecount = 9999
            total = 999999
        else:
            pagecount = page
            total = (page - 1) * 24

        return {
            "list": data,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 24,
            "total": total,
        }

    def _page_url(self, path, page, host=None):
        """
        实测：
          第1页 https://jable.sbs/latest-updates/
          第2页 https://jable.sbs/latest-updates/?from=2  （内容与第1页不同）
          第3页 https://jable.sbs/latest-updates/?from=3
        路径 /latest-updates/2/ 也会到第2页，但统一用 ?from= 更稳
        """
        host = (host or self.BASE_URL).rstrip("/")
        path = (path or "latest-updates").strip("/")
        if page <= 1:
            return "%s/%s/" % (host, path)
        return "%s/%s/?from=%s" % (host, path, page)

    def _categories_folder(self):
        result = {
            "list": [],
            "page": 1,
            "pagecount": 1,
            "pageCount": 1,
            "limit": 200,
            "total": 200,
        }
        cat_html = self._fetch(self.BASE_URL + "/categories/")
        if cat_html and not self._is_gate(cat_html):
            for m in re.finditer(
                r'<a[^>]*href=["\'](?:https?://[^"\']+)?(/categories/([^"\'/]+)/?)["\'][^>]*>'
                r'([\s\S]*?)</a>',
                cat_html, re.I | re.S
            ):
                cat_path = "categories/" + m.group(2).strip("/")
                block = m.group(3)
                pic = ""
                img_m = re.search(r'<img[^>]*(?:src|data-src)=["\']([^"\']+)["\']', block, re.I)
                if img_m:
                    pic = img_m.group(1)
                    if pic.startswith("//"):
                        pic = "https:" + pic
                name = ""
                h4 = re.search(r'<h4[^>]*>([^<]+)', block, re.I)
                if h4:
                    name = h4.group(1).strip()
                if not name:
                    name = re.sub(r'<[^>]+>', ' ', block)
                    name = re.sub(r'\d[\d,]*\s*部?', '', name)
                    name = re.sub(r'\s+', ' ', name).strip()[:30]
                if not name:
                    continue
                result["list"].append({
                    "vod_id": cat_path,
                    "vod_name": self._clean(name),
                    "vod_pic": pic,
                    "vod_remarks": "主题",
                    "vod_tag": "folder",
                    "style": {"type": "rect", "ratio": 1.4},
                })
        if not result["list"]:
            for cid, cname in [
                ("categories/chinese-subtitle", "中文字幕"),
                ("categories/roleplay", "角色剧情"),
                ("categories/uniform", "制服诱惑"),
                ("categories/pantyhose", "丝袜美腿"),
                ("categories/bdsm", "主奴调教"),
                ("categories/sex-only", "直接开啪"),
                ("categories/insult", "凌辱快感"),
                ("categories/pov", "男友视角"),
                ("categories/groupsex", "多P群交"),
                ("categories/lesbian", "女同欢愉"),
                ("categories/uncensored", "无码解放"),
                ("categories/hidden-cam", "盗摄偷拍"),
            ]:
                result["list"].append({
                    "vod_id": cid,
                    "vod_name": cname,
                    "vod_pic": "",
                    "vod_remarks": "主题",
                    "vod_tag": "folder",
                    "style": {"type": "rect", "ratio": 1.4},
                })
        result["total"] = len(result["list"])
        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        q = urllib.parse.quote(str(key or "").strip())
        if page <= 1:
            urls = [
                "%s/search/%s/" % (self.BASE_URL, q),
                "%s/search/?q=%s" % (self.BASE_URL, q),
            ]
        else:
            urls = [
                "%s/search/%s/?from=%s" % (self.BASE_URL, q, page),
                "%s/search/?q=%s&from=%s" % (self.BASE_URL, q, page),
            ]
        data = []
        for url in urls:
            html = self._fetch(url)
            if html and not self._is_gate(html):
                data = self._parse_list(html)
                if data:
                    break
        pagecount = 9999 if data else page
        return {
            "list": data,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 24,
            "total": 999999 if data else 0,
        }

    def detailContent(self, ids):
        result = {"list": []}
        value = ids[0] if isinstance(ids, list) and ids else ids
        url = self._absolute(str(value or ""))
        if not url or "/videos/" not in url:
            return result
        page = self._fetch(url)
        if not page or self._is_gate(page):
            return result

        title = self._first(page, r'<section[^>]+class=["\'][^"\']*video-info[^"\']*["\'][^>]*>.*?<h4[^>]*>(.*?)</h4>')
        title = self._clean(title) or self._clean(
            self._first(page, r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)')
        )
        title = title or self._clean(self._first(page, r'<title[^>]*>(.*?)</title>'))
        pic = self._first(page, r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)')
        pic = pic or self._first(page, r'<video[^>]+poster=["\']([^"\']+)')
        actor = re.findall(
            r'<a[^>]+class=["\'][^"\']*model[^"\']*["\'][^>]*>.*?<span[^>]+(?:title|data-original-title)=["\']([^"\']+)',
            page, re.S | re.I
        )
        actor = ",".join(dict.fromkeys(self._clean(x) for x in actor if self._clean(x)))
        publish = self._first(page, r'上市于\s*([^<]+)')
        quality = self._first(
            page,
            r'<div[^>]+class=["\'][^"\']*header-right[^"\']*["\'][^>]*>.*?<h6[^>]*>(.*?)</h6>',
        )
        result["list"].append({
            "vod_id": url,
            "vod_name": title or url.rstrip("/").split("/")[-1],
            "vod_pic": self._absolute(pic),
            "type_name": "",
            "vod_year": self._clean(publish),
            "vod_area": "日本",
            "vod_remarks": self._clean(quality) or "",
            "vod_actor": actor,
            "vod_director": "",
            "vod_content": title or "",
            "vod_play_from": "JableTV",
            "vod_play_url": "直连$" + url + "#嗅探$" + url,
        })
        return result

    def playerContent(self, flag, id, vipFlags):
        value = str(id or "")
        headers = {
            "User-Agent": self.HEADERS["User-Agent"],
            "Referer": self.BASE_URL + "/",
            "Origin": self.BASE_URL.rstrip("/"),
            "Accept": "*/*",
        }
        if self.isVideoFormat(value):
            return {"parse": 0, "jx": 0, "url": value, "header": headers}
        url = self._norm_video_url(value) or self._absolute(value)
        page = self._fetch(url) if url else ""
        if not page and value:
            page = self._fetch(self._absolute(value))
        m3u8 = self._first(page, r'\bvar\s+hlsUrl\s*=\s*["\']([^"\']+)["\']')
        if not m3u8:
            m3u8 = self._first(page, r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']')
        if m3u8:
            try:
                pu = urllib.parse.urlparse(url or self.BASE_URL)
                headers["Referer"] = "%s://%s/" % (pu.scheme, pu.netloc)
                headers["Origin"] = "%s://%s" % (pu.scheme, pu.netloc)
            except Exception:
                pass
            return {"parse": 0, "jx": 0, "url": m3u8, "header": headers}
        return {"parse": 1, "jx": 0, "url": url or value, "header": headers}


    def _parse_list(self, page):
        result, seen = [], set()
        cards = re.findall(
            r'<div[^>]+class=["\'][^"\']*\bcol-6\b[^"\']*\bcol-sm-4\b[^"\']*["\'][^>]*>.*?(?=<div[^>]+class=["\'][^"\']*\bcol-6\b[^"\']*\bcol-sm-4\b|</section>)',
            page or "", re.S | re.I,
        )
        if len(cards) < 3:
            cards = re.findall(
                r'<div[^>]+class=["\'][^"\']*video-img-box[^"\']*["\'][^>]*>[\s\S]{0,2500}?</div>\s*</div>',
                page or "", re.I,
            )
        for card in cards:
            links = re.findall(r'<a[^>]+href=["\']([^"\']*/videos/[^"\']+)["\']', card, re.I)
            href = links[-1] if links else ""
            title = self._first(card, r'<h6[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>.*?<a[^>]*>(.*?)</a>')
            if not title:
                title = self._first(card, r'<h6[^>]*>\s*<a[^>]*>(.*?)</a>')
            if not title:
                title = self._first(card, r'title=["\']([^"\']{3,160})["\']')
            pic = self._first(card, r'data-src=["\']([^"\']+)["\']')
            if not pic or "placeholder" in (pic or ""):
                pic = self._first(card, r'data-original=["\']([^"\']+)["\']')
            if not pic or "placeholder" in (pic or ""):
                pic = self._first(card, r'<img[^>]+src=["\']([^"\']+)["\']')
            if pic and "placeholder" in pic:
                pic = ""
            if pic and "320x180" in pic:
                pic = pic.replace("320x180/1.jpg", "preview.jpg").replace("/320x180/1", "/preview")
            duration = self._first(
                card,
                r'class=["\'][^"\']*absolute-bottom-right[^"\']*["\'][^>]*>.*?(\d+:\d+(?::\d+)?)',
            )
            if not duration:
                duration = self._first(card, r'class=["\'][^"\']*label[^"\']*["\'][^>]*>([^<]+)')
            if not href or not title:
                continue
            url = self._norm_video_url(href)
            if not url or url in seen:
                continue
            seen.add(url)
            result.append({
                "vod_id": url,
                "vod_name": self._clean(title),
                "vod_pic": self._cover(pic),
                "vod_remarks": self._clean(duration),
            })

        return result


    def _norm_video_url(self, href):
        if not href:
            return ""
        m = re.search(r"/videos/([\w-]+)/?", href, re.I)
        if not m:
            return self._absolute(href)
        return "%s/videos/%s/" % (self.BASE_URL.rstrip("/"), m.group(1))

    def _cover(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        if pic.startswith("/"):
            pic = self.BASE_URL.rstrip("/") + pic
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    return "%s&url=%s" % (base, urllib.parse.quote(pic))
        except Exception:
            pass
        return pic

    def _fetch(self, url):
        for candidate in self._candidates(url):
            try:
                headers = dict(self.HEADERS)
                headers["Referer"] = self.BASE_URL + "/"
                req = urllib.request.Request(candidate, headers=headers)
                with self._opener.open(req, timeout=self.TIMEOUT) as resp:
                    data = resp.read().decode("utf-8", "ignore")
                    if data and not self._is_gate(data):
                        return data
                    if data and "Just a moment" not in data:
                        return data
            except Exception as exc:
                print("[Jable] fetch failed:", candidate, exc)
        return ""

    def _candidates(self, url):
        if not url:
            return []
        parsed = urllib.parse.urlparse(url)
        result = [url]
        for host in self.FALLBACK_URLS:
            candidate = host.rstrip("/") + parsed.path + (("?" + parsed.query) if parsed.query else "")
            if candidate not in result:
                result.append(candidate)
        return result

    def _absolute(self, value):
        return urllib.parse.urljoin(self.BASE_URL + "/", value or "") if value else ""

    def _is_gate(self, page):
        if not page:
            return True
        if "Just a moment" in page or "cf-mitigated" in page:
            return True
        return "继续访问" in page and ("/enter" in page or "continue-button" in page)

    def _first(self, text, pattern):
        match = re.search(pattern, text or "", re.S | re.I)
        return match.group(1).strip() if match else ""

    def _clean(self, value):
        value = html_lib.unescape(value or "")
        value = re.sub(r"<[^>]+>", "", value)
        return re.sub(r"\s+", " ", value).strip()
