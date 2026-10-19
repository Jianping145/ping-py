# coding=utf-8
# 玩偶姐姐 / nfyrkr.wojj4.beauty - 蜂蜜影视 spider
# 分类 /vodtype/{id}.html  分页 /vodtype/{id}-{page}.html
# 详情 /{id}.html  直链 m3u8 (const rawUrl = '...')
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
        self.siteUrl = "https://nfyrkr.wojj4.beauty"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.siteUrl + "/",
        }
        # type_id -> name (导航一致)
        self.classes = [
            {"type_name": "女神学生", "type_id": "21"},
            {"type_name": "美女直播", "type_id": "22"},
            {"type_name": "人妻系列", "type_id": "23"},
            {"type_name": "强奸乱伦", "type_id": "24"},
            {"type_name": "自拍偷拍", "type_id": "25"},
            {"type_name": "制服诱惑", "type_id": "26"},
            {"type_name": "巨乳系列", "type_id": "27"},
            {"type_name": "自慰系列", "type_id": "28"},
            {"type_name": "国产视频", "type_id": "29"},
            {"type_name": "无码视频", "type_id": "30"},
            {"type_name": "有码视频", "type_id": "31"},
            {"type_name": "中文字幕", "type_id": "32"},
            {"type_name": "日韩精品", "type_id": "33"},
            {"type_name": "欧美精品", "type_id": "34"},
            {"type_name": "动漫精品", "type_id": "35"},
            {"type_name": "三级伦理", "type_id": "36"},
            {"type_name": "热门", "type_id": "label/hot"},
            {"type_name": "最新", "type_id": "label/new"},
        ]

    def getName(self):
        return "玩偶姐姐"

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return self.categoryContent("21", 1, None, {})

    def _fetch(self, url, **kwargs):
        headers = dict(self.headers)
        if kwargs.get("headers"):
            headers.update(kwargs["headers"])
        try:
            r = self.fetch(url, headers=headers, timeout=kwargs.get("timeout", 20))
            text = r.text if hasattr(r, "text") else (r.content.decode("utf-8", "ignore") if hasattr(r, "content") else str(r))
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
        video_list = []
        seen = set()
        # 按 thumb-block 切块（页面嵌套不整齐，避免非贪婪 div 匹配失败）
        parts = html.split('class="thumb-block"')
        blocks = parts[1:] if len(parts) > 1 else []
        for chunk in blocks:
            hm = re.search(r'href="(/(\d+)\.html)"', chunk)
            if not hm:
                continue
            href = hm.group(1)
            vid = hm.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            tm = re.search(
                r'class="title"[^>]*>[\s\S]*?<a[^>]+(?:title="([^"]*)")?[^>]*>([^<]*)',
                chunk,
                re.I,
            )
            title = ""
            if tm:
                title = self._clean(tm.group(2) or tm.group(1) or "")
            if not title:
                tm2 = re.search(r'<a[^>]+href="/%s\.html"[^>]*>([^<]+)' % vid, chunk)
                if tm2:
                    title = self._clean(tm2.group(1))
            if not title:
                title = vid
            im = re.search(r'<img[^>]+src="([^"]+)"', chunk, re.I)
            pic = self._abs(im.group(1)) if im else ""
            dm = re.search(r'class="duration"[^>]*>([^<]+)', chunk, re.I)
            remarks = self._clean(dm.group(1)) if dm else ""
            video_list.append(
                {
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": format_remarks("玩偶姐姐", remarks),
                    "style": {"type": "rect", "ratio": 1.5},
                }
            )
        return video_list

    def _pagecount(self, html, tid, page):
        nums = []
        # /vodtype/21-522.html
        if tid.isdigit():
            nums = [int(x) for x in re.findall(r"/vodtype/%s-(\d+)\.html" % tid, html)]
        elif tid.startswith("label/"):
            lab = tid.split("/", 1)[1]
            nums = [int(x) for x in re.findall(r"/label/%s-(\d+)\.html" % re.escape(lab), html)]
        if nums:
            return max(max(nums), page)
        # search style /s/kw/page/N.html
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
            url = f"{self.siteUrl}/vodtype/21.html"

        res = self._fetch(url)
        html = res.get("text") or ""
        if not html or res.get("code") not in (0, 200):
            return {"page": page, "pagecount": 1, "limit": 0, "total": 0, "list": []}

        video_list = self._parse_list(html)
        pagecount = self._pagecount(html, tid if tid.isdigit() or tid.startswith("label/") else "21", page)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": len(video_list) or 30,
            "total": pagecount * max(len(video_list), 1),
            "list": video_list,
        }

    def detailContent(self, ids):
        vid = str(ids[0]).strip()
        if vid.startswith("http"):
            # 允许传完整 URL
            m = re.search(r"/(\d+)\.html", vid)
            vid = m.group(1) if m else vid
            url = ids[0] if str(ids[0]).startswith("http") else f"{self.siteUrl}/{vid}.html"
        else:
            url = f"{self.siteUrl}/{vid}.html"

        res = self._fetch(url)
        html = res.get("text") or ""
        if not html:
            return {"list": []}

        title = ""
        tm = re.search(r'<title>([^<]+)', html, re.I)
        if tm:
            title = self._clean(tm.group(1))
            title = re.sub(r"^正在播放[:：]?", "", title)
            title = re.sub(r"[-_].*玩偶姐姐.*$", "", title).strip()
            title = re.sub(r"[-_].*女神学生.*$", "", title).strip()

        pic = ""
        pm = re.search(r'<img[^>]+src="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', html, re.I)
        if pm:
            pic = pm.group(1)

        # 直链 m3u8
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

        # 描述
        desc = ""
        dm = re.search(r'class="[^"]*description[^"]*"[^>]*>([\s\S]*?)</div>', html, re.I)
        if dm:
            desc = self._clean(dm.group(1))[:300]

        vod = {
            "vod_id": vid,
            "vod_name": title or vid,
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_from": "玩偶姐姐",
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
            "limit": len(video_list) or 30,
            "total": pagecount * max(len(video_list), 1),
            "list": video_list,
        }

    def playerContent(self, flag, id, vipFlags):
        # id 可能是直链 m3u8 或 网页/详情 id
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
        # 重新取详情拿 m3u8
        if url.isdigit() or url.endswith(".html"):
            if url.isdigit():
                detail = f"{self.siteUrl}/{url}.html"
            else:
                detail = url if url.startswith("http") else f"{self.siteUrl}/{url.lstrip('/')}"
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
