# -*- coding: utf-8 -*-
# 3movs.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 轮海境：分类列表 + flashvars 直链 MP4

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
        self.name = "3Movs"
        self.host = "https://www.3movs.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        # 站点全部 82 个分类（与 /categories/ 一致）
        self.classes = [
            {"type_id": "18-year-old", "type_name": "18 Year Old"},
            {"type_id": "amateur", "type_name": "Amateur"},
            {"type_id": "amateur-teen-18", "type_name": "Amateur Teen 18+"},
            {"type_id": "amateur-threesome", "type_name": "Amateur Threesome"},
            {"type_id": "amateur-wife", "type_name": "Amateur Wife"},
            {"type_id": "anal", "type_name": "Anal"},
            {"type_id": "anal-orgasm", "type_name": "Anal Orgasm"},
            {"type_id": "asian", "type_name": "Asian"},
            {"type_id": "ass", "type_name": "Ass"},
            {"type_id": "ass-fucking", "type_name": "Ass Fucking"},
            {"type_id": "bathroom", "type_name": "Bathroom"},
            {"type_id": "bdsm", "type_name": "BDSM"},
            {"type_id": "beach", "type_name": "Beach"},
            {"type_id": "big-ass", "type_name": "Big Ass"},
            {"type_id": "big-cock", "type_name": "Big Cock"},
            {"type_id": "big-natural-tits", "type_name": "Big Natural Tits"},
            {"type_id": "big-tits", "type_name": "Big Tits"},
            {"type_id": "blowjob", "type_name": "Blowjob"},
            {"type_id": "busty-mom", "type_name": "Busty Mom"},
            {"type_id": "busty-teen-18", "type_name": "Busty Teen 18+"},
            {"type_id": "casting", "type_name": "Casting"},
            {"type_id": "cock-riding", "type_name": "Cock Riding"},
            {"type_id": "compilation", "type_name": "Compilation"},
            {"type_id": "cosplay", "type_name": "Cosplay"},
            {"type_id": "cowgirl", "type_name": "Cowgirl"},
            {"type_id": "cuckold", "type_name": "Cuckold"},
            {"type_id": "cum-in-mouth", "type_name": "Cum In Mouth"},
            {"type_id": "cum-inside", "type_name": "Cum Inside"},
            {"type_id": "cumshot", "type_name": "Cumshot"},
            {"type_id": "czech", "type_name": "Czech"},
            {"type_id": "deepthroat", "type_name": "Deepthroat"},
            {"type_id": "domination", "type_name": "Domination"},
            {"type_id": "double-penetration", "type_name": "Double Penetration"},
            {"type_id": "ebony", "type_name": "Ebony"},
            {"type_id": "extreme", "type_name": "Extreme"},
            {"type_id": "first-time-anal", "type_name": "First Time Anal"},
            {"type_id": "french", "type_name": "French"},
            {"type_id": "gangbang", "type_name": "Gangbang"},
            {"type_id": "german", "type_name": "German"},
            {"type_id": "group", "type_name": "Group"},
            {"type_id": "handjob", "type_name": "Handjob"},
            {"type_id": "hardcore", "type_name": "Hardcore"},
            {"type_id": "homemade", "type_name": "Homemade"},
            {"type_id": "horny-wife", "type_name": "Horny Wife"},
            {"type_id": "huge-boobs", "type_name": "Huge Boobs"},
            {"type_id": "interracial", "type_name": "Interracial"},
            {"type_id": "japanese", "type_name": "Japanese"},
            {"type_id": "kinky", "type_name": "Kinky"},
            {"type_id": "latin", "type_name": "Latin"},
            {"type_id": "lesbian", "type_name": "Lesbian"},
            {"type_id": "lingerie", "type_name": "Lingerie"},
            {"type_id": "massage", "type_name": "Massage"},
            {"type_id": "mature", "type_name": "Mature"},
            {"type_id": "mature-young-18", "type_name": "Mature & Young 18+"},
            {"type_id": "milf", "type_name": "MILF"},
            {"type_id": "mom", "type_name": "Mom"},
            {"type_id": "mom-anal-sex", "type_name": "Mom Anal Sex"},
            {"type_id": "monster-cock", "type_name": "Monster Cock"},
            {"type_id": "monster-tits", "type_name": "Monster Tits"},
            {"type_id": "muffdiving", "type_name": "Muffdiving"},
            {"type_id": "orgasm", "type_name": "Orgasm"},
            {"type_id": "outdoor", "type_name": "Outdoor"},
            {"type_id": "perfect-body", "type_name": "Perfect Body"},
            {"type_id": "pornstar", "type_name": "Pornstar"},
            {"type_id": "pov", "type_name": "POV"},
            {"type_id": "public", "type_name": "Public"},
            {"type_id": "real", "type_name": "Real"},
            {"type_id": "russian", "type_name": "Russian"},
            {"type_id": "slutty-wife", "type_name": "Slutty Wife"},
            {"type_id": "small-tits", "type_name": "Small Tits"},
            {"type_id": "softcore", "type_name": "Softcore"},
            {"type_id": "spanish", "type_name": "Spanish"},
            {"type_id": "squirting", "type_name": "Squirting"},
            {"type_id": "submission", "type_name": "Submission"},
            {"type_id": "surprise", "type_name": "Surprise"},
            {"type_id": "teen", "type_name": "Teens 18+"},
            {"type_id": "threesome", "type_name": "Threesome"},
            {"type_id": "tit-fucking", "type_name": "Tit Fucking"},
            {"type_id": "titjob", "type_name": "Titjob"},
            {"type_id": "toys", "type_name": "Toys"},
            {"type_id": "vintage", "type_name": "Vintage"},
            {"type_id": "voyeur", "type_name": "Voyeur"},
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
        # 启动时再从站点拉一次，保证分类完整
        try:
            html = self.fetch(f"{self.host}/categories/")
            if html:
                dyn = self._parse_categories(html)
                if len(dyn) >= 50:
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
            # 分页：第1页无参数，第2页起 ?from=页码
            if pg == "1":
                url = f"{self.host}/categories/{tid}/"
            else:
                url = f"{self.host}/categories/{tid}/?from={pg}"
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
            print(f"[3movs] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 36, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        # raw 可能是完整 path 或纯 id
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        elif re.match(r"^\d+$", raw):
            url = f"{self.host}/videos/{raw}/"
        else:
            url = f"{self.host}/videos/{raw}" if "/videos/" in raw else f"{self.host}/videos/{raw}/"

        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html, "html.parser")

            title = ""
            t = soup.select_one("title")
            if t:
                title = re.sub(r"\s*-\s*3movs.*$", "", t.get_text(), flags=re.I).strip()
            if not title:
                h1 = soup.select_one("h1")
                title = h1.get_text(strip=True) if h1 else raw

            # 封面
            pic = ""
            m = re.search(r"preview_url\s*:\s*['\"]([^'\"]+)['\"]", html)
            if m:
                pic = m.group(1)
            if not pic:
                for img in soup.select("img"):
                    src = img.get("src") or img.get("data-src") or ""
                    if "videos_screenshots" in src or "preview" in src:
                        pic = src
                        break

            # 播放地址：flashvars
            play_parts = []
            m = re.search(r"video_url\s*:\s*['\"]([^'\"]+)['\"]", html)
            if m:
                play_parts.append(f"HQ${m.group(1)}")
            m = re.search(r"video_alt_url\s*:\s*['\"]([^'\"]+)['\"]", html)
            if m:
                play_parts.append(f"LQ${m.group(1)}")
            # 兜底：页面里的 get_file mp4
            if not play_parts:
                for u in re.findall(r'(https?://[^"\'\s<>]*get_file[^"\'\s<>]+\.mp4[^"\'\s<>]*)', html):
                    if "_lq" in u:
                        play_parts.append(f"LQ${u}")
                    else:
                        play_parts.append(f"HQ${u}")
                    if len(play_parts) >= 2:
                        break
            if not play_parts:
                play_parts.append(f"Page${url}")

            # 去重保序
            seen = set()
            uniq = []
            for p in play_parts:
                if p not in seen:
                    seen.add(p)
                    uniq.append(p)

            vod_id = raw
            mid = re.search(r"/videos/(\d+)/", url)
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
                    "vod_play_from": "3Movs",
                    "vod_play_url": "#".join(uniq),
                }]
            }
        except Exception as e:
            print(f"[3movs] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        if self.isVideoFormat(id) or "get_file" in (id or ""):
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
                url = f"{self.host}/search/{q}/"
            else:
                url = f"{self.host}/search/{q}/?from={pg}"
            html = self.fetch(url)
            return {"list": self._parse_list(html)}
        except Exception as e:
            print(f"[3movs] search error: {e}")
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
                time.sleep(0.5)
        print(f"[3movs] fetch fail: {last_err}")
        return ""


    def _parse_categories(self, html):
        cats = []
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a.th_cat"):
            href = a.get("href") or ""
            m = re.search(r"/categories/([a-z0-9-]+)/?", href)
            if not m:
                continue
            slug = m.group(1)
            title_el = a.select_one(".title")
            if title_el:
                for span in title_el.find_all("span"):
                    span.decompose()
                name = title_el.get_text(strip=True)
            else:
                name = slug.replace("-", " ").title()
            name = re.sub(r"\s+", " ", name or "").strip() or slug.replace("-", " ").title()
            if slug not in [c["type_id"] for c in cats]:
                cats.append({"type_id": slug, "type_name": name})
        return cats

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.select('a[href*="/videos/"]'):
            href = a.get("href") or ""
            m = re.search(r"/videos/(\d+)/([^/]+)?/?", href)
            if not m:
                continue
            vod_id = m.group(1)
            # 跳过导航
            if href.rstrip("/").endswith("/videos"):
                continue

            title = (a.get("title") or "").strip()
            if not title:
                title = a.get_text(strip=True)
            if not title or len(title) < 2:
                continue
            # 过滤纯数字时长之类
            if re.match(r"^\d+[:：]\d+", title):
                continue

            pic = ""
            img = a.select_one("img")
            if img:
                pic = img.get("data-src") or img.get("data-original") or img.get("src") or ""
            if pic.startswith("data:"):
                pic = img.get("data-src") or img.get("data-original") or "" if img else ""
            if not pic:
                parent = a.parent
                if parent:
                    img = parent.select_one("img")
                    if img:
                        pic = img.get("data-src") or img.get("data-original") or img.get("src") or ""
            if pic and pic.startswith("//"):
                pic = "https:" + pic

            videos.append({
                "vod_id": f"{vod_id}/{m.group(2) or ''}".rstrip("/"),
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })

        seen = {}
        for v in videos:
            vid = v["vod_id"].split("/")[0]
            if vid not in seen or (v["vod_pic"] and not seen[vid]["vod_pic"]):
                seen[vid] = v
        return list(seen.values())


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    cat = sp.categoryContent("asian", "1", False, {})
    print("asian count", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(" ", v.get("vod_name", "")[:40], "|", (v.get("vod_pic") or "")[:60])
    if cat.get("list"):
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        print("detail", json.dumps(d, ensure_ascii=False)[:400])
