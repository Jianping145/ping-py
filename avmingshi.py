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
        m = re.search(r"/id/(\d+)", vod_id)
        if m:
            vod_id = m.group(1)

        detail_url = f"{self.host}{self.base}/vod/detail/id/{vod_id}.html"
        play_url = f"{self.host}{self.base}/vod/play/id/{vod_id}/sid/1/nid/1.html"

        # 先详情拿标题封面，再播放页拿真实流（苹果CMS 常见）
        detail_html = self._get(detail_url)
        play_html = self._get(play_url)
        html = play_html or detail_html

        play_info = self._extract_player_data(play_html) or self._extract_player_data(detail_html)
        title = (play_info or {}).get("title") or self._pick_title(detail_html) or self._pick_title(play_html) or vod_id
        cover = (play_info or {}).get("cover") or self._pick_cover(detail_html) or self._pick_cover(play_html) or ""

        # 从详情页扫多集/多线路（sid/nid）
        episodes = self._parse_play_list(detail_html, vod_id)
        direct = (play_info or {}).get("url") or ""
        if direct and not episodes:
            episodes = [("正片", direct)]

        # 页面里直接暴露的 m3u8/mp4
        if not episodes:
            for m3 in re.finditer(
                r'(https?://[^"\'\s<>\\]+?\.(?:m3u8|mp4)(?:\?[^"\'\s<>\\]*)?)',
                html or "",
                re.I,
            ):
                u = m3.group(1).replace("\\/", "/")
                episodes.append(("正片", u))
                break

        # 仍没有直链：把播放页交给 playerContent 再解析（更稳）
        if not episodes:
            episodes = [("正片", play_url)]

        # 去重保序
        seen = set()
        uniq = []
        for name, u in episodes:
            if u in seen:
                continue
            seen.add(u)
            uniq.append((name, u))

        play_from = "直链"
        play_urls = "#".join("%s$%s" % (n, u) for n, u in uniq)

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
        url = (id or "").strip()
        headers = {
            "User-Agent": self.header["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
        }

        # 已是媒体地址
        if self.isVideoFormat(url):
            return {"parse": 0, "jx": 0, "url": url, "header": headers}

        # 数字 id → 拼播放页
        if re.fullmatch(r"\d+", url):
            url = f"{self.host}{self.base}/vod/play/id/{url}/sid/1/nid/1.html"

        # 相对路径
        if url.startswith("/"):
            url = self.host + url
        elif url and not url.startswith("http"):
            url = f"{self.host}{self.base}/vod/play/id/{url}/sid/1/nid/1.html"

        # 拉播放页解析真实地址
        if "/vod/play/" in url or "/vod/detail/" in url:
            html = self._get(url)
            info = self._extract_player_data(html)
            real = (info or {}).get("url") or ""
            if not real:
                m = re.search(
                    r'(https?://[^"\'\s<>\\]+?\.(?:m3u8|mp4)(?:\?[^"\'\s<>\\]*)?)',
                    html or "",
                    re.I,
                )
                if m:
                    real = m.group(1).replace("\\/", "/")
            if real:
                # 部分 CDN 要带播放页 Referer
                headers["Referer"] = url if url.startswith("http") else self.host + "/"
                return {"parse": 0, "jx": 0, "url": real, "header": headers}

        # 兜底：交给壳解析
        return {"parse": 1, "jx": 0, "url": url, "header": headers}

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

    def _decode_play_url(self, url, encrypt=0):
        """苹果CMS encrypt: 0明文 1escape 2base64"""
        if not url:
            return ""
        url = str(url).strip().replace("\\/", "/")
        try:
            enc = int(encrypt) if encrypt is not None else 0
        except Exception:
            enc = 0
        try:
            if enc == 1:
                from urllib.parse import unquote
                url = unquote(url)
            elif enc == 2:
                import base64
                url = base64.b64decode(url).decode("utf-8", "ignore")
        except Exception:
            pass
        return url.replace("\\/", "/")

    def _extract_player_data(self, html):
        result = {}
        if not html:
            return result

        # 优先从 url / encrypt 字段硬抽（避免 JSON 嵌套截断）
        um = re.search(r'"url"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        em = re.search(r'"encrypt"\s*:\s*(\d+)', html)
        if um:
            raw_url = um.group(1).encode("utf-8").decode("unicode_escape") if "\\u" in um.group(1) else um.group(1)
            raw_url = raw_url.replace("\\/", "/")
            enc = em.group(1) if em else 0
            decoded = self._decode_play_url(raw_url, enc)
            if decoded:
                result["url"] = decoded

        # 完整 player_aaaa JSON
        if not result.get("url"):
            patterns = [
                r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;',
                r'player_data\s*=\s*(\{[\s\S]*?\})\s*;',
                r'var\s+player_[a-zA-Z0-9]+\s*=\s*(\{[\s\S]*?\})\s*;',
            ]
            for p in patterns:
                m = re.search(p, html)
                if not m:
                    continue
                raw = m.group(1)
                data = None
                try:
                    data = json.loads(raw.replace("\\/", "/"))
                except Exception:
                    um2 = re.search(r'"url"\s*:\s*"((?:\\.|[^"\\])*)"', raw)
                    em2 = re.search(r'"encrypt"\s*:\s*(\d+)', raw)
                    if um2:
                        data = {
                            "url": um2.group(1).replace("\\/", "/"),
                            "encrypt": em2.group(1) if em2 else 0,
                        }
                if not data:
                    continue
                url = self._decode_play_url(
                    data.get("url") or data.get("link") or "",
                    data.get("encrypt", 0),
                )
                if url:
                    result["url"] = url
                    break

        if not result.get("url"):
            m = re.search(
                r'(https?://[^"\'\s<>\\]+?\.(?:m3u8|mp4)(?:\?[^"\'\s<>\\]*)?)',
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

    def _parse_play_list(self, html, vod_id):
        """从详情页解析播放列表 sid/nid"""
        episodes = []
        if not html:
            return episodes
        # /vod/play/id/{id}/sid/{sid}/nid/{nid}.html
        for m in re.finditer(
            rf'href="((?:[^"]*)/vod/play/id/{re.escape(str(vod_id))}/sid/(\d+)/nid/(\d+)[^"]*)"',
            html,
        ):
            href, sid, nid = m.group(1), m.group(2), m.group(3)
            if not href.startswith("http"):
                href = self.host + (href if href.startswith("/") else "/" + href)
            name = "第%s集" % nid
            # 邻近文本作集名
            start = max(0, m.start() - 20)
            end = min(len(html), m.end() + 80)
            chunk = re.sub(r"<[^>]+>", " ", html[start:end])
            tm = re.search(r"(第?\d+[集期话]|正片|高清|HD|全集)", chunk)
            if tm:
                name = tm.group(1)
            episodes.append((name, href))
        return episodes

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
