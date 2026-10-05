# -*- coding: utf-8 -*-
# 85po.com TVBox Spider v5
# 修复：原域名 85po.com 已过期/被墙，切换到可用新域名 85po.net（备选 85po.co）
# 域名自动探测：按顺序尝试多个候选域名，取第一个能正常返回列表页的

import re
import json
import time
from urllib.parse import quote

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

import requests


class Spider:
    # 候选域名，按可用性排序（2026-10 验证：85po.net 可用）
    CANDIDATE_SITES = [
        "https://www.85po.net",
        "https://85po.net",
        "https://www.85po.co",
        "https://85po.co",
    ]

    def __init__(self):
        self.siteUrl = ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,en;q=0.7",
            "Referer": "https://www.85po.net/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self.cateMap = {
            "1": {"name": "最新更新", "url": "/latest-updates/"},
            "2": {"name": "高分评价", "url": "/top-rated/"},
            "3": {"name": "最受欢迎", "url": "/most-popular/"},
            "4": {"name": "日本", "url": "/categories/ri-ben/"},
            "5": {"name": "中国", "url": "/categories/zhong-guo/"},
            "6": {"name": "台湾", "url": "/categories/tai-wan/"},
            "7": {"name": "马来西亚", "url": "/categories/ma-lai-xi-ya/"},
            "8": {"name": "香港", "url": "/categories/xiang-gang/"},
            "9": {"name": "美女", "url": "/tags/mei-nv/"},
            "10": {"name": "品乳", "url": "/tags/pin-ru/"},
        }
        self._site_checked = False

    def getName(self):
        return "85PO"

    def init(self, extend=""):
        pass

    def _ensureSite(self):
        """探测并锁定可用域名"""
        if self._site_checked and self.siteUrl:
            return True
        for site in self.CANDIDATE_SITES:
            try:
                r = self.session.get(site + "/latest-updates/", timeout=10)
                if r.status_code == 200 and len(r.text) > 5000 and "/video/" in r.text:
                    self.siteUrl = site
                    self.session.headers["Referer"] = site + "/"
                    self._site_checked = True
                    print(f"[85PO] 使用域名: {site}")
                    return True
            except Exception:
                continue
        print("[85PO] 所有候选域名均不可用")
        return False

    def isVideoFormat(self, url):
        if not url:
            return False
        return any(x in url.lower() for x in [".m3u8", ".mp4", ".flv", ".m3u", "get_file"])

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        result = {"class": []}
        for tid, info in self.cateMap.items():
            result["class"].append({
                "type_id": tid,
                "type_name": info["name"]
            })
        return result

    def homeVideoContent(self):
        return self.categoryContent("1", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        result = {
            "list": [],
            "page": str(pg),
            "pagecount": 999,
            "limit": 24,
            "total": 99999
        }
        try:
            if not self._ensureSite():
                return result
            if tid not in self.cateMap:
                return result

            path = self.cateMap[tid]["url"]
            pg = int(pg) if str(pg).isdigit() else 1

            if pg > 1:
                url = self.siteUrl + path.rstrip("/") + f"/{pg}/"
            else:
                url = self.siteUrl + path

            html = self.fetch(url)
            if not html or len(html) < 500:
                print(f"empty html for {url}")
                return result

            low = html.lower()
            if "attention required" in low or "just a moment" in low:
                print("CF blocked")
                return result

            videos = self.parseVideoList(html)
            result["list"] = videos
            result["pagecount"] = self.extractPageCount(html)
            print(f"parsed {len(videos)} videos from {url}")

        except Exception as e:
            print(f"categoryContent error: {e}")
        return result

    def detailContent(self, ids):
        result = {"list": []}
        try:
            if not self._ensureSite():
                return result
            vid = ids[0] if isinstance(ids, list) else ids
            if not vid.startswith("http"):
                url = self.siteUrl + (vid if vid.startswith("/") else "/" + vid)
            else:
                url = vid.replace("https://www.85po.com", self.siteUrl).replace("https://85po.com", self.siteUrl)

            html = self.fetch(url)
            if not html:
                return result

            title = self.extractTitle(html)
            pic = self.extractPic(html)
            play_from, play_url = self.extractPlayUrls(html)

            remarks = ""
            m = re.search(r'<div class="duration">([^<]+)</div>', html)
            if m:
                remarks = m.group(1).strip()
            if not remarks:
                m = re.search(r'icon-playlist[^>]*>[\s\S]*?<span class="text">([^<]+)</span>', html)
                if m:
                    remarks = m.group(1).strip()

            vod = {
                "vod_id": vid,
                "vod_name": title or "未知标题",
                "vod_pic": pic or "",
                "vod_content": "",
                "type_name": "",
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": remarks,
                "vod_actor": "",
                "vod_director": "",
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
            result["list"].append(vod)
        except Exception as e:
            print(f"detailContent error: {e}")
        return result

    def playerContent(self, flag, id, vipFlags):
        header = dict(self.headers)
        header["Referer"] = (self.siteUrl or "https://www.85po.net") + "/"
        result = {
            "parse": 0 if self.isVideoFormat(id) else 1,
            "playUrl": "",
            "url": id,
            "header": json.dumps(header)
        }
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": []}
        try:
            if not self._ensureSite():
                return result
            pg = int(pg) if str(pg).isdigit() else 1
            if pg > 1:
                url = f"{self.siteUrl}/search/{quote(key)}/{pg}/"
            else:
                url = f"{self.siteUrl}/search/{quote(key)}/"

            html = self.fetch(url)
            if not html or "attention required" in html.lower():
                url2 = f"{self.siteUrl}/search/?q={quote(key)}"
                if pg > 1:
                    url2 += f"&page={pg}"
                html = self.fetch(url2)

            if html and "attention required" not in html.lower():
                result["list"] = self.parseVideoList(html)
        except Exception as e:
            print(f"searchContent error: {e}")
        return result

    def parseVideoList(self, html):
        videos = []
        seen = set()

        if BeautifulSoup:
            try:
                soup = BeautifulSoup(html, "html.parser")

                items = soup.select("div.item")
                if len(items) < 3:
                    items = soup.select("div.list-videos div.item, .list-videos .item")

                for item in items:
                    try:
                        a = item.find("a", href=True)
                        if not a:
                            continue
                        href = a.get("href", "").strip()
                        if "/video/" not in href:
                            continue
                        if href.startswith("http"):
                            href = re.sub(r'^https?://[^/]+', '', href)
                        if href in seen:
                            continue
                        seen.add(href)

                        name = ""
                        t = item.select_one("strong.title, .title, strong")
                        if t:
                            name = t.get_text(strip=True)
                        if not name:
                            name = a.get("title") or ""
                        name = re.sub(r'\s+', ' ', name).strip()[:100]
                        if not name:
                            continue

                        pic = ""
                        img = item.select_one("img")
                        if img:
                            pic = (img.get("data-original") or img.get("data-webp") or
                                   img.get("data-src") or img.get("src") or "")
                            if pic.startswith("data:"):
                                pic = img.get("data-original") or img.get("data-webp") or ""
                            if pic.startswith("//"):
                                pic = "https:" + pic
                            elif pic.startswith("/"):
                                pic = (self.siteUrl or "https://www.85po.net") + pic

                        remarks = ""
                        dur = item.select_one(".duration")
                        if dur:
                            remarks = dur.get_text(strip=True)

                        videos.append({
                            "vod_id": href,
                            "vod_name": name,
                            "vod_pic": pic,
                            "vod_remarks": remarks
                        })
                    except Exception:
                        continue

                if len(videos) >= 3:
                    return videos[:48]
            except Exception as e:
                print(f"BS4 error: {e}")

        try:
            links = re.findall(r'href=["\']((?:https?://[^"\']+)?/video/\d+/[^"\']+)["\']', html, re.I)
            titles = re.findall(r'(?:title=["\']([^"\']{4,80})["\']|class=["\'](?:card-)?title["\'][^>]*>([^<]{4,80})|class=["\']title["\'][^>]*>([^<]{4,80}))', html, re.I)
            pics = re.findall(r'data-original=["\']([^"\']+)["\']', html, re.I)
            if not pics:
                pics = re.findall(r'data-webp=["\']([^"\']+)["\']', html, re.I)
            durs = re.findall(r'class=["\']duration["\'][^>]*>([^<]+)', html, re.I)

            for i, link in enumerate(links):
                if link.startswith("http"):
                    link = re.sub(r'^https?://[^/]+', '', link)
                if link in seen:
                    continue
                seen.add(link)
                t = titles[i] if i < len(titles) else ("", "", "")
                if isinstance(t, tuple):
                    name = t[0] or t[1] or t[2] or f"视频{i+1}"
                else:
                    name = str(t) or f"视频{i+1}"
                name = re.sub(r'\s+', ' ', str(name)).strip()[:100]
                pic = pics[i] if i < len(pics) else ""
                if pic.startswith("/"):
                    pic = (self.siteUrl or "https://www.85po.net") + pic
                elif pic.startswith("//"):
                    pic = "https:" + pic
                remarks = durs[i].strip() if i < len(durs) else ""
                videos.append({
                    "vod_id": link,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
                if len(videos) >= 48:
                    break
        except Exception as e:
            print(f"regex error: {e}")

        return videos

    def extractPageCount(self, html):
        try:
            pages = re.findall(r'/(?:latest-updates|top-rated|most-popular|categories/[^/]+|tags/[^/]+)/(\d+)/', html)
            if pages:
                nums = [int(p) for p in pages if p.isdigit() and int(p) > 1]
                if nums:
                    return min(max(nums), 999)
        except Exception:
            pass
        return 999

    def extractTitle(self, html):
        try:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
            if m:
                return re.sub(r'<[^>]+>', '', m.group(1)).strip()
            m = re.search(r'og:title["\']\s+content=["\']([^"\']+)', html, re.I)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
        return ""

    def extractPic(self, html):
        try:
            m = re.search(r'og:image["\']\s+content=["\']([^"\']+)', html, re.I)
            if m:
                return m.group(1)
            m = re.search(r'"thumbnailUrl"\s*:\s*"([^"]+)"', html)
            if m:
                return m.group(1)
        except Exception:
            pass
        return ""

    def extractPlayUrls(self, html):
        urls = []
        try:
            m = re.search(r"video_alt_url2:\s*['\"]([^'\"]+)['\"]", html)
            if m:
                urls.append(("1080P", m.group(1)))
            m = re.search(r"video_alt_url:\s*['\"]([^'\"]+)['\"]", html)
            if m:
                urls.append(("720P", m.group(1)))
            m = re.search(r"video_url:\s*['\"]([^'\"]+)['\"]", html)
            if m:
                urls.append(("480P", m.group(1)))

            if not urls:
                m = re.search(r'"contentUrl"\s*:\s*"([^"]+get_file[^"]+)"', html)
                if m:
                    urls.append(("正片", m.group(1)))

            if not urls:
                m = re.search(r'(https?://[^"\'\s]+get_file/[^"\'\s]+\.mp4[^"\'\s]*)', html)
                if m:
                    urls.append(("正片", m.group(1)))
        except Exception as e:
            print(f"extractPlayUrls error: {e}")

        if not urls:
            return "85PO", "正片$"

        seen = set()
        froms = []
        links = []
        for name, u in urls:
            if u not in seen:
                seen.add(u)
                froms.append(name)
                links.append(u)

        play_from = "$$$".join(froms)
        play_url = "$$$".join([f"正片${u}" for u in links])
        return play_from, play_url

    def fetch(self, url, retry=3):
        for i in range(retry):
            try:
                r = self.session.get(url, timeout=18, allow_redirects=True)
                if r.status_code == 200:
                    text = r.text
                    if "Just a moment" in text or "Attention Required" in text:
                        print(f"CF challenge on {url}")
                        time.sleep(1.5)
                        continue
                    r.encoding = r.apparent_encoding or "utf-8"
                    return r.text
                print(f"status {r.status_code} for {url}")
                time.sleep(1)
            except Exception as e:
                print(f"fetch error {i}: {e}")
                time.sleep(1.2)
        return ""


if __name__ == "__main__":
    sp = Spider()
    home = sp.homeContent(False)
    print("分类:", json.dumps(home, ensure_ascii=False))

    cat = sp.categoryContent("1", "1", False, {})
    print(f"\n分类页返回 {len(cat['list'])} 条")
    for v in cat['list'][:3]:
        print(json.dumps(v, ensure_ascii=False))

    if cat['list']:
        det = sp.detailContent([cat['list'][0]['vod_id']])
        if det['list']:
            vod = det['list'][0]
            print(f"\n详情: {vod['vod_name']}")
            print(f"线路: {vod['vod_play_from']}")
            print(f"地址: {vod['vod_play_url'][:120]}...")