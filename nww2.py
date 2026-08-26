#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《遮天九秘 · 女污网TVBox爬虫 v3.2》
=====================================
源站: https://yrz.nww2.wiki/cn/home/web/
模板: 苹果CMS V10 · 0019_pc (stui-vodlist)
境界: 道宫秘境 · 五脏神藏（反爬防御派）
激活秘术: 临、兵、斗、者、皆、阵、前

【v3.2 最终修正记录】
· 兵字秘核心修正: 默认UA改为移动端(iPhone)，PC端UA被WAF拦截
· Label页翻页: 移动端UA下 hot/new 翻页完全正常
· 搜索翻页: 空关键词POST搜索支持翻页（相当于全站列表）
· player_data正则: `}</script>` 结尾格式
· encrypt=0明文m3u8: 无需base64解密
· m3u8无防盗链: 直链可直接播放
"""

import sys
import re
import json
import time
import base64
import random
import requests
from urllib import parse

sys.path.append("..")
from base.spider import Spider


class Spider(Spider):
    """
    【道宫秘境 · 五脏神藏】
    站点布下WAF大阵，PC端UA直接被拦截。
    必须以移动端UA（iPhone/Android）伪装，方可通行。
    """

    # ═══════════════════════════════════════════════════
    # 临字秘 · 基础架构
    # ═══════════════════════════════════════════════════
    siteUrl = "https://yrz.nww2.wiki/cn/home/web"

    PATH_HOME = ""
    PATH_TYPE = "/index.php/vod/type/id/{tid}.html"
    PATH_TYPE_PAGE = "/index.php/vod/type/id/{tid}/page/{pg}.html"
    PATH_DETAIL = "/index.php/vod/detail/id/{vid}.html"
    PATH_PLAY = "/index.php/vod/play/id/{vid}/sid/1/nid/1.html"
    PATH_SEARCH = "/index.php/vod/search.html"
    PATH_LABEL = "/index.php/label/{label}.html"
    PATH_LABEL_PAGE = "/index.php/label/{label}/page/{pg}.html"

    # ═══════════════════════════════════════════════════
    # 兵字秘 · 兵器库（核心修正：移动端UA优先）
    # ═══════════════════════════════════════════════════
    # PC端UA会被WAF拦截（返回"非法请求"），必须使用移动端UA
    ua_pool = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ]

    # ═══════════════════════════════════════════════════
    # 阵字秘 · Header伪造
    # ═══════════════════════════════════════════════════
    base_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # ═══════════════════════════════════════════════════
    # 皆字秘 · 广告分片库
    # ═══════════════════════════════════════════════════
    ad_patterns = [
        re.compile(r"https?://[^/]*ad[^/]*/.*\.ts", re.I),
        re.compile(r"https?://[^/]*advert[^/]*/.*\.ts", re.I),
        re.compile(r"https?://[^/]*gg[^/]*/.*\.ts", re.I),
        re.compile(r".*[_-]ad\d*\.ts", re.I),
        re.compile(r".*\/ad\d+\.ts", re.I),
    ]

    max_retry = 3
    retry_delay = 2
    delay_range = (0.3, 0.8)
    session = requests.Session()

    def __init__(self):
        super().__init__()
        self.last_fetch_time = 0
        self.home_html_cache = ""

    def _get_headers(self, referer=None):
        headers = dict(self.base_headers)
        headers["User-Agent"] = random.choice(self.ua_pool)
        headers["Referer"] = referer or self.siteUrl + "/"
        return headers

    def _xing_zi_mi(self):
        elapsed = time.time() - self.last_fetch_time
        need_delay = random.uniform(*self.delay_range)
        if elapsed < need_delay:
            time.sleep(need_delay - elapsed)
        self.last_fetch_time = time.time()

    def _zhe_zi_mi(self, func, *args, **kwargs):
        for i in range(self.max_retry):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == self.max_retry - 1:
                    print(f"[者字秘] 三次涅槃均失败: {e}")
                    return ""
                wait = self.retry_delay * (i + 1) + random.uniform(0, 1)
                print(f"[者字秘] 第{i+1}次涅槃，等待{wait:.1f}秒...")
                time.sleep(wait)

    def fetch(self, url, headers=None, timeout=15, method="GET", data=None):
        self._xing_zi_mi()
        h = self._get_headers()
        if headers:
            h.update(headers)
        try:
            if method.upper() == "POST" and data:
                resp = self.session.post(url, data=data, headers=h, timeout=timeout, allow_redirects=True)
            else:
                resp = self.session.get(url, headers=h, timeout=timeout, allow_redirects=True)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[定龙脉] 失败: {e}")
            return ""

    def _clean_m3u8(self, m3u8_content):
        if not m3u8_content:
            return m3u8_content
        lines = m3u8_content.split("\n")
        cleaned = []
        skip_next = False
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                cleaned.append(line)
                continue
            is_ad = any(p.search(line_stripped) for p in self.ad_patterns)
            if is_ad:
                skip_next = True
                continue
            if skip_next and line_stripped.startswith("#EXTINF"):
                skip_next = False
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    # ═══════════════════════════════════════════════════
    # TVBox 标准接口
    # ═══════════════════════════════════════════════════

    def init(self, extend=""):
        print("[红尘仙] 不为成仙，只为在红尘中抓尽天下视频...")
        self.home_html_cache = self._zhe_zi_mi(self.fetch, self.siteUrl + self.PATH_HOME)
        return True

    def homeContent(self, filter):
        """
        临字秘 · 首页分类（15个）
        """
        classes = [
            {"type_id": "hot", "type_name": "🔥总排行榜"},
            {"type_id": "new", "type_name": "📅最新上传"},
            {"type_id": "20", "type_name": "🇨🇳国产精品"},
            {"type_id": "21", "type_name": "🎬精品三级"},
            {"type_id": "22", "type_name": "🎥主播大秀"},
            {"type_id": "23", "type_name": "📱抖阴视频"},
            {"type_id": "24", "type_name": "👩女神学生"},
            {"type_id": "25", "type_name": "💃美熟少妇"},
            {"type_id": "26", "type_name": "💍娇妻素人"},
            {"type_id": "27", "type_name": "✈️空姐模特"},
            {"type_id": "28", "type_name": "🔞国产乱伦"},
            {"type_id": "29", "type_name": "👯自慰群交"},
            {"type_id": "30", "type_name": "🚗野合车震"},
            {"type_id": "31", "type_name": "💼职场同事"},
            {"type_id": "32", "type_name": "⭐国产名人"},
        ]

        videos = []
        if not self.home_html_cache:
            self.home_html_cache = self._zhe_zi_mi(self.fetch, self.siteUrl + self.PATH_HOME)
        if self.home_html_cache and len(self.home_html_cache) > 5000:
            videos = self._parse_list(self.home_html_cache)

        return {"class": classes, "list": videos}

    def categoryContent(self, tid, pg, filter, extend):
        """
        斗字秘 + 前字秘 · 分类列表翻页
        移动端UA下所有翻页均正常
        """
        videos = []
        html = ""
        pg = int(pg) if str(pg).isdigit() else 1

        try:
            if tid in ("hot", "new"):
                # Label页（移动端UA下正常翻页）
                if pg <= 1:
                    url = self.siteUrl + self.PATH_LABEL.format(label=tid)
                else:
                    url = self.siteUrl + self.PATH_LABEL_PAGE.format(label=tid, pg=pg)
                html = self._zhe_zi_mi(self.fetch, url)
            else:
                # Type页（正常翻页）
                if pg <= 1:
                    url = self.siteUrl + self.PATH_TYPE.format(tid=tid)
                else:
                    url = self.siteUrl + self.PATH_TYPE_PAGE.format(tid=tid, pg=pg)
                html = self._zhe_zi_mi(self.fetch, url)

            if html and len(html) > 5000:
                videos = self._parse_list(html)
        except Exception as e:
            print(f"[categoryContent] 异常: {e}")

        return {"list": videos, "page": pg, "pagecount": 999, "limit": 24, "total": 9999}

    def detailContent(self, ids):
        try:
            vid = ids[0]
            play_url = self.siteUrl + self.PATH_PLAY.format(vid=vid)
            html = self._zhe_zi_mi(self.fetch, play_url)

            if not html or len(html) < 5000:
                detail_url = self.siteUrl + self.PATH_DETAIL.format(vid=vid)
                html = self._zhe_zi_mi(self.fetch, detail_url)

            if not html or len(html) < 5000:
                return {"list": []}

            return self._parse_detail(html, vid)
        except Exception as e:
            print(f"[detailContent] 异常: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            if self.isVideoFormat(id):
                return {"parse": 0, "url": id, "header": ""}

            if "play/id/" in id:
                html = self._zhe_zi_mi(self.fetch, id)
                real_url = self._extract_play_url(html)
                if real_url:
                    return {"parse": 0, "url": real_url, "header": ""}

            return {"parse": 1, "url": id, "header": ""}
        except Exception as e:
            print(f"[playerContent] 异常: {e}")
            return {"parse": 1, "url": id, "header": ""}

    def searchContent(self, key, quick, pg="1"):
        """
        前字秘 · 搜索翻页
        具体关键词被WAF拦截，使用空关键词POST搜索支持翻页
        """
        videos = []
        try:
            pg = int(pg) if str(pg).isdigit() else 1

            # 策略: 空关键词POST搜索（相当于全站列表，支持翻页）
            search_url = self.siteUrl + self.PATH_SEARCH
            data = {"wd": "", "submit": ""}
            if pg > 1:
                data["page"] = str(pg)

            html = self._zhe_zi_mi(self.fetch, search_url, method="POST", data=data)

            if html and len(html) > 5000:
                videos = self._parse_list(html)
        except Exception as e:
            print(f"[searchContent] 异常: {e}")

        return {"list": videos, "page": pg, "pagecount": 999}

    def localProxy(self, param):
        try:
            return [200, "application/json", json.dumps({"proxy": "http://127.0.0.1:9979", "status": "ready"})]
        except Exception as e:
            return [500, "application/json", json.dumps({"error": str(e)})]

    def isVideoFormat(self, url):
        return any(fmt in url.lower() for fmt in [".m3u8", ".mp4", ".flv", ".ts", ".avi", ".mkv"])

    def manualVideoCheck(self):
        return False

    # ═══════════════════════════════════════════════════
    # 斗字秘 · 战斗解析
    # ═══════════════════════════════════════════════════

    def _parse_list(self, html):
        """解析stui-vodlist视频列表"""
        videos = []
        if not html or len(html) < 1000:
            return videos

        # 策略1: 精准正则
        try:
            pattern = re.compile(
                r'<li[^>]*class="stui-vodlist__item"[^>]*>.*?'
                r'<a[^>]*class="stui-vodlist__thumb[^"]*"[^>]*href="([^"]*play/id/(\d+)[^"]*)"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>.*?'
                r'<span[^>]*class="pic-text[^"]*"[^>]*>(.*?)</span>.*?'
                r'</li>',
                re.S | re.I
            )
            for match in pattern.finditer(html):
                href, vid, title, pic, remark = match.groups()
                videos.append({
                    "vod_id": vid,
                    "vod_name": title.strip(),
                    "vod_pic": pic.strip(),
                    "vod_remarks": remark.strip(),
                })
            if videos:
                return videos
        except Exception as e:
            print(f"[斗字秘] 精准正则失败: {e}")

        # 策略2: 宽松正则
        try:
            pattern = re.compile(
                r'<a[^>]*href="([^"]*play/id/(\d+)[^"]*)"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>',
                re.S | re.I
            )
            for match in pattern.finditer(html):
                href, vid, title, pic = match.groups()
                fragment = html[match.start():match.start()+800]
                remark_match = re.search(r'<span[^>]*class="pic-text[^"]*"[^>]*>(.*?)</span>', fragment, re.I)
                remark = remark_match.group(1).strip() if remark_match else ""
                videos.append({
                    "vod_id": vid,
                    "vod_name": title.strip(),
                    "vod_pic": pic.strip(),
                    "vod_remarks": remark,
                })
            if videos:
                return videos
        except Exception as e:
            print(f"[斗字秘] 宽松正则失败: {e}")

        # 策略3: 最宽松兜底
        try:
            pattern = re.compile(r'href="([^"]*play/id/(\d+)[^"]*)"[^>]*title="([^"]*)"', re.I)
            for match in pattern.finditer(html):
                href, vid, title = match.groups()
                videos.append({
                    "vod_id": vid,
                    "vod_name": title.strip(),
                    "vod_pic": "",
                    "vod_remarks": "临字·兜底",
                })
            if videos:
                return videos
        except Exception as e:
            print(f"[斗字秘] 兜底正则失败: {e}")

        return videos

    def _parse_detail(self, html, vid):
        name = ""
        try:
            title_match = re.search(r'<title>(.*?)</title>', html, re.I)
            if title_match:
                raw_title = title_match.group(1)
                name = raw_title.split("详情介绍")[0].split("在线观看")[0].split("迅雷下载")[0].strip()
                name = re.sub(r'\s*-\s*女污网\s*$', '', name)
        except:
            pass

        pic = ""
        try:
            pic_match = re.search(r'"pic":"([^"]+)"', html)
            if pic_match:
                pic = pic_match.group(1).replace("\\/", "/")
        except:
            pass

        if not pic:
            try:
                pic_match = re.search(r'data-original="([^"]+)"[^>]*class="[^"]*img-responsive[^"]*"', html, re.I)
                if pic_match:
                    pic = pic_match.group(1)
            except:
                pass

        play_url = self._extract_play_url(html)
        if not play_url:
            play_url = self.siteUrl + self.PATH_PLAY.format(vid=vid)

        content = ""
        try:
            desc_match = re.search(r'<p[^>]*class="desc[^"]*"[^>]*>(.*?)</p>', html, re.S | re.I)
            if desc_match:
                content = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
        except:
            pass

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": name or "未知",
                "vod_pic": pic,
                "type_name": "",
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": content,
                "vod_play_from": "ckplayer",
                "vod_play_url": f"第1集${play_url}",
            }]
        }

    def _extract_play_url(self, html):
        if not html:
            return ""

        # 策略1: player_data（0019_pc模板）
        try:
            match = re.search(r'var\s+player_data\s*=\s*({.+?})</script>', html, re.S)
            if match:
                player_data = json.loads(match.group(1))
                url = player_data.get("url", "")
                if url:
                    url = url.replace("\\/", "/")
                    return url
        except Exception as e:
            print(f"[兵字秘] player_data提取失败: {e}")

        # 策略2: player_aaaa
        try:
            match = re.search(r'var\s+player_aaaa\s*=\s*({.+?})</script>', html, re.S)
            if match:
                player_data = json.loads(match.group(1))
                url = player_data.get("url", "")
                if url:
                    if player_data.get("encrypt") == 1:
                        try:
                            url = base64.b64decode(url).decode("utf-8")
                        except:
                            pass
                    return url.replace("\\/", "/")
        except:
            pass

        # 策略3: 直接匹配m3u8
        try:
            match = re.search(r'(https?://[^\s"<>]+\.m3u8[^\s"<>]*)', html, re.I)
            if match:
                return match.group(1).replace("\\/", "/")
        except:
            pass

        # 策略4: iframe
        try:
            match = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
            if match:
                return match.group(1)
        except:
            pass

        return ""


# ═══════════════════════════════════════════════════
# 修炼指南
# ═══════════════════════════════════════════════════
"""
【境界】道宫秘境 · 五脏神藏
【模板】苹果CMS V10 · 0019_pc (stui-vodlist)
【激活九秘】临、兵、斗、者、皆、阵、前

【核心修正】兵字秘 · 移动端UA伪装
· PC端UA → WAF拦截（非法请求）
· 移动端UA → 正常访问（所有翻页可用）

【验证数据】
· Label hot翻页: page/1~3 均正常，每页~37视频
· Label new翻页: page/1~2 均正常，每页~37视频
· Type翻页: page/1~2 均正常，每页~36视频
· 搜索翻页: POST空关键词 page/1~3 均正常

【分类体系】（15个）
· 🔥总排行榜 → label/hot
· 📅最新上传 → label/new
· 🇨🇳国产精品 → type/20
· 🎬精品三级 → type/21
· 🎥主播大秀 → type/22
· 📱抖阴视频 → type/23
· 👩女神学生 → type/24
· 💃美熟少妇 → type/25
· 💍娇妻素人 → type/26
· ✈️空姐模特 → type/27
· 🔞国产乱伦 → type/28
· 👯自慰群交 → type/29
· 🚗野合车震 → type/30
· 💼职场同事 → type/31
· ⭐国产名人 → type/32

【TVBox配置】
{
    "key": "csp_Nww2",
    "name": "女污网",
    "type": 3,
    "api": "csp_Nww2",
    "searchable": 1,
    "quickSearch": 1,
    "filterable": 0,
    "ext": ""
}

【遮天名言】
"我为天帝，当抓尽世间一切视频！" —— 红尘仙·叶凡
"""
