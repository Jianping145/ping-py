# -*- coding: utf-8 -*-
"""
麻豆APP — https://bve.mdapp3.homes/mdapp/
蜂蜜影视 Python 源（HTML 解析，MacCMS 风格）
分类: /vodtype/{id}.html  分页: /vodtype/{id}-{page}.html
详情: /{id}.html  播放: 页内 const rawUrl = '...m3u8'
搜索: /cn/home/web/index.php?m=vod-search&wd=
"""
import re
import sys
from urllib.parse import quote, unquote

sys.path.append("..")
from base.spider import Spider


class Spider(Spider):

    siteUrl = "https://bve.mdapp3.homes"
    UA = (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )

    CATE = [
        ("20", "无码视频"),
        ("21", "强奸乱伦"),
        ("22", "人妻巨乳"),
        ("23", "国产视频"),
        ("24", "制服师生"),
        ("25", "有码视频"),
        ("26", "调教变态"),
        ("27", "出轨偷拍"),
        ("28", "三级伦理"),
    ]

    def init(self, extend=""):
        return

    def getName(self):
        return "麻豆APP"

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return ".m3u8" in u or ".mp4" in u or ".ts" in u

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    def _headers(self):
        return {
            "User-Agent": self.UA,
            "Referer": self.siteUrl + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _get(self, url):
        try:
            if not url.startswith("http"):
                url = self.siteUrl + (url if url.startswith("/") else "/" + url)
            rsp = self.fetch(url, headers=self._headers())
            if rsp is None:
                return ""
            if hasattr(rsp, "text") and rsp.text:
                return rsp.text
            if hasattr(rsp, "content") and rsp.content:
                try:
                    return rsp.content.decode("utf-8", errors="ignore")
                except Exception:
                    return str(rsp.content)
            return str(rsp)
        except Exception:
            return ""

    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos

        # 主结构: lazyload 卡片
        for m in re.finditer(
            r'<a class="[^"]*vodlycms_list_thumb[^"]*lazyload"[^>]*>',
            html, re.I
        ):
            tag = m.group(0)
            href = re.search(r'href="([^"]+)"', tag)
            title = re.search(r'title="([^"]+)"', tag)
            pic = re.search(r'data-original="([^"]+)"', tag)
            if not href:
                continue
            vod_id = self._extract_id(href.group(1))
            if not vod_id or vod_id in seen:
                continue
            seen.add(vod_id)
            name = (title.group(1) if title else "").strip()
            if not name:
                continue
            poster = (pic.group(1) if pic else "").strip()
            remarks = ""
            # 相邻 HD 标记
            tail = html[m.end():m.end() + 200]
            if "HD" in tail or "text_right" in tail:
                remarks = "HD"
            videos.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": poster,
                "vod_remarks": remarks,
            })
            if len(videos) >= 60:
                break

        # 兜底: /数字.html + title
        if len(videos) < 5:
            for m in re.finditer(r'href="(/\d+\.html)"[^>]*title="([^"]+)"', html):
                vod_id = self._extract_id(m.group(1))
                if not vod_id or vod_id in seen:
                    continue
                seen.add(vod_id)
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": m.group(2).strip(),
                    "vod_pic": "",
                    "vod_remarks": "",
                })
                if len(videos) >= 60:
                    break
        return videos

    def _extract_id(self, href):
        href = unquote(str(href or ""))
        m = re.search(r"/(\d+)\.html", href)
        if m:
            return m.group(1)
        m = re.search(r"vodplay/(\d+)", href)
        if m:
            return m.group(1)
        m = re.search(r"id[=/](\d+)", href)
        if m:
            return m.group(1)
        return ""

    def _page_count(self, html, tid):
        try:
            nums = re.findall(r"/vodtype/%s-(\d+)\.html" % re.escape(str(tid)), html)
            vals = [int(x) for x in nums if str(x).isdigit()]
            if vals:
                return min(max(vals), 999)
        except Exception:
            pass
        return 999

    def _parse_play(self, html):
        if not html:
            return "麻豆APP", "正片$"
        episodes = []
        # const rawUrl = '...'
        for m in re.finditer(r"""const\s+rawUrl\s*=\s*['"]([^'"]+)['"]""", html):
            u = m.group(1).strip()
            if u.startswith("http") and (".m3u8" in u or ".mp4" in u):
                episodes.append(("正片", u))
        # 其它 m3u8
        if not episodes:
            for m in re.finditer(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html):
                u = m.group(1).rstrip("\\;,")
                if "google" in u:
                    continue
                episodes.append(("正片", u))
                if len(episodes) >= 5:
                    break
        # player_aaaa
        if not episodes:
            m = re.search(r'"url"\s*:\s*"((?:https?:)?[^"]+\.m3u8[^"]*)"', html)
            if m:
                u = m.group(1).replace("\\/", "/")
                if u.startswith("//"):
                    u = "https:" + u
                episodes.append(("正片", u))

        if not episodes:
            return "麻豆APP", "正片$"
        play_url = "#".join(["%s$%s" % (n, u) for n, u in episodes])
        return "麻豆APP", play_url

    # ---------- 接口 ----------
    def homeContent(self, filter):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self.CATE]
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent("20", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        tid = str(tid).strip()
        if page <= 1:
            url = "%s/vodtype/%s.html" % (self.siteUrl, tid)
        else:
            url = "%s/vodtype/%s-%d.html" % (self.siteUrl, tid, page)
        html = self._get(url)
        videos = self._parse_list(html)
        pagecount = self._page_count(html, tid)
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": 36,
            "total": pagecount * 36,
        }

    def detailContent(self, ids):
        vid = str(ids[0])
        vod_id = self._extract_id(vid) or vid
        if vod_id.isdigit():
            url = "%s/%s.html" % (self.siteUrl, vod_id)
        else:
            url = vid if vid.startswith("http") else self.siteUrl + "/" + vid.lstrip("/")
        html = self._get(url)
        if not html:
            return {"list": []}

        title = ""
        m = re.search(r'<title>([^<]+)', html)
        if m:
            title = re.sub(r"\s*[-|].*?在线.*$", "", m.group(1)).strip()
            title = re.sub(r"\s*[-|].*?麻豆.*$", "", title).strip()
        if not title:
            m = re.search(r'title="([^"]+)"', html)
            if m:
                title = m.group(1).strip()

        pic = ""
        m = re.search(r'data-original="(https?://[^"]+)"', html)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, re.I)
            if m:
                pic = m.group(1)

        play_from, play_url = self._parse_play(html)
        return {"list": [{
            "vod_id": vod_id,
            "vod_name": title or vod_id,
            "vod_pic": pic,
            "vod_remarks": "",
            "vod_content": "",
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }]}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        # 优先用站内搜索
        url = "%s/cn/home/web/index.php?m=vod-search&wd=%s" % (self.siteUrl, quote(key))
        if page > 1:
            url += "&page=%d" % page
        html = self._get(url)
        videos = self._parse_list(html)
        if not videos:
            # 备用 MacCMS 搜索
            url2 = "%s/index.php/vod/search.html?wd=%s" % (self.siteUrl, quote(key))
            html2 = self._get(url2)
            videos = self._parse_list(html2)
        return {"list": videos, "page": page, "pagecount": page + 1 if videos else 1}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": {
                "User-Agent": self.UA,
                "Referer": self.siteUrl + "/",
                "Origin": self.siteUrl,
            },
        }

    def localProxy(self, param):
        return [200, "text/plain", b""]
