# -*- coding: utf-8 -*-
# LustPlus 撸社 https://www.lustplus.tv  蜂蜜影视 Spider
# API: https://api.lustplus.tv

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
        self.name = "LustPlus撸社"
        self.host = "https://www.lustplus.tv"
        self.api = "https://api.lustplus.tv"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": self.host,
            "Referer": self.host + "/",
        }
        self._ssl = None
        self.classes = [
            {"type_id": "latest", "type_name": "最新"},
            {"type_id": "hot", "type_name": "今日热门"},
            {"type_id": "shorts", "type_name": "短视频"},
        ]

    def getName(self):
        return self.name

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(x in (url or "").lower() for x in [".m3u8", ".mp4", ".flv"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        classes = [
            {"type_id": "latest", "type_name": "最新"},
            {"type_id": "hot", "type_name": "今日热门"},
            {"type_id": "shorts", "type_name": "短视频"},
        ]
        known = {c["type_id"] for c in classes}
        try:
            data = self._api_json("/api/videos/categories")
            for c in (data or {}).get("list") or []:
                if not c.get("enabled", 1):
                    continue
                tid = str(c.get("slug") or c.get("id") or "")
                name = (c.get("name") or tid).strip()
                if not tid or tid in known:
                    continue
                known.add(tid)
                classes.append({"type_id": tid, "type_name": name})
        except Exception as e:
            print("[lust] cats:", e)
        try:
            data = self._api_json("/api/search/tags")
            tags = sorted((data or {}).get("list") or [], key=lambda x: int(x.get("count") or 0), reverse=True)
            for tg in tags:
                name = (tg.get("tag") or "").strip()
                if not name or int(tg.get("count") or 0) < 10:
                    continue
                tid = "tag:" + name
                if tid in known or any(c["type_name"] == name for c in classes):
                    continue
                known.add(tid)
                classes.append({"type_id": tid, "type_name": name})
        except Exception as e:
            print("[lust] tags:", e)
        self.classes = classes
        return {"class": classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            data = self._api_json("/api/videos", {"page": 1, "limit": 24})
            return {"list": self._map_list((data or {}).get("list") or [])}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = str(tid or "latest").strip()
        videos, total = [], 0
        try:
            if tid in ("latest", "all", ""):
                data = self._api_json("/api/videos", {"page": page, "limit": 24})
            elif tid in ("hot", "hot-today"):
                data = self._api_json("/api/videos/hot-today")
                if isinstance(data, list):
                    return self._page(self._map_list(data), page, len(data))
                data = data or {}
            elif tid in ("shorts", "short"):
                data = self._api_json("/api/videos/shorts/type", {"page": page, "limit": 24})
            elif tid.startswith("tag:"):
                data = self._api_json("/api/videos/type", {"tag": tid[4:].strip(), "page": page, "limit": 24})
            else:
                data = self._api_json("/api/videos/type", {"category": tid, "page": page, "limit": 24})
            lst = (data or {}).get("list") or []
            total = int((data or {}).get("total") or 0)
            videos = self._map_list(lst)
        except Exception as e:
            print("[lust] category:", e)
        return self._page(videos, page, total)

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        vid = str(raw).strip()
        data = self._api_json("/api/videos/%s" % parse.quote(vid))
        if not data:
            return {"list": []}
        title = (data.get("title") or "").strip("《》") or "未知"
        pic = data.get("thumbnail") or data.get("thumbnail_small") or ""
        content = data.get("content") or ""
        remarks = data.get("remarks") or data.get("duration") or ""
        type_name = data.get("type_name") or ""
        play_url = data.get("play_url") or ""

        episodes = []
        for part in (play_url or "").split("#"):
            part = part.strip()
            if not part:
                continue
            if "$" in part:
                name, url = part.split("$", 1)
            else:
                name, url = "正片", part
            name, url = name.strip() or "正片", url.strip()
            if url:
                episodes.append((name, url))
        if not episodes:
            return {"list": []}

        # 多清晰度线路：默认 + 主m3u8里的各码率
        line_names, line_urls = [], []
        line_names.append("默认")
        line_urls.append("#".join("%s$%s" % (n, u) for n, u in episodes))

        qualities = self._parse_qualities(episodes[0][1])
        for qname, qurl in qualities:
            parts = []
            for n, u in episodes:
                parts.append("%s$%s" % (n, self._swap_quality(u, qurl, episodes[0][1])))
            line_names.append(qname)
            line_urls.append("#".join(parts))

        # 去重
        seen, names2, urls2 = set(), [], []
        for n, u in zip(line_names, line_urls):
            if u in seen:
                continue
            seen.add(u)
            names2.append(n)
            urls2.append(u)

        return {
            "list": [{
                "vod_id": str(data.get("id") or vid),
                "vod_name": title,
                "vod_pic": self._proxy_pic(pic),
                "vod_content": content,
                "vod_remarks": remarks,
                "vod_year": "",
                "vod_area": "",
                "vod_actor": "",
                "vod_director": "",
                "type_name": type_name,
                "vod_play_from": "$$$".join(names2),
                "vod_play_url": "$$$".join(urls2),
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
        if self.isVideoFormat(url) or url.startswith("http"):
            if "://" in url:
                try:
                    pu = parse.urlparse(url)
                    headers["Referer"] = "%s://%s/" % (pu.scheme, pu.netloc)
                    headers["Origin"] = "%s://%s" % (pu.scheme, pu.netloc)
                except Exception:
                    pass
            if ".m3u8" in url.lower():
                url = self._resolve_m3u8(url)
                url = self._maybe_proxy_m3u8(url)
            return {"parse": 0, "jx": 0, "url": url, "header": json.dumps(headers)}
        return {"parse": 1, "jx": 0, "url": url, "header": json.dumps(headers)}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        videos, total = [], 0
        try:
            data = self._api_json("/api/videos/actions/search", {
                "keyword": str(key or "").strip(), "page": page, "limit": 24
            })
            videos = self._map_list((data or {}).get("list") or [])
            total = int((data or {}).get("total") or 0)
        except Exception as e:
            print("[lust] search:", e)
        return self._page(videos, page, total)

    def localProxy(self, param):
        try:
            if not isinstance(param, dict):
                param = {"url": str(param or "")}
            url = param.get("url") or ""
            ptype = str(param.get("type") or "")
            for _ in range(3):
                if "%" in (url or "") and ("http%" in url.lower() or url.startswith("%")):
                    url = parse.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b"bad url"]

            if ptype == "m3u8" or "m3u8" in url.lower():
                text = self._fetch_text(url) or ""
                if not text:
                    return [500, "text/plain", b"empty m3u8"]
                if "#EXT-X-STREAM-INF" in text:
                    url2 = self._resolve_m3u8(url)
                    if url2 != url:
                        text = self._fetch_text(url2) or text
                        url = url2
                pu = parse.urlparse(url)
                root = "%s://%s" % (pu.scheme, pu.netloc)
                base = url.rsplit("/", 1)[0] + "/"
                parts = [x for x in pu.path.split("/") if x]
                main_token = ""
                for i, pth in enumerate(parts):
                    if re.match(r"^\d{8}$", pth) and i + 1 < len(parts):
                        main_token = parts[i + 1]
                        break
                if not main_token and len(parts) >= 2:
                    main_token = parts[1]

                def abs_url(u):
                    u = (u or "").strip()
                    if not u:
                        return u
                    if u.startswith("//"):
                        u = "https:" + u
                    elif u.startswith("/"):
                        u = root + u
                    elif not u.startswith("http"):
                        u = base + u
                    return re.sub(r"(https?://[^/:]+):\d+", r"\1", u)

                entries, buf = [], []
                for line in text.splitlines():
                    s = line.strip()
                    if not s:
                        continue
                    if s.startswith("#"):
                        if s.startswith(("#EXTM3U", "#EXT-X-VERSION", "#EXT-X-TARGETDURATION",
                                         "#EXT-X-MEDIA-SEQUENCE", "#EXT-X-PLAYLIST-TYPE", "#EXT-X-ENDLIST")):
                            continue
                        buf.append(s)
                        continue
                    entries.append((buf, s))
                    buf = []

                if main_token:
                    filtered = [(tg, sg) for tg, sg in entries if main_token in sg]
                    if len(filtered) >= 5:
                        entries = filtered

                out = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-X-PLAYLIST-TYPE:VOD", "#EXT-X-TARGETDURATION:10"]
                for tags, seg in entries:
                    for tg in tags:
                        if 'URI="' in tg:
                            tg = re.sub(r'URI="([^"]+)"', lambda m: 'URI="%s"' % abs_url(m.group(1)), tg)
                        out.append(tg)
                    out.append(abs_url(seg))
                out.append("#EXT-X-ENDLIST")
                return [200, "application/vnd.apple.mpegurl", ("\n".join(out) + "\n").encode("utf-8")]

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

    def _api_json(self, path, params=None):
        url = path if path.startswith("http") else (self.api + path)
        if params:
            url = url + ("&" if "?" in url else "?") + parse.urlencode(params, encoding="utf-8")
        last = None
        for _ in range(2):
            try:
                req = Request(url, headers=self.headers)
                with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
                    body = resp.read().decode("utf-8", "ignore")
                j = json.loads(body)
                if isinstance(j, dict) and "data" in j:
                    return j.get("data")
                return j
            except Exception as e:
                last = e
                time.sleep(0.12)
        print("[lust] api fail", path, last)
        return {}

    def _fetch_bytes(self, url):
        req = Request(url, headers={"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"})
        with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
            return resp.read() or b""

    def _fetch_text(self, url):
        try:
            return self._fetch_bytes(url).decode("utf-8", "ignore")
        except Exception as e:
            print("[lust] fetch_text:", e)
            return ""

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

    def _map_list(self, lst):
        out = []
        for it in lst or []:
            vid = str(it.get("id") or it.get("vod_id") or "")
            if not vid:
                continue
            title = (it.get("title") or "").strip("《》") or ("视频" + vid)
            pic = it.get("thumbnail") or it.get("thumbnail_small") or ""
            remarks = it.get("remarks") or it.get("duration") or it.get("type_name") or ""
            out.append({
                "vod_id": vid,
                "vod_name": title[:100],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": str(remarks)[:40],
            })
        return out

    def _page(self, videos, page, total=0):
        videos = videos or []
        if total and total > 0:
            pagecount = max(1, (int(total) + 23) // 24)
        else:
            pagecount = page + 1 if videos else page
            if videos and len(videos) >= 20:
                pagecount = max(page + 5, pagecount)
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 24,
            "total": int(total) if total else pagecount * 24,
        }

    def _parse_qualities(self, m3u8_url):
        if not m3u8_url or ".m3u8" not in m3u8_url.lower():
            return []
        try:
            body = self._fetch_text(m3u8_url)
            if not body or "#EXT-X-STREAM-INF" not in body:
                return []
            variants = re.findall(r"#EXT-X-STREAM-INF:([^\n]*)\n\s*([^\s#]+)", body)
            if not variants:
                return []

            def bw(info):
                m = re.search(r"BANDWIDTH=(\d+)", info or "")
                return int(m.group(1)) if m else 0

            def res_h(info):
                m = re.search(r"RESOLUTION=\d+x(\d+)", info or "")
                return int(m.group(1)) if m else 0

            variants = sorted(variants, key=lambda x: (bw(x[0]), res_h(x[0])), reverse=True)
            pu = parse.urlparse(m3u8_url)
            root = "%s://%s" % (pu.scheme, pu.netloc)
            base = m3u8_url.rsplit("/", 1)[0] + "/"
            out = []
            for info, path in variants:
                path = path.strip()
                if path.startswith("http"):
                    qurl = path
                elif path.startswith("/"):
                    qurl = root + path
                else:
                    qurl = base + path
                h, b = res_h(info), bw(info)
                km = re.search(r"/(\d+)kb/", path)
                if h and km:
                    name = "%dp-%skb" % (h, km.group(1))
                elif km:
                    name = km.group(1) + "kb"
                elif h >= 1080:
                    name = "1080P"
                elif h >= 720:
                    name = "720P"
                elif h >= 480:
                    name = "480P"
                elif b >= 2000000:
                    name = "高清"
                else:
                    name = "标清"
                out.append((name, qurl))
            return out
        except Exception as e:
            print("[lust] qualities:", e)
            return []

    def _swap_quality(self, ep_url, quality_url, template_url):
        if not ep_url or not quality_url:
            return ep_url or quality_url
        if ep_url == template_url:
            return quality_url
        try:
            tbase = template_url.rsplit("/", 1)[0]
            if quality_url.startswith(tbase):
                return ep_url.rsplit("/", 1)[0] + quality_url[len(tbase):]
        except Exception:
            pass
        return ep_url

    def _resolve_m3u8(self, url):
        if not url or ".m3u8" not in url.lower():
            return url
        try:
            body = self._fetch_text(url)
            if not body or "#EXT-X-STREAM-INF" not in body:
                return url
            variants = re.findall(r"#EXT-X-STREAM-INF:([^\n]*)\n\s*([^\s#]+)", body)
            if not variants:
                return url

            def bw(info):
                m = re.search(r"BANDWIDTH=(\d+)", info or "")
                return int(m.group(1)) if m else 0

            variants = sorted(variants, key=lambda x: bw(x[0]), reverse=True)
            path = variants[0][1].strip()
            if path.startswith("http"):
                return path
            pu = parse.urlparse(url)
            if path.startswith("/"):
                return "%s://%s%s" % (pu.scheme, pu.netloc, path)
            return url.rsplit("/", 1)[0] + "/" + path
        except Exception:
            return url

    def _maybe_proxy_m3u8(self, url):
        if not url or ".m3u8" not in url.lower():
            return url
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base:
                    return "%s&url=%s&type=m3u8" % (base, parse.quote(url, safe=""))
        except Exception:
            pass
        return url
