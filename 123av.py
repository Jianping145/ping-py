# -*- coding: utf-8 -*-
"""
123AV (123av.ink) —— 蜂蜜影视 / TVBox 爬虫

播放策略对齐能播的 SupJav.py：
  detailContent 只下发 iframe：https://upload18.to/play/index/{slug}
  playerContent 点播时再解析 PLAYER_CONFIG.m3u8
  请求头必须带 Sec-Fetch-Dest: empty 等，否则 helvid Cloudflare 403
"""
import re
import json
import urllib.parse
import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from bs4 import BeautifulSoup

sys.path.append("..")
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def __init__(self):
            pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


class Spider(Spider):
    name = "123AV"
    base_url = "https://123av.ink"
    site_url = "https://123av.ink"
    timeout = 15

    headers = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://123av.ink/",
    }

    CLASS_MAP = [
        ("", "最新 New"),
        ("uncensored", "无码 Uncensored"),
        ("censored", "有码 Censored"),
        ("uncensored-leaked", "无码流出 Leaked"),
        ("chinese", "国产 Chinese"),
        ("amateur", "素人 Amateur"),
    ]

    # 与能播的 SupJav 一致
    STREAM_HEADERS = {
        "User-Agent": _UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Referer": "https://upload18.to/",
        "Origin": "https://upload18.to",
    }

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        retry = Retry(total=2, backoff_factor=0.6,
                      status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset(["GET"]))
        adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def getName(self):
        return self.name

    def _fetch(self, url, referer=None, headers=None):
        try:
            hd = dict(headers or {})
            if referer:
                hd["Referer"] = referer
            resp = self.session.get(url, timeout=self.timeout, headers=hd or None)
            if resp.status_code != 200:
                print("[%s] HTTP %s %s" % (self.name, resp.status_code, url))
                return None
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print("[%s] 请求失败 %s: %s" % (self.name, url, e))
            return None

    def _abs(self, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.base_url + url
        return self.base_url + "/" + url

    def _parse_items(self, soup):
        out, seen = [], set()
        boxes = soup.select(".box-item")
        nodes = boxes if boxes else soup.select("a[href]")

        for box in nodes:
            try:
                if box.name == "a":
                    a = box
                    img = a.select_one("img")
                    title_el = a
                else:
                    a = box.select_one(".thumb a[href]") or box.select_one("a[href]")
                    if not a:
                        continue
                    img = box.find("img")
                    title_el = box.select_one(".detail a") or a

                href = a.get("href") or ""
                m = (re.search(r"/video/([A-Za-z0-9_\-\.]+)", href)
                     or re.search(r"[?&]slug=([A-Za-z0-9_\-\.]+)", href))
                if not m:
                    continue
                slug = m.group(1).lower()
                if slug in seen or slug in ("uncensored", "censored", "amateur", "chinese", "contact", "abuse"):
                    continue

                pic = ""
                if img:
                    pic = img.get("data-src") or img.get("src") or ""
                pic = self._abs(pic)
                if not pic:
                    pic = "https://upload18.cc/v/%s/poster.jpg" % slug.upper()

                title = (title_el.get("title") if title_el else "") or ""
                if not title and title_el:
                    title = title_el.get_text(strip=True)
                if not title and img:
                    title = img.get("alt", "")
                title = re.sub(r"\s+", " ", title or "").strip()
                if not title:
                    title = slug.upper()

                code = ""
                mc = re.match(r"([A-Za-z0-9]+-\d+[A-Za-z0-9]*)", title)
                if mc:
                    code = mc.group(1).upper()

                seen.add(slug)
                out.append({
                    "vod_id": slug,
                    "vod_name": title[:120],
                    "vod_pic": pic,
                    "vod_remarks": code or (slug.upper() if len(slug) < 20 else "123AV"),
                })
            except Exception:
                continue
        return out[:48]

    def homeContent(self, filter=False):
        result = {
            "class": [{"type_id": tid, "type_name": tname} for tid, tname in self.CLASS_MAP],
            "list": [],
            "filters": {},
        }
        html = self._fetch(self.base_url)
        if html:
            result["list"] = self._parse_items(BeautifulSoup(html, "html.parser"))[:40]
        return result

    def homeVideoContent(self):
        return self.homeContent()

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if str(pg).isdigit() else 1
        tid = str(tid or "").strip("/")
        if tid:
            url = "%s/%s?page=%s" % (self.base_url, tid, pg) if pg > 1 else "%s/%s" % (self.base_url, tid)
        else:
            url = "%s/?page=%s" % (self.base_url, pg) if pg > 1 else self.base_url + "/"
        result = {"list": [], "page": pg, "pagecount": 9999, "limit": 24, "total": 999999}
        html = self._fetch(url)
        if not html:
            return result
        soup = BeautifulSoup(html, "html.parser")
        result["list"] = self._parse_items(soup)
        maxpg = pg
        for a in soup.select("a[href*='page=']"):
            m = re.search(r"[?&]page=(\d+)", a.get("href") or "")
            if m:
                n = int(m.group(1))
                if pg <= n < 20000:
                    maxpg = max(maxpg, n)
        result["pagecount"] = maxpg if maxpg > pg else (pg + 1 if result["list"] else pg)
        return result

    def detailContent(self, ids):
        vod_id = ids[0] if isinstance(ids, list) and ids else ids
        slug = str(vod_id).strip()
        m = re.search(r"/video/([A-Za-z0-9_\-\.]+)", slug)
        if m:
            slug = m.group(1)
        slug = slug.strip("/").lower()
        if not slug:
            return {"list": []}

        url = "%s/video/%s" % (self.base_url, slug)
        html = self._fetch(url)
        if not html:
            return {"list": []}
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        title = re.sub(r"\s+", " ", h1.get_text(" ", strip=True)) if h1 else slug.upper()
        if not h1 and soup.title:
            title = re.sub(r"\s*\|\s*123AV.*$", "", soup.title.get_text(strip=True), flags=re.I).strip() or title

        pic = ""
        og = soup.find("meta", property="og:image")
        if og:
            pic = self._abs(og.get("content", ""))
        if not pic:
            pic = "https://upload18.cc/v/%s/poster.jpg" % slug.upper()

        content = ""
        desc = soup.select_one('meta[name="description"]')
        if desc:
            content = desc.get("content") or ""

        # 关键：只下发 iframe，播放时再解析 m3u8（token 新鲜 + Sec-Fetch 头）
        play_url = ""
        ifr = soup.select_one("#player iframe[src]") or soup.find("iframe", src=True)
        if ifr:
            play_url = self._abs(ifr.get("src"))
        if not play_url:
            play_url = "https://upload18.to/play/index/%s" % slug

        eps = "%s$%s" % (slug.upper(), play_url)

        return {"list": [{
            "vod_id": slug,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": content,
            "vod_remarks": slug.upper(),
            "type_name": "JAV",
            "vod_play_from": "123AV",
            "vod_play_url": eps,
        }]}

    def searchContent(self, key, quick=False, pg=1):
        pg = int(pg) if str(pg).isdigit() else 1
        result = {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}
        key = (key or "").strip()
        if not key:
            return result
        url = "%s/search/%s" % (self.base_url, urllib.parse.quote(key))
        if pg > 1:
            url = "%s/search/%s?page=%s" % (self.base_url, urllib.parse.quote(key), pg)
        html = self._fetch(url)
        if not html or ("/video/" not in html and "slug=" not in html):
            html = self._fetch("%s/search?keyword=%s&page=%s" % (
                self.base_url, urllib.parse.quote(key), pg))
        if not html or ("/video/" not in html and "slug=" not in html):
            html = self._fetch("%s/?q=%s" % (self.base_url, urllib.parse.quote(key)))
        if not html:
            return result
        result["list"] = self._parse_items(BeautifulSoup(html, "html.parser"))
        result["total"] = len(result["list"])
        result["pagecount"] = pg + 1 if result["list"] else pg
        return result

    @staticmethod
    def _json_after(html, marker):
        i = html.find(marker)
        if i < 0:
            return {}
        j = html.find("{", i)
        if j < 0:
            return {}
        depth, end = 0, -1
        for k, ch in enumerate(html[j:j + 300000], start=j):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = k + 1
                    break
        if end < 0:
            return {}
        blob = html[j:end]
        try:
            return json.loads(blob)
        except Exception:
            try:
                return json.loads(blob.replace("\\u0026", "&").replace("\\/", "/"))
            except Exception:
                return {}

    def _resolve_m3u8(self, play_page):
        html = self._fetch(play_page, referer=self.base_url + "/")
        if not html:
            return ""
        cfg = self._json_after(html, "window.PLAYER_CONFIG")
        url = (cfg or {}).get("m3u8") or ""
        if not url:
            m = re.search(r"""(?:m3u8|src)\s*[:=]\s*["'](https?://[^"']+?\.m3u8[^"']*)["']""", html)
            if m:
                url = m.group(1)
        if not url:
            m = re.search(r"""(https?://[^\s"'<>\\]+?\.m3u8[^\s"'<>]*)""", html)
            url = m.group(1) if m else ""
        return url.replace("\\u0026", "&").replace("\\/", "/")

    def playerContent(self, flag, id, vipFlags=None):
        play_page = self._abs(id)
        fallback_header = {
            "User-Agent": _UA,
            "Referer": self.base_url + "/",
            "Origin": "https://123av.ink",
        }

        if not play_page:
            return {"parse": 1, "playUrl": "", "url": "", "header": fallback_header}

        if ".m3u8" in play_page or "helvid.com" in play_page:
            return {"parse": 0, "playUrl": "", "url": play_page, "header": dict(self.STREAM_HEADERS)}

        m3u8 = self._resolve_m3u8(play_page)
        if m3u8:
            return {"parse": 0, "playUrl": "", "url": m3u8, "header": dict(self.STREAM_HEADERS)}

        return {"parse": 1, "playUrl": "", "url": play_page, "header": fallback_header}

    def isVideoFormat(self, url):
        url = url or ""
        if re.search(r"\.(m3u8|mp4|ts|flv)(\?|$)", url, re.I):
            return True
        return "helvid.com/m/" in url or "/playlist.m3u8" in url

    def manualVideoCheck(self):
        return False


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("分类:", sp.homeContent())
    d = sp.detailContent(["noskn-106"])
    print(d)
    if d.get("list"):
        play = d["list"][0]["vod_play_url"].split("$")[-1]
        print("player:", sp.playerContent("123AV", play, []))
