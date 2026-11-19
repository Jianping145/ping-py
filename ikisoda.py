# -*- coding: utf-8 -*-
# Ikisoda https://ikisoda.com  蜂蜜影视(FongMi) Spider

import re
import json
import time
from urllib import parse
from urllib.request import Request, urlopen
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
        self.name = "Ikisoda"
        self.host = "https://ikisoda.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://ikisoda.com/",
        }
        self._ssl = None
        # 常见分类中文对照
        self.cat_zh = {
            "masturbation": "自慰",
            "creampie": "中出",
            "big-tits": "巨乳",
            "beautiful-girl": "美少女",
            "married-woman": "人妻",
            "slut": "痴女",
            "slender": "苗条",
            "blowjob": "口交",
            "squirting": "潮吹",
            "deep-throat": "深喉",
            "anal": "肛交",
            "cuckold": "绿帽",
            "amateur": "素人",
            "cosplay": "角色扮演",
            "orgy": "乱交",
            "cowgirl": "骑乘",
            "pov": "主观视角",
            "handjob": "手交",
            "sister": "姐妹",
            "female-college-student": "女大学生",
            "massage": "按摩",
            "huge-tits": "超巨乳",
            "office-lady": "OL",
            "nurse": "护士",
            "lingerie": "情趣内衣",
            "facial": "颜射",
            "hardcore": "激烈",
            "swimsuit": "泳装",
            "underwear": "内衣",
            "bath": "浴室",
            "lesbian": "女同",
            "bondage": "捆绑",
            "uniform": "制服",
            "idol": "偶像",
            "teacher": "教师",
            "rape": "强制",
            "virgin": "处男/女",
            "pantyhose": "裤袜",
            "footjob": "足交",
            "pregnant": "孕妇",
            "elderly-man": "熟男",
            "kimono": "和服",
            "school": "校园",
            "cheating-wife": "出轨人妻",
        }

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
            {"type_id": "videos", "type_name": "最新"},
            {"type_id": "videos_viewed", "type_name": "最多播放"},
            {"type_id": "videos_rating", "type_name": "高分"},
        ]
        known = {c["type_id"] for c in classes}
        try:
            html = self.fetch(self.host + "/categories/")
            slugs = []
            for m in re.finditer(
                r'href="(?:https://ikisoda\.com)?/categories/([a-z0-9-]+)/"[^>]*>',
                html or "",
            ):
                slug = m.group(1)
                if slug.isdigit() or slug in known:
                    continue
                if slug in slugs:
                    continue
                slugs.append(slug)
            # 演员排在「自慰」等分类前面
            classes.append({"type_id": "models", "type_name": "演员"})
            known.add("models")
            for slug in slugs:
                name = self.cat_zh.get(slug) or slug.replace("-", " ").title()
                classes.append({"type_id": "cat:" + slug, "type_name": name})
                known.add("cat:" + slug)
        except Exception as e:
            print("[iki] cats:", e)
            if not any(c["type_id"] == "models" for c in classes):
                classes.append({"type_id": "models", "type_name": "演员"})
        return {"class": classes, "list": [], "filters": {}}

    def homeVideoContent(self):
        try:
            html = self.fetch(self.host + "/videos/?sort_by=post_date")
            return {"list": self._parse_list(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        tid = str(tid or "videos").strip()
        videos = []
        try:
            if tid in ("videos", "latest", "all", ""):
                url = self.host + "/videos/?sort_by=post_date"
                if page > 1:
                    url = self.host + "/videos/%d/?sort_by=post_date" % page
                html = self.fetch(url)
                videos = self._parse_list(html)
            elif tid in ("videos_viewed", "popular"):
                url = self.host + "/videos/?sort_by=video_viewed"
                if page > 1:
                    url = self.host + "/videos/%d/?sort_by=video_viewed" % page
                html = self.fetch(url)
                videos = self._parse_list(html)
            elif tid in ("videos_rating", "rating"):
                url = self.host + "/videos/?sort_by=rating"
                if page > 1:
                    url = self.host + "/videos/%d/?sort_by=rating" % page
                html = self.fetch(url)
                videos = self._parse_list(html)
            elif tid in ("models", "actress", "actors"):
                # 演员列表
                url = self.host + "/jav-models/?models_per_page=30&sort_by=video_viewed_count&type=actress"
                if page > 1:
                    url = self.host + "/jav-models/%d/?models_per_page=30&sort_by=video_viewed_count&type=actress" % page
                html = self.fetch(url)
                videos = self._parse_models(html)
            elif tid.startswith("model:"):
                # 某演员作品网格
                slug = tid[6:].strip()
                url = self.host + "/jav-models/%s/" % slug
                if page > 1:
                    url = self.host + "/jav-models/%s/%d/?videos_per_page=30&sort_by=custom1" % (slug, page)
                html = self.fetch(url)
                videos = self._parse_list(html)
            elif tid.startswith("cat:"):
                slug = tid[4:]
                url = self.host + "/categories/%s/" % slug
                if page > 1:
                    url = self.host + "/categories/%s/%d/" % (slug, page)
                html = self.fetch(url)
                videos = self._parse_list(html)
            else:
                url = self.host + "/videos/?sort_by=post_date"
                html = self.fetch(url)
                videos = self._parse_list(html)
        except Exception as e:
            print("[iki] category:", e)
        # 粗略翻页：有满页则认为还有下一页
        pagecount = page + 1 if len(videos) >= 20 else page
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 36,
            "total": pagecount * 36,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else str(ids)
        raw = str(raw).strip()

        # 演员页：作品列表作为选集
        if raw.startswith("model:") or "/jav-models/" in raw:
            return self._detail_model(raw)

        url = raw if raw.startswith("http") else (self.host + raw)
        if "/videos/" not in url:
            url = self.host + "/videos/" + raw.strip("/") + "/"
        try:
            html = self.fetch(url)
        except Exception as e:
            print("[iki] detail:", e)
            return {"list": []}
        if not html:
            return {"list": []}

        title = ""
        for pat in [
            r'property="og:title" content="([^"]+)"',
            r"<h1[^>]*>([^<]+)</h1>",
            r'class="is-title[^"]*"[^>]*>([^<]+)',
        ]:
            m = re.search(pat, html)
            if m:
                title = html_lib.unescape(m.group(1)).strip()
                break
        title = title or "Ikisoda"

        pic = ""
        m = re.search(r'property="og:image" content="([^"]+)"', html)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'data-original="(https://[^"]+videos_screenshots[^"]+)"', html)
            if m:
                pic = m.group(1)

        # license_code for KVS get_file decrypt
        license_code = ""
        lm = re.search(r"license_code:\s*'([^']+)'", html)
        if lm:
            license_code = lm.group(1)
            self._last_license = license_code

        # KTPlayer flashvars
        plays = []  # (name, url)
        # primary
        m = re.search(r"video_url\s*:\s*'([^']+)'", html)
        if m:
            u = self._clean_play(m.group(1), license_code)
            if u:
                plays.append(("360p", u))
        # alts
        alts = re.findall(r"video_alt_url(\d*)\s*:\s*'([^']+)'", html)
        texts = re.findall(r"video_alt_url(\d*)_text\s*:\s*'([^']+)'", html)
        text_map = {k: v for k, v in texts}
        for num, rawu in alts:
            u = self._clean_play(rawu, license_code)
            if not u:
                continue
            name = text_map.get(num) or ("线路" + (num or "1"))
            plays.append((name, u))
        # fallback: any get_file mp4 not preview
        if not plays:
            for u in re.findall(r"https://ikisoda\.com/get_file/[^\"'\s]+?\.mp4/", html):
                if "preview" in u:
                    continue
                name = "720p" if "720" in u else ("360p" if "360" in u else "播放")
                plays.append((name, u))
                if len(plays) >= 3:
                    break

        # 去重，高清优先排序
        def qkey(name):
            m = re.search(r"(\d{3,4})", name)
            return int(m.group(1)) if m else 0

        seen = set()
        uniq = []
        for n, u in sorted(plays, key=lambda x: qkey(x[0]), reverse=True):
            if u in seen:
                continue
            seen.add(u)
            uniq.append((n, u))
        if not uniq:
            uniq = [("播放", url)]

        play_url = "#".join("%s$%s" % (n, u) for n, u in uniq)
        # content
        content = ""
        m = re.search(r'property="og:description" content="([^"]+)"', html)
        if m:
            content = html_lib.unescape(m.group(1))

        return {
            "list": [{
                "vod_id": url,
                "vod_name": title[:120],
                "vod_pic": self._proxy_pic(pic),
                "vod_content": content[:500],
                "vod_remarks": "",
                "vod_year": "",
                "vod_area": "日本",
                "vod_actor": "",
                "vod_director": "",
                "type_name": "JAV",
                "vod_play_from": "Ikisoda",
                "vod_play_url": play_url,
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

        # 选集里是视频详情页时，先解析出真实 mp4
        if "/videos/" in url and not self.isVideoFormat(url):
            try:
                html = self.fetch(url)
                license_code = ""
                lm = re.search(r"license_code:\s*'([^']+)'", html or "")
                if lm:
                    license_code = lm.group(1)
                    self._last_license = license_code
                candidates = []
                for m in re.finditer(r"video(?:_alt)?_url\d*\s*:\s*'([^']+)'", html or ""):
                    rawu = m.group(1)
                    if "function/" in rawu or "get_file" in rawu:
                        candidates.append(rawu)
                # 优先 720
                chosen = ""
                for rawu in candidates:
                    if "720" in rawu:
                        chosen = self._clean_play(rawu, license_code)
                        break
                if not chosen and candidates:
                    chosen = self._clean_play(candidates[-1], license_code)
                if chosen:
                    url = chosen
            except Exception as e:
                print("[iki] play parse:", e)

        if url.startswith("function/"):
            url = self._clean_play(url, getattr(self, "_last_license", "") or "")
        if self.isVideoFormat(url) or (url.startswith("http") and "get_file" in url):
            return {
                "parse": 0,
                "jx": 0,
                "url": url,
                "header": json.dumps(headers),
            }
        if url.startswith("http"):
            return {
                "parse": 0,
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
            q = parse.quote(key)
            url = self.host + "/search/%s/" % q
            if page > 1:
                url = self.host + "/search/%s/%d/" % (q, page)
            html = self.fetch(url)
            videos = self._parse_list(html)
        except Exception as e:
            print("[iki] search:", e)
        pagecount = page + 1 if len(videos) >= 20 else page
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "pageCount": pagecount,
            "limit": 36,
            "total": pagecount * 36,
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

    def fetch(self, url):
        last = None
        for _ in range(2):
            try:
                req = Request(url, headers=self.headers)
                with urlopen(req, timeout=20, context=self._ssl_ctx()) as resp:
                    return resp.read().decode("utf-8", "ignore")
            except Exception as e:
                last = e
                time.sleep(0.15)
        print("[iki] fetch fail", url, last)
        return ""

    def _fetch_bytes(self, url):
        req = Request(url, headers={
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
        })
        with urlopen(req, timeout=18, context=self._ssl_ctx()) as resp:
            return resp.read() or b""

    def _clean_play(self, u, license_code=""):
        u = (u or "").strip()
        if not u:
            return ""
        # 非 function/ 前缀直接返回
        if not u.startswith("function/"):
            return u
        # KVS / KT Player license_code 解密 get_file 哈希
        return self._kvs_decode(u, license_code or self._last_license or "")

    def _kvs_decode(self, vu, lc, hr="16"):
        """Cumination/KVS function/0/ URL 解密"""
        import time as _time
        if not vu:
            return vu
        if not vu.startswith("function/"):
            return vu

        def calcseed(lc, hr):
            f = lc.replace("$", "").replace("0", "1")
            j = int(len(f) / 2)
            k = int(f[0:j + 1])
            el = int(f[j:])
            fi = abs(el - k) * 4
            s = str(fi)
            i = int(int(hr) / 2) + 2
            m = ""
            for g2 in range(j + 1):
                for h in range(1, 5):
                    n = int(lc[g2 + h]) + int(s[g2])
                    if n >= i:
                        n -= i
                    m += str(n)
            return m

        http_url = vu[vu.find("http"):]
        mo = re.search(r"(/get_file/\d+/)([0-9a-f]+)(/[^?\s]*)", http_url, re.I)
        if not mo:
            return http_url
        if not lc:
            # 无 license 时仍尝试去掉 function 前缀
            return http_url
        fullhash = mo.group(2)
        uhash = fullhash[0:2 * int(hr)]
        nchash = fullhash[2 * int(hr):]
        seed = calcseed(lc, hr)
        if seed and uhash:
            for k in range(len(uhash) - 1, -1, -1):
                el = k
                for mm in range(k, len(seed)):
                    el += int(seed[mm])
                while el >= len(uhash):
                    el -= len(uhash)
                n = ""
                for o in range(len(uhash)):
                    n += uhash[el] if o == k else uhash[k] if o == el else uhash[o]
                uhash = n
            newhash = uhash + nchash
            http_url = http_url[:mo.start(2)] + newhash + http_url[mo.end(2):]
        if http_url.endswith("/"):
            http_url = http_url[:-1]
        http_url += "?rnd=%d" % int(_time.time() * 1000)
        return http_url

    def _proxy_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        # 文件名含空格会导致客户端无法加载
        try:
            pu = parse.urlsplit(pic)
            path = parse.quote(pu.path, safe="/:@")
            pic = parse.urlunsplit((pu.scheme, pu.netloc, path, pu.query, pu.fragment))
        except Exception:
            pic = pic.replace(" ", "%20")
        try:
            if hasattr(self, "getProxyUrl"):
                base = self.getProxyUrl()
                if base and pic.startswith("http"):
                    return "%s&url=%s" % (base, parse.quote(pic, safe=""))
        except Exception:
            pass
        return pic


    def _parse_models(self, html):
        """演员列表"""
        if not html:
            return []
        html = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]{100,}", "BASE64", html)
        videos, seen = [], set()
        for m in re.finditer(
            r'href="(https://ikisoda\.com/jav-models/([a-z0-9-]+)/)"[^>]*class="is-item-link"([\s\S]{0,1800}?is-info-count-videos[\s\S]{0,80}?(\d+)\s*videos)?',
            html,
        ):
            url, slug = m.group(1), m.group(2)
            block = m.group(0)
            if slug.isdigit() or slug in seen:
                continue
            seen.add(slug)
            title = ""
            tm = re.search(r'alt="([^"]+)"', block)
            if tm:
                title = html_lib.unescape(tm.group(1)).strip()
            if not title:
                tm = re.search(r'is-item-title[^>]*>([\s\S]*?)</div>', block)
                if tm:
                    title = re.sub(r"<[^>]+>", " ", tm.group(1))
                    title = re.sub(r"\s+", " ", title).strip()
                    title = re.sub(r"^#\d+\s*", "", title)
            if not title:
                title = slug.replace("-", " ").title()
            pic = ""
            pm = re.search(r'data-original="(https://[^"]+)"', block)
            if pm:
                pic = pm.group(1)
            remarks = ""
            rm = re.search(r'(\d+)\s*videos', block, re.I)
            if rm:
                remarks = rm.group(1) + "部"
            elif m.lastindex and m.lastindex >= 4 and m.group(4):
                remarks = m.group(4) + "部"
            videos.append({
                "vod_id": "model:" + slug,
                "vod_name": title[:80],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": remarks,
                "vod_tag": "folder",
                "land": 1,
            })
            if len(videos) >= 48:
                break
        return videos

    def _detail_model(self, raw):
        """演员详情：作品作为选集（可播放）"""
        slug = raw
        if raw.startswith("model:"):
            slug = raw[6:].strip()
        elif "/jav-models/" in raw:
            m = re.search(r"/jav-models/([a-z0-9-]+)/?", raw)
            slug = m.group(1) if m else raw
        name = slug.replace("-", " ").title()
        pic = ""
        episodes = []
        # 抓取最多 3 页作品
        for page in range(1, 4):
            if page == 1:
                url = self.host + "/jav-models/%s/" % slug
            else:
                url = self.host + "/jav-models/%s/%d/?videos_per_page=30&sort_by=custom1" % (slug, page)
            html = self.fetch(url)
            if not html:
                break
            if page == 1:
                # 演员名与头像
                nm = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
                if nm:
                    name = html_lib.unescape(nm.group(1)).strip()
                pm = re.search(r'property="og:image" content="([^"]+)"', html)
                if pm:
                    pic = pm.group(1)
                if not pic:
                    pm = re.search(r'data-original="(https://[^"]+models[^"]+)"', html)
                    if pm:
                        pic = pm.group(1)
            items = self._parse_list(html)
            if not items:
                break
            for it in items:
                episodes.append("%s$%s" % (it["vod_name"], it["vod_id"]))
            if len(items) < 20:
                break
        if not episodes:
            episodes = ["暂无作品$%s" % (self.host + "/jav-models/%s/" % slug)]
        return {
            "list": [{
                "vod_id": "model:" + slug,
                "vod_name": name,
                "vod_pic": self._proxy_pic(pic),
                "vod_content": "演员：" + name,
                "vod_remarks": "%d部作品" % len(episodes),
                "vod_year": "",
                "vod_area": "日本",
                "vod_actor": name,
                "vod_director": "",
                "type_name": "演员",
                "vod_play_from": "作品列表",
                "vod_play_url": "#".join(episodes),
            }]
        }

    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()
        # strip huge base64 to speed regex
        html = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]{100,}", "BASE64", html)
        for m in re.finditer(
            r'is-item-link-video" href="(https://ikisoda\.com/videos/([a-z0-9-]+)/)"([\s\S]{0,2500}?)</a>',
            html,
        ):
            url, slug, block = m.group(1), m.group(2), m.group(3)
            if slug in seen or slug.isdigit() or len(slug) < 5:
                continue
            seen.add(slug)
            title = ""
            tm = re.search(r'alt="([^"]+)"', block)
            if tm:
                title = html_lib.unescape(tm.group(1)).strip()
            if not title:
                tm = re.search(r'is-item-title[^>]*>([^<]+)', block)
                if tm:
                    title = html_lib.unescape(tm.group(1)).strip()
            if not title:
                title = slug.replace("-", " ")
            pic = ""
            pm = re.search(r'data-original="(https://[^"]+)"', block)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'data-webp="(https://[^"]+)"', block)
                if pm:
                    pic = pm.group(1)
            remarks = ""
            dm = re.search(r'is-item-duration[^>]*>([^<]+)', block)
            if dm:
                remarks = dm.group(1).strip()
            videos.append({
                "vod_id": url,
                "vod_name": title[:100],
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": remarks,
            })
            if len(videos) >= 48:
                break
        return videos
