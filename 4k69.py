#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遮天TVBox九秘大师 · 4k69.com v21.0
修复：预解析重定向 + Range请求支持 + 保留末尾斜杠

【播放慢的原因】
4kporno链接会302重定向到fpvcdn.com CDN节点：
  https://www.4kporno.xxx/get_file/.../xxx_2160m.mp4/ 
  → 302 → https://fpvcdn.com/.../xxx_2160m.mp4
TVBox每次播放都要经历重定向，导致加载慢。

【修复方案】
1. detailContent中预解析HEAD请求，拿到真实CDN URL直接返回
2. playerContent增加Range: bytes=0- header（视频播放器必需）
3. 保留dlink解码URL末尾的/（去掉/会404）
"""

import sys
import re
import json
import time
import base64
import random
import requests
from urllib import parse
from html import unescape

sys.path.append("..")
from base.spider import Spider


class YuanTianShu:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    ua_pool = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    ]

    ad_patterns = [
        re.compile(r"https?://[^/\s]*ad[^/\s]*/[^\"\s]*\.ts", re.I),
        re.compile(r"https?://[^/\s]*advert[^/\s]*/[^\"\s]*\.ts", re.I),
        re.compile(r"https?://[^/\s]*banner[^/\s]*/[^\"\s]*\.ts", re.I),
        re.compile(r"https?://[^/\s]*tracker[^/\s]*/[^\"\s]*\.ts", re.I),
        re.compile(r"https?://[^/\s]*pop[^/\s]*/[^\"\s]*\.ts", re.I),
    ]

    RES_MAP = {
        "2160": "4K",
        "1080": "1080P",
        "720": "720P",
        "480": "480P",
        "360": "360P",
    }

    CATEGORIES = [
        ("3D", "3D"), ("4K", "4K"), ("69", "69"), ("ASMR", "ASMR"),
        ("Amateur", "Amateur"), ("Anal", "Anal"), ("Asian", "Asian"),
        ("BBW", "BBW"), ("BDSM", "BDSM"), ("Big-Ass", "Big Ass"),
        ("Big-Tits", "Big Tits"), ("Blonde", "Blonde"), ("Blowjob", "Blowjob"),
        ("Brunette", "Brunette"), ("Creampie", "Creampie"), ("Cumshot", "Cumshot"),
        ("Double-Penetration", "Double Penetration"), ("Ebony", "Ebony"),
        ("Fetish", "Fetish"), ("Gangbang", "Gangbang"), ("Group", "Group"),
        ("Hentai", "Hentai"), ("Interracial", "Interracial"), ("Japanese", "Japanese"),
        ("Latina", "Latina"), ("Lesbian", "Lesbian"), ("MILF", "MILF"),
        ("Masturbation", "Masturbation"), ("Orgy", "Orgy"), ("Outdoor", "Outdoor"),
        ("POV", "POV"), ("Pornstar", "Pornstar"), ("Public", "Public"),
        ("Redhead", "Redhead"), ("Rough", "Rough"), ("Solo", "Solo"),
        ("Squirt", "Squirt"), ("Teen", "Teen"), ("Threesome", "Threesome"),
        ("Toys", "Toys"), ("Vintage", "Vintage"), ("Webcam", "Webcam"),
    ]

    STUDIOS = [
        ("Brazzers", "Brazzers"), ("BangBros", "BangBros"),
        ("Naughty-America", "Naughty America"), ("Reality-Kings", "Reality Kings"),
        ("Tushy", "Tushy"), ("Blacked", "Blacked"), ("Vixen", "Vixen"),
        ("Digital-Playground", "Digital Playground"), ("Mofos", "Mofos"),
        ("TeamSkeet", "TeamSkeet"),
    ]

    PORNSTARS = [
        ("Riley-Reid", "Riley Reid"), ("Mia-Malkova", "Mia Malkova"),
        ("Lana-Rhoades", "Lana Rhoades"), ("Abella-Danger", "Abella Danger"),
        ("Angela-White", "Angela White"),
    ]

    def __init__(self):
        self.siteUrl = "https://4k69.com"
        self._init_session()
        self._cache = {}

    def _init_session(self):
        try:
            # 先写 cookie，再轻量预热；失败不阻塞后续列表请求
            self.session.cookies.set("age_verify", "1")
            self.session.cookies.set("ads_pageview", "1")
            h = dict(self.headers)
            h["User-Agent"] = random.choice(self.ua_pool)
            self.session.get(self.siteUrl, headers=h, timeout=10)
            h["Referer"] = self.siteUrl + "/"
        except Exception as e:
            print("[源天书] 定龙脉失败(可忽略): %s" % e)

    def fetch(self, url, headers=None, retry=3, delay=1):
        h = {**self.headers, **(headers or {})}
        h["User-Agent"] = random.choice(self.ua_pool)
        h["Referer"] = self.siteUrl + "/"
        last_err = None
        for i in range(retry):
            try:
                resp = self.session.get(url, headers=h, timeout=15)
                resp.encoding = "utf-8"
                if resp.status_code == 403 and len(resp.text) < 10000:
                    if "Just a moment" in resp.text or "challenges.cloudflare" in resp.text:
                        print("[源天书] CF拦截: %s" % url)
                        return ""
                if resp.status_code == 200:
                    if "\x00" in resp.text[:100]:
                        return ""
                    return resp.text
                elif resp.status_code in [403, 429, 503]:
                    time.sleep(delay * (i + 1) * 2)
            except Exception as e:
                last_err = e
            if i < retry - 1:
                time.sleep(delay * (i + 1))
        print("[源天书] 寻神源失败 [%s]: %s" % (url, last_err))
        return ""

    def _resolve_redirect(self, url, timeout=8):
        """
        兵字秘 · 预解析重定向
        对4kporno链接发送HEAD请求，直接拿到真实CDN URL
        省去TVBox播放时的302跳转延迟
        """
        if not url or not url.startswith("http"):
            return url
        try:
            h = {
                "User-Agent": random.choice(self.ua_pool),
                "Referer": self.siteUrl + "/",
                "Accept": "*/*",
            }
            resp = self.session.head(url, headers=h, timeout=timeout, allow_redirects=True)
            if resp.status_code in [200, 206] and resp.url != url:
                print("[重定向解析] %s -> %s" % (url[:60], resp.url[:60]))
                return resp.url
        except Exception as e:
            print("[重定向解析失败] %s: %s" % (url[:60], e))
        return url

    def _clean_m3u8(self, content):
        if not content:
            return content
        lines = content.split("\n")
        cleaned = []
        skip_next = False
        for line in lines:
            stripped = line.strip()
            is_ad = any(p.search(stripped) for p in self.ad_patterns)
            if is_ad:
                skip_next = True
                continue
            if skip_next and stripped.startswith("#EXTINF"):
                skip_next = False
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def _full_url(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return parse.urljoin(self.siteUrl, path)


class Spider(YuanTianShu, Spider):

    def init(self, extend=""):
        return True

    def getName(self):
        return "4k69"

    def destroy(self):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "latest", "type_name": "最新视频"},
            {"type_id": "trending", "type_name": "热门推荐"},
            {"type_id": "top", "type_name": "排行榜"},
        ]
        for slug, name in self.CATEGORIES:
            classes.append({"type_id": "categories|%s" % slug, "type_name": name})
        for slug, name in self.STUDIOS:
            classes.append({"type_id": "studios|%s" % slug, "type_name": name})
        for slug, name in self.PORNSTARS:
            classes.append({"type_id": "pornstars|%s" % slug, "type_name": name})
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        """首页推荐列表（多数 TVBox/FongMi 客户端依赖此方法）"""
        result = {"list": []}
        try:
            url = "%s/?link1=videos&page=latest&page_id=1" % self.siteUrl
            html = self.fetch(url, delay=1)
            if html and len(html) > 5000:
                result["list"] = self._extract_videos(html)
            if not result["list"]:
                # 备用：trending
                url2 = "%s/?link1=videos&page=trending&page_id=1" % self.siteUrl
                html2 = self.fetch(url2, delay=1)
                if html2 and len(html2) > 5000:
                    result["list"] = self._extract_videos(html2)
        except Exception as e:
            print("[homeVideoContent] 异常: %s" % e)
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 20}
        try:
            if tid in ["latest", "trending", "top"]:
                if tid == "trending":
                    result["pagecount"] = 3
                url = "%s/?link1=videos&page=%s&page_id=%s" % (self.siteUrl, tid, pg)
                html = self.fetch(url, delay=1)
                if html:
                    result["list"] = self._extract_videos(html)
                    if tid == "trending" and int(pg) >= 3:
                        result["pagecount"] = int(pg)
                return result

            parts = tid.split("|")
            if len(parts) == 2:
                main_type, sub_id = parts
            else:
                main_type, sub_id = tid, tid

            url = self._build_category_url(main_type, sub_id, pg)
            html = self.fetch(url, delay=2)

            if html and len(html) > 5000:
                result["list"] = self._extract_videos(html)
                if not result["list"]:
                    result["pagecount"] = int(pg)
                    return result
                next_page = int(pg) + 1
                has_next = ('page_id=%s"' % next_page in html or
                            "page_id=%s'" % next_page in html or
                            'page_id=%s' % next_page in html)
                result["pagecount"] = 999 if has_next else int(pg)
            else:
                print("[categoryContent] 获取失败: %s" % url)
                result["pagecount"] = int(pg)
        except Exception as e:
            print("[categoryContent] 者字秘兜底: %s" % e)
            result["pagecount"] = int(pg)
        return result

    def _fetch_watch_html(self, vid):
        strategies = [
            ("%s/?link1=watch&id=%s" % (self.siteUrl, vid), 1),
            ("%s/watch/%s" % (self.siteUrl, vid), 1),
            ("%s/?link1=watch&id=%s.html" % (self.siteUrl, vid.replace(".html", "")), 1),
            ("%s/watch/%s.html" % (self.siteUrl, vid.replace(".html", "")), 1),
        ]
        for url, delay in strategies:
            try:
                text = self.fetch(url, delay=delay)
                if text and len(text) > 5000 and "Just a moment" not in text:
                    return text
            except Exception:
                continue
        return ""

    def _extract_jwplayer_sources(self, html):
        """从 jwplayer sources 提取带 label 的多清晰度"""
        sources = {}
        try:
            for m in re.finditer(
                r'\{\s*"file"\s*:\s*"([^"]+)"\s*,\s*"label"\s*:\s*"([^"]+)"',
                html, re.I
            ):
                url, label = m.group(1), m.group(2).strip()
                if not url.startswith("http"):
                    continue
                label_l = label.lower()
                if label_l in ("4k", "2160", "2160p"):
                    q = "4K"
                elif "1080" in label_l:
                    q = "1080P"
                elif "720" in label_l:
                    q = "720P"
                elif "480" in label_l:
                    q = "480P"
                elif "360" in label_l:
                    q = "360P"
                else:
                    q = self._detect_quality(url)
                if q not in sources:
                    sources[q] = url
            # 兼容 label 在前
            for m in re.finditer(
                r'\{\s*"label"\s*:\s*"([^"]+)"\s*,\s*"file"\s*:\s*"([^"]+)"',
                html, re.I
            ):
                label, url = m.group(1).strip(), m.group(2)
                if not url.startswith("http"):
                    continue
                q = self._detect_quality(url)
                label_l = label.lower()
                if label_l in ("4k", "2160", "2160p"):
                    q = "4K"
                elif "1080" in label_l:
                    q = "1080P"
                elif "720" in label_l:
                    q = "720P"
                elif "480" in label_l:
                    q = "480P"
                if q not in sources:
                    sources[q] = url
        except Exception:
            pass
        return sources

    def _extract_all_sources(self, html):
        all_sources = {}
        # 优先 jwplayer 多清晰度（streamproxy / 4kporno 页）
        try:
            all_sources.update(self._extract_jwplayer_sources(html))
        except Exception:
            pass
        dlink_sources = self._extract_dlinks(html)
        for q, u in dlink_sources.items():
            if q not in all_sources:
                all_sources[q] = u
        extractors = [
            lambda h: self._extract_jsonld(h),
            lambda h: self._extract_cdn(h, "streamproxy"),
            lambda h: self._extract_cdn(h, "4kporno"),
            lambda h: self._extract_cdn(h, "fpvcdn"),
            lambda h: self._extract_cdn(h, "okcdn"),
            lambda h: self._extract_source_tag(h),
            lambda h: self._extract_generic_video(h),
            lambda h: self._extract_video_tag(h),
            lambda h: self._extract_data_attrs(h),
        ]
        for extractor in extractors:
            try:
                urls = extractor(html)
                for u in urls:
                    if not u or not u.startswith("http"):
                        continue
                    # 截断异常尾巴
                    u = re.split(r'["\'<\s]', u)[0]
                    q = self._detect_quality(u)
                    if q not in all_sources:
                        all_sources[q] = u
            except Exception:
                continue
        return all_sources

    def _unwrap_streamproxy(self, proxy_url, quality_hint=""):
        """
        streamproxy.php 会被播放器当网页嗅探失败。
        解出内层 4kporno 页面 → get_file/...mp4/ → 302 到 fpvcdn 真实直链。
        """
        try:
            from urllib.parse import urlparse, parse_qs, unquote
            qs = parse_qs(urlparse(proxy_url).query)
            inner = (qs.get("url") or [""])[0]
            if not inner:
                return ""
            inner = unquote(inner)
            if not inner.startswith("http"):
                return ""

            # 抓 4kporno 详情页拿 get_file
            h = {
                "User-Agent": random.choice(self.ua_pool),
                "Referer": self.siteUrl + "/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            resp = self.session.get(inner, headers=h, timeout=15)
            if resp.status_code != 200 or len(resp.text) < 1000:
                return ""
            page = resp.text

            # get_file/..._2160m.mp4/  注意必须保留末尾 /
            files = re.findall(
                r'https?://[^"\'\s<>]*get_file/[^"\'\s<>]+_\d+m\.mp4/?',
                page, re.I
            )
            # 去重并规范化：确保末尾有 /
            cleaned = []
            seen = set()
            for u in files:
                u = re.split(r'["\'<\s\?]', u)[0]
                if not u.endswith("/"):
                    u = u + "/"
                if u in seen:
                    continue
                seen.add(u)
                cleaned.append(u)
            if not cleaned:
                return ""

            # 按清晰度挑选
            def res_of(u):
                m = re.search(r'_(\d+)m\.mp4', u, re.I)
                return m.group(1) if m else ""

            qmap = {
                "4K": "2160", "2160P": "2160",
                "1080P": "1080", "HD": "1080",
                "720P": "720", "480P": "480", "360P": "360", "SD": "360",
            }
            want = qmap.get(quality_hint, "")
            chosen = ""
            if want:
                for u in cleaned:
                    if res_of(u) == want:
                        chosen = u
                        break
            if not chosen:
                # 优先 720 → 1080 → 480 → 2160
                for prefer in ("720", "1080", "480", "360", "2160"):
                    for u in cleaned:
                        if res_of(u) == prefer:
                            chosen = u
                            break
                    if chosen:
                        break
            if not chosen:
                chosen = cleaned[0]

            # HEAD/GET 跟随 302 拿到 fpvcdn 最终地址（保留当前出口 IP 签名）
            final = self._resolve_redirect(chosen, timeout=12)
            if final and final.startswith("http"):
                return final
            return chosen
        except Exception as e:
            print("[unwrap_streamproxy] %s" % e)
            return ""

    def _resolve_play_url(self, vid, quality_hint=""):
        """播放时现场解析：okcdn 保证 srcIp；streamproxy 展开为 get_file/fpvcdn"""
        html = self._fetch_watch_html(vid)
        if not html:
            return ""
        sources = self._extract_all_sources(html)
        if not sources:
            return ""

        def _pick(q):
            u = sources.get(q)
            if not u:
                return ""
            if "streamproxy" in u or "phoenixcdn" in u or "hornyhill" in u:
                real = self._unwrap_streamproxy(u, q or quality_hint)
                return real or u
            if "get_file" in u:
                # 保留末尾 /
                if u.endswith(".mp4"):
                    u = u + "/"
                return self._resolve_redirect(u)
            return self._resolve_redirect(u)

        if quality_hint:
            url = _pick(quality_hint)
            if url:
                return url
        for q in ["720P", "1080P", "480P", "4K", "HD", "360P", "SD", "AUTO", "未知"]:
            url = _pick(q)
            if url:
                return url
        return _pick(list(sources.keys())[0])

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if ids else ""
        if not vid:
            return result

        html = self._fetch_watch_html(vid)
        if not html:
            return result

        title = "未知视频"
        try:
            m = re.search(r"<title>([^<]+)</title>", html)
            if m:
                title = m.group(1).strip().replace(" - 4K69.com", "").replace("4K69.com", "").strip()
                title = unescape(title)
        except Exception:
            pass

        all_sources = self._extract_all_sources(html)

        # 仅保留页面真实出现的清晰度，不伪造带错误 sig 的链接
        # 播放地址用延迟解析 token：vid||QUALITY，避免详情阶段签名过期 / IP 不一致
        episodes = []
        quality_order = ["4K", "1080P", "HD", "720P", "480P", "360P", "SD", "AUTO", "未知"]
        for q in quality_order:
            if q in all_sources:
                episodes.append("%s$%s||%s" % (q, vid, q))
        for q in all_sources:
            if q not in quality_order:
                episodes.append("%s$%s||%s" % (q, vid, q))

        # 若完全没解析到源，仍给一个默认 token，播放时再试
        if not episodes:
            episodes.append("默认$%s||AUTO" % vid)

        play_url_str = "#".join(episodes)

        source_type = "4K直链"
        result["list"].append({
            "vod_id": vid,
            "vod_name": title,
            "vod_play_from": source_type,
            "vod_play_url": play_url_str,
            "vod_content": title,
        })
        return result

    def _as_media_url(self, url):
        """无媒体后缀的直链加 #.mp4，避免被当网页嗅探；fragment 不影响请求"""
        if not url or not url.startswith("http"):
            return url
        path = url.split("?", 1)[0].split("#", 1)[0].lower()
        if path.endswith((".mp4", ".m3u8", ".mkv", ".flv", ".ts", ".webm")):
            return url
        # 形如 xxx.mp4/ 也算
        if path.rstrip("/").endswith((".mp4", ".m3u8", ".mkv", ".flv", ".ts")):
            return url
        base = url.split("#", 1)[0]
        return base + "#.mp4"

    def playerContent(self, flag, id, vipFlags):
        try:
            if not id:
                return {"parse": 0, "jx": 0, "url": "", "header": {}}

            ua = random.choice(self.ua_pool)
            header = {
                "User-Agent": ua,
                "Referer": "https://www.4kporno.xxx/",
                "Accept": "*/*",
            }

            play_url = id

            # 延迟解析：vid||QUALITY
            if "||" in id and not id.startswith("http"):
                parts = id.split("||", 1)
                vid = parts[0].strip()
                qhint = parts[1].strip() if len(parts) > 1 else ""
                resolved = self._resolve_play_url(vid, qhint)
                if resolved:
                    play_url = resolved
                else:
                    print("[playerContent] 解析失败 vid=%s" % vid)
                    return {"parse": 0, "jx": 0, "url": "", "header": header}

            # 若仍是 streamproxy（解包失败），再试一次解包
            if "streamproxy" in play_url or "phoenixcdn" in play_url:
                real = self._unwrap_streamproxy(play_url, "")
                if real:
                    play_url = real

            # get_file 保留尾斜杠再跟 302
            if "get_file" in play_url:
                if play_url.rstrip("/").endswith(".mp4") and not play_url.endswith("/"):
                    play_url = play_url + "/"
                play_url = self._resolve_redirect(play_url)
                header["Referer"] = "https://www.4kporno.xxx/"

            if "okcdn" in play_url:
                header["Referer"] = self.siteUrl + "/"

            if "embed" in play_url and "okcdn" not in play_url and "fpvcdn" not in play_url:
                return {"parse": 1, "jx": 0, "url": play_url, "header": header}

            # 禁止把 streamproxy 交给播放器（会被 WebSniff 当网页）
            if "streamproxy" in play_url or "phoenixcdn" in play_url:
                print("[playerContent] streamproxy 解包失败，放弃该地址")
                return {"parse": 0, "jx": 0, "url": "", "header": header}

            play_url = self._as_media_url(play_url)

            # 关键字段：format 告知客户端这是视频直链，跳过网页嗅探
            return {
                "parse": 0,
                "jx": 0,
                "url": play_url,
                "header": header,
                "format": "video/mp4",
                "media_info": "video/mp4",
            }
        except Exception as e:
            print("[playerContent] 异常: %s" % e)
            return {"parse": 0, "jx": 0, "url": "", "header": {}}

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1}
        if not key:
            return result
        try:
            # 1) 优先：关键词匹配分类/工作室/女优（站点 search 常被 CF 拦截）
            key_norm = key.strip().lower().replace(" ", "-").replace("_", "-")
            mapped_url = None
            for slug, name in self.CATEGORIES:
                if key_norm == slug.lower() or key.lower() == name.lower():
                    mapped_url = self._build_category_url("categories", slug, pg)
                    break
            if not mapped_url:
                for slug, name in self.STUDIOS:
                    if key_norm == slug.lower() or key.lower() == name.lower():
                        mapped_url = self._build_category_url("studios", slug, pg)
                        break
            if not mapped_url:
                for slug, name in self.PORNSTARS:
                    if key_norm == slug.lower() or key.lower() == name.lower():
                        mapped_url = self._build_category_url("pornstars", slug, pg)
                        break

            html = ""
            if mapped_url:
                html = self.fetch(mapped_url, delay=1)

            # 2) 尝试官方搜索（可能被 CF）
            if not html or len(html) < 5000:
                search_urls = [
                    "%s/?link1=search&q=%s&page=%s" % (self.siteUrl, parse.quote(key), pg),
                    "%s/search/%s/" % (self.siteUrl, parse.quote(key)),
                ]
                for url in search_urls:
                    html = self.fetch(url, delay=2)
                    if html and len(html) > 5000 and "Just a moment" not in html:
                        break
                    html = ""

            if html and len(html) > 5000:
                result["list"] = self._extract_videos(html)
                next_page = int(pg) + 1
                has_next = (
                    'page_id=%s"' % next_page in html
                    or "page_id=%s'" % next_page in html
                    or 'page=%s"' % next_page in html
                )
                result["pagecount"] = 999 if has_next else int(pg)
        except Exception as e:
            print("[searchContent] 异常: %s" % e)
        return result

    def localProxy(self, param):
        try:
            import http.server
            import socketserver
            from urllib.parse import parse_qs, urlparse

            class ProxyHandler(http.server.BaseHTTPRequestHandler):
                def log_message(self, format, *args):
                    pass

                def do_GET(self):
                    parsed = urlparse(self.path)
                    params = parse_qs(parsed.query)

                    if parsed.path == "/proxy":
                        try:
                            real_url = base64.b64decode(params.get("url", [""])[0]).decode()
                            referer = base64.b64decode(params.get("ref", [""])[0]).decode()

                            h = {
                                "User-Agent": random.choice(self.ua_pool),
                                "Referer": referer,
                                "Accept": "*/*",
                            }
                            resp = requests.get(real_url, headers=h, stream=True, timeout=15)

                            content_type = resp.headers.get("Content-Type", "")

                            if "mpegurl" in content_type or real_url.endswith(".m3u8"):
                                content = resp.text
                                cleaned = self._clean_m3u8(content)
                                self.send_response(200)
                                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                                self.end_headers()
                                self.wfile.write(cleaned.encode())
                            else:
                                self.send_response(resp.status_code)
                                for key, val in resp.headers.items():
                                    if key.lower() not in ["content-encoding", "transfer-encoding", "content-length"]:
                                        self.send_header(key, val)
                                self.end_headers()
                                for chunk in resp.iter_content(8192):
                                    self.wfile.write(chunk)
                        except Exception as e:
                            self.send_response(500)
                            self.end_headers()
                            self.wfile.write(str(e).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

            import threading
            def run_proxy():
                with socketserver.TCPServer(("127.0.0.1", 9979), ProxyHandler) as httpd:
                    httpd.serve_forever()

            t = threading.Thread(target=run_proxy, daemon=True)
            t.start()

            return [200, "application/json", json.dumps({
                "proxy": "http://127.0.0.1:9979",
                "status": "running"
            })]
        except Exception as e:
            return [500, "application/json", json.dumps({"error": str(e)})]

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        # 直链 CDN / 代理（无后缀也会被当网页嗅探，必须识别为视频）
        if any(k in u for k in (
            "okcdn", "4kporno", "fpvcdn", "streamproxy",
            "phoenixcdn", "hornyhill", "get_file",
        )):
            return True
        path = u.split("?", 1)[0].split("#", 1)[0]
        return path.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".webm"))

    def manualVideoCheck(self):
        # True：强制走 isVideoFormat，避免把 streamproxy 当网页嗅探
        return True

    def _build_category_url(self, main_type, sub_id, pg):
        base = self.siteUrl
        if main_type == "pornstars":
            sub_id = sub_id.replace("-", "+")
        if main_type == "categories":
            page_type = "category"
        elif main_type == "studios":
            page_type = "studio"
        elif main_type == "pornstars":
            page_type = "pornstar"
        else:
            page_type = "category"
        return "%s/?link1=videos&page=%s&id=%s&page_id=%s" % (base, page_type, sub_id, pg)

    def _extract_dlinks(self, html):
        sources = {}
        if not html:
            return sources
        dlinks = re.findall(r'[?&]dlink=([A-Za-z0-9+/=]+)', html)
        dlinks += re.findall(r'dlink[=:]\s*["\']([A-Za-z0-9+/=]+)["\']', html)
        for dlink in dlinks:
            try:
                decoded = base64.b64decode(dlink).decode('utf-8')
                if not decoded.startswith("http"):
                    continue
                m = re.search(r'_(\d+)m\.mp4', decoded)
                if m:
                    res = m.group(1)
                    quality = self.RES_MAP.get(res, "%sP" % res)
                else:
                    quality = "未知"
                if quality not in sources:
                    sources[quality] = decoded
            except:
                continue
        return sources

    def _extract_videos(self, html):
        videos = []
        if not html or len(html) < 500:
            return videos
        try:
            all_ids = list(dict.fromkeys(
                re.findall(r'4k69\.com/watch/([^"\'\s<>]+)', html)
            ))
            for vid_id in all_ids[:50]:
                try:
                    pattern = r'<a[^>]*href=["\'][^"\']*watch/%s["\'][^>]*>.*?</a>' % re.escape(vid_id)
                    block_match = re.search(pattern, html, re.S)
                    if not block_match:
                        continue
                    block = block_match.group(0)
                    pic = ""
                    pic_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block)
                    if pic_m:
                        pic = pic_m.group(1)
                    title = ""
                    title_m = re.search(r'alt=["\']([^"\']*)["\']', block)
                    if title_m:
                        title = title_m.group(1)
                    if not title:
                        title_m2 = re.search(r'title=["\']([^"\']*)["\']', block)
                        if title_m2:
                            title = title_m2.group(1)
                    videos.append({
                        "vod_id": vid_id,
                        "vod_name": unescape(title.strip()),
                        "vod_pic": pic,
                        "vod_remarks": "4K"
                    })
                except:
                    continue
        except Exception as e:
            print("[_extract_videos] 精确模式失败: %s" % e)
        if not videos:
            try:
                for m in re.finditer(
                    r'<a[^>]*href=["\'][^"\']*watch/([^"\'\s<>]+)["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*)["\']',
                    html, re.S
                ):
                    videos.append({
                        "vod_id": m.group(1),
                        "vod_name": unescape(m.group(3).strip()),
                        "vod_pic": m.group(2),
                        "vod_remarks": "4K"
                    })
            except Exception as e:
                print("[_extract_videos] 宽松模式失败: %s" % e)
        if not videos:
            try:
                for m in re.finditer(r'href=["\'][^"\']*watch/([^"\'\s<>]+)["\'][^>]*>([^<]+)</a>', html, re.S):
                    vid = m.group(1)
                    title = m.group(2).strip()
                    if title and len(title) > 2:
                        videos.append({
                            "vod_id": vid,
                            "vod_name": unescape(title),
                            "vod_pic": "",
                            "vod_remarks": "4K"
                        })
            except Exception as e:
                print("[_extract_videos] 极简模式失败: %s" % e)
        return videos

    def _extract_jsonld(self, html):
        urls = []
        try:
            m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            if m:
                data = json.loads(m.group(1))
                url = data.get("contentUrl", "")
                if url:
                    urls.append(url)
        except:
            pass
        return urls

    def _extract_cdn(self, html, cdn_name):
        return re.findall(r'https?://[^"\'\s<>]*%s[^"\'\s<>]*' % cdn_name, html)

    def _extract_source_tag(self, html):
        return re.findall(r'<source[^>]+src=["\']?([^"\']+)["\']?', html)

    def _extract_generic_video(self, html):
        m = re.search(r'https?://[^"\'\s<>]+\.(?:mp4|m3u8)(?:\?[^"\'\s<>]*)?', html)
        return [m.group(0)] if m else []

    def _extract_video_tag(self, html):
        m = re.search(r'<video[^>]+src=["\']?([^"\']+)["\']?', html, re.I)
        return [m.group(1)] if m else []

    def _extract_data_attrs(self, html):
        return re.findall(r'data-(?:src|url)=["\']?(https?://[^"\']+)["\']?', html)

    def _detect_quality(self, url):
        if not url:
            return "未知"
        url_lower = url.lower()
        # streamproxy: q=2160p / q=720p（优先，避免域名 4kporno 误判）
        m = re.search(r'[?&]q=(\d+)p', url_lower)
        if m:
            res = m.group(1)
            return self.RES_MAP.get(res, "%sP" % res)
        m = re.search(r'_(\d+)m\.mp4', url_lower)
        if m:
            res = m.group(1)
            return self.RES_MAP.get(res, "%sP" % res)
        m = re.search(r'[?&]type=(\d+)', url_lower)
        if m:
            type_map = {"4": "4K", "3": "1080P", "5": "HD", "2": "720P", "1": "480P", "0": "360P", "7": "AUTO", "6": "SD"}
            return type_map.get(m.group(1), "%sP" % m.group(1))
        # 路径中的分辨率数字（不要用 "4k" 子串，会误匹配 4kporno 域名）
        m = re.search(r'(?:^|[^\w])(2160|1080|720|480|360)p?(?:[^\d]|$)', url_lower)
        if m:
            res = m.group(1)
            return self.RES_MAP.get(res, "%sP" % res)
        if re.search(r'(?:^|[^\w])4k(?:[^\w]|$)', url_lower):
            return "4K"
        return "未知"


if __name__ == "__main__":
    spider = Spider()
    print(json.dumps(spider.homeContent({}), ensure_ascii=False, indent=2))
