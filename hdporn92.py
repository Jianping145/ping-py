#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《遮天·轮海彼岸境·八转》—— hdporn92.com TVBox源
境界：轮海秘境·彼岸境（大圆满·Doodstream+Filemoon双解析版）
特征：Filemoon m3u8提取 + Doodstream pass_md5解析 + 86个制片商分类
"""

import sys
import re
import json
import base64
import urllib.request
import urllib.parse

sys.path.append("..")
from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        self.siteUrl = "https://hdporn92.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://hdporn92.com/",
        }
        self.filemoon_domains = (
            "filemoon.sx", "filemoon.to", "filemoon.top",
            "filemoon.in", "filemoon.nl", "filemoon.wf",
        )
        self.dood_domains = (
            "dood.re", "dood.to", "dood.watch", "doodstream.com",
            "dood.ws", "dood.sh", "dood.yt", "dood.la", "dood.wf",
            "doodstream.co", "dood.cx", "dood.pm", "dood.so",
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

    def log(self, msg):
        print("[遮天·彼岸境] " + str(msg))

    def fetch(self, url, headers=None):
        h = dict(self.headers)
        if headers:
            h.update(headers)
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                for enc in ("utf-8", "gbk", "latin-1"):
                    try:
                        return data.decode(enc)
                    except:
                        pass
                return data.decode("utf-8", errors="ignore")
        except Exception as e:
            self.log("fetch error: " + str(e))
            return ""

    def homeContent(self, filter):
        return {"class": self.categories}

    def categoryContent(self, tid, pg, filter, extend):
        if tid == "":
            if pg == "1":
                url = self.siteUrl + "/"
            else:
                url = self.siteUrl + "/page/" + str(pg) + "/?0"
        else:
            if pg == "1":
                url = self.siteUrl + "/category/" + tid + "/"
            else:
                url = self.siteUrl + "/category/" + tid + "/page/" + str(pg) + "/"

        self.log("category: " + url)
        html = self.fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

        videos = self._parse_list(html)
        pagecount = self._extract_pagecount(html, pg)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount,
            "limit": 24,
            "total": int(pagecount) * 24,
        }

    def _parse_list(self, html):
        videos = []
        patternA = re.compile(
            r'<article[^>]*class="[^"]*post[^"*"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]*(?:src|data-src|data-original)="([^"]+)"[^>]*>.*?(?:<span[^>]*class="[^"]*duration[^"]*"[^>]*>([^<]*)</span>)?.*?</article>',
            re.DOTALL | re.IGNORECASE,
        )
        matches = patternA.findall(html)
        if matches:
            self.log("patternA hit: " + str(len(matches)))
            for m in matches:
                videos.append(self._build_video(m[0], m[1], m[2], m[3] if len(m) > 3 else ""))

        if not videos:
            patternB = re.compile(
                r'<div[^>]*class="[^"]*(?:video-item|thumb|post-item)[^"]*"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>.*?<img[^>]*(?:src|data-src)="([^"]+)"[^>]*(?:title|alt)="([^"]*)"[^>]*>.*?(?:<span[^>]*>([^<]*(?:min|sec)[^<]*)</span>)?.*?</div>',
                re.DOTALL | re.IGNORECASE,
            )
            matches = patternB.findall(html)
            if matches:
                self.log("patternB hit: " + str(len(matches)))
                for m in matches:
                    videos.append(self._build_video(m[0], m[2], m[1], m[3] if len(m) > 3 else ""))

        if not videos:
            patternC = re.compile(
                r'<a[^>]*href="([^"]+)"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*>',
                re.DOTALL | re.IGNORECASE,
            )
            matches = patternC.findall(html)
            if matches:
                self.log("patternC hit: " + str(len(matches)))
                for m in matches:
                    videos.append(self._build_video(m[0], m[1], m[2], ""))

        seen = set()
        unique = []
        for v in videos:
            vid = v.get("vod_id", "")
            if vid and vid not in seen:
                seen.add(vid)
                unique.append(v)
        self.log("parsed videos: " + str(len(unique)))
        return unique

    def _decode_html_entities(self, text):
        if not text:
            return text
        entities = {
            "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
            "&apos;": "'", "&#8211;": "–", "&#8212;": "—", "&#8216;": "'",
            "&#8217;": "'", "&#8220;": '"', "&#8221;": '"', "&#8230;": "…",
            "&#038;": "&", "&#39;": "'", "&nbsp;": " ", "&#160;": " ",
            "&#x27;": "'", "&#x2F;": "/", "&#x3C;": "<", "&#x3E;": ">",
        }
        for ent, char in entities.items():
            text = text.replace(ent, char)
        text = re.sub(r"&#([0-9]+);", lambda m: chr(int(m.group(1))), text)
        text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)
        return text.strip()

    def _clean_title(self, title):
        if not title:
            return "未命名"
        title = re.sub(r"<[^>]+>", "", title)
        title = self._decode_html_entities(title)
        title = re.sub(r"[ \t]+", " ", title).strip()
        return title if title else "未命名"

    def _build_video(self, href, title, pic, remark):
        if href:
            if not href.startswith("http"):
                href = urllib.parse.urljoin(self.siteUrl, href)
            if not href.endswith("/"):
                href += "/"
        if pic and not pic.startswith("http"):
            pic = urllib.parse.urljoin(self.siteUrl, pic)
        return {
            "vod_id": href,
            "vod_name": self._clean_title(title),
            "vod_pic": pic,
            "vod_remarks": self._decode_html_entities(remark.strip()) if remark else "HD",
        }

    def _extract_pagecount(self, html, current_pg):
        try:
            max_page = int(current_pg)
            for m in re.finditer(r'page/([0-9]+)/', html):
                p = int(m.group(1))
                if p > max_page:
                    max_page = p
            if ">Next" in html or "next page" in html.lower() or 'class="next"' in html:
                max_page = max(max_page, int(current_pg) + 1)
            return max_page
        except:
            return 999

    def _is_filemoon(self, url):
        if not url:
            return False
        domain = urllib.parse.urlparse(url).netloc.lower()
        return any(d in domain for d in self.filemoon_domains)

    def _parse_filemoon(self, url):
        self.log("Filemoon parsing: " + url)
        html = self.fetch(url)
        if not html:
            return ""

        m = re.search(r'sources[ \t]*:[ \t]*\[[^\]]*\{[^}]*file[ \t]*:[ \t]*"([^"]+)"', html, re.IGNORECASE)
        if m:
            self.log("Filemoon sources = " + m.group(1))
            return m.group(1)

        m = re.search(r'jwplayer[^(]*\([^)]+\)[ \t]*\.[ \t]*setup[ \t]*\([^\)]*sources[ \t]*:[ \t]*\[[^\]]*\{[^}]*file[ \t]*:[ \t]*"([^"]+)"', html, re.DOTALL | re.IGNORECASE)
        if m:
            self.log("Filemoon jwplayer = " + m.group(1))
            return m.group(1)

        m = re.search(r'<video[^>]+src="([^"]+)"', html, re.IGNORECASE)
        if m:
            self.log("Filemoon video = " + m.group(1))
            return m.group(1)

        m = re.search(r'<source[^>]+src="([^"]+)"[^>]+type="application/x-mpegURL"', html, re.IGNORECASE)
        if m:
            self.log("Filemoon source = " + m.group(1))
            return m.group(1)

        m = re.search(r'["\']([^"\']+[.]m3u8[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            self.log("Filemoon m3u8 = " + m.group(1))
            return m.group(1)

        if re.search(r'eval\(function\(p,a,c,k,e,d\)', html):
            m = re.search(r'eval\(function\(p,a,c,k,e,d\)[^\)]+\)\)[ \t]*;?\s*var\s+\w+\s*=\s*\{[^\}]*file\s*:\s*"([^"]+)"', html, re.DOTALL | re.IGNORECASE)
            if m:
                self.log("Filemoon eval = " + m.group(1))
                return m.group(1)

        # Filemoon /download/ 路径可能是直接下载链接
        if "/download/" in url:
            self.log("Filemoon download link = " + url)
            return url

        if "/d/" in url:
            # 尝试 /download/ 变体
            vid = ""
            m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
            if m:
                vid = m.group(1)
                parsed = urllib.parse.urlparse(url)
                download_url = parsed.scheme + "://" + parsed.netloc + "/download/" + vid
                self.log("Filemoon try download = " + download_url)
                # 测试下载链接是否可用
                dl_html = self.fetch(download_url)
                if dl_html and ("video" in dl_html.lower() or "mp4" in dl_html.lower() or "m3u8" in dl_html.lower()):
                    self.log("Filemoon download valid")
                    return download_url

            embed = url.replace("/d/", "/e/", 1)
            self.log("Filemoon fallback embed = " + embed)
            return embed

        self.log("Filemoon parse failed")
        return ""

    def _is_doodstream(self, url):
        if not url:
            return False
        domain = urllib.parse.urlparse(url).netloc.lower()
        return any(d in domain for d in self.dood_domains)

    def _parse_doodstream(self, url):
        self.log("Doodstream parsing: " + url)
        html = self.fetch(url)
        if not html:
            self.log("Doodstream fetch empty")
            return ""

        m = re.search(r'<video[^>]+src="([^"]+)"', html, re.IGNORECASE)
        if m:
            self.log("Doodstream video = " + m.group(1))
            return m.group(1)

        m = re.search(r'<source[^>]+src="([^"]+)"', html, re.IGNORECASE)
        if m:
            self.log("Doodstream source = " + m.group(1))
            return m.group(1)

        pass_md5 = ""
        m = re.search(r"pass_md5/([a-zA-Z0-9_-]+)", html)
        if m:
            pass_md5 = m.group(1)
            self.log("Doodstream pass_md5 id = " + pass_md5)

        if pass_md5:
            parsed = urllib.parse.urlparse(url)
            base = parsed.scheme + "://" + parsed.netloc
            token_url = base + "/pass_md5/" + pass_md5
            self.log("Doodstream token url = " + token_url)

            token_html = self.fetch(token_url, headers={"Referer": url})
            if token_html and token_html.strip():
                self.log("Doodstream token raw = " + token_html[:200])

                if token_html.startswith("http"):
                    self.log("Doodstream token full url = " + token_html.strip())
                    return token_html.strip()

                video_id = ""
                m2 = re.search(r"/[ed]/([a-zA-Z0-9_-]+)", url)
                if m2:
                    video_id = m2.group(1)

                if video_id:
                    direct = base + "/d/" + video_id + "?token=" + token_html.strip()
                    self.log("Doodstream direct = " + direct)
                    return direct

        m = re.search(r'["\']([^"\']+[.]m3u8[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            self.log("Doodstream m3u8 = " + m.group(1))
            return m.group(1)

        m = re.search(r'["\']([^"\']+[.]mp4[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            self.log("Doodstream mp4 = " + m.group(1))
            return m.group(1)

        self.log("Doodstream parse failed, fallback")
        return url

    def _is_third_party_host(self, url):
        if not url:
            return False
        domain = urllib.parse.urlparse(url).netloc.lower()
        third_parties = (
            "filemoon", "streamtape", "dood", "vidcloud", "vidoza",
            "voe", "mixdrop", "streamsb", "sbembed", "bravoplayer",
            "playernow", "streamwish", "filelions", "embedrise",
            "vanfem", "streamhide", "luluvdo", "vidmoly", "upstream",
            "doodstream",
        )
        return any(tp in domain for tp in third_parties)

    def detailContent(self, ids):
        url = ids[0]
        if not url.startswith("http"):
            url = urllib.parse.urljoin(self.siteUrl, url)
        if not url.endswith("/"):
            url += "/"

        self.log("detail: " + url)
        html = self.fetch(url)
        if not html:
            self.log("detail fetch empty")
            return {"list": []}

        title = self._extract_title(html)
        pic = self._extract_detail_pic(html)
        self.log("detail title: " + title)

        play_url = self._extract_video_url(html, url)

        if not play_url:
            play_url = url
            self.log("fallback to detail page")

        if play_url and not play_url.startswith("http") and not play_url.startswith("eval://"):
            play_url = urllib.parse.urljoin(self.siteUrl, play_url)
        if play_url.startswith("//"):
            play_url = "https:" + play_url

        self.log("final play_url: " + play_url)

        return {
            "list": [{
                "vod_id": ids[0],
                "vod_name": title,
                "vod_pic": pic,
                "vod_play_from": "HDPlayer",
                "vod_play_url": "第1集$" + play_url,
                "vod_content": "source: " + url,
            }]
        }

    def _extract_video_url(self, html, referer_url):
        play_url = ""

        m = re.search(r'<video[^>]+src="([^"]+)"', html, re.IGNORECASE)
        if m:
            play_url = m.group(1)
            self.log("L1: video src = " + play_url)
            return play_url

        m = re.search(r'<source[^>]+src="([^"]+)"[^>]+type="video/', html, re.IGNORECASE)
        if m:
            play_url = m.group(1)
            self.log("L2: source = " + play_url)
            return play_url

        iframe_src = ""
        m = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.IGNORECASE)
        if m:
            iframe_src = m.group(1)
            self.log("L3: iframe raw = " + iframe_src)

        if iframe_src:
            if iframe_src.startswith("//"):
                iframe_src = "https:" + iframe_src
            elif iframe_src.startswith("/"):
                iframe_src = urllib.parse.urljoin(self.siteUrl, iframe_src)
            elif not iframe_src.startswith("http"):
                iframe_src = urllib.parse.urljoin(self.siteUrl, iframe_src)

            self.log("L3: iframe normalized = " + iframe_src)

            if self._is_filemoon(iframe_src):
                self.log("L3: filemoon detected")
                fm = self._parse_filemoon(iframe_src)
                if fm:
                    return fm
                if "/d/" in iframe_src:
                    return iframe_src.replace("/d/", "/e/", 1)
                return iframe_src

            if self._is_doodstream(iframe_src):
                self.log("L3: doodstream detected")
                ds = self._parse_doodstream(iframe_src)
                if ds:
                    return ds
                return iframe_src

            if self._is_third_party_host(iframe_src):
                self.log("L3: third-party iframe = " + iframe_src)
                return iframe_src

            iframe_html = self.fetch(iframe_src)
            if iframe_html:
                for pat in (
                    r'<video[^>]+src="([^"]+)"',
                    r'<source[^>]+src="([^"]+)"',
                    r'["\']([^"\']+[.]m3u8[^"\']*)["\']',
                    r'["\']([^"\']+[.]mp4[^"\']*)["\']',
                ):
                    m2 = re.search(pat, iframe_html, re.IGNORECASE)
                    if m2:
                        inner = m2.group(1)
                        if not self._is_third_party_host(inner):
                            play_url = inner
                            self.log("L3: iframe inner = " + play_url)
                            break

            if not play_url:
                play_url = iframe_src
                self.log("L3: iframe direct = " + play_url)
            return play_url

        m = re.search(r'["\']([^"\']+[.]m3u8[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            c = m.group(1)
            if not self._is_third_party_host(c):
                play_url = c
                self.log("L4: m3u8 = " + play_url)
                return play_url
            self.log("L4: skip third-party m3u8")

        m = re.search(r'["\']([^"\']+[.]mp4[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            c = m.group(1)
            if not self._is_third_party_host(c):
                play_url = c
                self.log("L5: mp4 = " + play_url)
                return play_url
            self.log("L5: skip third-party mp4")

        m = re.search(r'data-video="([^"]+)"', html, re.IGNORECASE)
        if m:
            play_url = m.group(1)
            self.log("L6: data-video = " + play_url)
            return play_url

        m = re.search(r'data-src="([^"]+)"', html, re.IGNORECASE)
        if m:
            v = m.group(1)
            if ".m3u8" in v or ".mp4" in v or "player" in v:
                play_url = v
                self.log("L7: data-src = " + play_url)
                return play_url

        m = re.search(r'meta[ \t]+property="og:video"[ \t]+content="([^"]+)"', html, re.IGNORECASE)
        if m:
            play_url = m.group(1)
            self.log("L8: og:video = " + play_url)
            return play_url

        m = re.search(r'"contentUrl"[ \t]*:[ \t]*"([^"]+)"', html)
        if m:
            play_url = m.group(1)
            self.log("L9: JSON-LD = " + play_url)
            return play_url

        for var_name in ("video_url", "videoUrl", "source", "file", "url"):
            pat = r'var[ \t]+' + var_name + r'[ \t]*=[ \t]*"([^"]+)"'
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                v = m.group(1)
                if v.startswith("http") or ".m3u8" in v or ".mp4" in v:
                    play_url = v
                    self.log("L10: var " + var_name + " = " + play_url)
                    return play_url

        for m in re.finditer(r'["\']([A-Za-z0-9+/=]{50,})["\']', html):
            try:
                decoded = base64.b64decode(m.group(1)).decode("utf-8")
                if decoded.startswith("http") and (".m3u8" in decoded or ".mp4" in decoded or "player" in decoded):
                    play_url = decoded
                    self.log("L11: base64 = " + play_url)
                    return play_url
            except:
                pass

        if re.search(r'eval\(function\(p,a,c,k,e,d\)', html):
            return "eval://" + referer_url

        m = re.search(r'<a[^>]+href="([^"]+\.(?:m3u8|mp4)[^"]*)"', html, re.IGNORECASE)
        if m:
            play_url = m.group(1)
            self.log("L12: a link = " + play_url)
            return play_url

        return ""

    def _extract_title(self, html):
        for pat in (
            r'<h1[^>]*>(.*?)</h1>',
            r'<title>(.*?)</title>',
            r'"name"[ \t]*:[ \t]*"([^"]+)"',
            r'meta[ \t]+property="og:title"[ \t]+content="([^"]+)"',
        ):
            m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
            if m:
                t = self._clean_title(m.group(1))
                if t and t != "未命名":
                    return t
        return "未知标题"

    def _extract_detail_pic(self, html):
        m = re.search(r'meta[ \t]+property="og:image"[ \t]+content="([^"]+)"', html, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'<video[^>]+poster="([^"]+)"', html, re.IGNORECASE)
        if m:
            return m.group(1)
        return ""

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "url": "", "header": ""}

        if id.startswith("eval://"):
            return {"parse": 1, "url": id.replace("eval://", ""), "header": ""}

        if self._is_filemoon(id) and ".m3u8" in id:
            self.log("player: filemoon m3u8 direct")
            return {"parse": 0, "url": id, "header": ""}

        if self._is_filemoon(id):
            self.log("player: filemoon parse=1")
            return {"parse": 1, "url": id, "header": ""}

        if self._is_doodstream(id) and ("token=" in id or ".m3u8" in id or ".mp4" in id):
            self.log("player: doodstream direct")
            return {"parse": 0, "url": id, "header": ""}

        if self._is_doodstream(id):
            self.log("player: doodstream parse=1")
            return {"parse": 1, "url": id, "header": ""}

        if self._is_third_party_host(id):
            self.log("player: third-party parse=1")
            return {"parse": 1, "url": id, "header": ""}

        if id.startswith("http") and ("player" in id or "embed" in id or "iframe" in id):
            return {"parse": 1, "url": id, "header": ""}

        if id.startswith("http") and (".m3u8" in id or ".mp4" in id):
            return {"parse": 0, "url": id, "header": ""}

        return {"parse": 1, "url": id, "header": ""}

    def searchContent(self, key, quick, pg="1"):
        url = self.siteUrl + "/?s=" + urllib.parse.quote(key)
        if pg != "1":
            url = self.siteUrl + "/page/" + str(pg) + "/?s=" + urllib.parse.quote(key)
        self.log("search: " + url)
        html = self.fetch(url)
        if not html:
            return {"list": []}
        videos = self._parse_list(html)
        return {"list": videos, "page": pg}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def localProxy(self, param):
        return [404, "text/plain", "Not Implemented"]

    def isVideoFormat(self, url):
        return any(fmt in url.lower() for fmt in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def init(self, extend=""):
        self.log("init ok")
        return True


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print(json.dumps(sp.homeContent(None), ensure_ascii=False, indent=2))
