# -*- coding: utf-8 -*-
"""
午夜影院 — https://wuyeov.wiki/
蜂蜜影视 Python 源
分类: /category/{slug}/  分页: /category/{slug}/{page}/
详情: /video/{id}/  播放: window.__ARCHIVE_PLAYER__ => cdnLine + rawPath
搜索: /search/{kw}/
"""
import json
import re
import sys
from urllib.parse import quote, unquote

sys.path.append("..")
from base.spider import Spider


class Spider(Spider):

    siteUrl = "https://wuyeov.wiki"
    UA = (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )

    # 与网站顶栏一致：父分类多为空，使用可出片的子分类
    CATE = [
        # 热播
        ("cate33", "热播/每日更新"),
        ("cate34", "热播/高颜尤物"),
        ("cate35", "热播/元气美少女"),
        ("cate36", "热播/可爱萝莉"),
        ("cate37", "热播/TS"),
        ("cate38", "热播/女同性恋"),
        ("cate39", "热播/口爆颜射"),
        ("cate40", "热播/巨乳女神"),
        ("cate41", "热播/媚黑"),
        ("cate42", "热播/JK妹妹"),
        ("cate43", "热播/福利姬"),
        ("cate44", "热播/网红黑料"),
        ("cate45", "热播/女仆"),
        ("cate46", "热播/动漫"),
        ("cate47", "热播/偷窥街拍"),
        ("cate48", "热播/婚纱"),
        ("cate49", "热播/反差婊"),
        ("cate50", "热播/偷情约炮"),
        ("cate51", "热播/短剧微剧"),
        ("cate52", "热播/直播裸舞"),
        ("cate53", "热播/色情综艺"),
        # 乱伦
        ("cate20", "乱伦/亲情"),
        ("cate21", "乱伦/姐弟"),
        ("cate22", "乱伦/全家"),
        ("cate23", "乱伦/母爱"),
        ("cate24", "乱伦/嫂子"),
        ("cate25", "乱伦/妹妹"),
        ("cate26", "乱伦/小姨子"),
        ("cate27", "乱伦/儿媳"),
        ("cate28", "乱伦/母女"),
        ("cate29", "乱伦/师生"),
        ("cate30", "乱伦/兽父"),
        ("cate31", "乱伦/爷孙"),
        # 网黄（代表）
        ("cate55", "网黄/辛尤里"),
        ("cate56", "网黄/阿朱姐姐"),
        ("cate57", "网黄/NicoLove"),
        ("cate58", "网黄/御梦子"),
        ("cate59", "网黄/小桃酱"),
        ("cate60", "网黄/刘玥"),
        ("cate61", "网黄/吴梦梦"),
        ("cate62", "网黄/米菲兔"),
        ("cate63", "网黄/桥本香菜"),
        ("cate64", "网黄/小水水"),
        ("cate65", "网黄/台北娜娜"),
        # VIP / 传媒 / 探花
        ("cate90", "VIP专区"),
        ("cate92", "传媒/麻豆"),
        ("cate93", "传媒/糖心VLOG"),
        ("cate94", "传媒/JVID"),
        ("cate95", "传媒/91制片厂"),
        ("cate96", "传媒/星空"),
        ("cate97", "传媒/其它"),
        ("cate98", "传媒/性视界"),
        ("cate99", "传媒/大象"),
        ("cate100", "传媒/爱豆"),
        ("cate101", "传媒/杏吧"),
        ("cate102", "传媒/果冻"),
        ("cate103", "传媒/精东"),
        ("cate107", "探花/高端外围"),
        ("cate108", "探花/足浴会所"),
        ("cate109", "探花/精选探花"),
        ("cate110", "探花/杏吧探花"),
        ("cate111", "探花/街边探店"),
        ("cate112", "探花/双飞"),
        ("cate113", "探花/商K"),
        ("cate114", "探花/换妻"),
        ("cate115", "探花/金先生"),
        ("cate116", "探花/李寻欢"),
        ("cate117", "探花/小宝寻花"),
        ("cate118", "探花/文轩"),
        # 日韩
        ("cate121", "日韩/素人"),
        ("cate122", "日韩/SM"),
        ("cate123", "日韩/巨乳"),
        ("cate124", "日韩/热门女优"),
        ("cate125", "日韩/中文字幕"),
        ("cate126", "日韩/高清无码"),
        ("cate127", "日韩/韩国精选"),
        ("cate128", "日韩/水果派"),
        ("cate129", "日韩/乱伦"),
        ("cate130", "日韩/NTR"),
        ("cate131", "日韩/同人"),
        ("cate132", "日韩/搜查官"),
        # 欧美
        ("cate138", "欧美/精选"),
        ("cate139", "欧美/SmeetH"),
        ("cate140", "欧美/剧情"),
        ("cate141", "欧美/按摩会所"),
        ("cate142", "欧美/抖音满天星"),
        ("cate143", "欧美/绿帽"),
        ("cate144", "欧美/小马拉大车"),
        ("cate145", "欧美/黑白配"),
        ("cate146", "欧美/街头搭讪"),
        ("cate147", "欧美/洋马"),
        ("cate148", "欧美/超市惩罚"),
    ]

    def init(self, extend=""):
        return

    def getName(self):
        return "午夜影院"

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return ".m3u8" in u or ".mp4" in u or ".ts" in u

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    def _headers(self):
        return {
            "User-Agent": self.UA,
            "Referer": self.siteUrl + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _get(self, url):
        try:
            if not url.startswith("http"):
                url = self.siteUrl + (url if url.startswith("/") else "/" + url)
            rsp = self.fetch(url, headers=self._headers())
            if rsp is None:
                return ""
            if hasattr(rsp, "text") and rsp.text:
                return rsp.text
            if hasattr(rsp, "content") and rsp.content:
                try:
                    return rsp.content.decode("utf-8", errors="ignore")
                except Exception:
                    return str(rsp.content)
            return str(rsp)
        except Exception:
            return ""

    def _extract_id(self, href):
        href = unquote(str(href or ""))
        m = re.search(r"/video/(\d+)/?", href)
        if m:
            return m.group(1)
        if re.match(r"^\d{10,}$", href.strip()):
            return href.strip()
        return ""

    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos

        for m in re.finditer(r'href="(/video/(\d+)/)"', html):
            vod_id = m.group(2)
            if vod_id in seen:
                continue
            seen.add(vod_id)
            start = max(0, m.start() - 120)
            end = min(len(html), m.end() + 700)
            block = html[start:end]

            name = ""
            for pat in [
                r'alt="([^"]+)"',
                r'aria-label="([^"]+)"',
                r'title="([^"]+)"',
                r'fg-card-title[^>]*>\s*([^<]+)',
                r'fg-video-title[^>]*>\s*([^<]+)',
                r'<strong[^>]*>\s*([^<]+)',
            ]:
                tm = re.search(pat, block)
                if tm and tm.group(1).strip():
                    name = tm.group(1).strip()
                    break
            if not name:
                name = vod_id

            pic = ""
            pm = re.search(r'data-src="(https?://[^"]+)"', block)
            if not pm:
                pm = re.search(r'src="(https?://[^"]+)"', block)
            if pm:
                pic = pm.group(1)

            remarks = ""
            dm = re.search(r'fg-duration[^>]*>\s*([^<]+)', block)
            if dm:
                remarks = dm.group(1).strip()

            videos.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })
            if len(videos) >= 48:
                break
        return videos

    def _page_count(self, html, slug):
        try:
            nums = re.findall(r"/category/%s/(\d+)/" % re.escape(str(slug)), html)
            vals = [int(x) for x in nums if str(x).isdigit() and int(x) > 0]
            if vals:
                return min(max(vals), 999)
        except Exception:
            pass
        return 99

    def _parse_play(self, html):
        if not html:
            return "午夜影院", "正片$"

        # window.__ARCHIVE_PLAYER__ = {...}
        m = re.search(
            r"window\.__ARCHIVE_PLAYER__\s*=\s*(\{.*?\})\s*;?\s*</script>",
            html, re.S
        )
        if m:
            try:
                info = json.loads(m.group(1))
                raw = (info.get("rawPath") or "").replace("\\/", "/")
                cdn = (info.get("cdnLine") or "").replace("\\/", "/").rstrip("/")
                if raw:
                    if raw.startswith("http"):
                        url = raw
                    elif cdn:
                        url = cdn + (raw if raw.startswith("/") else "/" + raw)
                    else:
                        url = "https://d2qyuoh1tjbp7d.cloudfront.net" + (
                            raw if raw.startswith("/") else "/" + raw
                        )
                    if ".m3u8" in url or ".mp4" in url:
                        return "午夜影院", "正片$%s" % url
            except Exception:
                pass

        # 兜底：拼接 cdn + path
        m1 = re.search(r'"rawPath"\s*:\s*"([^"]+)"', html)
        m2 = re.search(r'"cdnLine"\s*:\s*"([^"]+)"', html)
        if m1:
            raw = m1.group(1).replace("\\/", "/")
            cdn = (m2.group(1).replace("\\/", "/") if m2 else "").rstrip("/")
            if not cdn:
                cdn = "https://d2qyuoh1tjbp7d.cloudfront.net"
            url = raw if raw.startswith("http") else (cdn + (raw if raw.startswith("/") else "/" + raw))
            return "午夜影院", "正片$%s" % url

        for m in re.finditer(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html):
            u = m.group(1).replace("\\/", "/").rstrip("\\;,")
            if "google" in u:
                continue
            return "午夜影院", "正片$%s" % u

        return "午夜影院", "正片$"

    def homeContent(self, filter):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self.CATE]
        return {"class": classes}

    def homeVideoContent(self):
        # 首页混杂广告，改用「每日更新」
        return self.categoryContent("cate33", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        slug = str(tid).strip()
        if page <= 1:
            url = "%s/category/%s/" % (self.siteUrl, slug)
        else:
            url = "%s/category/%s/%d/" % (self.siteUrl, slug, page)
        html = self._get(url)
        videos = self._parse_list(html)
        # 部分分类首页为空时试 /1/
        if not videos and page <= 1:
            html = self._get("%s/category/%s/1/" % (self.siteUrl, slug))
            videos = self._parse_list(html)
        pagecount = self._page_count(html, slug)
        return {
            "list": videos,
            "page": page,
            "pagecount": max(pagecount, 1),
            "limit": 24,
            "total": pagecount * 24,
        }

    def detailContent(self, ids):
        vid = str(ids[0])
        vod_id = self._extract_id(vid) or vid
        url = "%s/video/%s/" % (self.siteUrl, vod_id)
        html = self._get(url)
        if not html:
            return {"list": []}

        title = ""
        m = re.search(r'class="fg-video-title"[^>]*>([^<]+)', html)
        if m:
            title = m.group(1).strip()
        if not title:
            m = re.search(r"<title>([^<]+)", html)
            if m:
                title = re.sub(r"\s*[-|].*?午夜.*$", "", m.group(1)).strip()
                title = re.sub(r"\s*[-|].*?影院.*$", "", title).strip()

        pic = ""
        m = re.search(r'"posterImg"\s*:\s*"([^"]+)"', html)
        if m:
            pic = m.group(1).replace("\\/", "/")
        if not pic:
            m = re.search(r'data-src="(https?://[^"]+)"', html)
            if m:
                pic = m.group(1)

        remarks = ""
        m = re.search(r'fg-video-meta[^>]*>[\s\S]{0,200}?<span>([^<]+)</span>', html)
        if m:
            remarks = m.group(1).strip()

        play_from, play_url = self._parse_play(html)
        return {"list": [{
            "vod_id": vod_id,
            "vod_name": title or vod_id,
            "vod_pic": pic,
            "vod_remarks": remarks,
            "vod_content": "",
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }]}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        # /search/{kw}/ 或 /search/{kw}/{page}/
        kw = quote(key.strip())
        if page <= 1:
            url = "%s/search/%s/" % (self.siteUrl, kw)
        else:
            url = "%s/search/%s/%d/" % (self.siteUrl, kw, page)
        html = self._get(url)
        videos = self._parse_list(html)
        if not videos:
            html = self._get("%s/?s=%s" % (self.siteUrl, kw))
            videos = self._parse_list(html)
        return {"list": videos, "page": page, "pagecount": page + 1 if videos else 1}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": {
                "User-Agent": self.UA,
                "Referer": self.siteUrl + "/",
                "Origin": self.siteUrl,
            },
        }

    def localProxy(self, param):
        return [200, "text/plain", b""]
