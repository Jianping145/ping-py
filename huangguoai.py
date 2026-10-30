# -*- coding: utf-8 -*-
# huangguoai.com 黄果短剧  蜂蜜影视(FongMi) / TVBox Python Spider
# 列表 /ai-duanju/N/  · 详情 /api/videos/{id}  · 播放 /api/videos/{id}/play?ep=N
# 封面 pic.drleao.cn AES-CBC 加密，经 localProxy 解密

import sys
import re
import json
import time
from urllib import parse
from bs4 import BeautifulSoup

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def __init__(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "黄果短剧"
        self.host = "https://huangguoai.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.classes = [
            {"type_id": "ai-duanju", "type_name": "AI短剧"},
            {"type_id": "ai-manju", "type_name": "AI漫剧"},
            {"type_id": "ai-huanlian", "type_name": "换脸"},
            {"type_id": "ai-mogai", "type_name": "魔改"},
            {"type_id": "ranks/hot", "type_name": "热门排行"},
            {"type_id": "chigua", "type_name": "吃瓜"},
            {"type_id": "tag/dushi", "type_name": "都市"},
            {"type_id": "tag/gufeng", "type_name": "古风"},
            {"type_id": "tag/qihuan", "type_name": "奇幻"},
            {"type_id": "tag/xiandai", "type_name": "现代"},
            {"type_id": "tag/nixi", "type_name": "逆袭"},
            {"type_id": "tag/xiaoyuan", "type_name": "校园"},
            {"type_id": "tag/xitong", "type_name": "系统"},
            {"type_id": "tag/xianxia", "type_name": "仙侠"},
            {"type_id": "tag/zhichang", "type_name": "职场"},
        ]
        self._img_key = b"f5d965df75336270"
        self._img_iv = b"97b60394abc2fbe1"

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv", ".mkv", ".ts"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        try:
            html = self.fetch(self.host + "/topics/")
            if html:
                tags = self._parse_tags(html)
                if tags:
                    known = {c["type_id"] for c in self.classes}
                    self.classes = self.classes + [t for t in tags if t["type_id"] not in known][:40]
        except Exception:
            pass
        return {"class": self.classes, "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            path = tid.strip("/")
            # 标签/吃瓜/排行：/tag/xxx/page/2/ ；主分类：/ai-duanju/2/
            use_page_seg = path.startswith("tag/") or path in ("chigua", "ranks/hot", "topics")
            if pg == "1":
                url = f"{self.host}/{path}/"
            elif use_page_seg:
                url = f"{self.host}/{path}/page/{pg}/"
            else:
                url = f"{self.host}/{path}/{pg}/"
            html = self.fetch(url)
            # 404 或空时尝试另一种分页格式
            if not html or "video/" not in html:
                alt = f"{self.host}/{path}/page/{pg}/" if not use_page_seg else f"{self.host}/{path}/{pg}/"
                html2 = self.fetch(alt)
                if html2 and "video/" in html2:
                    html = html2
            videos = self._parse_list(html)
            # 排行可能无分页：空列表时 pagecount=当前页
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999 if videos else int(pg),
                "limit": 24,
                "total": 999999 if videos else 0,
            }
        except Exception as e:
            print(f"[huangguoai] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        vid = re.search(r"(\d+)", raw)
        vid = vid.group(1) if vid else raw
        try:
            data = self._api_json(f"/api/videos/{vid}")
            if not data:
                return {"list": []}
            title = data.get("title") or data.get("page_h1") or f"视频{vid}"
            # title 可能在外层
            if not data.get("title") and data.get("name"):
                title = data["name"]
            # API 结构 data 内
            pic = data.get("cover") or ""
            desc = data.get("description") or ""
            remarks = ""
            ep_count = data.get("episode_count") or 0
            if ep_count:
                remarks = f"{ep_count}集"
            if data.get("is_finished"):
                remarks = (remarks + " 完结").strip()

            episodes = data.get("episodes") or []
            play_parts = []
            if episodes:
                for ep in episodes:
                    num = ep.get("ep_num") or ep.get("num") or 0
                    name = ep.get("title") or f"第{num}集"
                    # 过长截断
                    if len(name) > 30:
                        name = f"第{num}集"
                    play_parts.append(f"{name}${vid}|{num}")
            else:
                play_parts.append(f"正片${vid}|1")

            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": desc,
                    "vod_remarks": remarks,
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": (data.get("author") or {}).get("name") or "",
                    "vod_director": "",
                    "type_name": ",".join(data.get("tags") or []),
                    "vod_play_from": "黄果短剧",
                    "vod_play_url": "#".join(play_parts),
                }]
            }
        except Exception as e:
            print(f"[huangguoai] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        if self.isVideoFormat(id):
            return {
                "parse": 0,
                "url": id,
                "header": json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.host + "/",
                }),
            }
        try:
            vid, ep = id, "1"
            if "|" in id:
                vid, ep = id.split("|", 1)
            data = self._api_json(f"/api/videos/{vid}/play?ep={ep}")
            url = ""
            if data:
                url = data.get("video_url") or data.get("video_url_hevc") or ""
            if url:
                return {
                    "parse": 0,
                    "url": url,
                    "header": json.dumps({
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host + "/",
                    }),
                }
        except Exception as e:
            print(f"[huangguoai] play error: {e}")
        return {
            "parse": 1,
            "url": id,
            "header": json.dumps({
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
            }),
        }

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        try:
            q = parse.quote(key)
            if pg == "1":
                url = f"{self.host}/search/?q={q}"
            else:
                url = f"{self.host}/search/{pg}/?q={q}"
            html = self.fetch(url)
            return {"list": self._parse_list(html)}
        except Exception as e:
            print(f"[huangguoai] search error: {e}")
            return {"list": []}

    def localProxy(self, param):
        try:
            import requests
            from urllib import parse as up
            if isinstance(param, dict):
                url = param.get("url") or param.get("target") or ""
            else:
                url = str(param or "")
            if not url:
                return [400, "text/plain", b"no url"]
            for _ in range(2):
                if "%" in url and ("http%" in url.lower() or url.lower().startswith("%")):
                    url = up.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b"bad url"]
            resp = requests.get(url, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
                "Accept": "*/*",
            }, timeout=15, verify=False)
            if resp.status_code != 200 or not resp.content:
                return [resp.status_code, "text/plain", (resp.content or b"")[:200]]
            data = resp.content
            if data[:3] == b"\xff\xd8\xff":
                return [200, "image/jpeg", data]
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                return [200, "image/png", data]
            if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                return [200, "image/webp", data]
            pt = self._aes_cbc_decrypt(data, self._img_key, self._img_iv)
            if pt[:3] == b"\xff\xd8\xff":
                return [200, "image/jpeg", pt]
            if pt[:8] == b"\x89PNG\r\n\x1a\n":
                return [200, "image/png", pt]
            if pt[:4] == b"RIFF" and pt[8:12] == b"WEBP":
                return [200, "image/webp", pt]
            return [500, "text/plain", b"decrypt failed"]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    def _proxy_pic(self, pic):
        if not pic or not pic.startswith("http"):
            return pic or ""
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base:
                    return f"{base}&url={parse.quote(pic)}"
        except Exception:
            pass
        return pic

    def _api_json(self, path):
        import requests
        url = path if path.startswith("http") else self.host + path
        try:
            resp = requests.get(url, headers={
                **self.headers,
                "Accept": "application/json",
            }, timeout=15, verify=False)
            if resp.status_code != 200:
                return {}
            j = resp.json()
            return j.get("data") or j
        except Exception as e:
            print(f"[huangguoai] api error: {e}")
            return {}

    def fetch(self, url, retry=2):
        import requests
        last_err = None
        for _ in range(retry):
            try:
                resp = requests.get(url, headers=self.headers, timeout=15, verify=False)
                resp.encoding = "utf-8"
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.text
            except Exception as e:
                last_err = e
                time.sleep(0.3)
        print(f"[huangguoai] fetch fail: {last_err}")
        return ""

    def _parse_tags(self, html):
        tags = []
        for href, slug in re.findall(r'href="(/tag/([a-z0-9-]+)/)"', html):
            name = slug
            m = re.search(rf'href="{re.escape(href)}"[^>]*>([^<]+)<', html)
            if m:
                name = m.group(1).strip() or slug
            tid = f"tag/{slug}"
            if tid not in [t["type_id"] for t in tags]:
                tags.append({"type_id": tid, "type_name": name})
        return tags

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")
        seen = set()

        # 主列表卡片：每个卡片内封面与标题一一对应
        cards = soup.select(".hg-drama-card")
        for card in cards:
            a = card.select_one('a[href*="/video/"]')
            if not a:
                continue
            href = a.get("href") or ""
            m = re.search(r"/video/(\d+)/?", href)
            if not m or "/ep-" in href:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            title = ""
            t_el = card.select_one(".hg-drama-card__title")
            if t_el:
                title = t_el.get_text(" ", strip=True)
            if not title:
                title = a.get_text(" ", strip=True)
            title = re.sub(r"\s+", " ", title).strip()
            title = re.sub(r"全集在线观看\s*$", "", title).strip()
            title = re.sub(r"^《|》$", "", title).strip()
            if title.startswith("《") and title.endswith("》"):
                title = title[1:-1]
            if not title:
                title = f"视频{vid}"

            pic = ""
            img = card.select_one(".hg-drama-card__cover img, img")
            if img:
                pic = (img.get("data-src") or img.get("data-original") or img.get("src") or "").strip()
            if pic.startswith("data:"):
                pic = ""
            if pic.startswith("//"):
                pic = "https:" + pic

            remarks = ""
            ep_el = card.select_one(".hg-drama-card__episode, .hg-drama-card__badge")
            if ep_el:
                remarks = ep_el.get_text(strip=True)

            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": remarks,
            })

        if videos:
            return videos

        # 兜底：旧逻辑（无卡片结构时）
        entries = []
        for a in soup.select('a[href*="/video/"]'):
            href = a.get("href") or ""
            m = re.search(r"/video/(\d+)/?", href)
            if not m or "/ep-" in href:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            # 跳过搜索建议
            if a.find_parent(class_=re.compile(r"search-suggest")):
                continue
            seen.add(vid)
            title = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip() or f"视频{vid}"
            entries.append({"vid": vid, "title": title, "pic": ""})
        pics = []
        for img in soup.select("img"):
            src = (img.get("data-src") or img.get("data-original") or img.get("src") or "").strip()
            if not src or src.startswith("data:"):
                continue
            if "pic.drleao.cn" in src or "/upload_" in src:
                if src.startswith("//"):
                    src = "https:" + src
                pics.append(src)
        for i, e in enumerate(entries):
            if i < len(pics):
                e["pic"] = pics[i]
            videos.append({
                "vod_id": e["vid"],
                "vod_name": e["title"],
                "vod_pic": self._proxy_pic(e["pic"]),
                "vod_remarks": "",
            })
        return videos

    def _aes_cbc_decrypt(self, data, key, iv):
        aligned = data if len(data) % 16 == 0 else data[: len(data) - (len(data) % 16)]
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
            return decryptor.update(aligned) + decryptor.finalize()
        except Exception:
            pass
        try:
            from Crypto.Cipher import AES as _AES
            return _AES.new(key, _AES.MODE_CBC, iv).decrypt(aligned)
        except Exception:
            pass
        return self._aes_cbc_pure(aligned, key, iv)

    def _aes_cbc_pure(self, data, key, iv):
        sbox = [
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
        ]
        rcon = [0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36]
        inv_sbox = [0] * 256
        for i, v in enumerate(sbox):
            inv_sbox[v] = i

        def xor(a, b):
            return [x ^ y for x, y in zip(a, b)]

        def rot(w):
            return w[1:] + w[:1]

        def sub(w):
            return [sbox[b] for b in w]

        nk, nb, nr = 4, 4, 10
        key_bytes = list(key)
        w = [key_bytes[4 * i:4 * i + 4] for i in range(nk)]
        for i in range(nk, nb * (nr + 1)):
            t = w[i - 1][:]
            if i % nk == 0:
                t = xor(sub(rot(t)), [rcon[i // nk], 0, 0, 0])
            w.append(xor(w[i - nk], t))

        def add_round(state, rnd):
            return [state[i] ^ w[rnd * 4 + i // 4][i % 4] for i in range(16)]

        def inv_shift(s):
            return [s[0], s[13], s[10], s[7], s[4], s[1], s[14], s[11],
                    s[8], s[5], s[2], s[15], s[12], s[9], s[6], s[3]]

        def inv_sub(s):
            return [inv_sbox[b] for b in s]

        def xtime(a):
            return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1) & 0xff

        def mul(a, b):
            r = 0
            for _ in range(8):
                if b & 1:
                    r ^= a
                a = xtime(a)
                b >>= 1
            return r

        def inv_mix(s):
            out = [0] * 16
            for c in range(4):
                i = 4 * c
                a, b, c2, d = s[i:i + 4]
                out[i] = mul(a, 0x0e) ^ mul(b, 0x0b) ^ mul(c2, 0x0d) ^ mul(d, 0x09)
                out[i + 1] = mul(a, 0x09) ^ mul(b, 0x0e) ^ mul(c2, 0x0b) ^ mul(d, 0x0d)
                out[i + 2] = mul(a, 0x0d) ^ mul(b, 0x09) ^ mul(c2, 0x0e) ^ mul(d, 0x0b)
                out[i + 3] = mul(a, 0x0b) ^ mul(b, 0x0d) ^ mul(c2, 0x09) ^ mul(d, 0x0e)
            return out

        def dec_block(block):
            state = list(block)
            state = add_round(state, nr)
            state = inv_shift(state)
            state = inv_sub(state)
            for rnd in range(nr - 1, 0, -1):
                state = add_round(state, rnd)
                state = inv_mix(state)
                state = inv_shift(state)
                state = inv_sub(state)
            state = add_round(state, 0)
            return bytes(state)

        out = bytearray()
        prev = list(iv)
        for i in range(0, len(data), 16):
            block = list(data[i:i + 16])
            dec = dec_block(block)
            out.extend(x ^ y for x, y in zip(dec, prev))
            prev = block
        return bytes(out)


if __name__ == "__main__":
    sp = Spider()
    print("classes", len(sp.homeContent(False)["class"]))
    cat = sp.categoryContent("ai-duanju", "1", False, {})
    print("list", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(" ", v.get("vod_name", "")[:30], (v.get("vod_pic") or "")[:50])
    if cat.get("list"):
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        item = (d.get("list") or [{}])[0]
        print("detail", item.get("vod_name"), item.get("vod_remarks"))
        print("playurl", (item.get("vod_play_url") or "")[:100])
        first = (item.get("vod_play_url") or "").split("#")[0]
        if "$" in first:
            play = sp.playerContent("黄果短剧", first.split("$", 1)[1], [])
            print("m3u8", str(play.get("url", ""))[:100], "parse", play.get("parse"))
