# -*- coding: utf-8 -*-
# pornone.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 /{cat}/ /{cat}/{page}/  · 详情 <source> 直链 MP4

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
        self.name = "PornOne"
        self.host = "https://pornone.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.classes = [
            {"type_id": "asian", "type_name": "Asian"},
            {"type_id": "amateur", "type_name": "Amateur"},
            {"type_id": "anal", "type_name": "Anal"},
            {"type_id": "japanese", "type_name": "Japanese"},
            {"type_id": "milf", "type_name": "MILF"},
            {"type_id": "teen", "type_name": "Teen"},
            {"type_id": "lesbian", "type_name": "Lesbian"},
            {"type_id": "blowjob", "type_name": "Blowjob"},
            {"type_id": "big-boobs", "type_name": "Big Boobs"},
            {"type_id": "big-dick", "type_name": "Big Dick"},
            {"type_id": "bbw", "type_name": "BBW"},
            {"type_id": "blonde", "type_name": "Blonde"},
            {"type_id": "brunette", "type_name": "Brunette"},
            {"type_id": "creampie", "type_name": "Creampie"},
            {"type_id": "cumshot", "type_name": "Cumshot"},
            {"type_id": "ebony", "type_name": "Ebony"},
            {"type_id": "hardcore", "type_name": "Hardcore"},
            {"type_id": "interracial", "type_name": "Interracial"},
            {"type_id": "latina", "type_name": "Latina"},
            {"type_id": "massage", "type_name": "Massage"},
            {"type_id": "mature", "type_name": "Mature"},
            {"type_id": "pov", "type_name": "POV"},
            {"type_id": "public", "type_name": "Public"},
            {"type_id": "threesome", "type_name": "Threesome"},
            {"type_id": "gangbang", "type_name": "Gangbang"},
            {"type_id": "hentai", "type_name": "Hentai"},
            {"type_id": "anime", "type_name": "Anime"},
            {"type_id": "chinese", "type_name": "Chinese"},
            {"type_id": "korean", "type_name": "Korean"},
            {"type_id": "arab", "type_name": "Arab"},
            {"type_id": "indian", "type_name": "Indian"},
            {"type_id": "casting", "type_name": "Casting"},
            {"type_id": "compilation", "type_name": "Compilation"},
            {"type_id": "homemade", "type_name": "Homemade"},
            {"type_id": "squirting", "type_name": "Squirting"},
            {"type_id": "bdsm", "type_name": "BDSM"},
            {"type_id": "fetish", "type_name": "Fetish"},
            {"type_id": "cosplay", "type_name": "Cosplay"},
            {"type_id": "office", "type_name": "Office"},
            {"type_id": "school", "type_name": "School"},
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
            html = self.fetch(f"{self.host}/categories/")
            if html:
                dyn = self._parse_categories(html)
                if len(dyn) >= 40:
                    self.classes = dyn
        except Exception:
            pass
        return {"class": self.classes, "filters": {}}

    def homeVideoContent(self):
        try:
            html = self.fetch(self.host + "/")
            return {"list": self._parse_list(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            if pg == "1":
                url = f"{self.host}/{tid}/"
            else:
                url = f"{self.host}/{tid}/{pg}/"
            html = self.fetch(url)
            videos = self._parse_list(html)
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "limit": 36,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[pornone] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 36, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = f"{self.host}/{raw}" if "/" in raw else f"{self.host}/{raw}/"

        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html, "html.parser")

            title = ""
            t = soup.select_one("title")
            if t:
                title = re.sub(r"\s*[—\-|].*$", "", t.get_text()).strip()
            if not title:
                h1 = soup.select_one("h1")
                title = h1.get_text(strip=True) if h1 else raw

            pic = ""
            for prop in ["og:image", "twitter:image"]:
                m = re.search(rf'property=["\']{prop}["\'][^>]+content=["\']([^"\']+)', html)
                if not m:
                    m = re.search(rf'content=["\']([^"\']+)["\'][^>]+property=["\']{prop}', html)
                if m:
                    pic = m.group(1)
                    break
            if not pic:
                for img in soup.select("img"):
                    src = img.get("src") or img.get("data-src") or ""
                    if "/t/" in src and "http" in src:
                        pic = src
                        break

            # 播放源：<source src="...mp4"> 多清晰度
            play_parts = []
            seen = set()
            for m in re.finditer(r'<source[^>]+src=["\']([^"\']+\.mp4[^"\']*)["\']', html, re.I):
                u = m.group(1)
                if u in seen:
                    continue
                seen.add(u)
                # 从文件名提取分辨率
                qm = re.search(r'(\d{3,4})x(\d{3,4})_(\d+)k', u)
                if qm:
                    label = f"{qm.group(2)}p"
                else:
                    label = f"Q{len(play_parts)+1}"
                play_parts.append(f"{label}${u}")
            # 兜底正则 mp4
            if not play_parts:
                for u in re.findall(r'https?://s\d+\.pornone\.com/[^"\'\s<>]+\.mp4[^"\'\s<>]*', html):
                    if u not in seen:
                        seen.add(u)
                        play_parts.append(f"MP4${u}")
            if not play_parts:
                play_parts.append(f"Page${url}")

            # 按清晰度大致排序（数字大的在前）
            def qkey(s):
                m = re.match(r"(\d+)", s)
                return int(m.group(1)) if m else 0
            play_parts.sort(key=qkey, reverse=True)

            vod_id = raw
            mid = re.search(r"/(\d+)/?", url)
            if mid:
                vod_id = mid.group(1)

            return {
                "list": [{
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "PornOne",
                    "vod_play_url": "#".join(play_parts),
                }]
            }
        except Exception as e:
            print(f"[pornone] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        if self.isVideoFormat(id) or "pornone.com" in (id or ""):
            return {
                "parse": 0,
                "url": id,
                "header": json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.host + "/",
                }),
            }
        return {
            "parse": 1,
            "url": id,
            "header": json.dumps({
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
            }),
        }

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            q = parse.quote(key)
            if pg == "1":
                url = f"{self.host}/search/?q={q}"
            else:
                url = f"{self.host}/search/{pg}/?q={q}"
            # 备选路径
            html = self.fetch(url)
            if not html or "videocard" not in html:
                url2 = f"{self.host}/search/{q}/" if pg == "1" else f"{self.host}/search/{q}/{pg}/"
                html = self.fetch(url2)
            return {"list": self._parse_list(html)}
        except Exception as e:
            print(f"[pornone] search error: {e}")
            return {"list": []}

    def localProxy(self, param):
        return [200, "text/plain", ""]

    def fetch(self, url, retry=2):
        import requests
        last_err = None
        for _ in range(retry):
            try:
                resp = requests.get(url, headers=self.headers, timeout=15, verify=False)
                resp.encoding = "utf-8"
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.text
            except Exception as e:
                last_err = e
                time.sleep(0.4)
        print(f"[pornone] fetch fail: {last_err}")
        return ""

    def _parse_categories(self, html):
        cats = []
        soup = BeautifulSoup(html, "html.parser")
        skip = {
            "categories", "tags", "pornstars", "channels", "login", "register",
            "shorts", "gay", "shemale", "search", "upload", "terms", "privacy",
            "dmca", "contact", "faq", "newest", "best", "popular", "2", "3",
            "home", "pornone",
        }
        # 优先：分类页卡片 a.popbop
        nodes = soup.select("a.popbop[href], div.alpha-cont a[href]")
        if not nodes:
            nodes = soup.select("a[href]")
        for a in nodes:
            href = a.get("href") or ""
            m = re.match(r"^(?:https://pornone\.com)?/([a-z0-9-]+)/?$", href)
            if not m:
                continue
            slug = m.group(1)
            if slug in skip or len(slug) < 2:
                continue
            name = ""
            p_el = a.select_one("p")
            if p_el:
                name = p_el.get_text(strip=True)
            if not name:
                drop = a.select_one(".catNameDrop")
                if drop:
                    name = drop.get_text(strip=True)
            if not name:
                alt = a.select_one("img[alt]")
                if alt:
                    name = re.sub(r"^Video category\s*", "", alt.get("alt") or "", flags=re.I).strip()
            if not name:
                name = a.get_text(" ", strip=True)
                parts = name.split()
                if len(parts) >= 2 and len(parts) % 2 == 0 and parts[:len(parts)//2] == parts[len(parts)//2:]:
                    name = " ".join(parts[:len(parts)//2])
            name = re.sub(r"\s*\d[\d,]*\s*$", "", name or "").strip()
            if not name or len(name) > 50:
                name = slug.replace("-", " ").title()
            if slug not in [c["type_id"] for c in cats]:
                cats.append({"type_id": slug, "type_name": name})
        return cats

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")
        seen = set()

        cards = soup.select("a.videocard, a.vidLinkFX")
        for a in cards:
            href = (a.get("href") or "").split("#")[0]
            if not href or not re.search(r"/\d+/?", href):
                continue
            if href.startswith("/"):
                href = self.host + href
            mid = re.search(r"/(\d+)/?$", href.rstrip("/"))
            if not mid:
                mid = re.search(r"/(\d+)/", href)
            if not mid:
                continue
            vod_id = mid.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            # 标题：URL 中 slug
            title = ""
            parts = href.rstrip("/").split("/")
            if len(parts) >= 2:
                slug = parts[-2] if parts[-1].isdigit() else parts[-1]
                if slug and not slug.isdigit():
                    title = slug.replace("-", " ").strip().title()
            if not title:
                title = a.get("title") or f"Video {vod_id}"

            pic = ""
            for img in a.select("img"):
                for k in ("src", "data-src", "data-original"):
                    v = img.get(k) or ""
                    if "http" in v and "/t/" in v and "svg" not in v:
                        pic = v
                        break
                if pic:
                    break
            if not pic:
                # 页面其它位置按 id 匹配
                m = re.search(rf'https://th-[^"\']+/t/\d+/{vod_id}/[^"\']+\.jpg', html)
                if m:
                    pic = m.group(0)

            # 相对路径存完整 path 方便详情
            path = href.replace(self.host, "")
            videos.append({
                "vod_id": path if path.startswith("/") else f"/{path}",
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })

        # 兜底：纯正则
        if not videos:
            for m in re.finditer(r'href="(https://pornone\.com/[a-z0-9-]+/[a-z0-9-]+/(\d+)/)', html):
                href, vod_id = m.group(1), m.group(2)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                slug = href.rstrip("/").split("/")[-2]
                title = slug.replace("-", " ").title()
                pic = ""
                pm = re.search(rf'https://th-[^"\']+/t/\d+/{vod_id}/[^"\']+\.jpg', html)
                if pm:
                    pic = pm.group(0)
                videos.append({
                    "vod_id": href.replace(self.host, ""),
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })
        return videos


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    cat = sp.categoryContent("asian", "1", False, {})
    print("asian", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(" ", v.get("vod_name", "")[:40], "|", (v.get("vod_pic") or "")[:50])
    if cat.get("list"):
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        item = (d.get("list") or [{}])[0]
        print("play", (item.get("vod_play_url") or "")[:150])
