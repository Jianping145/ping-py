# -*- coding: utf-8 -*-
# 51瑟瑟短剧  flos-ubn-669t.xflooow8s701.cc/hwyayl  蜂蜜影视 Spider
# 列表 /vodtype/{id}/  /vodtype/{id}-{page}/
# 详情 /voddetail/{id}/  播放 /vodplay/{id}-{sid}-{nid}/  player_aaaa

import re
import json
import time
from urllib import parse
from urllib.request import Request, urlopen
from urllib.parse import urlparse, urljoin
import ssl
import html as html_lib

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def __init__(self):
            pass


# ===== 广告 variant 识别：只匹配明确的 ad/ads/adv 目录或 ad_ 前缀 =====
_AD_VARIANT_RE = re.compile(
    r"(?:^|[/_])(?:ad|ads|adv|advert|advertisement|advertise)(?:[/_.]|$)",
    re.I,
)


class Spider(BaseSpider):
    def __init__(self):
        self.name = "51瑟瑟短剧"
        self.host = "https://flos-ubn-669t.xflooow8s701.cc"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.host + "/hwyayl/",
        }
        self._ssl = None
        # 主分类（从站点导航提取）
        self.classes = [
            {"type_id": "66", "type_name": "成人短剧"},
            {"type_id": "45", "type_name": "在线一区"},
            {"type_id": "46", "type_name": "在线二区"},
            {"type_id": "47", "type_name": "在线三区"},
            {"type_id": "49", "type_name": "国产精品"},
            {"type_id": "55", "type_name": "国产乱伦"},
            {"type_id": "65", "type_name": "国产热瓜"},
            {"type_id": "72", "type_name": "国产高清"},
            {"type_id": "50", "type_name": "无码流出"},
            {"type_id": "51", "type_name": "日本高清"},
            {"type_id": "52", "type_name": "中文字幕"},
            {"type_id": "53", "type_name": "欧美极品"},
            {"type_id": "54", "type_name": "动漫精品"},
            {"type_id": "64", "type_name": "主播诱惑"},
            {"type_id": "63", "type_name": "良家少女"},
            {"type_id": "61", "type_name": "淫荡熟女"},
            {"type_id": "62", "type_name": "三级伦理"},
            {"type_id": "57", "type_name": "自拍偷拍"},
            {"type_id": "58", "type_name": "旗袍风情"},
            {"type_id": "59", "type_name": "岛国小女"},
            {"type_id": "68", "type_name": "剧情解说"},
            {"type_id": "71", "type_name": "网红黑料"},
            {"type_id": "73", "type_name": "清纯女生"},
            {"type_id": "70", "type_name": "同性世界"},
            {"type_id": "69", "type_name": "美乳妹妹"},
            {"type_id": "67", "type_name": "黑料网曝"},
            {"type_id": "56", "type_name": "SM变态"},
            {"type_id": "200", "type_name": "传媒系列"},
            {"type_id": "201", "type_name": "综合传媒"},
            {"type_id": "202", "type_name": "麻豆传媒"},
            {"type_id": "203", "type_name": "葫芦影业"},
            {"type_id": "204", "type_name": "猫爪影像"},
            {"type_id": "205", "type_name": "天美传媒"},
            {"type_id": "206", "type_name": "果冻传媒"},
            {"type_id": "207", "type_name": "91制片厂"},
            {"type_id": "208", "type_name": "蜜桃传媒"},
            {"type_id": "300", "type_name": "日本番号"},
            {"type_id": "350", "type_name": "综合番号"},
            {"type_id": "500", "type_name": "探花系列"},
            {"type_id": "511", "type_name": "综合探花"},
            {"type_id": "513", "type_name": "酒店"},
            {"type_id": "514", "type_name": "小宝寻花"},
            {"type_id": "515", "type_name": "午夜寻花"},
            {"type_id": "516", "type_name": "91系列"},
            {"type_id": "501", "type_name": "91沈先生"},
            {"type_id": "502", "type_name": "文轩探花"},
            {"type_id": "506", "type_name": "鸭哥探花"},
            {"type_id": "400", "type_name": "女优"},
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
        try:
            html = self.fetch(self.host + "/hwyayl/")
            extra = self._parse_nav(html)
            if extra:
                known = {c["type_id"] for c in self.classes}
                for e in extra:
                    if e["type_id"] not in known:
                        self.classes.append(e)
                        known.add(e["type_id"])
        except Exception as e:
            print("[hwy] home:", e)
        return {"class": self.classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host + "/hwyayl/"))}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = str(tid or "66").strip("/")
        try:
            url = self._list_url(tid, page)
            html = self.fetch(url)
            videos = self._parse_list(html)
            pagecount = 999 if videos else page
            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "pageCount": pagecount,
                "limit": 24,
                "total": pagecount * 24,
            }
        except Exception as e:
            print("[hwy] category:", e)
            return {"list": [], "page": page, "pagecount": 1, "pageCount": 1, "limit": 24, "total": 0}

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        url = self._detail_url(raw)
        try:
            html = self.fetch(url)
            if not html:
                return {"list": []}
            title = self._meta(html, "og:title") or self._tag_title(html)
            title = html_lib.unescape(title or "")
            title = re.sub(r"\s*[-_|].*$", "", title).strip() or "未知"
            pic = self._meta(html, "og:image") or ""
            if not pic:
                m = re.search(r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', html)
                if m:
                    pic = m.group(1)

            # 多线路 / 多集：/vodplay/{id}-{sid}-{nid}/
            lines = {}
            for m in re.finditer(
                r'href="(/vodplay/(\d+)-(\d+)-(\d+)/)"[^>]*>([^<]*)<',
                html,
            ):
                href, vid, sid, nid, name = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                name = html_lib.unescape(name or "").strip() or ("第%s集" % nid)
                name = re.sub(r"\s+", " ", name)
                key = "线路%s" % sid
                lines.setdefault(key, []).append("%s$%s" % (name, self.host + href))

            if not lines:
                m = re.search(r'href="(/vodplay/\d+-\d+-\d+/)"', html)
                if m:
                    lines["线路1"] = ["播放$%s" % (self.host + m.group(1))]
                else:
                    lines["线路1"] = ["播放$%s" % url]

            play_from, play_url = [], []
            for k in sorted(lines.keys()):
                eps = lines[k]
                by_nid = {}
                for item in eps:
                    m = re.search(r"/vodplay/\d+-\d+-(\d+)/", item)
                    nid = int(m.group(1)) if m else 0
                    name = item.split("$", 1)[0]
                    if nid not in by_nid or (len(name) < len(by_nid[nid].split("$")[0]) and "第" in name):
                        by_nid[nid] = item
                eps = [by_nid[n] for n in sorted(by_nid.keys())]
                play_from.append(k)
                play_url.append("#".join(eps))

            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": title.strip("《》"),
                    "vod_pic": self._proxy_pic(pic),
                    "vod_content": title,
                    "vod_remarks": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "type_name": "",
                    "vod_play_from": "$$$".join(play_from),
                    "vod_play_url": "$$$".join(play_url),
                }]
            }
        except Exception as e:
            print("[hwy] detail:", e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        if not id:
            return {"parse": 1, "url": self.host, "header": json.dumps(headers)}
        if self.isVideoFormat(id) or (id.startswith("http") and any(x in id for x in [".m3u8", ".mp4"])):
            url = id
            if ".m3u8" in url.lower():
                url = self._resolve_m3u8(url)
            if "://" in url:
                try:
                    pu = urlparse(url)
                    headers["Referer"] = "%s://%s/" % (pu.scheme, pu.netloc)
                    headers["Origin"] = "%s://%s" % (pu.scheme, pu.netloc)
                except Exception:
                    pass
            url = self._maybe_proxy_m3u8(url)
            return {
                "parse": 0,
                "jx": 0,
                "url": url,
                "header": json.dumps(headers),
            }

        url = id if id.startswith("http") else self._abs(id)
        try:
            html = self.fetch(url)
            src = self._extract_player(html or "")
            if not src:
                return {"parse": 1, "jx": 0, "url": url, "header": json.dumps(headers)}
            src = self._resolve_m3u8(src)
            headers["Referer"] = url
            if "://" in src:
                try:
                    pu = urlparse(src)
                    headers["Origin"] = "%s://%s" % (pu.scheme, pu.netloc)
                    headers["Referer"] = "%s://%s/" % (pu.scheme, pu.netloc)
                except Exception:
                    pass
            headers["User-Agent"] = self.headers["User-Agent"]
            src = self._maybe_proxy_m3u8(src)
            return {
                "parse": 0,
                "jx": 0,
                "url": src,
                "header": json.dumps(headers),
            }
        except Exception as e:
            print("[hwy] play:", e)
        return {"parse": 1, "jx": 0, "url": url, "header": json.dumps(headers)}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        q = parse.quote(str(key or "").strip())
        candidates = [
            "/vodsearch/%s----------%d---.html" % (q, page),
            "/index.php/vod/search/page/%d/wd/%s.html" % (page, q),
            "/vodsearch/-------------.html?wd=%s&page=%d" % (q, page),
        ]
        videos = []
        for path in candidates:
            try:
                html = self.fetch(self._abs(path))
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

    # ============================================================
    # localProxy：核心修复区
    # 规则：
    #   1) master → 只选非广告 variant，落到 media；若全部失败，返回原 master 重写
    #   2) media  → 重写所有相对路径 & KEY/MAP URI，不去端口，不过滤分片
    #   3) 不做广告过滤（宁可看广告，不可断正片）
    # ============================================================
    def localProxy(self, param):
        try:
            if not isinstance(param, dict):
                param = {"url": str(param or "")}
            url = param.get("url") or param.get("target") or ""
            ptype = str(param.get("type") or "")
            for _ in range(3):
                if "%" in (url or "") and ("http%" in url.lower() or url.startswith("%")):
                    url = parse.unquote(url)
            if not url.startswith("http"):
                return [400, "text/plain", b"bad url"]

            # ---------------- m3u8 ----------------
            if ptype in ("m3u8", "hls") or "m3u8" in url.lower():
                pu0 = urlparse(url)
                origin = "%s://%s/" % (pu0.scheme, pu0.netloc)
                body = self._fetch_m3u8(url, origin)
                if not body:
                    return [500, "text/plain", b"empty m3u8"]

                # Step 1: master → 选非广告 variant
                if "#EXT-X-STREAM-INF" in body:
                    media_url, media_body = self._pick_media_variant(url, body)
                    if media_url and media_body:
                        url = media_url
                        body = media_body
                        pu0 = urlparse(url)
                        origin = "%s://%s/" % (pu0.scheme, pu0.netloc)

                # Step 2: 重写媒体列表 / 或仍未落地的 master
                data = self._rewrite_m3u8(url, body)
                print("[hwy][proxy] m3u8 %s -> %d bytes" % (url, len(data)))
                return [200, "application/vnd.apple.mpegurl", data]

            # ---------------- 图片 ----------------
            candidates = [url]
            no_port = re.sub(r"(https?://[^/:]+):\d+", r"\1", url)
            if no_port != url:
                candidates = [no_port, url]
            last_err = b""
            for u in candidates:
                try:
                    body = self._fetch_bytes(u)
                    if not body or len(body) < 80:
                        continue
                    ctype = "image/jpeg"
                    if body[:8].startswith(b"\x89PNG"):
                        ctype = "image/png"
                    elif body[:4] == b"RIFF":
                        ctype = "image/webp"
                    elif body[:3] == b"GIF":
                        ctype = "image/gif"
                    return [200, ctype, body]
                except Exception as e:
                    last_err = str(e).encode("utf-8")
            return [500, "text/plain", last_err or b"fetch fail"]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    # ============================================================
    # m3u8 辅助方法
    # ============================================================
    def _fetch_m3u8(self, url, referer):
        try:
            req = Request(url, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": referer,
                "Accept": "*/*",
            })
            with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as e:
            print("[hwy][m3u8] fetch fail", url, e)
            return ""

    def _pick_media_variant(self, master_url, body):
        """从 master 里选出一个非广告的 media playlist。返回 (url, body) 或 (None, None)。"""
        pu = urlparse(master_url)
        variants = re.findall(
            r"#EXT-X-STREAM-INF:([^\r\n]*)[\r\n]+\s*([^\s#]+)",
            body,
        )
        if not variants:
            return None, None

        def bw(info):
            m = re.search(r"BANDWIDTH=(\d+)", info or "")
            return int(m.group(1)) if m else 0

        def is_ad(info, path):
            return bool(_AD_VARIANT_RE.search(path or "")) or bool(_AD_VARIANT_RE.search(info or ""))

        # 非广告优先，BANDWIDTH 降序
        cand = []
        for info, path in variants:
            path = path.strip()
            if path.startswith("//"):
                cand_url = "%s:%s" % (pu.scheme, path)
            elif path.startswith("/"):
                cand_url = "%s://%s%s" % (pu.scheme, pu.netloc, path)
            elif path.startswith("http"):
                cand_url = path
            else:
                cand_url = urljoin(master_url, path)
            cand.append({
                "url": cand_url,
                "is_ad": is_ad(info, path),
                "bw": bw(info),
            })
        cand.sort(key=lambda x: (x["is_ad"], -x["bw"]))  # 非广告优先，再按带宽降序

        for c in cand:
            cpu = urlparse(c["url"])
            sub_body = self._fetch_m3u8(c["url"], "%s://%s/" % (cpu.scheme, cpu.netloc))
            if not sub_body:
                continue
            # 子列表本身还是 master 的话，递归一层
            if "#EXT-X-STREAM-INF" in sub_body:
                u2, b2 = self._pick_media_variant(c["url"], sub_body)
                if u2 and b2:
                    return u2, b2
                continue
            return c["url"], sub_body
        return None, None

    def _rewrite_m3u8(self, base_url, body):
        """把 m3u8 里所有相对路径/URI 重写为绝对路径。不去端口，不删分片。"""
        pu = urlparse(base_url)
        root = "%s://%s" % (pu.scheme, pu.netloc)
        base = base_url.rsplit("/", 1)[0] + "/"
        scheme = pu.scheme

        def abs_url(u):
            u = (u or "").strip()
            if not u:
                return u
            if u.startswith("//"):
                return scheme + ":" + u
            if u.startswith("http://") or u.startswith("https://"):
                return u
            if u.startswith("/"):
                return root + u
            return urljoin(base, u)

        def rewrite_tag(tg):
            # 只重写 URI="..."，其它原样
            if 'URI="' in tg:
                tg = re.sub(
                    r'URI="([^"]*)"',
                    lambda m: 'URI="%s"' % abs_url(m.group(1)),
                    tg,
                )
            return tg

        out = []
        for line in body.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                out.append(rewrite_tag(s))
            else:
                out.append(abs_url(s))
        if not out:
            out = ["#EXTM3U"]
        return ("\n".join(out) + "\n").encode("utf-8")

    # ============================================================
    # 基础
    # ============================================================
    def _ssl_ctx(self):
        if self._ssl is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ssl = ctx
        return self._ssl

    def fetch(self, url, headers=None, retry=2):
        h = dict(self.headers)
        if headers:
            h.update(headers)
        last = None
        for _ in range(retry):
            try:
                req = Request(url, headers=h)
                with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
                    data = resp.read().decode("utf-8", "ignore")
                if data and (len(data) > 300 or "#EXTM3U" in data or data.strip().startswith("{")):
                    return data
            except Exception as e:
                last = e
                time.sleep(0.12)
        print("[hwy] fetch fail", url, last)
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
        if re.match(r"^\d+$", tid):
            if page <= 1:
                return self._abs("/vodtype/%s/" % tid)
            return self._abs("/vodtype/%s-%d/" % (tid, page))
        if page <= 1:
            return self._abs("/" + tid + "/")
        return self._abs("/%s-%d/" % (tid, page))

    def _detail_url(self, raw):
        raw = str(raw or "").strip()
        if raw.startswith("http"):
            return raw
        if raw.startswith("/"):
            return self._abs(raw)
        if re.match(r"^\d+$", raw):
            return self._abs("/voddetail/%s/" % raw)
        return self._abs("/" + raw.lstrip("/"))

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        if not pic.startswith("http"):
            pic = self._abs(pic)
        # 图片去非标端口（手机端 :3519 加载失败）
        pic = re.sub(r"(https?://[^/:]+):\d+", r"\1", pic)
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    return "%s&url=%s#.jpg" % (base, parse.quote(pic, safe=""))
        except Exception:
            pass
        return pic

    def _meta(self, html, prop):
        m = re.search(
            r'property=["\']%s["\'][^>]+content=["\']([^"\']+)' % re.escape(prop),
            html or "", re.I,
        )
        return html_lib.unescape(m.group(1).strip()) if m else ""

    def _tag_title(self, html):
        t = re.search(r"<title[^>]*>([^<]+)</title>", html or "", re.I)
        return html_lib.unescape(t.group(1).strip()) if t else ""

    def _parse_nav(self, html):
        out, seen = [], set()
        for m in re.finditer(r'href="(/vodtype/(\d+)/?)"[^>]*>(.*?)</a>', html or "", re.S):
            tid = m.group(2)
            if tid in seen:
                continue
            name = re.sub(r"<[^>]+>", "", m.group(3))
            name = html_lib.unescape(name).strip()
            if not name or name in ("更多",) or len(name) > 12:
                continue
            seen.add(tid)
            out.append({"type_id": tid, "type_name": name})
        return out

    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()
        blocks = re.findall(r"<li>\s*<a class=\"thumbnail\"[\s\S]*?</li>", html or "")
        if not blocks:
            blocks = re.findall(r"class=\"thumbnail\"[\s\S]{0,2500}?class=\"video-info\"[\s\S]{0,800}?</li>", html or "")
        for block in blocks:
            m = re.search(r'href="(/voddetail/(\d+)/)"', block)
            if not m:
                continue
            path, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)

            title = ""
            for pat in [r'alt="([^"]*)"', r'title="([^"]*)"', r"<h5[^>]*>\s*<a[^>]*>([\s\S]*?)</a>"]:
                tm = re.search(pat, block)
                if not tm:
                    continue
                cand = html_lib.unescape(tm.group(1))
                cand = re.sub(r"<[^>]+>", "", cand)
                cand = re.sub(r"\s+", " ", cand).strip()
                if cand and not re.fullmatch(r"\d+", cand):
                    title = cand
                    break
            title = title.strip("《》").strip()
            if len(title) > 80:
                title = title[:80] + "…"
            if not title:
                title = "视频" + vid

            pic = ""
            pm = re.search(r"--bg:url\(['\"]?(https?://[^'\"\s\)]+)", block)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'(?:data-src|src)="(https?://[^"]+)"', block, re.I)
                if pm:
                    pic = pm.group(1)
            if pic.startswith("//"):
                pic = "https:" + pic
            pic = (pic or "").strip()

            videos.append({
                "vod_id": self._abs(path),
                "vod_name": title,
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })
            if len(videos) >= 48:
                break

        if not videos:
            for m in re.finditer(r'href="(/voddetail/(\d+)/)"', html):
                path, vid = m.group(1), m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                win = html[m.start(): m.start() + 2000]
                title, pic = "", ""
                for pat in [r'alt="([^"]*)"', r'title="([^"]*)"']:
                    tm = re.search(pat, win)
                    if tm:
                        cand = html_lib.unescape(tm.group(1)).strip()
                        if cand and not re.fullmatch(r"\d+", cand):
                            title = cand
                            break
                title = (title.strip("《》") or ("视频" + vid))[:80]
                pm = re.search(r"--bg:url\(['\"]?(https?://[^'\"\s\)]+)", win)
                if not pm:
                    pm = re.search(r'src="(https?://[^"]+)"', win)
                if pm:
                    pic = pm.group(1)
                videos.append({
                    "vod_id": self._abs(path),
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(pic),
                    "vod_remarks": "",
                })
                if len(videos) >= 48:
                    break
        return videos

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

    def _resolve_m3u8(self, url):
        """playerContent 阶段先把 master 落到 media，减少代理端的处理成本。"""
        if not url or ".m3u8" not in url.lower():
            return url
        try:
            pu0 = urlparse(url)
            origin = "%s://%s/" % (pu0.scheme, pu0.netloc)
            body = self._fetch_m3u8(url, origin)
            if not body or "#EXT-X-STREAM-INF" not in body:
                return url
            media_url, media_body = self._pick_media_variant(url, body)
            if media_url:
                return media_url
            return url
        except Exception as e:
            print("[hwy] resolve m3u8:", e)
            return url

    def _extract_player(self, html):
        m = re.search(r"player_[a-zA-Z0-9]+\s*=\s*(\{.+?\})\s*;?\s*</script>", html or "", re.S)
        if not m:
            m = re.search(r"player_[a-zA-Z0-9]+\s*=\s*(\{.+?\})", html or "", re.S)
        if m:
            blob = m.group(1)
            um = re.search(r'"url"\s*:\s*"([^"]+)"', blob)
            if um:
                u = um.group(1).replace("\\/", "/")
                u = parse.unquote(u)
                em = re.search(r'"encrypt"\s*:\s*(\d+)', blob)
                if em and em.group(1) in ("1", "2") and not u.startswith("http"):
                    try:
                        import base64
                        u2 = base64.b64decode(u).decode("utf-8", "ignore")
                        if u2.startswith("http") or u2.startswith("//"):
                            u = u2
                    except Exception:
                        pass
                if u.startswith("//"):
                    u = "https:" + u
                if u.startswith("http"):
                    return u
        for u in re.findall(r'https?://[^"\'\\]+\.m3u8[^"\'\\]*', html or ""):
            return u.replace("\\/", "/")
        for u in re.findall(r'https?://[^"\'\\]+\.mp4[^"\'\\]*', html or ""):
            return u.replace("\\/", "/")
        return ""