# -*- coding: utf-8 -*-
# ============================================================
# 适配 https://mao.mdmao86.buzz 的 TVBox 爬虫脚本
# 网站：麻豆TV (自研CMS / MacCMS 风格)
# 功能：首页 / 分类 / 详情 / 播放 / 搜索
# 修复：路径 maoplay->vodplay, maotype->vodtype；host 更新；分类更新
# ============================================================

import re
import json
import html
import urllib.request
import urllib.parse
import ssl
from urllib.parse import urljoin, quote, unquote

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def homeContent(self, filter): pass
        def homeVideoContent(self): pass
        def categoryContent(self, tid, pg, filter, extend): pass
        def detailContent(self, ids): pass
        def playerContent(self, flag, id, vipFlags=None): pass
        def searchContent(self, key, quick, pg='1'): pass
        def isVideoFormat(self, url): pass
        def manualVideoCheck(self): pass
        def localProxy(self, param): pass


def clean_text(text):
    if not text:
        return ""
    text = html.unescape(str(text))
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fix_url(url, host):
    if not url:
        return ""
    url = url.strip()
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        return urljoin(host, url)
    if url.startswith(('http://', 'https://')):
        return url
    return urljoin(host, '/' + url)


class Spider(BaseSpider):

    def __init__(self):
        super().__init__()
        self.host = "https://mao.mdmao86.buzz"
        self.name = "madou_spider"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def init(self, extend=""):
        if extend and extend.startswith("http"):
            self.host = extend.rstrip("/")

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return any(x in url for x in [".m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "video/MP2T", b"", {}]

    def _fetch(self, url, referer=None):
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.host, url)

        try:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            if referer:
                headers["Referer"] = referer
            else:
                headers["Referer"] = self.host + "/"

            req = urllib.request.Request(url, headers=headers)
            r = urllib.request.urlopen(req, timeout=15)
            return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"[{self.name}] 请求失败: {e}")
            return ""

    # ============================================================
    # 解析视频列表
    # 当前页面结构示例:
    # <div class="z-video-item">
    #   <a href="/vodplay/1880469-1-1/" title="...">
    #     <img src="https://...jpg" ...>
    #     <h3 class="z-video-title">...</h3>
    #   </a>
    # </div>
    # ============================================================

    def _parse_video_items(self, html_text):
        if not html_text:
            return []

        videos = []

        # 主匹配：vodplay 路径
        pattern = (
            r'<div[^>]*class="[^"]*z-video-item[^"]*"[^>]*>.*?'
            r'<a[^>]*href="(/vodplay/([^"]+))/?"[^>]*(?:title="([^"]*)")?[^>]*>.*?'
            r'<img[^>]*src="([^"]*)"[^>]*>.*?'
            r'<h3[^>]*class="[^"]*z-video-title[^"]*"[^>]*>(.*?)</h3>'
        )
        matches = re.findall(pattern, html_text, re.DOTALL)

        if not matches:
            # 备用：更宽松
            pattern_simple = (
                r'<a[^>]*href="(/vodplay/([^"]+))/?"[^>]*>.*?'
                r'<img[^>]*src="([^"]*)"[^>]*>.*?'
                r'<h3[^>]*>(.*?)</h3>'
            )
            matches_simple = re.findall(pattern_simple, html_text, re.DOTALL)
            for href, vid, pic, title in matches_simple:
                vid = vid.strip().rstrip('/')
                title = clean_text(title)
                pic = fix_url(pic, self.host)
                if vid and title:
                    videos.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": ""
                    })
            print(f"[_parse_video_items] 备用匹配到 {len(videos)} 个视频项")
            return videos

        print(f"[_parse_video_items] 匹配到 {len(matches)} 个视频项")

        for match in matches:
            try:
                href, vid, title_attr, pic, title_h3 = match
                title = clean_text(title_h3 or title_attr or "")
                pic = fix_url(pic, self.host)
                vid = vid.strip().rstrip('/')
                if vid and title:
                    videos.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": ""
                    })
            except Exception as e:
                print(f"解析单个视频失败: {e}")
                continue

        return videos

    # ============================================================
    # 首页分类（与站点实际 /vodtype/ 一致）
    # ============================================================

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "国产传媒"},
            {"type_id": "2", "type_name": "国产视频"},
            {"type_id": "3", "type_name": "国产黑料"},
            {"type_id": "4", "type_name": "国产主播"},
            {"type_id": "5", "type_name": "亚洲精品"},
            {"type_id": "6", "type_name": "网黄明星"},
            {"type_id": "7", "type_name": "探花精品"},
            {"type_id": "8", "type_name": "自拍偷拍"},
            {"type_id": "9", "type_name": "日本AV"},
            {"type_id": "10", "type_name": "中文字幕"},
            {"type_id": "11", "type_name": "日本有码"},
            {"type_id": "12", "type_name": "日本无码"},
            {"type_id": "13", "type_name": "人妻系列"},
            {"type_id": "14", "type_name": "制服诱惑"},
            {"type_id": "15", "type_name": "强奸乱伦"},
            {"type_id": "16", "type_name": "巨乳系列"},
            {"type_id": "17", "type_name": "三级伦理"},
            {"type_id": "18", "type_name": "sm调教"},
            {"type_id": "20", "type_name": "日韩伦理"},
            {"type_id": "21", "type_name": "欧美极品"},
            {"type_id": "22", "type_name": "动漫电影"},
            {"type_id": "23", "type_name": "人兽乱交"},
            {"type_id": "24", "type_name": "AV解说"},
            {"type_id": "25", "type_name": "多P合集"},
        ]

        return {
            "class": classes,
            "filters": {}
        }

    # ============================================================
    # 首页推荐视频
    # ============================================================

    def homeVideoContent(self):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}
        html_text = self._fetch("/")
        if html_text:
            result["list"] = self._parse_video_items(html_text)
            result["total"] = len(result["list"])
        return result

    # ============================================================
    # 分类页视频列表  /vodtype/{tid}/  或  /vodtype/{tid}/page/{pg}/
    # ============================================================

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

        if int(pg) <= 1:
            url = f"/vodtype/{tid}/"
        else:
            url = f"/vodtype/{tid}/page/{pg}/"

        print(f"[{self.name}] 请求分类页: {url}")

        html_text = self._fetch(url)
        if not html_text:
            return result

        videos = self._parse_video_items(html_text)
        result["list"] = videos

        page_info = re.search(r'第\s*\d+\s*/\s*(\d+)\s*页', html_text)
        if page_info:
            result["pagecount"] = int(page_info.group(1))
        else:
            page_links = re.findall(r'/vodtype/\d+/page/(\d+)/', html_text)
            if page_links:
                result["pagecount"] = max(int(p) for p in page_links)
            else:
                result["pagecount"] = 1 if videos else 0

        result["total"] = len(videos) * result["pagecount"] if result["pagecount"] > 1 else len(videos)
        return result

    # ============================================================
    # 详情页  vod_id 形如 1880469-1-1
    # ============================================================

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        result = {"list": []}

        if not vid:
            return result

        play_path = f"/vodplay/{vid}/"
        html_text = self._fetch(play_path)
        title = f"视频 {vid}"
        pic = ""

        if html_text:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.DOTALL)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', html_text)
            if title_match:
                title = clean_text(title_match.group(1))
                # 去掉站点后缀
                title = re.sub(r'[-_|].*?麻豆.*$', '', title).strip() or title

            pic_match = re.search(r'<img[^>]+(?:src|data-src)="([^"]+)"[^>]*(?:class="[^"]*(?:pic|cover|thumb)[^"]*"|alt="[^"]*")', html_text)
            if not pic_match:
                pic_match = re.search(r'og:image["\']?\s+content=["\']([^"\']+)', html_text)
            if pic_match:
                pic = fix_url(pic_match.group(1), self.host)

        vod_data = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "默认线路",
            "vod_play_url": f"正片${play_path}",
        }

        result["list"].append(vod_data)
        return result

    # ============================================================
    # 播放解析：从 player_aaaa 提取 m3u8
    # ============================================================

    def playerContent(self, flag, id, vipFlags=None):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}

        if self.isVideoFormat(id):
            result["url"] = id
            result["header"] = json.dumps({
                "Referer": self.host + "/",
                "User-Agent": self.user_agent
            })
            return result

        if not id.startswith('http'):
            id = urljoin(self.host, id if id.startswith('/') else f"/vodplay/{id}/")

        print(f"[{self.name}] 请求播放页: {id}")

        html_text = self._fetch(id)
        if not html_text:
            result["url"] = id
            return result

        # 方法1：player_aaaa JSON
        # var player_aaaa={"flag":"play",...,"url":"https:\/\/....m3u8",...}
        player_match = re.search(
            r'player_aaaa\s*=\s*(\{[^;]*?\})\s*;?',
            html_text,
            re.DOTALL
        )
        if player_match:
            raw = player_match.group(1)
            try:
                json_str = raw.replace('\\/', '/')
                # 部分站点可能有多余转义，尽量宽松解析
                player_data = json.loads(json_str)
                play_url = player_data.get('url', '') or player_data.get('url_next', '')
                if play_url:
                    play_url = play_url.replace('\\/', '/')
                    if self.isVideoFormat(play_url) or play_url.startswith('http'):
                        result["url"] = play_url
                        result["header"] = json.dumps({
                            "Referer": self.host + "/",
                            "User-Agent": self.user_agent
                        })
                        print(f"[{self.name}] ✅ 从 player_aaaa 提取到: {play_url}")
                        return result
            except Exception as e:
                print(f"[{self.name}] 解析 player_aaaa JSON 失败: {e}")
                url_match = re.search(r'"url"\s*:\s*"((?:[^"\\]|\\.)+)"', raw)
                if url_match:
                    play_url = url_match.group(1).replace('\\/', '/').replace('\\"', '"')
                    if play_url and (self.isVideoFormat(play_url) or play_url.startswith('http')):
                        result["url"] = play_url
                        result["header"] = json.dumps({
                            "Referer": self.host + "/",
                            "User-Agent": self.user_agent
                        })
                        print(f"[{self.name}] ✅ 正则提取到播放地址: {play_url}")
                        return result

        # 方法2：直接匹配 m3u8 / mp4
        for pat in [
            r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)',
            r'(https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*)',
        ]:
            m = re.search(pat, html_text)
            if m:
                play_url = m.group(1).replace('\\/', '/')
                result["url"] = play_url
                result["header"] = json.dumps({
                    "Referer": self.host + "/",
                    "User-Agent": self.user_agent
                })
                print(f"[{self.name}] ✅ 直接匹配到: {play_url}")
                return result

        print(f"[{self.name}] ❌ 未能提取到播放地址")
        result["url"] = id
        return result

    # ============================================================
    # 搜索  /vodsearch/{key}-------------/  或带 page
    # ============================================================

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

        if not key:
            return result

        # MacCMS 常见搜索路径
        encoded = quote(key)
        if int(pg) <= 1:
            search_url = f"/vodsearch/{encoded}-------------/"
        else:
            search_url = f"/vodsearch/{encoded}-------------/page/{pg}/"

        print(f"[{self.name}] 请求搜索: {search_url}")

        html_text = self._fetch(search_url)
        if not html_text:
            # 备用搜索路径
            search_url2 = f"/vod/search/wd/{encoded}/"
            if int(pg) > 1:
                search_url2 += f"?page={pg}"
            html_text = self._fetch(search_url2)

        if html_text:
            videos = self._parse_video_items(html_text)
            result["list"] = videos
            result["total"] = len(videos)

            page_info = re.search(r'第\s*\d+\s*/\s*(\d+)\s*页', html_text)
            if page_info:
                result["pagecount"] = int(page_info.group(1))

        return result
