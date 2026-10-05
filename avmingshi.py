# -*- coding: utf-8 -*-
# AV名湿 蜂蜜影视 / TVBox 兼容爬虫
# 苹果CMS (maccms) 正则直取 m3u8
#
# 站点结构：
# - 分类: /vod/type/id/{id}.html
# - 分页: /vod/type/id/{id}/page/{page}.html
# - 播放: /vod/play/id/{id}/sid/1/nid/1.html
# - 视频源: player_data / player_aaaa JSON 的 url 字段

import re
import json
from urllib.parse import quote
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "AV名湿"

    def init(self, extend=""):
        self.host = "https://fzn.avms2.motorcycles"
        self.base = "/cn/home/web/index.php"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        }
        # 分类（与站点一致）
        self.categories = [
            ("20", "主播网红"),
            ("21", "偷拍自拍"),
            ("22", "人妻熟女"),
            ("23", "强奸乱伦"),
            ("24", "制服丝袜"),
            ("25", "自慰变态"),
            ("26", "国产精品"),
            ("27", "亚洲情色"),
            ("28", "卡通动漫"),
            ("29", "三级伦理"),
            ("30", "欧美精品"),
            ("31", "无广告视频"),
            ("32", "东京指南"),
            ("33", "滋色园"),
        ]

    def homeContent(self, filter):
        classes = [{"type_id": cid, "type_name": name} for cid, name in self.categories]
        return {"class": classes}

    def homeVideoContent(self):
        # 首页推荐：拉第一个分类第 1 页
        try:
            return self.categoryContent("20", "1", False, {})
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        if pg <= 1:
            url = f"{self.host}{self.base}/vod/type/id/{tid}.html"
        else:
            url = f"{self.host}{self.base}/vod/type/id/{tid}/page/{pg}.html"

        html = self._get(url)
        videos = self._parse_video_list(html)
        has_next = self._has_next(html, pg)

        return {
            "list": videos,
            "page": pg,
            "pagecount": 999 if has_next else max(pg, 1),
            "limit": 24,
            "total": 9999 if has_next else len(videos),
        }

    def detailContent(self, ids):
        vod_id = str(ids[0]).strip()
        # 兼容已是完整 path 的情况
        if vod_id.startswith("http") or "/vod/" in vod_id:
            if vod_id.startswith("http"):
                url = vod_id
            else:
                url = self.host + (vod_id if vod_id.startswith("/") else "/" + vod_id)
            m = re.search(r"/id/(\d+)", vod_id)
            if m:
                vod_id = m.group(1)
        else:
            url = f"{self.host}{self.base}/vod/play/id/{vod_id}/sid/1/nid/1.html"

        html = self._get(url)
        play_info = self._extract_player_data(html)
        if not play_info and "/vod/detail/" not in url:
            # 再试详情页
            detail_url = f"{self.host}{self.base}/vod/detail/id/{vod_id}.html"
            html2 = self._get(detail_url)
            play_info = self._extract_player_data(html2) or play_info
            if html2:
                html = html2

        title = (play_info or {}).get("title") or self._pick_title(html) or vod_id
        cover = (play_info or {}).get("cover") or self._pick_cover(html) or ""
        play_url = (play_info or {}).get("url") or ""

        # 多线路：从页面里扫全部 m3u8 / mp4
        sources = []
        if play_url:
            sources.append(("直链", play_url))
        for m in re.finditer(
            r'(https?://[^"\'\s<>\\]+?\.(?:m3u8|mp4)[^"\'\s<>\\]*)',
            html or "",
            re.I,
        ):
            u = m.group(1).replace("\\/", "/")
            if not any(u == s[1] for s in sources):
                sources.append(("线路%d" % (len(sources) + 1), u))

        if not sources:
            return {"list": []}

        play_from = "$$$".join(name for name, _ in sources)
        play_urls = "$$$".join("正片$%s" % u for _, u in sources)

        return {
            "list": [
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_remarks": "",
                    "vod_content": "",
                    "vod_play_from": play_from,
                    "vod_play_url": play_urls,
                }
            ]
        }

    def playerContent(self, flag, id, vipFlags):
        url = id
        # 若传入的是站内 play 页，再解析一次
        if url and ("/vod/play/" in url or not self.isVideoFormat(url)):
            if not url.startswith("http"):
                url = self.host + (url if url.startswith("/") else self.base + "/" + url)
            html = self._get(url)
            info = self._extract_player_data(html)
            if info and info.get("url"):
                url = info["url"]
            else:
                m = re.search(
                    r'(https?://[^"\'\s<>\\]+?\.(?:m3u8|mp4)[^"\'\s<>\\]*)',
                    html or "",
                    re.I,
                )
                if m:
                    url = m.group(1).replace("\\/", "/")

        return {
            "parse": 0,
            "url": url,
            "header": json.dumps(
                {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": self.host + "/",
                },
                ensure_ascii=False,
            ),
        }

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg="1"):
        pg = int(pg) if pg else 1
        wd = quote(key)
        if pg <= 1:
            url = f"{self.host}{self.base}/vod/search.html?wd={wd}"
        else:
            url = f"{self.host}{self.base}/vod/search/page/{pg}.html?wd={wd}"
        html = self._get(url)
        videos = self._parse_video_list(html)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pg + 1 if len(videos) >= 10 else pg,
            "limit": len(videos),
            "total": len(videos),
        }

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return any(x in u for x in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    # ─────────────────── 内部工具 ───────────────────

    def _get(self, url):
        try:
            rsp = self.fetch(url, headers=self.header)
            if rsp is None:
                return ""
            text = getattr(rsp, "text", None)
            if text is not None:
                return text
            if isinstance(rsp, (bytes, bytearray)):
                return rsp.decode("utf-8", "ignore")
            return str(rsp)
        except Exception as e:
            print("[AV名湿] fetch error:", url, e)
            return ""

    def _parse_video_list(self, html):
        videos = []
        if not html:
            return videos

        # 方式1：col 卡片块
        blocks = re.split(r'<div class="col-sm-6 col-md-4 col-lg-4"[^>]*>', html)
        for block in blocks[1:]:
            item = self._parse_block(block)
            if item:
                videos.append(item)

        # 方式2：通用 play 链接
        if not videos:
            seen = set()
            for m in re.finditer(
                r'href="([^"]*?/vod/play/id/(\d+)[^"]*)"[^>]*>[\s\S]{0,400}?<img[^>]+src="([^"]+)"[\s\S]{0,400}?(?:video-title[^>]*>|title=")([^"<]+)',
                html,
                re.I,
            ):
                vod_id, img, title = m.group(2), m.group(3), m.group(4).strip()
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                videos.append(
                    {
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": img,
                        "vod_remarks": "",
                    }
                )

        # 方式3：只抽 id + 邻近标题
        if not videos:
            seen = set()
            for m in re.finditer(r'/vod/play/id/(\d+)', html):
                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                start = max(0, m.start() - 200)
                end = min(len(html), m.end() + 400)
                chunk = html[start:end]
                title_m = re.search(
                    r'(?:video-title[^>]*>|alt="|title=")([^"<]{2,80})',
                    chunk,
                )
                img_m = re.search(r'<img[^>]+src="([^"]+)"', chunk)
                videos.append(
                    {
                        "vod_id": vod_id,
                        "vod_name": title_m.group(1).strip() if title_m else vod_id,
                        "vod_pic": img_m.group(1) if img_m else "",
                        "vod_remarks": "",
                    }
                )

        return videos

    def _parse_block(self, block):
        link_m = re.search(
            r'href="(?:/cn/home/web/index\.php)?/vod/play/id/(\d+)[^"]*"',
            block,
        )
        if not link_m:
            link_m = re.search(r'/vod/play/id/(\d+)', block)
        if not link_m:
            return None
        vod_id = link_m.group(1)

        img_m = re.search(r'<img[^>]+src="([^"]+)"', block)
        img = img_m.group(1) if img_m else ""

        title_m = re.search(
            r'<span class="video-title[^"]*">([^<]+)</span>',
            block,
        )
        if not title_m:
            title_m = re.search(r'alt="([^"]+)"', block)
        if not title_m:
            title_m = re.search(r'title="([^"]+)"', block)
        title = title_m.group(1).strip() if title_m else vod_id

        dur_m = re.search(r'class="duration"[^>]*>\s*([^<]+?)\s*<', block)
        remarks = dur_m.group(1).strip() if dur_m else ""

        return {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": img,
            "vod_remarks": remarks,
        }

    def _extract_player_data(self, html):
        result = {}
        if not html:
            return result

        # player_data / player_aaaa / player_xx 常见写法
        patterns = [
            r'player_aaaa\s*=\s*(\{.+?\})\s*;',
            r'player_data\s*=\s*(\{.+?\})\s*;',
            r'var\s+player_[a-zA-Z0-9]+\s*=\s*(\{.+?\})\s*;',
        ]
        raw = None
        for p in patterns:
            m = re.search(p, html, re.S)
            if m:
                raw = m.group(1)
                break

        if raw:
            # 处理转义与截断
            try:
                raw_fix = raw.replace("\\/", "/")
                # 若正则因嵌套截断，尽量补全到最后一个 }
                data = json.loads(raw_fix)
            except Exception:
                try:
                    # 非贪婪失败时，从 url 字段硬抽
                    um = re.search(r'"url"\s*:\s*"([^"]+)"', raw)
                    data = {"url": um.group(1).replace("\\/", "/")} if um else {}
                except Exception:
                    data = {}
            url = (data.get("url") or data.get("link") or "").replace("\\/", "/")
            if url:
                result["url"] = url

        if not result.get("url"):
            m = re.search(
                r'"url"\s*:\s*"(https?://[^"]+\.(?:m3u8|mp4)[^"]*)"',
                html,
                re.I,
            )
            if m:
                result["url"] = m.group(1).replace("\\/", "/")

        title = self._pick_title(html)
        if title:
            result["title"] = title
        cover = self._pick_cover(html)
        if cover:
            result["cover"] = cover
        return result

    def _pick_title(self, html):
        if not html:
            return ""
        m = re.search(r'<title>([^<]+)</title>', html)
        if not m:
            return ""
        title = m.group(1)
        title = re.sub(r'^在线播放', '', title)
        title = re.sub(r'\s*第\d+集.*$', '', title)
        title = re.sub(r'\s*[-_|].*$', '', title)
        return title.strip()

    def _pick_cover(self, html):
        if not html:
            return ""
        m = re.search(r'property="og:image"[^>]+content="([^"]+)"', html)
        if m:
            return m.group(1)
        m = re.search(
            r'<img[^>]+class="[^"]*img-responsive[^"]*"[^>]+src="([^"]+)"',
            html,
            re.I,
        )
        if m:
            return m.group(1)
        m = re.search(
            r'<img[^>]+src="([^"]+)"[^>]+class="[^"]*img-responsive[^"]*"',
            html,
            re.I,
        )
        return m.group(1) if m else ""

    def _has_next(self, html, current_page):
        if not html:
            return False
        n = current_page + 1
        patterns = [
            rf"/page/{n}\.html",
            rf"page/{n}",
            r"下一页",
            r">\s*»\s*<",
            r'rel="next"',
        ]
        for p in patterns:
            if re.search(p, html, re.I):
                return True
        return False
