# -*- coding: utf-8 -*-
# 91Hub (91hubw.com) 蜂蜜影视爬虫
# v11：封面 AES 解密 + 蜂蜜/FongMi 兼容请求 + 代理 url= 修正
# 2026-10-23

import json
import re
import sys
import ast
import base64
from urllib.parse import quote, unquote

sys.path.append('..')
try:
    from base.spider import Spider
except Exception:
    class Spider:
        def fetch(self, url, headers=None, timeout=15):
            import requests
            return requests.get(url, headers=headers or {}, timeout=timeout, verify=False)


class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://91hubw.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": "https://91hubw.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.cateManual = {
            "最新上架": "zxsj",
            "推荐给你": "tjgn",
            "家庭乱伦": "jtll",
            "萝莉少女": "llsn",
            "禁漫天堂": "jmtt",
            "网黄明星": "whmx",
            "熟女少妇": "snsf",
            "偷拍自拍": "tpzp",
            "强奸迷奸": "qjmj",
            "自慰高潮": "zwgc",
            "猎奇重口": "lqzk",
            "会所按摩": "hsam",
            "男上加男": "nsjn",
            "黑料吃瓜": "hlcg",
            "人妖TS": "ryts",
            "校园师生": "xyss",
            "童颜巨乳": "tyjr",
            "国产传媒": "gccm",
            "国产三级": "gcsj",
            "日韩伦理": "rhll",
            "欧美激情": "omjq",
            "媚黑一族": "mhyz",
            "探花大神": "thds",
            "福利姬": "flj",
            "制服诱惑": "zfyh",
            "无套内射": "wtns",
            "AI换脸": "aihl",
            "SM调教": "smdj",
            "网黄主播": "whzb",
            "户外搭讪": "hwds",
            "车震野合": "czyh",
            "女同拉拉": "ntll",
            "绿帽换妻": "lmhq",
            "成人综艺": "crzy",
            "白虎嫩穴": "bhnx",
            "勾引偷情": "gytq",
            "足交肛交": "zjgj",
            "多人群交": "drqj",
            "异域三级": "yysj",
            "原创精选": "ycjx",
            "足球宝贝": "zqbb",
            "AI成人短剧": "aicrdj",
        }


    def _req(self, url, method="GET", data=None, headers=None, timeout=20):
        """兼容 蜂蜜 / FongMi / peekpro"""
        h = dict(self.headers)
        if headers:
            h.update(headers)
        # BaseSpider
        try:
            if method.upper() == "POST" and hasattr(self, "post"):
                r = self.post(url, data=data, headers=h, timeout=timeout)
            elif hasattr(self, "fetch"):
                r = self.fetch(url, headers=h, timeout=timeout)
            else:
                r = None
            if r is not None:
                text, code = "", 200
                if hasattr(r, "text"):
                    text = r.text or ""
                    code = getattr(r, "status_code", 200) or 200
                elif hasattr(r, "content"):
                    text = r.content.decode("utf-8", "ignore")
                    code = getattr(r, "status_code", 200) or 200
                elif isinstance(r, str):
                    text = r
                elif isinstance(r, dict):
                    text = r.get("content") or r.get("text") or ""
                    code = r.get("code") or 200
                if text:
                    return {"code": code, "text": text}
        except Exception as e:
            print(f"[req base] {e}")
        # requests
        try:
            import requests
            if method.upper() == "POST":
                r = requests.post(url, data=data, headers=h, timeout=timeout, verify=False)
            else:
                r = requests.get(url, headers=h, timeout=timeout, verify=False)
            return {"code": r.status_code, "text": r.text or ""}
        except Exception as e:
            print(f"[req requests] {e}")
        # urllib
        try:
            import urllib.request
            body = data.encode("utf-8") if isinstance(data, str) else data
            req = urllib.request.Request(url, data=body, headers=h, method=method.upper())
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {"code": resp.status, "text": resp.read().decode("utf-8", "ignore")}
        except Exception as e:
            print(f"[req urllib] {e}")
        return {"code": 0, "text": ""}

    def getName(self):
        return "91Hub"

    def isVideoFormat(self, url):
        return any(x in str(url) for x in [".m3u8", ".mp4", "/media/m3u8/"])

    def manualVideoCheck(self):
        return True

    def homeContent(self, filter):
        result = {"class": [], "list": []}
        for name, tid in self.cateManual.items():
            result["class"].append({"type_name": name, "type_id": tid})
        try:
            html = (self._req(self.host).get("text") or "")
            result["list"] = self._parse_list(html)[:20]
        except Exception as e:
            print(f"[home] {e}")
        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": pg, "pagecount": 9999, "limit": 24, "total": 999999}
        try:
            pg = str(pg)
            url = f"{self.host}/movie/{tid}/" if pg in ("1", "0", "") else f"{self.host}/movie/{tid}/page/{pg}/"
            html = (self._req(url).get("text") or "")
            result["list"] = self._parse_list(html)
        except Exception as e:
            print(f"[cate] {e}")
        return result

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = str(ids[0]).strip()
            url = f"{self.host}/video/{vid}/"
            html = (self._req(url).get("text") or "")

            title = self._re(r'<title>(.*?)</title>', html) or ""
            title = re.split(r'[|｜]', title)[0].replace("A片", "").strip() or self._re(r'"title"\s*:\s*"([^"]+)"', html) or f"视频{vid}"

            pic = self._fix_pic(self._re(r'"poster"\s*:\s*"([^"]+)"', html) or "")
            tags = self._re(r'"tag"\s*:\s*"([^"]+)"', html) or ""
            desc = self._re(r'"description"\s*:\s*"([^"]+)"', html) or title

            play = self._extract_play(html, vid)

            result["list"].append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "type_name": tags,
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": "",
                "vod_actor": tags.replace(",", " "),
                "vod_director": "",
                "vod_content": desc,
                "vod_play_from": "91Hub",
                "vod_play_url": f"正片${play}" if play else f"正片${url}",
            })
        except Exception as e:
            print(f"[detail] {e}")
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": []}
        try:
            html = (self._req(f"{self.host}/search/?q={quote(str(key))}").get("text") or "")
            result["list"] = self._parse_list(html)
        except Exception as e:
            print(f"[search] {e}")
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {
            "parse": 0,
            "url": "",
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": "https://91hubw.com/",
                "Origin": "https://91hubw.com",
            },
        }
        try:
            id = str(id).strip()
            # 已是直链
            if id.startswith("http") and (
                ".m3u8" in id or "/media/m3u8/" in id or ".mp4" in id
            ):
                result["url"] = id
                result["parse"] = 0
                return result

            # 详情页再解一次
            page = id if id.startswith("http") else f"{self.host}/video/{id}/"
            if "/video/" not in page and not id.startswith("http"):
                page = f"{self.host}/video/{id}/"
            res = self._req(page)
            html = res.get("text") or ""
            play = self._extract_play(html, id if not id.startswith("http") else None)
            if play and ("m3u8" in play or "mp4" in play or "/media/" in play):
                result["url"] = play
                result["parse"] = 0
                return result

            # 失败
            result["url"] = page
            result["parse"] = 1
        except Exception as e:
            print(f"[player] {e}")
            result["url"] = str(id)
            result["parse"] = 1
        return result


    def localProxy(self, param):
        """图片 AES 解密 + 透传"""
        try:
            url = param.get("url") or param.get("path") or param.get("u") or ""
            if not url:
                return [404, "text/plain", b""]
            url = unquote(str(url))
            if url.startswith("proxy://"):
                url = url[8:]
            if url.startswith("http://proxy/"):
                url = url[13:]
            if url.startswith("http%3A") or url.startswith("https%3A"):
                url = unquote(url)
            import requests
            headers = {
                "User-Agent": self.headers["User-Agent"],
                "Referer": "https://91hubw.com/",
                "Accept": "image/webp,image/*,*/*",
            }
            r = requests.get(url, headers=headers, timeout=15, verify=False, allow_redirects=True)
            if r.status_code != 200 or not r.content:
                return [404, "text/plain", b""]
            data = bytes(r.content)
            ct = r.headers.get("Content-Type", "application/octet-stream")
            if data[:3] == b"\xff\xd8\xff":
                return [200, "image/jpeg", data]
            if data[:4] == b"\x89PNG":
                return [200, "image/png", data]
            if data[:3] == b"GIF":
                return [200, "image/gif", data]
            if len(data) >= 16:
                dec = self._aes_decrypt_image(data)
                if dec:
                    if dec[:3] == b"\xff\xd8\xff":
                        return [200, "image/jpeg", dec]
                    if dec[:4] == b"\x89PNG":
                        return [200, "image/png", dec]
                    if dec[:3] == b"GIF":
                        return [200, "image/gif", dec]
            return [200, ct, data]
        except Exception as e:
            print(f"[proxy] {e}")
            return [404, "text/plain", b""]

    def _aes_decrypt_image(self, data):
        key = b"f5d965df75336270"
        iv = b"97b60394abc2fbe1"
        n = len(data) - (len(data) % 16)
        if n <= 0:
            return None
        data = data[:n]
        try:
            from Crypto.Cipher import AES
            return AES.new(key, AES.MODE_CBC, iv).decrypt(data)
        except Exception:
            pass
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
            return d.update(data) + d.finalize()
        except Exception:
            pass
        try:
            return self._aes_cbc_pure(data, key, iv)
        except Exception as e:
            print(f"[aes] {e}")
            return None

    def _aes_cbc_pure(self, data, key, iv):
        Sbox = (
            0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
            0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
            0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
            0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
            0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
            0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
            0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
            0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
            0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
            0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
            0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
            0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
            0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
            0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
            0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
            0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
        )
        InvSbox = [0] * 256
        for i, v in enumerate(Sbox):
            InvSbox[v] = i
        Rcon = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)

        def xtime(a):
            return (((a << 1) ^ 0x1B) & 0xFF) if (a & 0x80) else ((a << 1) & 0xFF)

        def mul(a, b):
            p = 0
            for _ in range(8):
                if b & 1:
                    p ^= a
                a = xtime(a)
                b >>= 1
            return p

        w = list(key)
        for i in range(4, 44):
            t = w[(i - 1) * 4:(i - 1) * 4 + 4]
            if i % 4 == 0:
                t = [Sbox[t[1]] ^ Rcon[i // 4], Sbox[t[2]], Sbox[t[3]], Sbox[t[0]]]
            for j in range(4):
                w.append(w[(i - 4) * 4 + j] ^ t[j])

        def inv_shift_rows(s):
            return [s[0], s[13], s[10], s[7], s[4], s[1], s[14], s[11], s[8], s[5], s[2], s[15], s[12], s[9], s[6], s[3]]

        def inv_mix_columns(s):
            out = [0] * 16
            for c in range(4):
                a, b, c_, d = s[4 * c], s[4 * c + 1], s[4 * c + 2], s[4 * c + 3]
                out[4 * c] = mul(a, 14) ^ mul(b, 11) ^ mul(c_, 13) ^ mul(d, 9)
                out[4 * c + 1] = mul(a, 9) ^ mul(b, 14) ^ mul(c_, 11) ^ mul(d, 13)
                out[4 * c + 2] = mul(a, 13) ^ mul(b, 9) ^ mul(c_, 14) ^ mul(d, 11)
                out[4 * c + 3] = mul(a, 11) ^ mul(b, 13) ^ mul(c_, 9) ^ mul(d, 14)
            return out

        def decrypt_block(block):
            s = list(block)
            s = [s[i] ^ w[160 + i] for i in range(16)]
            for rnd in range(9, 0, -1):
                s = inv_shift_rows(s)
                s = [InvSbox[b] for b in s]
                s = [s[i] ^ w[rnd * 16 + i] for i in range(16)]
                s = inv_mix_columns(s)
            s = inv_shift_rows(s)
            s = [InvSbox[b] for b in s]
            s = [s[i] ^ w[i] for i in range(16)]
            return bytes(s)

        out = bytearray()
        prev = iv
        for i in range(0, len(data), 16):
            block = data[i:i + 16]
            dec = decrypt_block(block)
            out.extend(bytes(dec[j] ^ prev[j] for j in range(16)))
            prev = block
        return bytes(out)

    def _parse_list(self, html):
        videos = []
        seen = set()

        # 方法1：按 video-item 卡片解析（最准确）
        for m in re.finditer(
            r'data-gsce231-video-id="(\d+)"[\s\S]*?'
            r'<img[^>]+data-src="([^"]+)"[^>]*alt="([^"]*)"',
            html
        ):
            vid, pic, title = m.group(1), m.group(2), m.group(3).strip()
            if vid in seen:
                continue
            seen.add(vid)
            pic = self._fix_pic(pic)
            videos.append({"vod_id": vid, "vod_name": title, "vod_pic": pic, "vod_remarks": ""})

        # 方法2：用 line-clamp 标题 + 附近的 data-src 图片
        if len(videos) < 4:
            videos = []
            seen = set()
            for m in re.finditer(
                r'<a[^>]*class="[^"]*line-clamp[^"]*"[^>]*href="/video/(\d+)/"[^>]*>\s*([^<]{4,120})\s*</a>',
                html, re.I | re.S
            ):
                vid, title = m.group(1), m.group(2).strip()
                if vid in seen:
                    continue
                seen.add(vid)
                search_start = max(0, m.start() - 2000)
                chunk = html[search_start:m.start()]
                pm = None
                for pm_match in re.finditer(r'data-src="([^"]+)"', chunk):
                    pm = pm_match
                pic = self._fix_pic(pm.group(1)) if pm else ""
                videos.append({"vod_id": vid, "vod_name": title, "vod_pic": pic, "vod_remarks": ""})

        # 方法3：宽松匹配
        if len(videos) < 4:
            videos = []
            seen = set()
            for m in re.finditer(r'/video/(\d+)/', html):
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                chunk = html[max(0, m.start()-2000):m.end()+500]
                tm = re.search(r'>([^<]{5,90})</a>', chunk)
                title = tm.group(1).strip() if tm else f"视频{vid}"
                pm = re.search(r'data-src="([^"]+)"', chunk)
                if not pm:
                    pm = re.search(r'src="(https?://[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)"', chunk, re.I)
                pic = self._fix_pic(pm.group(1)) if pm else ""
                videos.append({"vod_id": vid, "vod_name": title, "vod_pic": pic, "vod_remarks": ""})

        return videos

    def _fix_pic(self, pic):
        """封面 AES：getProxyUrl?url= / proxy://"""
        if not pic:
            return ""
        pic = pic.replace("\\/", "/").replace("&amp;", "&").strip()
        if pic.startswith("//"):
            pic = "https:" + pic
        if not pic.startswith("http"):
            return pic
        if "poster_loading" in pic or "/static/web/images/" in pic:
            return ""
        try:
            if hasattr(self, "getProxyUrl"):
                pu = self.getProxyUrl()
                if pu:
                    if "url=" in pu:
                        return pu + quote(pic)
                    sep = "&" if ("?" in pu) else "?"
                    return pu + sep + "url=" + quote(pic)
        except Exception as e:
            print(f"[fix_pic proxy] {e}")
        return "proxy://" + pic

    def _extract_play(self, html, vid=None):
        if not html:
            return ""
        # 1) 明文
        m = re.search(r'["\'](/media/m3u8/\?url=[^"\']+)["\']', html)
        if m:
            url = m.group(1).replace("\\u0026", "&").replace("\\/", "/")
            if url.startswith("/"):
                url = self.host + url
            return url
        m = re.search(r'(https?://91hubw\.com/media/m3u8/\?[^\s"\'\\]+)', html)
        if m:
            return m.group(1).replace("\\u0026", "&").replace("\\/", "/")

        # 2) Dean Edwards packer 解包
        decoded = self._decode_packer(html)
        if decoded:
            m = re.search(r'(/media/m3u8/\?url=[^"\'\s]+)', decoded)
            if m:
                url = m.group(1).replace("\\u0026", "&").replace("\\/", "/")
                url = re.sub(r'[}\\\'].*$', '', url)
                if url.startswith("/"):
                    url = self.host + url
                return url
            m = re.search(r'(https?://[^\s"\'\\]+\.m3u8[^\s"\'\\]*)', decoded)
            if m:
                real = m.group(1).replace("\\u0026", "&").replace("\\/", "/")
                return f"{self.host}/media/m3u8/?url={quote(real)}"

        # 3) 直接找 m3u8
        m = re.search(r'(https?://[^\s"\'\\]+\.m3u8[^\s"\'\\]*)', html)
        if m:
            real = m.group(1).replace("\\u0026", "&").replace("\\/", "/")
            return f"{self.host}/media/m3u8/?url={quote(real)}"

        if vid and not str(vid).startswith("http"):
            return f"{self.host}/video/{vid}/"
        return ""

    def _decode_packer(self, html):
        """解 eval(function(p,a,c,k,e,d) 的 packer"""
        try:
            m = re.search(
                r"return p\}\('([\s\S]*?)',(\d+),(\d+),'([\s\S]*?)'\.split\('\|'\)",
                html,
            )
            if not m:
                return None
            p, a, c, k = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split("|")
            return self._packer_unpack(p, a, c, k)
        except Exception as e:
            print(f"[packer] {e}")
            return None

    def _packer_unpack(self, p, a, c, k):
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

        def base(val):
            return ("" if val < a else base(val // a)) + (
                chr(val % a + 29) if val % a > 35 else alphabet[val % a]
            )

        d = {}
        while c:
            c -= 1
            key = base(c)
            d[key] = k[c] if c < len(k) and k[c] else key
        for key in sorted(d.keys(), key=len, reverse=True):
            p = re.sub(r"\b" + re.escape(key) + r"\b", d[key], p)
        return p


    def _re(self, pat, text, flags=0):
        m = re.search(pat, text, flags)
        return m.group(1) if m else ""


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print("分类数:", len(sp.cateManual))