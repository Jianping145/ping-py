# -*- coding: utf-8 -*-
# 蜜桃仙子 lxxt001.top — 蜂蜜影视 Python 源
# 列表：/video/{cate}  分页：/video/{cate}/{page}
# 详情：/video/{id}.html  播放：JSON-LD contentUrl 内 m3u8

import re
import json
from urllib.parse import quote

from base.spider import Spider


class Spider(Spider):

    siteUrl = "https://www.lxxt001.top"
    UA = (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )

    # 导航分类（与站内一致）
    CATE = [
        ("21", "黑料泄密"),
        ("25", "AI短剧"),
        ("26", "黑料吃瓜"),
        ("27", "探花约炮"),
        ("28", "国产偷拍"),
        ("29", "国产自拍"),
        ("30", "国产主播"),
        ("31", "野外激情"),
        ("32", "短视频"),
        ("22", "传媒厂商"),
        ("33", "精东影业"),
        ("34", "麻豆传媒"),
        ("35", "皇家华人"),
        ("36", "糖心vlog"),
        ("37", "天美传媒"),
        ("38", "星空传媒"),
        ("39", "蜜桃传媒"),
        ("40", "性视界"),
        ("23", "无码AV"),
        ("41", "日本无码"),
        ("42", "日本有码"),
        ("43", "中文字幕"),
        ("44", "熟女人妻"),
        ("45", "制服诱惑"),
        ("46", "AV明星"),
        ("47", "强奸乱伦"),
        ("48", "巨乳美乳"),
        ("24", "素人AV"),
        ("49", "欧美精品"),
        ("50", "成人动漫"),
        ("51", "绿帽淫妻"),
        ("52", "SM调教"),
        ("53", "家庭乱伦"),
        ("54", "韩国伦理"),
        ("55", "百合女同"),
        ("56", "AI换脸"),
    ]

    def init(self, extend=""):
        return

    def getName(self):
        return "蜜桃仙子"

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return ".m3u8" in u or ".mp4" in u

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
            rsp = self.fetch(url, headers=self._headers())
            if rsp is None:
                return ""
            if hasattr(rsp, "text"):
                return rsp.text or ""
            if hasattr(rsp, "content"):
                try:
                    return rsp.content.decode("utf-8", errors="ignore")
                except Exception:
                    return str(rsp.content)
            return str(rsp)
        except Exception:
            return ""

    def homeContent(self, filter):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self.CATE]
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent(self.CATE[0][0], "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page <= 1:
            url = "%s/video/%s" % (self.siteUrl, tid)
        else:
            url = "%s/video/%s/%d" % (self.siteUrl, tid, page)
        html = self._get(url)
        videos = self._parse_list(html)
        pagecount = self._page_count(html, tid)
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
        }

    def detailContent(self, ids):
        vid = str(ids[0])
        if vid.startswith("http"):
            url = vid
        elif vid.endswith(".html"):
            url = self.siteUrl + "/video/" + vid.lstrip("/")
            if "/video/video/" in url:
                url = self.siteUrl + "/" + vid.lstrip("/")
        elif vid.isdigit():
            url = "%s/video/%s.html" % (self.siteUrl, vid)
        else:
            url = self.siteUrl + "/" + vid.lstrip("/")

        html = self._get(url)
        if not html:
            return {"list": []}

        title = self._meta(html, "og:title") or self._h1(html) or ""
        title = re.sub(r"\s*[-|].*?蜜桃.*$", "", title).strip()
        pic = self._meta(html, "og:image") or ""
        if not pic:
            m = re.search(r'"thumbnailUrl"\s*:\s*"([^"]+)"', html)
            if m:
                pic = m.group(1)

        play_from, play_url = self._parse_play(html)
        remarks = ""
        m = re.search(r"(\d{4}-\d{2}-\d{2})", html)
        if m:
            remarks = m.group(1)

        return {"list": [{
            "vod_id": vid,
            "vod_name": title or "未知",
            "vod_pic": pic,
            "vod_remarks": remarks,
            "vod_content": "",
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }]}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        url = "%s/search/video?q=%s" % (self.siteUrl, quote(key))
        if page > 1:
            url = "%s/search/video?q=%s&page=%d" % (self.siteUrl, quote(key), page)
        html = self._get(url)
        return {"list": self._parse_list(html)}

    def playerContent(self, flag, id, vipFlags):
        # id 已是直链 m3u8/mp4
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

    # ---------- 解析 ----------
    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos

        # 主策略：hp-video-card
        for m in re.finditer(
            r'<article class="hp-video-card[^"]*"[\s\S]*?</article>',
            html, re.I
        ):
            block = m.group(0)
            href = ""
            hm = re.search(r'href="(https?://[^"]+/video/\d+\.html|/video/\d+\.html)"', block)
            if not hm:
                hm = re.search(r'data-preview-detail="([^"]+)"', block)
            if hm:
                href = hm.group(1)
            if not href:
                continue
            # vod_id 用相对路径或纯 id
            mid = re.search(r'/video/(\d+)\.html', href)
            vod_id = mid.group(1) if mid else href
            if vod_id in seen:
                continue
            seen.add(vod_id)

            title = ""
            tm = re.search(r'<h3 class="hp-video-title"[^>]*>\s*<a[^>]*>([^<]+)</a>', block)
            if not tm:
                tm = re.search(r'title="([^"]+)"', block)
            if tm:
                title = tm.group(1).strip()

            pic = ""
            pm = re.search(r'data-preview-poster="([^"]+)"', block)
            if not pm:
                pm = re.search(r'data-original-src="([^"]+)"', block)
            if not pm:
                pm = re.search(r'<img[^>]+src="([^"]+)"', block)
            if pm:
                pic = pm.group(1)

            remarks = ""
            dm = re.search(r'<span>(\d{4}-\d{2}-\d{2})</span>', block)
            if dm:
                remarks = dm.group(1)

            if not title:
                continue
            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })
            if len(videos) >= 48:
                break

        # 兜底：纯链接
        if len(videos) < 3:
            for m in re.finditer(r'href="(?:https://www\.lxxt001\.top)?(/video/(\d+)\.html)"[^>]*title="([^"]+)"', html):
                vod_id = m.group(2)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": m.group(3).strip(),
                    "vod_pic": "",
                    "vod_remarks": "",
                })
        return videos

    def _page_count(self, html, tid):
        try:
            nums = re.findall(r'/video/%s/(\d+)' % re.escape(str(tid)), html)
            vals = [int(x) for x in nums if x.isdigit()]
            if vals:
                return min(max(vals), 999)
        except Exception:
            pass
        return 999

    def _parse_play(self, html):
        """从 JSON-LD contentUrl 或页面 m3u8 提取线路"""
        episodes = []  # [(name, url), ...]

        # 1) contentUrl: jpm3u8|||第01集$url#第02集$url
        m = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', html)
        if m:
            raw = m.group(1).replace("\\/", "/")
            if "|||" in raw:
                raw = raw.split("|||", 1)[1]
            for part in raw.split("#"):
                part = part.strip()
                if not part:
                    continue
                if "$" in part:
                    name, url = part.split("$", 1)
                else:
                    name, url = "正片", part
                url = url.strip()
                if url.startswith("http") and (".m3u8" in url or ".mp4" in url):
                    episodes.append((name.strip() or "正片", url))

        # 2) data-preview-url
        if not episodes:
            for um in re.finditer(r'data-preview-url="(https?://[^"]+\.m3u8[^"]*)"', html):
                episodes.append(("正片", um.group(1)))
                break

        # 3) 页面任意 m3u8
        if not episodes:
            for um in re.finditer(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html):
                u = um.group(1).rstrip("\\")
                if "google" in u:
                    continue
                episodes.append(("正片", u))
                if len(episodes) >= 10:
                    break

        if not episodes:
            return "蜜桃仙子", "正片$"

        # 单线路多集
        play_url = "#".join(["%s$%s" % (n, u) for n, u in episodes])
        return "蜜桃仙子", play_url

    def _meta(self, html, prop):
        m = re.search(
            r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]+)"' % re.escape(prop),
            html, re.I
        )
        if not m:
            m = re.search(
                r'<meta[^>]+content="([^"]+)"[^>]+(?:property|name)="%s"' % re.escape(prop),
                html, re.I
            )
        return m.group(1).strip() if m else ""

    def _h1(self, html):
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
        return ""

    def localProxy(self, param):
        return [200, "application/json", b""]
