# -*- coding: utf-8 -*-
# redtube.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 /redtube/{slug}?page=N  · 详情 media/hls|mp4 解析多清晰度

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
        self.name = "RedTube"
        self.host = "https://www.redtube.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.classes = [
            {"type_id": "amateur", "type_name": "Amateur"},
            {"type_id": "anal", "type_name": "Anal"},
            {"type_id": "arab", "type_name": "Arab"},
            {"type_id": "asian", "type_name": "Asian"},
            {"type_id": "bbw", "type_name": "BBW"},
            {"type_id": "bigass", "type_name": "Big Ass"},
            {"type_id": "bigdick", "type_name": "Big Dick"},
            {"type_id": "bigtits", "type_name": "Big Tits"},
            {"type_id": "blonde", "type_name": "Blonde"},
            {"type_id": "blowjob", "type_name": "Blowjob"},
            {"type_id": "bondage", "type_name": "Bondage"},
            {"type_id": "brazilian", "type_name": "Brazilian"},
            {"type_id": "brunette", "type_name": "Brunette"},
            {"type_id": "bukkake", "type_name": "Bukkake"},
            {"type_id": "cartoon", "type_name": "Cartoon"},
            {"type_id": "casting", "type_name": "Casting"},
            {"type_id": "celebrity", "type_name": "Celebrity"},
            {"type_id": "college", "type_name": "College"},
            {"type_id": "compilation", "type_name": "Compilation"},
            {"type_id": "cosplay", "type_name": "Cosplay"},
            {"type_id": "creampie", "type_name": "Creampie"},
            {"type_id": "cuckold", "type_name": "Cuckold"},
            {"type_id": "cumshot", "type_name": "Cumshot"},
            {"type_id": "doublepenetration", "type_name": "Double Penetration"},
            {"type_id": "ebony", "type_name": "Ebony"},
            {"type_id": "european", "type_name": "European"},
            {"type_id": "facials", "type_name": "Facials"},
            {"type_id": "feet", "type_name": "Feet"},
            {"type_id": "femaleorgasm", "type_name": "Female Orgasm"},
            {"type_id": "fetish", "type_name": "Fetish"},
            {"type_id": "fingering", "type_name": "Fingering"},
            {"type_id": "fisting", "type_name": "Fisting"},
            {"type_id": "french", "type_name": "French"},
            {"type_id": "funny", "type_name": "Funny"},
            {"type_id": "gangbang", "type_name": "Gangbang"},
            {"type_id": "german", "type_name": "German"},
            {"type_id": "group", "type_name": "Group"},
            {"type_id": "handjob", "type_name": "Handjob"},
            {"type_id": "hardcore", "type_name": "Hardcore"},
            {"type_id": "hd", "type_name": "HD"},
            {"type_id": "hentai", "type_name": "Hentai"},
            {"type_id": "indian", "type_name": "Indian"},
            {"type_id": "interracial", "type_name": "Interracial"},
            {"type_id": "japanese", "type_name": "Japanese"},
            {"type_id": "latina", "type_name": "Latina"},
            {"type_id": "lesbian", "type_name": "Lesbian"},
            {"type_id": "lingerie", "type_name": "Lingerie"},
            {"type_id": "massage", "type_name": "Massage"},
            {"type_id": "masturbation", "type_name": "Masturbation"},
            {"type_id": "mature", "type_name": "Mature"},
            {"type_id": "milf", "type_name": "MILF"},
            {"type_id": "orgy", "type_name": "Orgy"},
            {"type_id": "parody", "type_name": "Parody"},
            {"type_id": "party", "type_name": "Party"},
            {"type_id": "pissing", "type_name": "Pissing"},
            {"type_id": "popular-with-women", "type_name": "Popular With Women"},
            {"type_id": "pov", "type_name": "POV"},
            {"type_id": "public", "type_name": "Public"},
            {"type_id": "pussy-licking", "type_name": "Pussy Licking"},
            {"type_id": "reality", "type_name": "Reality"},
            {"type_id": "redhead", "type_name": "Redhead"},
            {"type_id": "romantic", "type_name": "Romantic"},
            {"type_id": "rough", "type_name": "Rough"},
            {"type_id": "small-tits", "type_name": "Small Tits"},
            {"type_id": "solomale", "type_name": "Solo Male"},
            {"type_id": "squirting", "type_name": "Squirting"},
            {"type_id": "stepfantasy", "type_name": "Step Fantasy"},
            {"type_id": "striptease", "type_name": "Striptease"},
            {"type_id": "teens", "type_name": "Teens"},
            {"type_id": "threesome", "type_name": "Threesome"},
            {"type_id": "toys", "type_name": "Toys"},
            {"type_id": "transgender", "type_name": "Trans"},
            {"type_id": "verifiedamateurs", "type_name": "Verified Amateurs"},
            {"type_id": "vintage", "type_name": "Vintage"},
            {"type_id": "virtualreality", "type_name": "VR"},
            {"type_id": "webcam", "type_name": "Webcam"},
            {"type_id": "youngandold", "type_name": "Young And Old"},
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
            html = self.fetch(f"{self.host}/categories")
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
                url = f"{self.host}/redtube/{tid}"
            else:
                url = f"{self.host}/redtube/{tid}?page={pg}"
            html = self.fetch(url)
            videos = self._parse_list(html)
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "limit": 40,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[redtube] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 40, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        vid = re.search(r"(\d+)", raw)
        vid = vid.group(1) if vid else raw
        url = f"{self.host}/{vid}"
        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html, "html.parser")

            title = ""
            t = soup.select_one("title")
            if t:
                title = re.sub(r"\s*-\s*RedTube.*$", "", t.get_text(), flags=re.I).strip()
                title = title.replace("&apos;", "'").replace("&#039;", "'")
            if not title:
                h1 = soup.select_one("h1")
                title = h1.get_text(strip=True) if h1 else vid

            pic = ""
            m = re.search(r'"image_url"\s*:\s*"([^"]+)"', html)
            if m:
                pic = m.group(1).replace("\\/", "/")
            if not pic:
                for img in soup.select("img"):
                    src = img.get("src") or img.get("data-src") or ""
                    if "rdtcdn" in src or "phncdn" in src:
                        pic = src
                        break

            play_parts = self._extract_play(html, vid)
            if not play_parts:
                play_parts = [f"Page${url}"]

            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "RedTube",
                    "vod_play_url": "#".join(play_parts),
                }]
            }
        except Exception as e:
            print(f"[redtube] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        if self.isVideoFormat(id) or "rdtcdn.com" in (id or "") or "phncdn.com" in (id or ""):
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
                url = f"{self.host}/?search={q}"
            else:
                url = f"{self.host}/?search={q}&page={pg}"
            html = self.fetch(url)
            return {"list": self._parse_list(html)}
        except Exception as e:
            print(f"[redtube] search error: {e}")
            return {"list": []}


    def _proxy_pic(self, pic):
        """把封面改成走 localProxy，解决 CDN 403 防盗链"""
        if not pic or not pic.startswith("http"):
            return pic or ""
        try:
            # 优先用基类代理地址（蜂蜜影视 / TVBox 会注入）
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base:
                    return f"{base}&url={parse.quote(pic)}"
        except Exception:
            pass
        # 无基类时返回原图（电脑调试仍可看）
        return pic

    def localProxy(self, param):
        """图片防盗链代理：用站点 Referer 拉取封面，避免客户端 403"""
        try:
            import requests
            from urllib import parse as up
            # param 可能是 dict 或已解析
            if isinstance(param, dict):
                url = param.get("url") or param.get("target") or ""
            else:
                url = str(param or "")
            if not url:
                return [400, "text/plain", b"no url"]
            # 兼容二次编码
            for _ in range(2):
                if "%" in url and ("http%" in url.lower() or url.lower().startswith("%")):
                    url = up.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b"bad url"]
            headers = {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            }
            resp = requests.get(url, headers=headers, timeout=12, verify=False)
            ctype = resp.headers.get("Content-Type") or "image/jpeg"
            if resp.status_code != 200:
                return [resp.status_code, "text/plain", resp.content[:200]]
            return [200, ctype, resp.content]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    def _extract_play(self, html, vid):
        """从详情页 mediaDefinitions 拉取 HLS/MP4 多清晰度"""
        parts = []
        try:
            m = re.search(r'"mediaDefinitions"\s*:\s*(\[.*?\])\s*,\s*"', html, re.S)
            if not m:
                return parts
            defs = json.loads(m.group(1))
            hls_path = mp4_path = ""
            for d in defs:
                vu = (d.get("videoUrl") or "").replace("\\/", "/")
                fmt = (d.get("format") or "").lower()
                if fmt == "hls" and vu:
                    hls_path = vu
                elif fmt == "mp4" and vu:
                    mp4_path = vu

            # 优先 HLS（多码率自适应）
            for path, label in ((hls_path, "HLS"), (mp4_path, "MP4")):
                if not path:
                    continue
                api = path if path.startswith("http") else self.host + path
                try:
                    import requests
                    resp = requests.get(api, headers={
                        **self.headers,
                        "Referer": f"{self.host}/{vid}",
                        "Accept": "*/*",
                    }, timeout=12, verify=False)
                    if resp.status_code != 200:
                        continue
                    qualities = resp.json()
                    if not isinstance(qualities, list):
                        continue
                    # 按清晰度从高到低
                    def qkey(x):
                        try:
                            return int(x.get("quality") or x.get("height") or 0)
                        except Exception:
                            return 0
                    qualities = sorted(qualities, key=qkey, reverse=True)
                    for q in qualities:
                        u = (q.get("videoUrl") or "").replace("\\/", "/")
                        if not u:
                            continue
                        qual = str(q.get("quality") or q.get("height") or label)
                        parts.append(f"{qual}p${u}")
                except Exception as e:
                    print(f"[redtube] media api error: {e}")
        except Exception as e:
            print(f"[redtube] extract_play error: {e}")
        # 去重保序
        seen = set()
        out = []
        for p in parts:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

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
        print(f"[redtube] fetch fail: {last_err}")
        return ""

    def _parse_categories(self, html):
        cats = []
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select('a[href*="/redtube/"]'):
            href = a.get("href") or ""
            m = re.search(r"/redtube/([a-z0-9-]+)", href)
            if not m:
                continue
            slug = m.group(1)
            name = a.get_text(strip=True)
            name = re.sub(r"\s*[\d,]+\s*$", "", name).strip()
            if not name or len(name) > 40:
                name = slug.replace("-", " ").title()
            if slug not in [c["type_id"] for c in cats]:
                cats.append({"type_id": slug, "type_name": name})
        return cats

    def _pick_pic(self, img):
        """按优先级取封面，跳过 base64 占位图"""
        if not img:
            return ""
        candidates = []
        for key in ("data-src", "data-o_thumb", "data-mediumthumb", "data-largeThumb",
                    "data-thumb_url", "data-path", "data-srcset", "srcset", "src"):
            v = img.get(key) or ""
            if not v or not isinstance(v, str):
                continue
            # srcset 取第一段
            if "srcset" in key:
                v = v.split(",")[0].strip().split(" ")[0]
            # path 模板去掉 {index}
            if "{index}" in v:
                v = v.replace("{index}", "8")
            candidates.append(v.strip())
        for pic in candidates:
            if not pic or pic.startswith("data:"):
                continue
            if pic.startswith("//"):
                pic = "https:" + pic
            if not pic.startswith("http"):
                continue
            # 过滤明显无效
            if "blank" in pic or "placeholder" in pic:
                continue
            return pic
        return ""

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")

        blocks = soup.select("li.tm_video_block, li.videoblock_list, li.js_thumbContainer")
        if not blocks:
            blocks = soup.select('a.video_link[href^="/"]')

        seen = set()
        for block in blocks:
            a = block if block.name == "a" else block.select_one('a.video_link[href^="/"], a[href^="/"]')
            if not a:
                continue
            href = a.get("href") or ""
            m = re.match(r"^/(\d+)/?$", href.split("?")[0])
            if not m:
                for aa in block.select("a[href^='/']"):
                    mm = re.match(r"^/(\d+)/?$", (aa.get("href") or "").split("?")[0])
                    if mm:
                        m = mm
                        a = aa
                        break
            if not m:
                continue
            vod_id = m.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            title = (a.get("title") or "").strip()
            if not title or re.match(r"^[\d:]+$", title):
                tw = block.select_one(".video_title, .video-title-wrapper a, .title")
                if tw:
                    title = (tw.get("title") or tw.get_text(strip=True) or "").strip()
            if not title or re.match(r"^[\d:]+$", title):
                # 再试 data-title
                title = (block.get("data-title") or "").strip()
            if not title or re.match(r"^[\d:]+$", title):
                continue

            img = None
            if block.name != "a":
                img = block.select_one("img")
            if not img:
                img = a.select_one("img")
            pic = self._pick_pic(img)
            # 块内任意 rdtcdn 兜底
            if not pic:
                for u in re.findall(r'https?://[^"\'\s<>]+(?:rdtcdn|phncdn)[^"\'\s<>]+', str(block)):
                    if "{index}" in u:
                        u = u.replace("{index}", "8")
                    if not u.endswith(".mp4") and "mediabook" not in u:
                        pic = u
                        break

            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })
        return videos


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    cat = sp.categoryContent("asian", "1", False, {})
    print("asian", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(" ", "Y" if v.get("vod_pic") else "N", v.get("vod_name", "")[:50])
    if cat.get("list"):
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        item = (d.get("list") or [{}])[0]
        print("play", (item.get("vod_play_url") or "")[:200])
