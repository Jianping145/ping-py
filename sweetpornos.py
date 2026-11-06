# -*- coding: utf-8 -*-
# sa.sweetpornos.com  SweetPorno  蜂蜜影视(FongMi) / TVBox Python Spider
# KVS: /video/{id}/{slug}/ · /categories/{slug}/ · /latest-updates/
# 播放 get_file 多清晰度 MP4

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
        self.name = "SweetPorno"
        self.host = "https://sa.sweetpornos.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.zh_cats = {'hd-porno': '高清', 'anal': '肛交', 'milf': '熟女', 'molodye': '年轻', 'bolshie-siski': '大胸', 'bolshie-jopy': '大臀', 'minet': '口交', 'grupovoe': '群交', 'mejrasovoe': '跨种族', 'negry': '黑人', 'studentki': '学生', 'zrelye-milfy': '极品熟女', 'izmena': '出轨', 'fetish': '恋物', 'strapon': '假阳具', 'bryunetki': '黑发', 'shatenki': '棕发', 'hudye': '瘦身', 'volosatye': '毛毛', 'bolshoy-chlen': '大鸡巴', 'konchil-v-pizdu-krempay': '内射', 'chulki-i-kolgotki': '丝袜', 'massaj': '按摩', 'sexwife': '性妻子', 'porno-zvezdy': '明星', 'erotika': '情色', 'russian': '俄罗斯', 'russkaya-ozvuchka': '俄语配音', 'domashnee': '素人自拍', 'aziatki': '亚洲', 'blondinki': '金发', 'lesbiyanki': '百合', 'multiki': '动漫', 'kasting': '试镜', 'masturbaciya': '自慰', 'jestkoe': '硬核', 'fisting': '拳交', 'incest': '乱伦', 'medsestry': '护士', 'maid': '女仆', 'secretaries': '秘书', 'orgazm': '高潮', 'kunilingus': '舔阴', 'anilingus': '舔肛', 'kukold': '绿帽', 'dvoynoe-proniknovenie': '双插', 'dominirovanie': '调教', 'skrytaya-kamera': '偷拍', 'beautiful': '唯美', 'porno-podborki': '合集', 'redhead': '红发', 'pikap': '搭讪', 'public': '公开'}
        self.classes = [
            {"type_id": "latest-updates", "type_name": "最新"},
            {"type_id": "most-popular", "type_name": "最热"},
            {"type_id": "top-rated", "type_name": "好评"},
            {"type_id": "categories/hd-porno", "type_name": "高清"},
            {"type_id": "categories/anal", "type_name": "肛交"},
            {"type_id": "categories/milf", "type_name": "熟女"},
            {"type_id": "categories/molodye", "type_name": "年轻"},
            {"type_id": "categories/bolshie-siski", "type_name": "大胸"},
            {"type_id": "categories/bolshie-jopy", "type_name": "大臀"},
            {"type_id": "categories/minet", "type_name": "口交"},
            {"type_id": "categories/grupovoe", "type_name": "群交"},
            {"type_id": "categories/mejrasovoe", "type_name": "跨种族"},
            {"type_id": "categories/negry", "type_name": "黑人"},
            {"type_id": "categories/studentki", "type_name": "学生"},
            {"type_id": "categories/zrelye-milfy", "type_name": "极品熟女"},
            {"type_id": "categories/izmena", "type_name": "出轨"},
            {"type_id": "categories/fetish", "type_name": "恋物"},
            {"type_id": "categories/strapon", "type_name": "假阳具"},
            {"type_id": "categories/bryunetki", "type_name": "黑发"},
            {"type_id": "categories/shatenki", "type_name": "棕发"},
            {"type_id": "categories/hudye", "type_name": "瘦身"},
            {"type_id": "categories/volosatye", "type_name": "毛毛"},
            {"type_id": "categories/bolshoy-chlen", "type_name": "大鸡巴"},
            {"type_id": "categories/konchil-v-pizdu-krempay", "type_name": "内射"},
            {"type_id": "categories/chulki-i-kolgotki", "type_name": "丝袜"},
            {"type_id": "categories/massaj", "type_name": "按摩"},
            {"type_id": "categories/sexwife", "type_name": "性妻子"},
            {"type_id": "categories/porno-zvezdy", "type_name": "明星"},
            {"type_id": "categories/erotika", "type_name": "情色"},
            {"type_id": "categories/russian", "type_name": "俄罗斯"},
            {"type_id": "categories/russkaya-ozvuchka", "type_name": "俄语配音"},
            {"type_id": "categories/domashnee", "type_name": "素人自拍"},
            {"type_id": "categories/aziatki", "type_name": "亚洲"},
            {"type_id": "categories/blondinki", "type_name": "金发"},
            {"type_id": "categories/lesbiyanki", "type_name": "百合"},
            {"type_id": "categories/multiki", "type_name": "动漫"},
            {"type_id": "categories/kasting", "type_name": "试镜"},
            {"type_id": "categories/masturbaciya", "type_name": "自慰"},
            {"type_id": "categories/jestkoe", "type_name": "硬核"},
            {"type_id": "categories/fisting", "type_name": "拳交"},
            {"type_id": "categories/incest", "type_name": "乱伦"},
            {"type_id": "categories/medsestry", "type_name": "护士"},
            {"type_id": "categories/maid", "type_name": "女仆"},
            {"type_id": "categories/secretaries", "type_name": "秘书"},
            {"type_id": "categories/orgazm", "type_name": "高潮"},
            {"type_id": "categories/kunilingus", "type_name": "舔阴"},
            {"type_id": "categories/anilingus", "type_name": "舔肛"},
            {"type_id": "categories/kukold", "type_name": "绿帽"},
            {"type_id": "categories/dvoynoe-proniknovenie", "type_name": "双插"},
            {"type_id": "categories/dominirovanie", "type_name": "调教"},
            {"type_id": "categories/skrytaya-kamera", "type_name": "偷拍"},
            {"type_id": "categories/beautiful", "type_name": "唯美"},
            {"type_id": "categories/porno-podborki", "type_name": "合集"},
            {"type_id": "categories/redhead", "type_name": "红发"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv", ".mkv", "get_file"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        try:
            html = self.fetch(self.host + "/categories/")
            dyn = self._parse_categories(html)
            if dyn and len(dyn) >= 8:
                base = [
                    {"type_id": "latest-updates", "type_name": "最新"},
                    {"type_id": "most-popular", "type_name": "最热"},
                    {"type_id": "top-rated", "type_name": "好评"},
                ]
                # 动态分类已转中文
                self.classes = base + dyn
        except Exception as e:
            print(f"[sweet] home cats: {e}")
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            tid = (tid or "latest-updates").strip("/")
            url = self._build_list_url(tid, pg)
            videos = self._parse_list(self.fetch(url))
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "pageCount": 9999 if videos else int(pg),
                "limit": 24,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[sweet] category: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "pageCount": 1, "limit": 24, "total": 0}

    def _build_list_url(self, tid, pg):
        tid = (tid or "latest-updates").strip("/")
        if tid in ("", "home", "new"):
            tid = "latest-updates"
        # KVS 分页：/latest-updates/2/ · /categories/anal/2/
        if pg == "1":
            return f"{self.host}/{tid}/"
        return f"{self.host}/{tid}/{pg}/"

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
                og = re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html or "", re.I)
                if og:
                    title = og.group(1).strip()
            if not title and soup.title:
                title = re.sub(r"\s*[-|].*$", "", soup.title.get_text()).strip()

            pic = ""
            m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html or "", re.I)
            if m:
                pic = m.group(1)

            play_parts = []
            seen = set()
            by_q = {}

            def add_q(name, u):
                u = self._resolve_kvs_url(u)
                if not u or not u.startswith("http"):
                    return
                ul = u.lower()
                if any(x in ul for x in ("preview", "trailer", "sample", "/thumb", "sprite", ".jpg")):
                    return
                if "get_file" not in ul and ".mp4" not in ul and ".m3u8" not in ul:
                    return
                # 只有 download 链稳定可播；统一补 download=true
                if "get_file" in ul:
                    base = u.split("?")[0].rstrip("/")
                    u = base + "/?download=true"
                key = u.split("?")[0].rstrip("/").lower()
                if key in seen:
                    return
                seen.add(key)
                blob = (name + " " + u).lower()
                if "1080" in blob:
                    q = "1080P"
                elif "720" in blob:
                    q = "720P"
                elif "480" in blob:
                    q = "480P"
                elif "360" in blob:
                    q = "360P"
                else:
                    q = (name or "HD").strip() or "HD"
                # 优先保留带 download 的；后写覆盖
                by_q[q] = u

            # 1) 先收 flashvars（可能 404，仅作空缺填充）
            for key in ("video_url", "video_alt_url2", "video_alt_url", "video_alt_url3", "video_alt_url4"):
                for m in re.finditer(rf"{key}\s*:\s*['\"]([^'\"]+)['\"]", html or "", re.I):
                    name = ""
                    tm = re.search(rf"{key}_text\s*:\s*['\"]([^'\"]+)['\"]", html or "", re.I)
                    if tm:
                        name = tm.group(1).strip()
                    # flashvars 的 hash 常 404，不写入 by_q
                    pass

            # 2) 只收页面 get_file，尤其 download=true（可播）
            for src in re.findall(
                r'https?://[^"\'\s<>]*get_file/[^"\'\s<>]+',
                (html or "").replace("\\/", "/"),
            ):
                ul = src.lower()
                if "preview" in ul:
                    continue
                nm = "1080P" if "1080" in ul else "720P" if "720" in ul else "480P" if "480" in ul else "360P" if "360" in ul else "HD"
                # download 链优先覆盖
                if "download" in ul or nm not in by_q:
                    add_q(nm, src)

            # 若 download 一个都没有，再退回 flashvars
            if not by_q:
                for key in ("video_alt_url2", "video_url", "video_alt_url", "video_alt_url3"):
                    for m in re.finditer(rf"{key}\s*:\s*['\"]([^'\"]+)['\"]", html or "", re.I):
                        name = ""
                        tm = re.search(rf"{key}_text\s*:\s*['\"]([^'\"]+)['\"]", html or "", re.I)
                        if tm:
                            name = tm.group(1).strip()
                        add_q(name, m.group(1))

            order = ["1080P", "720P", "480P", "360P", "HD"]
            final = []
            for q in order:
                if q in by_q:
                    final.append(f"{q}${by_q[q]}")
            for q, u in by_q.items():
                if q not in order:
                    final.append(f"{q}${u}")
            final.append(f"嗅探${url}")

            return {
                "list": [{
                    "vod_id": url.replace(self.host, "").rstrip("/") + "/",
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "SweetPorno",
                    "vod_play_url": "#".join(final),
                }]
            }
        except Exception as e:
            print(f"[sweet] detail: {e}")
            return {"list": []}

    def _resolve_kvs_url(self, u):
        if not u:
            return ""
        u = u.replace("\\/", "/").strip()
        # function/0/https://... 或 function/0/get_file/...
        m = re.search(r"function/\d+/(https?://.+)$", u)
        if m:
            return m.group(1)
        m = re.search(r"function/\d+/(.+)$", u)
        if m:
            path = m.group(1)
            if path.startswith("http"):
                return path
            if path.startswith("/"):
                return self.host + path
            return self.host + "/" + path
        return u

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

        id = self._resolve_kvs_url(id)

        if self.isVideoFormat(id) or "get_file" in id:
            play = id
            if "get_file" in play:
                base = play.split("?")[0].rstrip("/")
                play = base + "/?download=true"
            return {"parse": 0, "jx": 0, "url": play, "header": headers_json}

        page = id if id.startswith("http") else self.host + (id if id.startswith("/") else "/" + id)
        if not page.endswith("/"):
            page += "/"
        headers["Referer"] = page
        headers_json = json.dumps(headers)

        try:
            html = self.fetch(page)
            candidates = []
            for key in ("video_alt_url2", "video_url", "video_alt_url", "video_alt_url3"):
                for m in re.finditer(rf"{key}\s*:\s*['\"]([^'\"]+)['\"]", html or "", re.I):
                    candidates.append(self._resolve_kvs_url(m.group(1)))
            for src in re.findall(
                r'https?://[^"\'\s<>]*(?:get_file/|\.mp4|\.m3u8)[^"\'\s<>]*',
                (html or "").replace("\\/", "/"),
            ):
                if "preview" in src.lower() or ".jpg" in src.lower():
                    continue
                candidates.append(src)

            # 高清优先
            def sc(u):
                ul = u.lower()
                return (0 if "1080" in ul else 1 if "720" in ul else 2 if "480" in ul else 3)

            candidates = [c for c in candidates if c and c.startswith("http")]
            candidates = sorted(set(candidates), key=sc)
            if candidates:
                play = candidates[0]
                if "get_file" in play:
                    play = play.split("?")[0].rstrip("/") + "/?download=true"
                return {"parse": 0, "jx": 0, "url": play, "header": headers_json}
        except Exception as e:
            print(f"[sweet] play: {e}")

        return {"parse": 1, "jx": 0, "url": page, "header": headers_json}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            q = parse.quote(key.strip())
            # KVS search: /search/{q}/ 或 ?q=
            if pg == "1":
                url = f"{self.host}/search/{q}/"
            else:
                url = f"{self.host}/search/{q}/{pg}/"
            videos = self._parse_list(self.fetch(url))
            if not videos:
                alt = f"{self.host}/search/?q={q}"
                if pg != "1":
                    alt += f"&from_videos={pg}"
                videos = self._parse_list(self.fetch(alt))
            return {"list": videos}
        except Exception as e:
            print(f"[sweet] search: {e}")
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
        print(f"[sweet] fetch fail: {url} {last_err}")
        return ""

    def _parse_categories(self, html):
        out = []
        seen = set()
        for m in re.finditer(
            r'href="(?:https?://[^"]+)?/categories/([a-z0-9-]+)/?"[^>]*>([^<]{2,40})<',
            html or "",
            re.I,
        ):
            slug, name = m.group(1).lower(), re.sub(r"\s+", " ", m.group(2)).strip()
            if slug in seen or slug in ("", "all"):
                continue
            seen.add(slug)
            zh = getattr(self, "zh_cats", {}).get(slug)
            if zh:
                name = zh
            elif not name:
                name = slug.replace("-", " ").title()
            out.append({"type_id": f"categories/{slug}", "type_name": name[:40]})
        if len(out) < 5:
            for m in re.finditer(r"/categories/([a-z0-9-]+)/?", html or "", re.I):
                slug = m.group(1).lower()
                if slug in seen:
                    continue
                seen.add(slug)
                zh = getattr(self, "zh_cats", {}).get(slug)
                out.append({
                    "type_id": f"categories/{slug}",
                    "type_name": (zh or slug.replace("-", " ").title())[:40],
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
            u = u.strip().replace("&amp;", "&")
            if u.startswith("//"):
                u = "https:" + u
            if u.startswith("/"):
                u = self.host + u
            if not u.startswith("http") or u.startswith("data:"):
                return ""
            return u

        def add(path, title, pic, remarks=""):
            if not path or path in seen:
                return
            if not re.search(r"/video/\d+/", path):
                return
            seen.add(path)
            title = re.sub(r"\s+", " ", (title or "")).strip()
            if not title or len(title) < 2:
                return
            videos.append({
                "vod_id": path if path.endswith("/") else path + "/",
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic) if pic else "",
                "vod_remarks": remarks,
            })

        for a in soup.select('a[href*="/video/"]'):
            href = a.get("href") or ""
            m = re.search(r"(/video/(\d+)/[a-z0-9-]+/?)", href, re.I)
            if not m:
                continue
            path = m.group(1)
            if not path.endswith("/"):
                path += "/"
            if path in seen:
                continue
            title = (a.get("title") or "").strip()
            if not title:
                title = a.get_text(" ", strip=True)
            title = re.sub(r"\s+", " ", title)
            # 去掉时长、百分比等尾巴
            title = re.sub(r"\d+%\s*$", "", title).strip()
            title = re.sub(r"\d{1,2}:\d{2}(:\d{2})?\s*$", "", title).strip()
            pic = ""
            img = a.select_one("img")
            if img:
                pic = norm_pic(
                    img.get("data-src")
                    or img.get("data-original")
                    or img.get("data-poster")
                    or img.get("src")
                    or ""
                )
            if not pic and a.parent:
                img = a.parent.select_one("img")
                if img:
                    pic = norm_pic(img.get("data-src") or img.get("src") or "")
            remarks = ""
            blob = a.get_text(" ", strip=True)
            dm = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", blob)
            if dm:
                remarks = dm.group(1)
            add(path, title, pic, remarks)

        if len(videos) < 5:
            for m in re.finditer(
                r'href="((?:https?://[^"]+)?/video/(\d+)/[a-z0-9-]+/?)"',
                html or "",
                re.I,
            ):
                path = "/" + "/".join(m.group(1).split("/")[-3:])
                if not path.startswith("/video/"):
                    path = re.sub(r"^https?://[^/]+", "", m.group(1))
                if not path.endswith("/"):
                    path += "/"
                if path in seen:
                    continue
                window = (html or "")[max(0, m.start() - 100): m.end() + 500]
                title = ""
                mt = re.search(r'title="([^"]{3,120})"', window, re.I)
                if mt:
                    title = mt.group(1)
                if not title:
                    title = m.group(1).rstrip("/").split("/")[-1].replace("-", " ")
                pic = ""
                pm = re.search(
                    r'(?:data-src|data-original|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    window,
                    re.I,
                )
                if pm:
                    pic = norm_pic(pm.group(1))
                remarks = ""
                dm = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", window)
                if dm:
                    remarks = dm.group(1)
                add(path, title, pic, remarks)

        return videos


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    print(sp._build_list_url("latest-updates", "1"))
    print(sp._build_list_url("categories/anal", "2"))
    print(sp._resolve_kvs_url("function/0/https://sa.sweetpornos.com/get_file/1/xxx/720p.mp4/"))
