#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遮天·轮海彼岸境 — 色爱阁专用（语法修复版v5）
目标站点: https://www.seaige9.fit
"""

import sys
import re
import json
import time
import base64
import requests
from urllib import parse

sys.path.append("..")
from base.spider import Spider


class YuanTianShu:
    """源天书 — 基础HTTP架构"""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    session = requests.Session()

    @classmethod
    def fetch(cls, url, headers=None, timeout=15):
        h = {**cls.headers, **(headers or {})}
        try:
            resp = cls.session.get(url, headers=h, timeout=timeout, verify=False)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[源天书] 抓取失败: {e}")
            return ""

    @staticmethod
    def homeContent():
        raise NotImplementedError

    @staticmethod
    def categoryContent(tid, pg, filter, extend):
        raise NotImplementedError

    @staticmethod
    def detailContent(ids):
        raise NotImplementedError

    @staticmethod
    def playerContent(flag, id, vipFlags):
        raise NotImplementedError

    @staticmethod
    def searchContent(key, quick, pg="1"):
        raise NotImplementedError


class SeAiGe_Spider(YuanTianShu):
    """色爱阁专用爬虫 — 语法修复版v5"""

    def __init__(self):
        self.siteUrl = "https://www.seaige9.fit"
        self.publish_url = "https://dfs.seaige1.com/a/"

        # 分类配置
        self.categories = [
            {"type_id": "20", "type_name": "亚洲情色"},
            {"type_id": "21", "type_name": "制服师生"},
            {"type_id": "22", "type_name": "卡通动漫"},
            {"type_id": "23", "type_name": "三级伦理"},
            {"type_id": "24", "type_name": "强奸乱伦"},
            {"type_id": "25", "type_name": "偷拍自拍"},
            {"type_id": "26", "type_name": "中文字幕"},
            {"type_id": "27", "type_name": "欧美性爱"},
            {"type_id": "28", "type_name": "人妻熟女"},
            {"type_id": "29", "type_name": "无码专区"},
        ]

        # 正则模式库 - 使用单引号包裹，内部双引号无需转义
        self.patterns = {
            "video_card": re.compile(
                '<div class="video-card">(.*?)</div>\s*</div>\s*</div>',
                re.DOTALL
            ),
            "play_link": re.compile(
                'href="(/cn/home/web/index\.php/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"'
            ),
            "img": re.compile(
                '<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"'
            ),
            "title": re.compile(
                '<div class="video-title">(.*?)</div>',
                re.DOTALL
            ),
            "player_data": re.compile(
                'var\s+player_data\s*=\s*(\{[^}]+\})',
                re.DOTALL
            ),
            # 使用字符类避免引号问题
            "m3u8_direct": re.compile(
                'https?://[^\x22\x27<>\s]+\.m3u8[^\x22\x27<>\s]*'
            ),
        }

    def _full_url(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        if path.startswith("//"):
            return "https:" + path
        return parse.urljoin(self.siteUrl, path)

    def _clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_videos_from_cards(self, html):
        videos = []
        debug_info = {
            "html_length": len(html),
            "cards_found": 0,
            "videos_extracted": 0,
            "errors": []
        }

        if not html:
            debug_info["errors"].append("HTML为空")
            return videos, debug_info

        cards = self.patterns["video_card"].findall(html)
        debug_info["cards_found"] = len(cards)

        for card in cards:
            try:
                play_match = self.patterns["play_link"].search(card)
                if not play_match:
                    continue

                play_url, vid, sid, nid = play_match.groups()

                img_match = self.patterns["img"].search(card)
                img_url = img_match.group(1) if img_match else ""

                title_match = self.patterns["title"].search(card)
                if title_match:
                    title = self._clean_text(title_match.group(1))
                else:
                    title = img_match.group(2) if img_match else f"视频{vid}"

                videos.append({
                    "vod_id": f"play_{vid}_{sid}_{nid}",
                    "vod_name": title,
                    "vod_pic": img_url,
                    "vod_remarks": "",
                })

            except Exception as e:
                debug_info["errors"].append(f"卡片解析错误: {e}")

        debug_info["videos_extracted"] = len(videos)
        return videos, debug_info

    def _extract_player_data(self, html):
        debug_info = {"errors": []}

        if not html:
            debug_info["errors"].append("HTML为空")
            return "", "", debug_info

        player_match = self.patterns["player_data"].search(html)
        if player_match:
            try:
                player_json = player_match.group(1)
                player_json = player_json.replace("\/", "/")
                player_data = json.loads(player_json)

                m3u8_url = player_data.get("url", "")
                title = player_data.get("title", "")
                encrypt = player_data.get("encrypt", 0)

                debug_info["player_data"] = player_data
                debug_info["encrypt"] = encrypt

                if encrypt == 0 and m3u8_url:
                    return m3u8_url, title, debug_info

            except json.JSONDecodeError as e:
                debug_info["errors"].append(f"JSON解析失败: {e}")
            except Exception as e:
                debug_info["errors"].append(f"player_data解析错误: {e}")

        m3u8_match = self.patterns["m3u8_direct"].search(html)
        if m3u8_match:
            return m3u8_match.group(0), "", debug_info

        debug_info["errors"].append("未找到player_data或m3u8")
        return "", "", debug_info

    def homeContent(self, filter):
        print(f"[首页] 站点: {self.siteUrl}")
        return {"class": self.categories}

    def categoryContent(self, tid, pg, filter, extend):
        if int(pg) == 1:
            url = f"{self.siteUrl}/cn/home/web/index.php/vod/type/id/{tid}.html"
        else:
            url = f"{self.siteUrl}/cn/home/web/index.php/vod/type/id/{tid}/page/{pg}.html"

        print(f"[分类] tid={tid}, pg={pg}")

        html = self.fetch(url)
        videos, debug = self._extract_videos_from_cards(html)

        print(f"[分类] 找到{debug['cards_found']}个卡片，提取{debug['videos_extracted']}个视频")

        has_next = f"/page/{int(pg)+1}.html" in html if html else False

        return {
            "list": videos,
            "page": int(pg),
            "pagecount": 999 if has_next or len(videos) >= 10 else int(pg),
            "limit": len(videos),
            "total": 9999
        }

    def detailContent(self, ids):
        vod_id = ids[0]
        print(f"[详情] vod_id: {vod_id}")

        if vod_id.startswith("play_"):
            parts = vod_id.split("_")
            if len(parts) >= 4:
                vid, sid, nid = parts[1], parts[2], parts[3]
            else:
                return {"list": []}
        else:
            return {"list": []}

        play_url = f"{self.siteUrl}/cn/home/web/index.php/vod/play/id/{vid}/sid/{sid}/nid/{nid}.html"
        print(f"[详情] 播放页: {play_url}")

        html = self.fetch(play_url)
        m3u8_url, title, debug = self._extract_player_data(html)

        print(f"[详情] m3u8: {m3u8_url[:80] if m3u8_url else '未找到'}...")

        if not title:
            title = f"视频{vid}"

        pic = ""
        img_match = re.search('<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if not img_match:
            img_match = re.search('<img[^>]+class="[^"]*(?:cover|pic|thumb)[^"]*"[^>]+src="([^"]+)"', html)
        if img_match:
            pic = self._full_url(img_match.group(1))

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_play_from": "直链",
                "vod_play_url": f"第1集${m3u8_url}"
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        if ".m3u8" in id:
            return {
                "parse": 0,
                "url": id,
                "header": json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.siteUrl
                })
            }
        return {"parse": 0, "url": id, "header": ""}

    def searchContent(self, key, quick, pg="1"):
        keyword = parse.quote(key)
        search_urls = [
            f"{self.siteUrl}/cn/home/web/index.php/vod/search/wd/{keyword}.html",
            f"{self.siteUrl}/cn/home/web/index.php/vod/search.html?wd={keyword}",
        ]

        videos = []
        for url in search_urls:
            print(f"[搜索] 尝试: {url}")
            html = self.fetch(url)
            if html:
                videos, debug = self._extract_videos_from_cards(html)
                if videos:
                    break

        return {
            "list": videos,
            "page": int(pg),
            "pagecount": 999,
            "limit": len(videos),
            "total": 9999
        }


class Spider(SeAiGe_Spider):
    """TVBox 标准入口"""

    def init(self, extend=""):
        print("[红尘仙] 色爱阁专用爬虫（语法修复版v5）已激活")
        return True

    def isVideoFormat(self, url):
        return ".m3u8" in url.lower() or ".ts" in url.lower()

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "application/json", json.dumps({"code": 0, "msg": "运行中"})]
