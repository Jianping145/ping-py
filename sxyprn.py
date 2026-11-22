# -*- coding: utf-8 -*-
# SexyPorn / sxyprn.com  蜂蜜影视(FongMi) Spider

import re
import json
import time
import base64
from urllib import parse
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor, HTTPSHandler
from http.cookiejar import CookieJar
import ssl
import html as html_lib

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def __init__(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "SexyPorn"
        self.host = "https://sxyprn.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Referer": "https://sxyprn.com/",
        }
        self._ssl = None
        self._cj = CookieJar()
        self.classes = [
            {"type_id": "blog:all", "type_name": "最新"},
            {"type_id": "popular:top-pop", "type_name": "最热"},
            {"type_id": "popular:top-viewed", "type_name": "最多播放"},
            {"type_id": "orgasm", "type_name": "Orgasm"},
            {"type_id": "community", "type_name": "社区"},
            {"type_id": "keys", "type_name": "Keys"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return any(x in u for x in [".m3u8", ".mp4", ".flv", ".vid"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        classes = list(self.classes)
        # 动态补充热门标签到一级分类
        try:
            html = self.fetch(self.host + "/searches/0.html")
            known = {c["type_id"] for c in classes}
            for m in re.finditer(
                r"<a[^>]+href='(/([A-Za-z0-9+\-]+)\.html(?:\?[^']*)?)'[^>]*>([^<]{2,40})</a>",
                html or "",
            ):
                path, slug, name = m.group(1), m.group(2), html_lib.unescape(m.group(3)).strip()
                if not name or len(name) > 30:
                    continue
                # 跳过非标签页
                if slug.lower() in ("sxyprn1", "2026"):
                    continue
                tid = "tag:%s" % slug
                if tid in known:
                    continue
                known.add(tid)
                classes.append({"type_id": tid, "type_name": name})
                if len(classes) >= 60:
                    break
        except Exception as e:
            print("[sxy] home tags:", e)
        self.classes = classes
        return {"class": classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            html = self.fetch(self.host + "/blog/all/0.html")
            return {"list": self._parse_list(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = str(tid or "blog:all").strip()
        videos = []
        try:
            # 社区博主列表（文件夹）
            if tid == "community":
                # 分页：/community/0.html, /community/12.html (每页约12)
                offset = (page - 1) * 12
                url = self.host + "/community/%d.html" % offset
                html = self.fetch(url)
                videos = self._parse_community(html)
                pagecount = page + 1 if len(videos) >= 8 else page
                return {
                    "list": videos,
                    "page": page,
                    "pagecount": max(pagecount, page + 5) if len(videos) >= 8 else page,
                    "pageCount": max(pagecount, page + 5) if len(videos) >= 8 else page,
                    "limit": 12,
                    "total": 2400,
                }
            # Keys 热搜词 /searches/0.html, /searches/150.html ...
            if tid == "keys":
                offset = (page - 1) * 150
                url = self.host + "/searches/%d.html" % offset
                html = self.fetch(url)
                videos = self._parse_keys(html)
                pagecount = page + 1 if len(videos) >= 100 else page
                if len(videos) >= 100:
                    pagecount = max(pagecount, page + 10)
                return {
                    "list": videos,
                    "page": page,
                    "pagecount": pagecount,
                    "pageCount": pagecount,
                    "limit": 150,
                    "total": pagecount * 150,
                }
            # 站点分页步进: blog/user=20, popular=30, tag=30, keys=150, community=12
            if tid.startswith("blog:"):
                slug = tid.split(":", 1)[1]
                offset = (page - 1) * 20
                url = self.host + "/blog/%s/%d.html" % (slug, offset)
            elif tid.startswith("popular:"):
                slug = tid.split(":", 1)[1]
                offset = (page - 1) * 30
                # /popular/top-pop.html/0  /popular/top-pop.html/30
                url = self.host + "/popular/%s.html/%d" % (slug, offset)
            elif tid == "orgasm":
                offset = (page - 1) * 30
                if page <= 1:
                    url = self.host + "/orgasm/"
                else:
                    # 尝试与 popular 类似的偏移
                    url = self.host + "/orgasm/%d" % offset
                    # 备用
                    alt = self.host + "/orgasm/?page=%d" % offset
                    html = self.fetch(url)
                    if not html or len(re.findall(r"/post/[a-f0-9]+\.html", html)) < 5:
                        html = self.fetch(alt)
                    videos = self._parse_list(html)
                    pagecount = page + 1 if len(videos) >= 15 else page
                    if len(videos) >= 15:
                        pagecount = max(pagecount, page + 20)
                    return {
                        "list": videos,
                        "page": page,
                        "pagecount": pagecount,
                        "pageCount": pagecount,
                        "limit": 30,
                        "total": pagecount * 30,
                    }
            elif tid.startswith("user:"):
                name = tid.split(":", 1)[1]
                offset = (page - 1) * 20
                # /blog/@ILUVY/0.html
                url = self.host + "/blog/@%s/%d.html" % (name, offset)
            elif tid.startswith("blogid:"):
                bid = tid.split(":", 1)[1]
                offset = (page - 1) * 20
                url = self.host + "/blog/%s/%d.html" % (bid, offset)
            elif tid.startswith("tag:"):
                slug = tid.split(":", 1)[1]
                offset = (page - 1) * 30
                # /Anal.html?page=0&sm=trending
                url = self.host + "/%s.html?page=%d&sm=trending" % (slug, offset)
            else:
                offset = (page - 1) * 20
                url = self.host + "/blog/all/%d.html" % offset
            html = self.fetch(url)
            videos = self._parse_list(html)
        except Exception as e:
            print("[sxy] category:", e)
        # 有满页内容就继续允许翻页
        pagecount = page + 1 if len(videos) >= 10 else page
        if len(videos) >= 10:
            pagecount = max(pagecount, page + 30)
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 30,
            "total": pagecount * 30,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        raw = str(raw).strip()
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self.host + raw
        else:
            url = self.host + "/post/%s.html" % raw.replace(".html", "")
        try:
            html = self.fetch(url)
        except Exception as e:
            print("[sxy] detail:", e)
            return {"list": []}
        if not html:
            return {"list": []}

        title = ""
        m = re.search(r"<title[^>]*>([^<]+)</title>", html)
        if m:
            title = html_lib.unescape(m.group(1)).strip()
            title = re.sub(r"\s*[|\-]\s*SexyPorn.*$", "", title, flags=re.I).strip()
        if not title:
            m = re.search(r"title='([^']+)'", html)
            if m:
                title = html_lib.unescape(m.group(1)).split("http")[0].strip()
        title = title or "SexyPorn"

        pic = ""
        m = re.search(r"<video[^>]+poster='([^']+)'", html)
        if not m:
            m = re.search(r'<video[^>]+poster="([^"]+)"', html)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r"data-src='(//[^']+/(?:small|0)\.(?:jpg|webp))'", html)
            if m:
                pic = m.group(1)
        if pic.startswith("//"):
            pic = "https:" + pic

        # 解密站内播放 + 外链多线路
        plays = []  # [(name, url)]
        try:
            play_url, size = self._extract_play(html, with_size=True)
            if play_url:
                if size and size < 800000:
                    plays.append(("预览", play_url))
                else:
                    plays.append(("直连", play_url))
        except Exception as e:
            print("[sxy] play decode:", e)

        # 页面外链（常为完整片）
        exter_hosts = (
            "lulustream.com", "vidara.so", "vidara.to", "doodstream.com", "dood.",
            "streamtape.com", "streamlare.com", "voe.sx", "filemoon.", "krakenfiles.",
            "upstream.to", "upstreamcdn", "mixdrop.", "mp4upload.", "wolfsban.",
        )
        seen_u = set(u for _, u in plays)
        for m in re.finditer(r"https?://[^\s'\"<>]+", html):
            u = m.group(0).rstrip(".,);]\"'")
            low = u.lower()
            if any(h in low for h in exter_hosts):
                if u in seen_u:
                    continue
                if any(x in low for x in (".jpg", ".png", ".webp", ".css", ".js")):
                    continue
                seen_u.add(u)
                name = "外链"
                for h in exter_hosts:
                    if h in low:
                        name = h.split(".")[0][:12]
                        break
                plays.append((name, u))
            if len(plays) >= 8:
                break

        if not plays:
            plays = [("详情", url)]

        # 线路名去重
        from_names, urls = [], []
        used = set()
        for i, (name, u) in enumerate(plays):
            n = name
            if n in used:
                n = "%s%d" % (name, i + 1)
            used.add(n)
            from_names.append(n)
            urls.append("播放$%s" % u)

        return {
            "list": [{
                "vod_id": url,
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_content": title[:300],
                "vod_remarks": "",
                "vod_year": "",
                "vod_area": "",
                "vod_actor": "",
                "vod_director": "",
                "type_name": "SexyPorn",
                "vod_play_from": "$$$".join(from_names),
                "vod_play_url": "$$$".join(urls),
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
        }
        url = (id or "").strip()
        if not url:
            return {"parse": 1, "url": self.host, "header": json.dumps(headers)}

        # 若仍是详情页，再解一次
        if "/post/" in url and not self.isVideoFormat(url):
            try:
                html = self.fetch(url)
                u2 = self._extract_play(html)
                if isinstance(u2, tuple):
                    u2 = u2[0]
                if u2:
                    url = u2
            except Exception as e:
                print("[sxy] player reparse:", e)

        # cdn8 中间链：跟随到最终 mp4
        if "/cdn8/" in url or url.endswith(".vid"):
            try:
                u2 = self._resolve_final(url)
                if isinstance(u2, tuple):
                    u2 = u2[0]
                if u2:
                    url = u2
            except Exception as e:
                print("[sxy] resolve:", e)

        if url.startswith("//"):
            url = "https:" + url

        if self.isVideoFormat(url) or url.startswith("http"):
            try:
                pu = parse.urlparse(url)
                if "trafficdeposit.com" in (pu.netloc or ""):
                    headers["Referer"] = self.host + "/"
            except Exception:
                pass
            return {
                "parse": 0 if self.isVideoFormat(url) or "trafficdeposit" in url else 1,
                "jx": 0,
                "url": url,
                "header": json.dumps(headers),
            }
        return {"parse": 1, "jx": 0, "url": url, "header": json.dumps(headers)}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        key = str(key or "").strip()
        videos = []
        try:
            # 站点搜索路径：/searches 或 关键词路径
            q = parse.quote(key)
            # 常见形式 /popular.html? 或 标签
            url = self.host + "/%s.html" % q.replace("%20", "+")
            if page > 1:
                url = self.host + "/%s/%d.html" % (q.replace("%20", "+"), page - 1)
            html = self.fetch(url)
            videos = self._parse_list(html)
            if not videos:
                # 备用：在最新里本地过滤意义不大，再试 searches
                html = self.fetch(self.host + "/blog/all/0.html")
                videos = [v for v in self._parse_list(html) if key.lower() in v.get("vod_name", "").lower()]
        except Exception as e:
            print("[sxy] search:", e)
        pagecount = page + 1 if len(videos) >= 15 else page
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 30,
            "total": pagecount * 30,
        }

    def localProxy(self, param):
        try:
            url = param.get("url") if isinstance(param, dict) else str(param or "")
            for _ in range(2):
                if "%" in (url or "") and ("http%" in url.lower() or url.startswith("%")):
                    url = parse.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b"bad url"]
            body = self._fetch_bytes(url)
            if not body:
                return [500, "text/plain", b"empty"]
            ctype = "image/jpeg"
            if body[:8].startswith(b"\x89PNG"):
                ctype = "image/png"
            elif body[:4] == b"RIFF":
                ctype = "image/webp"
            elif body[:3] == b"GIF":
                ctype = "image/gif"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    # ---------- helpers ----------
    def _ssl_ctx(self):
        if self._ssl is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl = ctx
        return self._ssl

    def _opener(self):
        return build_opener(
            HTTPCookieProcessor(self._cj),
            HTTPSHandler(context=self._ssl_ctx()),
        )

    def fetch(self, url):
        last = None
        for _ in range(2):
            try:
                req = Request(url, headers=self.headers)
                with self._opener().open(req, timeout=20) as resp:
                    return resp.read().decode("utf-8", "ignore")
            except Exception as e:
                last = e
                time.sleep(0.2)
        print("[sxy] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        with self._opener().open(req, timeout=18) as resp:
            return resp.read() or b""

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    return "%s&url=%s" % (base, parse.quote(pic, safe=""))
        except Exception:
            pass
        return pic

    @staticmethod
    def _ssut51(arg):
        s = re.sub(r"[^0-9]", "", str(arg or ""))
        return sum(int(c) for c in s) if s else 0

    @staticmethod
    def _boo(ss, es, host="sxyprn.com"):
        raw = "%s-%s-%s" % (ss, host, es)
        b = base64.b64encode(raw.encode()).decode()
        return b.replace("+", "-").replace("/", "_").replace("=", ".")

    def _decode_vnfo_src(self, src, host="sxyprn.com"):
        """将 data-vnfo 中的 /cdn/...vid 转为 /cdn8/... 可跳转地址"""
        if not src:
            return ""
        src = src.strip()
        if not src.startswith("/"):
            src = "/" + src
        tmp = src.split("/")
        if len(tmp) < 8:
            return src
        tmp[1] = tmp[1] + "8/" + self._boo(self._ssut51(tmp[6]), self._ssut51(tmp[7]), host)
        try:
            tmp[5] = str(int(tmp[5]) - self._ssut51(tmp[6]) - self._ssut51(tmp[7]))
        except Exception:
            pass
        return "/".join(tmp)

    def _extract_play(self, html, with_size=False):
        empty = ("", 0) if with_size else ""
        m = re.search(r"data-vnfo='(\{[^']+\})'", html or "")
        if not m:
            m = re.search(r'data-vnfo="(\{[^"]+\})"', html or "")
        if not m:
            return empty
        raw = m.group(1).replace("\\/", "/")
        try:
            vnfo = json.loads(raw)
        except Exception:
            return empty
        if not isinstance(vnfo, dict) or not vnfo:
            return empty
        # 可能有多个 pid key，取第一个有效
        best_url, best_size = "", 0
        for src in vnfo.values():
            path = self._decode_vnfo_src(src)
            if not path:
                continue
            mid = self.host + path
            try:
                final, size = self._resolve_final(mid, with_size=True)
            except Exception:
                final, size = mid, 0
            if not final:
                continue
            if size >= best_size:
                best_url, best_size = final, size
        if not best_url:
            return empty
        if with_size:
            return best_url, best_size
        return best_url


    def _resolve_final(self, url, with_size=False):
        if not url:
            return ("", 0) if with_size else url
        if url.startswith("//"):
            url = "https:" + url
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Accept": "*/*",
        })
        try:
            with self._opener().open(req, timeout=20) as resp:
                final = resp.geturl() or url
                size = 0
                try:
                    size = int(resp.headers.get("Content-Length") or 0)
                except Exception:
                    size = 0
                # 读一点确认是视频
                head = resp.read(16)
                if with_size:
                    return final, size
                return final
        except Exception as e:
            print("[sxy] resolve fail:", e)
            if with_size:
                return url, 0
            return url


    def _parse_community(self, html):
        """社区博主 → folder，点击进入其作品网格"""
        if not html:
            return []
        videos, seen = [], set()
        for m in re.finditer(
            r"<a href='(/@([A-Za-z0-9_\-]+)|/blog/(\d+)/0\.html)'>\s*<div class='blogger_el'>([\s\S]*?)</div></a>",
            html,
        ):
            href, uname, blogid, block = m.group(1), m.group(2), m.group(3), m.group(4)
            name_m = re.search(r"class='a_name'[^>]*>([^<]+)", block)
            name = html_lib.unescape(name_m.group(1)).strip() if name_m else (uname or blogid)
            name = re.sub(r"\s+", " ", name).strip()
            vids_m = re.search(r"Vids:\s*<b>(\d+)</b>", block)
            posts_m = re.search(r"Posts:\s*<b>(\d+)</b>", block)
            remarks = ""
            if vids_m:
                remarks = vids_m.group(1)
            elif posts_m:
                remarks = posts_m.group(1)
            if uname:
                vid = "user:" + uname
            else:
                vid = "blogid:" + str(blogid)
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": vid,
                "vod_name": name[:80],
                "vod_pic": "",
                "vod_remarks": "",
                "vod_year": remarks,
                "vod_tag": "folder",
                "land": 1,
            })
        return videos

    def _parse_keys(self, html):
        """Keys 热搜表：trend_link + 结果数"""
        if not html:
            return []
        videos, seen = [], set()
        # 表格行: <a href='/Anal.html?sm=trending&trends=1' class='trend_link' title='Anal'>Anal</a> ... <td>142339</td>
        for m in re.finditer(
            r"<a href='(/([A-Za-z0-9+\-]+)\.html(?:\?[^']*)?)'\s+class='trend_link'[^>]*title='([^']*)'[^>]*>[^<]*</a></td>"
            r"<td>(\d+)</td>\s*<td[^>]*>[^<]*</td>\s*<td>(\d+)</td>",
            html,
        ):
            slug, name, freq, results = m.group(2), html_lib.unescape(m.group(3)).strip(), m.group(4), m.group(5)
            if not name:
                continue
            if slug.lower() in ("sxyprn1",):
                continue
            tid = "tag:" + slug
            if tid in seen:
                continue
            seen.add(tid)
            videos.append({
                "vod_id": tid,
                "vod_name": name[:80],
                "vod_pic": "",
                "vod_remarks": "",
                "vod_year": results,
                "vod_tag": "folder",
                "land": 1,
            })
        # 回退：仅 trend_link
        if not videos:
            for m in re.finditer(
                r"<a href='(/([A-Za-z0-9+\-]+)\.html(?:\?[^']*)?)'\s+class='trend_link'[^>]*title='([^']*)'",
                html,
            ):
                slug, name = m.group(2), html_lib.unescape(m.group(3)).strip()
                if not name or slug.lower() == "sxyprn1":
                    continue
                tid = "tag:" + slug
                if tid in seen:
                    continue
                seen.add(tid)
                videos.append({
                    "vod_id": tid,
                    "vod_name": name[:80],
                    "vod_pic": "",
                    "vod_remarks": "",
                    "vod_tag": "folder",
                    "land": 1,
                })
        return videos

    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()

        # 封面: pid -> pic（取路径末尾文件名前的 post id）
        pic_map = {}
        for m in re.finditer(r"data-src='(//[^']+)'", html):
            pic = m.group(1)
            pm = re.search(r"/([a-f0-9]{10,})/(?:small|full|0)\.(?:jpg|webp|png)", pic)
            if not pm:
                pm = re.search(r"/([a-f0-9]{10,})/[^/]+$", pic)
            if not pm:
                continue
            pid = pm.group(1)
            if "small" in pic or "full" in pic or "0.webp" in pic or "0.jpg" in pic or "/img/" in pic:
                pic_map[pid] = pic
            else:
                pic_map.setdefault(pid, pic)

        # 正文备选标题: pid -> text
        text_map = {}
        for m in re.finditer(
            r"data-id='([a-f0-9]+)'[\s\S]{0,50}?title='([\s\S]*?)'",
            html,
        ):
            # prefer title already
            pass
        for m in re.finditer(
            r"class='post_text[^']*'[^>]*>([\s\S]*?)(?:</div>|<div class='post_control')",
            html,
        ):
            raw = m.group(1)
            # 找前面的 post id
            start_i = max(0, m.start() - 1200)
            chunk = html[start_i:m.start()]
            pm = re.search(r"/post/([a-f0-9]+)\.html", chunk)
            if not pm:
                pm = re.search(r"data-id='([a-f0-9]+)'", chunk)
            if not pm:
                continue
            pid = pm.group(1)
            text = re.sub(r"<[^>]+>", " ", raw)
            text = html_lib.unescape(text)
            text = re.sub(r"https?://\S+", " ", text)
            text = re.sub(r"#\w+", " ", text)
            text = re.sub(r"\{[^}]*\}", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) >= 4:
                text_map.setdefault(pid, text)

        # aria-label 备选
        aria_map = {}
        for m in re.finditer(
            r"href='/post/([a-f0-9]+)\.html[^']*'[^>]*aria-label='([^']*)'",
            html,
        ):
            lab = html_lib.unescape(m.group(2)).strip()
            lab = re.sub(r"\s*video\s*$", "", lab, flags=re.I).strip()
            if lab and lab.lower() != "video" and len(lab) >= 3:
                aria_map[m.group(1)] = lab

        def clean_title(title):
            if not title:
                return ""
            title = html_lib.unescape(title)
            title = re.split(r"\s*https?://", title)[0]
            title = re.sub(r"\{FULL[^}]*\}", "", title, flags=re.I)
            title = re.sub(r"\{?\s*FULL\s*HD\s*[^\s]*", "", title, flags=re.I)
            title = re.sub(r"[→\-]+\s*$", "", title).strip()
            title = re.sub(r"\{NEW\}\s*", "", title, flags=re.I)
            title = re.sub(r"\{[^}]*\}", " ", title)
            # 去掉标签但保留正文
            title = re.sub(r"#\w+", " ", title)
            title = re.sub(r"\s+", " ", title).strip(" -|")
            # 纯数字/hex 视为无效
            if re.fullmatch(r"[a-f0-9]{10,}", title, re.I):
                return ""
            if len(title) < 3:
                return ""
            return title

        # 主解析：带 title 的链接
        for m in re.finditer(
            r"href='/post/([a-f0-9]+)\.html[^']*'\s+title='([\s\S]*?)'",
            html,
        ):
            pid, title = m.group(1), m.group(2)
            if pid in seen:
                continue
            seen.add(pid)
            name = clean_title(title)
            if not name:
                name = clean_title(text_map.get(pid, ""))
            if not name:
                name = clean_title(aria_map.get(pid, ""))
            if not name:
                # 最后用 post 文本前缀，再不行用简短 id 标注
                name = text_map.get(pid) or aria_map.get(pid) or ("视频 " + pid[-6:])
            pic = pic_map.get(pid, "")
            if not pic:
                idx = m.start()
                chunk = html[max(0, idx - 2500): idx + 400]
                pm = re.search(r"data-src='(//[^']*%s[^']*)'" % pid, chunk)
                if pm:
                    pic = pm.group(1)
            if pic.startswith("//"):
                pic = "https:" + pic
            videos.append({
                "vod_id": self.host + "/post/%s.html" % pid,
                "vod_name": name[:100],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })
            if len(videos) >= 48:
                break

        # 无 title 属性的帖子
        if len(videos) < 10:
            for m in re.finditer(r"href='/post/([a-f0-9]+)\.html", html):
                pid = m.group(1)
                if pid in seen:
                    continue
                seen.add(pid)
                name = clean_title(text_map.get(pid, "")) or clean_title(aria_map.get(pid, ""))
                if not name:
                    name = text_map.get(pid) or ("视频 " + pid[-6:])
                pic = pic_map.get(pid, "")
                if pic.startswith("//"):
                    pic = "https:" + pic
                videos.append({
                    "vod_id": self.host + "/post/%s.html" % pid,
                    "vod_name": name[:100],
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "",
                })
                if len(videos) >= 48:
                    break
        return videos
