# -*- coding: utf-8 -*-
# youperv.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 /{tag}/page/N/  · 详情直链 MP4 (files.klubnichka-hd.com)

import sys
import re
import json
import time
from urllib import parse
from bs4 import BeautifulSoup

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def __init__(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "YouPerv"
        self.host = "https://youperv.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.classes = [
            {"type_id": "latest", "type_name": "Latest"},
            {"type_id": "top-porn-videos.html", "type_name": "Top Videos"},
            {"type_id": "top-50-most-viewed-videos.html", "type_name": "Most Viewed"},
            {"type_id": "anal", "type_name": "Anal"},
            {"type_id": "amateur", "type_name": "Amateur"},
            {"type_id": "big-tits", "type_name": "Big Tits"},
            {"type_id": "big-dick", "type_name": "Big Dick"},
            {"type_id": "blonde", "type_name": "Blonde"},
            {"type_id": "brunette", "type_name": "Brunette"},
            {"type_id": "creampie", "type_name": "Creampie"},
            {"type_id": "cuckold", "type_name": "Cuckold"},
            {"type_id": "cumshot", "type_name": "Cumshot"},
            {"type_id": "handjob", "type_name": "Handjob"},
            {"type_id": "interracial", "type_name": "Interracial"},
            {"type_id": "lesbian", "type_name": "Lesbian"},
            {"type_id": "milf", "type_name": "MILF"},
            {"type_id": "pov", "type_name": "POV"},
            {"type_id": "teen", "type_name": "Teen"},
            {"type_id": "threesome", "type_name": "Threesome"},
            {"type_id": "beautiful-girl", "type_name": "Beautiful Girl"},
            {"type_id": "juicy-ass", "type_name": "Juicy Ass"},
            {"type_id": "female-orgasm", "type_name": "Female Orgasm"},
            {"type_id": "bathroom", "type_name": "Bathroom"},
            {"type_id": "kitchen", "type_name": "Kitchen"},
            {"type_id": "high-heels", "type_name": "High Heels"},
            {"type_id": "anal-creampie", "type_name": "Anal Creampie"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv", ".mkv", ".ts"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        try:
            html = self.fetch(self.host + "/tags/")
            if html:
                dyn = self._parse_tags(html)
                if dyn:
                    known = {c["type_id"] for c in self.classes}
                    extra = [c for c in dyn if c["type_id"] not in known]
                    self.classes = self.classes + extra
        except Exception:
            pass
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            tid = (tid or "latest").strip("/")
            if tid in ("latest", "home", ""):
                url = self.host + "/" if pg == "1" else f"{self.host}/page/{pg}/"
            elif tid.endswith(".html"):
                url = f"{self.host}/{tid}"
            else:
                if pg == "1":
                    url = f"{self.host}/{tid}/"
                else:
                    url = f"{self.host}/{tid}/page/{pg}/"
            html = self.fetch(url)
            videos = self._parse_list(html)
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "pageCount": 9999 if videos else int(pg),
                "limit": 24,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[youperv] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "pageCount": 1, "limit": 24, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = self.host + "/" + raw.lstrip("/")

        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html or "", "html.parser")

            title = ""
            h1 = soup.select_one("h1")
            if h1:
                title = h1.get_text(strip=True)
            if not title and soup.title:
                title = re.sub(r"\s*[-|].*$", "", soup.title.get_text()).strip()
            if not title:
                # 从 URL 文件名还原
                slug = url.rstrip("/").split("/")[-1].replace(".html", "")
                slug = re.sub(r"^\d+-", "", slug)
                title = slug.replace("-", " ").strip().title()

            pic = ""
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html or "")
            if not m:
                m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html or "")
            if m:
                pic = m.group(1)
            if not pic:
                img = soup.select_one("video[poster], img[src*='upload'], img[src*='http']")
                if img:
                    pic = img.get("poster") or img.get("src") or ""

            # MP4 sources
            play_parts = []
            seen = set()
            for src in re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', html or ""):
                if not src.startswith("http"):
                    continue
                if src in seen:
                    continue
                seen.add(src)
                play_parts.append(f"HD${self._fix_media_url(src)}")
            for src in re.findall(r'https://files\.[^"\'\s<>]+\.mp4', html or ""):
                if src in seen:
                    continue
                seen.add(src)
                play_parts.append(f"HD${self._fix_media_url(src)}")
            if not play_parts:
                play_parts.append(f"Page${url}")

            return {
                "list": [{
                    "vod_id": url.replace(self.host, "") if url.startswith(self.host) else url,
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "YouPerv",
                    "vod_play_url": "#".join(play_parts),
                }]
            }
        except Exception as e:
            print(f"[youperv] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers_json = json.dumps({
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        if not id:
            return {"parse": 1, "url": self.host, "header": headers_json}

        if self.isVideoFormat(id) or "klubnichka" in id or "get_file" in id:
            url = self._fix_media_url(id)
            return {"parse": 0, "jx": 0, "url": url, "header": headers_json}

        # 详情页再解析
        if ".html" in id or id.startswith("http") or id.startswith("/"):
            d = self.detailContent([id])
            item = (d.get("list") or [{}])[0]
            play = (item.get("vod_play_url") or "").split("#")[0]
            if "$" in play:
                real = play.split("$", 1)[1]
                if self.isVideoFormat(real):
                    return {"parse": 0, "jx": 0, "url": self._fix_media_url(real), "header": headers_json}
            return {"parse": 1, "url": id if id.startswith("http") else self.host + id, "header": headers_json}

        return {"parse": 1, "url": id, "header": headers_json}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            # 站点搜索若存在
            q = parse.quote(key)
            url = f"{self.host}/index.php?do=search&subaction=search&story={q}"
            if pg != "1":
                url += f"&search_start={pg}"
            html = self.fetch(url)
            videos = self._parse_list(html)
            if not videos:
                # 退化为分类关键词页
                slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
                videos = self._parse_list(self.fetch(f"{self.host}/{slug}/"))
            return {"list": videos}
        except Exception as e:
            print(f"[youperv] search error: {e}")
            return {"list": []}

    def localProxy(self, param):
        try:
            import requests
            from urllib import parse as up
            if isinstance(param, dict):
                url = param.get("url") or param.get("target") or ""
            else:
                url = str(param or "")
            if not url:
                return [400, "text/plain", b"no url"]
            for _ in range(2):
                if "%" in url and ("http%" in url.lower() or url.lower().startswith("%")):
                    url = up.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b"bad url"]
            resp = requests.get(url, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
                "Accept": "image/*,*/*;q=0.8",
            }, timeout=15, verify=False)
            if resp.status_code != 200 or not resp.content:
                return [resp.status_code, "text/plain", (resp.content or b"")[:200]]
            body = resp.content
            ctype = "image/jpeg"
            if body[:3] == b"\xff\xd8\xff":
                ctype = "image/jpeg"
            elif body[:8] == b"\x89PNG\r\n\x1a\n":
                ctype = "image/png"
            elif body[:4] == b"RIFF" and body[8:12] == b"WEBP":
                ctype = "image/webp"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    def _proxy_pic(self, pic):
        if not pic or not str(pic).startswith("http"):
            if pic and pic.startswith("/"):
                pic = self.host + pic
            else:
                return pic or ""
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base:
                    return f"{base}&url={parse.quote(pic)}"
        except Exception:
            pass
        return pic

    def _fix_media_url(self, url):
        if not url:
            return url
        try:
            # 避免二次编码
            raw = parse.unquote(url)
            parts = parse.urlsplit(raw)
            path = parse.quote(parts.path, safe="/")
            return parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
        except Exception:
            return url.replace(" ", "%20")

    def fetch(self, url, retry=2):
        import requests
        last_err = None
        for _ in range(retry):
            try:
                resp = requests.get(url, headers=self.headers, timeout=12, verify=False)
                resp.encoding = "utf-8"
                if resp.status_code == 200 and len(resp.text) > 200:
                    return resp.text
                last_err = f"status={resp.status_code}"
            except Exception as e:
                last_err = e
                time.sleep(0.2)
        print(f"[youperv] fetch fail: {url} {last_err}")
        return ""

    def _parse_tags(self, html):
        cats = []
        seen = set()
        skip = {
            "es", "fr", "de", "cz", "pl", "it", "zh", "ar", "tr", "pt", "nl", "ja",
            "ro", "id", "th", "vi", "my", "gr", "he", "ua", "sv", "hu", "hr", "bg", "hi", "tags",
        }
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[href]"):
            href = a.get("href") or ""
            m = re.match(r"https?://youperv\.com/([a-z0-9-]+)/?$", href)
            if not m:
                continue
            slug = m.group(1)
            if slug in skip or slug in seen:
                continue
            seen.add(slug)
            name = a.get_text(strip=True) or slug.replace("-", " ").title()
            cats.append({"type_id": slug, "type_name": name})
        return cats

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")
        seen = set()

        for a in soup.select('a[href*=".html"]'):
            href = a.get("href") or ""
            if not re.search(r"/(\d+)-[^/]+\.html", href):
                continue
            if href.startswith("/"):
                href = self.host + href
            if not href.startswith("http"):
                continue
            path = href
            if path in seen:
                continue
            seen.add(path)

            # 标题：优先 img alt / title，其次 URL 文件名
            title = a.get("title") or ""
            img = a.select_one("img")
            if not img and a.parent:
                img = a.parent.select_one("img")
            if img and not title:
                title = img.get("alt") or ""
            if not title or title.upper() in ("HD", "NEW", "VIDEO"):
                text = a.get_text(" ", strip=True)
                if text and text.upper() not in ("HD", "NEW") and not re.match(r"^\d+:\d+$", text):
                    title = text
            if not title or title.upper() in ("HD", "NEW"):
                slug = href.rstrip("/").split("/")[-1].replace(".html", "")
                slug = re.sub(r"^\d+-", "", slug)
                title = slug.replace("-", " ").strip().title()

            pic = ""
            if img:
                pic = (img.get("data-src") or img.get("data-original") or img.get("src") or "").strip()
            if pic.startswith("data:"):
                pic = ""
            if pic.startswith("//"):
                pic = "https:" + pic
            if pic.startswith("/"):
                pic = self.host + pic

            videos.append({
                "vod_id": path.replace(self.host, ""),
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })
        return videos


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    cat = sp.categoryContent("big-tits", "1", False, {})
    print("list", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(" ", v.get("vod_name", "")[:50], "|", (v.get("vod_pic") or "")[:40])
    if cat.get("list"):
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        item = (d.get("list") or [{}])[0]
        print("play", (item.get("vod_play_url") or "")[:120])
        play = sp.playerContent("YouPerv", item.get("vod_play_url", "").split("#")[0].split("$")[-1], [])
        print("player", play.get("parse"), str(play.get("url", ""))[:80])
