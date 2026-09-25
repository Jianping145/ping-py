# -*- coding: utf-8 -*-
"""
7mmtv.sx TVBox / T4Api Spider - 最终完美版 v11
支持所有分类，智能提取JSON-LD contentUrl + mvarr多播放器
"""

import re
import sys
import json
from urllib.parse import urljoin, quote, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

sys.path.append("..")
try:
    from base.spider import Spider
except Exception:
    class Spider:
        pass


class Spider(Spider):

    def init(self, extend=""):
        self.host = "https://7mmtv.sx"
        self.base = self.host + "/zh/"

        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=2,
            pool_block=False
        )

        self.session = requests.Session()
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0 Mobile Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.base,
            "Connection": "keep-alive",
        })

        # 广告域名黑名单
        self.ad_domains = [
            "whitetrafsa.com", "doubleclick.net", "googlesyndication.com",
            "adservice.google.com", "popads.net", "exoclick.com",
            "juicyads.com", "trafficjunky.com", "19sex.live",
            "labadena.com", "tsyndicate.com", "bg4nxu2u5t.com",
            "realsrv.com", "erodatalabs.com", "tapioni.com",
        ]

        # 预编译正则
        self._patterns = {
            'm3u8': re.compile(r'["\'](https?://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']', re.I),
            'mp4': re.compile(r'["\'](https?://[^"\']+\.mp4(?:\?[^"\']*)?)["\']', re.I),
            'turbos': re.compile(r'["\'](https?://g\d+\.turbosplayer\.com/[^"\']+)["\']', re.I),
            'emturbo': re.compile(r'["\'](https?://[^"\']*emturbovid[^"\']*\.(?:m3u8|mp4)[^"\']*)["\']', re.I),
            'playmogo': re.compile(r'["\'](https?://[^"\']*playmogo[^"\']*\.(?:m3u8|mp4)[^"\']*)["\']', re.I),
            'mmvh': re.compile(r'["\'](https?://[^"\']*mmvh[^"\']*\.(?:m3u8|mp4)[^"\']*)["\']', re.I),
            'mmsi': re.compile(r'["\'](https?://[^"\']*mmsi[^"\']*\.(?:m3u8|mp4)[^"\']*)["\']', re.I),
            'cdn_mp4': re.compile(r'["\'](https?://[^"\']*1024cdn\.sx/[^"\']+\.mp4[^"\']*)["\']', re.I),
            'cdn_video': re.compile(r'<video[^>]+data-src=["\']([^"\']+\.mp4[^"\']*)["\']', re.I),
            'source': re.compile(r'<source[^>]+src=["\']([^"\']+)["\']', re.I),
            'video': re.compile(r'<video[^>]+src=["\']([^"\']+)["\']', re.I),
            'json_ld': re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S),
            'content_url': re.compile(r'"contentUrl"\s*:\s*"([^"]+)"', re.I),
            'embed_url': re.compile(r'"embedUrl"\s*:\s*"([^"]+)"', re.I),
            'iframe_src': re.compile(r'<iframe[^>]+src=["\']([^"\']+)["\']', re.I),
            'data_src': re.compile(r'<iframe[^>]+data-src=["\']([^"\']+)["\']', re.I),
            'hls_url': re.compile(r'["\'](https?://[^"\']*\.(?:m3u8|m3u)[^"\']*)["\']', re.I),
            'mvarr': re.compile(r"mvarr\['(\d+_\d+)'\]=\[\['([^']+)','([^']+)','([^']+)','([^']+)','([^']*)','([^']+)','([^']*)'\],\];", re.I),
        }

        # CDN配置（优先级从高到低）
        self.cdn_config = {
            "mmvh02.com": {"referer": "https://mmvh02.com/", "origin": "https://mmvh02.com", "priority": 1},
            "playmogo.com": {"referer": "https://playmogo.com/", "origin": "https://playmogo.com", "priority": 2},
            "emturbovid.com": {"referer": "https://emturbovid.com/", "origin": "https://emturbovid.com", "priority": 3},
            "mmsi02.com": {"referer": "https://mmsi02.com/", "origin": "https://mmsi02.com", "priority": 4},
            "turbosplayer.com": {"referer": "https://7mmtv.sx/", "origin": "https://7mmtv.sx", "priority": 5},
        }

        # 缓存
        self._content_url_cache = {}

        return None

    def getName(self):
        return "7mmtv"

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower().split("?", 1)[0]
        return u.endswith((".m3u8", ".mp4", ".m4v", ".webm", ".ts"))

    def manualVideoCheck(self):
        return False

    def _get(self, url, referer=None, timeout=10):
        headers = {}
        if referer:
            headers["Referer"] = referer
        try:
            r = self.session.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                stream=False,
            )
            r.encoding = r.apparent_encoding or r.encoding or "utf-8"
            if r.status_code >= 400:
                return ""
            return r.text
        except Exception:
            return ""

    def _get_stream(self, url, referer=None, timeout=8, max_bytes=131072):
        headers = {}
        if referer:
            headers["Referer"] = referer
        try:
            resp = self.session.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                stream=True,
            )
            content = b""
            for chunk in resp.iter_content(chunk_size=8192, decode_unicode=False):
                content += chunk
                if len(content) > max_bytes:
                    break
            resp.close()
            if resp.status_code >= 400:
                return "", resp.status_code
            return content.decode('utf-8', errors='ignore'), resp.status_code
        except Exception:
            return "", 0

    def _soup(self, html):
        if not html or BeautifulSoup is None:
            return None
        try:
            return BeautifulSoup(html, "html.parser")
        except Exception:
            return None

    def _clean(self, text):
        if text is None:
            return ""
        text = re.sub(r"\s+", " ", str(text))
        return text.strip()

    def _abs(self, url, base=None):
        if not url:
            return ""
        return urljoin(base or self.base, url)

    def _img(self, img, base=None):
        if not img:
            return ""
        for key in (
            "data-original", "data-src", "data-lazy-src",
            "data-url", "src"
        ):
            value = img.get(key)
            if value:
                return self._abs(value, base)
        return ""

    def _is_ad_url(self, url):
        if not url:
            return False
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            for ad_domain in self.ad_domains:
                if ad_domain in domain:
                    return True
            ad_paths = ["/ads/", "/ad/", "/advert/", "/widget/", "/track/", "/popunder/"]
            path = parsed.path.lower()
            for ad_path in ad_paths:
                if ad_path in path:
                    return True
            query = parsed.query.lower()
            ad_params = ["autoplay=all", "campaignid=", "tracker=", "clickid="]
            for param in ad_params:
                if param in query:
                    return True
        except Exception:
            pass
        return False

    def _get_cdn_config(self, url):
        if not url:
            return None
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            for cdn_domain, config in self.cdn_config.items():
                if cdn_domain in domain:
                    return config
        except Exception:
            pass
        return None

    def _extract_mvarr_urls(self, html):
        """提取mvarr中的所有播放器URL，按CDN优先级排序"""
        urls = []
        mvarr_matches = self._patterns['mvarr'].findall(html)

        for match in mvarr_matches:
            key = match[0]  # 如 '28_1'
            encoded = match[1]  # 编码的ID
            iframe_base = match[3]  # 基础URL如 'https://playmogo.com/e/'

            # 直接使用编码作为URL参数（移除w分隔符）
            clean_encoded = encoded.replace('w', '')

            if iframe_base.startswith('//'):
                full_url = 'https:' + iframe_base + clean_encoded
            elif iframe_base.startswith('http'):
                full_url = iframe_base + clean_encoded
            else:
                full_url = iframe_base + clean_encoded

            if not self._is_ad_url(full_url):
                # 获取CDN优先级
                cdn_config = self._get_cdn_config(full_url)
                priority = cdn_config.get("priority", 99) if cdn_config else 99
                urls.append((priority, full_url))

        # 按优先级排序
        urls.sort(key=lambda x: x[0])
        return [url for _, url in urls]

    def _extract_json_ld_content_url(self, html):
        """从JSON-LD中提取contentUrl"""
        content_url = ""
        json_ld_scripts = self._patterns['json_ld'].findall(html)

        for script_content in json_ld_scripts:
            try:
                data = json.loads(script_content)
                if isinstance(data, dict):
                    # 主VideoObject
                    if data.get("@type") == "VideoObject":
                        content_url = data.get("contentUrl", "") or data.get("embedUrl", "")

                    # 嵌套video数组
                    videos = data.get("video", [])
                    if isinstance(videos, list):
                        for v in videos:
                            if isinstance(v, dict):
                                cu = v.get("contentUrl", "") or v.get("embedUrl", "")
                                if cu:
                                    content_url = cu
                                    break
            except Exception:
                continue
            if content_url:
                break

        return content_url

    # ---------------------------------------------------------
    # 分类
    # ---------------------------------------------------------
    def homeContent(self, filter):
        classes = [
            {"type_name": "無碼破解", "type_id": "reducing-mosaic"},
            {"type_name": "中字AV", "type_id": "chinese"},
            {"type_name": "有碼AV", "type_id": "censored"},
            {"type_name": "素人AV", "type_id": "amateurjav"},
            {"type_name": "無碼AV", "type_id": "uncensored"},
            {"type_name": "國產影片", "type_id": "amateur"},
        ]
        return {"class": classes, "list": []}

    def homeVideoContent(self):
        try:
            return self.categoryContent("reducing-mosaic", "1", False, {})
        except Exception:
            return {"list": []}

    # ---------------------------------------------------------
    # 列表
    # ---------------------------------------------------------
    def categoryContent(self, tid, pg, filter, extend):
        try:
            tid = str(tid).strip()
            try:
                page = max(1, int(pg))
            except Exception:
                page = 1

            url = f"{self.base}{tid}_list/all/{page}.html"
            html = self._get(url, self.base, timeout=8)
            if not html:
                return {"list": [], "page": page, "pagecount": 0}

            soup = self._soup(html)
            videos = []

            if soup:
                # 提取所有视频卡片
                for col_item in soup.find_all("div", class_="col-item"):
                    a_tag = col_item.find("a", href=re.compile(r"_content/"))
                    if not a_tag:
                        continue

                    href = self._abs(a_tag.get("href"), url)
                    title = ""
                    h3 = col_item.find("h3", class_="video-title")
                    if h3:
                        a_title = h3.find("a")
                        if a_title:
                            title = self._clean(a_title.get_text(" ", strip=True))

                    if not title:
                        title = self._clean(a_tag.get("title", ""))

                    if not href or not title:
                        continue

                    # 提取封面
                    pic = ""
                    img = col_item.find("img")
                    if img:
                        pic = self._img(img, url)

                    # 提取日期
                    remarks = ""
                    date_span = col_item.find("span", class_="text-muted")
                    if date_span:
                        remarks = self._clean(date_span.get_text())

                    if any(x.get("vod_id") == href for x in videos):
                        continue

                    videos.append({
                        "vod_id": href,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remarks,
                    })

            # 备用：正则提取
            if not videos:
                seen = set()
                pattern = re.compile(
                    r'href=["\']([^"\']+_content/[^"\']+\.html[^"\']*)["\']',
                    re.I
                )
                for href in pattern.findall(html):
                    full = self._abs(href, url)
                    if full in seen:
                        continue
                    seen.add(full)
                    name = full.rstrip("/").rsplit("/", 1)[-1]
                    name = re.sub(r"\.html.*$", "", name, flags=re.I)
                    videos.append({
                        "vod_id": full,
                        "vod_name": name,
                        "vod_pic": "",
                        "vod_remarks": "",
                    })

            pagecount = self._get_pagecount(soup, html)

            return {"list": videos, "page": page, "pagecount": pagecount}

        except Exception:
            return {"list": [], "page": 1, "pagecount": 0}

    def _get_pagecount(self, soup, html):
        max_page = 1
        try:
            if soup:
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "")
                    m = re.search(r"_list/all/(\d+)\.html", href, re.I)
                    if m:
                        max_page = max(max_page, int(m.group(1)))
                for a in soup.find_all("a"):
                    txt = self._clean(a.get_text())
                    if txt.isdigit():
                        n = int(txt)
                        if 1 <= n <= 100000:
                            max_page = max(max_page, n)
        except Exception:
            pass
        if max_page > 100000:
            max_page = 9999
        return max_page

    # ---------------------------------------------------------
    # 详情
    # ---------------------------------------------------------
    def detailContent(self, ids):
        try:
            if not ids:
                return {"list": []}

            detail_url = ids[0]
            if not detail_url.startswith("http"):
                detail_url = self._abs(detail_url)

            # 检查缓存
            if detail_url in self._content_url_cache:
                content_url = self._content_url_cache[detail_url]
                vod = self._build_vod(detail_url, "", "", "", "", "", "", "", "", "", content_url)
                return {"list": [vod]}

            html = self._get(detail_url, self.base, timeout=8)
            if not html:
                return {"list": []}

            soup = self._soup(html)

            title = ""
            pic = ""
            year = ""
            duration = ""
            category = ""
            actor = ""
            director = ""
            publisher = ""
            maker = ""
            desc = ""
            iframe_url = ""
            content_url = ""

            if soup:
                h1 = soup.find("h1")
                if h1:
                    title = self._clean(h1.get_text(" ", strip=True))
                if not title and soup.title:
                    title = self._clean(soup.title.get_text())

                for img in soup.find_all("img"):
                    src = self._img(img, detail_url)
                    if src:
                        pic = src
                        break

                # ===== 多模式视频源提取（优先级从高到低） =====

                # 模式1: JSON-LD contentUrl（最可靠）
                content_url = self._extract_json_ld_content_url(html)

                # 模式2: mvarr解密（备用）
                if not content_url:
                    mvarr_urls = self._extract_mvarr_urls(html)
                    if mvarr_urls:
                        content_url = mvarr_urls[0]

                # 模式3: 正则contentUrl / embedUrl
                if not content_url:
                    m = self._patterns['content_url'].search(html)
                    if m:
                        content_url = m.group(1)

                if not content_url:
                    m = self._patterns['embed_url'].search(html)
                    if m:
                        content_url = m.group(1)

                # 模式4: 直链MP4（amateurjav/amateur分类）
                if not content_url:
                    video_matches = self._patterns['cdn_video'].findall(html)
                    for mp4_url in video_matches:
                        if "1024cdn.sx" in mp4_url and not self._is_ad_url(mp4_url):
                            content_url = mp4_url
                            break

                # 模式5: CDN MP4正则
                if not content_url:
                    cdn_matches = self._patterns['cdn_mp4'].findall(html)
                    for mp4_url in cdn_matches:
                        if not self._is_ad_url(mp4_url):
                            content_url = mp4_url
                            break

                # 模式6: HLS/MP4通用
                if not content_url:
                    m = self._patterns['hls_url'].search(html)
                    if m:
                        content_url = m.group(1)
                    else:
                        m = self._patterns['m3u8'].search(html)
                        if m:
                            content_url = m.group(1)
                        else:
                            m = self._patterns['mp4'].search(html)
                            if m:
                                content_url = m.group(1)

                # 模式7: 查找非广告iframe
                if not content_url:
                    iframes = self._patterns['iframe_src'].findall(html)
                    for src in iframes:
                        full_src = self._abs(src, detail_url)
                        if not self._is_ad_url(full_src):
                            iframe_url = full_src
                            break

                # 提取元数据
                text = self._clean(soup.get_text(" ", strip=True))

                m = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text)
                if m:
                    year = m.group(1)
                m = re.search(r"(\d{1,4})\s*(?:分|分鐘|分钟|min)", text, re.I)
                if m:
                    duration = m.group(1) + "分钟"
                m = re.search(r"影片介紹\s*(.*?)(?:隨機主題|All clips|$)", text, re.I)
                if m:
                    desc = self._clean(m.group(1))
                m = re.search(r"影片類別\s*(.*?)\s*(?:女優|發行商|製作商|導演)", text, re.I)
                if m:
                    category = self._clean(m.group(1))
                m = re.search(r"女優\s*(.*?)\s*(?:發行商|製作商|導演|影片介紹)", text, re.I)
                if m:
                    actor = self._clean(m.group(1))
                m = re.search(r"發行商:\s*(.*?)\s*(?:製作商:|導演:|影片介紹)", text, re.I)
                if m:
                    publisher = self._clean(m.group(1))
                m = re.search(r"製作商:\s*(.*?)\s*(?:導演:|影片介紹)", text, re.I)
                if m:
                    maker = self._clean(m.group(1))
                m = re.search(r"導演:\s*(.*?)\s*(?:iframe|影片介紹)", text, re.I)
                if m:
                    director = self._clean(m.group(1))

            code = ""
            m = re.search(r"/([^/]+)\.html(?:\?|$)", detail_url, re.I)
            if m:
                code = m.group(1)
            if not title:
                title = code or "7mmtv"

            play_url = content_url or iframe_url or detail_url

            if content_url:
                self._content_url_cache[detail_url] = content_url

            vod = {
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_year": year,
                "vod_area": "日本",
                "vod_director": director,
                "vod_actor": actor,
                "vod_content": desc,
                "vod_remarks": duration,
                "vod_pubdate": publisher,
                "vod_class": category,
                "vod_play_from": "7mmtv",
                "vod_play_url": "播放$" + play_url,
            }

            if maker and not vod["vod_pubdate"]:
                vod["vod_pubdate"] = maker

            return {"list": [vod]}

        except Exception:
            return {"list": []}

    def _build_vod(self, detail_url, title, pic, year, actor, director, publisher, category, desc, duration, play_url):
        return {
            "vod_id": detail_url,
            "vod_name": title or "7mmtv",
            "vod_pic": pic,
            "vod_year": year,
            "vod_area": "日本",
            "vod_director": director,
            "vod_actor": actor,
            "vod_content": desc,
            "vod_remarks": duration,
            "vod_pubdate": publisher,
            "vod_class": category,
            "vod_play_from": "7mmtv",
            "vod_play_url": "播放$" + play_url,
        }

    # ---------------------------------------------------------
    # 搜索
    # ---------------------------------------------------------
    def searchContent(self, key, quick, pg="1"):
        try:
            key = str(key or "").strip()
            if not key:
                return {"list": []}

            candidates = [
                f"{self.base}search/{quote(key)}/1.html",
                f"{self.base}search.html?keyword={quote(key)}",
                f"{self.base}?s={quote(key)}",
            ]

            for url in candidates:
                html = self._get(url, self.base, timeout=8)
                if not html:
                    continue
                result = self._parse_search_html(html, url, key)
                if result:
                    return {"list": result, "page": int(pg or 1), "pagecount": 1}

            return {"list": []}
        except Exception:
            return {"list": []}

    def _parse_search_html(self, html, base_url, key):
        result = []
        seen = set()
        soup = self._soup(html)
        if soup:
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "_content/" not in href:
                    continue
                full = self._abs(href, base_url)
                if full in seen:
                    continue
                title = self._clean(a.get_text(" ", strip=True))
                if not title:
                    continue
                if key.lower() not in title.lower():
                    continue
                seen.add(full)
                pic = ""
                img = a.find("img")
                if img:
                    pic = self._img(img, base_url)
                result.append({"vod_id": full, "vod_name": title, "vod_pic": pic})
        return result

    # ---------------------------------------------------------
    # 播放解析
    # ---------------------------------------------------------
    def playerContent(self, flag, id, vipFlags):
        try:
            url = str(id or "").strip()
            if not url:
                return {}

            play_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0 Mobile Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Encoding": "identity",
            }

            # 1. 直接媒体地址（1024cdn.sx直链MP4）
            if self.isVideoFormat(url):
                referer = self._guess_referer(url)
                play_headers["Referer"] = referer
                play_headers["Origin"] = referer.rstrip("/")
                return {
                    "parse": 0,
                    "jx": 0,
                    "playUrl": "",
                    "url": url,
                    "header": play_headers,
                }

            # 2. 广告URL
            if self._is_ad_url(url):
                return {
                    "parse": 1, "jx": 1, "playUrl": "", "url": url,
                    "header": {"User-Agent": play_headers["User-Agent"], "Referer": self.base},
                }

            # 3. CDN智能识别与解析
            cdn_config = self._get_cdn_config(url)
            if cdn_config:
                m3u8_url = self._parse_cdn_url(url, cdn_config)
                if m3u8_url:
                    play_headers["Referer"] = cdn_config["referer"]
                    play_headers["Origin"] = cdn_config["origin"]
                    return {
                        "parse": 0, "jx": 0, "playUrl": "", "url": m3u8_url, "header": play_headers,
                    }

            # 4. 7mmtv详情页
            if "7mmtv.sx" in url:
                return self._parse_7mmtv_detail(url, play_headers)

            # 5. 其他iframe页面
            if self._is_iframe_page(url):
                m3u8_url = self._parse_generic_iframe(url)
                if m3u8_url:
                    referer = self._guess_referer(m3u8_url)
                    play_headers["Referer"] = referer
                    play_headers["Origin"] = referer.rstrip("/")
                    return {
                        "parse": 0, "jx": 0, "playUrl": "", "url": m3u8_url, "header": play_headers,
                    }

            # 6. 兜底
            return {
                "parse": 1, "jx": 1, "playUrl": "", "url": url,
                "header": {"User-Agent": play_headers["User-Agent"], "Referer": self.base},
            }

        except Exception:
            return {"parse": 1, "jx": 1, "playUrl": "", "url": str(id or "")}

    def _parse_cdn_url(self, url, cdn_config):
        """通用CDN解析"""
        try:
            html, status = self._get_stream(url, referer="https://7mmtv.sx/", timeout=8, max_bytes=65536)
            if not html or status != 200:
                return ""

            patterns_to_try = [
                ('turbos', True),
                ('m3u8', False),
                ('source', True),
                ('video', True),
                ('mp4', False),
                ('emturbo', False),
                ('playmogo', False),
                ('mmvh', False),
                ('mmsi', False),
            ]

            for pattern_name, need_check in patterns_to_try:
                m = self._patterns[pattern_name].search(html)
                if m:
                    video_url = m.group(1)
                    if need_check:
                        if self.isVideoFormat(video_url):
                            return video_url
                    else:
                        return video_url

            return ""

        except Exception:
            return ""

    def _parse_7mmtv_detail(self, url, play_headers):
        """解析7mmtv详情页"""
        # 检查缓存
        if url in self._content_url_cache:
            content_url = self._content_url_cache[url]
            result = self._try_play_url(content_url, play_headers)
            if result:
                return result

        # 获取详情页
        html = self._get(url, self.base, timeout=8)
        if not html:
            return {
                "parse": 1, "jx": 1, "playUrl": "", "url": url,
                "header": {"User-Agent": play_headers["User-Agent"], "Referer": self.base},
            }

        # 多模式提取
        content_url = ""

        # 模式1: JSON-LD contentUrl（最可靠）
        content_url = self._extract_json_ld_content_url(html)

        # 模式2: mvarr解密（备用）
        if not content_url:
            mvarr_urls = self._extract_mvarr_urls(html)
            if mvarr_urls:
                content_url = mvarr_urls[0]

        # 模式3: 正则contentUrl / embedUrl
        if not content_url:
            m = self._patterns['content_url'].search(html)
            if m:
                content_url = m.group(1)

        if not content_url:
            m = self._patterns['embed_url'].search(html)
            if m:
                content_url = m.group(1)

        # 模式4: CDN MP4
        if not content_url:
            cdn_matches = self._patterns['cdn_mp4'].findall(html)
            for mp4_url in cdn_matches:
                if not self._is_ad_url(mp4_url):
                    content_url = mp4_url
                    break

        # 模式5: HLS/MP4
        if not content_url:
            m = self._patterns['hls_url'].search(html)
            if m:
                content_url = m.group(1)

        # 模式6: 查找非广告iframe
        if not content_url:
            iframes = self._patterns['iframe_src'].findall(html)
            for src in iframes:
                full_src = self._abs(src, url)
                if not self._is_ad_url(full_src):
                    content_url = full_src
                    break

        # 尝试播放
        if content_url:
            self._content_url_cache[url] = content_url
            result = self._try_play_url(content_url, play_headers)
            if result:
                return result

        # 兜底
        return {
            "parse": 1, "jx": 1, "playUrl": "", "url": url,
            "header": {"User-Agent": play_headers["User-Agent"], "Referer": self.base},
        }

    def _try_play_url(self, url, play_headers):
        """尝试解析播放URL"""
        if not url:
            return None

        # 直接媒体格式（1024cdn.sx直链）
        if self.isVideoFormat(url):
            referer = self._guess_referer(url)
            play_headers["Referer"] = referer
            play_headers["Origin"] = referer.rstrip("/")
            return {
                "parse": 0, "jx": 0, "playUrl": "", "url": url, "header": play_headers,
            }

        # CDN智能识别
        cdn_config = self._get_cdn_config(url)
        if cdn_config:
            m3u8_url = self._parse_cdn_url(url, cdn_config)
            if m3u8_url:
                play_headers["Referer"] = cdn_config["referer"]
                play_headers["Origin"] = cdn_config["origin"]
                return {
                    "parse": 0, "jx": 0, "playUrl": "", "url": m3u8_url, "header": play_headers,
                }

        # 其他iframe
        if self._is_iframe_page(url):
            m3u8_url = self._parse_generic_iframe(url)
            if m3u8_url:
                referer = self._guess_referer(m3u8_url)
                play_headers["Referer"] = referer
                play_headers["Origin"] = referer.rstrip("/")
                return {
                    "parse": 0, "jx": 0, "playUrl": "", "url": m3u8_url, "header": play_headers,
                }

        return None

    def _is_iframe_page(self, url):
        iframe_indicators = [
            "embed", "player", "iframe", "video", "watch",
            "play", "stream", "view", "content", "t/", "e/", "v/"
        ]
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            for indicator in iframe_indicators:
                if indicator in path:
                    return True
        except Exception:
            pass
        return False

    def _parse_generic_iframe(self, url, depth=0):
        """通用iframe穿透解析（最多3层）"""
        if depth > 3:
            return ""

        try:
            html, status = self._get_stream(url, referer=self.base, timeout=8, max_bytes=131072)
            if not html or status != 200:
                return ""

            patterns_to_try = [
                ('turbos', True),
                ('emturbo', False),
                ('playmogo', False),
                ('mmvh', False),
                ('mmsi', False),
                ('m3u8', False),
                ('source', True),
                ('video', True),
                ('mp4', False),
                ('cdn_mp4', False),
            ]

            for pattern_name, need_check in patterns_to_try:
                m = self._patterns[pattern_name].search(html)
                if m:
                    video_url = m.group(1)
                    if need_check:
                        if self.isVideoFormat(video_url):
                            return video_url
                    else:
                        return video_url

            # 嵌套iframe - 递归穿透
            iframes = self._patterns['iframe_src'].findall(html)
            for src in iframes:
                full_src = self._abs(src, url)
                if not self._is_ad_url(full_src) and full_src != url:
                    result = self._parse_generic_iframe(full_src, depth + 1)
                    if result:
                        return result

            return ""

        except Exception:
            return ""

    def _guess_referer(self, url):
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # CDN域名
            cdn_config = self._get_cdn_config(url)
            if cdn_config:
                return cdn_config["referer"]

            # 1024cdn.sx 图片/视频CDN
            if "1024cdn" in domain or "1025cdn" in domain or "1026cdn" in domain:
                return "https://7mmtv.sx/"

            return self.base
        except Exception:
            return self.base

    def localProxy(self, param):
        return ""

    def action(self, action):
        return {}

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass
