# -*- coding: utf-8 -*-
# 站点：YesPornVIP  https://yesporn.vip
# 适配：蜂蜜影视 / TVBox
# 说明：KVS function/0/ 解密直链播放（修复嗅探到十几秒预览的问题）

import re
import json
from urllib import parse

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def fetch(self, url, headers=None):
            import requests
            h = headers or {}
            r = requests.get(url, headers=h, timeout=15, verify=False)
            r.encoding = "utf-8"
            return r.text


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://yesporn.vip"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def getName(self):
        return "YesPornVIP"

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        classes = [
            {"type_id": "milf", "type_name": "MILF"},
            {"type_id": "anal", "type_name": "Anal"},
            {"type_id": "big-tits", "type_name": "Big Tits"},
            {"type_id": "big-ass", "type_name": "Big Ass"},
            {"type_id": "stepmom", "type_name": "Stepmom"},
            {"type_id": "cheating", "type_name": "Cheating"},
            {"type_id": "latina", "type_name": "Latina"},
            {"type_id": "mature", "type_name": "Mature"},
            {"type_id": "bbw", "type_name": "BBW"},
            {"type_id": "gilf", "type_name": "GILF"},
            {"type_id": "facial", "type_name": "Facial"},
            {"type_id": "deep-throat", "type_name": "Deep Throat"},
            {"type_id": "step-sister", "type_name": "Step Sister"},
            {"type_id": "step-daughter", "type_name": "Step Daughter"},
            {"type_id": "japanese", "type_name": "Japanese"},
            {"type_id": "voyeur", "type_name": "Voyeur"},
            {"type_id": "doctor", "type_name": "Doctor"},
            {"type_id": "big-dick", "type_name": "Big Dick"},
            {"type_id": "fetish", "type_name": "Fetish"},
            {"type_id": "family", "type_name": "Family"},
        ]
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent("big-tits", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            if str(pg) == "1":
                url = f"{self.host}/categories/{tid}/"
            else:
                url = f"{self.host}/categories/{tid}/{pg}/"

            html = self.fetch(url)
            if not html:
                return {"list": [], "page": pg, "pagecount": 999, "limit": 20, "total": 99999}

            videos = self._parse_list(html)
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 999,
                "limit": 20,
                "total": 99999,
            }
        except Exception as e:
            print(f"[categoryContent] error: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

    def _parse_list(self, html):
        videos = []
        item_pattern = re.compile(
            r'<a[^>]+href="((?:https?://yesporn\.vip)?/video/\d+/[^"]+)"[^>]*title="([^"]+)"[^>]*>'
            r'[\s\S]*?<img[^>]+(?:src|data-src|data-webp)="(https?://[^"]+?\.(?:jpg|jpeg|png|webp)[^"]*)"',
            re.I,
        )
        matches = item_pattern.findall(html)
        if not matches:
            links = re.findall(
                r'<a[^>]+href="((?:https?://yesporn\.vip)?/video/\d+/[^"]+)"[^>]*title="([^"]+)"',
                html,
                re.I,
            )
            for href, title in links:
                full_href = href if href.startswith("http") else self.host + href
                videos.append(
                    {
                        "vod_id": full_href,
                        "vod_name": title.strip(),
                        "vod_pic": "",
                        "vod_remarks": "",
                    }
                )
        else:
            for href, title, pic in matches:
                full_href = href if href.startswith("http") else self.host + href
                if pic.startswith("data:"):
                    pic = ""
                videos.append(
                    {
                        "vod_id": full_href,
                        "vod_name": title.strip(),
                        "vod_pic": pic,
                        "vod_remarks": "",
                    }
                )

        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

    def detailContent(self, ids):
        try:
            url = ids[0]
            if not url.startswith("http"):
                url = self.host + url

            html = self.fetch(url)
            if not html:
                return {"list": []}

            title_match = re.search(r"<title>([^<]+)</title>", html)
            title = title_match.group(1).strip() if title_match else "YesPornVIP"
            title = re.sub(r"\s*[-|].*$", "", title).strip()

            pic = ""
            pic_match = re.search(
                r'(https?://[^"\']+videos_screenshots[^"\']+\.(?:jpg|jpeg|png))',
                html,
            )
            if pic_match:
                pic = pic_match.group(1)

            plays = self._extract_plays(html, url)
            if plays:
                # 高清优先
                def _score(name):
                    m = re.search(r"(\d{3,4})", name or "")
                    return int(m.group(1)) if m else 0

                plays.sort(key=lambda x: _score(x[0]), reverse=True)
                play_from = "YesPorn"
                play_url = "#".join([f"{n}${u}" for n, u in plays])
            else:
                # 兜底：把详情页交给 player 再解析 / 嗅探
                play_from = "YesPorn"
                play_url = f"正片${url}"

            vod = {
                "vod_id": ids[0],
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": title,
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            }
            return {"list": [vod]}
        except Exception as e:
            print(f"[detailContent] error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        try:
            encoded_key = parse.quote(key)
            if str(pg) == "1":
                url = f"{self.host}/search/?q={encoded_key}"
            else:
                url = f"{self.host}/search/{pg}/?q={encoded_key}"

            html = self.fetch(url)
            if not html:
                return {"list": []}

            videos = self._parse_list(html)
            for v in videos:
                v["vod_remarks"] = "搜索"
            return {"list": videos}
        except Exception as e:
            print(f"[searchContent] error: {e}")
            return {"list": []}

    # ---------- KVS 解密（与 yt-dlp 一致） ----------
    def _kvs_license_token(self, license_code):
        code = (license_code or "").replace("$", "")
        license_values = [int(c) if c.isdigit() else 0 for c in code]
        mod = code.replace("0", "1")
        center = len(mod) // 2
        fronthalf = int(mod[: center + 1] or "0")
        backhalf = int(mod[center:] or "0")
        mod = str(4 * abs(fronthalf - backhalf))[: center + 1]
        token = []
        for index, current in enumerate(mod):
            cur = int(current)
            for offset in range(4):
                token.append((license_values[index + offset] + cur) % 10)
        return token

    def _kvs_real_url(self, video_url, license_code):
        if not video_url or not video_url.startswith("function/0/"):
            return video_url
        raw = video_url[len("function/0/") :]
        query = ""
        if "?" in raw:
            raw, query = raw.split("?", 1)
            query = "?" + query
        m = re.match(
            r"^(https?://[^/]+)(/get_file/\d+/)([a-f0-9]{32})(.*)$",
            raw,
            re.I,
        )
        if not m:
            return raw + query
        host, mid, hash32, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        license_token = self._kvs_license_token(license_code)
        hash_len = 32
        indices = list(range(hash_len))
        accum = 0
        for src in range(hash_len - 1, -1, -1):
            accum += license_token[src] if src < len(license_token) else 0
            dest = (src + accum) % hash_len
            indices[src], indices[dest] = indices[dest], indices[src]
        new_hash = "".join(hash32[i] for i in indices)
        return host + mid + new_hash + tail + query

    def _extract_plays(self, html, page_url):
        """从 flashvars 提取并解密各清晰度直链。"""
        plays = []
        if not html:
            return plays

        lm = re.search(r"license_code\s*:\s*'([^']+)'", html)
        license_code = lm.group(1) if lm else ""

        pairs = [
            ("video_url", "video_url_text"),
            ("video_alt_url", "video_alt_url_text"),
            ("video_alt_url2", "video_alt_url2_text"),
            ("video_alt_url3", "video_alt_url3_text"),
            ("video_alt_url4", "video_alt_url4_text"),
        ]
        seen = set()
        for key, text_key in pairs:
            m = re.search(key + r"\s*:\s*'(function/0/[^']+|/get_file/[^']+|https?:[^']+)'", html)
            if not m:
                continue
            u = m.group(1)
            if u.startswith("function/0/"):
                u = self._kvs_real_url(u, license_code)
            elif u.startswith("/get_file/"):
                u = self.host + u
            if not u or u in seen:
                continue
            # 跳过其它视频的 preview 广告
            if re.search(r"_preview\.mp4", u, re.I) and "/get_file/" in u:
                # 仍保留本片清晰度（路径含当前页 video id 时）
                vid = re.search(r"/video/(\d+)/", page_url)
                if vid and f"/{vid.group(1)}/" not in u:
                    continue
            label = ""
            tm = re.search(text_key + r"\s*:\s*'([^']+)'", html)
            if tm:
                label = tm.group(1).strip()
            if not label:
                if re.search(r"1080p", u, re.I):
                    label = "1080p"
                elif re.search(r"720p", u, re.I):
                    label = "720p"
                elif re.search(r"480p", u, re.I):
                    label = "480p"
                else:
                    label = "正片"
            seen.add(u)
            plays.append((label, u))
        return plays

    def playerContent(self, flag, id, vipFlags):
        """
        id 可能是：
        1) 已解密的 get_file mp4 直链
        2) 详情页地址（需再解析）
        """
        try:
            play_url = id
            # 若是详情页，再解析一次
            if "yesporn.vip/video/" in (id or "") and "/get_file/" not in id:
                html = self.fetch(id)
                plays = self._extract_plays(html or "", id)
                if plays:
                    def _score(name):
                        m = re.search(r"(\d{3,4})", name or "")
                        return int(m.group(1)) if m else 0

                    plays.sort(key=lambda x: _score(x[0]), reverse=True)
                    play_url = plays[0][1]
                else:
                    # 最后兜底嗅探
                    return {
                        "parse": 1,
                        "url": id,
                        "header": json.dumps(
                            {
                                "User-Agent": self.headers["User-Agent"],
                                "Referer": self.host + "/",
                            }
                        ),
                    }

            return {
                "parse": 0,
                "url": play_url,
                "header": json.dumps(
                    {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host + "/",
                    }
                ),
            }
        except Exception as e:
            print(f"[playerContent] error: {e}")
            return {
                "parse": 1,
                "url": id,
                "header": json.dumps(
                    {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host + "/",
                    }
                ),
            }

    def fetch(self, url, headers=None):
        try:
            import requests

            h = headers or self.headers
            r = requests.get(url, headers=h, timeout=15, verify=False)
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"[fetch] {url} error: {e}")
            return ""
