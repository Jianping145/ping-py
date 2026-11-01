# -*- coding: utf-8 -*-
# pornhat.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 /popular/N/  /tags/xxx/N/  · 详情 get_file 多清晰度 MP4

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
        self.name = "PornHat"
        self.host = "https://www.pornhat.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.classes = [
            {"type_id": "popular", "type_name": "Popular"},
            {"type_id": "trending", "type_name": "Trending"},
            {"type_id": "channels", "type_name": "Channels"},
            {"type_id": "models", "type_name": "Models"},
            {"type_id": "tags/asian", "type_name": "Asian"},
            {"type_id": "tags/japanese", "type_name": "Japanese"},
            {"type_id": "tags/chinese", "type_name": "Chinese"},
            {"type_id": "tags/korean", "type_name": "Korean"},
            {"type_id": "tags/amateur", "type_name": "Amateur"},
            {"type_id": "tags/anal", "type_name": "Anal"},
            {"type_id": "tags/milf", "type_name": "MILF"},
            {"type_id": "tags/teen-18", "type_name": "Teen"},
            {"type_id": "tags/lesbian", "type_name": "Lesbian"},
            {"type_id": "tags/blowjob", "type_name": "Blowjob"},
            {"type_id": "tags/big-tits", "type_name": "Big Tits"},
            {"type_id": "tags/big-ass", "type_name": "Big Ass"},
            {"type_id": "tags/blonde", "type_name": "Blonde"},
            {"type_id": "tags/brunette", "type_name": "Brunette"},
            {"type_id": "tags/ebony", "type_name": "Ebony"},
            {"type_id": "tags/hot-latina", "type_name": "Latina"},
            {"type_id": "tags/indian", "type_name": "Indian"},
            {"type_id": "tags/arab", "type_name": "Arab"},
            {"type_id": "tags/threesome", "type_name": "Threesome"},
            {"type_id": "tags/gangbang", "type_name": "Gangbang"},
            {"type_id": "tags/creampie", "type_name": "Creampie"},
            {"type_id": "tags/hardcore", "type_name": "Hardcore"},
            {"type_id": "tags/pov", "type_name": "POV"},
            {"type_id": "tags/massage", "type_name": "Massage"},
            {"type_id": "tags/public", "type_name": "Public"},
            {"type_id": "tags/homemade", "type_name": "Homemade"},
            {"type_id": "tags/hentai", "type_name": "Hentai"},
            {"type_id": "tags/cosplay", "type_name": "Cosplay"},
            {"type_id": "tags/bdsm", "type_name": "BDSM"},
            {"type_id": "tags/1080p", "type_name": "1080p"},
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
            # 频道
            ch_html = self.fetch(self.host + "/channels/")
            chans = self._parse_channels(ch_html) if ch_html else []
            # 标签
            html = self.fetch(self.host + "/tags/")
            dyn = self._parse_tags(html) if html else []
            base = [c for c in self.classes if c["type_id"] in ("popular", "trending", "channels", "models")]
            known = {c["type_id"] for c in base}
            # 频道站点作为分类
            extra_ch = [c for c in chans if c["type_id"] not in known][:40]
            known |= {c["type_id"] for c in extra_ch}
            extra_tag = [c for c in dyn if c["type_id"] not in known][:60]
            self.classes = base + extra_ch + extra_tag
        except Exception:
            pass
        return {"class": self.classes, "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            path = tid.strip("/")
            if path == "channels":
                url = f"{self.host}/channels/" if pg == "1" else f"{self.host}/channels/{pg}/"
                html = self.fetch(url)
                videos = self._parse_channel_cards(html)
            elif path == "models":
                url = f"{self.host}/models/" if pg == "1" else f"{self.host}/models/{pg}/"
                html = self.fetch(url)
                videos = self._parse_model_cards(html)
            else:
                # popular / tags/xxx / sites/xxx
                url = f"{self.host}/{path}/" if pg == "1" else f"{self.host}/{path}/{pg}/"
                html = self.fetch(url)
                videos = self._parse_list(html)
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "limit": 48,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[pornhat] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 48, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        # 频道：把该站视频做成选集
        if "sites/" in raw and "/video/" not in raw:
            return self._detail_channel(raw)

        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = f"{self.host}/video/{raw.strip('/')}/"

        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html, "html.parser")

            title = ""
            if soup.title:
                title = re.sub(r"\s*[-|].*$", "", soup.title.get_text()).strip()
            h1 = soup.select_one("h1")
            if h1:
                title = h1.get_text(strip=True) or title
            if not title:
                title = raw.rstrip("/").split("/")[-1].replace("-", " ")

            pic = ""
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html)
            if not m:
                m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html)
            if m:
                pic = m.group(1)
            if not pic:
                img = soup.select_one("img[data-original], video[poster]")
                if img:
                    pic = img.get("data-original") or img.get("poster") or img.get("src") or ""

            # 多清晰度 MP4（排除 preview）
            play_parts = []
            seen = set()
            for u in re.findall(r'https://www\.pornhat\.com/get_file/[^"\'\s<>]+\.mp4/?', html):
                if "preview" in u.lower():
                    continue
                if u in seen:
                    continue
                seen.add(u)
                if "1080" in u:
                    label = "1080p"
                elif "720" in u:
                    label = "720p"
                elif "480" in u:
                    label = "480p"
                elif "360" in u:
                    label = "360p"
                else:
                    label = "HD"
                # get_file 必须带尾部 /，否则 404；响应为 m3u8 主列表
                u = u if u.endswith("/") else u + "/"
                play_parts.append((label, u))

            # 按清晰度排序
            order = {"1080p": 4, "720p": 3, "HD": 2, "480p": 1, "360p": 0}
            play_parts.sort(key=lambda x: order.get(x[0], 0), reverse=True)
            # 去重 label
            final = []
            used = set()
            for lab, u in play_parts:
                if lab in used:
                    continue
                used.add(lab)
                final.append(f"{lab}${u}")
            if not final:
                final.append(f"Page${url}")

            return {
                "list": [{
                    "vod_id": raw if raw.startswith("/") else f"/video/{raw.strip('/')}/",
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "/".join(used) if used else "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "PornHat",
                    "vod_play_url": "#".join(final),
                }]
            }
        except Exception as e:
            print(f"[pornhat] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers_json = json.dumps({
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
        })
        # 频道选集：先变成 get_file 地址
        if id and "/video/" in id and "get_file" not in id:
            try:
                d = self.detailContent([id])
                item = (d.get("list") or [{}])[0]
                play = (item.get("vod_play_url") or "").split("#")[0]
                if "$" in play:
                    id = play.split("$", 1)[1]
            except Exception as e:
                print(f"[pornhat] play resolve error: {e}")

        if id and ("get_file" in id or self.isVideoFormat(id)):
            url = id
            if "get_file" in url and not url.endswith("/"):
                url += "/"
            # 预解析到 CDN m3u8，避免播放器多次跳转/嗅探导致卡顿
            resolved = self._resolve_play_url(url)
            return {
                "parse": 0,
                "jx": 0,
                "url": resolved or url,
                "header": headers_json,
            }

        return {
            "parse": 1,
            "url": id if (id or "").startswith("http") else self.host + (id or ""),
            "header": headers_json,
        }

    def _resolve_play_url(self, url):
        """get_file → CDN master/media m3u8，加快起播"""
        try:
            import requests
            resp = requests.get(url, headers=self.headers, timeout=12, allow_redirects=True, verify=False)
            if resp.status_code != 200:
                return url
            text = resp.text or ""
            final = resp.url or url
            # 已是 media playlist
            if "#EXTINF" in text and "#EXT-X-STREAM-INF" not in text:
                return final
            # master：优先 720p，其次最高带宽
            variants = []
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if not line.startswith("#EXT-X-STREAM-INF"):
                    continue
                bw = re.search(r"BANDWIDTH=(\d+)", line)
                res = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
                nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if not nxt or nxt.startswith("#"):
                    continue
                h = int(res.group(2)) if res else 0
                b = int(bw.group(1)) if bw else 0
                variants.append((h, b, nxt))
            if variants:
                # 优先 720，没有则最高
                variants.sort(key=lambda x: (x[0] == 720, x[0], x[1]), reverse=True)
                return variants[0][2]
            if final.endswith(".m3u8") or "privatehost.com" in final:
                return final
        except Exception as e:
            print(f"[pornhat] resolve play: {e}")
        return url


    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            q = parse.quote(key)
            if pg == "1":
                url = f"{self.host}/search/{q}/"
            else:
                url = f"{self.host}/search/{q}/{pg}/"
            html = self.fetch(url)
            return {"list": self._parse_list(html)}
        except Exception as e:
            print(f"[pornhat] search error: {e}")
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
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            }, timeout=15, verify=False)
            if resp.status_code != 200 or not resp.content:
                return [resp.status_code, "text/plain", (resp.content or b"")[:200]]
            body = resp.content
            ctype = resp.headers.get("Content-Type") or "image/jpeg"
            if "text" in ctype or "html" in ctype:
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

    def _fix_pic(self, pic):
        if not pic or not pic.startswith("http"):
            return pic or ""
        try:
            from urllib.parse import urlsplit, urlunsplit, quote
            parts = urlsplit(pic)
            path = quote(parts.path, safe="/")
            pic = urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
        except Exception:
            pic = pic.replace(" ", "%20")
        return pic

    def _proxy_pic(self, pic):
        pic = self._fix_pic(pic)
        if not pic:
            return ""
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
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.text
            except Exception as e:
                last_err = e
                time.sleep(0.3)
        print(f"[pornhat] fetch fail: {last_err}")
        return ""


    def _detail_channel(self, raw):
        path = raw if raw.startswith("/") else "/" + raw.strip("/")
        if not path.endswith("/"):
            path += "/"
        try:
            html = self.fetch(self.host + path)
            videos = self._parse_list(html)
            # 多页合并前几页，方便选集
            for pg in range(2, 4):
                more = self._parse_list(self.fetch(f"{self.host}{path}{pg}/"))
                if not more:
                    break
                videos.extend(more)
            seen = set()
            play_parts = []
            for i, v in enumerate(videos, 1):
                vid = v.get("vod_id") or ""
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                name = v.get("vod_name") or f"视频{i}"
                if len(name) > 40:
                    name = name[:40] + "…"
                play_parts.append(f"{name}${vid}")
            title = path.strip("/").split("/")[-1].replace("-", " ").title()
            pic = videos[0].get("vod_pic", "") if videos else ""
            if not play_parts:
                play_parts.append(f"打开${path}")
            return {
                "list": [{
                    "vod_id": path,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_content": title,
                    "vod_remarks": f"{len(play_parts)} videos",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "Channel",
                    "vod_play_from": "PornHat",
                    "vod_play_url": "#".join(play_parts),
                }]
            }
        except Exception as e:
            print(f"[pornhat] channel detail error: {e}")
            return {"list": []}

    def _parse_channels(self, html):
        cats = []
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select('a[href*="/sites/"]'):
            href = a.get("href") or ""
            m = re.match(r"^(/sites/([a-z0-9-]+)/)$", href)
            if not m:
                continue
            path, slug = m.group(1), m.group(2)
            name = a.get("title") or ""
            img = a.select_one("img")
            if img and not name:
                name = img.get("alt") or ""
            if not name:
                name = a.get_text(strip=True)
            name = re.sub(r"\s+", " ", name).strip() or slug.replace("-", " ").title()
            tid = f"sites/{slug}"
            if tid not in [c["type_id"] for c in cats]:
                cats.append({"type_id": tid, "type_name": name})
        return cats

    def _parse_channel_cards(self, html):
        """频道目录页：把每个频道当成列表项"""
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        for a in soup.select('a[href*="/sites/"]'):
            href = a.get("href") or ""
            m = re.match(r"^(/sites/([a-z0-9-]+)/)$", href)
            if not m:
                continue
            path = m.group(1)
            if path in seen:
                continue
            seen.add(path)
            name = a.get("title") or ""
            pic = ""
            img = a.select_one("img")
            if img:
                pic = (img.get("data-original") or img.get("data-src") or img.get("src") or "").strip()
                if not name:
                    name = img.get("alt") or ""
            if pic.startswith("data:"):
                pic = ""
            if pic.startswith("//"):
                pic = "https:" + pic
            if not name:
                name = a.get_text(strip=True) or m.group(2).replace("-", " ").title()
            videos.append({
                "vod_id": f"sites/{m.group(2)}",
                "vod_name": name.strip(),
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "文件夹",
                "vod_tag": "folder",
            })
        return videos


    def _parse_model_cards(self, html):
        """演员目录：点击后以 folder 进入作品列表"""
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        for a in soup.select('a[href*="/models/"]'):
            href = a.get("href") or ""
            m = re.match(r"^(/models/([a-z0-9-]+)/)$", href)
            if not m:
                continue
            slug = m.group(2)
            if slug in ("videos", "updated") or slug.isdigit():
                continue
            path = m.group(1)
            if path in seen:
                continue
            seen.add(path)
            name = a.get("title") or ""
            pic = ""
            img = a.select_one("img")
            if img:
                pic = (img.get("data-original") or img.get("data-src") or img.get("src") or "").strip()
                if not name:
                    name = img.get("alt") or ""
            if pic.startswith("data:"):
                pic = ""
            if pic.startswith("//"):
                pic = "https:" + pic
            if not name:
                name = a.get_text(strip=True) or slug.replace("-", " ").title()
            videos.append({
                "vod_id": f"models/{slug}",
                "vod_name": name.strip(),
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "演员",
                "vod_tag": "folder",
            })
        return videos

    def _parse_tags(self, html):
        cats = []
        # 优先选内容较多的标签
        for m in re.finditer(r'href="(/tags/([a-z0-9-]+)/)"[^>]*>([^<]+)<', html):
            path, slug, name = m.group(1), m.group(2), m.group(3).strip()
            name = re.sub(r"\s*\([\d,]+\)\s*$", "", name).strip()
            if not name:
                name = slug.replace("-", " ").title()
            tid = f"tags/{slug}"
            if tid not in [c["type_id"] for c in cats]:
                cats.append({"type_id": tid, "type_name": name})
        return cats

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")
        seen = set()

        # 常见结构：a.item / .thumb 内链接
        anchors = soup.select("a.item[href*='/video/'], .item a[href*='/video/'], a[href*='/video/']")
        for a in anchors:
            href = (a.get("href") or "").split("?")[0]
            if not href or "/video/" not in href:
                continue
            if href.startswith("/"):
                path = href
            elif "pornhat.com" in href:
                path = "/" + href.split("pornhat.com/", 1)[-1]
            else:
                continue
            path = "/" + path.strip("/") + "/"
            if path in seen:
                continue
            seen.add(path)

            title = a.get("title") or ""
            if not title:
                img = a.select_one("img")
                if img:
                    title = img.get("alt") or ""
            if not title:
                title = a.get_text(" ", strip=True)
            title = re.sub(r"\s+", " ", title).strip()
            if not title:
                title = path.strip("/").split("/")[-1].replace("-", " ").title()

            pic = ""
            img = a.select_one("img")
            if not img and a.parent:
                img = a.parent.select_one("img")
            if img:
                pic = (img.get("data-original") or img.get("data-src") or img.get("src") or "").strip()
            if pic.startswith("data:"):
                pic = ""
            if pic.startswith("//"):
                pic = "https:" + pic

            videos.append({
                "vod_id": path,
                "vod_name": title,
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })
        return videos


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    cat = sp.categoryContent("popular", "1", False, {})
    print("popular", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(" ", v.get("vod_name", "")[:40], "|", (v.get("vod_pic") or "")[:50])
    if cat.get("list"):
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        item = (d.get("list") or [{}])[0]
        print("play", (item.get("vod_play_url") or "")[:150])
