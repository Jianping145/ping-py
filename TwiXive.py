"""TwiXive 1.0.1 - UBOX / TVBox Python Spider.

Import this file through UBOX Settings -> Configuration -> Python -> Local file.
Categories: 24 hours, 3 days, 7 days, trending, newest. Each page has 50 videos.
Search accepts an X/Twitter post URL, a TwiXive video URL, or an author keyword
(keyword search covers the current ranking snapshots, not all X posts).
Playback uses the ranking's media URL without requiring the main website.
Only Python standard libraries and the host's base.spider are required.
"""

import html
import json
import math
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlparse

from base.spider import Spider as BaseSpider


class _VideoPage(HTMLParser):
    def __init__(self, video_id):
        super().__init__(convert_charrefs=True)
        self.video_id = video_id
        self.video = {}
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.meta[attrs.get("property") or attrs.get("name", "")] = attrs.get("content", "")
        elif tag == "video" and attrs.get("data-watch-id") == self.video_id:
            self.video = {
                "id": self.video_id,
                "url": attrs.get("src", ""),
                "thumbnail": attrs.get("poster", ""),
                "title": attrs.get("aria-label", ""),
            }


class Spider(BaseSpider):
    HOST = "https://twixive.net"
    DATA = "https://data.twixive.net"
    API = "https://api.twixive.net"
    VERSION = "1.0.1"
    PAGE_SIZE = 50
    CACHE_SECONDS = 120
    MAX_ITEMS = 1000  # The site's own ranking limit.
    CATEGORIES = (
        ("day-1", "排行榜 · 24小时", "day", 1),
        ("day-3", "排行榜 · 3天", "day", 3),
        ("day-7", "排行榜 · 7天", "day", 7),
        ("trend", "趋势", "trend", None),
        ("new", "新着", "new", None),
    )
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    def getName(self):
        return "TwiXive 1.0.1"

    def init(self, extend=""):
        self.extend = extend
        self._snapshots = {}
        self._videos = {}

    def _ready(self):
        if not hasattr(self, "_snapshots"):
            self.init()

    def _headers(self):
        return {"User-Agent": self.UA, "Referer": self.HOST + "/", "Origin": self.HOST}

    def _get(self, url, params=None):
        response = self.fetch(url, params=params, headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response

    @staticmethod
    def _page(pg):
        try:
            return max(1, int(pg))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _media_url(url):
        parsed = urlparse(str(url or ""))
        return parsed.scheme == "https" and parsed.hostname == "video.twimg.com"

    def _remember(self, video):
        self._ready()
        video_id = str(video.get("id") or "")
        if not re.fullmatch(r"\d{1,25}", video_id) or not self._media_url(video.get("url")):
            return False
        self._videos.pop(video_id, None)
        self._videos[video_id] = (time.monotonic(), dict(video))
        while len(self._videos) > 5000:
            del self._videos[next(iter(self._videos))]
        return True

    def _snapshot(self, tid):
        self._ready()
        kind = next((row[2] for row in self.CATEGORIES if row[0] == tid), None)
        if kind is None:
            raise ValueError("未知的 TwiXive 分类")
        cached = self._snapshots.get(tid)
        if cached and time.monotonic() - cached[0] < self.CACHE_SECONDS:
            return cached[1]
        data = self._get(self.DATA + "/ranking/" + tid + ".json").json()
        if not isinstance(data, dict) or data.get("kind") != kind or not isinstance(data.get("items"), list):
            raise ValueError("TwiXive 列表接口已变化")
        self._snapshots[tid] = (time.monotonic(), data["items"][:self.MAX_ITEMS])
        return self._snapshots[tid][1]

    def _card(self, entry):
        video = entry.get("video", {})
        if not self._remember(video):
            return None
        author = video.get("author") or {}
        name = author.get("name") or author.get("username") or "TwiXive"
        handle = author.get("username") or video.get("authorHandle") or ""
        metrics = entry.get("metrics") or {}
        remarks = []
        if handle:
            remarks.append("@" + handle)
        if metrics.get("downloads") is not None:
            remarks.append("下载 " + str(metrics["downloads"]))
        return {
            "vod_id": str(video["id"]),
            "vod_name": str(video.get("title") or name + "的视频"),
            "vod_pic": str(video.get("thumbnail") or ""),
            "vod_remarks": " · ".join(remarks),
        }

    def _result(self, entries, page, total):
        cards = [self._card(entry) for entry in entries if isinstance(entry, dict)]
        return {"list": [card for card in cards if card], "page": page,
                "pagecount": max(1, math.ceil(total / self.PAGE_SIZE)),
                "limit": self.PAGE_SIZE, "total": total}

    def homeContent(self, filter):
        return {"class": [{"type_id": row[0], "type_name": row[1]} for row in self.CATEGORIES]}

    def homeVideoContent(self):
        return self.categoryContent("day-1", 1, False, {})

    def categoryContent(self, tid, pg, filter, extend):
        page = self._page(pg)
        category = next((row for row in self.CATEGORIES if row[0] == str(tid)), None)
        if category is None:
            return self._result([], page, 0)
        offset = (page - 1) * self.PAGE_SIZE
        try:
            entries = self._snapshot(category[0])
        except Exception:
            # The website also falls back to this paged API if its data CDN fails.
            if offset >= self.MAX_ITEMS:
                return self._result([], page, self.MAX_ITEMS)
            params = {"kind": category[2], "limit": self.PAGE_SIZE, "offset": offset}
            if category[3] is not None:
                params["days"] = category[3]
            data = self._get(self.API + "/api/rankings/video", params=params).json()
            if not isinstance(data, dict) or data.get("kind") != category[2] or not isinstance(data.get("items"), list):
                raise ValueError("TwiXive 列表接口已变化")
            entries = data["items"][:self.PAGE_SIZE]
            total = offset + len(entries)
            if len(entries) == self.PAGE_SIZE:
                total = min(self.MAX_ITEMS, total + 1)
            return self._result(entries, page, total)
        return self._result(entries[offset:offset + self.PAGE_SIZE], page, len(entries))

    def _video(self, video_id):
        self._ready()
        video_id = str(video_id)
        if not re.fullmatch(r"\d{1,25}", video_id):
            raise ValueError("无效的 TwiXive 视频 ID")
        cached = self._videos.get(video_id)
        if cached:
            return cached[1]
        # An imported favorite or history entry may contain only the video ID.
        # Recover its direct URL from the accessible data CDN before attempting
        # the main website, which can be unreachable on a device's network.
        for category in self.CATEGORIES:
            try:
                entries = self._snapshot(category[0])
            except Exception:
                continue
            for entry in entries:
                video = entry.get("video") or {}
                if str(video.get("id")) == video_id and self._remember(video):
                    return video
        parser = _VideoPage(video_id)
        parser.feed(self._get(self.HOST + "/video/" + video_id).text)
        video = parser.video
        if not video or not self._media_url(video.get("url")):
            raise ValueError("视频已失效，或站点暂时无法获取播放地址")
        video["title"] = video.get("title") or parser.meta.get("og:title", "TwiXive").removesuffix(" | TwiXive")
        video["thumbnail"] = video.get("thumbnail") or parser.meta.get("og:image", "")
        self._remember(video)
        return video

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        video = self._video(ids[0])
        author = video.get("author") or {}
        return {"list": [{
            "vod_id": str(video["id"]),
            "vod_name": str(video.get("title") or (author.get("name") or "TwiXive") + "的视频"),
            "vod_pic": str(video.get("thumbnail") or ""),
            "vod_actor": str(author.get("name") or author.get("username") or ""),
            "vod_content": str(video.get("text") or ""),
            "vod_play_from": "TwiXive直链",
            # Carry the resolved URL with the episode so playback survives a
            # Python instance reset and does not fetch twixive.net again.
            "vod_play_url": "播放$" + video["url"],
        }]}

    def _lookup(self, post_id):
        response = self.post(self.API + "/api/videos/lookup", json={"postId": post_id},
                             headers=self._headers(), timeout=25)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("videos"), list):
            raise ValueError("TwiXive 未返回视频")
        entries = []
        for video in data["videos"]:
            variants = [v for v in video.get("variants", []) if self._media_url(v.get("url"))]
            if not variants:
                continue
            best = max(variants, key=lambda v: (v.get("contentType") == "video/mp4", v.get("bitrate") or 0))
            entries.append({"video": {
                "id": str(video.get("videoId") or ""), "url": best["url"],
                "thumbnail": video.get("thumbnail", ""),
                "author": video.get("author") or data.get("author") or {},
                "postId": data.get("postId", post_id), "text": data.get("text", ""),
            }})
        return entries

    def searchContent(self, key, quick, pg="1"):
        query = html.unescape(str(key or "")).strip()
        page = self._page(pg)
        if not query:
            return self._result([], page, 0)
        url = urlparse(query)
        if url.scheme in ("http", "https"):
            if page != 1:
                return self._result([], page, 0)
            match = re.fullmatch(r"/video/(\d{1,25})/?", url.path)
            if url.hostname in ("twixive.net", "www.twixive.net") and match:
                return self._result([{"video": self._video(match.group(1))}], 1, 1)
            match = re.fullmatch(r"/(?:[A-Za-z0-9_]{1,15}|i/web)/status/(\d{1,25})/?", url.path)
            if url.hostname in ("x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com") and match:
                entries = self._lookup(match.group(1))
                return self._result(entries, 1, len(entries))
            return self._result([], page, 0)
        # No global keyword-search API is offered by TwiXive. Match author/IDs
        # across its five current snapshots, preserving the ranking order.
        needle = query.casefold().lstrip("@")
        if not needle:
            return self._result([], page, 0)
        found, entries = set(), []
        for category in self.CATEGORIES:
            for entry in self._snapshot(category[0]):
                video = entry.get("video") or {}
                video_id = str(video.get("id") or "")
                author = video.get("author") or {}
                fields = [video_id, video.get("postId", ""), video.get("title", ""),
                          author.get("name", ""), author.get("username", "")]
                if video_id not in found and any(needle in str(value).casefold() for value in fields):
                    found.add(video_id)
                    entries.append(entry)
        offset = (page - 1) * self.PAGE_SIZE
        return self._result(entries[offset:offset + self.PAGE_SIZE], page, len(entries))

    def playerContent(self, flag, id, vipFlags):
        # Accept direct episode URLs as well as old numeric episode IDs.
        url = str(id or "")
        if not self._media_url(url):
            url = self._video(url)["url"]
        # X's media CDN rejects a TwiXive Referer with HTTP 403. Keep API/page
        # headers separate from the media request headers.
        return {"parse": 0, "jx": 0, "url": url,
                "header": {"User-Agent": self.UA, "Referer": "https://x.com/"}}

    def isVideoFormat(self, url):
        return self._media_url(url)

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self._snapshots = {}
        self._videos = {}
