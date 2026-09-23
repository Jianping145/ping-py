#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【遮天法 · 四极境】netfapx.net TVBox 爬虫 v11 修复版
修复：luluvdo eval 混淆解码 + DoodStream 两步握手 + 通用嵌入页回退
"""

import sys
import re
import json
import time
import base64
import random
import string
import requests
from urllib import parse
from bs4 import BeautifulSoup

sys.path.append("..")
from base.spider import Spider

RE_WATCH_ID = re.compile(r"/watch/\d+/?$")
RE_WATCH_ACTOR = re.compile(r"/watch/actor/[^/]+")
RE_VIDEO_EXT = re.compile(r"\.(m3u8|mp4|flv|mkv|ts|avi|mov)(?:\?|#|$)", re.I)
RE_PLAYER_VAR = re.compile(r"var\s+player_[a-zA-Z_]*\s*=\s*({.+?});")
RE_VIDEO_URL = re.compile(r"(?:videoUrl|video_url|sourceUrl|src|file)\s*[:=]\s*[\"\']([^\"\']+\.(?:m3u8|mp4|flv))[\"\']")
RE_JWPLAYER = re.compile(r"jwplayer\(\".*?\"\)\.setup\({.*?file:\s*[\"\']([^\"\']+)[\"\']", re.DOTALL)
RE_BASE64 = re.compile(r"[\"\']([A-Za-z0-9+/]{50,}={0,2})[\"\']")
RE_EVAL = re.compile(r"eval\((function\(p,a,c,k,e,d\).+?)\)")
RE_HTTP_VIDEO = re.compile(r"(https?://[^\s\"\'>]+\.(?:m3u8|mp4|flv))")
RE_IFRAME_SRC = re.compile(r"<iframe[^>]+src=[\"\']([^\"\']+)[\"\']")
RE_JS_M3U8 = re.compile(r"[\"\'](https?://[^\"\']+\.m3u8[^\"\']*)[\"\']")
RE_JS_MP4 = re.compile(r"[\"\'](https?://[^\"\']+\.mp4[^\"\']*)[\"\']")
RE_JS_URL = re.compile(r"(?:url|file|src)\s*[:=]\s*[\"\'](https?://[^\"\']+)[\"\']")
RE_CDN_LINK = re.compile(r"(https?://[^\s\"\'<>]+(?:key|token|exp|sig)=[^\s\"\'<>]+)")


class YuanTianShu(Spider):
    session = requests.Session()
    proxyPort = 9979
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def fetch(self, url, headers=None, timeout=20, referer=None):
        h = {**self.headers, **(headers or {})}
        if referer:
            h["Referer"] = referer
        # 跟随跳转：luluvid.com -> luluvdo.com
        for i in range(3):
            try:
                resp = self.session.get(
                    url, headers=h, timeout=timeout,
                    allow_redirects=True, verify=False,
                )
                # 不强制 raise，部分环境证书异常但仍有正文
                if resp is None:
                    continue
                text = resp.text or ""
                if not text and hasattr(resp, "content"):
                    try:
                        text = resp.content.decode("utf-8", "ignore")
                    except Exception:
                        text = ""
                if text:
                    return text
                print(f"[源天书] 空响应 code={getattr(resp,'status_code', '?')} url={url}")
            except Exception as e:
                print(f"[源天书] 请求异常({i}): {url} | {e}")
                if i == 2:
                    return ""
                time.sleep(1 + i)
        return ""


class ZheTian_Master(YuanTianShu):
    # 类级别配置（TVBox 环境兼容性）
    siteUrl = "https://netfapx.net"
    proxyPort = 9979
    luluvdo_domains = [
        "luluvdo.com", "lulustream.com", "lulust.com", "lulucdn.com",
        "luluvid.com", "lulustream.net", "luluvid.net", "lulucdn.net",
        "luluvid.org", "lulustream.org",
    ]
    doodstream_domains = [
        "dood.to", "dood.so", "dood.watch", "dood.ws", "dood.sh",
        "dood.cx", "dood.la", "dood.pm", "dood.re", "dood.wf",
        "dood.yt", "dooood.com", "doods.pro", "ds2play.com",
        "doodstream.com", "playmogo.com", "doodcdn.com",
        "doply.net", "do7go.com", "dooodster.com", "vide0.net", "video.net", "d0000d.com",
        "d000d.com", "dood.li", "dood.work", "doods.yt",
    ]
    embed_domains = [
        "dsvplay", "streamtape", "mixdrop", "voe", "filemoon",
        "streamhub", "upstream", "evoload", "vidcloud", "sbembed",
        "fembed", "streamsb", "sbface", "lvturbo", "wolfstream",
        "vanfem", "streamwish", "filelions", "vidhide", "vidguard",
        "mp4upload", "yourupload", "fastupload", "videovard",
        "tapecontent", "strcloud", "streamta", "stape",
        "streamadblock", "streamvid", "embedrise", "vidmoly",
        "streamhg", "vidoza", "uqload",
    ]


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

        # luluvdo / lulustream
        self.luluvdo_domains = [
            "luluvdo.com", "lulustream.com", "lulust.com", "lulucdn.com",
            "luluvid.com", "lulustream.net", "luluvid.net", "lulucdn.net",
            "luluvid.org", "lulustream.org",
        ]

        # DoodStream 及其镜像
        self.doodstream_domains = [
            "dood.to", "dood.so", "dood.watch", "dood.ws", "dood.sh",
            "dood.cx", "dood.la", "dood.pm", "dood.re", "dood.wf",
            "dood.yt", "dooood.com", "doods.pro", "ds2play.com",
            "doodstream.com", "playmogo.com", "doodcdn.com",
            "doply.net", "do7go.com", "dooodster.com", "vide0.net", "d0000d.com",
            "d000d.com", "dood.li", "dood.work", "doods.yt",
            "doodstream.co", "doodstream.link", "doodstream.me",
            "doodstream.to", "doodstream.so", "doodstream.cc",
            "doodstream.click", "doodstream.download",
        ]

        # 其他嵌入播放器
        self.embed_domains = [
            "dsvplay", "streamtape", "mixdrop", "voe", "filemoon",
            "streamhub", "upstream", "evoload", "vidcloud", "sbembed",
            "fembed", "streamsb", "sbface", "lvturbo", "wolfstream",
            "vanfem", "streamwish", "filelions", "vidhide", "vidguard",
            "mp4upload", "yourupload", "fastupload", "videovard",
            "tapecontent", "strcloud", "streamta", "stape",
            "streamadblock", "streamvid", "embedrise", "vidmoly",
            "streamhg", "vidoza", "uqload",
        ]

    def init(self, extend=""):
        print("[遮天大师] v11 luluvdo专版已激活")
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
            pattern = re.compile(r'<a[^>]+href=["\']([^"\']*/watch/actor/[^"\']+)["\'][^>]*>.*?<img[^>]+(?:src|data-src|data-original)=["\']([^"\']*)["\'][^>]*>.*?(h[2-6]|span|div|p)[^>]*>([^<]+)</\3', re.S | re.I)
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
            pattern = re.compile(r'<a[^>]+href=["\']([^"\']*/watch/\d+/?)["\'][^>]*>.*?<img[^>]+(?:src|data-src|data-original)=["\']([^"\']*)["\'][^>]*>.*?(h[2-6]|span|div|p)[^>]*>([^<]+)</\3', re.S | re.I)
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
            pattern = re.compile(r'<a[^>]+href=["\']([^"\']*/watch/\d+/?)["\'][^>]*>.*?<img[^>]+(?:src|data-src|data-original)=["\']([^"\']*)["\'][^>]*>.*?(h[2-6]|span|div|p)[^>]*>([^<]+)</\3', re.S | re.I)
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
        # 第1层: video标签直链
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

        # 第2层: iframe嵌入 → 先预解析嵌入页
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
            print(f"[前字秘] 发现iframe嵌入: {iframe_src[:80]}...")
            embed_url = self._parse_embed_page(iframe_src)
            if embed_url:
                print(f"[前字秘] 嵌入页预解析成功，拿到直链")
                return f"第1集${embed_url}"
            print(f"[前字秘] 嵌入页预解析失败，回退到iframe地址")
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
                urls = re.findall(r"(https?://[^\s\"\'<>]+)", script.string)
                for u in urls:
                    if self.isVideoFormat(u):
                        return f"第1集${u}"

        # 第15层: 页面中所有http链接
        urls = re.findall(r"(https?://[^\s\"\'<>]+)", html)
        for u in urls:
            if self.isVideoFormat(u):
                return f"第1集${u}"

        # 第16层: xhcdn CDN
        xhcdn = re.findall(r"(https?://video-[^\s\"\'<>]+\.xhcdn\.com/[^\s\"\'<>]+\.mp4[^\s\"\'<>]*)", html)
        if xhcdn:
            return f"第1集${xhcdn[0]}"

        # 第17层: trailer/video/stream路径
        trailer = re.findall(r"(https?://[^\s\"\'<>]+/(?:trailer|video|stream)/[^\s\"\'<>]+\.(?:mp4|m3u8)[^\s\"\'<>]*)", html)
        if trailer:
            return f"第1集${trailer[0]}"

        # 第18层: 返回页面本身
        return f"第1集${page_url}"

    # ═══════════════════════════════════════════════════
    # 【兵字秘 · 嵌入页预解析 · v11 三合一】
    # ═══════════════════════════════════════════════════
    def _parse_embed_page(self, embed_url):
        try:
            print("[兵字秘] 预解析: " + str(embed_url)[:80])
            low = str(embed_url).lower()
            luluvdo_domains = getattr(self, 'luluvdo_domains', [
                "luluvdo.com", "lulustream.com", "lulust.com", "lulucdn.com",
                "luluvid.com", "lulustream.net", "luluvid.net", "lulucdn.net",
            ])
            is_luluvdo = any(d in low for d in luluvdo_domains) or ("lulu" in low)
            if is_luluvdo:
                print("[兵字秘] 检测到 luluvdo/lulust")
                return self._parse_luluvdo(embed_url)
            doodstream_domains = getattr(self, 'doodstream_domains', ["dood.to", "dood.so", "dood.watch", "playmogo.com", "doply.net"])
            is_dood = any(d in embed_url.lower() for d in doodstream_domains)
            if is_dood:
                print("[兵字秘] 检测到 DoodStream")
                return self._parse_doodstream(embed_url)

            dsvplay_domains = ["dsvplay", "streamwish", "filelions", "lvturbo", "wishfast"]
            if any(d in low for d in dsvplay_domains):
                print("[兵字秘] 检测到 dsvplay/streamwish 系，尝试 packer 解码")
                result = self._parse_dsvplay(embed_url)
                if result:
                    return result
                print("[兵字秘] dsvplay packer 解码失败，回退通用")

            print("[兵字秘] 未知嵌入，先试通用再试 packer")
            generic = self._parse_generic_embed(embed_url)
            if generic:
                return generic
            return self._parse_luluvdo(embed_url)
        except Exception as e:
            print("[兵字秘] 预解析异常: " + str(e))
            return None


    def _parse_luluvdo(self, embed_url):
        try:
            print("[luluvdo] 解析: " + str(embed_url))
            site_url = getattr(self, 'siteUrl', "https://netfapx.net")
            fetch_url = str(embed_url).replace("luluvid.com", "luluvdo.com")
            html = self.fetch(fetch_url, headers={"Referer": site_url}, referer=site_url)
            if not html:
                print("[luluvdo] 主域名失败，试原链")
                html = self.fetch(embed_url, headers={"Referer": site_url}, referer=site_url)
            if not html:
                print("[luluvdo] 下载失败")
                return None
            print("[luluvdo] 下载成功 len=" + str(len(html)))

            direct = re.search(r"(https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*)", html)
            if direct:
                print("[luluvdo] 明文命中: " + direct.group(1)[:100])
                return direct.group(1)

            # 宽松 packer：匹配 }\('p',a,c,'k'.split('|'))
            eval_match = re.search(
                r"}\('((?:\\'|[^'])*)',(\d+),(\d+),'((?:\\'|[^'])*)'\.split\('\|'\)\)\)",
                html, re.DOTALL
            )
            if not eval_match:
                eval_match = re.search(
                    r"eval\(function\(p,a,c,k,e,d\)\{while\(c--\)if\(k\[c\]\)p=p\.replace\(new RegExp\('\\b'\+c\.toString\(a\)\+'\\b'\,'g'\),k\[c\]\);return p\}\('(.+?)',(\d+),(\d+),'(.+?)'\.split\('\|'\)\)\)",
                    html, re.DOTALL
                )
            if not eval_match:
                print("[luluvdo] packer失败")
                m = re.search(r"file\s*:\s*[\"'](https?://[^\"']+)[\"']", html)
                return m.group(1) if m else None

            p = eval_match.group(1).replace("\\'", "'").replace('\\"', '"')
            a = int(eval_match.group(2))
            c = int(eval_match.group(3))
            k = eval_match.group(4).split("|")
            print("[luluvdo] 参数 a=%s c=%s k=%s" % (a, c, len(k)))
            digits = "0123456789abcdefghijklmnopqrstuvwxyz"

            def int_to_base(n, base):
                if n == 0:
                    return "0"
                result = ""
                while n > 0:
                    result = digits[n % base] + result
                    n //= base
                return result

            decoded = p
            for i in range(c - 1, -1, -1):
                if i < len(k) and k[i]:
                    decoded = re.sub(r"\b" + re.escape(int_to_base(i, a)) + r"\b", k[i], decoded)

            print("[luluvdo] 解码完成 len=" + str(len(decoded)))
            m3u8 = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', decoded)
            if m3u8:
                print("[luluvdo] 命中m3u8: " + m3u8.group(1)[:100])
                return m3u8.group(1)
            m3u8 = re.search(r"(https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*)", decoded)
            if m3u8:
                print("[luluvdo] 回退命中: " + m3u8.group(1)[:100])
                return m3u8.group(1)
            mp4 = re.search(r"(https?://[^\s\"'<>]+\.mp4[^\s\"'<>]*)", decoded)
            if mp4:
                return mp4.group(1)
            print("[luluvdo] 未找到视频链接")
            return None
        except Exception as e:
            print("[luluvdo] 异常: " + str(e))
            import traceback
            traceback.print_exc()
            return None


    def _parse_doodstream(self, embed_url):
        """
        DoodStream 解析 v2 - 支持 playmogo/do7go/vide0 等新镜像
        """
        try:
            print("[doodstream] 解析: " + str(embed_url))
            site_url = getattr(self, 'siteUrl', "https://netfapx.net")

            fetch_url = str(embed_url)
            if "/d/" in fetch_url and "/e/" not in fetch_url:
                fetch_url = fetch_url.replace("/d/", "/e/")

            html = self.fetch(fetch_url, headers={"Referer": site_url}, referer=site_url)
            if not html:
                print("[doodstream] 下载失败")
                return None

            low = html.lower()
            cf_signs = ["just a moment", "cf-browser-verification", "turnstile",
                        "challenge-platform", "checking your browser", "cf_chl_"]
            is_cf = any(s in low for s in cf_signs)
            if is_cf and "pass_md5" not in low:
                print("[doodstream] Cloudflare 拦截，换UA重试...")
                alt_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Referer": site_url,
                    "Accept-Language": "en-US,en;q=0.9",
                }
                html = self.fetch(fetch_url, headers=alt_headers, referer=site_url)
                if not html:
                    return None
                low = html.lower()
                if any(s in low for s in cf_signs) and "pass_md5" not in low:
                    print("[doodstream] Cloudflare 仍然拦截")
                    return None

            print("[doodstream] 下载成功 len=" + str(len(html)))

            token = None
            patterns = [
                r"[?&]token=([a-zA-Z0-9]+)",
                r"var\s+token\s*=\s*['\"]([a-zA-Z0-9]+)['\"]",
                r"token\s*:\s*['\"]([a-zA-Z0-9]+)['\"]",
                r'data-token=["\']([a-zA-Z0-9]+)["\']',
                r"/pass_md5/[^/\s<>]+/[^/\s<>?]+\?token=([a-zA-Z0-9]+)",
                r"pass_md5[^\n]{0,200}?token['\"\s:=]+([a-zA-Z0-9]+)",
            ]
            for pat in patterns:
                m = re.search(pat, html)
                if m:
                    token = m.group(1)
                    break

            if not token:
                print("[doodstream] token未找到")
                return None
            print("[doodstream] token=" + token)

            pass_md5 = None
            m = re.search(r"['\"](/pass_md5/[^'\"]+)['\"]", html)
            if m:
                pass_md5 = m.group(1)
            if not pass_md5:
                m = re.search(r"(/pass_md5/[^\s<>'\"]+)", html)
                if m:
                    pass_md5 = m.group(1)
            if not pass_md5:
                m = re.search(r"(pass_md5/[^\s<>'\"]+)", html)
                if m:
                    pass_md5 = "/" + m.group(1)

            if not pass_md5:
                print("[doodstream] pass_md5未找到")
                return None
            print("[doodstream] pass_md5=" + pass_md5)

            from urllib.parse import urlparse
            parsed = urlparse(fetch_url)
            domain = parsed.scheme + "://" + parsed.netloc
            auth_url = domain + pass_md5

            auth_headers = {
                "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"),
                "Referer": fetch_url,
                "Origin": domain,
                "Accept": "*/*",
                "X-Requested-With": "XMLHttpRequest",
            }
            try:
                resp = self.session.get(auth_url, headers=auth_headers, timeout=20, verify=False)
                base_url = (resp.text or "").strip()
            except Exception as e:
                print("[doodstream] auth请求异常: " + str(e))
                return None

            if not base_url.startswith("http"):
                print("[doodstream] base_url无效")
                return None
            print("[doodstream] base_url=" + base_url[:80])

            random_str = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            expiry = int(time.time() * 1000)
            sep = "" if base_url.endswith("/") else "/"
            final_url = base_url + sep + random_str + "?token=" + token + "&expiry=" + str(expiry)
            print("[doodstream] 最终URL=" + final_url[:80])
            return final_url

        except Exception as e:
            print("[doodstream] 异常: " + str(e))
            import traceback
            traceback.print_exc()
            return None

    # ═══════════════════════════════════════════════════
    # 【新增 · dsvplay/streamwish 专用解析】
    # ═══════════════════════════════════════════════════
    def _parse_dsvplay(self, embed_url):
        """
        dsvplay.com / streamwish.com / filelions.com 系列
        页面结构：嵌入页 HTML 里有 packer 混淆的 eval，解开后得到 m3u8/mp4
        """
        try:
            print("[dsvplay] 解析: " + str(embed_url))
            site_url = getattr(self, 'siteUrl', "https://netfapx.net")
            html = self.fetch(embed_url, headers={"Referer": site_url}, referer=site_url)
            if not html:
                print("[dsvplay] 下载失败")
                return None
            print("[dsvplay] 下载成功 len=" + str(len(html)))

            direct = re.search(r"(https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*)", html)
            if direct:
                print("[dsvplay] 明文命中: " + direct.group(1)[:100])
                return direct.group(1)
            direct = re.search(r"(https?://[^\s\"'<>]+\.mp4[^\s\"'<>]*)", html)
            if direct:
                return direct.group(1)

            m = re.search(r'(?:file|sources)\s*[:=]\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html)
            if m:
                print("[dsvplay] 变量命中: " + m.group(1)[:100])
                return m.group(1)

            decoded = self._unpack_packer(html)
            if decoded:
                m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', decoded)
                if m3u8:
                    print("[dsvplay] packer解码命中m3u8: " + m3u8.group(1)[:100])
                    return m3u8.group(1)
                mp4 = re.search(r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']', decoded)
                if mp4:
                    print("[dsvplay] packer解码命中mp4: " + mp4.group(1)[:100])
                    return mp4.group(1)
                rel = re.search(r'["\'](/[^\s"\']+\.m3u8[^"\']*)["\']', decoded)
                if rel:
                    from urllib.parse import urlparse
                    p = urlparse(embed_url)
                    abs_url = p.scheme + "://" + p.netloc + rel.group(1)
                    print("[dsvplay] 相对路径拼接: " + abs_url[:100])
                    return abs_url

            soup = BeautifulSoup(html, "html.parser")
            for attr in ["data-url", "data-src", "data-file", "data-video", "data-source", "data-link"]:
                el = soup.select_one(f"[{attr}]")
                if el:
                    src = el.get(attr, "")
                    if src and (".m3u8" in src or ".mp4" in src):
                        if src.startswith("/"):
                            from urllib.parse import urlparse
                            p = urlparse(embed_url)
                            src = p.scheme + "://" + p.netloc + src
                        if src.startswith("http"):
                            return src

            iframe = soup.select_one("iframe")
            if iframe:
                src = iframe.get("src", "")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        from urllib.parse import urlparse
                        p = urlparse(embed_url)
                        src = p.scheme + "://" + p.netloc + src
                    if "dsvplay" in src or "streamwish" in src or "filelions" in src:
                        print("[dsvplay] 嵌套iframe，递归解析: " + src[:80])
                        return self._parse_dsvplay(src)

            print("[dsvplay] 所有方法均失败")
            return None
        except Exception as e:
            print("[dsvplay] 异常: " + str(e))
            import traceback
            traceback.print_exc()
            return None

    def _unpack_packer(self, html):
        """
        Dean Edwards Packer 解码器
        返回解码后的 JS 字符串，失败返回 None
        """
        try:
            eval_match = re.search(
                r"}\('((?:\\'|[^'])*)',(\d+),(\d+),'((?:\\'|[^'])*)'\.split\('\|'\)\)\)",
                html, re.DOTALL
            )
            if not eval_match:
                eval_match = re.search(
                    r"eval\(function\(p,a,c,k,e,d\)\{while\(c--\)if\(k\[c\]\)p=p\.replace\(new RegExp\('\\b'\+c\.toString\(a\)\+'\\b'\,'g'\),k\[c\]\);return p\}\('(.+?)',(\d+),(\d+),'(.+?)'\.split\('\|'\)\)\)",
                    html, re.DOTALL
                )
            if not eval_match:
                eval_match = re.search(
                    r"\}\('((?:\\'|[^'])*)',\s*(\d+),\s*(\d+),\s*'((?:\\'|[^'])*)'\.split\('\|'\)",
                    html, re.DOTALL
                )
            if not eval_match:
                return None

            p = eval_match.group(1).replace("\\'", "'").replace('\\"', '"').replace("\\/", "/")
            a = int(eval_match.group(2))
            c = int(eval_match.group(3))
            k = eval_match.group(4).split("|")
            print("[packer] 参数 a=%s c=%s k=%s" % (a, c, len(k)))
            digits = "0123456789abcdefghijklmnopqrstuvwxyz"

            def int_to_base(n, base):
                if n == 0:
                    return "0"
                result = ""
                while n > 0:
                    result = digits[n % base] + result
                    n //= base
                return result

            decoded = p
            for i in range(c - 1, -1, -1):
                if i < len(k) and k[i]:
                    decoded = re.sub(r"\b" + re.escape(int_to_base(i, a)) + r"\b", k[i], decoded)
            print("[packer] 解码完成 len=" + str(len(decoded)))
            return decoded
        except Exception as e:
            print("[packer] 解码异常: " + str(e))
            return None

    def _dsvplay_play_header(self, embed_url="https://dsvplay.com"):
        """dsvplay/streamwish 系的播放头：Referer 必须是嵌入页域名"""
        ua = self.headers.get(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        host = "https://dsvplay.com"
        try:
            from urllib.parse import urlparse
            u = str(embed_url)
            if u.startswith("http"):
                p = urlparse(u)
                if p.netloc:
                    host = p.scheme + "://" + p.netloc
        except Exception:
            pass
        # ★ 返回 JSON 字符串（TVBox T4 接口兼容性最好）
        return json.dumps({
            "User-Agent": ua,
            "Referer": host + "/",
            "Origin": host,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _parse_generic_embed(self, embed_url):
        try:
            headers = {"Referer": self.siteUrl}
            html = self.fetch(embed_url, headers=headers, referer=self.siteUrl)
            if not html:
                return None

            embed_soup = BeautifulSoup(html, "html.parser")

            for sel in ["video source", "video", ".jw-video", "#video-player", ".video-js", "video[data-src]"]:
                video = embed_soup.select_one(sel)
                if video:
                    for attr in ["src", "data-src", "data-url", "data-file", "data-video", "data-source"]:
                        src = video.get(attr, "")
                        if src and self.isVideoFormat(src):
                            return src

            for pattern in [RE_PLAYER_VAR,
                            re.compile(r"var\s+player\s*=\s*({.+?});"),
                            re.compile(r"player\s*=\s*({.+?});"),
                            re.compile(r"sources\s*[:=]\s*(\[.+?\])"),
                            re.compile(r"videoData\s*[:=]\s*({.+?})"),
                            re.compile(r"config\s*[:=]\s*({.+?})")]:
                m = pattern.search(html)
                if m:
                    try:
                        data = json.loads(m.group(1).rstrip(";"))
                        if isinstance(data, list):
                            url = data[0].get("file") or data[0].get("src") or data[0].get("url", "")
                        else:
                            url = data.get("url") or data.get("file") or data.get("src") or data.get("videoUrl", "")
                        if url:
                            return url
                    except:
                        pass

            for pattern in [RE_JS_M3U8, RE_JS_MP4, RE_JS_URL,
                            re.compile(r"[\"\']](https?://[^\"\']+\.(?:mp4|m3u8|flv)[^\"\']*)[\"\']")]:
                m = pattern.search(html)
                if m:
                    url = m.group(1)
                    if self.isVideoFormat(url) or ".m3u8" in url or ".mp4" in url:
                        return url

            m = RE_EVAL.search(html)
            if m:
                urls = RE_HTTP_VIDEO.findall(m.group(1))
                if urls:
                    return urls[0]

            for script in embed_soup.find_all("script"):
                if script.string:
                    urls = RE_HTTP_VIDEO.findall(script.string)
                    if urls:
                        return urls[0]

            urls = RE_HTTP_VIDEO.findall(html)
            if urls:
                return urls[0]

            urls = re.findall(r"(https?://[^\s\"\'<>]+)", html)
            for u in urls:
                if self.isVideoFormat(u):
                    return u

            cdn = RE_CDN_LINK.findall(html)
            if cdn:
                for u in cdn:
                    if ".mp4" in u or ".m3u8" in u:
                        return u

            return None

        except Exception as e:
            print(f"[兵字秘] 通用解析异常: {e}")
            return None

    def _proxy_play_url(self, url):
        """有 getProxyUrl 时走本地代理（保证带 Referer），否则直链"""
        try:
            base = None
            if hasattr(self, "getProxyUrl"):
                try:
                    base = self.getProxyUrl()
                except Exception:
                    base = None
            if not base or not str(base).startswith("http"):
                return url
            from urllib.parse import quote
            proxied = str(base) + "&url=" + quote(url, safe="")
            print("[proxy] use " + proxied[:120])
            return proxied
        except Exception as e:
            print("[proxy] build url fail: " + str(e))
            return url

    def _proxy_media_url(self, url):
        """
        ★ 核心修复：把 m3u8/mp4 直链包装成 localProxy 地址
        TVBox 播放时会调用 localProxy，由 Python 带 Referer 拉流
        """
        try:
            base = None
            if hasattr(self, "getProxyUrl"):
                try:
                    base = self.getProxyUrl()
                except Exception:
                    base = None
            if not base or not str(base).startswith("http"):
                print("[proxy] getProxyUrl 不可用，返回直链")
                return url
            from urllib.parse import quote
            proxied = str(base) + "&url=" + quote(url, safe="")
            print("[proxy] 媒体走代理: " + proxied[:120])
            return proxied
        except Exception as e:
            print("[proxy] build media url fail: " + str(e))
            return url


    def _fmt_header(self, hdr):
        """同时兼容 dict 与 JSON 字符串两种播放头格式"""
        if not hdr:
            return {}
        if isinstance(hdr, str):
            return hdr
        # 多数 FongMi/T4 支持 dict；部分只要 JSON 字符串
        try:
            return hdr  # 优先 dict
        except Exception:
            return json.dumps(hdr, ensure_ascii=False)

    def _lulu_play_header(self, embed_or_host="https://lulust.com"):
        ua = self.headers.get(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        host = "https://lulust.com"
        try:
            from urllib.parse import urlparse
            u = str(embed_or_host)
            if u.startswith("http"):
                p = urlparse(u)
                if p.netloc:
                    host = p.scheme + "://" + p.netloc
        except Exception:
            pass
        return json.dumps({
            "User-Agent": ua,
            "Referer": host + "/",
            "Origin": host,
            "Accept": "*/*",
        })

    def _resolve_media_m3u8(self, master_url, header=None):
        """master.m3u8 -> 最高清晰度 media playlist（同会话立刻拉）"""
        try:
            if not master_url or ".m3u8" not in master_url:
                return master_url
            # 已经是 media 列表则不再解析
            if "index-" in master_url and "master.m3u8" not in master_url:
                return master_url
            h = {
                "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"),
                "Accept": "*/*",
                "Referer": "https://lulust.com/",
                "Origin": "https://lulust.com",
            }
            if header:
                try:
                    if isinstance(header, str):
                        h.update(json.loads(header))
                    else:
                        h.update(header)
                except Exception:
                    pass
            try:
                resp = self.session.get(master_url, headers=h, timeout=15, verify=False)
                body = resp.text or ""
            except Exception as e:
                print("[luluvdo] master fetch fail: " + str(e))
                return master_url
            if "#EXTM3U" not in body:
                print("[luluvdo] master 非 m3u8 code=%s len=%s" % (getattr(resp, "status_code", "?"), len(body)))
                return master_url
            # media playlist 特征
            if "#EXT-X-STREAM-INF" not in body:
                return master_url
            best_bw, best_url = -1, None
            lines = body.strip().splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("#EXT-X-STREAM-INF"):
                    bw = 0
                    m = re.search(r"BANDWIDTH=(\d+)", line)
                    if m:
                        bw = int(m.group(1))
                    if i + 1 < len(lines):
                        u = lines[i + 1].strip()
                        if u and not u.startswith("#"):
                            abs_u = u if u.startswith("http") else parse.urljoin(master_url, u)
                            if bw >= best_bw:
                                best_bw, best_url = bw, abs_u
                i += 1
            if best_url:
                print("[luluvdo] media playlist: " + best_url[:120])
                return best_url
            return master_url
        except Exception as e:
            print("[luluvdo] resolve media 失败: " + str(e))
            return master_url

    def playerContent(self, flag, id, vipFlags):
        try:
            print("[playerContent] flag=" + str(flag) + " id=" + str(id)[:100])
            ua = self.headers.get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            if not id:
                return {"parse": 0, "url": "", "header": json.dumps({"User-Agent": ua}), "jx": 0}

            sid = str(id)
            low_sid = sid.lower()

            # ═══════════════════════════════════════════════════
            # 第0层：actor 页面
            # ═══════════════════════════════════════════════════
            if sid.startswith("actor::"):
                return {
                    "parse": 1,
                    "url": sid.replace("actor::", ""),
                    "header": json.dumps({"User-Agent": ua, "Referer": str(self.siteUrl)}),
                    "jx": 0,
                }

            # ═══════════════════════════════════════════════════
            # 第1层：已是视频直链（m3u8/mp4）
            # ═══════════════════════════════════════════════════
            if ".m3u8" in sid or sid.endswith(".mp4") or ".mp4?" in sid:
                print("[playerContent] 已是视频直链")
                # 判断 CDN 类型
                is_tnmr = "tnmr.org" in low_sid or "dsvplay" in low_sid or "streamwish" in low_sid or "filelions" in low_sid
                is_lulu = "lulu" in low_sid or "lulust" in low_sid or "luluvdo" in low_sid
                is_cloud = "cloudatacdn" in low_sid or "cloudflare" in low_sid

                if is_cloud:
                    # cloudatacdn 不校验 Referer，直接播放
                    print("[playerContent] cloudatacdn 直链，直接播放")
                    return {"parse": 0, "url": sid, "header": json.dumps({"User-Agent": ua}), "jx": 0}

                # 其他 CDN 尝试走 localProxy 代理
                proxied = self._proxy_media_url(sid)
                if proxied != sid:
                    print("[playerContent] 直链走 localProxy 代理")
                    return {"parse": 0, "url": proxied, "header": json.dumps({"User-Agent": ua}), "jx": 0}

                # localProxy 不可用，尝试直接播放（部分 CDN 不校验 Referer）
                print("[playerContent] localProxy 不可用，尝试直接播放")
                hdr = json.dumps({"User-Agent": ua, "Referer": "https://dsvplay.com/" if is_tnmr else "https://lulust.com/"})
                return {"parse": 0, "url": sid, "header": hdr, "jx": 0}

            # ═══════════════════════════════════════════════════
            # 第2层：netfapx 详情页 → 提取嵌入页
            # ═══════════════════════════════════════════════════
            if "netfapx.net" in sid and "/watch/" in sid:
                print("[playerContent] netfapx 详情页，提取嵌入")
                try:
                    html = self.fetch(sid, referer=str(self.siteUrl))
                    embed = None
                    if html:
                        # 提取 iframe
                        for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
                            src = m.group(1).strip()
                            if src.startswith("//"):
                                src = "https:" + src
                            low = src.lower()
                            if any(x in low for x in ("lulu", "dood", "do7go", "playmogo", "vide0", "dsvplay", "streamwish", "filelions", "/e/", "embed", "myvidplay")):
                                if "tsyndicate" in low or "ads" in low:
                                    continue
                                embed = src
                                break
                        # 正则提取嵌入域名
                        if not embed:
                            m = re.search(r'https?://(?:www\.)?(?:lulu[^\s"\'<>]+|dood[^\s"\'<>]+|do7go\.com[^\s"\'<>]*|dsvplay\.com[^\s"\'<>]*|myvidplay\.com[^\s"\'<>]*|streamwish\.com[^\s"\'<>]*|filelions\.com[^\s"\'<>]*)', html, re.I)
                            if m:
                                embed = m.group(0)
                    if embed:
                        print("[playerContent] 详情页嵌入: " + embed[:100])
                        return self.playerContent(flag, embed, vipFlags)
                    print("[playerContent] 详情页未找到嵌入")
                except Exception as e:
                    print("[playerContent] 详情页解析异常: " + str(e))

            # ═══════════════════════════════════════════════════
            # 第3层：嵌入页解析
            # ═══════════════════════════════════════════════════
            embed_signs = ["/e/", "/embed/", "/player/", "/stream/", "/v/"]
            luluvdo_domains = getattr(self, "luluvdo_domains", [
                "luluvdo.com", "lulustream.com", "lulust.com", "lulucdn.com",
                "luluvid.com", "lulustream.net", "luluvid.net", "lulucdn.net",
            ])
            doodstream_domains = getattr(self, "doodstream_domains", [
                "dood.to", "dood.so", "dood.watch", "doply.net", "do7go.com",
                "playmogo.com", "doodstream.com", "myvidplay.com",
            ])
            dsvplay_domains = ["dsvplay.com", "streamwish.com", "filelions.com", "lvturbo.com", "wishfast.com", "myvidplay.com"]
            embed_domains = getattr(self, "embed_domains", ["streamtape", "mixdrop"])
            all_embed_domains = embed_domains + doodstream_domains + luluvdo_domains + dsvplay_domains

            is_embed = any(s in sid for s in embed_signs) or any(d in low_sid for d in all_embed_domains)
            print("[playerContent] is_embed=" + str(is_embed))

            if is_embed:
                print("[兵字秘] 嵌入页: " + sid[:80])

                # ── 3.1 尝试预解析嵌入页 ──
                real_url = self._parse_embed_page(sid)
                print("[兵字秘] real_url=" + (str(real_url)[:100] if real_url else "None"))

                is_lulu = any(d in low_sid for d in luluvdo_domains) or ("lulu" in low_sid)
                is_dsv = any(d in low_sid for d in dsvplay_domains)
                is_dood = any(d in low_sid for d in doodstream_domains)

                if real_url:
                    play = str(real_url)
                    # master.m3u8 → 最高清晰度
                    if "master.m3u8" in play:
                        play = self._resolve_media_m3u8(play, None)

                    # 判断解析结果的 CDN 类型
                    play_low = play.lower()

                    if "cloudatacdn" in play_low:
                        # cloudatacdn 不校验 Referer，直接播放
                        print("[兵字秘] cloudatacdn 解析结果，直接播放")
                        return {"parse": 0, "url": play, "header": json.dumps({"User-Agent": ua}), "jx": 0}

                    # 尝试走 localProxy 代理
                    proxied = self._proxy_media_url(play)
                    if proxied != play:
                        print("[兵字秘] 解析结果走 localProxy: " + proxied[:80])
                        return {"parse": 0, "url": proxied, "header": json.dumps({"User-Agent": ua}), "jx": 0}

                    # localProxy 不可用，直接播放（带 Referer 碰碰运气）
                    print("[兵字秘] localProxy 不可用，直接播放: " + play[:80])
                    if is_dsv or "tnmr.org" in play_low:
                        hdr = json.dumps({"User-Agent": ua, "Referer": "https://dsvplay.com/"})
                    elif is_lulu:
                        hdr = json.dumps({"User-Agent": ua, "Referer": "https://lulust.com/"})
                    else:
                        hdr = json.dumps({"User-Agent": ua, "Referer": str(self.siteUrl)})
                    return {"parse": 0, "url": play, "header": hdr, "jx": 0}

                # ── 3.2 预解析失败，尝试用 localProxy 代理嵌入页本身 ──
                # 让 TVBox 通过 localProxy 加载嵌入页，由 Python 带 Referer 请求
                # 嵌入页里的播放器会自动请求视频，Python 代理会带上正确的 Referer
                print("[兵字秘] 预解析失败，尝试代理嵌入页")
                proxied_embed = self._proxy_media_url(sid)
                if proxied_embed != sid:
                    print("[兵字秘] 嵌入页走 localProxy: " + proxied_embed[:80])
                    return {
                        "parse": 0,
                        "url": proxied_embed,
                        "header": json.dumps({"User-Agent": ua, "Referer": str(self.siteUrl)}),
                        "jx": 0,
                    }

                # ── 3.3 localProxy 也不可用，返回嵌入页让 TVBox 处理 ──
                print("[兵字秘] localProxy 不可用，返回嵌入页 parse=0")
                return {
                    "parse": 0,
                    "url": sid,
                    "header": json.dumps({"User-Agent": ua, "Referer": str(self.siteUrl)}),
                    "jx": 0,
                }

            # ═══════════════════════════════════════════════════
            # 第4层：非嵌入，直接返回
            # ═══════════════════════════════════════════════════
            print("[playerContent] 非嵌入 parse=0")
            return {
                "parse": 0,
                "url": sid,
                "header": json.dumps({"User-Agent": ua, "Referer": str(self.siteUrl)}),
                "jx": 0,
            }
        except Exception as e:
            print("[playerContent] 异常: " + str(e))
            import traceback
            traceback.print_exc()
            return {
                "parse": 1,
                "url": id,
                "header": json.dumps({
                    "User-Agent": "Mozilla/5.0",
                    "Referer": str(getattr(self, "siteUrl", "https://netfapx.net")),
                }),
                "jx": 0,
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
        """代理 m3u8/ts/嵌入页：带 Referer 拉取，重写 m3u8 内相对路径为代理地址"""
        try:
            url = param.get("url") or param.get("path") or ""
            if not url:
                return [400, "text/plain", {}, "no url"]
            # 有的实现会把完整 query 再包一层
            if url.startswith("http") is False and "http" in str(param):
                for v in param.values():
                    if isinstance(v, str) and v.startswith("http"):
                        url = v
                        break

            # 根据目标域名选择 header
            low_url = str(url).lower()
            if "tnmr.org" in low_url or "dsvplay" in low_url or "streamwish" in low_url or "filelions" in low_url or "myvidplay" in low_url:
                hdr = json.loads(self._dsvplay_play_header("https://dsvplay.com"))
                print("[proxy] dsvplay header")
            elif "lulu" in low_url or "lulust" in low_url or "luluvdo" in low_url:
                hdr = json.loads(self._lulu_play_header("https://lulust.com"))
                print("[proxy] lulu header")
            elif "dood" in low_url or "playmogo" in low_url or "do7go" in low_url:
                hdr = {
                    "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"),
                    "Referer": "https://" + parse.urlparse(url).netloc + "/",
                    "Accept": "*/*",
                }
                print("[proxy] dood header")
            else:
                hdr = json.loads(self._lulu_play_header("https://lulust.com"))

            print("[proxy] fetch " + str(url)[:100])
            resp = self.session.get(url, headers=hdr, timeout=20, verify=False, allow_redirects=True)
            content = resp.content or b""
            ctype = resp.headers.get("Content-Type") or "application/vnd.apple.mpegurl"

            # m3u8 内容：重写相对路径为代理地址
            if b"#EXTM3U" in content[:20] or "mpegurl" in ctype or ".m3u8" in url:
                try:
                    text_body = content.decode("utf-8", "ignore")
                    lines = []
                    for line in text_body.splitlines():
                        s = line.strip()
                        if s and not s.startswith("#"):
                            if not s.startswith("http"):
                                abs_url = parse.urljoin(url, s)
                            else:
                                abs_url = s
                            # 分片也走代理（带 Referer）
                            proxied = self._proxy_media_url(abs_url)
                            lines.append(proxied)
                        else:
                            lines.append(line)
                    content = "\n".join(lines).encode("utf-8")
                    ctype = "application/vnd.apple.mpegurl"
                except Exception as e:
                    print("[proxy] rewrite fail: " + str(e))

            # 嵌入页 HTML：重写其中的资源地址为代理地址
            elif "text/html" in ctype:
                try:
                    text_body = content.decode("utf-8", "ignore")
                    # 重写 video/src 地址
                    def repl_url(m):
                        u = m.group(1)
                        if u.startswith("//"):
                            u = "https:" + u
                        elif u.startswith("/"):
                            u = parse.urljoin(url, u)
                        if u.startswith("http") and (".m3u8" in u or ".mp4" in u or "tnmr.org" in u or "dsvplay" in u):
                            return m.group(0).replace(m.group(1), self._proxy_media_url(u))
                        return m.group(0)
                    text_body = re.sub(r'["\'](https?://[^"\']+)["\']', repl_url, text_body)
                    content = text_body.encode("utf-8")
                except Exception as e:
                    print("[proxy] html rewrite fail: " + str(e))

            print("[proxy] ok len=" + str(len(content)) + " ctype=" + str(ctype))
            return [200, ctype, hdr, content]
        except Exception as e:
            print("[proxy] error: " + str(e))
            import traceback
            traceback.print_exc()
            return [500, "text/plain", {}, str(e).encode("utf-8")]



class Spider(ZheTian_Master):
    pass
