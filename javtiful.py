# coding=utf-8
# Javtiful - https://javtiful.com/zh/main
# 蜂蜜影视 spider
# 列表 /zh/videos?page=N  /zh/censored|uncensored|reducing-mosaic?page=N
# 分类 /zh/category/{slug}?page=N
# 详情 /zh/video/{id}/{slug} -> POST /zh/video/{id}/playback  ticket=...

import json
import re
import sys
from urllib.parse import quote, urljoin, unquote

sys.path.append("..")
from base.spider import Spider as BaseSpider


def format_remarks(source, extra=""):
    if extra:
        return f"{source} | {extra}"
    return source


class Spider(BaseSpider):
    def init(self, extend=""):
        self.siteUrl = "https://javtiful.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.siteUrl + "/zh/main",
        }
        # 主导航 + 分类页全部标签
        self.classes = [
            {"type_name": "最新", "type_id": "zh/videos"},
            {"type_name": "有码", "type_id": "zh/censored"},
            {"type_name": "无码", "type_id": "zh/uncensored"},
            {"type_name": "去码", "type_id": "zh/reducing-mosaic"},
            {"type_name": "为本周热门", "type_id": "zh/videos?sort=popular_week"},
            {"type_name": "最多观看", "type_id": "zh/videos?sort=most_viewed"},
            {"type_name": "最多点赞", "type_id": "zh/videos?sort=most_liked"},
            {"type_name": "厂牌", "type_id": "zh/channels"},
            {"type_name": "女优", "type_id": "zh/actresses"},
            {"type_name": "女调查员", "type_id": "zh/category/女調查員"},
            {"type_name": "Chinese AV", "type_id": "zh/category/chinese-av"},
            {"type_name": "女老板", "type_id": "zh/category/女老板"},
            {"type_name": "成熟的女人", "type_id": "zh/category/成熟的女人"},
            {"type_name": "角色扮演", "type_id": "zh/category/角色扮演"},
            {"type_name": "业余爱好者", "type_id": "zh/category/业余爱好者"},
            {"type_name": "管家", "type_id": "zh/category/管家"},
            {"type_name": "护士", "type_id": "zh/category/护士"},
            {"type_name": "女学生", "type_id": "zh/category/女学生"},
            {"type_name": "学校女生", "type_id": "zh/category/学校女生"},
            {"type_name": "办公室女郎", "type_id": "zh/category/办公室女郎"},
            {"type_name": "嫂子", "type_id": "zh/category/嫂子"},
            {"type_name": "催眠", "type_id": "zh/category/催眠"},
            {"type_name": "美丽的女孩", "type_id": "zh/category/美丽的女孩"},
            {"type_name": "肥胖妇女", "type_id": "zh/category/肥胖妇女"},
            {"type_name": "戏剧", "type_id": "zh/category/戏剧"},
            {"type_name": "已婚妇女", "type_id": "zh/category/已婚妇女"},
            {"type_name": "阿姨", "type_id": "zh/category/阿姨"},
            {"type_name": "女教师", "type_id": "zh/category/女教师"},
            {"type_name": "不忠行为", "type_id": "zh/category/不忠行为"},
            {"type_name": "大乳房", "type_id": "zh/category/大乳房"},
            # 厂牌频道
            {"type_name": "FC2PPV", "type_id": "zh/channel/fc2ppv"},
            {"type_name": "Madonna", "type_id": "zh/channel/madonna"},
            {"type_name": "Moodyz", "type_id": "zh/channel/moodyz"},
            {"type_name": "S1", "type_id": "zh/channel/s1-no1-style"},
            {"type_name": "SOD", "type_id": "zh/channel/sod-create"},
            {"type_name": "Idea Pocket", "type_id": "zh/channel/idea-pocket"},
            {"type_name": "Attackers", "type_id": "zh/channel/attackers"},
            {"type_name": "Prestige", "type_id": "zh/channel/prestige"},
            {"type_name": "Hunter", "type_id": "zh/channel/hunter"},
            {"type_name": "Faleno", "type_id": "zh/channel/faleno"},
            {"type_name": "Venus", "type_id": "zh/channel/venus"},
            {"type_name": "DAS", "type_id": "zh/channel/das"},
        ]

    def getName(self):
        return "Javtiful"

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url or "fast-stream.jav.si" in url))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return self.categoryContent("zh/videos", 1, None, {})

    def _fetch(self, url, method="GET", data=None, headers=None, **kwargs):
        h = dict(self.headers)
        if headers:
            h.update(headers)
        timeout = kwargs.get("timeout", 20)
        try:
            if method.upper() == "POST":
                if hasattr(self, "post"):
                    r = self.post(url, data=data, headers=h, timeout=timeout)
                else:
                    r = self.fetch(url, headers=h, data=data, timeout=timeout)
            else:
                r = self.fetch(url, headers=h, timeout=timeout)
            text = (
                r.text
                if hasattr(r, "text")
                else (
                    r.content.decode("utf-8", "ignore")
                    if hasattr(r, "content")
                    else str(r)
                )
            )
            return {"code": getattr(r, "status_code", 200), "text": text, "err": ""}
        except Exception as e1:
            try:
                import urllib.request
                body = data.encode("utf-8") if isinstance(data, str) else data
                req = urllib.request.Request(url, data=body, headers=h, method=method.upper())
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return {"code": resp.status, "text": resp.read().decode("utf-8", "ignore"), "err": ""}
            except Exception as e2:
                return {"code": 0, "text": "", "err": str(e1) + " | " + str(e2)}

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
        # 以 video-card 为单位切分
        parts = re.split(r'class="video-card(?:\s|"|$)', html)
        for chunk in parts[1:]:
            hm = re.search(r'href="(/zh/video/(\d+)/[^"]+)"', chunk)
            if not hm:
                continue
            path, vid = hm.group(1), hm.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            tm = re.search(r'video-card__title[^>]*title="([^"]+)"', chunk, re.I)
            if not tm:
                tm = re.search(r'class="video-card__title"[^>]*>([^<]+)', chunk, re.I)
            title = self._clean(tm.group(1)) if tm else ""
            if not title:
                alt = re.search(r'alt="(?:Thumbnail for\s*)?([^"]+)"', chunk, re.I)
                title = self._clean(alt.group(1)) if alt else vid
            pic = ""
            im = re.search(r'data-front-lazy-src="([^"]+)"', chunk, re.I)
            if im and "placeholder" not in im.group(1):
                pic = im.group(1)
            if not pic:
                im2 = re.search(r'<img[^>]+src="([^"]+)"', chunk, re.I)
                if im2 and "placeholder" not in im2.group(1):
                    pic = im2.group(1)
            dm = re.search(r'video-card__details[^>]*>[\s\S]*?</strong>\s*([^<]+)', chunk, re.I)
            duration = self._clean(dm.group(1)) if dm else ""
            video_list.append(
                {
                    "vod_id": path,
                    "vod_name": title or vid,
                    "vod_pic": self._abs(pic),
                    "vod_remarks": format_remarks("Javtiful", duration),
                    "style": {"type": "rect", "ratio": 1.78},
                }
            )
        return video_list


    def _parse_directory(self, html, kind):
        """厂牌/女优目录。vod_id 与 type_id 同形，便于点进后走 categoryContent。"""
        video_list = []
        seen = set()
        for m in re.finditer(
            r'<article[^>]*class="[^"]*directory-card[^"]*"[^>]*>([\s\S]*?)</article>',
            html,
            re.I,
        ):
            chunk = m.group(1)
            if kind == "channel":
                hm = re.search(r'href="(/zh/channel/([^"/?]+))"', chunk)
            else:
                hm = re.search(r'href="(/zh/actress/([^"/?]+))"', chunk)
            if not hm:
                continue
            path, slug = hm.group(1), hm.group(2)
            # 统一成无前导 / 的 type_id，与 home 分类一致
            tid = path.lstrip("/")
            if tid in seen:
                continue
            seen.add(tid)
            nm = re.search(r'directory-card__name[^>]*>([^<]+)', chunk, re.I)
            if not nm:
                nm = re.search(r'<strong[^>]*>([^<]+)', chunk, re.I)
            name = self._clean(nm.group(1)) if nm else slug.replace("-", " ").title()
            pic = ""
            im = re.search(r'<img[^>]+src="([^"]+)"', chunk, re.I)
            if im:
                pic = im.group(1)
            cnt = ""
            cm = re.search(r'directory-card__count[^>]*>([^<]+)', chunk, re.I)
            if cm:
                cnt = self._clean(cm.group(1))
            item = {
                "vod_id": tid,
                "vod_name": name,
                "vod_pic": self._abs(pic),
                "vod_remarks": cnt or ("厂牌" if kind == "channel" else "女优"),
                "vod_tag": "folder",
                "style": {"type": "rect", "ratio": 1.0 if kind == "actress" else 1.78},
            }
            video_list.append(item)
        return video_list


    def _pagecount(self, html, page):
        nums = [int(x) for x in re.findall(r"[?&]page=(\d+)", html)]
        nums = [n for n in nums if 1 <= n <= 5000]
        if nums:
            return max(max(nums), page)
        if re.search(r"[?&]page=%d(?:[\"'&]|$)" % (page + 1), html):
            return page + 1
        if html.count("video-card") > 10 and page < 200:
            return page + 1
        return page

    def _build_list_url(self, tid, page):
        tid = str(tid).strip().lstrip("/")
        if tid.startswith("http"):
            base = tid
        elif tid.startswith("zh/category/"):
            parts = tid.split("zh/category/", 1)[1].split("?")
            path_slug = quote(parts[0], safe="-_.~")
            rest = ("?" + parts[1]) if len(parts) > 1 else ""
            base = f"{self.siteUrl}/zh/category/{path_slug}{rest}"
        else:
            # zh/videos、zh/channels、zh/channel/xxx、zh/actress/xxx 等
            if "?" in tid:
                path, query = tid.split("?", 1)
                base = f"{self.siteUrl}/{path}?{query}"
            else:
                base = f"{self.siteUrl}/{tid}"
        if page <= 1:
            return base
        if re.search(r"[?&]page=\d+", base):
            return re.sub(r"([?&])page=\d+", r"\1page=%d" % page, base)
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}page={page}"


    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        tid_s = str(tid).strip().lstrip("/")
        # 兼容误带 folder 前缀
        if tid_s.startswith("folder$$"):
            tid_s = tid_s[8:]
        if tid_s.startswith("folder/"):
            tid_s = tid_s[7:]

        url = self._build_list_url(tid_s, page)
        res = self._fetch(url)
        html = res.get("text") or ""
        if not html or res.get("code") not in (0, 200):
            return {"page": page, "pagecount": 1, "limit": 0, "total": 0, "list": []}

        # 仅「目录索引」走 directory；单个厂牌/女优页走视频列表
        is_ch_index = bool(re.search(r"^zh/channels(?:\?|$)", tid_s))
        is_ac_index = bool(re.search(r"^zh/actresses(?:\?|$)", tid_s))
        if is_ch_index:
            video_list = self._parse_directory(html, "channel")
        elif is_ac_index:
            video_list = self._parse_directory(html, "actress")
        else:
            video_list = self._parse_list(html)

        pagecount = self._pagecount(html, page)
        if video_list and pagecount <= page:
            if is_ch_index or is_ac_index or "/channel/" in tid_s or "/actress/" in tid_s:
                if page < 500:
                    pagecount = page + 1
            elif page < 100:
                pagecount = page + 1
        return {
            "page": page,
            "pagecount": max(pagecount, page),
            "limit": len(video_list) or 24,
            "total": max(pagecount, page) * max(len(video_list), 1),
            "list": video_list,
        }


    def _playback_sources(self, detail_html, detail_url):
        """POST ticket to playback endpoint, return [(label, url), ...]"""
        m = re.search(
            r'"playback"\s*:\s*\{\s*"endpoint"\s*:\s*"([^"]+)"\s*,\s*"ticket"\s*:\s*"([^"]+)"',
            detail_html,
        )
        if not m:
            m = re.search(
                r'"endpoint"\s*:\s*"(/zh/video/\d+/playback)"[^}]*"ticket"\s*:\s*"([^"]+)"',
                detail_html,
            )
        if not m:
            return []
        endpoint, ticket = m.group(1), m.group(2)
        api = self._abs(endpoint)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.siteUrl,
            "Referer": detail_url,
            "User-Agent": self.headers["User-Agent"],
        }
        body = "ticket=" + quote(ticket, safe="")
        res = self._fetch(api, method="POST", data=body, headers=headers)
        text = res.get("text") or ""
        try:
            data = json.loads(text)
        except Exception:
            return []
        if not data.get("success") or not data.get("sources"):
            # try renewTicket path not available offline; return empty
            return []
        items = []
        for src in data["sources"]:
            u = src.get("src") or ""
            if not u:
                continue
            label = src.get("label") or (f"{src.get('size')}p" if src.get("size") else "正片")
            items.append((str(label), self._abs(u)))
        # high quality first
        def qkey(it):
            m2 = re.search(r"(\d{3,4})", it[0])
            return int(m2.group(1)) if m2 else 0

        items.sort(key=qkey, reverse=True)
        return items

    def _detail_folder(self, url, path):
        """厂牌/女优页：把视频列表做成多集，播放时再解析真实地址"""
        res = self._fetch(url)
        html = res.get("text") or ""
        if not html:
            return {"list": []}
        name = ""
        tm = re.search(r"<title>([^<]+)", html, re.I)
        if tm:
            name = self._clean(tm.group(1))
            name = re.sub(r"\s*\|\s*Javtiful.*$", "", name, flags=re.I).strip()
        if not name:
            name = path.rstrip("/").split("/")[-1].replace("-", " ").title()
        pic = ""
        im = re.search(r'<img[^>]+src="(/uploads/[^"]+)"', html, re.I)
        if im:
            pic = self._abs(im.group(1))
        videos = self._parse_list(html)
        if not videos:
            return {"list": [{"vod_id": path, "vod_name": name, "vod_pic": pic, "vod_play_from": "Javtiful", "vod_play_url": ""}]}
        # 多集：标题$path
        parts = []
        for v in videos:
            tname = v.get("vod_name") or v.get("vod_id")
            # 缩短过长标题
            if len(tname) > 60:
                tname = tname[:57] + "..."
            parts.append(f"{tname}${v['vod_id']}")
        return {
            "list": [
                {
                    "vod_id": path,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_content": f"共 {len(videos)} 部（当前页）",
                    "vod_play_from": "Javtiful",
                    "vod_play_url": "#".join(parts),
                }
            ]
        }


    def detailContent(self, ids):
        path = str(ids[0]).strip()
        if path.startswith("http"):
            url = path
        else:
            url = self._abs(path if path.startswith("/") else f"/zh/video/{path}")

        # 厂牌 / 女优：聚合该页视频为选集（点某一集再进真正详情/播放）
        if re.search(r"/zh/channel/[^/]+/?$", path) or re.search(r"/zh/actress/[^/]+/?$", path) or            re.search(r"/channel/[^/]+/?$", path) or re.search(r"/actress/[^/]+/?$", path):
            return self._detail_folder(url, path)

        res = self._fetch(url)
        html = res.get("text") or ""
        if not html:
            return {"list": []}

        title = ""
        vt = re.search(r'"videoTitle"\s*:\s*"([^"]+)"', html)
        if vt:
            title = self._clean(vt.group(1))
        if not title:
            hm = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.I)
            if hm:
                title = self._clean(hm.group(1))
        if not title:
            tm = re.search(r"<title>([^<]+)", html, re.I)
            if tm:
                title = self._clean(tm.group(1))
                title = re.sub(r"\s*\|\s*Javtiful.*$", "", title, flags=re.I).strip()

        pic = ""
        pm = re.search(r'"videoPoster"\s*:\s*"([^"]+)"', html)
        if pm:
            pic = self._abs(pm.group(1))
        if not pic:
            pm2 = re.search(
                r'<img[^>]+src="(/uploads/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                html,
                re.I,
            )
            if pm2:
                pic = self._abs(pm2.group(1))

        sources = self._playback_sources(html, url)
        if sources:
            play_url = "#".join(f"{n}${u}" for n, u in sources)
        else:
            play_url = f"网页${url}"

        vid = path
        m_id = re.search(r"/video/(\d+)", path)
        if m_id:
            vid = m_id.group(1)

        return {
            "list": [
                {
                    "vod_id": vid,
                    "vod_name": title or vid,
                    "vod_pic": pic,
                    "vod_content": "",
                    "vod_play_from": "Javtiful",
                    "vod_play_url": play_url,
                }
            ]
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        q = quote(key.strip())
        url = f"{self.siteUrl}/zh/search?q={q}"
        if page > 1:
            url += f"&page={page}"
        res = self._fetch(url)
        html = res.get("text") or ""
        video_list = self._parse_list(html) if html else []
        pagecount = self._pagecount(html, page)
        if video_list and pagecount <= page:
            pagecount = page
        return {
            "page": page,
            "pagecount": max(pagecount, 1),
            "limit": len(video_list) or 24,
            "total": len(video_list),
            "list": video_list,
        }

    def playerContent(self, flag, id, vipFlags):
        url = str(id).strip()
        if url.startswith("http") and (
            ".mp4" in url or ".m3u8" in url or "fast-stream.jav.si" in url
        ):
            return {
                "parse": 0,
                "url": url,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.siteUrl + "/",
                    "Origin": self.siteUrl,
                },
            }
        # detail path — re-resolve
        if "/video/" in url or url.isdigit():
            detail = (
                url
                if url.startswith("http")
                else self._abs(url if url.startswith("/") else f"/zh/video/{url}")
            )
            res = self._fetch(detail)
            html = res.get("text") or ""
            sources = self._playback_sources(html, detail)
            if sources:
                return {
                    "parse": 0,
                    "url": sources[0][1],
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.siteUrl + "/",
                        "Origin": self.siteUrl,
                    },
                }
            return {"parse": 1, "url": detail, "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}

    def localProxy(self, param):
        return None
