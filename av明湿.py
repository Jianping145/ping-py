#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AV名湿 蜂蜜影视爬虫
轮海秘境 · 苦海境 —— 苹果CMS正则直取流

网站结构：
- 苹果CMS (maccms)
- 分类: /vod/type/id/{id}.html
- 分页: /vod/type/id/{id}/page/{page}.html
- 播放: /vod/play/id/{id}/sid/1/nid/1.html
- 视频源: player_data JSON 中的 url 字段 (m3u8)
"""

import sys
import re
import json
import requests
from urllib import parse

sys.path.append("..")
from base.spider import Spider


class YuanTianShu:
    """源天书——基础HTTP抓取"""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    session = requests.Session()

    @classmethod
    def fetch(cls, url, headers=None, timeout=15):
        h = {**cls.headers, **(headers or {})}
        try:
            resp = cls.session.get(url, headers=h, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[源天书] 抓取失败 {url}: {e}")
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


class LunHai_KuHai(YuanTianShu):
    """
    【轮海秘境 · 苦海境】
    苹果CMS正则直取流
    """

    siteUrl = "https://fzn.avms2.motorcycles"
    basePath = "/cn/home/web/index.php"

    # 分类映射（根据截图）
    categories = {
        "20": "主播网红",
        "21": "偷拍自拍",
        "22": "人妻熟女",
        "23": "强奸乱伦",
        "24": "制服丝袜",
        "25": "自慰变态",
        "26": "国产精品",
        "27": "亚洲情色",
        "28": "卡通动漫",
        "29": "三级伦理",
        "30": "欧美精品",
        "31": "无广告视频",
        "32": "东京指南",
        "33": "滋色园",
    }

    # ═══════════════════════════════════════════════════
    # 首页分类
    # ═══════════════════════════════════════════════════
    def homeContent(self, filter):
        classes = []
        for cid, name in self.categories.items():
            classes.append({
                "type_id": cid,
                "type_name": name
            })
        return {"class": classes}

    # ═══════════════════════════════════════════════════
    # 分类列表
    # ═══════════════════════════════════════════════════
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1

        # 构建URL
        if pg == 1:
            url = f"{self.siteUrl}{self.basePath}/vod/type/id/{tid}.html"
        else:
            url = f"{self.siteUrl}{self.basePath}/vod/type/id/{tid}/page/{pg}.html"

        html = self.fetch(url)
        videos = self._parse_video_list(html)

        # 检查是否有下一页
        has_next = self._check_has_next(html, pg)

        return {
            "list": videos,
            "page": pg,
            "pagecount": 999 if has_next else pg,
            "limit": len(videos),
            "total": 999 * len(videos) if has_next else len(videos),
        }

    # ═══════════════════════════════════════════════════
    # 详情页
    # ═══════════════════════════════════════════════════
    def detailContent(self, ids):
        vod_id = ids[0]

        # 构建播放页URL
        url = f"{self.siteUrl}{self.basePath}/vod/play/id/{vod_id}/sid/1/nid/1.html"
        html = self.fetch(url)

        # 提取player_data
        play_info = self._extract_player_data(html)

        if not play_info:
            return {"list": []}

        title = play_info.get("title", "")
        play_url = play_info.get("url", "")
        cover = play_info.get("cover", "")

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": cover,
                "vod_remarks": "",
                "vod_content": "",
                "vod_play_from": "直链",
                "vod_play_url": f"第1集${play_url}" if play_url else "",
            }]
        }

    # ═══════════════════════════════════════════════════
    # 播放
    # ═══════════════════════════════════════════════════
    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "url": id,
            "header": "",
        }

    # ═══════════════════════════════════════════════════
    # 搜索
    # ═══════════════════════════════════════════════════
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if pg else 1

        # 苹果CMS搜索
        search_url = f"{self.siteUrl}{self.basePath}/vod/search.html?wd={parse.quote(key)}"
        if pg > 1:
            search_url = f"{self.siteUrl}{self.basePath}/vod/search/page/{pg}.html?wd={parse.quote(key)}"

        html = self.fetch(search_url)
        videos = self._parse_video_list(html)

        return {
            "list": videos,
            "page": pg,
            "pagecount": 1,
            "limit": len(videos),
            "total": len(videos),
        }

    # ═══════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════

    def _parse_video_list(self, html):
        """解析视频列表"""
        videos = []

        # 分割视频块
        blocks = html.split('<div class="col-sm-6 col-md-4 col-lg-4">')

        for block in blocks[1:]:
            try:
                # 提取播放链接和ID
                link_match = re.search(r'href="(/cn/home/web/index\.php/vod/play/id/(\d+)[^"]*)"', block)
                if not link_match:
                    continue

                vod_id = link_match.group(2)

                # 提取图片
                img_match = re.search(r'<img src="([^"]+)"', block)
                img_url = img_match.group(1) if img_match else ""

                # 提取标题
                title_match = re.search(r'<span class="video-title[^"]*">([^<]+)</span>', block)
                title = title_match.group(1).strip() if title_match else ""

                # 提取时长
                duration_match = re.search(r'<div class="duration">\s*([^<]+?)\s*</div>', block)
                duration = duration_match.group(1).strip() if duration_match else ""

                # 提取观看数
                views_match = re.search(r'fa-eye[^>]*>.*?(\d+)', block)
                views = views_match.group(1) if views_match else ""

                remarks = duration or views or ""

                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": img_url,
                    "vod_remarks": remarks,
                })
            except Exception:
                continue

        return videos

    def _extract_player_data(self, html):
        """提取player_data中的播放信息"""
        result = {}

        # 提取player_data JSON
        player_match = re.search(r'player_data\s*=\s*(\{[^}]+\})', html)
        if player_match:
            try:
                player_json = json.loads(player_match.group(1))
                url = player_json.get("url", "")
                # 处理转义的URL
                url = url.replace("\\/", "/")
                result["url"] = url
            except Exception as e:
                print(f"[苦海境] player_data解析失败: {e}")

        # 提取标题
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            title = title_match.group(1)
            # 清理标题: "在线播放XXX 第1集 - 高清资源 - AV名湿" -> "XXX"
            title = re.sub(r'^在线播放', '', title)
            title = re.sub(r'\s*第\d+集.*$', '', title)
            result["title"] = title.strip()

        # 提取封面
        cover_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="[^"]*img-responsive[^"]*"', html)
        if not cover_match:
            cover_match = re.search(r'property="og:image"[^>]+content="([^"]+)"', html)
        if cover_match:
            result["cover"] = cover_match.group(1)

        return result

    def _check_has_next(self, html, current_page):
        """检查是否有下一页"""
        # 查找分页链接
        next_patterns = [
            rf'page/{current_page + 1}\.html',
            r'下一页',
            r'next',
            r'»',
        ]
        for pattern in next_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                return True
        return False


# ═══════════════════════════════════════════════════
# 蜂蜜影视标准入口
# ═══════════════════════════════════════════════════
class Spider(LunHai_KuHai):
    def init(self, extend=""):
        print("[红尘仙] AV名湿 Spider 初始化")
        return True

    def isVideoFormat(self, url):
        video_formats = [".m3u8", ".mp4", ".webm", ".mkv", ".ts"]
        return any(fmt in url.lower() for fmt in video_formats)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "application/json", json.dumps({"status": "no_proxy_needed"})]
