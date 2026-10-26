# -*- coding: utf-8 -*-
# 站点：YouPorn  https://www.youporn.com
# 适配：蜂蜜影视 / TVBox
# 修复：pix-cdn77 封面走本地代理并带 Referer，解决 403

import re
import json
from urllib import parse

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        pass


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://www.youporn.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": "age_verified=1; platform=pc; age_gate=1",
        }
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        except Exception:
            self.session = None

    def getName(self):
        return "YouPorn"

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv", ".ts", "/media/"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        classes = [
            {"type_id": "milf", "type_name": "MILF"},
            {"type_id": "anal", "type_name": "Anal"},
            {"type_id": "bigtits", "type_name": "Big Tits"},
            {"type_id": "blowjob", "type_name": "Blowjob"},
            {"type_id": "creampie", "type_name": "Creampie"},
            {"type_id": "gangbang", "type_name": "Gangbang"},
            {"type_id": "threesome", "type_name": "Threesome"},
            {"type_id": "asian", "type_name": "Asian"},
            {"type_id": "japanese", "type_name": "Japanese"},
            {"type_id": "latina", "type_name": "Latina"},
            {"type_id": "lesbian", "type_name": "Lesbian"},
            {"type_id": "ebony", "type_name": "Ebony"},
            {"type_id": "blonde", "type_name": "Blonde"},
            {"type_id": "stepfantasy", "type_name": "Step Fantasy"},
            {"type_id": "bondage", "type_name": "Bondage"},
            {"type_id": "pov", "type_name": "POV"},
            {"type_id": "mature", "type_name": "Mature"},
            {"type_id": "squirt", "type_name": "Squirt"},
            {"type_id": "orgy", "type_name": "Orgy"},
            {"type_id": "college", "type_name": "College"},
        ]
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent("milf", "1", False, {})

    def _get(self, url, **kwargs):
        import requests
        headers = kwargs.pop("headers", None) or self.headers
        if self.session is not None:
            r = self.session.get(url, headers=headers, timeout=15, verify=False, **kwargs)
        else:
            r = requests.get(url, headers=headers, timeout=15, verify=False, **kwargs)
        r.encoding = "utf-8"
        return r

    def _wrap_pic(self, pic):
        """需要 Referer 的封面走本地 Python 代理，避免 App 直连 403"""
        if not pic:
            return ""
        pic = pic.replace("&amp;", "&")
        # fi1 等不需要 Referer，直接用
        if "pix-cdn77" not in pic:
            return pic
        # pix-cdn77 必须带 Referer：走 9978 代理（蜂蜜影视 PyHttpProxy）
        # 同时附带 header 参数，兼容多种代理实现
        enc = parse.quote(pic, safe="")
        # 常见两种写法，优先短链
        return f"http://127.0.0.1:9978/proxy?do=image&url={enc}"

    def _pick_cover(self, block):
        candidates = re.findall(
            r'(?:data-(?:src|poster)|src)="(https?://[^"]+)"',
            block,
            re.I,
        )
        candidates = [
            c.replace("&amp;", "&")
            for c in candidates
            if c and not c.startswith("data:")
        ]
        # 1) 优先不需要 Referer 的
        for c in candidates:
            if "pix-cdn77" not in c and "ypncdn" in c:
                return self._wrap_pic(c)
        for c in candidates:
            if "pix-cdn77" not in c and any(
                x in c.lower() for x in [".jpg", ".jpeg", ".png", ".webp"]
            ):
                return self._wrap_pic(c)
        # 2) 只有 pix 时也返回（会走代理）
        for c in candidates:
            if "ypncdn" in c or "phncdn" in c:
                return self._wrap_pic(c)
        return self._wrap_pic(candidates[0]) if candidates else ""

    def _parse_list(self, html):
        videos = []
        for m in re.finditer(
            r'<article[^>]+data-video-id="(\d+)"[^>]*aria-label="([^"]+)"[^>]*>',
            html,
            re.I,
        ):
            vid, title = m.group(1), m.group(2).strip()
            tail = html[m.end() : m.end() + 2800]
            pic = self._pick_cover(tail)

            duration = ""
            d_m = re.search(
                r'video-duration[^>]*>[\s\S]*?([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)',
                tail,
                re.I,
            )
            if d_m:
                duration = d_m.group(1).strip()

            remarks = duration
            if duration:
                parts = [int(x) for x in duration.split(":")]
                secs = (
                    parts[0] * 60 + parts[1]
                    if len(parts) == 2
                    else parts[0] * 3600 + parts[1] * 60 + parts[2]
                )
                if secs <= 90:
                    remarks = f"{duration} 预告"

            videos.append(
                {
                    "vod_id": f"/watch/{vid}/",
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                }
            )

        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen and v["vod_name"]:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = str(pg)
            if pg == "1":
                url = f"{self.host}/category/{tid}/"
            else:
                url = f"{self.host}/category/{tid}/?page={pg}"

            r = self._get(url)
            html = r.text if r is not None else ""
            if not html:
                return {
                    "list": [],
                    "page": int(pg),
                    "pagecount": int(pg),
                    "limit": 24,
                    "total": 0,
                }

            videos = self._parse_list(html)
            has_next = bool(re.search(rf"page={int(pg) + 1}", html))
            pagecount = (
                int(pg) if not videos else (int(pg) + 30 if has_next else int(pg) + 1)
            )

            return {
                "list": videos,
                "page": int(pg),
                "pagecount": pagecount,
                "limit": 24,
                "total": pagecount * 24,
            }
        except Exception as e:
            print(f"[categoryContent] error: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}

    def _extract_media_apis(self, html):
        apis = []
        for m in re.finditer(r'videoUrl"\s*:\s*"(https:[^"]+)"', html):
            u = m.group(1).replace("\\/", "/")
            if "/media/mp4" in u or "/media/hls" in u:
                if u not in apis:
                    apis.append(u)
        apis.sort(key=lambda x: (0 if "/media/mp4" in x else 1))
        return apis

    def _pick_best(self, data):
        if not isinstance(data, list) or not data:
            return ""
        prefer = ["1080", "720", "480", "240"]
        by_q = {}
        for item in data:
            q = str(item.get("quality", ""))
            u = item.get("videoUrl") or item.get("video_url") or ""
            if u:
                by_q[q] = u.replace("\\/", "/")
        for q in prefer:
            if q in by_q:
                return by_q[q]
        for item in data:
            if item.get("defaultQuality"):
                u = item.get("videoUrl") or ""
                if u:
                    return u.replace("\\/", "/")
        u = data[0].get("videoUrl") or ""
        return u.replace("\\/", "/") if u else ""

    def _resolve_play_url(self, html, page_url):
        apis = self._extract_media_apis(html)
        print(f"[resolve] apis={len(apis)}")
        for api in apis:
            try:
                rr = self._get(
                    api,
                    headers={
                        **self.headers,
                        "Accept": "application/json, */*",
                        "Referer": page_url,
                    },
                )
                if rr.status_code != 200:
                    continue
                text = rr.text.strip()
                if not text.startswith("[") and not text.startswith("{"):
                    continue
                data = rr.json()
                play = self._pick_best(data)
                if play:
                    print(f"[resolve] got {play[:90]}")
                    return play
            except Exception as e:
                print(f"[resolve] err {e}")
                continue
        return ""

    def detailContent(self, ids):
        try:
            path = ids[0]
            url = path if str(path).startswith("http") else self.host + path

            r = self._get(url)
            html = r.text if r is not None else ""
            if not html:
                return {"list": []}

            title = "YouPorn"
            title_m = re.search(r"<title>([^<]+)</title>", html)
            if title_m:
                title = title_m.group(1)
                for sep in [" - Free Porn", " | YouPorn", " - YouPorn"]:
                    if sep in title:
                        title = title.split(sep)[0].strip()
                        break

            play_url = self._resolve_play_url(html, url)

            pic = ""
            all_pics = re.findall(
                r'(https?://[^"\']+(?:ypncdn|phncdn)[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)',
                html,
            )
            for p in all_pics:
                p = p.replace("&amp;", "&")
                if "pix-cdn77" not in p:
                    pic = p
                    break
            if not pic and all_pics:
                pic = self._wrap_pic(all_pics[0].replace("&amp;", "&"))
            else:
                pic = self._wrap_pic(pic) if pic else ""

            if play_url:
                vod_play_from = "YouPorn"
                vod_play_url = f"正片${play_url}"
            else:
                vod_play_from = "嗅探"
                vod_play_url = f"正片${url}"

            return {
                "list": [
                    {
                        "vod_id": ids[0],
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_content": title,
                        "vod_play_from": vod_play_from,
                        "vod_play_url": vod_play_url,
                    }
                ]
            }
        except Exception as e:
            print(f"[detailContent] error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        try:
            encoded = parse.quote(key)
            pg = str(pg)
            if pg == "1":
                url = f"{self.host}/search/?query={encoded}"
            else:
                url = f"{self.host}/search/?query={encoded}&page={pg}"
            r = self._get(url)
            html = r.text if r is not None else ""
            if not html:
                return {"list": []}
            return {"list": self._parse_list(html)}
        except Exception as e:
            print(f"[searchContent] error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": "https://www.youporn.com/",
            "Origin": "https://www.youporn.com",
        }
        if id and (".mp4" in id or "ypncdn.com" in id or "phncdn.com" in id):
            return {"parse": 0, "url": id, "header": json.dumps(headers)}
        play = id if str(id).startswith("http") else self.host + str(id)
        return {
            "parse": 1,
            "url": play,
            "header": json.dumps(
                {
                    **headers,
                    "Cookie": "age_verified=1; platform=pc; age_gate=1",
                }
            ),
        }

    def localProxy(self, param):
        """本地代理：给需要 Referer 的图片/资源加头"""
        try:
            import requests

            url = param.get("url") or param.get("src") or ""
            if not url:
                return [400, "text/plain", {}, b"missing url"]
            url = parse.unquote(url)
            headers = {
                "User-Agent": self.headers["User-Agent"],
                "Referer": "https://www.youporn.com/",
                "Origin": "https://www.youporn.com",
            }
            r = requests.get(url, headers=headers, timeout=15, verify=False)
            ctype = r.headers.get("Content-Type", "image/jpeg")
            return [r.status_code, ctype, {}, r.content]
        except Exception as e:
            print(f"[localProxy] {e}")
            return [500, "text/plain", {}, str(e).encode("utf-8")]

    def fetch(self, url, headers=None):
        try:
            r = self._get(url, headers=headers or self.headers)
            return r.text
        except Exception as e:
            print(f"[fetch] {url} error: {e}")
            return ""
