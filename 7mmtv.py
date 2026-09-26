# -*- coding: utf-8 -*-
"""
7mmtv.sx TVBox / T4Api Spider - 修复版 v18
修复：
1. mvarr 解码索引错误（encoded/base 错位）
2. emturbovid/turboviplay 的 data-hash m3u8 提取
3. mmvh/vidhide 类页面 Dean Edwards packer 解包提取 m3u8
4. 國產影片：mvarr 加密 ID 解密（parseInt+XOR + AES-CBC）
5. 多线路：SW/TV/VH/DO/SP 全部返回（网页多线路多清晰度）
6. CDN referer / Origin 更准确
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
            'custom_cdn': re.compile(r'["\'](https?://[^"\']*\.cyou/[^"\']*\.txt#\.m3u8[^"\']*)["\']', re.I),
            'cdn_mp4': re.compile(r'["\'](https?://[^"\']*102[4-6]cdn\.sx/[^"\']+\.mp4[^"\']*)["\']', re.I),
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
            'quality_json': re.compile(r'\{"names":\[[^\]]+\],"urls":\[[^\]]+\],"headers":\[[^\]]+\]\}', re.I),
            # v16 新增
            'data_hash': re.compile(r'data-hash=["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', re.I),
            'any_m3u8': re.compile(r'(https?://[^\s"\'<>\\]+\.m3u8(?:\?[^\s"\'<>\\]*)?)', re.I),
            'relative_m3u8': re.compile(r'["\'](/[^"\']*master\.m3u8[^"\']*)["\']', re.I),
            'packer': re.compile(
                r"eval\(function\(p,a,c,k,e,d\).*?\}\('(.*)',(\d+),(\d+),'(.*)'\.split\('\|'\)\)\)",
                re.I | re.S
            ),
        }

        # CDN配置
        self.cdn_config = {
            "mmvh02.com": {"referer": "https://mmtv01.xyz/", "origin": "https://mmtv01.xyz", "priority": 1},
            "mmvh": {"referer": "https://mmtv01.xyz/", "origin": "https://mmtv01.xyz", "priority": 1},
            "playmogo.com": {"referer": "https://7mmtv.sx/", "origin": "https://7mmtv.sx", "priority": 2},
            "emturbovid.com": {"referer": "https://emturbovid.com/", "origin": "https://emturbovid.com", "priority": 3},
            "turboviplay.com": {"referer": "https://emturbovid.com/", "origin": "https://emturbovid.com", "priority": 3},
            "mmsi02.com": {"referer": "https://mmsi02.com/", "origin": "https://mmsi02.com", "priority": 4},
            "turbosplayer.com": {"referer": "https://mmtv01.xyz/", "origin": "https://mmtv01.xyz", "priority": 5},
            "cyou": {"referer": "https://7mmtv.sx/", "origin": "https://7mmtv.sx", "priority": 6},
            "vidhide": {"referer": "https://mmtv01.xyz/", "origin": "https://mmtv01.xyz", "priority": 1},
            "dramiyos": {"referer": "https://mmtv01.xyz/", "origin": "https://mmtv01.xyz", "priority": 1},
            "harbortraildesignstudio": {"referer": "https://mmtv01.xyz/", "origin": "https://mmtv01.xyz", "priority": 1},
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

    def _extract_page_crypto_params(self, html):
        """从页面提取 AES 解密参数（國產/部分分类 mvarr 加密用）"""
        params = {
            "xor_key": 26,
            "radix": 8,
            "aes_key": "9bed2afeec277724",
            "aes_iv": "6e31f81c1836d9f7",
        }
        try:
            m = re.search(r'hadeedg252\s*=\s*(\d+)', html)
            if m:
                params["xor_key"] = int(m.group(1))
            m = re.search(r'hcdeedg252\s*=\s*(\d+)', html)
            if m:
                params["radix"] = int(m.group(1))
            m = re.search(r"argdeqweqweqwe\s*=\s*'([^']+)'", html)
            if m:
                params["aes_key"] = m.group(1)
            m = re.search(r"hdddedg252\s*=\s*'([^']+)'", html)
            if m:
                params["aes_iv"] = m.group(1)
            # 兼容 d/f 后缀变量
            if not re.search(r'hcdeedg252\s*=', html):
                m = re.search(r'hcdeed[df]252\s*=\s*(\d+)', html)
                if m:
                    params["radix"] = int(m.group(1))
            if not re.search(r'hadeedg252\s*=', html):
                m = re.search(r'hadeed[df]252\s*=\s*(\d+)', html)
                if m:
                    params["xor_key"] = int(m.group(1))
        except Exception:
            pass
        return params

    def _aes_cbc_decrypt(self, ciphertext_b64, key_str, iv_str):
        """AES-128-CBC 解密，返回明文。优先 cryptography / pycryptodome，否则 openssl。"""
        import base64
        try:
            raw = base64.b64decode(ciphertext_b64)
        except Exception:
            return ""
        key = key_str.encode("utf-8")[:16].ljust(16, b"\0")
        iv = iv_str.encode("utf-8")[:16].ljust(16, b"\0")

        # 1) cryptography
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            pt = cipher.decryptor().update(raw) + cipher.decryptor().finalize()
            if pt and 1 <= pt[-1] <= 16 and pt.endswith(bytes([pt[-1]]) * pt[-1]):
                pt = pt[:-pt[-1]]
            return pt.decode("utf-8", errors="ignore")
        except Exception:
            pass

        # 2) pycryptodome
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import unpad
            cipher = AES.new(key, AES.MODE_CBC, iv)
            pt = unpad(cipher.decrypt(raw), 16)
            return pt.decode("utf-8", errors="ignore")
        except Exception:
            pass

        # 3) openssl CLI
        try:
            import subprocess, tempfile, os
            key_hex = key.hex()
            iv_hex = iv.hex()
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(raw)
                ct_path = f.name
            try:
                out = subprocess.check_output(
                    ["openssl", "enc", "-aes-128-cbc", "-d",
                     "-K", key_hex, "-iv", iv_hex, "-in", ct_path],
                    stderr=subprocess.DEVNULL, timeout=5,
                )
                return out.decode("utf-8", errors="ignore")
            finally:
                try:
                    os.unlink(ct_path)
                except Exception:
                    pass
        except Exception:
            pass
        return ""

    def _decode_mvarr_id(self, encoded, crypto_params=None):
        """解密 mvarr 中的加密播放 ID
        算法：split(sep) → parseInt(radix) XOR xor_key → fromCharCode → Base64 → AES-CBC
        """
        if not encoded:
            return ""
        # 旧格式：用 w 分隔的 hex token —— 多数无法直接得到有效 ID，返回空
        # （此类页面通常有 JSON-LD contentUrl 可用）
        if "w" in encoded and "i" not in encoded:
            cleaned = encoded.replace("w", "")
            if re.match(r'^[a-zA-Z0-9_-]{4,40}$', cleaned):
                return cleaned
            return ""

        params = crypto_params or {}
        xor_key = params.get("xor_key", 26)
        radix = params.get("radix", 8)
        aes_key = params.get("aes_key", "9bed2afeec277724")
        aes_iv = params.get("aes_iv", "6e31f81c1836d9f7")

        try:
            r = radix if radix <= 25 else radix % 25
            if r < 2:
                r = 8
            sep = chr(r + 97)
            parts = encoded.split(sep)
            chars = []
            for p in parts:
                if not p:
                    continue
                v = int(p, r) ^ xor_key
                chars.append(chr(v & 0xff))
            b64 = "".join(chars)
            if not b64:
                return ""
            # 若已经是明文 ID（无 AES）
            if re.match(r"^[a-zA-Z0-9_-]+$", b64) and len(b64) < 20:
                return b64
            plain = self._aes_cbc_decrypt(b64, aes_key, aes_iv)
            plain = (plain or "").strip()
            # 校验：播放 ID 应为较短的字母数字串
            if plain and re.match(r'^[a-zA-Z0-9_-]{4,40}$', plain):
                return plain
            return ""
        except Exception:
            return ""

    def _extract_mvarr_urls(self, html):
        """提取mvarr中的所有播放器URL，按CDN优先级排序
        mvarr 结构: [['iframe_id','encoded','<iframe attrs>','base_url','','></iframe>','']]
        groups: 0=key, 1=id, 2=encoded, 3=attrs, 4=base, 5='', 6=close, 7=''
        """
        urls = []
        crypto_params = self._extract_page_crypto_params(html)
        mvarr_matches = self._patterns['mvarr'].findall(html)

        for match in mvarr_matches:
            key = match[0]
            encoded = match[2]
            iframe_base = match[4]

            if not iframe_base or not encoded:
                continue

            # 解密播放 ID
            play_id = self._decode_mvarr_id(encoded, crypto_params)
            if not play_id:
                # 解密失败时跳过（避免把密文当 URL）
                continue

            if iframe_base.startswith('//'):
                full_url = 'https:' + iframe_base + play_id
            elif iframe_base.startswith('http'):
                full_url = iframe_base + play_id
            else:
                full_url = iframe_base + play_id

            if 'play.php?id=' in full_url:
                priority = 80
            elif self._is_ad_url(full_url):
                continue
            else:
                cdn_config = self._get_cdn_config(full_url)
                priority = cdn_config.get("priority", 50) if cdn_config else 50

            # 线路名：根据 mvarr key 前缀映射（与网页 SW/TV/VH/DO/SP 一致）
            key_prefix = key.split('_')[0] if key else ''
            name_map = {
                '37': 'SW',   # mmsi
                '38': 'VH',   # mmvh
                '28': 'DO',   # playmogo
                '40': 'TV',   # emturbovid
                '42': 'SP',   # play.php / 备用
            }
            line_name = name_map.get(key_prefix, f'线路{key_prefix or len(result)+1}')

            urls.append((priority, line_name, full_url))

        urls.sort(key=lambda x: x[0])
        # 去重保序，返回 [(name, url), ...]
        seen = set()
        result = []
        for priority, name, url in urls:
            if url not in seen:
                seen.add(url)
                result.append((name, url))
        return result

    def _extract_json_ld_content_url(self, html):
        """从JSON-LD中提取contentUrl"""
        content_url = ""
        json_ld_scripts = self._patterns['json_ld'].findall(html)

        for script_content in json_ld_scripts:
            try:
                data = json.loads(script_content)
                if isinstance(data, dict):
                    if data.get("@type") == "VideoObject":
                        content_url = data.get("contentUrl", "") or data.get("embedUrl", "")
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

    def _parse_quality_json(self, html):
        """解析多清晰度JSON格式"""
        try:
            m = self._patterns['quality_json'].search(html)
            if m:
                data = json.loads(m.group(0))
                if "urls" in data and len(data["urls"]) > 0:
                    # 返回第一个URL（通常是最高清晰度）
                    url = data["urls"][0]
                    # 清理URL（移除#isVideo=true#等后缀）
                    url = url.split('#')[0]
                    return url
        except Exception:
            pass
        return ""

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

                    pic = ""
                    img = col_item.find("img")
                    if img:
                        pic = self._img(img, url)

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
            play_lines = []

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

                # 收集全部播放线路 [(name, url), ...]
                # 模式1: JSON-LD contentUrl（作为主线路之一）
                content_url = self._extract_json_ld_content_url(html)

                # 模式2: mvarr 解密（多线路 SW/TV/VH/DO/SP）
                mvarr_urls = self._extract_mvarr_urls(html)
                if mvarr_urls:
                    play_lines.extend(mvarr_urls)
                    if not content_url:
                        content_url = mvarr_urls[0][1]

                # 模式3: 正则 contentUrl / embedUrl
                if not content_url:
                    m = self._patterns['content_url'].search(html)
                    if m:
                        content_url = m.group(1)
                if not content_url:
                    m = self._patterns['embed_url'].search(html)
                    if m:
                        content_url = m.group(1)

                # 模式4: 直链 MP4
                if not content_url:
                    video_matches = self._patterns['cdn_video'].findall(html)
                    for mp4_url in video_matches:
                        if "1024cdn" in mp4_url and not self._is_ad_url(mp4_url):
                            content_url = mp4_url
                            break

                # 模式5: CDN MP4
                if not content_url:
                    cdn_matches = self._patterns['cdn_mp4'].findall(html)
                    for mp4_url in cdn_matches:
                        if not self._is_ad_url(mp4_url):
                            content_url = mp4_url
                            break

                # 模式6: HLS/MP4 通用
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

                # 模式7: 非广告 iframe
                if not content_url:
                    iframes = self._patterns['iframe_src'].findall(html)
                    for src in iframes:
                        full_src = self._abs(src, detail_url)
                        if not self._is_ad_url(full_src):
                            iframe_url = full_src
                            break

                # 若 JSON-LD contentUrl 不在 mvarr 线路中，补为主线路
                if content_url:
                    existing = {u for _, u in play_lines}
                    if content_url not in existing:
                        # 根据域名猜测线路名
                        cu = content_url.lower()
                        if 'emturbo' in cu:
                            play_lines.insert(0, ('TV', content_url))
                        elif 'mmvh' in cu:
                            play_lines.insert(0, ('VH', content_url))
                        elif 'playmogo' in cu:
                            play_lines.insert(0, ('DO', content_url))
                        elif 'mmsi' in cu:
                            play_lines.insert(0, ('SW', content_url))
                        else:
                            play_lines.insert(0, ('主线', content_url))

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

            # 组装多线路
            if not play_lines:
                fallback = content_url or iframe_url or detail_url
                play_lines = [('播放', fallback)]

            if content_url:
                self._content_url_cache[detail_url] = content_url

            # TVBox 多线路格式: from 用 $$$ 分隔，url 用 $$$ 分隔
            from_list = []
            url_list = []
            for name, url in play_lines:
                from_list.append(name)
                url_list.append(f"CD1${url}")

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
                "vod_play_from": "$$$".join(from_list),
                "vod_play_url": "$$$".join(url_list),
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
    # 播放解析 - 修复版
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

            # 1. 直接媒体地址
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


    def _to_base(self, n, base):
        if n == 0:
            return '0'
        digits = '0123456789abcdefghijklmnopqrstuvwxyz'
        s = ''
        while n:
            s = digits[n % base] + s
            n //= base
        return s

    def _unpack_packer(self, html):
        """解包 Dean Edwards packer，返回解包后的 JS 文本"""
        try:
            m = self._patterns['packer'].search(html)
            if not m:
                return ''
            p, a, c, ks = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split('|')
            p = p.replace("\\'", "'").replace("\\\\", "\\")
            while c:
                c -= 1
                if c < len(ks) and ks[c]:
                    token = self._to_base(c, a)
                    p = re.sub(r'\b' + re.escape(token) + r'\b', ks[c], p)
            return p
        except Exception:
            return ''

    def _extract_media_from_html(self, html, base_url=''):
        """从播放页 HTML 中提取真实 m3u8/mp4 地址（含 packer / data-hash）"""
        if not html:
            return ''

        # 1. data-hash（emturbovid / turboviplay）
        m = self._patterns['data_hash'].search(html)
        if m:
            return m.group(1).split('#')[0]

        # 2. quality_json
        quality_url = self._parse_quality_json(html)
        if quality_url:
            return quality_url

        # 3. 解包 packer 后再提取（mmvh / vidhide）
        unpacked = self._unpack_packer(html)
        search_html = unpacked if unpacked else html

        # 优先绝对 m3u8
        for pat_name in ('any_m3u8', 'm3u8', 'hls_url'):
            m = self._patterns[pat_name].search(search_html)
            if m:
                u = m.group(1).split('#')[0]
                if u.startswith('http') and not self._is_ad_url(u):
                    return u

        # 相对 master.m3u8
        m = self._patterns['relative_m3u8'].search(search_html)
        if m and base_url:
            return urljoin(base_url, m.group(1).split('#')[0])

        # 其它模式
        patterns_to_try = [
            ('turbos', True),
            ('custom_cdn', False),
            ('source', True),
            ('video', True),
            ('mp4', False),
            ('emturbo', False),
            ('playmogo', False),
            ('mmvh', False),
            ('mmsi', False),
            ('cdn_mp4', False),
        ]
        for pattern_name, need_check in patterns_to_try:
            m = self._patterns[pattern_name].search(search_html)
            if m:
                video_url = m.group(1).split('#')[0]
                if need_check:
                    if self.isVideoFormat(video_url):
                        return video_url
                else:
                    if video_url.startswith('http') and not self._is_ad_url(video_url):
                        return video_url

        return ''

    def _parse_cdn_url(self, url, cdn_config):
        """CDN解析 - 支持turbosplayer / emturbovid / mmvh / playmogo 等"""
        try:
            referer = cdn_config.get("referer") or self.base
            html, status = self._get_stream(url, referer=referer, timeout=12, max_bytes=400000)
            if not html:
                return ""
            # Cloudflare 挑战页直接放弃
            if 'Just a moment' in html or 'cf-browser-verification' in html or status in (403, 503):
                # 再试一次无 stream 限制
                html = self._get(url, referer=referer, timeout=12)
                if not html or 'Just a moment' in html:
                    return ""

            media = self._extract_media_from_html(html, base_url=url)
            return media

        except Exception:
            return ""

    def _parse_7mmtv_detail(self, url, play_headers):
        """解析7mmtv详情页"""
        if url in self._content_url_cache:
            content_url = self._content_url_cache[url]
            result = self._try_play_url(content_url, play_headers)
            if result:
                return result

        html = self._get(url, self.base, timeout=8)
        if not html:
            return {
                "parse": 1, "jx": 1, "playUrl": "", "url": url,
                "header": {"User-Agent": play_headers["User-Agent"], "Referer": self.base},
            }

        content_url = ""

        # 模式1: JSON-LD contentUrl
        content_url = self._extract_json_ld_content_url(html)

        # 模式2: mvarr解密
        if not content_url:
            mvarr_urls = self._extract_mvarr_urls(html)
            if mvarr_urls:
                content_url = mvarr_urls[0][1]

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

        if content_url:
            self._content_url_cache[url] = content_url
            result = self._try_play_url(content_url, play_headers)
            if result:
                return result

        return {
            "parse": 1, "jx": 1, "playUrl": "", "url": url,
            "header": {"User-Agent": play_headers["User-Agent"], "Referer": self.base},
        }

    def _try_play_url(self, url, play_headers):
        """尝试解析播放URL"""
        if not url:
            return None

        # 直接媒体格式
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
            html, status = self._get_stream(url, referer=self.base, timeout=12, max_bytes=400000)
            if not html:
                return ""
            if 'Just a moment' in html or status in (403, 503):
                html = self._get(url, referer=self.base, timeout=12)
                if not html or 'Just a moment' in html:
                    return ""

            media = self._extract_media_from_html(html, base_url=url)
            if media:
                return media

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

            cdn_config = self._get_cdn_config(url)
            if cdn_config:
                return cdn_config["referer"]

            if any(x in domain for x in ("1024cdn", "1025cdn", "1026cdn", "n39s.", "n3.")):
                return "https://7mmtv.sx/"
            if "turboviplay" in domain or "emturbo" in domain:
                return "https://emturbovid.com/"
            if any(x in domain for x in ("dramiyos", "harbortrail", "vidhide", "mmvh")):
                return "https://mmtv01.xyz/"

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
