# -*- coding: utf-8 -*-
"""
8day.icu TVBox Spider
站点：苹果CMS改版 + Alpine.js 播放器
播放地址：详情页 x-data="player([...])" 或底部注释 <!--地址xxx.m3u8地址-->
"""
import re
import json
import requests
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup


class Spider(object):
    def __init__(self):
        self.host = "https://8day.icu"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        # 六区完整分类
        self.classes = [
            {"type_name": "一区·欧美极品", "type_id": "/vod/show/class/欧美极品/id/1/"},
            {"type_name": "一区·日韩无码", "type_id": "/vod/show/class/日韩无码/id/1/"},
            {"type_name": "一区·AV明星",  "type_id": "/vod/show/class/AV明星/id/1/"},
            {"type_name": "一区·中文字幕", "type_id": "/vod/show/class/中文字幕/id/1/"},
            {"type_name": "一区·童颜巨乳", "type_id": "/vod/show/class/童颜巨乳/id/1/"},
            {"type_name": "一区·动漫精品", "type_id": "/vod/show/class/动漫精品/id/1/"},

            {"type_name": "二区·国产大制作", "type_id": "/vod/show/class/国产大制作/id/2/"},
            {"type_name": "二区·中文字幕",   "type_id": "/vod/show/class/中文字幕/id/2/"},
            {"type_name": "二区·高清无码",   "type_id": "/vod/show/class/高清无码/id/2/"},
            {"type_name": "二区·高清有码",   "type_id": "/vod/show/class/高清有码/id/2/"},
            {"type_name": "二区·无码流出",   "type_id": "/vod/show/class/无码流出/id/2/"},

            {"type_name": "三区·中文字幕", "type_id": "/vod/show/class/中文字幕/id/3/"},
            {"type_name": "三区·日本有码", "type_id": "/vod/show/class/日本有码/id/3/"},
            {"type_name": "三区·日本无码", "type_id": "/vod/show/class/日本无码/id/3/"},
            {"type_name": "三区·激情动漫", "type_id": "/vod/show/class/激情动漫/id/3/"},
            {"type_name": "三区·网红主播", "type_id": "/vod/show/class/网红主播/id/3/"},
            {"type_name": "三区·国产传媒", "type_id": "/vod/show/class/国产传媒/id/3/"},

            {"type_name": "四区·传媒出品", "type_id": "/vod/show/class/传媒出品/id/4/"},
            {"type_name": "四区·主播直播", "type_id": "/vod/show/class/主播直播/id/4/"},
            {"type_name": "四区·亚洲无码", "type_id": "/vod/show/class/亚洲无码/id/4/"},
            {"type_name": "四区·亚洲有码", "type_id": "/vod/show/class/亚洲有码/id/4/"},
            {"type_name": "四区·中文字幕", "type_id": "/vod/show/class/中文字幕/id/4/"},
            {"type_name": "四区·巨乳美乳", "type_id": "/vod/show/class/巨乳美乳/id/4/"},
            {"type_name": "四区·人妻熟女", "type_id": "/vod/show/class/人妻熟女/id/4/"},
            {"type_name": "四区·女同性恋", "type_id": "/vod/show/class/女同性恋/id/4/"},
            {"type_name": "四区·女优系列", "type_id": "/vod/show/class/女优系列/id/4/"},
            {"type_name": "四区·欧美精品", "type_id": "/vod/show/class/欧美精品/id/4/"},
            {"type_name": "四区·伦理三级", "type_id": "/vod/show/class/伦理三级/id/4/"},
            {"type_name": "四区·成人动漫", "type_id": "/vod/show/class/成人动漫/id/4/"},

            {"type_name": "五区·日本无码", "type_id": "/vod/show/class/日本无码/id/5/"},
            {"type_name": "五区·AV明星",  "type_id": "/vod/show/class/AV明星/id/5/"},
            {"type_name": "五区·中文字幕", "type_id": "/vod/show/class/中文字幕/id/5/"},
            {"type_name": "五区·网红主播", "type_id": "/vod/show/class/网红主播/id/5/"},
            {"type_name": "五区·成人动漫", "type_id": "/vod/show/class/成人动漫/id/5/"},
            {"type_name": "五区·欧美情色", "type_id": "/vod/show/class/欧美情色/id/5/"},

            {"type_name": "六区·国产精品", "type_id": "/vod/show/class/国产精品/id/6/"},
            {"type_name": "六区·国产传媒", "type_id": "/vod/show/class/国产传媒/id/6/"},
            {"type_name": "六区·精品探花", "type_id": "/vod/show/class/精品探花/id/6/"},
            {"type_name": "六区·中文字幕", "type_id": "/vod/show/class/中文字幕/id/6/"},
            {"type_name": "六区·日韩精品", "type_id": "/vod/show/class/日韩精品/id/6/"},
            {"type_name": "六区·日韩无码", "type_id": "/vod/show/class/日韩无码/id/6/"},
            {"type_name": "六区·人妻系列", "type_id": "/vod/show/class/人妻系列/id/6/"},
            {"type_name": "六区·制服诱惑", "type_id": "/vod/show/class/制服诱惑/id/6/"},
            {"type_name": "六区·AV明星",  "type_id": "/vod/show/class/AV明星/id/6/"},
            {"type_name": "六区·欧美精品", "type_id": "/vod/show/class/欧美精品/id/6/"},
            {"type_name": "六区·动漫精品", "type_id": "/vod/show/class/动漫精品/id/6/"},
        ]

    # ---------------- 首页分类 ----------------
    def homeContent(self, filter):
        return {"class": self.classes}

    # ---------------- 分类页列表 ----------------
    def categoryContent(self, tid, pg, filter, extend):
        try:
            base = tid.rstrip("/")
            if int(pg) > 1:
                url = f"{self.host}{base}/page/{pg}/"
            else:
                url = f"{self.host}{base}/"

            r = requests.get(url, headers=self.headers, timeout=10)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            videos = []
            for card in soup.select("div.card"):
                a_cover = card.select_one("a.card__cover")
                if not a_cover:
                    continue
                href = a_cover.get("href", "")
                vod_id = urljoin(self.host, href)

                img = card.select_one("img.card__img")
                pic = ""
                if img:
                    pic = img.get("src") or img.get("data-preview") or ""
                    if pic and not pic.startswith("http"):
                        pic = urljoin(self.host, pic)

                title_el = card.select_one("h3.card__title a.card__link")
                title = title_el.get_text(strip=True) if title_el else ""

                meta = card.select_one("div.card__meta")
                remarks = ""
                if meta:
                    spans = meta.find_all("span")
                    if spans:
                        remarks = spans[0].get_text(strip=True)

                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })

            pagecount = 1
            last = soup.select_one("div.pager a[rel='last']")
            if last:
                m = re.search(r"/page/(\d+)/", last.get("href", ""))
                if m:
                    pagecount = int(m.group(1))

            return {
                "list": videos,
                "page": int(pg),
                "pagecount": pagecount,
                "limit": 20,
                "total": pagecount * 20,
            }
        except Exception:
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 20, "total": 0}

    # ---------------- 详情页 ----------------
    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            url = vod_id if vod_id.startswith("http") else urljoin(self.host, vod_id)
            r = requests.get(url, headers=self.headers, timeout=10)
            r.encoding = "utf-8"
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # 标题
            title = ""
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

            # 封面（og:image 最稳）
            pic = ""
            og = soup.find("meta", property="og:image")
            if og:
                pic = og.get("content", "")

            # 简介
            desc = ""
            ogd = soup.find("meta", property="og:description")
            if ogd:
                desc = ogd.get("content", "")

            # 方式1：x-data="player([...])"
            play_url = ""
            m = re.search(r'x-data="player\((\[.*?\])\s*,', html, re.S)
            if m:
                raw = m.group(1).replace("'", '"')
                try:
                    arr = json.loads(raw)
                    if arr and isinstance(arr, list):
                        play_url = arr[0].get("url", "")
                except Exception:
                    m2 = re.search(r'play2\.html\?url=([^&\s"\']+)', html)
                    if m2:
                        play_url = m2.group(1)

            # 方式2：底部注释 <!--地址xxx.m3u8地址-->
            if not play_url:
                m3 = re.search(r'<!--地址(https?://[^\s<>"\']+?\.m3u8)地址-->', html)
                if m3:
                    play_url = m3.group(1)

            # 方式3：直接搜 m3u8
            if not play_url:
                m4 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
                if m4:
                    play_url = m4.group(1)

            # 去掉 play2.html 壳
            if "play2.html" in play_url:
                m5 = re.search(r'url=([^&\s]+)', play_url)
                if m5:
                    play_url = m5.group(1)

            play_url = unquote(play_url)

            vod = {
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": desc,
                "vod_play_from": "8day",
                "vod_play_url": f"正片${play_url}" if play_url else "",
            }
            return {"list": [vod]}
        except Exception:
            return {"list": []}

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick):
        try:
            url = f"{self.host}/vod/search/wd/{key}/"
            r = requests.get(url, headers=self.headers, timeout=10)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            videos = []
            for card in soup.select("div.card"):
                a_cover = card.select_one("a.card__cover")
                if not a_cover:
                    continue
                href = a_cover.get("href", "")
                vod_id = urljoin(self.host, href)

                img = card.select_one("img.card__img")
                pic = ""
                if img:
                    pic = img.get("src") or img.get("data-preview") or ""
                    if pic and not pic.startswith("http"):
                        pic = urljoin(self.host, pic)

                title_el = card.select_one("h3.card__title a.card__link")
                title = title_el.get_text(strip=True) if title_el else ""

                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })

            return {"list": videos}
        except Exception:
            return {"list": []}

    # ---------------- 播放 ----------------
    def playerContent(self, flag, id, vipFlags):
        try:
            url = id.split("$")[-1] if "$" in id else id
            header = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://8day.icu/",
                "Origin": "https://8day.icu",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "keep-alive",
            }
            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": header,
            }
        except Exception:
            return {"parse": 0, "url": id, "header": self.headers}