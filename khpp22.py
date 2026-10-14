# -*- coding: utf-8 -*-
"""
色库视频 / 学习教程2026 — https://992.khpp22.cc
蜂蜜影视 Python 源（参考肉視頻 localProxy / getProxyUrl 兼容方式）

API: /api/v1/*
响应: X-Obf 反转减7 + X-Txt-Obf 文本解码
封面: /cover/{id}_cover.webp  (x-encrypted XOR，走 localProxy)
播放: 详情 sources[].episodes[].url 直链 m3u8
"""
import json
import re
import struct
import sys
from urllib.parse import quote, unquote

sys.path.append("..")
from base.spider import Spider


class Spider(Spider):

    siteUrl = "https://992.khpp22.cc"
    apiBase = "https://992.khpp22.cc/api/v1"
    UA = (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )

    TOB_OFFSET = 1000
    TOB_CJK_START = 0x4E00
    TOB_CJK_END = 0x9FFF
    TOB_CJK_RANGE = 0x9FFF - 0x4E00 + 1
    TOB_ASCII_BASE = 0x3400
    COVER_SECRET = "vody59!@"

    # 兜底分类（init 成功后会被 sdk-config 覆盖）
    CATE = [
        ("31", "国产"),
        ("80", "自拍偷拍"),
        ("81", "吃瓜网曝"),
        ("82", "主播直播"),
        ("83", "伦理三级"),
        ("85", "传媒探花"),
        ("93", "网红黑料"),
        ("32", "日韩"),
        ("86", "中文字幕"),
        ("87", "巨乳美乳"),
        ("88", "萝莉少女"),
        ("89", "人妻熟女"),
        ("90", "强奸乱伦"),
        ("91", "无码"),
        ("76", "伦理三级(日)"),
        ("33", "欧美"),
        ("34", "动漫"),
        ("71", "同性"),
        ("72", "基友"),
        ("73", "拉拉"),
        ("79", "伪娘"),
        ("74", "AI"),
        ("75", "明星"),
    ]

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self._cfg = None
        self._ready = False

    def init(self, extend=""):
        try:
            self._load_config()
            self._ready = True
        except Exception:
            self._ready = False
        return

    def getName(self):
        return "色库视频"

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return ".m3u8" in u or ".mp4" in u or ".ts" in u or "do=py" in u

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    # ---------- 代理入口（对齐肉視頻写法） ----------
    def _get_proxy_base(self):
        try:
            if hasattr(self, "getProxyUrl") and callable(self.getProxyUrl):
                base = self.getProxyUrl()
                if base:
                    return str(base).rstrip("&?")
        except Exception:
            pass
        for attr in ("t4_api", "localProxyUrl"):
            v = getattr(self, attr, None)
            if v:
                return str(v).rstrip("&?")
        return "http://127.0.0.1:9978/proxy?do=py"

    def _make_proxy_url(self, real_url, typ="cover"):
        proxy_base = self._get_proxy_base()
        sep = "&" if "?" in proxy_base else "?"
        return "%s%stype=%s&url=%s" % (
            proxy_base, sep, quote(str(typ), safe=""), quote(str(real_url), safe="")
        )

    # ---------- 加解密 ----------
    def _deobfuscate(self, s):
        n = len(s)
        out = [""] * n
        for i, ch in enumerate(s):
            out[n - 1 - i] = chr(ord(ch) - 7)
        return "".join(out)

    def _to_decode_text(self, s):
        out = []
        for ch in s:
            c = ord(ch)
            if self.TOB_ASCII_BASE <= c <= self.TOB_ASCII_BASE + 0xFF:
                out.append(chr(c - self.TOB_ASCII_BASE))
            elif self.TOB_CJK_START <= c <= self.TOB_CJK_END:
                out.append(chr(
                    self.TOB_CJK_START + (
                        ((c - self.TOB_CJK_START - self.TOB_OFFSET) % self.TOB_CJK_RANGE
                         + self.TOB_CJK_RANGE) % self.TOB_CJK_RANGE
                    )
                ))
            else:
                out.append(ch)
        return "".join(out)

    def _to_decode_tree(self, v):
        if isinstance(v, str):
            return self._to_decode_text(v)
        if isinstance(v, list):
            return [self._to_decode_tree(x) for x in v]
        if isinstance(v, dict):
            return {k: self._to_decode_tree(val) for k, val in v.items()}
        return v

    def _xor_cover(self, data, secret=None):
        secret = secret or self.COVER_SECRET or "vody59!@"
        key_a = bytes([(ord(secret[i]) if i < len(secret) else 120) for i in range(8)])
        key_b = bytes([(ord(secret[i + 8]) if (i + 8) < len(secret) else 121) for i in range(8)])
        buf = bytearray(data)
        n = len(buf)
        block = n - (n % 4)
        if block > 0:
            ka = list(struct.unpack("<II", key_a))
            kb = list(struct.unpack("<II", key_b))
            for i in range(block // 4):
                v = struct.unpack_from("<I", buf, i * 4)[0]
                v ^= ka[i & 1] ^ kb[i & 1]
                struct.pack_into("<I", buf, i * 4, v & 0xFFFFFFFF)
        for i in range(block, n):
            buf[i] ^= key_a[i & 7] ^ key_b[i & 7]
        return bytes(buf)

    # ---------- HTTP ----------
    def _headers(self):
        return {
            "User-Agent": self.UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": self.siteUrl + "/",
            "Origin": self.siteUrl,
        }

    def _raw_get(self, url, headers=None, timeout=20):
        headers = headers or self._headers()
        body = None
        hdrs = {}
        status = 0
        # 1) 框架 fetch
        try:
            if hasattr(self, "fetch"):
                rsp = self.fetch(url, headers=headers)
                if rsp is not None:
                    status = getattr(rsp, "status_code", None) or getattr(rsp, "status", 0) or 0
                    if hasattr(rsp, "content") and rsp.content is not None:
                        body = rsp.content
                    elif hasattr(rsp, "text"):
                        body = (rsp.text or "").encode("utf-8", errors="ignore")
                    if hasattr(rsp, "headers"):
                        try:
                            hdrs = {str(k).lower(): v for k, v in dict(rsp.headers).items()}
                        except Exception:
                            hdrs = {}
                    if body is not None:
                        return status or 200, hdrs, body
        except Exception:
            pass
        # 2) requests
        try:
            import requests
            r = requests.get(url, headers=headers, timeout=timeout, verify=False)
            return r.status_code, {str(k).lower(): v for k, v in r.headers.items()}, r.content
        except Exception:
            pass
        # 3) urllib
        try:
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
                h = {str(k).lower(): v for k, v in resp.headers.items()}
                return getattr(resp, "status", 200) or 200, h, data
        except Exception:
            return 0, {}, None

    def _api(self, path_qs):
        if path_qs.startswith("/api/v1"):
            url = self.siteUrl + path_qs
        elif path_qs.startswith("/api/"):
            url = self.siteUrl + path_qs.replace("/api/", "/api/v1/", 1)
        elif path_qs.startswith("/"):
            url = self.apiBase + path_qs
        else:
            url = self.apiBase + "/" + path_qs

        status, hdrs, body = self._raw_get(url, headers=self._headers())
        if not body:
            return {}
        try:
            text = body.decode("utf-8", errors="ignore")
        except Exception:
            text = str(body)
        if str(hdrs.get("x-obf") or "") == "1":
            try:
                text = self._deobfuscate(text)
            except Exception:
                pass
        try:
            j = json.loads(text)
        except Exception:
            return {}
        if isinstance(j, dict) and j.get("code") == 0 and str(hdrs.get("x-txt-obf") or "") == "1":
            try:
                j = self._to_decode_tree(j)
            except Exception:
                pass
        if isinstance(j, dict) and j.get("code") == 0:
            return j.get("data") if j.get("data") is not None else j
        return j if isinstance(j, dict) else {}

    def _load_config(self):
        data = self._api("/sdk-config")
        if not isinstance(data, dict) or not data:
            return
        self._cfg = data
        cover = data.get("cover") or {}
        if cover.get("secret"):
            self.COVER_SECRET = str(cover["secret"])
        cats = []
        for c in (data.get("categories") or []):
            cid = str(c.get("id"))
            cname = c.get("name") or cid
            cats.append((cid, cname))
            for ch in (c.get("children") or []):
                cats.append((str(ch.get("id")), "%s/%s" % (cname, ch.get("name") or "")))
        if cats:
            self.CATE = cats

    def _ensure(self):
        if not self._ready or not self._cfg:
            try:
                self._load_config()
                self._ready = True
            except Exception:
                pass

    def _cover_url(self, vid):
        raw = "%s/cover/%s_cover.webp" % (self.siteUrl, vid)
        return self._make_proxy_url(raw, "cover")

    def _fmt_duration(self, sec):
        try:
            sec = int(sec)
        except Exception:
            return ""
        if sec <= 0:
            return ""
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if h:
            return "%d:%02d:%02d" % (h, m, s)
        return "%d:%02d" % (m, s)

    def _item(self, it):
        vid = str(it.get("id") or "")
        title = (it.get("title") or "").strip()
        remarks = it.get("remarks") or ""
        if not remarks and it.get("duration_s"):
            remarks = self._fmt_duration(it.get("duration_s"))
        return {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": self._cover_url(vid),
            "vod_remarks": remarks,
        }

    # ---------- 首页 / 分类 / 详情 / 搜索 / 播放 ----------
    def homeContent(self, filter):
        self._ensure()
        classes = [{"type_id": tid, "type_name": name} for tid, name in self.CATE]
        return {"class": classes}

    def homeVideoContent(self):
        self._ensure()
        return self.categoryContent("0", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        self._ensure()
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        qs = "page=%d&size=24" % page
        if tid and str(tid) not in ("0", "all", ""):
            qs += "&cat=%s" % quote(str(tid))
        data = self._api("/videos?" + qs)
        if not isinstance(data, dict):
            data = {}
        items = data.get("list") or []
        total = int(data.get("total") or 0)
        size = int(data.get("size") or 24) or 24
        pagecount = (total + size - 1) // size if total else 999
        return {
            "list": [self._item(it) for it in items if isinstance(it, dict)],
            "page": page,
            "pagecount": max(pagecount, 1),
            "limit": size,
            "total": total or len(items),
        }

    def detailContent(self, ids):
        self._ensure()
        vid = str(ids[0])
        data = self._api("/video/" + vid)
        if not isinstance(data, dict):
            return {"list": []}
        v = data.get("video") or {}
        sources = data.get("sources") or []
        title = (v.get("title") or "").strip()
        pic = v.get("pic_url") or ""
        if not pic or "23.225." in pic or "127.0.0.1" in pic:
            pic = self._cover_url(vid)
        remarks = v.get("remarks") or self._fmt_duration(v.get("duration_s"))
        content = data.get("category_name") or ""
        tags = data.get("tags") or []
        if isinstance(tags, list) and tags:
            content = (content + " " + " ".join(
                [(t.get("name") if isinstance(t, dict) else str(t)) for t in tags[:8]]
            )).strip()

        froms, urls = [], []
        for src in sources:
            if not isinstance(src, dict):
                continue
            if src.get("playable") is False:
                continue
            name = src.get("from") or "线路"
            eps = src.get("episodes") or []
            parts = []
            for ep in eps:
                if not isinstance(ep, dict):
                    continue
                en = ep.get("name") or "正片"
                eu = ep.get("url") or ""
                if eu:
                    parts.append("%s$%s" % (en, eu))
            if parts:
                froms.append(str(name))
                urls.append("#".join(parts))

        if not froms:
            froms = ["色库"]
            urls = ["正片$"]

        return {"list": [{
            "vod_id": vid,
            "vod_name": title or "未知",
            "vod_pic": pic,
            "vod_remarks": remarks,
            "vod_content": content,
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
        }]}

    def searchContent(self, key, quick, pg="1"):
        self._ensure()
        try:
            page = int(pg)
        except Exception:
            page = 1
        qs = "page=%d&size=24&kw=%s" % (page, quote(key))
        data = self._api("/videos?" + qs)
        if not isinstance(data, dict):
            data = {}
        items = data.get("list") or []
        return {"list": [self._item(it) for it in items if isinstance(it, dict)]}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": {
                "User-Agent": self.UA,
                "Referer": self.siteUrl + "/",
                "Origin": self.siteUrl,
            },
        }

    def localProxy(self, param):
        """蜂蜜影视三元组: [code, contentType, body(bytes)]
        解密封面 /cover/{id}_cover.webp
        """
        try:
            if isinstance(param, str):
                url = param
            else:
                url = (param or {}).get("url") or (param or {}).get("src") or ""
            url = unquote(str(url)).strip()
            if not url:
                return [400, "text/plain", b"no url"]
            if not url.startswith("http"):
                url = self.siteUrl + (url if url.startswith("/") else "/" + url)

            status, hdrs, body = self._raw_get(url, headers={
                "User-Agent": self.UA,
                "Referer": self.siteUrl + "/",
                "Accept": "*/*",
            })
            if not body:
                return [404, "text/plain", b"empty"]

            enc = str(hdrs.get("x-encrypted") or "") == "1"
            ctype = hdrs.get("x-image-type") or hdrs.get("content-type") or "image/webp"
            # 加密封面或魔数不对时尝试 XOR
            need_xor = enc or (
                "/cover/" in url
                and not (body[:4] in (b"RIFF", b"\x89PNG") or body[:3] == b"\xff\xd8\xff")
            )
            if need_xor:
                try:
                    body = self._xor_cover(body, self.COVER_SECRET)
                except Exception:
                    pass
            if not ctype or "octet" in ctype or "text" in ctype or "html" in ctype:
                if body[:4] == b"RIFF":
                    ctype = "image/webp"
                elif body[:3] == b"\xff\xd8\xff":
                    ctype = "image/jpeg"
                elif body[:4] == b"\x89PNG":
                    ctype = "image/png"
                else:
                    ctype = "image/webp"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8", errors="ignore")]
