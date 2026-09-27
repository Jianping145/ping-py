# -*- coding: utf-8 -*-
# 遮天·轮海彼岸境 · XNXX 专用 Spider
# 目标站点: https://www.xnxx.com/
# 精简版：去除内容重复的分类

import re
import json
from datetime import datetime
from urllib import parse
from bs4 import BeautifulSoup
import requests

# 如果在 TVBox 环境中运行，请取消下一行注释并确保 base.spider 路径正确
# from base.spider import Spider


class Spider:
    def __init__(self):
        self.siteUrl = "https://www.xnxx.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.xnxx.com/",
            "Connection": "keep-alive",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 真实路径映射（内容互不重复）
        self.path_map = {
            "hot": "/hits/week",    # 本周最热
            "new": "/hits/month",   # 本月热门
            "hits": "/hits",        # 历史总榜
            "best": "/best",        # 站点当月 Best（动态）
        }

    def fetch(self, url, timeout=15):
        try:
            resp = self.session.get(url, timeout=timeout, allow_redirects=True)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[XNXX] fetch error: {e}")
            return ""

    def homeContent(self, filter):
        """首页分类 —— 去重，只保留内容不同的"""
        classes = [
            # 官方榜单（内容各不相同）
            {"type_id": "hot", "type_name": "Hot"},
            {"type_id": "new", "type_name": "New Videos"},
            {"type_id": "hits", "type_name": "Hits"},
            {"type_id": "best", "type_name": "Best Videos"},

            # 地区 / 风格
            {"type_id": "search/chica", "type_name": "Chica"},
            {"type_id": "search/japan-porn", "type_name": "Japan Porn"},
            {"type_id": "search/japanese-porn", "type_name": "Japanese Porn"},
            {"type_id": "search/jav-uncensored", "type_name": "JAV Uncensored"},
            {"type_id": "search/uncensored-japanese-porn", "type_name": "Uncensored Japanese"},
            {"type_id": "search/latina", "type_name": "Latina"},
            {"type_id": "search/indian-sex", "type_name": "Indian Sex"},
            {"type_id": "search/%E7%B4%A0%E4%BA%BA", "type_name": "素人"},

            # Teen / Young
            {"type_id": "search/teen-blowjob", "type_name": "Teen Blowjob"},
            {"type_id": "search/teen-fuck", "type_name": "Teen Fuck"},
            {"type_id": "search/teen-porn", "type_name": "Teen Porn"},
            {"type_id": "search/teen-sex", "type_name": "Teen Sex"},
            {"type_id": "search/18-year-old", "type_name": "18 Year Old"},
            {"type_id": "search/amateur-teen", "type_name": "Amateur Teen"},
            {"type_id": "search/young-woman", "type_name": "Young Woman"},

            # Amateur / Couple
            {"type_id": "search/amateur-sex-video", "type_name": "Amateur Sex"},
            {"type_id": "search/amateur-porn-video", "type_name": "Amateur Porn"},
            {"type_id": "search/amateur-pussy", "type_name": "Amateur Pussy"},
            {"type_id": "search/couple-porn", "type_name": "Couple Porn"},
            {"type_id": "search/hot-couple-sex", "type_name": "Hot Couple"},
            {"type_id": "search/college-party", "type_name": "College Party"},

            # Step Family
            {"type_id": "search/step-daughter", "type_name": "Step Daughter"},
            {"type_id": "search/step-daddy", "type_name": "Step Daddy"},
            {"type_id": "search/step-sister", "type_name": "Step Sister"},
            {"type_id": "search/stepdad-and-stepdaughter", "type_name": "Stepdad & Stepdaughter"},
            {"type_id": "search/stepmom-and-stepson", "type_name": "Stepmom & Stepson"},

            # 其他热门
            {"type_id": "search/1-on-1", "type_name": "1 on 1"},
            {"type_id": "search/2-on-1", "type_name": "2 on 1"},
            {"type_id": "search/3-on-1", "type_name": "3 on 1"},
            {"type_id": "search/3some", "type_name": "Threesome"},
            {"type_id": "search/POV", "type_name": "POV"},
            {"type_id": "search/1080p", "type_name": "1080p"},
            {"type_id": "search/adult", "type_name": "Adult"},
            {"type_id": "search/adult-toys", "type_name": "Adult Toys"},
            {"type_id": "search/ai-generated", "type_name": "AI Generated"},
            {"type_id": "search/airplane-position", "type_name": "Airplane Position"},
            {"type_id": "search/anal-with-sex-machine", "type_name": "Anal Sex Machine"},
            {"type_id": "search/ass-to-mouth", "type_name": "Ass to Mouth"},
            {"type_id": "search/ass-to-pussy-atp", "type_name": "Ass to Pussy"},
            {"type_id": "search/beautiful", "type_name": "Beautiful"},
            {"type_id": "search/beautiful-face", "type_name": "Beautiful Face"},
            {"type_id": "search/beauty", "type_name": "Beauty"},
            {"type_id": "search/big-ass", "type_name": "Big Ass"},
            {"type_id": "search/big-ass-teen", "type_name": "Big Ass Teen"},
            {"type_id": "search/big-cock-blowjob", "type_name": "Big Cock Blowjob"},
            {"type_id": "search/black-and-white", "type_name": "Black and White"},
            {"type_id": "search/boy-fuck-girl", "type_name": "Boy Fuck Girl"},
            {"type_id": "search/cum-on-pussy", "type_name": "Cum on Pussy"},
            {"type_id": "search/cum-in-mouth", "type_name": "Cum in Mouth"},
            {"type_id": "search/fuck-my-pussy", "type_name": "Fuck My Pussy"},
            {"type_id": "search/pussy-fuck", "type_name": "Pussy Fuck"},
            {"type_id": "search/rough-sex-video", "type_name": "Rough Sex"},
            {"type_id": "search/sexy-girl", "type_name": "Sexy Girl"},
            {"type_id": "search/straight-to-the-ass", "type_name": "Straight to the Ass"},
            {"type_id": "search/super-hot-porn", "type_name": "Super Hot"},
            {"type_id": "search/tight-pussy-fuck", "type_name": "Tight Pussy"},
            {"type_id": "search/0-pussy", "type_name": "0 Pussy"},
            {"type_id": "search/family-sex", "type_name": "Family Sex"},
            {"type_id": "search/sexy-girl-sex", "type_name": "Sexy Girl Sex"},
            {"type_id": "search/sex-pussy", "type_name": "Sex Pussy"},
            {"type_id": "search/bear-and-cub", "type_name": "Bear And Cub"},
            {"type_id": "search/big-black-cock", "type_name": "Big Black Cock"},
            {"type_id": "search/big-black-dick", "type_name": "Big Black Dick"},
            {"type_id": "search/big-ass-milf", "type_name": "Big Ass Milf"},
            {"type_id": "search/big-ass-gape", "type_name": "Big Ass Gape"},
            {"type_id": "search/big-cock", "type_name": "Big Cock"},
            {"type_id": "search/big-cock-porn", "type_name": "Big Cock Porn"},
            {"type_id": "search/big-dick", "type_name": "Big Dick"},
            {"type_id": "search/big-dick-ts", "type_name": "Big Dick Ts"},
            {"type_id": "search/big-dicks", "type_name": "Big Dicks"},
            {"type_id": "search/big-dildo", "type_name": "Big Dildo"},
            {"type_id": "search/big-lips", "type_name": "Big Lips"},
            {"type_id": "search/big-mouth", "type_name": "Big Mouth"},
            {"type_id": "search/big-natural-tits", "type_name": "Big Natural Tits"},
            {"type_id": "search/big-nipples", "type_name": "Big Nipples"},
            {"type_id": "search/big-pussy", "type_name": "Big Pussy"},
            {"type_id": "search/big-pussy-lips", "type_name": "Big Pussy Lips"},
            {"type_id": "search/big-tits", "type_name": "Big Tits"},
            {"type_id": "search/big-tits-milf", "type_name": "Big Tits Milf"},
            {"type_id": "search/big-tits-ts", "type_name": "Big Tits Ts"},
            {"type_id": "search/big-woman", "type_name": "Big Woman"},
            {"type_id": "search/black-cock", "type_name": "Black Cock"},
            {"type_id": "search/black-cock-lover", "type_name": "Black Cock Lover"},
            {"type_id": "search/black-dick", "type_name": "Black Dick"},
            {"type_id": "search/black-girl", "type_name": "Black Girl"},
            {"type_id": "search/blowjob-porn", "type_name": "Blowjob Porn"},
            {"type_id": "search/blowjob-video", "type_name": "Blowjob Video"},
            {"type_id": "search/brazzers", "type_name": "Brazzers"},
            {"type_id": "search/brazilian", "type_name": "Brazilian"},
            {"type_id": "search/breasts", "type_name": "Breasts"},
            {"type_id": "search/brown-pussy", "type_name": "Brown Pussy"},
            {"type_id": "search/buceta", "type_name": "Buceta"},
            {"type_id": "search/bunda-grande", "type_name": "Bunda Grande"},
            {"type_id": "search/busty-milf", "type_name": "Busty Milf"},
            {"type_id": "search/butt-fuck", "type_name": "Butt Fuck"},
            {"type_id": "search/butt-sex", "type_name": "Butt Sex"},
            {"type_id": "search/caliente", "type_name": "Caliente"},
            {"type_id": "search/cock-rubbing", "type_name": "Cock Rubbing"},
            {"type_id": "search/cock-play", "type_name": "Cock Play"},
            {"type_id": "search/cock-suck", "type_name": "Cock Suck"},
            {"type_id": "search/cock-suckers", "type_name": "Cock Suckers"},
            {"type_id": "search/cock", "type_name": "Cock"},
            {"type_id": "search/college", "type_name": "College"},
            {"type_id": "search/coming-from-anal", "type_name": "Coming From Anal"},
            {"type_id": "search/creamy-pussy", "type_name": "Creamy Pussy"},
            {"type_id": "search/cum-in-pussy", "type_name": "Cum In Pussy"},
            {"type_id": "search/cum-on-ass", "type_name": "Cum On Ass"},
            {"type_id": "search/cum-on-belly-button", "type_name": "Cum On Belly Button"},
            {"type_id": "search/cum-on-bush", "type_name": "Cum On Bush"},
            {"type_id": "search/cum-on-face", "type_name": "Cum On Face"},
            {"type_id": "search/cum-on-tits", "type_name": "Cum On Tits"},
            {"type_id": "search/cumming-on-feet", "type_name": "Cumming On Feet"},
            {"type_id": "search/de-quatro", "type_name": "De Quatro"},
            {"type_id": "search/dick-sucking-porn", "type_name": "Dick Sucking Porn"},
            {"type_id": "search/ebony-ass", "type_name": "Ebony Ass"},
            {"type_id": "search/fat-ass", "type_name": "Fat Ass"},
            {"type_id": "search/free-hard-core-porn", "type_name": "Free Hard Core Porn"},
            {"type_id": "search/free-rough-sex", "type_name": "Free Rough Sex"},
            {"type_id": "search/free-rough-sex-porn", "type_name": "Free Rough Sex Porn"},
            {"type_id": "search/fuck-me-hard", "type_name": "Fuck Me Hard"},
            {"type_id": "search/fuck-my-pussy-hard", "type_name": "Fuck My Pussy Hard"},
            {"type_id": "search/fuck-her-hard", "type_name": "Fuck Her Hard"},
            {"type_id": "search/fucking-sex", "type_name": "Fucking Sex"},
            {"type_id": "search/girl-enjoying-sex", "type_name": "Girl Enjoying Sex"},
            {"type_id": "search/girl-fucked-hard", "type_name": "Girl Fucked Hard"},
            {"type_id": "search/girl-gets-fucked", "type_name": "Girl Gets Fucked"},
            {"type_id": "search/girl-get-fuck", "type_name": "Girl Get Fuck"},
            {"type_id": "search/girl-on-girl", "type_name": "Girl On Girl"},
            {"type_id": "search/girl-sucking-dick", "type_name": "Girl Sucking Dick"},
            {"type_id": "search/hard-and-fast-fucking", "type_name": "Hard And Fast Fucking"},
            {"type_id": "search/hard-cock", "type_name": "Hard Cock"},
            {"type_id": "search/hard-core-sex", "type_name": "Hard Core Sex"},
            {"type_id": "search/hard-fuck", "type_name": "Hard Fuck"},
            {"type_id": "search/hard-fucking", "type_name": "Hard Fucking"},
            {"type_id": "search/hard-porn", "type_name": "Hard Porn"},
            {"type_id": "search/hard-rough-sex", "type_name": "Hard Rough Sex"},
            {"type_id": "search/hard-sex", "type_name": "Hard Sex"},
        ]
        return {"class": classes}

    def _resolve_best_base(self):
        """解析 /best 实际跳转到的月份路径，例如 /best/2026-08"""
        if hasattr(self, "_best_base") and self._best_base:
            return self._best_base
        try:
            resp = self.session.get(self.siteUrl + "/best", timeout=10, allow_redirects=True)
            # 最终 URL 形如 https://www.xnxx.com/best/2026-08
            path = resp.url.split(".com")[-1].rstrip("/")
            if path.startswith("/best/"):
                self._best_base = path
            else:
                # 兜底：用当前年月
                from datetime import datetime
                self._best_base = "/best/" + datetime.now().strftime("%Y-%m")
        except Exception:
            from datetime import datetime
            self._best_base = "/best/" + datetime.now().strftime("%Y-%m")
        return self._best_base

    def _build_url(self, tid, pg):
        """统一构建列表页 URL"""
        pg = str(pg).strip()
        if not pg or pg == "0":
            pg = "1"

        # Best 特殊处理：必须用真实月份路径才能翻页
        if tid == "best":
            base = self._resolve_best_base()
            if pg == "1":
                return self.siteUrl + base
            return f"{self.siteUrl}{base}/{pg}"

        if tid in self.path_map:
            base = self.path_map[tid]
            if pg == "1":
                return self.siteUrl + base
            return f"{self.siteUrl}{base}/{pg}"

        if tid.startswith("best/"):
            if pg == "1":
                return f"{self.siteUrl}/{tid}"
            return f"{self.siteUrl}/{tid}/{pg}"

        if tid.startswith("search/"):
            keyword = tid[7:]
            if pg == "1":
                return f"{self.siteUrl}/search/{keyword}"
            return f"{self.siteUrl}/search/{keyword}/{pg}"

        if pg == "1":
            return f"{self.siteUrl}/search/{tid}"
        return f"{self.siteUrl}/search/{tid}/{pg}"

    def _parse_list(self, html):
        """多策略解析视频列表"""
        videos = []
        if not html or "Not found" in html[:200]:
            return videos

        try:
            soup = BeautifulSoup(html, "html.parser")
            items = soup.select("div.thumb-block.video") or soup.select("div.thumb-block")

            for item in items:
                try:
                    a = (item.select_one("a.thumb-link") or
                         item.select_one("div.thumb a") or
                         item.select_one("a[href*='video-']"))
                    if not a:
                        continue
                    href = a.get("href", "")
                    if not href or "video-" not in href:
                        continue

                    title_a = item.select_one("a.title") or item.select_one(".thumb-under a[title]")
                    if title_a:
                        title = title_a.get("title") or title_a.get_text(strip=True)
                    else:
                        title = a.get("title") or ""
                    if not title or title.startswith("thl(") or len(title) < 3:
                        title = href.split("/")[-1].replace("_", " ").title()

                    img = item.select_one("img")
                    pic = ""
                    if img:
                        pic = img.get("data-src") or img.get("src") or img.get("data-lazy-src") or ""

                    full_url = href if href.startswith("http") else self.siteUrl + href
                    videos.append({
                        "vod_id": full_url,
                        "vod_name": title.strip(),
                        "vod_pic": pic,
                        "vod_remarks": "XNXX"
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[XNXX] BS4 parse error: {e}")

        if len(videos) < 5:
            try:
                pattern = re.compile(
                    r'href="(/video-[a-z0-9]+/[^"]+)"[^>]*>.*?'
                    r'(?:title="([^"]+)"|>([^<]{5,80})</a>)',
                    re.DOTALL | re.IGNORECASE
                )
                seen = set()
                for m in pattern.finditer(html):
                    href = m.group(1)
                    if href in seen:
                        continue
                    seen.add(href)
                    title = (m.group(2) or m.group(3) or "").strip()
                    if not title or title.startswith("thl("):
                        title = href.split("/")[-1].replace("_", " ").title()
                    videos.append({
                        "vod_id": self.siteUrl + href,
                        "vod_name": title,
                        "vod_pic": "",
                        "vod_remarks": "XNXX"
                    })
                    if len(videos) >= 40:
                        break
            except Exception as e:
                print(f"[XNXX] regex parse error: {e}")

        return videos

    def categoryContent(self, tid, pg, filter, extend):
        try:
            url = self._build_url(tid, pg)
            html = self.fetch(url)
            videos = self._parse_list(html)

            pagecount = 99 if len(videos) >= 10 else max(1, int(pg) if str(pg).isdigit() else 1)
            return {
                "list": videos,
                "page": int(pg) if str(pg).isdigit() else 1,
                "pagecount": pagecount,
                "limit": 36,
                "total": pagecount * 36
            }
        except Exception as e:
            print(f"[XNXX] category error: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 36, "total": 0}

    def detailContent(self, ids):
        try:
            url = ids[0] if ids[0].startswith("http") else self.siteUrl + ids[0]
            html = self.fetch(url)
            if not html:
                return {"list": []}

            title_match = re.search(r'<title>([^<]+)</title>', html, re.I)
            title = title_match.group(1).strip() if title_match else "XNXX Video"
            title = re.sub(r'\s*-\s*XNXX.*', '', title, flags=re.I).strip()

            play_urls = []
            hls = re.search(r'setVideoHLS\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', html)
            if hls:
                play_urls.append(f"HLS${hls.group(1)}")
            high = re.search(r'setVideoUrlHigh\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', html)
            if high:
                play_urls.append(f"High${high.group(1)}")
            low = re.search(r'setVideoUrlLow\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', html)
            if low:
                play_urls.append(f"Low${low.group(1)}")
            if not play_urls:
                m3u8s = re.findall(r'(https?://[^\'"\s]+\.m3u8[^\'"\s]*)', html)
                for m in m3u8s[:2]:
                    play_urls.append(f"HLS备用${m}")
            if not play_urls:
                return {"list": []}

            return {
                "list": [{
                    "vod_id": ids[0],
                    "vod_name": title,
                    "vod_pic": "",
                    "vod_content": title,
                    "vod_play_from": "XNXX",
                    "vod_play_url": "#".join(play_urls)
                }]
            }
        except Exception as e:
            print(f"[XNXX] detail error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            header = {
                "User-Agent": self.headers["User-Agent"],
                "Referer": "https://www.xnxx.com/"
            }
            return {"parse": 0, "url": id, "header": json.dumps(header)}
        except Exception:
            return {"parse": 0, "url": id, "header": ""}

    def searchContent(self, key, quick, pg="1"):
        try:
            keyword = parse.quote(key)
            url = f"{self.siteUrl}/search/{keyword}/{pg}" if str(pg) != "1" else f"{self.siteUrl}/search/{keyword}"
            html = self.fetch(url)
            videos = self._parse_list(html)
            return {"list": videos}
        except Exception as e:
            print(f"[XNXX] search error: {e}")
            return {"list": []}

    def isVideoFormat(self, url):
        return any(x in url.lower() for x in [".m3u8", ".mp4", "hls", "video_"])

    def manualVideoCheck(self):
        return False


if __name__ == "__main__":
    spider = Spider()
    print("官方分类:")
    for c in spider.homeContent(None)["class"][:4]:
        print(f"  {c['type_name']:15} -> {c['type_id']}")
    print("总分类数:", len(spider.homeContent(None)["class"]))
    print()
    for tid in ["hot", "new", "hits", "best"]:
        r = spider.categoryContent(tid, "1", None, None)
        first = r["list"][0]["vod_name"][:45] if r.get("list") else "空"
        print(f"{tid:6} ({len(r.get('list',[])):2}条) {first}")
