# -*- coding: utf-8 -*-
# 蜂蜜影视 / FongMi 可用 Python 爬虫
# 站点：https://javhdz.today/ （备用域名，无需代理）
# 分页规则：
#   recent/popular → ?ajax=browse_videos&page=N
#   普通分类 → 第1页 ?ajax=1；第2页起 /recent/N/?ajax=1
#   channel/xxx → ?page=N&ajax=1

import re
import json
import time
from urllib.parse import quote

try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider:
        def __init__(self):
            pass

class Spider(BaseSpider):
    def init(self, extend=""):
        # 使用备用域名（无需代理）
        self.host = "https://javhdz.today"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        self.timeout = 12

    def getName(self):
        return "JavHD"

    def isVideoFormat(self, url):
        return any(x in str(url).lower() for x in [".m3u8", ".mp4", ".flv", "video"])

    def manualVideoCheck(self):
        return True

    def homeContent(self, filter):
        result = {}
        result["class"] = [
            {"type_name": "最新上传", "type_id": "recent"},
            {"type_name": "今日热门", "type_id": "popular/today"},
            {"type_name": "本周热门", "type_id": "popular/week"},
            {"type_name": "本月热门", "type_id": "popular/month"},
            {"type_name": "FC2PPV", "type_id": "channel/fc2ppv"},
            {"type_name": "无码", "type_id": "uncensored-jav"},
            {"type_name": "马赛克破解", "type_id": "reducing-mosaic"},
            {"type_name": "英文字幕", "type_id": "jav-sub"},
            {"type_name": "中文字幕", "type_id": "chinese-subtitle"},
            {"type_name": "中出", "type_id": "creampie"},
            {"type_name": "巨乳", "type_id": "big-tits"},
            {"type_name": "业余", "type_id": "amateur"},
            {"type_name": "人妻", "type_id": "married-woman"},
            {"type_name": "美少女", "type_id": "beautiful-girl"},
            {"type_name": "熟女", "type_id": "mature-woman"},
            {"type_name": "绿帽", "type_id": "cuckold"},
            {"type_name": "潮吹", "type_id": "squirting"},
            {"type_name": "淫乱", "type_id": "nasty"},
            {"type_name": "硬核", "type_id": "hardcore"},
            {"type_name": "发行日", "type_id": "releaseday"},
        ]
        result["filters"] = {}
        return result

    def homeVideoContent(self):
        return self.categoryContent("recent", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        result = {
            "list": [],
            "page": int(pg) if str(pg).isdigit() else 1,
            "pagecount": 999,
            "limit": 28,
            "total": 999999
        }
        try:
            page = int(pg) if str(pg).isdigit() else 1
            tid = tid.strip("/") if isinstance(tid, str) else tid
            if tid.startswith("http"):
                base = tid.rstrip("/")
            else:
                base = f"{self.host}/{tid}"

            tid_low = tid.lower()
            videos = []
            candidates = []

            # 1) recent / popular / releaseday：?ajax=browse_videos&page=N
            if any(x in tid_low for x in ["recent", "popular", "releaseday"]) and "channel/" not in tid_low:
                candidates = [
                    f"{base}/?ajax=browse_videos&page={page}",
                    f"{base}/?ajax=1&page={page}",
                ]
            # 2) channel/xxx：?page=N&ajax=1
            elif tid_low.startswith("channel/"):
                if page <= 1:
                    candidates = [f"{base}/?ajax=1", f"{base}/?ajax=browse_videos&page=1"]
                else:
                    candidates = [
                        f"{base}/?page={page}&ajax=1",
                        f"{base}/?ajax=browse_videos&page={page}",
                    ]
            # 3) 普通分类（无码/字幕/巨乳等）：第1页 ?ajax=1；第2页起 /recent/N/?ajax=1
            else:
                if page <= 1:
                    candidates = [
                        f"{base}/?ajax=1",
                        f"{base}/?ajax=1&page=1",
                        f"{base}/?ajax=browse_videos&page=1",
                    ]
                else:
                    candidates = [
                        f"{base}/recent/{page}/?ajax=1",
                        f"{base}/recent/{page}/?ajax=browse_videos",
                        f"{base}/?ajax=browse_videos&page={page}",
                    ]

            for ajax_url in candidates:
                html_fragment = self.get_ajax_html(ajax_url)
                if not html_fragment:
                    continue
                videos = self.parse_video_list(html_fragment)
                if videos:
                    break

            result["list"] = videos
            if not videos and page > 1:
                result["pagecount"] = page - 1
            elif videos and len(videos) < 15:
                result["pagecount"] = page
        except Exception as e:
            print(f"[categoryContent] error: {e}")
        return result

    def get_ajax_html(self, url):
        """请求 ajax 接口并返回 html 片段（兼容 JSON / 直接 HTML）"""
        try:
            import requests
            r = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)
            if r.status_code != 200:
                print(f"ajax status {r.status_code} url={url}")
                return ""
            text = r.text.strip()
            if text.startswith("{"):
                data = json.loads(text)
                if data.get("html"):
                    return data["html"]
                return ""
            # channel 等页面可能直接返回带视频的 HTML
            if "thumbnail" in text or "video-thumb" in text or re.search(r'href="/\d+/', text):
                return text
            return ""
        except Exception as e:
            print(f"get_ajax_html error: {e}")
            return ""

    def parse_video_list(self, html):
        """从 ajax 返回的 html 片段解析视频列表"""
        videos = []
        pattern = re.compile(
            r'<a\s+href="(/\d+/[^"]+)"[^>]*?title="([^"]*)"[^>]*?class="[^"]*thumbnail[^"]*"[^>]*>.*?<img[^>]+src="(https?://[^"]+)"',
            re.S | re.I
        )
        for m in pattern.finditer(html):
            href, title, pic = m.group(1), m.group(2), m.group(3)
            title = self.clean_title(title)
            if not title or len(title) < 2:
                continue
            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": ""
            })

        # 宽松兜底
        if not videos:
            hrefs = re.findall(r'href="(/\d+/[^"]+)"', html)
            titles = re.findall(r'title="([^"]+)"', html)
            pics = re.findall(r'src="(https://pics\.javhd\.today[^"]+)"', html)
            for i, href in enumerate(hrefs):
                title = titles[i] if i < len(titles) else href.split("/")[-2]
                pic = pics[i] if i < len(pics) else ""
                videos.append({
                    "vod_id": href,
                    "vod_name": self.clean_title(title),
                    "vod_pic": pic,
                    "vod_remarks": ""
                })

        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

    def detailContent(self, ids):
        result = {"list": []}
        try:
            import base64
            from urllib.parse import urljoin

            url = ids[0]
            if not url.startswith("http"):
                url = self.host + url
            html = self.fetch(url)
            if not html:
                return result

            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
            title = self.clean_title(title_match.group(1)) if title_match else "未知标题"

            pic_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
            if not pic_match:
                pic_match = re.search(r'<img[^>]+src="(https://pics\.javhd[z]?\.today[^"]+)"', html)
            pic = pic_match.group(1) if pic_match else ""

            desc = ""
            dm = re.search(r'Release Day:\s*([\d\-]+)', html)
            if dm:
                desc = "上映: " + dm.group(1)

            # 解析 data-embeds（base64 JSON 数组，每组是多个备用 embed 地址）
            play_from_list = []
            play_url_list = []
            seen_names = set()

            # 同时匹配 data-embeds + data-name 两种属性顺序
            pattern = re.compile(
                r'data-embeds="([^"]+)"[^>]*?data-name="([^"]+)"|data-name="([^"]+)"[^>]*?data-embeds="([^"]+)"',
                re.I | re.S
            )
            for m in pattern.finditer(html):
                emb_b64 = m.group(1) or m.group(4)
                name = (m.group(2) or m.group(3) or "线路").strip()
                if not emb_b64 or name in seen_names:
                    continue
                try:
                    embeds = json.loads(base64.b64decode(emb_b64).decode("utf-8", errors="ignore"))
                except Exception:
                    continue
                if not embeds or not isinstance(embeds, list):
                    continue
                seen_names.add(name)
                # 取该线路第一个 embed 地址，交给 playerContent 解析 m3u8
                play_from_list.append(name)
                play_url_list.append(f"{name}${embeds[0]}")

            # 兜底
            if not play_from_list:
                play_from_list = ["播放"]
                play_url_list = [f"播放${url}"]

            result["list"].append({
                "vod_id": ids[0],
                "vod_name": title,
                "vod_pic": pic,
                "type_name": "JAV",
                "vod_year": "",
                "vod_area": "日本",
                "vod_remarks": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": desc,
                "vod_play_from": "$$$".join(play_from_list),
                "vod_play_url": "$$$".join(play_url_list)
            })
        except Exception as e:
            print(f"[detailContent] error: {e}")
        return result

    def playerContent(self, flag, id, vipFlags):
        """
        id 可能是：
        1) stream.javhdz.today/embed.php?p=xxx  （来自 data-embeds）
        2) 详情页地址（兜底）
        目标：解析出真正的 m3u8 直链，parse=0 直接播放
        """
        from urllib.parse import urljoin
        headers = {
            "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"),
            "Referer": self.host + "/",
        }
        result = {"parse": 0, "playUrl": "", "url": "", "header": headers}
        try:
            url = id if id.startswith("http") else self.host + id

            # 已经是 m3u8
            if ".m3u8" in url:
                result["url"] = url
                result["parse"] = 0
                return result

            # 情况1：embed.php —— 页面内含 /universal-stream-hls/.../playlist.m3u8
            if "embed.php" in url or "stream" in url and "javhd" in url:
                html = self.fetch(url)
                if html:
                    # 相对或绝对 m3u8
                    m3u8s = re.findall(r'["\']([^"\']*m3u8[^"\']*)["\']', html)
                    for p in m3u8s:
                        full = urljoin(url, p)
                        if "universal-stream" in full or full.endswith(".m3u8"):
                            result["url"] = full
                            result["parse"] = 0
                            result["header"] = {
                                "User-Agent": headers["User-Agent"],
                                "Referer": url,
                            }
                            return result
                    # 也尝试完整 https m3u8
                    abs_m3u8 = re.search(r'(https?://[^"\'\s>]+\.m3u8[^"\'\s>]*)', html)
                    if abs_m3u8:
                        result["url"] = abs_m3u8.group(1)
                        result["parse"] = 0
                        return result

            # 情况2：详情页 —— 先解 data-embeds，再递归取 m3u8
            if "javhd" in url and "embed.php" not in url:
                html = self.fetch(url)
                if html:
                    import base64
                    m = re.search(r'data-embeds="([^"]+)"', html)
                    if m:
                        try:
                            embeds = json.loads(base64.b64decode(m.group(1)).decode("utf-8", errors="ignore"))
                            if embeds:
                                # 递归用第一个 embed
                                return self.playerContent(flag, embeds[0], vipFlags)
                        except Exception:
                            pass

            # 兜底嗅探
            result["url"] = url
            result["parse"] = 1
        except Exception as e:
            print(f"[playerContent] error: {e}")
            result["url"] = id
            result["parse"] = 1
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg="1"):
        result = {"list": [], "page": pg, "pagecount": 50, "limit": 28, "total": 999}
        try:
            page = int(pg) if str(pg).isdigit() else 1
            url = f"{self.host}/search/video/?s={quote(key)}&ajax=browse_videos&page={page}"
            html_fragment = self.get_ajax_html(url)
            if not html_fragment:
                url2 = f"{self.host}/search/video/?s={quote(key)}"
                html_fragment = self.fetch(url2)
            if html_fragment:
                result["list"] = self.parse_video_list(html_fragment)
        except Exception as e:
            print(f"[search] error: {e}")
        return result

    def fetch(self, url, retry=2):
        """普通页面请求（详情页用）"""
        headers = dict(self.headers)
        headers.pop("X-Requested-With", None)
        for i in range(retry + 1):
            try:
                import requests
                r = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
                if r.status_code == 200:
                    return r.text
            except Exception as e:
                print(f"fetch fail {i}: {e}")
                time.sleep(0.8)
        return ""

    def clean_title(self, title):
        if not title:
            return ""
        title = re.sub(r'<[^>]+>', '', title)
        # 常见 HTML 实体
        title = title.replace("&#039;", "'").replace("&amp;", "&").replace("&quot;", '"')
        title = title.replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    def localProxy(self, param):
        return [200, "text/plain", ""]
