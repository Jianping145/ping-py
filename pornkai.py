# -*- coding: utf-8 -*-
# pornkai.com  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 /videos?q=TAG&sort=new&page=N  · 详情 /view?key=ID
# 播放：xhamster / txxx 等嵌入源，能解析则直链，否则 parse=1 嗅探

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
        self.name = "PornKai"
        self.host = "https://pornkai.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.classes = [
            {"type_id": "recommended", "type_name": "Recommended"},
            {"type_id": "japanese", "type_name": "Japanese"},
            {"type_id": "asian", "type_name": "Asian"},
            {"type_id": "chinese", "type_name": "Chinese"},
            {"type_id": "korean", "type_name": "Korean"},
            {"type_id": "amateur", "type_name": "Amateur"},
            {"type_id": "milf", "type_name": "MILF"},
            {"type_id": "teen", "type_name": "Teen"},
            {"type_id": "anal", "type_name": "Anal"},
            {"type_id": "lesbian", "type_name": "Lesbian"},
            {"type_id": "blowjob", "type_name": "Blowjob"},
            {"type_id": "big-tits", "type_name": "Big Tits"},
            {"type_id": "big-ass", "type_name": "Big Ass"},
            {"type_id": "blonde", "type_name": "Blonde"},
            {"type_id": "brunette", "type_name": "Brunette"},
            {"type_id": "ebony", "type_name": "Ebony"},
            {"type_id": "latina", "type_name": "Latina"},
            {"type_id": "indian", "type_name": "Indian"},
            {"type_id": "arab", "type_name": "Arab"},
            {"type_id": "threesome", "type_name": "Threesome"},
            {"type_id": "pov", "type_name": "POV"},
            {"type_id": "hentai", "type_name": "Hentai"},
            {"type_id": "cosplay", "type_name": "Cosplay"},
            {"type_id": "massage", "type_name": "Massage"},
            {"type_id": "public", "type_name": "Public"},
            {"type_id": "homemade", "type_name": "Homemade"},
            {"type_id": "creampie", "type_name": "Creampie"},
            {"type_id": "hardcore", "type_name": "Hardcore"},
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
            html = self.fetch(self.host + "/all-categories")
            if html:
                dyn = self._parse_categories(html)
                if dyn:
                    # 常用分类置顶，其余按站点顺序追加
                    base = list(self.classes)
                    known = {c["type_id"] for c in base}
                    extra = [c for c in dyn if c["type_id"] not in known]
                    # 保留足够多分类（站点约 900+）
                    self.classes = base + extra
        except Exception as e:
            print(f"[pornkai] home categories: {e}")
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/videos?q=japanese&sort=new"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            tid = (tid or "japanese").strip()
            if tid in ("recommended", "home", ""):
                # 首页推荐
                if pg == "1":
                    url = f"{self.host}/"
                else:
                    url = f"{self.host}/videos?q=japanese&sort=new&page={pg}"
            else:
                url = f"{self.host}/videos?q={parse.quote(tid)}&sort=new&page={pg}"
            html = self.fetch(url)
            videos = self._parse_list(html)
            # 首页若解析为空，回退 japanese
            if not videos and tid in ("recommended", "home", ""):
                html = self.fetch(f"{self.host}/videos?q=japanese&sort=new&page={pg}")
                videos = self._parse_list(html)
            result = {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "pageCount": 9999 if videos else int(pg),
                "limit": 48,
                "total": 999999 if videos else 0,
            }
            return result
        except Exception as e:
            print(f"[pornkai] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "pageCount": 1, "limit": 48, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        key = raw
        if "key=" in raw:
            key = parse.parse_qs(parse.urlparse(raw).query).get("key", [raw])[0]
        key = key.replace("/view?key=", "").strip("/")

        try:
            url = f"{self.host}/view?key={parse.quote(key)}"
            html = self.fetch(url)
            soup = BeautifulSoup(html or "", "html.parser")

            title = ""
            if soup.title:
                title = re.sub(r"\s*[-|].*$", "", soup.title.get_text()).strip()
            h1 = soup.select_one("h1")
            if h1:
                title = h1.get_text(strip=True) or title
            if not title or title.lower() in ("pornkai", "view"):
                title = key

            pic = ""
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html or "")
            if not m:
                m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html or "")
            if m:
                pic = m.group(1)
            if not pic:
                img = soup.select_one("img[src*='http']")
                if img:
                    pic = img.get("src") or ""

            # 播放：优先可解析直链，否则用 key 交给 playerContent
            play_parts = [f"Play${key}"]
            # 多线路：若页面有多个 iframe
            iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)', html or "")
            for i, iframe in enumerate(iframes[:3]):
                if "http" in iframe:
                    play_parts.append(f"Embed{i+1}${iframe}")

            return {
                "list": [{
                    "vod_id": key,
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "PornKai",
                    "vod_play_url": "#".join(play_parts),
                }]
            }
        except Exception as e:
            print(f"[pornkai] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers_json = json.dumps({
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
        })
        if not id:
            return {"parse": 1, "url": self.host, "header": headers_json}

        if self.isVideoFormat(id) or "get_file" in id or ".m3u8" in id or "video-nss" in id:
            return {"parse": 0, "jx": 0, "url": id, "header": headers_json}

        key = id
        embed = ""
        if id.startswith("http"):
            if "key=" in id:
                key = parse.parse_qs(parse.urlparse(id).query).get("key", [""])[0] or id
            elif any(x in id for x in ("embed", "partners", "xhamster", "videotxxx", "videopornl")):
                embed = id
                key = ""
            else:
                embed = id

        if key and "key=" in str(key):
            key = parse.parse_qs(parse.urlparse(str(key)).query).get("key", [key])[0]

        play = ""
        if embed:
            play = self._resolve_embed(embed)
        if not play and key:
            play = self._resolve_key(str(key))
        if play:
            return {
                "parse": 0,
                "jx": 0,
                "url": play,
                "header": json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": "https://xhamster.com/",
                }),
            }

        view = f"{self.host}/view?key={parse.quote(str(key))}" if key else (embed or self.host)
        return {"parse": 1, "jx": 0, "url": view, "header": headers_json}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            url = f"{self.host}/videos?q={parse.quote(key)}&sort=new&page={pg}"
            return {"list": self._parse_list(self.fetch(url))}
        except Exception as e:
            print(f"[pornkai] search error: {e}")
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
            return pic or ""
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
                resp = requests.get(url, headers=self.headers, timeout=12, verify=False)
                resp.encoding = "utf-8"
                if resp.status_code == 200 and len(resp.text) > 200:
                    return resp.text
                last_err = f"status={resp.status_code} len={len(resp.text)}"
            except Exception as e:
                last_err = e
                time.sleep(0.2)
        print(f"[pornkai] fetch fail: {url} {last_err}")
        return ""

    def _parse_categories(self, html):
        cats = []
        seen = set()
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select('a[href*="/videos?q="]'):
            href = a.get("href") or ""
            m = re.search(r"[?&]q=([a-z0-9-]+)", href, re.I)
            if not m:
                continue
            slug = m.group(1).lower()
            if slug in seen:
                continue
            seen.add(slug)
            name = a.get_text(" ", strip=True)
            name = re.sub(r"\s*\([\d,]+\)\s*$", "", name).strip()
            if not name:
                name = slug.replace("-", " ").title()
            cats.append({"type_id": slug, "type_name": name})
        if not cats:
            for m in re.finditer(r'href="/videos\?q=([a-z0-9-]+)"', html, re.I):
                slug = m.group(1).lower()
                if slug in seen:
                    continue
                seen.add(slug)
                cats.append({"type_id": slug, "type_name": slug.replace("-", " ").title()})
        return cats

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")
        seen = set()

        for a in soup.select('a[href*="/view?key="]'):
            href = a.get("href") or ""
            m = re.search(r"key=([^&\"#]+)", href)
            if not m:
                continue
            key = parse.unquote(m.group(1))
            if key in seen:
                continue
            img = a.select_one("img")
            if not img:
                continue
            seen.add(key)

            title = ""
            parent = a
            for _ in range(5):
                parent = parent.parent if parent else None
                if not parent:
                    break
                texts = []
                for t in parent.stripped_strings:
                    t = t.strip()
                    if not t or re.match(r"^\d+:\d+$", t) or t.lower() in ("hd", "new"):
                        continue
                    if len(t) > 3:
                        texts.append(t)
                if texts:
                    title = texts[0]
                    break
            if not title:
                title = a.get("title") or key

            pic = ""
            for attr in ("data-src", "data-xham", "data-original", "src"):
                cand = (img.get(attr) or "").strip()
                if cand and not cand.startswith("data:"):
                    pic = cand.split(";")[0].strip()
                    break
            if pic.startswith("//"):
                pic = "https:" + pic

            remarks = ""
            for t in a.stripped_strings:
                if re.match(r"^\d+:\d+$", t.strip()):
                    remarks = t.strip()
                    break

            videos.append({
                "vod_id": key,
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": remarks,
            })
        return videos

    def _guess_embed(self, key):
        if key.startswith("txxx_"):
            return f"https://videotxxx.com/embed/{key.replace('txxx_', '')}/"
        if key.startswith("pl"):
            num = re.sub(r"^pl", "", key)
            return f"https://videopornl.com/embed/{num}/?promo=10954"
        if key.startswith("up"):
            num = re.sub(r"^up", "", key)
            return f"https://upornia.com/embed/{num}/"
        if key.startswith("xh") or re.match(r"^xh[a-zA-Z0-9]+$", key):
            return f"https://xhamster.com/embed/{key}"
        return f"https://xh.partners/p/{key}"

    def _resolve_key(self, key):
        html = self.fetch(f"{self.host}/view?key={parse.quote(key)}")
        if html:
            for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)', html):
                if iframe.startswith("//"):
                    iframe = "https:" + iframe
                if iframe.startswith("http"):
                    got = self._resolve_embed(iframe)
                    if got:
                        return got
            # partners 链接
            for u in re.findall(r'https://xh\.partners/p/[a-zA-Z0-9]+', html):
                got = self._resolve_embed(u)
                if got:
                    return got
        return self._resolve_embed(self._guess_embed(key))

    def _resolve_embed(self, url):
        try:
            import requests
            sess = requests.Session()
            sess.headers.update(self.headers)
            sess.headers["Referer"] = self.host + "/"
            # age cookies（xhamster）
            for dom in (".xhamster.com", "xhamster.com"):
                try:
                    sess.cookies.set("age_verified", "1", domain=dom)
                    sess.cookies.set("ageVerified", "true", domain=dom)
                    sess.cookies.set("cookie_accept_v2", '{"e":1,"f":1,"t":1,"a":1}', domain=dom)
                    sess.cookies.set("parental-control", "yes", domain=dom)
                except Exception:
                    pass

            resp = sess.get(url, timeout=15, allow_redirects=True, verify=False)
            html = (resp.text or "").replace("\\/", "/").replace("\\u0026", "&")
            final = resp.url or url

            # 若落到 xhamster 视频页，再拉一次完整页
            if "xhamster.com" in final and "/embed/" in final:
                # 尝试从 embed initials 取分享链接再打开
                mshare = re.search(r'"shareLink"\s*:\s*"(https:[^"]+xhamster[^"]+)"', html)
                if mshare:
                    share = mshare.group(1).replace("\\/", "/")
                    resp2 = sess.get(share, timeout=15, verify=False)
                    if resp2.status_code == 200 and len(resp2.text) > len(html):
                        html = resp2.text.replace("\\/", "/").replace("\\u0026", "&")
                        final = resp2.url
                else:
                    # embed -> /videos/{id}
                    mid = re.search(r"/embed/([a-zA-Z0-9]+)", final)
                    if mid:
                        resp2 = sess.get(f"https://xhamster.com/videos/{mid.group(1)}", timeout=15, verify=False)
                        if resp2.status_code == 200:
                            html2 = resp2.text.replace("\\/", "/")
                            if ".m3u8" in html2 or "videoModel" in html2:
                                html = html2
                                final = resp2.url

            play = self._extract_media(html)
            if play:
                return play
        except Exception as e:
            print(f"[pornkai] resolve embed: {e}")
        return ""

    def _extract_media(self, html):
        if not html:
            return ""
        # m3u8 直链
        m3 = re.findall(r'https://[^"\'\s<>\\]+\.m3u8[^"\'\s<>\\]*', html)
        m3 = [u for u in m3 if any(x in u for x in ("xhcdn", "video-nss", "cdn", "hls"))]
        if m3:
            for u in m3:
                if "720" in u or "1080" in u:
                    return u
            return m3[0]
        # mp4
        mp4 = re.findall(r'https://[^"\'\s<>\\]+\.mp4[^"\'\s<>\\]*', html)
        mp4 = [u for u in mp4 if "preview" not in u.lower() and "thumb" not in u.lower() and "ico" not in u.lower()]
        if mp4:
            for u in mp4:
                if any(x in u for x in ("720", "1080", "480", "get_file")):
                    return u
            return mp4[0]
        # initials JSON
        m = re.search(r"window\.initials\s*=\s*(\{.*?\})\s*;\s*</script>", html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                s = json.dumps(data)
                found = re.findall(r'https:[^"]+\.m3u8[^"]*', s)
                if found:
                    return found[0].replace("\\/", "/")
                found = re.findall(r'https:[^"]+\.mp4[^"]*', s)
                found = [u for u in found if "preview" not in u.lower()]
                if found:
                    return found[0].replace("\\/", "/")
            except Exception:
                pass
        # 常见 tube 字段
        for pat in [
            r'video_url["\']?\s*[:=]\s*["\']([^"\']+)',
            r'["\']file["\']\s*:\s*["\']([^"\']+)',
            r'hls["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)',
        ]:
            mm = re.search(pat, html, re.I)
            if mm:
                u = mm.group(1).replace("\\/", "/")
                if u.startswith("function/"):
                    continue
                if u.startswith("http"):
                    return u
                if u.startswith("//"):
                    return "https:" + u
        return ""



if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    cat = sp.categoryContent("japanese", "1", False, {})
    print("list", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(" ", v.get("vod_name", "")[:50], "|", (v.get("vod_pic") or "")[:40])
    if cat.get("list"):
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        item = (d.get("list") or [{}])[0]
        print("detail", item.get("vod_name", "")[:50])
        play = sp.playerContent("PornKai", cat["list"][0]["vod_id"], [])
        print("play parse", play.get("parse"), str(play.get("url", ""))[:100])
