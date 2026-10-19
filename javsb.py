# coding=utf-8
# JAVSB - https://ayp.javsb3.ink/javsb/
# 蜂蜜影视 spider
# 分类 /vodtype/{id}.html  分页 /vodtype/{id}-{page}.html
# 详情 /{id}.html  直链 m3u8: const rawUrl = '...'
# 搜索 /s/{kw}.html  分页 /s/{kw}/page/{page}.html

import re
import sys
from urllib.parse import quote, urljoin

sys.path.append("..")
from base.spider import Spider as BaseSpider


def format_remarks(source, duration=""):
    if duration:
        return f"{source} | {duration}"
    return source


class Spider(BaseSpider):
    def init(self, extend=""):
        self.siteUrl = "https://ayp.javsb3.ink"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.siteUrl + "/",
        }
        self.classes = [
            {"type_name": "熟母少妇", "type_id": "20"},
            {"type_name": "网红直播", "type_id": "21"},
            {"type_name": "自拍偷拍", "type_id": "22"},
            {"type_name": "强奸乱伦", "type_id": "23"},
            {"type_name": "高清国产", "type_id": "24"},
            {"type_name": "韩国专区", "type_id": "25"},
            {"type_name": "日本有码", "type_id": "26"},
            {"type_name": "日本无码", "type_id": "27"},
            {"type_name": "欧美情色", "type_id": "28"},
            {"type_name": "动漫卡通", "type_id": "29"},
            {"type_name": "三级伦理", "type_id": "30"},
            {"type_name": "总排行", "type_id": "label/hot"},
            {"type_name": "月排行", "type_id": "label/hot_month"},
            {"type_name": "周排行", "type_id": "label/hot_week"},
            {"type_name": "日排行", "type_id": "label/hot_day"},
            {"type_name": "最新上传", "type_id": "label/new"},
        ]

    def getName(self):
        return "JAVSB"

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return self.categoryContent("26", 1, None, {})

    def _fetch(self, url, **kwargs):
        headers = dict(self.headers)
        if kwargs.get("headers"):
            headers.update(kwargs["headers"])
        try:
            r = self.fetch(url, headers=headers, timeout=kwargs.get("timeout", 20))
            text = (
                r.text
                if hasattr(r, "text")
                else (
                    r.content.decode("utf-8", "ignore")
                    if hasattr(r, "content")
                    else str(r)
                )
            )
            code = getattr(r, "status_code", 200)
            return {"code": code, "text": text, "err": ""}
        except Exception as e:
            return {"code": 0, "text": "", "err": str(e)}

    def _clean(self, s):
        if not s:
            return ""
        s = re.sub(r"<[^>]+>", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _abs(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http"):
            return u
        return urljoin(self.siteUrl + "/", u.lstrip("/"))

    def _parse_list(self, html):
        """列表项: <li>...<a href="/ID.html" title="标题"><img src="封面" class="imgPlay">"""
        video_list = []
        seen = set()
        # 优先匹配带 title 的 a+img
        for m in re.finditer(
            r'<a[^>]+href="(/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*>\s*<img[^>]+src="([^"]+)"',
            html,
            re.I,
        ):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            title = self._clean(m.group(3)) or vid
            pic = self._abs(m.group(4))
            video_list.append(
                {
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": format_remarks("JAVSB"),
                    "style": {"type": "rect", "ratio": 1.5},
                }
            )
        if video_list:
            return video_list
        # 回退：href + 附近 img
        for m in re.finditer(r'href="(/(\d+)\.html)"', html):
            vid = m.group(2)
            if vid in seen:
                continue
            start = max(0, m.start() - 50)
            end = min(len(html), m.end() + 400)
            chunk = html[start:end]
            im = re.search(r'<img[^>]+src="([^"]+)"', chunk, re.I)
            tm = re.search(r'title="([^"]+)"', chunk, re.I)
            title = self._clean(tm.group(1)) if tm else vid
            pic = self._abs(im.group(1)) if im else ""
            seen.add(vid)
            video_list.append(
                {
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": format_remarks("JAVSB"),
                    "style": {"type": "rect", "ratio": 1.5},
                }
            )
        return video_list

    def _pagecount(self, html, tid, page):
        nums = []
        if tid.isdigit():
            nums = [int(x) for x in re.findall(r"/vodtype/%s-(\d+)\.html" % tid, html)]
        elif str(tid).startswith("label/"):
            lab = str(tid).split("/", 1)[1]
            nums = [
                int(x)
                for x in re.findall(r"/label/%s-(\d+)\.html" % re.escape(lab), html)
            ]
        if nums:
            return max(max(nums), page)
        nums2 = [int(x) for x in re.findall(r"/page/(\d+)\.html", html)]
        if nums2:
            return max(max(nums2), page)
        if re.search(r"/page/%d\.html" % (page + 1), html) or re.search(
            r"-%d\.html" % (page + 1), html
        ):
            return page + 1
        return page

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        tid = str(tid).strip().strip("/")
        if tid.startswith("http"):
            url = tid
        elif tid.startswith("label/"):
            lab = tid.split("/", 1)[1]
            if page <= 1:
                url = f"{self.siteUrl}/label/{lab}.html"
            else:
                url = f"{self.siteUrl}/label/{lab}-{page}.html"
        elif tid.isdigit():
            if page <= 1:
                url = f"{self.siteUrl}/vodtype/{tid}.html"
            else:
                url = f"{self.siteUrl}/vodtype/{tid}-{page}.html"
        else:
            url = f"{self.siteUrl}/vodtype/26.html"

        res = self._fetch(url)
        html = res.get("text") or ""
        if not html or res.get("code") not in (0, 200):
            return {"page": page, "pagecount": 1, "limit": 0, "total": 0, "list": []}

        video_list = self._parse_list(html)
        key = tid if (tid.isdigit() or tid.startswith("label/")) else "26"
        pagecount = self._pagecount(html, key, page)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": len(video_list) or 36,
            "total": pagecount * max(len(video_list), 1),
            "list": video_list,
        }

    def detailContent(self, ids):
        vid = str(ids[0]).strip()
        if vid.startswith("http"):
            m = re.search(r"/(\d+)\.html", vid)
            if m:
                vid = m.group(1)
            url = ids[0] if str(ids[0]).startswith("http") else f"{self.siteUrl}/{vid}.html"
        else:
            url = f"{self.siteUrl}/{vid}.html"

        res = self._fetch(url)
        html = res.get("text") or ""
        if not html:
            return {"list": []}

        title = ""
        tm = re.search(r"<title>([^<]+)", html, re.I)
        if tm:
            title = self._clean(tm.group(1))
            title = re.sub(r"^正在播放[:：]?", "", title)
            title = re.sub(r"[-_].*JAVSB.*$", "", title, flags=re.I).strip()
            title = re.sub(r"[-_].*(日本有码|日本无码|高清国产).*$", "", title).strip()

        pic = ""
        pm = re.search(
            r'<img[^>]+src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
            html,
            re.I,
        )
        if pm:
            pic = pm.group(1)

        play_url = ""
        m1 = re.search(r"const\s+rawUrl\s*=\s*['\"]([^'\"]+)['\"]", html)
        if m1:
            play_url = m1.group(1).strip()
        if not play_url:
            m2 = re.search(r"""['"](https?://[^'"]+\.m3u8[^'"]*)['"]""", html)
            if m2:
                play_url = m2.group(1).strip()
        if not play_url:
            m3 = re.search(r"(https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*)", html)
            if m3:
                play_url = m3.group(1).strip()

        vod = {
            "vod_id": vid,
            "vod_name": title or vid,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "JAVSB",
            "vod_play_url": f"正片${play_url}" if play_url else f"网页${url}",
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        q = quote(key.strip())
        if page <= 1:
            url = f"{self.siteUrl}/s/{q}.html"
        else:
            url = f"{self.siteUrl}/s/{q}/page/{page}.html"
        res = self._fetch(url)
        html = res.get("text") or ""
        video_list = self._parse_list(html) if html else []
        pagecount = self._pagecount(html, "search", page)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": len(video_list) or 36,
            "total": pagecount * max(len(video_list), 1),
            "list": video_list,
        }

    def playerContent(self, flag, id, vipFlags):
        url = str(id).strip()
        if url.startswith("http") and (".m3u8" in url or ".mp4" in url):
            return {
                "parse": 0,
                "url": url,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.siteUrl + "/",
                },
            }
        if url.isdigit() or url.endswith(".html"):
            if url.isdigit():
                detail = f"{self.siteUrl}/{url}.html"
            else:
                detail = (
                    url
                    if url.startswith("http")
                    else f"{self.siteUrl}/{url.lstrip('/')}"
                )
            res = self._fetch(detail)
            html = res.get("text") or ""
            m1 = re.search(r"const\s+rawUrl\s*=\s*['\"]([^'\"]+)['\"]", html)
            if m1:
                return {
                    "parse": 0,
                    "url": m1.group(1).strip(),
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.siteUrl + "/",
                    },
                }
            m2 = re.search(r"""['"](https?://[^'"]+\.m3u8[^'"]*)['"]""", html)
            if m2:
                return {
                    "parse": 0,
                    "url": m2.group(1).strip(),
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.siteUrl + "/",
                    },
                }
            return {"parse": 1, "url": detail, "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}

    def localProxy(self, param):
        return None
