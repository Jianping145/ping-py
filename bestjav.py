#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BestJavPorn spider - bestjavporn.me
# 2026-10: 播放源改为 api.videplay.us 多线路，旧 /xx/ + AES 已失效
# 解析：rocket base64 取 embed → 二进制 ID / packer m3u8 → 失败则 parse=1 嗅探

import re
import json
import base64
import hashlib
import gzip
import zlib
import ssl
import http.cookiejar
import urllib.request
import urllib.parse
from urllib.parse import quote, urljoin

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


def format_remarks(brand="BestJAV", meta=""):
    clean_meta = re.sub(r"[\r\n\t]+", " ", str(meta or "").strip()).strip()
    if clean_meta:
        return "%s | %s" % (brand, clean_meta)
    return brand


def bin_decode_01(b):
    """把 01 二进制串解码成 ASCII id"""
    out = []
    for i in range(0, len(b) // 8 * 8, 8):
        out.append(chr(int(b[i:i + 8], 2)))
    return "".join(out)


def unpack_packer(html):
    """Dean Edwards packer → 明文"""
    m = re.search(
        r"return p\}\('([\s\S]*?)',(\d+),(\d+),'([\s\S]*?)'\.split\('\|'\)\)",
        html,
    )
    if not m:
        return ""
    payload, radix, count, keys_s = (
        m.group(1),
        int(m.group(2)),
        int(m.group(3)),
        m.group(4),
    )
    keys = keys_s.split("|")
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"

    def to_base(n, b):
        if n == 0:
            return "0"
        s = ""
        while n:
            s = digits[n % b] + s
            n //= b
        return s

    p, c = payload, count
    while c:
        c -= 1
        if c < len(keys) and keys[c]:
            p = re.sub(r"\b" + re.escape(to_base(c, radix)) + r"\b", keys[c], p)
    return p


class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://bestjavporn.me"
        self._ua = (
            "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        self.options = {}
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx),
        )
        # 第三方主机候选
        self.stream_hosts = [
            "https://mmsi02.com/e/",
            "https://mmvh02.com/v/",
            "https://mmvh02.com/e/",
            "https://vidhidefast.com/e/",
            "https://vidhidepre.com/e/",
            "https://morencius.com/embed/",
            "https://ahvsh.com/e/",
            "https://streamhide.com/e/",
            "https://filemoon.to/e/",
            "https://playmogo.com/e/",
            "https://dood.re/e/",
        ]

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        return True

    def getName(self):
        return "BestJavPorn"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        if any(b in low for b in ("preview.mp4", "sample.mp4", "trailer.mp4")):
            return False
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".mpd"))

    def manualVideoCheck(self):
        return True

    def log(self, msg):
        try:
            print("[bestjav] %s" % msg)
        except Exception:
            pass

    def _fetch(self, target_url, data=None, referer="", headers_custom=None):
        if not target_url:
            return {"code": 0, "text": "", "bytes": b"", "err": ""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self.siteUrl + target_url
        headers = {
            "User-Agent": self._ua,
            "Referer": referer if referer else (self.siteUrl + "/"),
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        if headers_custom:
            headers.update(headers_custom)
        req_data = None
        if isinstance(data, dict):
            req_data = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        last_err = ""
        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, data=req_data, headers=headers)
                with self.opener.open(req, timeout=18) as resp:
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        try:
                            raw = gzip.decompress(raw)
                        except Exception:
                            pass
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            try:
                                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                            except Exception:
                                pass
                    try:
                        text = raw.decode("utf-8")
                    except Exception:
                        text = raw.decode("latin1", errors="ignore")
                    return {"code": resp.getcode(), "text": text, "bytes": raw, "err": ""}
            except Exception as e:
                last_err = str(e)
                if attempt == 0:
                    continue
                return {"code": -1, "text": "", "bytes": b"", "err": last_err}
        return {"code": -1, "text": "", "bytes": b"", "err": last_err}

    def _clean_text(self, raw):
        t = re.sub(r"<[^>]+>", "", raw or "")
        return re.sub(r"[\r\n\t\s]+", " ", t).strip()

    def homeContent(self, filter):
        return {
            "class": [
                {"type_name": "有码专区", "type_id": "censored"},
                {"type_name": "素人专区", "type_id": "amateur"},
                {"type_name": "去码专区", "type_id": "reducing-mosaic"},
                {"type_name": "最新更新", "type_id": "latest"},
                {"type_name": "最多观看", "type_id": "most-viewed"},
                {"type_name": "最长时长", "type_id": "longest"},
                {"type_name": "随机推荐", "type_id": "random"},
            ]
        }

    def homeVideoContent(self):
        return self.categoryContent("censored", 1, None, {})

    def _extract_img(self, chunk):
        for attr in ("data-src", "data-lazy-src", "data-original", "src"):
            m = re.search(r'\b%s=["\']([^"\']+)["\']' % attr, chunk, re.I)
            if m:
                val = m.group(1).strip()
                if val and not val.startswith("data:") and "svg" not in val:
                    if val.startswith("//"):
                        val = "https:" + val
                    elif val.startswith("http://"):
                        val = "https://" + val[7:]
                    return val
        return ""

    def _wrap_img(self, img_url):
        if not img_url:
            return ""
        if not img_url.startswith("http"):
            img_url = urljoin(self.siteUrl, img_url)
        return "%s@Referer=%s@User-Agent=%s" % (
            img_url,
            self.siteUrl + "/",
            quote(self._ua),
        )

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        tid = str(tid).strip()
        route = {
            "censored": "/category/censored/",
            "amateur": "/category/amateur/",
            "reducing-mosaic": "/category/reducing-mosaic/",
            "latest": "/?filter=latest",
            "most-viewed": "/?filter=most-viewed",
            "longest": "/?filter=longest",
            "random": "/?filter=random",
        }
        if tid.startswith("http") or tid.startswith("/") or tid.startswith("?s="):
            base = tid if tid.startswith("http") else (
                self.siteUrl + (tid if tid.startswith("/") or tid.startswith("?") else "/" + tid)
            )
        elif tid in route:
            base = self.siteUrl + route[tid]
        else:
            base = self.siteUrl + "/category/censored/"
        if page > 1:
            if "filter=" in base or "?s=" in base:
                sep = "&" if "?" in base else "?"
                req_url = base + ("%spaged=%d" % (sep, page))
            else:
                req_url = base.rstrip("/") + "/page/%d/" % page
        else:
            req_url = base
        res = self._fetch(req_url)
        html = res.get("text", "")
        if not html or len(html) < 500:
            return {"page": page, "pagecount": 1, "limit": 0, "total": 0, "list": []}
        scoped = re.sub(r"<header[\s\S]*?</header>", "", html, flags=re.I)
        scoped = re.sub(r"<nav[\s\S]*?</nav>", "", scoped, flags=re.I)
        articles = re.findall(
            r'(<article[^>]*class="[^"]*loop-video[^"]*"[^>]*>[\s\S]*?</article>)',
            scoped,
            re.I,
        )
        if not articles:
            parts = scoped.split("thumb-block")
            if len(parts) > 2:
                articles = parts[1:]
        video_list = []
        for chunk in articles:
            link_m = re.search(
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*title=["\']([^"\']*)["\']',
                chunk,
                re.I,
            )
            if not link_m:
                link_m = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', chunk, re.I)
            if not link_m:
                continue
            href = link_m.group(1).strip()
            title = (
                self._clean_text(link_m.group(2))
                if link_m.lastindex and link_m.lastindex >= 2
                else ""
            )
            if not title:
                t2 = re.search(
                    r"<header[^>]*>[\s\S]*?<span[^>]*>([\s\S]*?)</span>", chunk, re.I
                )
                if t2:
                    title = self._clean_text(t2.group(1))
            if not href or href.startswith("javascript:"):
                continue
            full_href = href if href.startswith("http") else urljoin(self.siteUrl, href)
            pic = self._wrap_img(self._extract_img(chunk))
            dur_m = re.search(
                r'class="duration"[^>]*>[\s\S]*?</i>\s*([0-9:]+)', chunk, re.I
            )
            if not dur_m:
                dur_m = re.search(
                    r"duration[^>]*>[\s\S]*?([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)",
                    chunk,
                    re.I,
                )
            duration = self._clean_text(dur_m.group(1)) if dur_m else ""
            video_list.append({
                "vod_id": full_href,
                "vod_name": title or "未知片目",
                "vod_pic": pic,
                "vod_remarks": format_remarks("BestJAV", duration),
                "style": {"type": "rect", "ratio": 1.78},
            })
        has_next = bool(re.search(r'/page/%d[/\"\']' % (page + 1), scoped)) or bool(
            re.search(r"paged=%d" % (page + 1), scoped)
        )
        return {
            "page": page,
            "pagecount": (page + 1) if has_next else page,
            "limit": len(video_list),
            "total": 9999 if has_next else len(video_list),
            "list": video_list,
        }

    def _extract_embed_url(self, html):
        # rocket-lazyload base64 脚本里的 defaultUrl
        for m in re.finditer(
            r"data-rocketlazyloadscript=['\"]data:text/javascript;base64,([A-Za-z0-9+/=]+)['\"]",
            html,
        ):
            try:
                js = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
                um = re.search(r'defaultUrl\s*=\s*["\']([^"\']+)["\']', js)
                if um:
                    u = um.group(1)
                    if u.startswith("http://"):
                        u = "https://" + u[7:]
                    return u
            except Exception:
                pass
        # 明文
        m2 = re.search(
            r'(https?://(?:api\.)?videplay\.[a-z]+/embed/[^"\'\s]+)', html, re.I
        )
        if m2:
            return m2.group(1).replace("http://", "https://")
        m3 = re.search(r'(https?://[^"\']+/xx/[A-Za-z0-9]+)', html)
        if m3:
            return m3.group(1).replace("http://", "https://")
        return ""

    def _m3u8_from_html(self, html):
        if not html:
            return ""
        if "eval(function" in html:
            unpacked = unpack_packer(html)
            if unpacked:
                m = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', unpacked)
                if m:
                    return m.group(0).replace("\\/", "/")
                m = re.search(
                    r'["\']hls2["\']\s*:\s*["\'](https?://[^"\']+)["\']', unpacked
                )
                if m:
                    return m.group(1).replace("\\/", "/")
        m = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html)
        if m and "preview" not in m.group(0).lower():
            return m.group(0)
        m = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html, re.I)
        if m:
            return m.group(1)
        return ""

    def _ids_from_embed(self, emb_html):
        """从下载链二进制串提取第三方视频 id"""
        ids = []
        for b in re.findall(
            r"(?:streamhide|doodstream)/([01]{40,})\.html", emb_html, re.I
        ):
            try:
                vid = bin_decode_01(b)
                if vid and vid not in ids:
                    ids.append(vid)
            except Exception:
                pass
        return ids

    def _resolve_from_hosts(self, vids, referer):
        for vid in vids:
            for host in self.stream_hosts:
                url = host + vid
                res = self._fetch(url, referer=referer)
                text = res.get("text", "")
                if not text or len(text) < 400:
                    continue
                m3 = self._m3u8_from_html(text)
                if m3:
                    self.log("host hit %s" % host)
                    return m3
        return ""

    def _resolve_stream(self, page_url, html=None):
        if not html:
            res = self._fetch(page_url)
            html = res.get("text", "")
        if not html:
            return "", ""

        # 页内直链
        m3 = self._m3u8_from_html(html)
        if m3:
            return m3, ""

        embed = self._extract_embed_url(html)
        if not embed:
            return "", ""

        emb = self._fetch(embed, referer=page_url)
        emb_html = emb.get("text", "")

        # embed 页直链 / packer
        m3 = self._m3u8_from_html(emb_html)
        if m3:
            return m3, embed

        # 二进制 id → 多主机尝试
        vids = self._ids_from_embed(emb_html)
        if vids:
            m3 = self._resolve_from_hosts(vids, embed)
            if m3:
                return m3, embed

        # 返回 embed 供嗅探
        return "", embed

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        target_url = str(raw_id)
        res = self._fetch(target_url)
        html = res.get("text", "")
        title_m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
        if not title_m:
            title_m = re.search(r'itemprop="name"\s+content="([^"]+)"', html, re.I)
        title = self._clean_text(title_m.group(1)) if title_m else "正片详情"
        cover = self._wrap_img(self._extract_img(html))
        dur_m = re.search(r'class="duration"[^>]*>[\s\S]*?([0-9:]+)', html, re.I)
        dur_str = self._clean_text(dur_m.group(1)) if dur_m else ""
        # 播放时实时解析，避免 token 过期
        final_deliver = "raw_page@@%s" % target_url
        return {
            "list": [{
                "vod_id": target_url,
                "vod_name": title,
                "vod_pic": cover,
                "vod_remarks": format_remarks("BestJAV", dur_str),
                "vod_content": title,
                "vod_play_from": "BestJAV",
                "vod_play_url": "正片$%s" % final_deliver,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        raw = str(id).strip()
        stream_url = ""
        embed_url = ""
        page = ""

        if raw.startswith("raw_page@@"):
            page = raw.split("@@", 1)[1]
            stream_url, embed_url = self._resolve_stream(page)
        elif raw.startswith("http") and self.isVideoFormat(raw):
            stream_url = raw
        elif raw.startswith("http") and "videplay" in raw and "/embed/" in raw:
            emb = self._fetch(raw, referer=self.siteUrl + "/")
            stream_url = self._m3u8_from_html(emb.get("text", ""))
            if not stream_url:
                vids = self._ids_from_embed(emb.get("text", ""))
                stream_url = self._resolve_from_hosts(vids, raw)
            embed_url = raw
        elif raw.startswith("http"):
            stream_url, embed_url = self._resolve_stream(raw)

        headers = {
            "User-Agent": self._ua,
            "Referer": self.siteUrl + "/",
            "Origin": self.siteUrl,
            "Accept": "*/*",
        }
        if stream_url:
            if any(x in stream_url for x in ("dramiyos", "mediastream", "cdn", "m3u8")):
                headers["Referer"] = (embed_url or "https://api.videplay.us/") 
                headers["Origin"] = "https://api.videplay.us"
            return {
                "parse": 0,
                "jx": 0,
                "playUrl": "",
                "url": stream_url,
                "header": headers,
            }

        # 嗅探 fallback：把 videplay embed 交给播放器
        sniff = embed_url or page or raw
        self.log("fallback sniff %s" % sniff[:50])
        return {
            "parse": 1,
            "jx": 0,
            "playUrl": "",
            "url": sniff,
            "header": {
                "User-Agent": self._ua,
                "Referer": self.siteUrl + "/",
            },
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        q = quote(str(key).strip())
        path = ("/page/%d/?s=%s" % (page, q)) if page > 1 else ("/?s=%s" % q)
        return self.categoryContent(path, page, None, {})

    def localProxy(self, params):
        url = params.get("url", "")
        if not url:
            return [404, "text/plain", b""]
        res = self._fetch(url, referer=self.siteUrl + "/")
        raw_b = res.get("bytes", b"")
        mime = "image/jpeg"
        if raw_b.startswith(b"\x89PNG"):
            mime = "image/png"
        elif raw_b.startswith(b"GIF8"):
            mime = "image/gif"
        return [res.get("code", 200), mime, raw_b]

    def destroy(self):
        self.options = {}
