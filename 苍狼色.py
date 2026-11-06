# -*- coding: utf-8 -*-
# 苍狼色视频 clssp2.xyz  蜂蜜影视(FongMi) / TVBox Python Spider
# 分类 /vodtype/{id}.html · 分页 /vodtype/{id}-{pg}.html
# 详情 /{id}.html · 搜索 /s/index.html?wd= 或 /s/{kw}.html
# 播放：直链优先 + 嗅探兜底

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
        self.name = "苍狼色视频"
        self.host = "https://www.clssp2.xyz"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.classes = [
            {"type_id": "home", "type_name": "首页"},
            {"type_id": "20", "type_name": "主播网红"},
            {"type_id": "21", "type_name": "偷拍自拍"},
            {"type_id": "22", "type_name": "人妻熟女"},
            {"type_id": "23", "type_name": "强奸乱伦"},
            {"type_id": "24", "type_name": "制服丝袜"},
            {"type_id": "25", "type_name": "自慰变态"},
            {"type_id": "26", "type_name": "国产精品"},
            {"type_id": "27", "type_name": "亚洲情色"},
            {"type_id": "28", "type_name": "卡通动漫"},
            {"type_id": "29", "type_name": "三级伦理"},
            {"type_id": "30", "type_name": "欧美精品"},
            {"type_id": "label/new", "type_name": "最新上传"},
            {"type_id": "label/hot", "type_name": "总排行"},
            {"type_id": "label/hot_day", "type_name": "日排行"},
            {"type_id": "label/hot_week", "type_name": "周排行"},
            {"type_id": "label/hot_month", "type_name": "月排行"},
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
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/cn/home/web/"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            tid = (tid or "home").strip()
            url = self._build_list_url(tid, pg)
            videos = self._parse_list(self.fetch(url))
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "pageCount": 9999 if videos else int(pg),
                "limit": 36,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[canglang] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "pageCount": 1, "limit": 36, "total": 0}

    def _build_list_url(self, tid, pg):
        tid = (tid or "home").strip("/")
        if tid in ("home", "index", ""):
            return self.host + "/cn/home/web/"
        if tid.startswith("label/"):
            # /label/hot.html · 分页因站点而异，先同页
            base = tid if tid.endswith(".html") else tid + ".html"
            return f"{self.host}/{base}"
        # 数字分类 /vodtype/20.html · /vodtype/20-2.html
        if re.match(r"^\d+$", tid):
            if pg == "1":
                return f"{self.host}/vodtype/{tid}.html"
            return f"{self.host}/vodtype/{tid}-{pg}.html"
        if tid.startswith("vodtype/"):
            return f"{self.host}/{tid}" if tid.endswith(".html") else f"{self.host}/{tid}.html"
        return f"{self.host}/vodtype/{tid}.html"

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = self.host + "/" + raw.lstrip("/")
        if not url.endswith(".html") and re.search(r"/\d+$", url):
            url = url + ".html"

        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html or "", "html.parser")

            title = ""
            h1 = soup.select_one("h1")
            if h1:
                title = h1.get_text(strip=True)
            if not title:
                og = re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html or "", re.I)
                if og:
                    title = og.group(1).strip()
            if not title and soup.title:
                title = re.sub(r"\s*[-|_].*$", "", soup.title.get_text()).strip()
            if not title:
                title = re.sub(r"\.html$", "", url.rstrip("/").split("/")[-1])

            pic = ""
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html or "", re.I)
            if m:
                pic = m.group(1)
            if not pic:
                img = soup.select_one(".detail-pic img, .vod-pic img, .thumb img, img.lazy-load")
                if img:
                    pic = img.get("data-src") or img.get("src") or ""

            play_parts = []
            seen = set()

            def add(name, u):
                if not u or u in seen:
                    return
                u = u.replace("\\/", "/").strip()
                if not u.startswith("http"):
                    return
                if any(x in u.lower() for x in ("preview", "trailer", "sample", "/thumb", "sprite")):
                    return
                seen.add(u)
                play_parts.append(f"{name}${u}")

            # 苹果 CMS 常见 player_aaaa / MacPlayer
            for m in re.finditer(
                r'player_[a-z0-9]+\s*=\s*(\{.+?\})\s*;',
                html or "",
                re.S | re.I,
            ):
                try:
                    blob = m.group(1)
                    um = re.search(r'"url"\s*:\s*"([^"]+)"', blob)
                    if um:
                        u = um.group(1).replace("\\/", "/")
                        if self.isVideoFormat(u) or "http" in u:
                            add("线路", u)
                except Exception:
                    pass

            for pat in [
                r'"url"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"',
                r'"url"\s*:\s*"(https?://[^"]+\.mp4[^"]*)"',
                r'url\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'url\s*:\s*["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
                r'video_url\s*[:=]\s*["\'](https?://[^"\']+)["\']',
                r'<source[^>]+src=["\']([^"\']+)["\']',
            ]:
                for src in re.findall(pat, html or "", re.I):
                    src = src.replace("\\/", "/")
                    if self.isVideoFormat(src) or src.startswith("http"):
                        add("直链", src)

            for src in re.findall(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', (html or "").replace("\\/", "/")):
                add("HLS", src)
            for src in re.findall(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', (html or "").replace("\\/", "/")):
                if "/thumb" in src.lower() or "preview" in src.lower():
                    continue
                add("MP4", src)

            # 多线路 from 苹果CMS 播放列表
            for m in re.finditer(r'(\w+)\$?(https?://[^\s"\'#<>]+(?:\.m3u8|\.mp4)[^\s"\'#<>]*)', html or ""):
                add(m.group(1)[:20] or "线路", m.group(2))

            # 高码率排前
            def _qscore(part):
                u = part.split("$")[-1].lower() if "$" in part else part.lower()
                s = 0
                if "2000kb" in u or "1080" in u:
                    s += 100
                if "1500kb" in u or "720" in u:
                    s += 80
                if "/hls/" in u:
                    s += 20
                if ".m3u8" in u:
                    s += 10
                return -s
            play_parts.sort(key=_qscore)
            final = list(play_parts)
            final.append(f"嗅探${url}")

            return {
                "list": [{
                    "vod_id": url.replace(self.host, ""),
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "苍狼",
                    "vod_play_url": "#".join(final),
                }]
            }
        except Exception as e:
            print(f"[canglang] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        headers_json = json.dumps(headers)
        if not id:
            return {"parse": 1, "url": self.host, "header": headers_json}

        # 已是 m3u8/mp4 直链
        if self.isVideoFormat(id):
            # CDN 域名用自身作 Referer 更稳
            try:
                from urllib.parse import urlparse
                host = urlparse(id).scheme + "://" + urlparse(id).netloc + "/"
                headers["Referer"] = host
                headers["Origin"] = urlparse(id).scheme + "://" + urlparse(id).netloc
            except Exception:
                pass
            headers_json = json.dumps(headers)
            return {"parse": 0, "jx": 0, "url": id, "header": headers_json}

        page = id if id.startswith("http") else self.host + (id if id.startswith("/") else "/" + id)
        if not page.endswith(".html") and re.search(r"/\d+$", page):
            page += ".html"
        headers["Referer"] = page
        headers_json = json.dumps(headers)

        try:
            html = self.fetch(page)
            candidates = []
            # 苹果CMS player 对象
            for m in re.finditer(r'player_[a-z0-9]+\s*=\s*(\{.+?\})\s*;', html or "", re.S | re.I):
                um = re.search(r'"url"\s*:\s*"([^"]+)"', m.group(1))
                if um:
                    candidates.append(um.group(1).replace("\\/", "/"))
            for src in re.findall(r'"url"\s*:\s*"(https?://[^"]+)"', html or ""):
                candidates.append(src.replace("\\/", "/"))
            for src in re.findall(
                r'https?://[^"\'\s<>]+\.(?:m3u8|mp4)[^"\'\s<>]*',
                (html or "").replace("\\/", "/"),
            ):
                candidates.append(src)

            seen = set()
            ordered = []
            for c in candidates:
                if not c or not c.startswith("http") or c in seen:
                    continue
                if any(x in c.lower() for x in ("preview", "trailer", "/thumb", "sprite", "sample")):
                    continue
                if not self.isVideoFormat(c):
                    continue
                seen.add(c)
                ordered.append(c)

            # 码率优先：2000kb/1080/720 > 普通 index.m3u8 > mp4
            def score(u):
                ul = u.lower()
                s = 0
                if "2000kb" in ul or "1080" in ul or "hd" in ul:
                    s += 100
                if "1500kb" in ul or "720" in ul:
                    s += 80
                if "1000kb" in ul or "480" in ul:
                    s += 50
                if "/hls/" in ul:
                    s += 20
                if ".m3u8" in ul:
                    s += 10
                if ul.rstrip("/").endswith("index.m3u8") and "/hls/" not in ul:
                    s -= 5  # 根 index 可能是多码率 master，仍可用但略降
                return -s  # 越小越优先（sort 升序）

            ordered.sort(key=score)
            if ordered:
                best = ordered[0]
                try:
                    from urllib.parse import urlparse
                    ph = urlparse(best)
                    headers["Referer"] = ph.scheme + "://" + ph.netloc + "/"
                    headers["Origin"] = ph.scheme + "://" + ph.netloc
                    headers_json = json.dumps(headers)
                except Exception:
                    pass
                return {"parse": 0, "jx": 0, "url": best, "header": headers_json}
        except Exception as e:
            print(f"[canglang] play: {e}")

        return {"parse": 1, "jx": 0, "url": page, "header": headers_json}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            q = parse.quote(key.strip())
            # /s/index.html?wd= 与 /s/关键词.html
            url = f"{self.host}/s/index.html?wd={q}"
            if pg != "1":
                url = f"{self.host}/s/index.html?wd={q}&page={pg}"
            videos = self._parse_list(self.fetch(url))
            if not videos:
                alt = f"{self.host}/s/{q}.html"
                videos = self._parse_list(self.fetch(alt))
            return {"list": videos}
        except Exception as e:
            print(f"[canglang] search error: {e}")
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
            }, timeout=20, verify=False)
            if resp.status_code != 200 or not resp.content:
                return [resp.status_code, "text/plain", (resp.content or b"")[:200]]
            body = resp.content
            ctype = "image/jpeg"
            if body[:3] == b"\xff\xd8\xff":
                ctype = "image/jpeg"
            elif body[:8] == b"\x89PNG\r\n\x1a\n":
                ctype = "image/png"
            elif body[:4] == b"RIFF":
                ctype = "image/webp"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        if pic.startswith("/"):
            pic = self.host + pic
        if not pic.startswith("http"):
            return pic
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base:
                    return f"{base}&url={parse.quote(pic)}"
        except Exception:
            pass
        return pic

    def fetch(self, url, retry=2):
        import requests
        last_err = None
        for _ in range(retry):
            try:
                resp = requests.get(url, headers=self.headers, timeout=15, verify=False)
                resp.encoding = "utf-8"
                if resp.status_code == 200 and len(resp.text) > 200:
                    return resp.text
                last_err = f"status={resp.status_code}"
            except Exception as e:
                last_err = e
                time.sleep(0.2)
        print(f"[canglang] fetch fail: {url} {last_err}")
        return ""

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        seen = set()
        soup = BeautifulSoup(html or "", "html.parser")

        def norm_pic(u):
            if not u:
                return ""
            u = u.strip().replace("&amp;", "&")
            if u.startswith("//"):
                u = "https:" + u
            if u.startswith("/"):
                u = self.host + u
            if not u.startswith("http") or u.startswith("data:"):
                return ""
            return u

        def is_video_href(href):
            """只要纯数字详情页 /123456.html，排除 /vodtype/20.html 等分类"""
            if not href:
                return False
            href = href.split("?")[0].strip()
            # 排除分类、标签、搜索、分页
            low = href.lower()
            if any(x in low for x in (
                "/vodtype/", "/label/", "/s/", "/type/", "/show/",
                "/index", "/page/", "/actor/", "/plot/", "/cn/home",
            )):
                return False
            # 纯 /数字.html ，且数字至少 5 位（短数字多半是分类）
            m = re.search(r"(?:https?://[^/]+)?/(\d{5,})\.html/?$", href)
            return bool(m)

        def add_item(vid, title, pic, remarks=""):
            if not vid or vid in seen:
                return
            if not re.match(r"^/\d{5,}\.html$", vid):
                return
            seen.add(vid)
            if not title or len(title) < 2:
                return
            # 排除导航文字
            if title in (
                "首页", "主播网红", "偷拍自拍", "人妻熟女", "强奸乱伦", "制服丝袜",
                "自慰变态", "国产精品", "亚洲情色", "卡通动漫", "三级伦理", "欧美精品",
                "最新上传", "总排行榜", "月排行榜", "周排行榜", "日排行榜",
            ):
                return
            videos.append({
                "vod_id": vid,
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic) if pic else "",
                "vod_remarks": remarks,
            })

        for item in soup.select(".item, .video-item, .col-md-2, .stui-vodlist__box, li, .list-videos .item"):
            a = item.select_one("a[href]")
            if not a:
                continue
            href = a.get("href") or ""
            if not is_video_href(href):
                continue
            m = re.search(r"/(\d{5,})\.html", href)
            if not m:
                continue
            vid = "/" + m.group(1) + ".html"
            title = (a.get("title") or "").strip()
            if not title:
                tnode = item.select_one(".title, strong.title, .vod-title, h3, h4, strong")
                if tnode:
                    title = tnode.get_text(strip=True)
            if not title:
                title = a.get_text(" ", strip=True)
            title = re.sub(r"\s+", " ", title).strip()
            pic = ""
            img = item.select_one("img")
            if img:
                pic = norm_pic(
                    img.get("data-src")
                    or img.get("data-original")
                    or img.get("data-lazy-src")
                    or img.get("src")
                    or ""
                )
            remarks = ""
            rnode = item.select_one(".rating, .views, .pic-text, .text-right, .is-hd")
            if rnode:
                remarks = rnode.get_text(strip=True)[:20]
            add_item(vid, title, pic, remarks)

        # 正则兜底：只匹配 title= 的视频卡片，排除 vodtype
        if len(videos) < 5:
            for m in re.finditer(
                r'href="(/(\d{5,})\.html)"[^>]*title="([^"]{2,120})"',
                html or "",
                re.I,
            ):
                vid = m.group(1)
                title = m.group(3).strip()
                window = (html or "")[max(0, m.start() - 80): m.start() + 700]
                if "/vodtype/" in window[:80]:
                    continue
                pic = ""
                pm = re.search(
                    r'(?:data-src|data-original|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    window,
                    re.I,
                )
                if pm:
                    pic = norm_pic(pm.group(1))
                add_item(vid, title, pic)

        if len(videos) < 5:
            for m in re.finditer(
                r'<a[^>]+href="(/(\d{5,})\.html)"[^>]*>[\s\S]{0,400}?<img[^>]+(?:data-src|src)="([^"]+)"[\s\S]{0,300}?<strong[^>]*class="title"[^>]*>([^<]+)',
                html or "",
                re.I,
            ):
                add_item(m.group(1), m.group(4).strip(), norm_pic(m.group(3)))

        return videos



if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    print("url", sp._build_list_url("20", "1"))
    print("url2", sp._build_list_url("20", "2"))
    print("home", sp._build_list_url("home", "1"))
