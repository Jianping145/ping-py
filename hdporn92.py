# -*- coding: utf-8 -*-
# hdporn92.com - 蜂蜜影视爬虫
# 播放源：morencius/vidhide packer 解出 m3u8；兼容 filemoon / doodstream
import re
import json
import base64
import requests
import urllib3
from urllib.parse import urljoin, urlparse, quote, unquote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Spider(BaseSpider):
    def init(self, extend=""):
        self.siteUrl = "https://hdporn92.com"
        self.ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.siteUrl + "/",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        ad = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16)
        self.session.mount("http://", ad)
        self.session.mount("https://", ad)
        self.proxy = None
        self._apply_extend(extend)

        self.filemoon_domains = (
            "filemoon.sx", "filemoon.to", "filemoon.top",
            "filemoon.in", "filemoon.nl", "filemoon.wf",
        )
        self.dood_domains = (
            "dood.re", "dood.to", "dood.watch", "doodstream.com",
            "dood.ws", "dood.sh", "dood.yt", "dood.la", "dood.wf",
            "doodstream.co", "dood.cx", "dood.pm", "dood.so",
        )
        # vidhide 系嵌入域
        self.vidhide_domains = (
            "morencius.com", "vidhide.com", "vidhidepro.com", "vidhidepre.com",
            "earnvids.com", "smoothpre.com", "filemoon.nl",
        )

        self.categories = [
            {"type_id": "", "type_name": "首页"},
            {"type_id": "fillupmymom", "type_name": "Fillup My Mom"},
            {"type_id": "my-pervy-family", "type_name": "My Pervy Family"},
            {"type_id": "brazzers-porn-videos", "type_name": "Brazzers"},
            {"type_id": "bangbros", "type_name": "BangBros"},
            {"type_id": "mom-swap", "type_name": "Mom Swap"},
            {"type_id": "daughterswap", "type_name": "DaughterSwap"},
            {"type_id": "mom-swapped", "type_name": "Mom Swapped"},
            {"type_id": "naughty-america", "type_name": "Naughty America"},
            {"type_id": "sex-mex", "type_name": "Sex Mex"},
            {"type_id": "momishorny", "type_name": "Mom Is Horny"},
            {"type_id": "sis-swap", "type_name": "Sis Swap"},
            {"type_id": "touch-my-wife", "type_name": "Touch My Wife"},
            {"type_id": "fake-hub", "type_name": "Fake Hub"},
            {"type_id": "perv-mom", "type_name": "Perv Mom"},
            {"type_id": "dadsloveporn", "type_name": "Dads Love Porn"},
            {"type_id": "familystrokes", "type_name": "Family Strokes"},
            {"type_id": "anal-mom", "type_name": "Anal Mom"},
            {"type_id": "sis-loves-me", "type_name": "Sis Loves Me"},
            {"type_id": "tigermoms", "type_name": "Tiger Moms"},
            {"type_id": "mylf", "type_name": "MYLF"},
            {"type_id": "milfty", "type_name": "Milfty"},
            {"type_id": "momcomesfirst", "type_name": "Mom Comes First"},
            {"type_id": "reality-kings", "type_name": "Reality Kings"},
            {"type_id": "perfect-girlfriend", "type_name": "Perfect Girlfriend"},
            {"type_id": "horny-hostel", "type_name": "Horny Hostel"},
            {"type_id": "askyourmother", "type_name": "Ask Your Mother"},
            {"type_id": "freeuse-milf", "type_name": "Freeuse Milf"},
            {"type_id": "freeusefantasy", "type_name": "Freeuse Fantasy"},
            {"type_id": "mommys-boy", "type_name": "Mommy's Boy"},
            {"type_id": "family-swap", "type_name": "Family Swap"},
            {"type_id": "milfcoach", "type_name": "Milf Coach"},
            {"type_id": "mom-drips", "type_name": "Mom Drips"},
            {"type_id": "got-mylf", "type_name": "Got MYLF"},
            {"type_id": "brattysis", "type_name": "Bratty Sis"},
            {"type_id": "bratty-milf", "type_name": "Bratty Milf"},
            {"type_id": "brattamer", "type_name": "Brat Tamer"},
            {"type_id": "breedingmaterial", "type_name": "Breeding Material"},
            {"type_id": "moms-teach-sex", "type_name": "Moms Teach Sex"},
            {"type_id": "reptylelabs", "type_name": "Reptyle Labs"},
            {"type_id": "hot-milfs-fuck", "type_name": "Hot Milfs Fuck"},
            {"type_id": "latinamylf", "type_name": "Latina MYLF"},
            {"type_id": "exxxtra-small", "type_name": "Exxxtra Small"},
            {"type_id": "momwantscreampie", "type_name": "Mom Wants Creampie"},
            {"type_id": "myfamilypies", "type_name": "My Family Pies"},
            {"type_id": "pervprincipal", "type_name": "Perv Principal"},
            {"type_id": "shop-lyfter", "type_name": "Shop Lyfter"},
            {"type_id": "shoplyftermylf", "type_name": "Shoplyfter MYLF"},
            {"type_id": "nfbusty", "type_name": "NF Busty"},
            {"type_id": "exploited-college-girls", "type_name": "Exploited College Girls"},
            {"type_id": "cheatingmommy", "type_name": "Cheating Mommy"},
            {"type_id": "cheatingsis", "type_name": "Cheating Sis"},
            {"type_id": "my-babysitters-club", "type_name": "My Babysitters Club"},
            {"type_id": "cumswappingsis", "type_name": "Cum Swapping Sis"},
            {"type_id": "stepsiblingscaught", "type_name": "Step Siblings Caught"},
            {"type_id": "datingmystepson", "type_name": "Dating My Stepson"},
            {"type_id": "freaky-fembots", "type_name": "Freaky Fembots"},
            {"type_id": "shesbreedingmaterial", "type_name": "Shes Breeding Material"},
            {"type_id": "imadeporn", "type_name": "I Made Porn"},
            {"type_id": "filthyfamily", "type_name": "Filthy Family"},
            {"type_id": "milfy", "type_name": "Milfy"},
            {"type_id": "pure-taboo", "type_name": "Pure Taboo"},
            {"type_id": "filthy-taboo", "type_name": "Filthy Taboo"},
            {"type_id": "perv-nana", "type_name": "Perv Nana"},
            {"type_id": "blacked", "type_name": "Blacked"},
            {"type_id": "blacked-raw", "type_name": "Blacked Raw"},
            {"type_id": "mom-shoot", "type_name": "Mom Shoot"},
            {"type_id": "princess-cum", "type_name": "Princess Cum"},
            {"type_id": "usepov", "type_name": "Use POV"},
            {"type_id": "milf-body", "type_name": "Milf Body"},
            {"type_id": "tushy", "type_name": "Tushy"},
            {"type_id": "tushy-raw", "type_name": "Tushy Raw"},
            {"type_id": "mature-nl", "type_name": "Mature NL"},
            {"type_id": "nubiles-porn", "type_name": "Nubiles Porn"},
            {"type_id": "oyemami", "type_name": "Oye Mami"},
            {"type_id": "oye-loca", "type_name": "Oye Loca"},
            {"type_id": "bad-milfs", "type_name": "Bad Milfs"},
            {"type_id": "bffs", "type_name": "BFFs"},
            {"type_id": "milflicious", "type_name": "Milflicious"},
            {"type_id": "net-girl", "type_name": "Net Girl"},
            {"type_id": "net-video-girls", "type_name": "Net Video Girls"},
            {"type_id": "imnotyourmommy", "type_name": "I'm Not Your Mommy"},
            {"type_id": "innocent-high", "type_name": "Innocent High"},
            {"type_id": "perv-therapy", "type_name": "Perv Therapy"},
            {"type_id": "devilsfilm", "type_name": "Devils Film"},
            {"type_id": "jules-jordan", "type_name": "Jules Jordan"},
            {"type_id": "backroomcastingcouch", "type_name": "Backroom Casting Couch"},
        ]

    def _apply_extend(self, extend):
        if not extend:
            return
        obj = extend
        if isinstance(extend, str):
            extend = extend.strip()
            if not extend:
                return
            try:
                obj = json.loads(extend)
            except Exception:
                if extend.startswith("http") or extend.startswith("socks"):
                    obj = {"proxy": extend}
                else:
                    return
        if isinstance(obj, dict):
            proxy = obj.get("proxy") or obj.get("proxies")
            if proxy:
                if isinstance(proxy, dict):
                    self.proxy = proxy
                else:
                    self.proxy = {"http": proxy, "https": proxy}

    def getName(self):
        return "HDPorn92"

    def log(self, msg):
        try:
            print("[hdporn92] %s" % msg)
        except Exception:
            pass

    def fetch(self, url, headers=None):
        h = dict(self.headers)
        if headers:
            h.update(headers)
        try:
            r = self.session.get(
                url, headers=h, timeout=20, verify=False,
                proxies=self.proxy, allow_redirects=True,
            )
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception as e:
            self.log("fetch %s" % e)
            return ""

    def homeContent(self, filter):
        return {"class": self.categories, "filters": {}}

    def homeVideoContent(self):
        html = self.fetch(self.siteUrl + "/")
        return {"list": self._parse_list(html)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        if not tid:
            url = self.siteUrl + "/" if pg == "1" else self.siteUrl + "/page/%s/" % pg
        else:
            url = (
                self.siteUrl + "/category/%s/" % tid
                if pg == "1"
                else self.siteUrl + "/category/%s/page/%s/" % (tid, pg)
            )
        html = self.fetch(url)
        videos = self._parse_list(html)
        pagecount = self._extract_pagecount(html, pg)
        return {
            "list": videos,
            "page": int(pg),
            "pagecount": pagecount,
            "limit": 24,
            "total": int(pagecount) * 24,
        }

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        q = quote(key)
        if pg == "1":
            url = self.siteUrl + "/?s=" + q
        else:
            url = self.siteUrl + "/page/%s/?s=%s" % (pg, q)
        html = self.fetch(url)
        return {"list": self._parse_list(html)}

    def _decode_html_entities(self, text):
        if not text:
            return text
        entities = {
            "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
            "&apos;": "'", "&#8211;": "–", "&#8212;": "—",
            "&#8216;": "'", "&#8217;": "'", "&#8220;": '"', "&#8221;": '"',
            "&#8230;": "…", "&#038;": "&", "&#39;": "'", "&nbsp;": " ",
        }
        for ent, char in entities.items():
            text = text.replace(ent, char)
        text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
        text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)
        return text.strip()

    def _clean_title(self, title):
        if not title:
            return "未命名"
        title = re.sub(r"<[^>]+>", "", title)
        title = self._decode_html_entities(title)
        title = re.sub(r"[ \t]+", " ", title).strip()
        return title or "未命名"

    def _parse_list(self, html):
        if not html:
            return []
        videos, seen = [], set()
        # article.post 结构
        for m in re.finditer(
            r'<article[^>]*>[\s\S]*?<a[^>]+href="([^"]+)"[^>]*title="([^"]*)"[^>]*>[\s\S]*?<img[^>]+(?:src|data-src|data-original)="([^"]+)"',
            html,
            re.I,
        ):
            href, title, pic = m.group(1), m.group(2), m.group(3)
            if href in seen:
                continue
            if "/category/" in href or "/tag/" in href or "/page/" in href:
                continue
            seen.add(href)
            remark = ""
            dm = re.search(
                r'duration[^>]*>([^<]+)',
                html[m.start() : m.start() + 800],
                re.I,
            )
            if dm:
                remark = dm.group(1).strip()
            videos.append(self._build_video(href, title, pic, remark))

        if not videos:
            for m in re.finditer(
                r'<a[^>]+href="(https?://hdporn92\.com/[^"]+/)"[^>]*title="([^"]+)"[^>]*>[\s\S]{0,400}?<img[^>]+src="([^"]+)"',
                html,
                re.I,
            ):
                href = m.group(1)
                if href in seen or "/category/" in href:
                    continue
                seen.add(href)
                videos.append(self._build_video(href, m.group(2), m.group(3), ""))
        self.log("list %d" % len(videos))
        return videos

    def _build_video(self, href, title, pic, remark):
        if href and not href.startswith("http"):
            href = urljoin(self.siteUrl, href)
        if href and not href.endswith("/"):
            href += "/"
        if pic and not pic.startswith("http"):
            pic = urljoin(self.siteUrl, pic)
        return {
            "vod_id": href,
            "vod_name": self._clean_title(title),
            "vod_pic": pic,
            "vod_remarks": self._decode_html_entities(remark) if remark else "HD",
        }

    def _extract_pagecount(self, html, current_pg):
        try:
            max_page = int(current_pg)
            for m in re.finditer(r"/page/(\d+)/", html):
                max_page = max(max_page, int(m.group(1)))
            if re.search(r'class="[^"]*next', html, re.I) or "next page" in html.lower():
                max_page = max(max_page, int(current_pg) + 1)
            return max_page
        except Exception:
            return int(current_pg) + 1

    # ---------- Dean Edwards packer ----------
    def _to_base(self, n, base):
        if n == 0:
            return "0"
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"
        s = ""
        while n:
            s = digits[n % base] + s
            n //= base
        return s

    def _unpack_packer(self, html):
        """解 eval(function(p,a,c,k,e,d){while(c--)...}('...',radix,count,'k|k|...'.split('|'))"""
        # 兼容 RegExp 参数里的嵌套括号
        m = re.search(
            r"eval\(function\(p,a,c,k,e,d\)\{while\(c--\)if\(k\[c\]\)p=p\.replace"
            r"\(new RegExp\(.*?\),k\[c\]\);return p\}"
            r"\('([\s\S]*?)',(\d+),(\d+),'([\s\S]*?)'\.split\('\|'\)\)",
            html,
        )
        if not m:
            # 宽松：直接抓 payload / radix / count / keys
            m = re.search(
                r"return p\}\('([\s\S]*?)',(\d+),(\d+),'([\s\S]*?)'\.split\('\|'\)\)",
                html,
            )
        if not m:
            return ""
        payload, radix, count, keys_s = (
            m.group(1),
            int(m.group(2)),
            int(m.group(3)),
            m.group(4),
        )
        keys = keys_s.split("|")
        p = payload
        c = count
        while c:
            c -= 1
            if c < len(keys) and keys[c]:
                p = re.sub(r"\b" + re.escape(self._to_base(c, radix)) + r"\b", keys[c], p)
        return p

    def _extract_m3u8_from_embed(self, embed_html):
        if not embed_html:
            return ""
        # 先解 packer
        unpacked = self._unpack_packer(embed_html)
        src = unpacked or embed_html
        # hls2 优先（带签名的 m3u8）
        m = re.search(
            r'["\']hls2["\']\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            src,
        )
        if m:
            return m.group(1).replace("\\/", "/")
        m = re.search(r'https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*', src)
        if m:
            return m.group(0).replace("\\/", "/")
        # links 对象
        m = re.search(
            r'links\s*=\s*\{[^}]*hls2["\']?\s*:\s*["\']([^"\']+)["\']',
            src,
        )
        if m:
            return m.group(1).replace("\\/", "/")
        m = re.search(r'file\s*:\s*["\'](https?://[^"\']+)["\']', src)
        if m:
            return m.group(1).replace("\\/", "/")
        return ""

    def _domain_in(self, url, domains):
        if not url:
            return False
        host = urlparse(url).netloc.lower()
        return any(d in host for d in domains)

    def detailContent(self, ids):
        url = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        if not url.startswith("http"):
            url = urljoin(self.siteUrl, url)
        if not url.endswith("/"):
            url += "/"

        html = self.fetch(url)
        if not html:
            return {"list": []}

        title = "未知标题"
        for pat in (
            r"<h1[^>]*>(.*?)</h1>",
            r'property="og:title"\s+content="([^"]+)"',
            r"<title>(.*?)</title>",
        ):
            m = re.search(pat, html, re.I | re.S)
            if m:
                t = self._clean_title(m.group(1))
                if t and t != "未命名":
                    title = t
                    break

        pic = ""
        m = re.search(r'property="og:image"\s+content="([^"]+)"', html, re.I)
        if m:
            pic = m.group(1)

        play_url = self._extract_video_url(html, url)
        if not play_url:
            play_url = url

        return {
            "list": [{
                "vod_id": ids[0] if isinstance(ids, (list, tuple)) else url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_play_from": "HDPlayer",
                "vod_play_url": "正片$%s" % play_url,
                "vod_content": "",
            }]
        }

    def _extract_video_url(self, html, referer_url):
        # 1) 详情页直链
        m = re.search(r'<video[^>]+src="([^"]+)"', html, re.I)
        if m and (".m3u8" in m.group(1) or ".mp4" in m.group(1)):
            return m.group(1)

        # 2) 所有 iframe（跳过广告）
        iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', html, re.I)
        for src in iframes:
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(self.siteUrl, src)
            low = src.lower()
            if any(x in low for x in ("smartflora", "ad", "ads.", "doubleclick", "pop")):
                continue

            # VidHide / morencius
            if self._domain_in(src, self.vidhide_domains) or "/embed/" in low:
                emb = self.fetch(src, headers={"Referer": referer_url})
                m3u8 = self._extract_m3u8_from_embed(emb)
                if m3u8:
                    self.log("vidhide m3u8 ok")
                    return m3u8
                # 嗅探兜底
                if emb and ("jwplayer" in emb or "packer" in emb or "eval(function" in emb):
                    return src

            if self._domain_in(src, self.filemoon_domains):
                fm = self._parse_filemoon(src)
                if fm:
                    return fm
                return src

            if self._domain_in(src, self.dood_domains):
                ds = self._parse_doodstream(src)
                if ds:
                    return ds
                return src

            # 其它第三方：尝试解 packer / 取 m3u8
            emb = self.fetch(src, headers={"Referer": referer_url})
            m3u8 = self._extract_m3u8_from_embed(emb)
            if m3u8:
                return m3u8
            m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', emb or "")
            if m:
                return m.group(0)

        # 3) 页内 m3u8
        m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', html)
        if m:
            return m.group(0)
        return ""

    def _parse_filemoon(self, url):
        html = self.fetch(url)
        if not html:
            return ""
        for pat in (
            r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'sources\s*:\s*\[[^\]]*file\s*:\s*["\']([^"\']+)["\']',
            r'https?://[^"\']+\.m3u8[^"\']*',
        ):
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1) if m.lastindex else m.group(0)
        unpacked = self._unpack_packer(html)
        if unpacked:
            m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', unpacked)
            if m:
                return m.group(0)
        return ""

    def _parse_doodstream(self, url):
        html = self.fetch(url)
        if not html:
            return ""
        m = re.search(r"pass_md5/([a-zA-Z0-9_-]+)", html)
        if m:
            parsed = urlparse(url)
            base = parsed.scheme + "://" + parsed.netloc
            token = self.fetch(
                base + "/pass_md5/" + m.group(1),
                headers={"Referer": url},
            )
            if token and token.strip().startswith("http"):
                return token.strip()
            mid = re.search(r"/[ed]/([a-zA-Z0-9_-]+)", url)
            if token and mid:
                return base + "/d/" + mid.group(1) + "?token=" + token.strip()
        m = re.search(r'https?://[^"\']+\.m3u8[^"\']*', html)
        if m:
            return m.group(0)
        return ""

    def playerContent(self, flag, id, vipFlags):
        url = unquote(str(id or "")).strip()
        if not url:
            return {"parse": 1, "url": "", "header": {}}

        headers = {
            "User-Agent": self.ua,
            "Referer": self.siteUrl + "/",
        }

        # 已是直链
        if any(x in url.lower() for x in (".m3u8", ".mp4", ".mkv")):
            # m3u8 常需带上嵌入域 Referer
            if "dramiyos" in url or "mediastream" in url or "cdn" in url:
                headers["Referer"] = "https://morencius.com/"
                headers["Origin"] = "https://morencius.com"
            return {"parse": 0, "jx": 0, "url": url, "header": headers}

        # 嵌入页：再解一次
        if self._domain_in(url, self.vidhide_domains) or "/embed/" in url:
            emb = self.fetch(url, headers={"Referer": self.siteUrl + "/"})
            m3u8 = self._extract_m3u8_from_embed(emb)
            if m3u8:
                headers["Referer"] = "https://morencius.com/"
                headers["Origin"] = "https://morencius.com"
                return {"parse": 0, "jx": 0, "url": m3u8, "header": headers}
            return {"parse": 1, "jx": 0, "url": url, "header": headers}

        if self._domain_in(url, self.filemoon_domains):
            fm = self._parse_filemoon(url)
            if fm and (".m3u8" in fm or ".mp4" in fm):
                return {"parse": 0, "jx": 0, "url": fm, "header": headers}
            return {"parse": 1, "jx": 0, "url": url, "header": headers}

        if self._domain_in(url, self.dood_domains):
            ds = self._parse_doodstream(url)
            if ds and (".m3u8" in ds or ".mp4" in ds or "token=" in ds):
                return {"parse": 0, "jx": 0, "url": ds, "header": headers}
            return {"parse": 1, "jx": 0, "url": url, "header": headers}

        return {"parse": 1, "jx": 0, "url": url, "header": headers}

    def isVideoFormat(self, url):
        if not url:
            return False
        low = url.lower()
        return any(x in low for x in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return True

    def localProxy(self, param):
        return [404, "text/plain", b"Not Implemented"]

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass
