# -*- coding: utf-8 -*-
# 小女16 / xnv16jep.click  蜂蜜影视(FongMi) / TVBox Python Spider
# 修复版：封面完整提取 + 真实 m3u8 直链播放
# 境界：轮海秘境 · 彼岸境

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
        self.name = "小女16"
        self.host = "https://xnv16jep.click"
        self.hosts = [
            "https://xnv16jep.click",
            "https://dxnv161001.buzz",
            "https://xnv16aa.xyz",
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.classes = [
            {"type_id": "高清无码", "type_name": "高清无码"},
            {"type_id": "每天更新", "type_name": "每天更新"},
            {"type_id": "国产主播", "type_name": "国产主播"},
            {"type_id": "日本动漫", "type_name": "日本动漫"},
            {"type_id": "国产视频", "type_name": "国产视频"},
            {"type_id": "女优明星", "type_name": "女优明星"},
            {"type_id": "网曝黑料", "type_name": "网曝黑料"},
            {"type_id": "黑料大瓜", "type_name": "黑料大瓜"},
            {"type_id": "福利一区", "type_name": "福利一区"},
            {"type_id": "自拍偷拍", "type_name": "自拍偷拍"},
            {"type_id": "糖心VLOG", "type_name": "糖心VLOG"},
            {"type_id": "中文高清", "type_name": "中文高清"},
            {"type_id": "白虎无码", "type_name": "白虎无码"},
            {"type_id": "热门泄密", "type_name": "热门泄密"},
            {"type_id": "AV解说", "type_name": "AV解说"},
            {"type_id": "国产9探花", "type_name": "国产9探花"},
            {"type_id": "中文字幕", "type_name": "中文字幕"},
            {"type_id": "制服诱惑", "type_name": "制服诱惑"},
            {"type_id": "少妇诱惑", "type_name": "少妇诱惑"},
            {"type_id": "sort_21", "type_name": "无码专区"},
            {"type_id": "sort_25", "type_name": "制服诱惑·热"},
            {"type_id": "sort_27", "type_name": "三级伦理"},
            {"type_id": "sort_29", "type_name": "AI换脸"},
            {"type_id": "sort_30", "type_name": "中文字幕·热"},
            {"type_id": "sort_32", "type_name": "卡通动漫"},
            {"type_id": "sort_35", "type_name": "欧美系列"},
            {"type_id": "sort_36", "type_name": "美女主播"},
            {"type_id": "sort_38", "type_name": "国产自拍"},
            {"type_id": "sort_40", "type_name": "熟女人妻"},
            {"type_id": "sort_42", "type_name": "萝莉少女"},
            {"type_id": "sort_50", "type_name": "抖阴视频"},
            {"type_id": "sort_53", "type_name": "网爆黑料"},
            {"type_id": "sort_54", "type_name": "欧美无码"},
            {"type_id": "sort_55", "type_name": "女优明星·热"},
            {"type_id": "sort_56", "type_name": "SM调教"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv", ".mkv", ".ts"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes, "filters": {}}

    def homeVideoContent(self):
        try:
            html = self.fetch(self.host)
            return {"list": self._parse_list(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        try:
            if tid.startswith("sort_"):
                cid = tid.replace("sort_", "")
                if pg == "1":
                    url = f"{self.host}/sort/id/{cid}.html"
                else:
                    url = f"{self.host}/sort/id/{cid}/page/{pg}.html"
            else:
                if pg == "1":
                    url = f"{self.host}/hunt/{parse.quote(tid)}.html"
                else:
                    url = f"{self.host}/hunt/{parse.quote(tid)}/page/{pg}.html"
            html = self.fetch(url)
            videos = self._parse_list(html)
            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999,
                "limit": 24,
                "total": 999999,
            }
        except Exception as e:
            print(f"[xnv16] category error: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else str(ids)
        m = re.search(r"(\d+)", vid)
        if m:
            vid = m.group(1)
        try:
            info_url = f"{self.host}/info/id/{vid}.html"
            html = self.fetch(info_url)
            soup = BeautifulSoup(html, "html.parser")

            title = ""
            t = soup.select_one("title")
            if t:
                title = re.sub(r"的详情信息.*$", "", t.get_text()).strip()
            if not title:
                title = vid

            pic = ""
            for img in soup.select("img.lazy, img"):
                src = img.get("src") or img.get("data-src") or img.get("data-original") or ""
                if src and any(x in src for x in [".jpg", ".jpeg", ".png", ".webp"]) and "static" not in src and "gif" not in src:
                    pic = self._full_url(src)
                    break

            play_url = self._get_play_url(vid)
            if not play_url:
                play_url = f"{self.host}/play/id/{vid}.html"

            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "小女16",
                    "vod_play_url": f"正片${play_url}",
                }]
            }
        except Exception as e:
            print(f"[xnv16] detail error: {e}")
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
        if "/play/id/" in id or (id and id.isdigit()):
            m = re.search(r"(\d+)", id)
            real = self._get_play_url(m.group(1) if m else id)
            if real:
                return {
                    "parse": 0,
                    "url": real,
                    "header": json.dumps({
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host + "/",
                    }),
                }
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
            if pg == "1":
                url = f"{self.host}/hunt/{parse.quote(key)}.html"
            else:
                url = f"{self.host}/hunt/{parse.quote(key)}/page/{pg}.html"
            html = self.fetch(url)
            return {"list": self._parse_list(html)}
        except Exception as e:
            print(f"[xnv16] search error: {e}")
            return {"list": []}

    def localProxy(self, param):
        return [200, "text/plain", ""]

    def _get_play_url(self, vid):
        """从 /play/id/xxx.html 提取 var playUrl = 'xxx.m3u8'"""
        try:
            play_page = f"{self.host}/play/id/{vid}.html"
            html = self.fetch(play_page)
            if not html:
                return ""
            m = re.search(r"var\s+playUrl\s*=\s*['\"]([^'\"]+)['\"]", html)
            if m:
                return m.group(1).strip()
            m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
            if m:
                return m.group(1).strip()
            m = re.search(r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']', html)
            if m:
                return m.group(1).strip()
        except Exception as e:
            print(f"[xnv16] get_play_url error: {e}")
        return ""

    def fetch(self, url, retry=2):
        import requests
        last_err = None
        for host in self.hosts:
            try:
                u = url
                for h in self.hosts:
                    if h in u:
                        u = u.replace(h, host)
                        break
                else:
                    if not u.startswith("http"):
                        u = host + (u if u.startswith("/") else "/" + u)
                for _ in range(retry):
                    try:
                        resp = requests.get(u, headers=self.headers, timeout=12, verify=False)
                        resp.encoding = "utf-8"
                        if resp.status_code == 200 and len(resp.text) > 300:
                            self.host = host
                            return resp.text
                    except Exception as e:
                        last_err = e
                        time.sleep(0.4)
            except Exception as e:
                last_err = e
        print(f"[xnv16] fetch fail: {last_err}")
        return ""

    def _full_url(self, path):
        if not path:
            return ""
        if path.startswith("//"):
            return "https:" + path
        if path.startswith("http"):
            return path
        return parse.urljoin(self.host, path)

    def _parse_list(self, html):
        if not html:
            return []
        videos = []
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.select('a[href*="/info/id/"]'):
            href = a.get("href", "")
            m = re.search(r"/info/id/(\d+)\.html", href)
            if not m:
                continue
            vod_id = m.group(1)
            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if not title or len(title) < 2:
                continue

            pic = ""
            img = a.select_one("img.lazy") or a.select_one("img")
            if img:
                pic = img.get("src") or img.get("data-src") or img.get("data-original") or ""
            if not pic:
                parent = a.parent
                if parent:
                    img = parent.select_one("img.lazy") or parent.select_one("img")
                    if img:
                        pic = img.get("src") or img.get("data-src") or img.get("data-original") or ""
            pic = self._full_url(pic)

            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })

        seen = {}
        for v in videos:
            vid = v["vod_id"]
            if vid not in seen or (v["vod_pic"] and not seen[vid]["vod_pic"]):
                seen[vid] = v
        return list(seen.values())


if __name__ == "__main__":
    sp = Spider()
    print("=== category 国产主播 ===")
    cat = sp.categoryContent("国产主播", "1", False, {})
    print("count:", len(cat.get("list", [])))
    for v in cat.get("list", [])[:3]:
        print(v)
    if cat.get("list"):
        print("\n=== detail ===")
        d = sp.detailContent([cat["list"][0]["vod_id"]])
        print(json.dumps(d, ensure_ascii=False, indent=2)[:800])
