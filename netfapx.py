#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【遮天法 · 道宫境】netfapx.net TVBox 爬虫 v8
修复：嵌入播放器预解析（dsvplay/luluvdo等）
"""

import sys
import re
import json
import time
import base64
import requests
from urllib import parse
from bs4 import BeautifulSoup

sys.path.append("..")
from base.spider import Spider

RE_WATCH_ID = re.compile(r"/watch/\d+/?$")
RE_WATCH_ACTOR = re.compile(r"/watch/actor/[^/]+")
RE_VIDEO_EXT = re.compile(r"\.(m3u8|mp4|flv|mkv|ts|avi|mov)$", re.I)
RE_PLAYER_VAR = re.compile(r"var\s+player_[a-zA-Z_]*\s*=\s*({.+?});")
RE_VIDEO_URL = re.compile(r"(?:videoUrl|video_url|sourceUrl|src|file)\s*[:=]\s*[\"']([^\"']+\.(?:m3u8|mp4|flv))[\"']")
RE_JWPLAYER = re.compile(r"jwplayer\(\".*?\"\)\.setup\({.*?file:\s*[\"']([^\"']+)[\"']", re.DOTALL)
RE_BASE64 = re.compile(r"[\"']([A-Za-z0-9+/]{50,}={0,2})[\"']")
RE_EVAL = re.compile(r"eval\((function\(p,a,c,k,e,d\).+?)\)")
RE_HTTP_VIDEO = re.compile(r"(https?://[^\s\"']+\.(?:m3u8|mp4|flv))")
RE_IFRAME_SRC = re.compile(r"<iframe[^>]+src=[\"']([^\"']+)[\"']")
RE_JS_M3U8 = re.compile(r"[\"'](https?://[^\"']+\.m3u8[^\"']*)[\"']")
RE_JS_MP4 = re.compile(r"[\"'](https?://[^\"']+\.mp4[^\"']*)[\"']")
RE_JS_URL = re.compile(r"(?:url|file|src)\s*[:=]\s*[\"'](https?://[^\"']+)[\"']")
RE_CDN_LINK = re.compile(r"(https?://[^\s\"'<>]+(?:key|token|exp|sig)=[^\s\"'<>]+)")


class YuanTianShu(Spider):
    session = requests.Session()
    proxyPort = 9979
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def fetch(self, url, headers=None, timeout=15):
        h = {**self.headers, **(headers or {})}
        for i in range(3):
            try:
                resp = self.session.get(url, headers=h, timeout=timeout, allow_redirects=True)
                resp.raise_for_status()
                resp.encoding = "utf-8"
                return resp.text
            except Exception as e:
                if i == 2:
                    print(f"[源天书] 定龙脉失败: {url} | {e}")
                    return ""
                time.sleep(2 ** i)


class ZheTian_Master(YuanTianShu):
    def __init__(self):
        self.siteUrl = "https://netfapx.net"
        self.classes = [
            {"type_id": "latest-videos", "type_name": "最新视频"},
            {"type_id": "latest-videos::hot", "type_name": "最热"},
            {"type_id": "pornstars-1", "type_name": "Pornstars"},
            {"type_id": "search::big+ass", "type_name": "Big Ass"},
            {"type_id": "search::big+tits", "type_name": "Big Tits"},
            {"type_id": "search::big+cock", "type_name": "Big Cock"},
            {"type_id": "search::anal", "type_name": "Anal"},
            {"type_id": "search::teen", "type_name": "Teen"},
            {"type_id": "search::lesbian", "type_name": "Lesbian"},
            {"type_id": "search::milf", "type_name": "MILF"},
            {"type_id": "search::ebony", "type_name": "Ebony"},
            {"type_id": "search::asian", "type_name": "Asian"},
            {"type_id": "search::latina", "type_name": "Latina"},
            {"type_id": "search::squirt", "type_name": "Squirt"},
            {"type_id": "search::interracial", "type_name": "Interracial"},
            {"type_id": "search::double+penetration", "type_name": "Double Penetration"},
            {"type_id": "search::threesome", "type_name": "Threesome"},
            {"type_id": "search::massage", "type_name": "Massage"},
            {"type_id": "search::blonde", "type_name": "Blonde"},
            {"type_id": "search::brunette", "type_name": "Brunette"},
            {"type_id": "search::blowjob", "type_name": "Blowjob"},
            {"type_id": "search::creampie", "type_name": "Creampie"},
            {"type_id": "search::facial", "type_name": "Facial"},
            {"type_id": "search::casting", "type_name": "Casting"},
            {"type_id": "search::step", "type_name": "Step"},
            {"type_id": "search::hardcore", "type_name": "Hardcore"},
            {"type_id": "search::deepthroat", "type_name": "Deepthroat"},
            {"type_id": "search::pov", "type_name": "POV"},
            {"type_id": "search::erotic", "type_name": "Erotic"},
            {"type_id": "search::small+tits", "type_name": "Small Tits"},
            {"type_id": "search::public", "type_name": "Public"},
        ]

    def init(self, extend=""):
        print("[遮天大师] v8 已激活")
        return True

    def isVideoFormat(self, url):
        return bool(RE_VIDEO_EXT.search(url)) if url else False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes}


    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg) if pg else 1
            if tid.startswith("search::"):
                keyword = tid.replace("search::", "")
                url = f"{self.siteUrl}/page/{pg}/?s={keyword}&filter=random" if pg > 1 else f"{self.siteUrl}/?s={keyword}&filter=random"
                is_pstar_list = False
            elif tid == "pornstars-1":
                url = f"{self.siteUrl}/pornstars-1/page/{pg}/" if pg > 1 else f"{self.siteUrl}/pornstars-1/"
                is_pstar_list = True
            elif tid == "latest-videos::hot":
                base = f"{self.siteUrl}/latest-videos/"
                url = f"{base}page/{pg}/?filter=random" if pg > 1 else f"{base}?filter=random"
                is_pstar_list = False
            elif tid == "latest-videos":
                base = f"{self.siteUrl}/latest-videos/"
                url = f"{base}page/{pg}/" if pg > 1 else base
                is_pstar_list = False
            else:
                base = f"{self.siteUrl}/{tid}/"
                url = f"{base}page/{pg}/?filter=random" if pg > 1 else f"{base}?filter=random"
                is_pstar_list = False

            print(f"[斗字秘] 抓取: {url}")
            html = self.fetch(url)
            if not html:
                return {"list": [], "page": pg, "pagecount": 999}

            print(f"[斗字秘] HTML长度: {len(html)}")
            soup = BeautifulSoup(html, "html.parser")
            videos = []

            selectors = [
                "article.post", "article", "div.video-item", "div.video", "div.item",
                ".thumb-block", ".content-block", ".post-item", ".video-block",
                ".video-list .item", ".videos .video", ".grid .cell",
                ".actor-item", ".pornstar-item", ".model-item", ".star-item",
            ]
            items = []
            for sel in selectors:
                items = soup.select(sel)
                if items:
                    print(f"[斗字秘] 选择器命中: {sel} -> {len(items)} 个")
                    break

            if not items:
                print("[斗字秘] 选择器未命中，尝试a标签直接匹配")
                if is_pstar_list:
                    items = soup.find_all("a", href=RE_WATCH_ACTOR)
                else:
                    all_watch = soup.find_all("a", href=re.compile(r"/watch/"))
                    items = [a for a in all_watch if not RE_WATCH_ACTOR.search(a.get("href", ""))]
                print(f"[斗字秘] a标签匹配: {len(items)} 个")

            if not items:
                print("[斗字秘] 进入正则终极回退")
                return self._regex_fallback(html, pg, is_pstar_list)

            for item in items:
                try:
                    a = item if item.name == "a" else item.select_one("a")
                    if not a:
                        continue
                    href = a.get("href", "")
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = self.siteUrl + href
                    elif not href.startswith("http"):
                        href = parse.urljoin(self.siteUrl, href)

                    is_actor_page = RE_WATCH_ACTOR.search(href)
                    is_video_page = RE_WATCH_ID.search(href)

                    if not is_actor_page and not is_video_page:
                        continue

                    title = a.get("title", "")
                    if not title:
                        img = a.select_one("img")
                        if img:
                            title = img.get("alt", "") or img.get("title", "")
                    if not title:
                        for tsel in ["h2", "h3", "h4", ".title", ".entry-title", "span", "div", "p"]:
                            t = item.select_one(tsel)
                            if t:
                                title = t.get_text(strip=True)
                                break
                    if not title:
                        title = href.rstrip("/").split("/")[-1].replace("-", " ").title()

                    pic = ""
                    img = item.select_one("img") if item.name != "a" else a.select_one("img")
                    if img:
                        for attr in ["data-src", "data-original", "src", "data-lazy-src"]:
                            pic = img.get(attr, "")
                            if pic:
                                break
                    if pic and pic.startswith("/"):
                        pic = self.siteUrl + pic
                    elif pic and not pic.startswith("http"):
                        pic = parse.urljoin(self.siteUrl, pic)

                    remarks = ""
                    for rsel in [".duration", ".time", ".length", ".video-duration", ".length-badge", ".views", ".quality", ".count", ".videos-count"]:
                        r = item.select_one(rsel)
                        if r:
                            remarks = r.get_text(strip=True)
                            break
                    if not remarks:
                        remarks = "Pornstar" if is_actor_page else "HD"

                    if is_actor_page:
                        vod_id = f"actor::{href}"
                    else:
                        vod_id = f"video::{href}"

                    videos.append({
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remarks,
                    })
                except Exception:
                    continue

            print(f"[斗字秘] 解析完成: {len(videos)} 条")
            pagecount = 999
            if len(videos) == 0 and pg > 1:
                pagecount = pg - 1
            return {"list": videos, "page": pg, "pagecount": pagecount}

        except Exception as e:
            print(f"[斗字秘] 异常: {e}")
            return {"list": [], "page": pg, "pagecount": 999}


    def _regex_fallback(self, html, pg, is_pstar_list=False):
        videos = []
        if is_pstar_list:
            pattern = re.compile(r'<a[^>]+href=["\']([^"\']*/watch/actor/[^"\']+)["\'][^>]*>.*?<img[^>]+(?:src|data-src|data-original)=["\']([^"\']*)["\'][^>]*>.*?<(h[2-6]|span|div|p)[^>]*>([^<]+)</\3', re.S | re.I)
            for m in pattern.finditer(html):
                href, pic, _, title = m.groups()
                if href:
                    if href.startswith("/"):
                        href = self.siteUrl + href
                    elif not href.startswith("http"):
                        href = parse.urljoin(self.siteUrl, href)
                    videos.append({
                        "vod_id": f"actor::{href}",
                        "vod_name": (title or "Pornstar").strip(),
                        "vod_pic": pic or "",
                        "vod_remarks": "Pornstar",
                    })
        else:
            pattern = re.compile(r'<a[^>]+href=["\']([^"\']*/watch/\d+/?)["\'][^>]*>.*?<img[^>]+(?:src|data-src|data-original)=["\']([^"\']*)["\'][^>]*>.*?<(h[2-6]|span|div|p)[^>]*>([^<]+)</\3', re.S | re.I)
            for m in pattern.finditer(html):
                href, pic, _, title = m.groups()
                if href:
                    if href.startswith("/"):
                        href = self.siteUrl + href
                    elif not href.startswith("http"):
                        href = parse.urljoin(self.siteUrl, href)
                    videos.append({
                        "vod_id": f"video::{href}",
                        "vod_name": (title or "Video").strip(),
                        "vod_pic": pic or "",
                        "vod_remarks": "HD",
                    })
            if not videos:
                pattern2 = re.compile(r'<a[^>]+href=["\']([^"\']*/watch/\d+/?)["\'][^>]*title=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+(?:src|data-src|data-original)=["\']([^"\']*)["\']', re.S | re.I)
                for m in pattern2.finditer(html):
                    href, title, pic = m.groups()
                    if href.startswith("/"):
                        href = self.siteUrl + href
                    elif not href.startswith("http"):
                        href = parse.urljoin(self.siteUrl, href)
                    videos.append({
                        "vod_id": f"video::{href}",
                        "vod_name": title.strip(),
                        "vod_pic": pic or "",
                        "vod_remarks": "HD",
                    })

        print(f"[斗字秘·正则回退] 匹配: {len(videos)} 条")
        pagecount = 999 if videos else (pg - 1 if pg > 1 else 999)
        return {"list": videos, "page": pg, "pagecount": pagecount}


    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            if vod_id.startswith("actor::"):
                return self._detail_actor(vod_id)
            else:
                return self._detail_video(vod_id)
        except Exception as e:
            print(f"[前字秘] 异常: {e}")
            return {"list": []}

    def _detail_video(self, vod_id):
        url = vod_id.replace("video::", "")
        print(f"[前字秘] 视频详情: {url}")
        html = self.fetch(url)
        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        title = ""
        for sel in ["h1.title", "h1.entry-title", ".video-title h1", "h1", ".post-title"]:
            h1 = soup.select_one(sel)
            if h1:
                title = h1.get_text(strip=True)
                break

        pic = ""
        meta_img = soup.select_one('meta[property="og:image"]')
        if meta_img:
            pic = meta_img.get("content", "")
        if not pic:
            for sel in [".video-player img", ".poster img", ".featured-image img"]:
                poster = soup.select_one(sel)
                if poster:
                    pic = poster.get("src") or poster.get("data-src", "")
                    break

        desc = ""
        meta_desc = soup.select_one('meta[property="og:description"]')
        if meta_desc:
            desc = meta_desc.get("content", "")

        tags = []
        for sel in [".video-tags a", ".tags a", ".categories a", "a[rel='tag']", ".models a", ".pornstars a", ".actors a"]:
            for tag in soup.select(sel):
                t = tag.get_text(strip=True)
                if t and t not in tags:
                    tags.append(t)

        play_url = self._extract_play_url(html, soup, url)
        display = play_url[:120] + "..." if play_url and len(play_url) > 120 else play_url
        print(f"[前字秘] 播放地址: {display}")

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": title or "未知视频",
                "vod_pic": pic,
                "vod_content": desc,
                "vod_actor": ",".join(tags[:8]),
                "vod_play_from": "线路1",
                "vod_play_url": play_url or "第1集$",
            }]
        }


    def _detail_actor(self, vod_id):
        url = vod_id.replace("actor::", "")
        print(f"[列字秘] 女优作品页: {url}")
        html = self.fetch(url)
        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        name = ""
        h1 = soup.select_one("h1")
        if h1:
            name = h1.get_text(strip=True)

        pic = ""
        for sel in [".avatar img", ".profile-pic img", ".actor-avatar img", ".pornstar-avatar img", ".featured-image img"]:
            img = soup.select_one(sel)
            if img:
                pic = img.get("src") or img.get("data-src", "")
                break

        videos = []
        items = soup.select("article, div.video-item, .thumb-block, .post-item, .video-block, .item")
        if not items:
            items = soup.find_all("a", href=RE_WATCH_ID)

        for item in items:
            a = item if item.name == "a" else item.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            if not href:
                continue
            if not href.startswith("http"):
                href = parse.urljoin(self.siteUrl, href)
            if RE_WATCH_ACTOR.search(href) or not RE_WATCH_ID.search(href):
                continue

            title = a.get("title", "")
            if not title:
                img = a.select_one("img")
                if img:
                    title = img.get("alt", "")
            if not title:
                title = href.rstrip("/").split("/")[-1].replace("-", " ").title()

            if title:
                videos.append(f"{title}${href}")

        if not videos:
            pattern = re.compile(r'<a[^>]+href=["\']([^"\']*/watch/\d+/?)["\'][^>]*>.*?<img[^>]+(?:src|data-src|data-original)=["\']([^"\']*)["\'][^>]*>.*?<(h[2-6]|span|div|p)[^>]*>([^<]+)</\3', re.S | re.I)
            for m in pattern.finditer(html):
                href, _, _, title = m.groups()
                if href:
                    if not href.startswith("http"):
                        href = parse.urljoin(self.siteUrl, href)
                    if title:
                        videos.append(f"{title.strip()}${href}")

        play_url = "#".join(videos) if videos else ""
        print(f"[列字秘] 女优作品: {len(videos)} 部")

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": name or "Pornstar",
                "vod_pic": pic,
                "vod_content": f"{name} 的作品合集" if name else "",
                "vod_actor": name or "",
                "vod_play_from": "作品列表",
                "vod_play_url": play_url or "第1集$",
            }]
        }


    def _extract_play_url(self, html, soup, page_url):
        # 第1层: video标签
        video = soup.select_one("video")
        if video:
            src = video.get("src") or video.get("data-src", "")
            if src and self.isVideoFormat(src):
                return f"第1集${src}"
            source = video.select_one("source")
            if source:
                src = source.get("src") or source.get("data-src", "")
                if src and self.isVideoFormat(src):
                    return f"第1集${src}"

        # 第2层: iframe嵌入 → 预解析嵌入页
        iframe_src = ""
        iframe = soup.select_one("iframe")
        if iframe:
            iframe_src = iframe.get("src", "")
        if not iframe_src:
            m = RE_IFRAME_SRC.search(html)
            if m:
                iframe_src = m.group(1)
        if iframe_src:
            if iframe_src.startswith("//"):
                iframe_src = "https:" + iframe_src
            real_url = self._parse_embed_page(iframe_src)
            if real_url:
                return f"第1集${real_url}"
            return f"第1集${iframe_src}"

        # 第3层: player变量
        m = RE_PLAYER_VAR.search(html)
        if m:
            try:
                data = json.loads(m.group(1).rstrip(";"))
                url = data.get("url") or data.get("file", "")
                if url:
                    return f"第1集${url}"
            except:
                pass

        # 第4层: videoUrl/sourceUrl
        m = RE_VIDEO_URL.search(html)
        if m:
            return f"第1集${m.group(1)}"

        # 第5层: data-video
        dv = soup.select_one("[data-video]")
        if dv:
            src = dv.get("data-video", "")
            if src:
                return f"第1集${src}"

        # 第6层: data属性
        for attr in ["data-url", "data-src", "data-link", "data-file", "data-play"]:
            el = soup.select_one(f"[{attr}]")
            if el:
                src = el.get(attr, "")
                if src and (self.isVideoFormat(src) or src.startswith("http")):
                    return f"第1集${src}"

        # 第7层: JWPlayer
        m = RE_JWPLAYER.search(html)
        if m:
            return f"第1集${m.group(1)}"

        # 第8层: Base64
        m = RE_BASE64.search(html)
        if m:
            try:
                decoded = base64.b64decode(m.group(1)).decode("utf-8")
                if decoded.startswith("http") and self.isVideoFormat(decoded):
                    return f"第1集${decoded}"
            except:
                pass

        # 第9层: eval解密
        m = RE_EVAL.search(html)
        if m:
            urls = RE_HTTP_VIDEO.findall(m.group(1))
            if urls:
                return f"第1集${urls[0]}"

        # 第10层: script标签
        for script in soup.find_all("script"):
            if script.string:
                urls = RE_HTTP_VIDEO.findall(script.string)
                if urls:
                    return f"第1集${urls[0]}"

        # 第11层: 页面中所有视频链接
        urls = RE_HTTP_VIDEO.findall(html)
        if urls:
            return f"第1集${urls[0]}"

        # 第12层: a标签href视频链接
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if self.isVideoFormat(href):
                return f"第1集${href}"

        # 第13层: button/data属性
        for btn in soup.find_all(["button", "div", "span"], attrs={"data-link": True}):
            src = btn.get("data-link", "")
            if src and self.isVideoFormat(src):
                return f"第1集${src}"

        # 第14层: script中所有http链接
        for script in soup.find_all("script"):
            if script.string:
                urls = re.findall(r"(https?://[^\s\"'<>]+)", script.string)
                for u in urls:
                    if self.isVideoFormat(u):
                        return f"第1集${u}"

        # 第15层: 页面中所有http链接
        urls = re.findall(r"(https?://[^\s\"'<>]+)", html)
        for u in urls:
            if self.isVideoFormat(u):
                return f"第1集${u}"

        # 第16层: xhcdn CDN
        xhcdn = re.findall(r"(https?://video-[^\s\"'<>]+\.xhcdn\.com/[^\s\"'<>]+\.mp4[^\s\"'<>]*)", html)
        if xhcdn:
            return f"第1集${xhcdn[0]}"

        # 第17层: trailer/video/stream路径
        trailer = re.findall(r"(https?://[^\s\"'<>]+/(?:trailer|video|stream)/[^\s\"'<>]+\.(?:mp4|m3u8)[^\s\"'<>]*)", html)
        if trailer:
            return f"第1集${trailer[0]}"

        # 第18层: 返回页面本身
        return f"第1集${page_url}"


    def _parse_embed_page(self, embed_url):
        try:
            print(f"[兵字秘] 预解析嵌入页: {embed_url[:80]}...")
            headers = {"Referer": self.siteUrl}
            html = self.fetch(embed_url, headers=headers)
            if not html:
                return None

            embed_soup = BeautifulSoup(html, "html.parser")

            # 1. video标签
            for sel in ["video source", "video", ".jw-video", "#video-player"]:
                video = embed_soup.select_one(sel)
                if video:
                    for attr in ["src", "data-src", "data-url", "data-file", "data-video"]:
                        src = video.get(attr, "")
                        if src and self.isVideoFormat(src):
                            print(f"[兵字秘] 嵌入页video命中")
                            return src

            # 2. player变量 (多种格式)
            for pattern in [RE_PLAYER_VAR,
                            re.compile(r"var\s+player\s*=\s*({.+?});"),
                            re.compile(r"player\s*=\s*({.+?});"),
                            re.compile(r"sources\s*[:=]\s*(\[.+?\])")]:
                m = pattern.search(html)
                if m:
                    try:
                        data = json.loads(m.group(1).rstrip(";"))
                        if isinstance(data, list):
                            url = data[0].get("file") or data[0].get("src") or data[0].get("url", "")
                        else:
                            url = data.get("url") or data.get("file") or data.get("src", "")
                        if url:
                            print(f"[兵字秘] 嵌入页player命中")
                            return url
                    except:
                        pass

            # 3. JS中的m3u8/mp4链接
            for pattern in [RE_JS_M3U8, RE_JS_MP4, RE_JS_URL]:
                m = pattern.search(html)
                if m:
                    url = m.group(1)
                    if ".m3u8" in url or ".mp4" in url or self.isVideoFormat(url):
                        print(f"[兵字秘] 嵌入页JS命中")
                        return url

            # 4. eval解密
            m = RE_EVAL.search(html)
            if m:
                urls = RE_HTTP_VIDEO.findall(m.group(1))
                if urls:
                    print(f"[兵字秘] 嵌入页eval命中")
                    return urls[0]

            # 5. script标签
            for script in embed_soup.find_all("script"):
                if script.string:
                    urls = RE_HTTP_VIDEO.findall(script.string)
                    if urls:
                        print(f"[兵字秘] 嵌入页script命中")
                        return urls[0]

            # 6. 页面中所有视频链接
            urls = RE_HTTP_VIDEO.findall(html)
            if urls:
                print(f"[兵字秘] 嵌入页正则命中")
                return urls[0]

            # 7. 所有http链接筛选
            urls = re.findall(r"(https?://[^\s\"'<>]+)", html)
            for u in urls:
                if self.isVideoFormat(u):
                    print(f"[兵字秘] 嵌入页全链接命中")
                    return u

            # 8. CDN链接 (key/token/exp/sig)
            cdn = RE_CDN_LINK.findall(html)
            if cdn:
                for u in cdn:
                    if ".mp4" in u or ".m3u8" in u:
                        print(f"[兵字秘] 嵌入页CDN命中")
                        return u

            print("[兵字秘] 嵌入页预解析未命中，回退到iframe本身")
            return None
        except Exception as e:
            print(f"[兵字秘] 嵌入页预解析异常: {e}")
            return None


    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "url": "", "header": ""}

        embed_signs = ["/e/", "/embed/", "/player/", "/stream/", "/v/", "iframe", "php", "html"]
        embed_domains = ["dsvplay", "luluvdo", "streamtape", "doodstream", "mixdrop", "voe", "filemoon",
                         "streamhub", "upstream", "evoload", "vidcloud", "sbembed", "fembed",
                         "streamsb", "sbface", "lvturbo", "wolfstream", "vanfem", "dood", "stream"]
        is_embed = any(s in id for s in embed_signs) or any(d in id.lower() for d in embed_domains)

        if is_embed:
            print(f"[兵字秘] 嵌入播放器: {id[:100]}...")
            return {
                "parse": 1,
                "url": id,
                "header": f"Referer={self.siteUrl}&User-Agent={self.headers['User-Agent']}"
            }

        if "xhcdn.com" in id or "xhamster" in id:
            cookies = "; ".join([f"{k}={v}" for k, v in self.session.cookies.items()])
            header = f"Referer={self.siteUrl}&User-Agent={self.headers['User-Agent']}"
            if cookies:
                header += f"&Cookie={cookies}"
            print(f"[兵字秘] xhcdn播放")
            return {"parse": 0, "url": id, "header": header}

        return {
            "parse": 0,
            "url": id,
            "header": f"Referer={self.siteUrl}&User-Agent={self.headers['User-Agent']}"
        }

    def searchContent(self, key, quick, pg="1"):
        try:
            keyword = parse.quote(key.replace(" ", "+"))
            return self.categoryContent(f"search::{keyword}", pg, False, {})
        except Exception as e:
            print(f"[列字秘] 搜索失败: {e}")
            return {"list": [], "page": pg, "pagecount": 999}

    def searchContentPage(self, key, quick, pg="1"):
        return self.searchContent(key, quick, pg)

    def localProxy(self, param):
        return [200, "application/json", json.dumps({"proxy": f"http://127.0.0.1:{self.proxyPort}", "status": "ready"})]


class Spider(ZheTian_Master):
    pass
