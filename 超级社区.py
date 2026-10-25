# -*- coding: utf-8 -*-
# 站点：超级片社区  https://wnp.cjpsq5.motorcycles
# 适配：蜂蜜影视 / TVBox
# 境界：轮海大圆满 + 道宫轻量防御

import re
import json
from urllib import parse

try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider:
        def fetch(self, url, headers=None):
            import requests
            h = headers or {}
            r = requests.get(url, headers=h, timeout=15, verify=False)
            r.encoding = "utf-8"
            return r.text


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://wnp.cjpsq5.motorcycles"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/"
        }

    def getName(self):
        return "超级片社区"

    def isVideoFormat(self, url):
        return any(x in url.lower() for x in [".m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        """分类列表"""
        classes = [
            {"type_id": "20", "type_name": "国产精品"},
            {"type_id": "21", "type_name": "精品三级"},
            {"type_id": "22", "type_name": "主播大秀"},
            {"type_id": "23", "type_name": "抖阴视频"},
            {"type_id": "24", "type_name": "女神学生"},
            {"type_id": "25", "type_name": "美熟少妇"},
            {"type_id": "26", "type_name": "娇妻素人"},
            {"type_id": "27", "type_name": "空姐模特"},
            {"type_id": "28", "type_name": "国产乱伦"},
            {"type_id": "29", "type_name": "自慰群交"},
            {"type_id": "30", "type_name": "野合车震"},
            {"type_id": "31", "type_name": "职场同事"},
            {"type_id": "32", "type_name": "国产名人"},
        ]
        return {"class": classes}

    def homeVideoContent(self):
        """首页推荐"""
        return self.categoryContent("20", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        """分类列表"""
        try:
            if str(pg) == "1":
                url = f"{self.host}/vodtype/{tid}.html"
            else:
                url = f"{self.host}/vodtype/{tid}-{pg}.html"

            html = self.fetch(url)
            if not html:
                return {"list": [], "page": pg, "pagecount": 999, "limit": 40, "total": 99999}

            videos = []
            # 匹配 stui-vodlycms 结构 + data-original 懒加载图
            pattern = re.compile(
                r'<a[^>]+class="[^"]*stui-vodlycms_list__thumb[^"]*"[^>]+href="(/?\d+\.html)"[^>]+title="([^"]*)"[^>]+data-original="([^"]+)"',
                re.S
            )
            matches = pattern.findall(html)

            if not matches:
                # 备用：通用匹配
                pattern2 = re.compile(
                    r'<a[^>]+href="(/?\d{6,}\.html)"[^>]+title="([^"]+)"[^>]*(?:data-original|src)="([^"]+)"',
                    re.S
                )
                matches2 = pattern2.findall(html)
                for href, title, pic in matches2:
                    videos.append({
                        "vod_id": href.lstrip("/"),
                        "vod_name": title.strip(),
                        "vod_pic": pic,
                        "vod_remarks": ""
                    })
            else:
                for href, title, pic in matches:
                    videos.append({
                        "vod_id": href.lstrip("/"),
                        "vod_name": title.strip(),
                        "vod_pic": pic,
                        "vod_remarks": ""
                    })

            # 去重
            seen = set()
            unique_videos = []
            for v in videos:
                if v["vod_id"] not in seen:
                    seen.add(v["vod_id"])
                    unique_videos.append(v)

            return {
                "list": unique_videos,
                "page": int(pg),
                "pagecount": 999,
                "limit": 40,
                "total": 99999
            }
        except Exception as e:
            print(f"[categoryContent] error: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 40, "total": 0}

    def detailContent(self, ids):
        """详情 + 播放地址"""
        try:
            vid = ids[0]
            if not vid.endswith(".html"):
                vid = vid + ".html"
            url = f"{self.host}/{vid.lstrip('/')}"

            html = self.fetch(url)
            if not html:
                return {"list": []}

            # 标题
            title_match = re.search(r'<title>([^<]+)</title>', html)
            title = ""
            if title_match:
                title = title_match.group(1).split("-")[0].strip()
                title = title.replace("正在播放：", "").replace("视频播放", "").strip()

            # 提取 m3u8（页面直接暴露 rawUrl）
            play_url = ""
            m3u8_patterns = [
                r"const\s+rawUrl\s*=\s*['\"](https?://[^'\"]+\.m3u8[^'\"]*)['\"]",
                r"['\"](https?://[^'\"]+\.m3u8[^'\"]*)['\"]",
                r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
            ]
            for p in m3u8_patterns:
                m = re.search(p, html)
                if m:
                    play_url = m.group(1)
                    break

            if not play_url:
                all_m3u8 = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
                if all_m3u8:
                    play_url = all_m3u8[0]

            vod = {
                "vod_id": ids[0],
                "vod_name": title or vid,
                "vod_pic": "",
                "vod_content": title or vid,
                "vod_play_from": "超级片直链",
                "vod_play_url": f"正片${play_url}" if play_url else "暂无播放地址$"
            }
            return {"list": [vod]}
        except Exception as e:
            print(f"[detailContent] error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        """搜索"""
        try:
            encoded_key = parse.quote(key)
            if str(pg) == "1":
                url = f"{self.host}/s/index.html?wd={encoded_key}"
            else:
                url = f"{self.host}/s/{encoded_key}/page/{pg}.html"

            html = self.fetch(url)
            if not html:
                return {"list": []}

            videos = []
            pattern = re.compile(
                r'<a[^>]+class="[^"]*stui-vodlycms_list__thumb[^"]*"[^>]+href="(/?\d+\.html)"[^>]+title="([^"]*)"[^>]+data-original="([^"]+)"',
                re.S
            )
            matches = pattern.findall(html)

            if not matches:
                pattern2 = re.compile(
                    r'<a[^>]+href="(/?\d{6,}\.html)"[^>]+title="([^"]+)"[^>]*(?:data-original|src)="([^"]+)"',
                    re.S
                )
                matches2 = pattern2.findall(html)
                for href, title, pic in matches2:
                    videos.append({
                        "vod_id": href.lstrip("/"),
                        "vod_name": title.strip(),
                        "vod_pic": pic,
                        "vod_remarks": "搜索"
                    })
            else:
                for href, title, pic in matches:
                    videos.append({
                        "vod_id": href.lstrip("/"),
                        "vod_name": title.strip(),
                        "vod_pic": pic,
                        "vod_remarks": "搜索"
                    })

            # 去重
            seen = set()
            unique_videos = []
            for v in videos:
                if v["vod_id"] not in seen:
                    seen.add(v["vod_id"])
                    unique_videos.append(v)

            return {"list": unique_videos}
        except Exception as e:
            print(f"[searchContent] error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        """播放"""
        return {
            "parse": 0,
            "url": id,
            "header": json.dumps({
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/"
            })
        }

    def fetch(self, url, headers=None):
        """统一请求"""
        try:
            import requests
            h = headers or self.headers
            r = requests.get(url, headers=h, timeout=15, verify=False)
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"[fetch] {url} error: {e}")
            return ""
