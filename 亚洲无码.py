# -*- coding: utf-8 -*-
# 亚洲无码 bormyl.yzwm5.skin 蜂蜜影视 Spider
# 模板同 tutumo：/vodtype/30.html  /{id}.html  /s/index.html

import re
import json
import time
from urllib import parse
from urllib.request import Request, urlopen
import ssl

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def __init__(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "亚洲无码"
        self.host = "https://bormyl.yzwm5.skin"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.host + "/",
        }
        self._ssl = None
        self.classes = [
            {"type_id": "21", "type_name": "女神学生"},
            {"type_id": "22", "type_name": "美女直播"},
            {"type_id": "23", "type_name": "人妻系列"},
            {"type_id": "24", "type_name": "强奸乱伦"},
            {"type_id": "25", "type_name": "自拍偷拍"},
            {"type_id": "26", "type_name": "制服诱惑"},
            {"type_id": "27", "type_name": "巨乳系列"},
            {"type_id": "28", "type_name": "自慰系列"},
            {"type_id": "29", "type_name": "国产视频"},
            {"type_id": "30", "type_name": "无码视频"},
            {"type_id": "31", "type_name": "有码视频"},
            {"type_id": "32", "type_name": "中文字幕"},
            {"type_id": "33", "type_name": "日韩精品"},
            {"type_id": "34", "type_name": "欧美精品"},
            {"type_id": "35", "type_name": "动漫精品"},
            {"type_id": "36", "type_name": "三级伦理"},
            {"type_id": "hot", "type_name": "总排行榜"},
            {"type_id": "hot_month", "type_name": "月排行榜"},
            {"type_id": "hot_week", "type_name": "周排行榜"},
            {"type_id": "hot_day", "type_name": "日排行榜"},
            {"type_id": "new", "type_name": "最新上传"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            html = self.fetch(self._abs("/cn/home/web/"))
            if not html:
                html = self.fetch(self._abs("/vodtype/30.html"))
            return {"list": self._parse_list(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = str(tid or "30").strip()
        try:
            url = self._list_url(tid, page)
            html = self.fetch(url)
            videos = self._parse_list(html)
            pagecount = page + 1 if videos else page
            # 分页：/vodtype/30-2.html
            if videos and len(videos) >= 10:
                pagecount = max(page + 5, pagecount)
            m = re.search(r"共\s*(\d+)\s*页|/page/(\d+)|-(\d+)\.html", html or "")
            if m:
                for g in m.groups():
                    if g and g.isdigit() and int(g) > page:
                        pagecount = max(pagecount, int(g))
            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "pageCount": pagecount,
                "limit": 24,
                "total": pagecount * 24,
            }
        except Exception as e:
            print("[yzwm] category:", e)
            return {"list": [], "page": page, "pagecount": 1, "pageCount": 1, "limit": 24, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        url = self._detail_url(raw)
        try:
            html = self.fetch(url)
            if not html:
                return {"list": []}
            title = ""
            m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
            if m:
                title = m.group(1)
            if not title:
                m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
                if m:
                    title = re.sub(r"\s*[-_|].*$", "", m.group(1)).strip()
            pic = ""
            m = re.search(r'property="og:image"\s+content="([^"]+)"', html)
            if m:
                pic = m.group(1)
            if not pic:
                m = re.search(r'class="[^"]*thumb[^"]*"[^>]*(?:src|data-src)="(https?://[^"]+)"', html)
                if m:
                    pic = m.group(1)

            sources = self._extract_sources(html)
            if sources:
                play_from = "线路"
                play_url = "#".join("%s$%s" % (n, u) for n, u in sources)
            else:
                # 尝试播放页
                play_links = re.findall(
                    r'href="\s*((?:https?://[^"]+)?/(?:vodplay|play)/[^"]+)"',
                    html,
                    re.I,
                )
                if play_links:
                    lines = []
                    for i, pl in enumerate(play_links[:8]):
                        pu = pl if pl.startswith("http") else self._abs(pl.strip())
                        lines.append("播放%d$%s" % (i + 1, pu))
                    play_from = "线路"
                    play_url = "#".join(lines)
                else:
                    play_from = "嗅探"
                    play_url = "播放$%s" % url

            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": title or "未知",
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title or "",
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": play_from,
                    "vod_play_url": play_url,
                }]
            }
        except Exception as e:
            print("[yzwm] detail:", e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
        }
        hj = json.dumps(headers)
        if not id:
            return {"parse": 1, "url": self.host, "header": hj}
        if self.isVideoFormat(id):
            return {"parse": 0, "jx": 0, "url": id, "header": hj}
        url = id if id.startswith("http") else self._abs(id)
        try:
            html = self.fetch(url)
            sources = self._extract_sources(html or "")
            if sources:
                # 优先完整 m3u8（非 preview）
                pick = sources[0][1]
                for n, u in sources:
                    if ".m3u8" in u and "preview" not in u.lower():
                        pick = u
                        if any(x in u for x in ("2000kb", "1080", "720", "index.m3u8")):
                            break
                return {"parse": 0, "jx": 0, "url": pick, "header": hj}
        except Exception as e:
            print("[yzwm] play:", e)
        return {"parse": 1, "jx": 0, "url": url, "header": hj}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        q = parse.quote(str(key or "").strip())
        # /s/关键词.html 或 /s/index.html?wd=
        urls = [
            self._abs("/s/%s.html" % q),
            self._abs("/s/index.html?wd=%s&page=%d" % (q, page)),
        ]
        if page > 1:
            urls.insert(0, self._abs("/s/%s/page/%d.html" % (q, page)))
        videos = []
        for u in urls:
            try:
                html = self.fetch(u)
                videos = self._parse_list(html or "")
                if videos:
                    break
            except Exception:
                continue
        return {
            "list": videos,
            "page": page,
            "pagecount": 999 if videos else page,
            "pageCount": 999 if videos else page,
            "limit": 24,
            "total": 9999 if videos else 0,
        }

    def localProxy(self, param):
        try:
            url = param.get("url") if isinstance(param, dict) else str(param or "")
            for _ in range(2):
                if "%" in url:
                    url = parse.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b""]
            body = self._fetch_bytes(url)
            ctype = "image/jpeg"
            if body[:8].startswith(b"\x89PNG"):
                ctype = "image/png"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    def _ssl_ctx(self):
        if self._ssl is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl = ctx
        return self._ssl

    def fetch(self, url, retry=2):
        last = None
        for _ in range(retry):
            try:
                req = Request(url, headers=self.headers)
                with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
                    data = resp.read().decode("utf-8", "ignore")
                if data and len(data) > 300:
                    return data
            except Exception as e:
                last = e
                time.sleep(0.12)
        print("[yzwm] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
            return resp.read() or b""

    def _abs(self, path):
        if not path:
            return self.host
        path = path.strip()
        if path.startswith("http"):
            return path
        if path.startswith("//"):
            return "https:" + path
        return self.host + (path if path.startswith("/") else "/" + path)

    def _list_url(self, tid, page=1):
        tid = str(tid).strip("/")
        page = int(page or 1)
        # 排行榜
        if tid in ("hot", "hot_month", "hot_week", "hot_day", "new"):
            path = "/label/%s.html" % tid
            if page > 1:
                path = "/label/%s/page/%d.html" % (tid, page)
            return self._abs(path)
        # 数字分类：/vodtype/30.html  /vodtype/30-2.html
        if re.match(r"^\d+$", tid):
            if page <= 1:
                return self._abs("/vodtype/%s.html" % tid)
            return self._abs("/vodtype/%s-%d.html" % (tid, page))
        # 已是路径
        if "vodtype" in tid or tid.endswith(".html"):
            path = tid if tid.startswith("/") else "/" + tid
            if page > 1 and "-%d.html" % page not in path:
                path = re.sub(r"\.html$", "-%d.html" % page, path)
            return self._abs(path)
        return self._abs("/vodtype/%s.html" % tid)

    def _detail_url(self, raw):
        raw = str(raw or "").strip()
        if raw.startswith("http"):
            return raw
        raw = raw.strip()
        if raw.startswith("/"):
            return self._abs(raw)
        if re.match(r"^\d+$", raw):
            return self._abs("/%s.html" % raw)
        return self._abs("/" + raw.lstrip("/"))

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        if pic.startswith("/"):
            pic = self._abs(pic)
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    return "%s&url=%s" % (base, parse.quote(pic))
        except Exception:
            pass
        return pic

    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()
        # 模板：li.aj_item  href=" /1176074.html"  img.thumb.aj_img
        for m in re.finditer(
            r'<li[^>]*class="[^"]*aj_item[^"]*"[\s\S]{0,1200}?</li>',
            html,
            re.I,
        ):
            block = m.group(0)
            hm = re.search(r'href="\s*/?(\d+)\.html"', block)
            if not hm:
                hm = re.search(r'href="\s*((?:https?://[^"]+)?/\d+\.html)"', block)
            if not hm:
                continue
            href = hm.group(1).strip()
            vid = re.search(r"(\d+)\.html", href)
            vid = vid.group(1) if vid else href
            if vid in seen:
                continue
            seen.add(vid)
            title = ""
            for tp in [
                r'class="aj_tit"[^>]*>([^<]+)<',
                r'title="([^"]{2,120})"',
                r'alt="([^"]{2,120})"',
            ]:
                tm = re.search(tp, block)
                if tm:
                    title = tm.group(1).strip()
                    break
            pic = ""
            pm = re.search(
                r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                block,
                re.I,
            )
            if pm:
                pic = pm.group(1)
            url = href if href.startswith("http") else self._abs("/" + href.lstrip("/"))
            if not url.endswith(".html") and vid.isdigit():
                url = self._abs("/%s.html" % vid)
            videos.append({
                "vod_id": url,
                "vod_name": (title or ("视频" + vid))[:100],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })

        # 兜底：全页数字.html 链接
        if len(videos) < 5:
            for m in re.finditer(r'href="\s*((?:https?://[^"]+)?/(\d{5,})\.html)"', html):
                href, vid = m.group(1).strip(), m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                win = html[max(0, m.start() - 80): m.end() + 400]
                title = ""
                tm = re.search(r'(?:title|alt)="([^"]{2,100})"', win)
                if tm:
                    title = tm.group(1)
                pic = ""
                pm = re.search(r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', win)
                if pm:
                    pic = pm.group(1)
                url = href if href.startswith("http") else self._abs(href if href.startswith("/") else "/" + href)
                videos.append({
                    "vod_id": url,
                    "vod_name": (title or ("视频" + vid))[:100],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "",
                })
                if len(videos) >= 48:
                    break
        return videos

    def _extract_sources(self, html):
        sources = []
        # player_aaaa / MacCMS
        m = re.search(r"player_[a-zA-Z0-9]+\s*=\s*(\{.+?\})\s*;", html or "", re.S)
        if m:
            blob = m.group(1)
            um = re.search(r'"url"\s*:\s*"([^"]+)"', blob)
            if um:
                u = parse.unquote(um.group(1).replace("\\/", "/"))
                if u.startswith("http"):
                    sources.append(("直连", u))
            # url 可能是 escape
            um = re.search(r'"url"\s*:\s*"([^"]+)"', blob)
        # 明文 m3u8
        for u in re.findall(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', html or ""):
            u = u.replace("\\/", "/")
            if "preview" in u.lower():
                continue
            label = "HLS"
            if "2000kb" in u or "1080" in u:
                label = "高清"
            elif "1000kb" in u or "720" in u:
                label = "标清"
            sources.append((label, u))
        for u in re.findall(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', html or ""):
            u = u.replace("\\/", "/")
            if any(x in u.lower() for x in ("preview", "thumb", "trailer")):
                continue
            sources.append(("MP4", u))
        # MacCMS url 字段
        for m in re.finditer(r'"(?:url|url_next)"\s*:\s*"(https?[^"]+)"', html or ""):
            u = m.group(1).replace("\\/", "/")
            u = parse.unquote(u)
            if self.isVideoFormat(u):
                sources.append(("线路", u))
        seen, out = set(), []
        for n, u in sources:
            if u in seen:
                continue
            seen.add(u)
            out.append((n, u))
        return out
