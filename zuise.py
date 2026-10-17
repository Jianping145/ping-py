# -*- coding: utf-8 -*-
# zuise.co 色最色 - 蜂蜜影视爬虫
# 分类 /list/{id}  详情 /video/{id}  直链 m3u8
import re
import json
import requests
import urllib3
from urllib.parse import quote, unquote, urljoin

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://zuise.co"
        self.ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # 过门页需要的入口 cookie
        self.session.cookies.set("ff_entry", "zuise.co", domain="zuise.co")
        self.proxy = None
        self._apply_extend(extend)
        ad = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16)
        self.session.mount("http://", ad)
        self.session.mount("https://", ad)

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
        return "色最色"

    def isVideoFormat(self, url):
        if not url:
            return False
        low = url.lower()
        return any(x in low for x in (".m3u8", ".mp4", ".m4a", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return True

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def log(self, msg):
        try:
            print("[zuise] %s" % msg)
        except Exception:
            pass

    def _req(self, url, **kwargs):
        kwargs.setdefault("timeout", 20)
        kwargs.setdefault("verify", False)
        kwargs.setdefault("allow_redirects", True)
        if self.proxy:
            kwargs["proxies"] = self.proxy
        headers = kwargs.pop("headers", None)
        try:
            r = self.session.get(url, headers=headers, **kwargs)
            return r
        except Exception as e:
            self.log("req %s" % e)
            return None

    def _abs(self, href):
        if not href:
            return ""
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("http"):
            return href
        return urljoin(self.host, href)

    def homeContent(self, filter):
        # 与站内导航一致
        classes = [
            {"type_name": "国产精品", "type_id": "19"},
            {"type_name": "偷拍自拍", "type_id": "20"},
            {"type_name": "日本无码", "type_id": "21"},
            {"type_name": "中文有码", "type_id": "22"},
            {"type_name": "中文无码", "type_id": "23"},
            {"type_name": "卡通动漫", "type_id": "24"},
            {"type_name": "欧美高清", "type_id": "26"},
            {"type_name": "色图", "type_id": "28"},
            {"type_name": "日本有码", "type_id": "31"},
            {"type_name": "标签", "type_id": "11"},
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + "/")
        return {"list": self._parse_list(html, 40)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid)

        # 标签分类：第一层展示标签云
        if tid == "11":
            url = "%s/list/11" % self.host
            html = self._fetch(url)
            items = self._parse_tags(html, 100)
            return {
                "list": items,
                "page": 1,
                "pagecount": 1,
                "limit": 100,
                "total": len(items),
            }

        # 标签下的视频：tid 形如 vod-tags-name-FC2（folder 点击进入）
        if "vod-tags-name-" in tid:
            path = tid if tid.startswith("/") else "/" + tid
            base = path.split("-p-")[0]
            if pg <= 1:
                url = self.host + base
            else:
                url = "%s%s-p-%s" % (self.host, base, pg)
            html = self._fetch(url)
            items = self._parse_list(html, 60)
            return {
                "list": items,
                "page": pg,
                "pagecount": pg + 1 if items else pg,
                "limit": 40,
                "total": 999999,
            }

        # 普通分类 / 色图
        if pg <= 1:
            url = "%s/list/%s" % (self.host, tid)
        else:
            url = "%s/list-read-id-%s-p-%s" % (self.host, tid, pg)
        html = self._fetch(url)
        items = self._parse_list(html, 60)
        return {
            "list": items,
            "page": pg,
            "pagecount": pg + 1 if items else pg,
            "limit": 40,
            "total": 999999,
        }

    def searchContent(self, key, quick, pg="1"):
        url = "%s/search?wd=%s" % (self.host, quote(key))
        if str(pg) not in ("", "1"):
            url += "&p=%s" % pg
        html = self._fetch(url)
        return {"list": self._parse_list(html, 50)}

    def _fetch(self, url):
        # 确保入口 cookie
        if "ff_entry" not in self.session.cookies.get_dict():
            self.session.cookies.set("ff_entry", "zuise.co", domain="zuise.co")
        r = self._req(url)
        if not r:
            return ""
        # 若仍是门页，再写一次 cookie 重试
        if "走进X时代" in r.text or "line-enter" in r.text and "/video/" not in r.text:
            self.session.cookies.set("ff_entry", "zuise.co", domain="zuise.co")
            r = self._req(url)
        return r.text if r else ""

    def _parse_list(self, html, limit=40):
        """解析视频 /video/ 与色图 /photo/ 列表卡片。"""
        if not html:
            return []
        items, seen = [], set()
        # 视频或色图卡片
        for m in re.finditer(
            r'<a[^>]+href="(/(?:video|photo)/\d+)"[^>]*title="([^"]*)"[^>]*>',
            html,
            re.I,
        ):
            href, title = m.group(1), m.group(2).strip()
            if href in seen:
                continue
            seen.add(href)
            start = max(0, m.start() - 80)
            chunk = html[start : m.end() + 220]
            pic = ""
            pm = re.search(r'data-original="([^"]+)"', chunk)
            if not pm:
                pm = re.search(
                    r'(?:src|data-src)="((?:https?:)?//[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                    chunk,
                    re.I,
                )
            if pm:
                pic = self._abs(pm.group(1))
            remarks = ""
            dm = re.search(r'pic-text[^>]*>([^<]+)', chunk)
            if dm:
                remarks = dm.group(1).strip()
            elif href.startswith("/photo/"):
                remarks = "图集"
            if not title:
                continue
            items.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })
            if len(items) >= limit:
                break

        if not items:
            for m in re.finditer(r'href="(/(?:video|photo)/(\d+))"', html):
                href = m.group(1)
                if href in seen:
                    continue
                seen.add(href)
                chunk = html[max(0, m.start() - 100) : m.end() + 250]
                title_m = re.search(r'title="([^"]+)"', chunk)
                title = title_m.group(1).strip() if title_m else ("内容 " + m.group(2))
                pic_m = re.search(r'data-original="([^"]+)"', chunk)
                pic = self._abs(pic_m.group(1)) if pic_m else ""
                items.append({
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "图集" if href.startswith("/photo/") else "",
                })
                if len(items) >= limit:
                    break
        return items

    def _parse_tags(self, html, limit=80):
        """标签云 /list/11 → 可点进标签视频列表。"""
        if not html:
            return []
        items, seen = [], set()
        for m in re.finditer(
            r'href="(/vod-tags-name-([^"]+))"[^>]*>([^<]+)<',
            html,
            re.I,
        ):
            href, slug, name = m.group(1), m.group(2), m.group(3).strip()
            # 去掉分页链接
            if "-p-" in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            if not name:
                name = unquote(slug)
            items.append({
                "vod_id": href.lstrip("/"),  # 作 type_id：vod-tags-name-FC2
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "标签",
                "vod_tag": "folder",  # 蜂蜜/TVBox：点击进分类列表，不进详情
            })
            if len(items) >= limit:
                break
        return items

    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
            vid = unquote(str(vid))
            if vid.isdigit():
                path = "/video/" + vid
            else:
                path = vid if vid.startswith("/") else "/" + vid

            # 标签：把该标签下视频作为多集，点播时再解析 m3u8
            if "vod-tags-name-" in path:
                url = self._abs(path.split("-p-")[0])
                html = self._fetch(url)
                vlist = self._parse_list(html, 40)
                if not vlist:
                    return {"list": []}
                name = unquote(path.split("vod-tags-name-")[-1])
                eps = []
                for i, it in enumerate(vlist):
                    lab = it.get("vod_name") or ("第%d条" % (i + 1))
                    lab = re.sub(r"\s+", " ", lab)[:40]
                    eps.append("%s$%s" % (lab, it["vod_id"]))
                return {"list": [{
                    "vod_id": path,
                    "vod_name": name,
                    "vod_pic": vlist[0].get("vod_pic") or "",
                    "vod_content": "标签合集，共%d条" % len(eps),
                    "vod_play_from": "色最色",
                    "vod_play_url": "#".join(eps),
                }]}

            # 色图图集：无视频流，仅展示说明
            if path.startswith("/photo/"):
                url = self._abs(path)
                html = self._fetch(url)
                title = ""
                tm = re.search(r"<h1[^>]*>([^<]+)</h1>", html or "")
                if tm:
                    title = tm.group(1).strip()
                if not title:
                    tm = re.search(r"<title>([^_<]+)", html or "")
                    if tm:
                        title = tm.group(1).strip()
                pics = re.findall(
                    r'data-original="(/photo/[^"]+\.(?:jpg|jpeg|png|webp))"',
                    html or "",
                    re.I,
                )
                if not pics:
                    pics = re.findall(r'data-original="([^"]*photo/[^"]+)"', html or "", re.I)
                pic = self._abs(pics[0]) if pics else ""
                if pic and not pic.startswith("http"):
                    pic = "https://pic3.jise99.com" + (pics[0] if pics[0].startswith("/") else "/" + pics[0])
                # 蜂蜜以视频为主，图集无法播放；仍返回条目避免空白
                return {"list": [{
                    "vod_id": path,
                    "vod_name": title or path,
                    "vod_pic": pic,
                    "vod_content": "图集共%d张（站内看图，无视频流）" % len(pics),
                    "vod_play_from": "色最色",
                    "vod_play_url": "图集无视频$https://zuise.co%s" % path,
                }]}

            # 普通视频
            url = self._abs(path)
            html = self._fetch(url)
            if not html:
                return {"list": []}

            title = ""
            tm = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
            if tm:
                title = tm.group(1).strip()
            if not title:
                tm = re.search(r"<title>《?([^《》<]+)》?", html)
                if tm:
                    title = tm.group(1).strip()

            pic = ""
            pm = re.search(r'cms_player\s*=\s*\{[^}]*"poster"\s*:\s*"([^"]+)"', html)
            if pm:
                pic = pm.group(1).replace(chr(92) + '/', '/')
            if not pic:
                pm = re.search(r'property="og:image"\s+content="([^"]+)"', html)
                if pm:
                    pic = pm.group(1)

            play_url = ""
            um = re.search(r'cms_player\s*=\s*\{[^}]*"url"\s*:\s*"([^"]+)"', html)
            if um:
                play_url = um.group(1).replace(chr(92) + '/', '/')
            if not play_url:
                um = re.search(r'https?://[^"\'\s]+index\.m3u8', html)
                if um:
                    play_url = um.group(0)
            if not play_url:
                um = re.search(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html)
                if um:
                    play_url = um.group(0)

            if not play_url:
                return {"list": []}

            return {"list": [{
                "vod_id": path,
                "vod_name": title or path,
                "vod_pic": pic,
                "vod_content": "",
                "vod_play_from": "色最色",
                "vod_play_url": "正片$%s" % play_url,
            }]}
        except Exception as e:
            self.log("detail %s" % e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            url = unquote(str(id)).strip()
            headers = {
                "User-Agent": self.ua,
                "Referer": self.host + "/",
                "Origin": self.host,
            }
            # 标签集数传入的是 /video/id，现场取 m3u8
            if "/video/" in url and not url.startswith("http"):
                det = self.detailContent([url])
                lst = det.get("list") or []
                if lst:
                    pu = lst[0].get("vod_play_url") or ""
                    if "$" in pu:
                        url = pu.split("$", 1)[1]
            elif not url.startswith("http"):
                det = self.detailContent([url])
                lst = det.get("list") or []
                if lst:
                    pu = lst[0].get("vod_play_url") or ""
                    if "$" in pu:
                        url = pu.split("$", 1)[1]
            if self.isVideoFormat(url):
                return {"parse": 0, "jx": 0, "url": url, "header": headers}
            # 图集页等非直链
            if "zuise.co/photo" in url or url.endswith("/photo") or "/photo/" in url:
                return {"parse": 1, "jx": 0, "url": url, "header": headers}
            return {"parse": 1, "jx": 0, "url": url, "header": headers}
        except Exception as e:
            self.log("player %s" % e)
            return {"parse": 0, "url": str(id), "header": {"User-Agent": self.ua}}

    def localProxy(self, param):
        try:
            url = unquote((param or {}).get("url", ""))
            if not url:
                return [400, "text/plain", b"missing"]
            r = self.session.get(
                url,
                headers={"User-Agent": self.ua, "Referer": self.host + "/"},
                timeout=20,
                verify=False,
                proxies=self.proxy,
            )
            return [r.status_code, r.headers.get("Content-Type", "application/octet-stream"), r.content]
        except Exception as e:
            return [500, "text/plain", str(e).encode()]
