# coding=utf-8
# HQPorner 移动站 - https://m.hqporner.com/
# 蜂蜜影视 spider
# 列表 /hdporn/{page}  分类 /category/{slug}/{page}
# 详情 /hdporn/{id}-slug.html -> mydaddy.cc 多清晰度 mp4

import re
import sys
from urllib.parse import quote, urljoin

sys.path.append("..")
from base.spider import Spider as BaseSpider


def format_remarks(source, extra=""):
    if extra:
        return f"{source} | {extra}"
    return source


class Spider(BaseSpider):
    def init(self, extend=""):
        self.siteUrl = "https://m.hqporner.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Referer": self.siteUrl + "/",
        }
        # 常用分类（slug 与站内一致）
        self.classes = [
            {"type_name": "最新", "type_id": "latest"},
            {"type_name": "热门", "type_id": "top"},
            {"type_name": "1080p Porn", "type_id": "category/1080p-porn"},
            {"type_name": "Anal", "type_id": "category/anal-sex-hd"},
            {"type_name": "4k Porn", "type_id": "category/4k-porn"},
            {"type_name": "Milf", "type_id": "category/milf"},
            {"type_name": "Lesbian", "type_id": "category/lesbian"},
            {"type_name": "Creampie", "type_id": "category/creampie"},
            {"type_name": "60fps", "type_id": "category/60fps-porn"},
            {"type_name": "Big Tits", "type_id": "category/big-tits"},
            {"type_name": "Teen Porn", "type_id": "category/teen-porn"},
            {"type_name": "Pov", "type_id": "category/pov"},
            {"type_name": "Threesome", "type_id": "category/threesome"},
            {"type_name": "Asian", "type_id": "category/asian"},
            {"type_name": "Old And Young", "type_id": "category/old-and-young"},
            {"type_name": "Ebony", "type_id": "category/ebony"},
            {"type_name": "Big Ass", "type_id": "category/big-ass"},
            {"type_name": "Interracial", "type_id": "category/interracial"},
            {"type_name": "Mature", "type_id": "category/mature"},
            {"type_name": "Squirt", "type_id": "category/squirt"},
            {"type_name": "Casting", "type_id": "category/casting"},
            {"type_name": "Amateur", "type_id": "category/amateur"},
            {"type_name": "Sex Massage", "type_id": "category/porn-massage"},
            {"type_name": "Gangbang", "type_id": "category/gangbang"},
            {"type_name": "Stockings", "type_id": "category/stockings"},
            {"type_name": "Big Dick", "type_id": "category/big-dick"},
            {"type_name": "Latina", "type_id": "category/latina"},
            {"type_name": "Babe", "type_id": "category/babe"},
            {"type_name": "Group Sex", "type_id": "category/group-sex"},
            {"type_name": "Russian", "type_id": "category/russian"},
            {"type_name": "Masturbation", "type_id": "category/masturbation"},
            {"type_name": "Hairy Pussy", "type_id": "category/hairy-pussy"},
            {"type_name": "Uniforms", "type_id": "category/uniforms"},
            {"type_name": "Shemale", "type_id": "category/shemale"},
            {"type_name": "Blonde", "type_id": "category/blonde"},
            {"type_name": "Orgasm", "type_id": "category/orgasm"},
            {"type_name": "Pickup", "type_id": "category/pickup"},
            {"type_name": "Bdsm", "type_id": "category/bdsm"},
            {"type_name": "Sex Party", "type_id": "category/sex-parties"},
            {"type_name": "Public", "type_id": "category/public"},
            {"type_name": "Japanese", "type_id": "category/japanese-girls-porn"},
            {"type_name": "Redhead", "type_id": "category/redhead"},
            {"type_name": "Orgy", "type_id": "category/orgy"},
            {"type_name": "Fetish", "type_id": "category/fetish"},
            {"type_name": "Blowjob", "type_id": "category/blowjob"},
            {"type_name": "Small Tits", "type_id": "category/small-tits"},
            {"type_name": "Brunette", "type_id": "category/brunette"},
            {"type_name": "Undressing", "type_id": "category/undressing"},
            {"type_name": "Cumshot", "type_id": "category/cumshot"},
            {"type_name": "Outdoor", "type_id": "category/outdoor"},
            {"type_name": "Deepthroat", "type_id": "category/deepthroat"},
            {"type_name": "Bondage", "type_id": "category/bondage"},
            {"type_name": "Shaved Pussy", "type_id": "category/shaved-pussy"},
            {"type_name": "Bisexual", "type_id": "category/bisexual"},
            {"type_name": "Hentai", "type_id": "category/hentai"},
            {"type_name": "Handjob", "type_id": "category/handjob"},
            {"type_name": "Pussy Licking", "type_id": "category/pussy-licking"},
            {"type_name": "Fisting", "type_id": "category/fisting"},
            {"type_name": "Moaning", "type_id": "category/moaning"},
            {"type_name": "Vintage", "type_id": "category/vintage"},
            {"type_name": "Tattooed", "type_id": "category/tattooed"},
            {"type_name": "Beach", "type_id": "category/beach-porn"},
            {"type_name": "Vibrator", "type_id": "category/vibrator"},
            {"type_name": "Fingering", "type_id": "category/fingering"},
            {"type_name": "Squeezing Tits", "type_id": "category/squeezing-tits"},
            {"type_name": "Long Hair", "type_id": "category/long-hair"},
        ]

    def getName(self):
        return "HQPorner"

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return self.categoryContent("latest", 1, None, {})

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
        video_list = []
        seen = set()
        # 块结构: img-container > a[href=/hdporn/ID-slug.html] > img + 后面 h2 标题 + duration
        for m in re.finditer(
            r'<div class="img-container">\s*<a[^>]+href="(/hdporn/(\d+)[^"]*)"[^>]*>\s*'
            r'<img[^>]+src="([^"]+)"[^>]*(?:alt="([^"]*)")?[^>]*>',
            html,
            re.I,
        ):
            path, vid, pic, alt = m.group(1), m.group(2), m.group(3), m.group(4) or ""
            if vid in seen:
                continue
            seen.add(vid)
            # 标题优先后面 h2
            tail = html[m.end() : m.end() + 400]
            hm = re.search(r"<h2[^>]*>([^<]+)</h2>", tail, re.I)
            title = self._clean(hm.group(1)) if hm else self._clean(alt)
            if not title:
                title = vid
            dm = re.search(
                r'fa-clock-o[^>]*>[\s\S]*?</i>\s*([0-9hms:\s]+)',
                tail,
                re.I,
            )
            if not dm:
                dm = re.search(
                    r'class="meta_data"[^>]*>[\s\S]*?</i>\s*([^<]+)',
                    tail,
                    re.I,
                )
            duration = self._clean(dm.group(1)) if dm else ""
            video_list.append(
                {
                    "vod_id": path if path.startswith("/") else f"/hdporn/{vid}.html",
                    "vod_name": title,
                    "vod_pic": self._abs(pic),
                    "vod_remarks": format_remarks("HQP", duration),
                    "style": {"type": "rect", "ratio": 1.78},
                }
            )
        if video_list:
            return video_list
        # 回退：仅链接
        for m in re.finditer(
            r'href="(/hdporn/(\d+)[^"]*\.html)"[^>]*(?:title="([^"]*)")?',
            html,
            re.I,
        ):
            path, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            title = self._clean(m.group(3) or "")
            if not title:
                # slug
                sm = re.search(r"/hdporn/\d+-([^.]+)\.html", path)
                if sm:
                    title = sm.group(1).replace("_", " ")
            video_list.append(
                {
                    "vod_id": path,
                    "vod_name": title or vid,
                    "vod_pic": "",
                    "vod_remarks": format_remarks("HQP"),
                    "style": {"type": "rect", "ratio": 1.78},
                }
            )
        return video_list

    def _pagecount(self, html, page):
        nums = []
        # 仅分页：/category/xxx/2、/hdporn/2、/top/2（后面不能是 -slug）
        nums += [int(x) for x in re.findall(r"/category/[^\"/]+/(\d+)(?:[\"'/]|$)", html)]
        nums += [int(x) for x in re.findall(r"/hdporn/(\d+)(?:[\"'/]|$)", html)]
        nums += [int(x) for x in re.findall(r"/top/(\d+)(?:[\"'/]|$)", html)]
        nums = [n for n in nums if 1 <= n <= 2000]
        if nums:
            return max(max(nums), page)
        if re.search(r"/(?:category/[^\"/]+|hdporn|top)/%d(?:[\"'/]|$)" % (page + 1), html):
            return page + 1
        if re.search(r"next|›|»|>\s*Next", html, re.I) and page < 300:
            return page + 1
        return page

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        tid = str(tid).strip().strip("/")

        if tid in ("latest", "home", ""):
            url = (
                f"{self.siteUrl}/"
                if page <= 1
                else f"{self.siteUrl}/hdporn/{page}"
            )
        elif tid == "top":
            url = f"{self.siteUrl}/top" if page <= 1 else f"{self.siteUrl}/top/{page}"
        elif tid.startswith("category/"):
            base = tid  # category/milf
            url = (
                f"{self.siteUrl}/{base}"
                if page <= 1
                else f"{self.siteUrl}/{base}/{page}"
            )
        elif tid.startswith("http"):
            url = tid
        else:
            # 当作 category slug
            url = (
                f"{self.siteUrl}/category/{tid}"
                if page <= 1
                else f"{self.siteUrl}/category/{tid}/{page}"
            )

        res = self._fetch(url)
        html = res.get("text") or ""
        if not html or res.get("code") not in (0, 200):
            return {"page": page, "pagecount": 1, "limit": 0, "total": 0, "list": []}

        video_list = self._parse_list(html)
        pagecount = self._pagecount(html, page)
        # 首页分页较深，给个保底
        if tid in ("latest", "home", "") and pagecount < page + 1 and video_list:
            pagecount = max(page + 1, pagecount)
        return {
            "page": page,
            "pagecount": max(pagecount, page),
            "limit": len(video_list) or 36,
            "total": max(pagecount, page) * max(len(video_list), 1),
            "list": video_list,
        }

    def _extract_mydaddy(self, html):
        m = re.search(
            r'(?:src|href)=["\'](//mydaddy\.cc/video/[^"\']+|https?://mydaddy\.cc/video/[^"\']+)["\']',
            html,
            re.I,
        )
        if m:
            return self._abs(m.group(1))
        m2 = re.search(r"mydaddy\.cc/video/([a-z0-9]+)", html, re.I)
        if m2:
            return f"https://mydaddy.cc/video/{m2.group(1)}/"
        return ""

    def _parse_qualities(self, embed_html):
        """从 mydaddy 页面提取多清晰度 mp4，返回 [(name, url), ...] 高清优先"""
        found = {}
        for m in re.finditer(
            r'//([a-z0-9.]+/pubs/[^"\']+?/(\d{3,4})\.mp4)',
            embed_html,
            re.I,
        ):
            path, q = m.group(1), m.group(2)
            url = "https://" + path
            found[int(q)] = url
        # 也匹配完整 https
        for m in re.finditer(
            r'(https?://[^"\']+/pubs/[^"\']+?/(\d{3,4})\.mp4)',
            embed_html,
            re.I,
        ):
            url, q = m.group(1), int(m.group(2))
            found[q] = url
        if not found:
            # 任意 mp4
            for m in re.finditer(r'(https?:)?//([^"\']+\.mp4)', embed_html, re.I):
                url = ("https:" if not m.group(1) else m.group(1)) + "//" + m.group(2) if not m.group(1) else m.group(0)
                if m.group(1):
                    url = m.group(0)
                else:
                    url = "https://" + m.group(2)
                if "tile" in url or "preview" in url:
                    continue
                found[0] = url
        items = []
        for q in sorted(found.keys(), reverse=True):
            name = f"{q}p" if q else "正片"
            items.append((name, found[q]))
        return items

    def detailContent(self, ids):
        path = str(ids[0]).strip()
        if path.startswith("http"):
            url = path
        else:
            url = self._abs(path if path.startswith("/") else f"/hdporn/{path}")

        res = self._fetch(url)
        html = res.get("text") or ""
        if not html:
            return {"list": []}

        title = ""
        tm = re.search(r"<title>([^<]+)", html, re.I)
        if tm:
            title = self._clean(tm.group(1))
            title = re.sub(r"\s*[-|].*HQporner.*$", "", title, flags=re.I).strip()
        if not title:
            hm = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.I)
            if hm:
                title = self._clean(hm.group(1))

        pic = ""
        pm = re.search(
            r'<img[^>]+src="((?:https?:)?//[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
            html,
            re.I,
        )
        if pm:
            pic = self._abs(pm.group(1))

        # duration
        duration = ""
        dm = re.search(
            r'fa-clock-o[^>]*>[\s\S]*?</i>\s*([0-9hms:\s]+)',
            html,
            re.I,
        )
        if dm:
            duration = self._clean(dm.group(1))

        embed = self._extract_mydaddy(html)
        play_parts = []
        if embed:
            er = self._fetch(
                embed,
                headers={
                    "Referer": self.siteUrl + "/",
                    "User-Agent": self.headers["User-Agent"],
                },
            )
            ehtml = er.get("text") or ""
            quals = self._parse_qualities(ehtml)
            for name, u in quals:
                play_parts.append(f"{name}${u}")

        if not play_parts:
            # 嗅探回退：打开详情页
            play_parts.append(f"网页${url}")

        vod_id = path
        m_id = re.search(r"/hdporn/(\d+)", path)
        if m_id:
            vod_id = m_id.group(1)

        vod = {
            "vod_id": vod_id,
            "vod_name": title or vod_id,
            "vod_pic": pic,
            "vod_remarks": duration,
            "vod_content": "",
            "vod_play_from": "HQPorner",
            "vod_play_url": "#".join(play_parts)
            if len(play_parts) == 1
            else "#".join(play_parts),
        }
        # 多线路用 $$$ 分隔 from；多集用 # —— 这里同一线路多清晰度用 #
        if len(play_parts) > 1:
            vod["vod_play_url"] = "#".join(play_parts)
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        q = quote(key.strip())
        # 站内搜索 ?q=
        url = f"{self.siteUrl}/?q={q}"
        if page > 1:
            # 搜索分页不稳定，尝试 p=
            url = f"{self.siteUrl}/?q={q}&p={page}"
        res = self._fetch(url)
        html = res.get("text") or ""
        video_list = self._parse_list(html) if html else []
        pagecount = self._pagecount(html, page)
        if video_list and pagecount <= page:
            pagecount = page  # 搜索往往只有一页
        return {
            "page": page,
            "pagecount": max(pagecount, 1),
            "limit": len(video_list) or 36,
            "total": len(video_list),
            "list": video_list,
        }

    def playerContent(self, flag, id, vipFlags):
        url = str(id).strip()
        if url.startswith("http") and (".mp4" in url or ".m3u8" in url):
            return {
                "parse": 0,
                "url": url,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": "https://mydaddy.cc/",
                    "Origin": "https://mydaddy.cc",
                },
            }
        # 详情路径，重新解析
        if "hdporn" in url or url.isdigit():
            detail = (
                url
                if url.startswith("http")
                else self._abs(url if url.startswith("/") else f"/hdporn/{url}")
            )
            res = self._fetch(detail)
            html = res.get("text") or ""
            embed = self._extract_mydaddy(html)
            if embed:
                er = self._fetch(
                    embed,
                    headers={
                        "Referer": self.siteUrl + "/",
                        "User-Agent": self.headers["User-Agent"],
                    },
                )
                quals = self._parse_qualities(er.get("text") or "")
                if quals:
                    # 取最高清
                    best = quals[0][1]
                    return {
                        "parse": 0,
                        "url": best,
                        "header": {
                            "User-Agent": self.headers["User-Agent"],
                            "Referer": "https://mydaddy.cc/",
                            "Origin": "https://mydaddy.cc",
                        },
                    }
            return {"parse": 1, "url": detail, "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}

    def localProxy(self, param):
        return None
