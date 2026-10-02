#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AiPornFeed TVBox Spider
轮海秘境 · 彼岸境 —— HTML JSON-LD 直取流

API 分析结论：
- /tag/{tag}?page=N → HTML 内嵌 JSON-LD CollectionPage，30个视频/页，支持分页
- /video/{id} → HTML 内嵌 JSON-LD VideoObject，包含 contentUrl 直链
- /api/videos → 支持 cursor 分页（用于"最新"）
- /api/search?q=xxx → 搜索（20条，无分页）
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
        "Accept-Language": "en-US,en;q=0.9",
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


class LunHai_BiAn(YuanTianShu):
    """
    【轮海秘境 · 彼岸境】
    轻量直取流 —— HTML JSON-LD 解析
    """

    siteUrl = "https://aipornfeed.com"
    apiBase = "https://aipornfeed.com/api"

    # ═══════════════════════════════════════════════════
    # 首页分类 —— 硬编码88个分类
    # ═══════════════════════════════════════════════════
    def homeContent(self, filter):
        classes = [
            {"type_id": "__latest__", "type_name": "✨ 最新视频"},
            {"type_id": "__popular__", "type_name": "🔥 热门视频"},
            {"type_id": "big-tits", "type_name": "# Big Tits (43.3K)"},
            {"type_id": "blowjob", "type_name": "# Blowjob (15K)"},
            {"type_id": "cumshot", "type_name": "# Cumshot (14.7K)"},
            {"type_id": "anime", "type_name": "# Anime (11.6K)"},
            {"type_id": "orgasm", "type_name": "# Orgasm (11.6K)"},
            {"type_id": "rough-sex", "type_name": "# Rough Sex (10.8K)"},
            {"type_id": "big-ass", "type_name": "# Big Ass (9.5K)"},
            {"type_id": "anal", "type_name": "# Anal (9.2K)"},
            {"type_id": "solo", "type_name": "# Solo (8K)"},
            {"type_id": "deepthroat", "type_name": "# Deepthroat (8K)"},
            {"type_id": "big-dick", "type_name": "# Big Dick (7.9K)"},
            {"type_id": "cowgirl", "type_name": "# Cowgirl (7.8K)"},
            {"type_id": "creampie", "type_name": "# Creampie (7.3K)"},
            {"type_id": "blonde", "type_name": "# Blonde (6.5K)"},
            {"type_id": "masturbation", "type_name": "# Masturbation (5.8K)"},
            {"type_id": "doggystyle", "type_name": "# Doggystyle (5.3K)"},
            {"type_id": "asian", "type_name": "# Asian (5.2K)"},
            {"type_id": "facial", "type_name": "# Facial (5K)"},
            {"type_id": "handjob", "type_name": "# Handjob (4.8K)"},
            {"type_id": "lesbian", "type_name": "# Lesbian (4.8K)"},
            {"type_id": "striptease", "type_name": "# Striptease (4.4K)"},
            {"type_id": "pov", "type_name": "# POV (4.3K)"},
            {"type_id": "outdoor", "type_name": "# Outdoor (3.8K)"},
            {"type_id": "bikini", "type_name": "# Bikini (3.8K)"},
            {"type_id": "bdsm", "type_name": "# BDSM (3.8K)"},
            {"type_id": "mature", "type_name": "# Mature (3.6K)"},
            {"type_id": "moaning", "type_name": "# Moaning (3.4K)"},
            {"type_id": "tit-play", "type_name": "# Tit Play (3.2K)"},
            {"type_id": "long-hair", "type_name": "# Long Hair (3.2K)"},
            {"type_id": "lingerie", "type_name": "# Lingerie (3.1K)"},
            {"type_id": "beach", "type_name": "# Beach (3.1K)"},
            {"type_id": "4k", "type_name": "# 4K Porn (2.8K)"},
            {"type_id": "curvy", "type_name": "# Curvy (2.8K)"},
            {"type_id": "romantic", "type_name": "# Romantic (2.7K)"},
            {"type_id": "threesome", "type_name": "# Threesome (2.6K)"},
            {"type_id": "brunette", "type_name": "# Brunette (2.4K)"},
            {"type_id": "toys", "type_name": "# Toys (2.3K)"},
            {"type_id": "petite", "type_name": "# Petite (2.2K)"},
            {"type_id": "milf", "type_name": "# MILF (2.2K)"},
            {"type_id": "interracial", "type_name": "# Interracial (2.2K)"},
            {"type_id": "reverse-cowgirl", "type_name": "# Reverse Cowgirl (2.1K)"},
            {"type_id": "cosplay", "type_name": "# Cosplay (2.1K)"},
            {"type_id": "redhead", "type_name": "# Redhead (2K)"},
            {"type_id": "fetish", "type_name": "# Fetish (1.9K)"},
            {"type_id": "fingering", "type_name": "# Fingering (1.7K)"},
            {"type_id": "japanese", "type_name": "# Japanese (1.7K)"},
            {"type_id": "public", "type_name": "# Public (1.5K)"},
            {"type_id": "small-tits", "type_name": "# Small Tits (1.5K)"},
            {"type_id": "bondage", "type_name": "# Bondage (1.4K)"},
            {"type_id": "squirt", "type_name": "# Squirt (1.4K)"},
            {"type_id": "pussy-licking", "type_name": "# Pussy Licking (1.3K)"},
            {"type_id": "amateur", "type_name": "# Amateur (1.3K)"},
            {"type_id": "group-sex", "type_name": "# Group Sex (1.3K)"},
            {"type_id": "hentai", "type_name": "# Hentai (1.3K)"},
            {"type_id": "office", "type_name": "# Office (1.2K)"},
            {"type_id": "babe", "type_name": "# Babe (1.1K)"},
            {"type_id": "double-penetration", "type_name": "# Double Penetration (1.1K)"},
            {"type_id": "shower", "type_name": "# Shower (1K)"},
            {"type_id": "gangbang", "type_name": "# Gangbang (1K)"},
            {"type_id": "shaved-pussy", "type_name": "# Shaved Pussy (906)"},
            {"type_id": "stockings", "type_name": "# Stockings (875)"},
            {"type_id": "undressing", "type_name": "# Undressing (785)"},
            {"type_id": "bbw", "type_name": "# BBW (751)"},
            {"type_id": "uniforms", "type_name": "# Uniforms (699)"},
            {"type_id": "ebony", "type_name": "# Ebony (657)"},
            {"type_id": "tattooed", "type_name": "# Tattooed (626)"},
            {"type_id": "latina", "type_name": "# Latina (616)"},
            {"type_id": "hairy-pussy", "type_name": "# Hairy Pussy (605)"},
            {"type_id": "spanking", "type_name": "# Spanking (481)"},
            {"type_id": "indian", "type_name": "# Indian (458)"},
            {"type_id": "feet", "type_name": "# Feet (431)"},
            {"type_id": "voyeur", "type_name": "# Voyeur (401)"},
            {"type_id": "trans", "type_name": "# Trans (394)"},
            {"type_id": "orgy", "type_name": "# Orgy (366)"},
            {"type_id": "nurse", "type_name": "# Nurse (350)"},
            {"type_id": "fisting", "type_name": "# Fisting (342)"},
            {"type_id": "gay", "type_name": "# Gay (339)"},
            {"type_id": "massage", "type_name": "# Massage (331)"},
            {"type_id": "vintage", "type_name": "# Vintage (330)"},
            {"type_id": "rimjob", "type_name": "# Rimjob (219)"},
            {"type_id": "60fps", "type_name": "# 60 FPS (185)"},
            {"type_id": "bisexual", "type_name": "# Bisexual (185)"},
            {"type_id": "pantyhose", "type_name": "# Pantyhose (162)"},
            {"type_id": "vibrator", "type_name": "# Vibrator (62)"},
            {"type_id": "sex-party", "type_name": "# Sex Party (62)"},
            {"type_id": "russian", "type_name": "# Russian (37)"},
            {"type_id": "pickup", "type_name": "# Pickup (28)"},
            {"type_id": "casting", "type_name": "# Casting (3)"},
        ]
        return {"class": classes}

    # ═══════════════════════════════════════════════════
    # 分类列表
    # ═══════════════════════════════════════════════════
    def categoryContent(self, tid, pg, filter, extend):
        """
        彼岸境修士翻列表

        策略：
        - __latest__: /api/videos + cursor分页
        - __popular__: /api/videos 取50条按views排序
        - 其他分类: /tag/{tag}?page=N → HTML JSON-LD（30条/页，支持分页）
        """
        pg = int(pg) if pg else 1
        videos = []

        try:
            if tid == "__latest__":
                url = f"{self.apiBase}/videos?limit=30"
                if pg > 1:
                    cursor = self._get_cursor_for_page(url, pg)
                    if cursor:
                        url += f"&cursor={cursor}"
                data = self._fetch_json_api(url)
                videos = self._parse_api_video_list(data.get("videos", []))
                has_more = data.get("hasMore", False)

            elif tid == "__popular__":
                url = f"{self.apiBase}/videos?limit=50"
                data = self._fetch_json_api(url)
                all_videos = data.get("videos", [])
                all_videos.sort(key=lambda x: x.get("views", 0), reverse=True)
                videos = self._parse_api_video_list(all_videos[:30])
                has_more = False

            else:
                # 分类页面 HTML JSON-LD
                url = f"{self.siteUrl}/tag/{tid}?page={pg}"
                html = self.fetch(url)
                videos = self._parse_tag_page_json_ld(html)
                has_more = len(videos) >= 30

        except Exception as e:
            print(f"[彼岸境] 分类获取失败 tid={tid}: {e}")
            videos = []
            has_more = False

        return {
            "list": videos,
            "page": pg,
            "pagecount": 999 if has_more else pg,
            "limit": len(videos),
            "total": 999 * len(videos) if has_more else len(videos),
        }

    # ═══════════════════════════════════════════════════
    # 详情页
    # ═══════════════════════════════════════════════════
    def detailContent(self, ids):
        vod_id = ids[0]
        try:
            url = f"{self.siteUrl}/video/{vod_id}"
            html = self.fetch(url)

            # 解析 JSON-LD VideoObject
            info = self._parse_video_page_json_ld(html)

            if not info:
                return {"list": []}

            play_url = info.get("contentUrl", "")
            title = info.get("name", "AI Video")
            cover = info.get("thumbnailUrl", "")
            if isinstance(cover, list):
                cover = cover[0] if cover else ""
            desc = info.get("description", "")
            upload_date = info.get("uploadDate", "")

            # 从HTML提取额外信息
            views = self._extract_views(html)
            tags = self._extract_tags(html)

            remarks = f"👁 {views}" if views else ""
            if tags:
                remarks += f" | {' '.join(['#'+t for t in tags[:3]])}"

            content_parts = []
            if desc:
                content_parts.append(desc)
            if upload_date:
                content_parts.append(f"📅 发布: {upload_date[:10]}")
            content = "\n".join(content_parts)

            return {
                "list": [{
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_remarks": remarks,
                    "vod_content": content,
                    "vod_play_from": "AI直链",
                    "vod_play_url": f"正片${play_url}" if play_url else "",
                }]
            }
        except Exception as e:
            print(f"[彼岸境] 详情获取失败 id={vod_id}: {e}")
            return {"list": []}

    # ═══════════════════════════════════════════════════
    # 播放
    # ═══════════════════════════════════════════════════
    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id, "header": ""}

    # ═══════════════════════════════════════════════════
    # 搜索
    # ═══════════════════════════════════════════════════
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if pg else 1
        try:
            url = f"{self.apiBase}/search?q={parse.quote(key)}"
            data = self._fetch_json_api(url)
            videos = self._parse_api_video_list(data.get("videos", []))
            return {
                "list": videos,
                "page": pg,
                "pagecount": 1,
                "limit": len(videos),
                "total": len(videos),
            }
        except Exception as e:
            print(f"[彼岸境] 搜索失败 key={key}: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

    # ═══════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════

    def _fetch_json_api(self, url):
        """获取JSON API数据"""
        h = {**self.headers, "Accept": "application/json"}
        try:
            resp = self.session.get(url, headers=h, timeout=15)
            resp.encoding = "utf-8"
            return resp.json()
        except Exception as e:
            print(f"[源天书] API获取失败 {url}: {e}")
            return {}

    def _parse_tag_page_json_ld(self, html):
        """解析 tag 页面的 JSON-LD CollectionPage"""
        videos = []
        pattern = r'<script type="application/ld\+json">(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL)

        for m in matches:
            try:
                data = json.loads(m)
                if data.get("@type") == "CollectionPage":
                    items = data.get("mainEntity", {}).get("itemListElement", [])
                    for item in items:
                        vid_url = item.get("url", "")
                        vid_id = vid_url.split("/video/")[-1] if "/video/" in vid_url else vid_url
                        videos.append({
                            "vod_id": vid_id,
                            "vod_name": item.get("name", "未命名"),
                            "vod_pic": item.get("image", ""),
                            "vod_remarks": "",
                        })
            except Exception:
                continue
        return videos

    def _parse_video_page_json_ld(self, html):
        """解析 video 详情页的 JSON-LD VideoObject"""
        pattern = r'<script type="application/ld\+json">(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL)

        for m in matches:
            try:
                data = json.loads(m)
                if data.get("@type") == "VideoObject":
                    return data
            except Exception:
                continue
        return None

    def _parse_api_video_list(self, videos_raw):
        """解析 API 返回的视频列表"""
        result = []
        for v in videos_raw:
            try:
                vid = v.get("id", "")
                title = v.get("title", "未命名")
                cover = v.get("thumbnailUrl", "")
                views = v.get("views", 0)
                tags = v.get("tags", [])
                remarks = f"👁 {views}"
                if tags:
                    remarks += f" | #{tags[0]}"
                result.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_remarks": remarks,
                })
            except Exception:
                continue
        return result

    def _extract_views(self, html):
        """从HTML提取观看次数"""
        match = re.search(r'"views"\s*:\s*(\d+)', html)
        if match:
            return match.group(1)
        match = re.search(r'(\d+)\s*views', html, re.IGNORECASE)
        if match:
            return match.group(1)
        return ""

    def _extract_tags(self, html):
        """从HTML提取标签"""
        tags = re.findall(r'href="/tag/([^"]+)"', html)
        return list(set(tags))[:5]

    def _get_cursor_for_page(self, base_url, target_page):
        cursor = None
        current_page = 1
        while current_page < target_page:
            url = base_url
            if cursor:
                url += f"&cursor={cursor}"
            data = self._fetch_json_api(url)
            if not data:
                break
            cursor = data.get("nextCursor")
            has_more = data.get("hasMore", False)
            if not has_more or not cursor:
                return None
            current_page += 1
        return cursor


# ═══════════════════════════════════════════════════
# TVBox 标准入口
# ═══════════════════════════════════════════════════
class Spider(LunHai_BiAn):
    def init(self, extend=""):
        print("[红尘仙] AiPornFeed Spider 初始化")
        return True

    def isVideoFormat(self, url):
        video_formats = [".m3u8", ".mp4", ".webm", ".mkv", ".ts"]
        return any(fmt in url.lower() for fmt in video_formats)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "application/json", json.dumps({"status": "no_proxy_needed"})]
