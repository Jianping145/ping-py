# -*- coding: utf-8 -*-
# trendyporn.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 /most-recent/ · 分类 /channels/{id}/{slug}/ · 标签 /tag/{slug}/
# 详情 /video/{slug}-{id}.html · 播放：优先嗅探 + mp4/m3u8 直链

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
        self.name = "TrendyPorn"
        self.host = "https://www.trendyporn.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        # channels/{id}/{slug}/  来自站点分类页 + 详情页链接
        self.cat_map = {
            "newest": "most-recent",
            "amateur": "1/amateur",
            "anal": "3/anal",
            "asian": "4/asian",
            "ass": "5/ass",
            "bbw": "6/bbw",
            "bdsm": "7/bdsm",
            "blonde": "8/blonde",
            "blowjobs": "9/blowjobs",
            "british": "10/british",
            "bukkake": "11/bukkake",
            "cartoons": "12/cartoons",
            "celebrity": "13/celebrity",
            "chinese": "14/chinese",
            "couples": "15/couples",
            "deepthroat": "16/deepthroat",
            "desi": "17/desi",
            "dildos": "18/dildos",
            "ebony": "19/ebony",
            "femdom": "20/femdom",
            "flashing": "21/flashing",
            "gangbang": "22/gangbang",
            "gay": "23/gay",
            "girlfriend": "24/girlfriend",
            "hardcore": "25/hardcore",
            "hentai": "26/hentai",
            "hidden-cams": "27/hidden-cams",
            "home-made": "28/home-made",
            "indian": "29/indian",
            "indonesian": "30/indonesian",
            "interracial": "31/interracial",
            "japanese": "32/japanese",
            "kissing": "33/kissing",
            "korean": "34/korean",
            "lesbians": "35/lesbians",
            "massage": "36/massage",
            "milf": "37/milf",
            "nipples": "38/nipples",
            "pornstars": "54/pornstars",
            "pov": "55/pov",
            "public": "56/public",
            "pussy": "47/pussy",
            "russian": "48/russian",
            "shemale": "49/shemale",
            "showers": "50/showers",
            "teen": "51/teen",
            "tits": "52/tits",
            "toys": "42/toys",
            "vintage": "53/vintage",
            "webcams": "57/webcams",
            "wife": "58/wife",
            "group-sex": "59/group-sex",
            "hairy": "60/hairy",
            "handjobs": "61/handjobs",
            "hd": "62/hd",
            "close-ups": "63/close-ups",
        }
        self.classes = [
            {"type_id": "newest", "type_name": "最新"},
        ] + [
            {"type_id": k, "type_name": k.replace("-", " ").title()}
            for k in self.cat_map
            if k != "newest"
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
            html = self.fetch(self.host + "/channels/")
            dyn = self._parse_channels(html)
            if dyn and len(dyn) >= 10:
                self.classes = [{"type_id": "newest", "type_name": "最新"}] + dyn
        except Exception as e:
            print(f"[trendyporn] home cats: {e}")
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            tid = (tid or "newest").strip("/")
            url = self._build_list_url(tid, pg)
            videos = self._parse_list(self.fetch(url))
            if not videos and tid not in ("newest", "most-recent"):
                # 兜底：按名字搜索
                q = parse.quote(re.sub(r"^\d+/", "", tid).replace("-", " "))
                alt = f"{self.host}/search/{q}/" if pg == "1" else f"{self.host}/search/{q}/page{pg}.html"
                videos = self._parse_list(self.fetch(alt))
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "pageCount": 9999 if videos else int(pg),
                "limit": 36,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[trendyporn] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "pageCount": 1, "limit": 36, "total": 0}

    def _build_list_url(self, tid, pg):
        tid = (tid or "newest").strip()
        if tid in ("newest", "most-recent", ""):
            if pg == "1":
                return f"{self.host}/most-recent/"
            return f"{self.host}/most-recent/page{pg}.html"
        # 已是 channels/id/slug 或 id/slug
        if tid.startswith("channels/"):
            path = tid
        elif re.match(r"^\d+/[a-z0-9-]+$", tid):
            path = "channels/" + tid
        elif tid.startswith("tag/"):
            path = tid
        else:
            mapped = self.cat_map.get(tid, tid)
            if mapped == "most-recent":
                if pg == "1":
                    return f"{self.host}/most-recent/"
                return f"{self.host}/most-recent/page{pg}.html"
            if re.match(r"^\d+/[a-z0-9-]+$", mapped):
                path = "channels/" + mapped
            elif mapped.startswith("tag/"):
                path = mapped
            else:
                path = "tag/" + mapped
        if pg == "1":
            return f"{self.host}/{path}/"
        # 分页：/channels/3/anal/page2.html 或 /tag/milf/page2.html
        return f"{self.host}/{path.rstrip('/')}/page{pg}.html"

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = self.host + "/" + raw.lstrip("/")
        if not url.endswith(".html") and "/video/" in url and not url.endswith("/"):
            pass
        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html or "", "html.parser")

            title = ""
            h1 = soup.select_one("h1")
            if h1:
                title = h1.get_text(strip=True)
            if not title:
                ogt = re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html or "", re.I)
                if ogt:
                    title = ogt.group(1).strip()
            if not title and soup.title:
                title = re.sub(r"\s*[-|].*$", "", soup.title.get_text()).strip()
            if not title:
                slug = url.rstrip("/").split("/")[-1].replace(".html", "")
                slug = re.sub(r"-\d+$", "", slug)
                title = slug.replace("-", " ").title()

            pic = ""
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html or "", re.I)
            if not m:
                m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html or "", re.I)
            if m:
                pic = m.group(1)

            play_parts = []
            seen = set()

            def add(name, u):
                if not u or u in seen:
                    return
                if not u.startswith("http"):
                    return
                ul = u.lower()
                if any(x in ul for x in ("preview", "trailer", "sample", "teaser", "thumb", "sprite")):
                    return
                seen.add(u)
                play_parts.append(f"{name}${u}")

            for src in re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', html or "", re.I):
                if self.isVideoFormat(src):
                    add("HD", src)
            for src in re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', html or "", re.I):
                if self.isVideoFormat(src):
                    add("HD", src)
            for pat in [
                r'contentUrl["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']',
                r'["\']file["\']\s*:\s*["\'](https?://[^"\']+)["\']',
                r'videoUrl["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']',
                r'["\']src["\']\s*:\s*["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']',
            ]:
                for src in re.findall(pat, html or "", re.I):
                    src = src.replace("\\/", "/")
                    if self.isVideoFormat(src):
                        add("HD", src)
            for src in re.findall(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', (html or "").replace("\\/", "/")):
                add("HLS", src)
            mp4s = re.findall(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', (html or "").replace("\\/", "/"))
            for src in mp4s[:3]:
                if any(x in src.lower() for x in ("/thumb", "/cover", "/poster", "preview")):
                    continue
                add("MP4", src)
            for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html or "", re.I):
                if iframe.startswith("//"):
                    iframe = "https:" + iframe
                if iframe.startswith("http") and "ad" not in iframe.lower():
                    add("Embed", iframe)

            # 直链优先，嗅探放最后兜底
            final = list(play_parts)
            sniff = f"嗅探${url}"
            if sniff not in final:
                final.append(sniff)
            if not play_parts:
                final = [sniff, f"Page${url}"]

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
                    "vod_play_from": "TrendyPorn",
                    "vod_play_url": "#".join(final),
                }]
            }
        except Exception as e:
            print(f"[trendyporn] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
        }
        headers_json = json.dumps(headers)
        if not id:
            return {"parse": 1, "url": self.host, "header": headers_json}

        # 已是直链 → 直接播
        if self.isVideoFormat(id):
            if any(x in id.lower() for x in ("preview", "trailer", "sample", "teaser")):
                return {"parse": 1, "jx": 0, "url": self.host, "header": headers_json}
            return {"parse": 0, "jx": 0, "url": id, "header": headers_json}

        page = id if id.startswith("http") else self.host + (id if id.startswith("/") else "/" + id)
        headers["Referer"] = page
        headers_json = json.dumps(headers)

        # 重新抓详情，优先直链
        try:
            html = self.fetch(page)
            candidates = []
            for src in re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', html or "", re.I):
                if self.isVideoFormat(src):
                    candidates.append(src)
            for src in re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', html or "", re.I):
                if self.isVideoFormat(src):
                    candidates.append(src)
            for pat in [
                r'contentUrl["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']',
                r'["\']file["\']\s*:\s*["\'](https?://[^"\']+)["\']',
                r'videoUrl["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']',
                r'["\']src["\']\s*:\s*["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']',
            ]:
                for src in re.findall(pat, html or "", re.I):
                    candidates.append(src.replace("\\/", "/"))
            for src in re.findall(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', (html or "").replace("\\/", "/")):
                candidates.append(src)
            for src in re.findall(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', (html or "").replace("\\/", "/")):
                candidates.append(src)

            seen = set()
            ordered = []
            for c in candidates:
                if not c or not c.startswith("http") or c in seen:
                    continue
                if any(x in c.lower() for x in ("preview", "trailer", "sample", "teaser", "/thumb", "/cover", "sprite")):
                    continue
                if not self.isVideoFormat(c):
                    continue
                seen.add(c)
                ordered.append(c)
            # m3u8 / high 优先
            ordered.sort(key=lambda u: (0 if ".m3u8" in u.lower() else 1, 0 if "high" in u.lower() else 1))
            if ordered:
                return {"parse": 0, "jx": 0, "url": ordered[0], "header": headers_json}

            for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html or "", re.I):
                if iframe.startswith("//"):
                    iframe = "https:" + iframe
                if iframe.startswith("http") and "ad" not in iframe.lower():
                    # 嵌入页仍可能需嗅探
                    return {"parse": 1, "jx": 0, "url": iframe, "header": headers_json}
        except Exception as e:
            print(f"[trendyporn] play extract: {e}")

        # 无直链时才嗅探
        return {"parse": 1, "jx": 0, "url": page, "header": headers_json}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            q = parse.quote(key.strip().replace(" ", "-"))
            # 站点搜索 /search/keyword/ 与 /search/keyword/page2.html
            url = f"{self.host}/search/{q}/" if pg == "1" else f"{self.host}/search/{q}/page{pg}.html"
            videos = self._parse_list(self.fetch(url))
            if not videos:
                q2 = parse.quote(key)
                alt = f"{self.host}/search/{q2}/" if pg == "1" else f"{self.host}/search/{q2}/page{pg}.html"
                if alt != url:
                    videos = self._parse_list(self.fetch(alt))
            return {"list": videos}
        except Exception as e:
            print(f"[trendyporn] search error: {e}")
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
            elif body[:4] == b"RIFF" and body[8:12] == b"WEBP":
                ctype = "image/webp"
            elif b"#EXTM3U" in body[:50]:
                ctype = "application/vnd.apple.mpegurl"
            elif url.lower().endswith(".mp4"):
                ctype = "video/mp4"
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
                if resp.status_code == 200 and len(resp.text) > 300:
                    return resp.text
                last_err = f"status={resp.status_code}"
            except Exception as e:
                last_err = e
                time.sleep(0.2)
        print(f"[trendyporn] fetch fail: {url} {last_err}")
        return ""

    def _parse_channels(self, html):
        """从 /channels/ 解析分类"""
        if not html:
            return []
        out = []
        seen = set()
        for m in re.finditer(
            r'href="((?:https?://(?:www\.)?trendyporn\.com)?/channels/(\d+)/([a-z0-9-]+)/?)"[^>]*>([^<]{2,40})<',
            html,
            re.I,
        ):
            cid, slug, name = m.group(2), m.group(3).lower(), re.sub(r"\s+", " ", m.group(4)).strip()
            path = f"{cid}/{slug}"
            if path in seen:
                continue
            seen.add(path)
            if not name:
                name = slug.replace("-", " ").title()
            out.append({"type_id": path, "type_name": name[:40]})
        # 宽松：只有 channels/id/slug
        if len(out) < 10:
            for m in re.finditer(r"/channels/(\d+)/([a-z0-9-]+)/?", html, re.I):
                path = f"{m.group(1)}/{m.group(2).lower()}"
                if path in seen:
                    continue
                seen.add(path)
                out.append({
                    "type_id": path,
                    "type_name": m.group(2).replace("-", " ").title()[:40],
                })
        return out

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        seen = set()
        soup = BeautifulSoup(html or "", "html.parser")

        def norm_pic(u):
            if not u:
                return ""
            u = u.strip().replace("&amp;", "&").replace("\\/", "/")
            if u.startswith("//"):
                u = "https:" + u
            if u.startswith("/"):
                u = self.host + u
            if not u.startswith("http") or u.lower().startswith("data:"):
                return ""
            ul = u.lower()
            if any(x in ul for x in ("flag", "sprite", "icon", "logo", "placeholder", "1x1", "pixel", "loading", "spinner")):
                return ""
            return u

        def from_anchor(a, block_text=""):
            href = a.get("href") or ""
            m = re.search(r"/video/([a-z0-9-]+-\d+)\.html", href, re.I)
            if not m:
                return None
            path = "/video/" + m.group(1) + ".html"
            if path in seen:
                return None
            title = (a.get("title") or "").strip()
            if not title or len(title) < 3:
                img = a.select_one("img")
                if img:
                    title = (img.get("alt") or "").strip()
            if not title or len(title) < 3:
                title = a.get_text(" ", strip=True)
            title = re.sub(r"\s+", " ", title).strip()
            if not title or len(title) < 3:
                slug = re.sub(r"-\d+$", "", m.group(1))
                title = slug.replace("-", " ").title()
            if title.lower() in ("more", "next", "prev", "live models"):
                return None

            pic = ""
            for img in a.select("img"):
                for attr in ("data-src", "data-original", "data-lazy-src", "data-poster", "src"):
                    cand = (img.get(attr) or "").strip()
                    if cand and not cand.startswith("data:"):
                        pic = norm_pic(cand)
                        if pic:
                            break
                if pic:
                    break
            if not pic and a.parent:
                for img in a.parent.select("img"):
                    for attr in ("data-src", "data-original", "src"):
                        cand = (img.get(attr) or "").strip()
                        if cand and not cand.startswith("data:"):
                            pic = norm_pic(cand)
                            if pic:
                                break
                    if pic:
                        break

            remarks = ""
            blob = block_text or (a.parent.get_text(" ", strip=True) if a.parent else "")
            mm = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?|\d+\s*min)", blob, re.I)
            if mm:
                remarks = mm.group(1)

            seen.add(path)
            return {
                "vod_id": path,
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic) if pic else "",
                "vod_remarks": remarks,
            }

        # 卡片
        for block in soup.select(".item, .thumb, .video, article, .post, .thumb-block, li"):
            a = block.select_one('a[href*="/video/"]')
            if not a:
                continue
            item = from_anchor(a, block.get_text(" ", strip=True))
            if item:
                videos.append(item)

        # 全页链接
        if len(videos) < 8:
            for a in soup.select('a[href*="/video/"]'):
                item = from_anchor(a)
                if item:
                    videos.append(item)

        # 正则兜底
        if len(videos) < 5:
            for m in re.finditer(
                r'href="((?:https?://(?:www\.)?trendyporn\.com)?/video/([a-z0-9-]+-\d+)\.html)"',
                html or "",
                re.I,
            ):
                path = "/video/" + m.group(2) + ".html"
                if path in seen:
                    continue
                window = (html or "")[max(0, m.start() - 200): m.end() + 500]
                title = re.sub(r"-\d+$", "", m.group(2)).replace("-", " ").title()
                mt = re.search(r'(?:title|alt)="([^"]{3,100})"', window, re.I)
                if mt:
                    title = mt.group(1).strip()
                pic = ""
                mp = re.search(
                    r'(?:data-src|data-original|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    window,
                    re.I,
                )
                if mp:
                    pic = norm_pic(mp.group(1))
                remarks = ""
                md = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", window)
                if md:
                    remarks = md.group(1)
                seen.add(path)
                videos.append({
                    "vod_id": path,
                    "vod_name": title[:120],
                    "vod_pic": self._proxy_pic(pic) if pic else "",
                    "vod_remarks": remarks,
                })
        return videos


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    print("url newest", sp._build_list_url("newest", "1"))
    print("url milf", sp._build_list_url("milf", "2"))
    print("url anal", sp._build_list_url("anal", "1"))
