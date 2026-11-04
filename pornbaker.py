# -*- coding: utf-8 -*-
# pornbaker.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 / 与 /page/N/  · 分类 /{id}-{slug}/  · 标签 /tag/{id}-{slug}/
# 详情 /{id}-{slug}/  · 播放：m3u8/mp4 直链或 parse=1 嗅探

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
        self.name = "PornBaker"
        self.host = "https://pornbaker.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        # 已知分类：数字id-slug（站点真实路径）
        self.cat_map = {
            "newest": "",
            "best": "?filter=best",
            "most-viewed": "?filter=popular",
            "longest": "?filter=longest",
            # 已确认数字 id
            "milf": "6386-milf",
            "teen": "6411-teen",
            "threesome": "6412-threesome",
            "massage": "6383-massage",
            "exclusive": "6363-exclusive",
            "french": "6369-french",
            "japanese": "6379-japanese",
            "korean": "6380-korean",
            "indian": "6376-indian",
            "asian": "8-asian",
            # 其余先用 slug，加载失败时走搜索
            "amateur": "amateur",
            "anal": "anal",
            "arab": "arab",
            "lesbian": "lesbian",
            "hentai": "hentai",
            "trans": "trans",
            "outdoor": "outdoor",
            "big-tits": "big-tits",
            "gangbang": "gangbang",
            "ebony": "ebony",
            "deepthroat": "deepthroat",
            "creampie": "creampie",
            "bondage": "bondage",
            "orgy": "orgy",
            "latina": "latina",
            "pov": "pov",
            "asmr": "asmr",
            "blowjob": "blowjob",
            "public": "public",
            "babysitter": "babysitter",
            "bbc": "bbc",
            "cosplay": "cosplay",
            "hardcore": "hardcore",
            "blonde": "blonde",
            "brunette": "brunette",
            "cuckold": "cuckold",
            "squirt": "squirt",
            "german": "german",
            "czech": "czech",
            "bbw": "bbw",
            "big-ass": "big-ass",
            "big-dick": "big-dick",
            "bisexual": "bisexual",
            "bukkake": "bukkake",
            "cartoon": "cartoon",
            "casting": "casting",
            "celebrity": "celebrity",
            "cheerleader": "cheerleader",
            "college": "college",
            "compilation": "compilation",
            "cumshot": "cumshot",
            "doctor": "doctor",
            "double-penetration": "double-penetration",
            "euro": "euro",
            "facial": "facial",
            "feet": "feet",
            "fetish": "fetish",
            "fingering": "fingering",
            "fisting": "fisting",
            "funny": "funny",
            "handjob": "handjob",
            "interracial": "interracial",
            "italian": "italian",
            "joi": "joi",
            "maid": "maid",
            "masturbation": "masturbation",
            "mature": "mature",
            "nurse": "nurse",
            "old-young": "old-young",
            "parody": "parody",
            "party": "party",
            "pissing": "pissing",
            "police": "police",
            "pornstars": "pornstars",
            "professional": "professional",
            "pussy-licking": "pussy-licking",
            "reality": "reality",
            "redhead": "redhead",
            "rough-sex": "rough-sex",
            "russian": "russian",
            "school": "school",
            "small-tits": "small-tits",
            "smoking": "smoking",
            "solo": "solo",
            "stewardess": "stewardess",
            "strap-on": "strap-on",
            "striptease": "striptease",
            "tattoo": "tattoo",
            "toys": "toys",
            "transgender": "transgender",
            "uniforms": "uniforms",
            "vintage": "vintage",
            "virtual-reality": "virtual-reality",
            "webcam": "webcam",
            "60fps": "60fps",
            "babe": "babe",
            "brazilian": "brazilian",
            "british": "british",
            "music-pmv": "music-pmv",
        }
        self.classes = [
            {"type_id": "newest", "type_name": "Newest"},
            {"type_id": "best", "type_name": "Best"},
            {"type_id": "most-viewed", "type_name": "Most Viewed"},
            {"type_id": "longest", "type_name": "Longest"},
        ] + [
            {"type_id": k, "type_name": k.replace("-", " ").title()}
            for k in self.cat_map.keys()
            if k not in ("newest", "best", "most-viewed", "longest")
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
            html = self.fetch(self.host + "/categories/")
            if html and "blocked" not in html.lower()[:500]:
                dyn = self._parse_categories(html)
                if dyn and len(dyn) > 10:
                    self.classes = [
                        {"type_id": "newest", "type_name": "Newest"},
                        {"type_id": "best", "type_name": "Best"},
                        {"type_id": "most-viewed", "type_name": "Most Viewed"},
                        {"type_id": "longest", "type_name": "Longest"},
                    ] + dyn
        except Exception as e:
            print(f"[pornbaker] home cats: {e}")
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
            html = self.fetch(url)
            videos = self._parse_list(html)
            # 若无 slug 无，尝试搜索到的数字id路径
            if not videos and tid in self.cat_map and self.cat_map[tid] and not re.match(r"^\d+-", self.cat_map[tid]):
                # 再试 /tag/ 形式（部分标签）
                alt = f"{self.host}/tag/{self.cat_map[tid]}/" if pg == "1" else f"{self.host}/tag/{self.cat_map[tid]}/page/{pg}/"
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
            print(f"[pornbaker] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "pageCount": 1, "limit": 36, "total": 0}

    def _build_list_url(self, tid, pg):
        tid = (tid or "").strip()
        # 已是 数字-slug
        if re.match(r"^\d+-[a-z0-9-]+$", tid):
            return f"{self.host}/{tid}/" if pg == "1" else f"{self.host}/{tid}/page/{pg}/"
        # tag/xxx
        if tid.startswith("tag/"):
            return f"{self.host}/{tid}/" if pg == "1" else f"{self.host}/{tid}/page/{pg}/"
        # 排序首页
        if tid in ("newest", "home", ""):
            return self.host + "/" if pg == "1" else f"{self.host}/page/{pg}/"
        if tid == "best":
            base = self.host + "/" if pg == "1" else f"{self.host}/page/{pg}/"
            return base + ("?filter=best" if "?" not in base else "&filter=best")
        if tid == "most-viewed":
            base = self.host + "/" if pg == "1" else f"{self.host}/page/{pg}/"
            return base + ("?filter=popular" if "?" not in base else "&filter=popular")
        if tid == "longest":
            base = self.host + "/" if pg == "1" else f"{self.host}/page/{pg}/"
            return base + ("?filter=longest" if "?" not in base else "&filter=longest")
        # 映射
        mapped = self.cat_map.get(tid, tid)
        if re.match(r"^\d+-[a-z0-9-]+$", mapped):
            return f"{self.host}/{mapped}/" if pg == "1" else f"{self.host}/{mapped}/page/{pg}/"
        # 纯 slug：站点多数国家/题材分类需要数字 id，未知时用搜索保证有内容
        q = parse.quote(mapped.replace("-", " "))
        if pg == "1":
            return f"{self.host}/?s={q}"
        return f"{self.host}/page/{pg}/?s={q}"

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = self.host + "/" + raw.lstrip("/")
        if not url.endswith("/"):
            url += "/"

        try:
            html = self.fetch(url)
            soup = BeautifulSoup(html or "", "html.parser")

            title = ""
            h1 = soup.select_one("h1")
            if h1:
                title = h1.get_text(strip=True)
            if not title:
                ogt = re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html or "")
                if ogt:
                    title = ogt.group(1).strip()
            if not title and soup.title:
                title = re.sub(r"\s*[-|].*$", "", soup.title.get_text()).strip()
            if not title:
                slug = url.rstrip("/").split("/")[-1]
                slug = re.sub(r"^\d+-", "", slug)
                title = slug.replace("-", " ").strip().title()

            pic = ""
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html or "")
            if not m:
                m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html or "")
            if m:
                pic = m.group(1)

            play_parts = []
            seen = set()

            def is_preview(u):
                ul = (u or "").lower()
                return any(x in ul for x in (
                    "preview", "trailer", "sample", "teaser", "thumb", "sprite",
                    "snippet", "intro", "promo", "/short/", "previews/",
                ))

            def add(name, u):
                if not u or u in seen or is_preview(u):
                    return
                if not u.startswith("http"):
                    return
                seen.add(u)
                play_parts.append(f"{name}${u}")

            # 1) <source> / <video> 主播放器（最优先，只取前几个）
            for src in re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', html or ""):
                if self.isVideoFormat(src):
                    add("HD", src)
            for src in re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', html or ""):
                if self.isVideoFormat(src):
                    add("HD", src)

            # 2) 结构化字段（contentUrl / file 等）
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

            # 3) m3u8（主片）
            for src in re.findall(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', (html or "").replace("\\/", "/")):
                add("HLS", src)

            # 4) 正文中的 mp4：只取「主区域」前几条，且排除预览
            #    页面下方相关推荐会有大量短 mp4，全部收录会导致只有 5 秒
            mp4s = re.findall(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', (html or "").replace("\\/", "/"))
            main_mp4 = []
            for src in mp4s:
                if is_preview(src):
                    continue
                # 跳过明显缩略/静态路径
                if any(x in src.lower() for x in ("/thumb", "/cover", "/poster", "/static/")):
                    continue
                if src not in seen:
                    main_mp4.append(src)
            # 只保留前 2 条主 mp4，避免相关视频污染
            for i, src in enumerate(main_mp4[:2]):
                add("MP4" if i else "HD", src)

            # 5) iframe 嵌入
            for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html or ""):
                if iframe.startswith("//"):
                    iframe = "https:" + iframe
                if iframe.startswith("http") and "ad" not in iframe.lower():
                    add("Embed", iframe)

            # 最多保留 4 条线路，优先 HD/HLS
            if len(play_parts) > 4:
                play_parts = play_parts[:4]
            if not play_parts:
                play_parts.append(f"Page${url}")

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
                    "vod_play_from": "PornBaker",
                    "vod_play_url": "#".join(play_parts),
                }]
            }
        except Exception as e:
            print(f"[pornbaker] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers_json = json.dumps({
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
        })
        if not id:
            return {"parse": 1, "url": self.host, "header": headers_json}

        # 直链
        if self.isVideoFormat(id):
            # 过滤明显预览短链
            if any(x in id.lower() for x in ("preview", "trailer", "sample", "teaser")):
                pass
            else:
                return {"parse": 0, "jx": 0, "url": id, "header": headers_json}

        url = id if id.startswith("http") else self.host + (id if id.startswith("/") else "/" + id)
        if not url.endswith("/") and ".html" not in url and not self.isVideoFormat(url):
            url = url + "/"

        # 详情页提取
        if not self.isVideoFormat(url):
            d = self.detailContent([url])
            item = (d.get("list") or [{}])[0]
            for p in (item.get("vod_play_url") or "").split("#"):
                if "$" not in p:
                    continue
                name, real = p.split("$", 1)
                if not real.startswith("http"):
                    continue
                if self.isVideoFormat(real) and not any(x in real.lower() for x in ("preview", "trailer", "sample")):
                    return {"parse": 0, "jx": 0, "url": real, "header": headers_json}
                if "embed" in real or "player" in real:
                    got = self._resolve_embed(real)
                    if got and not any(x in got.lower() for x in ("preview", "trailer", "sample")):
                        return {"parse": 0, "jx": 0, "url": got, "header": headers_json}

        # 回退：整页嗅探（设备 WebView 可加载完整播放器）
        return {"parse": 1, "jx": 0, "url": url, "header": headers_json}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            q = parse.quote(key)
            url = f"{self.host}/?s={q}" if pg == "1" else f"{self.host}/page/{pg}/?s={q}"
            videos = self._parse_list(self.fetch(url))
            # 无结果时：搜索兜底（国家/未知 slug）
            if not videos:
                q = parse.quote(re.sub(r"^\d+-", "", tid).replace("-", " "))
                alt = f"{self.host}/?s={q}" if pg == "1" else f"{self.host}/page/{pg}/?s={q}"
                if alt != url:
                    videos = self._parse_list(self.fetch(alt))
            return {"list": videos}
        except Exception as e:
            print(f"[pornbaker] search error: {e}")
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
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.text
                last_err = f"status={resp.status_code}"
            except Exception as e:
                last_err = e
                time.sleep(0.2)
        print(f"[pornbaker] fetch fail: {url} {last_err}")
        return ""

    def _parse_categories(self, html):
        """从 /categories/ 解析全部分类（约 100 个）"""
        if not html:
            return []
        out = []
        seen = set()
        # 数字id-slug 分类链接
        for m in re.finditer(
            r'href="((?:https?://(?:www\.)?pornbaker\.com)?/(\d+-[a-z0-9-]+)/?)"[^>]*>([^<]{2,60})<',
            html,
            re.I,
        ):
            path_id = m.group(2).lower()
            name = re.sub(r"\s+", " ", m.group(3)).strip()
            slug = re.sub(r"^\d+-", "", path_id)
            # 分类 slug 通常较短（1-3 词）
            if path_id in seen:
                continue
            if len(slug) > 40 or slug.count("-") > 4:
                continue  # 像视频长标题，跳过
            if not name or len(name) < 2:
                name = slug.replace("-", " ").title()
            nlow = name.lower()
            if nlow in ("home", "categories", "more", "all", "next", "prev"):
                continue
            seen.add(path_id)
            out.append({"type_id": path_id, "type_name": name[:40]})
        # 纯 slug 分类（无数字时）
        if len(out) < 20:
            for m in re.finditer(
                r'href="((?:https?://(?:www\.)?pornbaker\.com)?/([a-z][a-z0-9-]{2,30})/?)"[^>]*>([^<]{2,40})<',
                html,
                re.I,
            ):
                slug = m.group(2).lower()
                name = re.sub(r"\s+", " ", m.group(3)).strip()
                if slug in seen or slug in (
                    "categories", "pornstars", "tags", "page", "search", "login",
                    "my-favorites", "actors", "models", "channels", "about", "contact",
                ):
                    continue
                if slug.startswith("page") or slug.isdigit():
                    continue
                seen.add(slug)
                if not name:
                    name = slug.replace("-", " ").title()
                out.append({"type_id": slug, "type_name": name[:40]})
        return out


    def _parse_list(self, html):
        if not html or "you have been blocked" in html.lower() or "just a moment" in html.lower():
            return []
        videos = []
        seen = set()
        used_pics = set()
        soup = BeautifulSoup(html or "", "html.parser")

        nav_titles = {
            "categories", "pornstars", "pornstar", "tags", "tag", "home", "search",
            "login", "register", "favorites", "favourite", "models", "channels",
            "newest", "best", "popular", "longest", "most viewed", "trending",
            "all categories", "more", "next", "prev", "previous", "page",
            "uncategorized",
        }

        def norm_pic(u):
            if not u:
                return ""
            u = u.strip().replace("&amp;", "&").replace("\\/", "/")
            if u.startswith("//"):
                u = "https:" + u
            if u.startswith("/"):
                u = self.host + u
            if not u.startswith("http"):
                return ""
            ul = u.lower()
            if ul.startswith("data:") or any(x in ul for x in (
                "flag", "sprite", "icon", "logo", "placeholder", "blank",
                "1x1", "pixel", "loading", "spinner", "avatar", "default-thumb",
                "no-image", "noimage", "missing", "gravatar", "emoji", "badge",
                "favicon",
            )):
                return ""
            if re.search(r"/(16|32|48|64)x(16|32|48|64)/", ul):
                return ""
            return u

        def extract_from_anchor(a, block_text=""):
            href = a.get("href") or ""
            if href.startswith("/"):
                href_full = self.host + href
            elif href.startswith("http"):
                href_full = href
            else:
                return None
            m = re.search(r"pornbaker\.com/(\d+-[a-z0-9%-]+)/?", href_full, re.I)
            if not m:
                return None
            path_id = parse.unquote(m.group(1))
            slug = re.sub(r"^\d+-", "", path_id).lower()
            # 分类页本身：slug 很短且无连字符
            if len(slug) < 12 or slug.count("-") < 2:
                return None
            path = "/" + path_id + "/"
            if path in seen:
                return None

            # 封面：优先 a 内 img
            pic = ""
            for img in a.select("img"):
                for attr in ("data-src", "data-original", "data-lazy-src", "data-poster", "data-thumb", "src"):
                    cand = (img.get(attr) or "").strip()
                    if cand and not cand.startswith("data:"):
                        pic = norm_pic(cand)
                        if pic:
                            break
                if pic:
                    break
            if not pic:
                # 父级 video-block 内找
                parent = a.parent
                for _ in range(3):
                    if not parent:
                        break
                    for img in parent.select("img"):
                        for attr in ("data-src", "data-original", "data-lazy-src", "src"):
                            cand = (img.get(attr) or "").strip()
                            if cand and not cand.startswith("data:"):
                                pic = norm_pic(cand)
                                if pic:
                                    break
                        if pic:
                            break
                    if pic:
                        break
                    parent = parent.parent
            if pic and pic in used_pics:
                pic = ""
            if pic:
                used_pics.add(pic)

            title = (a.get("title") or "").strip()
            if not title or len(title) < 5:
                img = a.select_one("img")
                if img:
                    title = (img.get("alt") or "").strip()
            if not title or len(title) < 5:
                # video-block 标题节点
                parent = a.parent
                for _ in range(4):
                    if not parent:
                        break
                    for sel in (".title", ".video-title", "h2", "h3", "h4", "[class*='title']"):
                        node = parent.select_one(sel)
                        if node:
                            t = node.get_text(" ", strip=True)
                            if t and len(t) > 5:
                                title = t
                                break
                    if title and len(title) > 5:
                        break
                    parent = parent.parent
            if not title or len(title) < 5:
                title = slug.replace("-", " ").title()

            tlow = re.sub(r"[^a-z0-9\s\-]", "", title.lower()).strip()
            if tlow in nav_titles:
                return None
            # 单单词分类名
            if " " not in title.strip() and len(title) < 16 and tlow in nav_titles:
                return None

            remarks = ""
            blob = block_text or (a.parent.get_text(" ", strip=True) if a.parent else "")
            mm = re.search(r"(\d+\s*(?:min|sec|h)|\d+:\d{2})", blob, re.I)
            if mm:
                remarks = mm.group(1)

            # 关键：无时长且标题很短 → 多半是分类/导航卡片
            if not remarks and len(title) < 18 and title.count(" ") < 2:
                return None

            seen.add(path)
            return {
                "vod_id": path,
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic) if pic else "",
                "vod_remarks": remarks,
            }

        # 1) 优先 video-block 卡片（kolortube 主题）
        blocks = soup.select(".video-block, .video-item, .thumb, article, .post")
        for block in blocks:
            a = block.select_one('a[href*="-"]')
            if not a:
                continue
            item = extract_from_anchor(a, block.get_text(" ", strip=True))
            if item:
                videos.append(item)

        # 2) 兜底：全页视频链接
        if len(videos) < 8:
            for a in soup.select('a[href*="-"]'):
                item = extract_from_anchor(a)
                if item:
                    videos.append(item)

        return videos

    def _resolve_embed(self, url):
        try:
            import requests
            resp = requests.get(url, headers={**self.headers, "Referer": self.host + "/"}, timeout=15, allow_redirects=True, verify=False)
            html = (resp.text or "").replace("\\/", "/")
            m3 = re.findall(r'https://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', html)
            if m3:
                for u in m3:
                    if "720" in u or "1080" in u:
                        return u
                return m3[0]
            mp4 = [u for u in re.findall(r'https://[^"\'\s<>]+\.mp4[^"\'\s<>]*', html)
                   if "preview" not in u.lower() and "thumb" not in u.lower()]
            if mp4:
                return mp4[0]
        except Exception as e:
            print(f"[pornbaker] resolve: {e}")
        return ""


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    print("url milf", sp._build_list_url("milf", "1"))
    print("url newest", sp._build_list_url("newest", "2"))
