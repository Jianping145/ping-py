# -*- coding: utf-8 -*-
# ============================================================
# 适配 https://flos-ubn-669t.xflooow8s701.cc 的 TVBox 爬虫脚本
# 网站：51吃瓜网 (MacCMS)
# 功能：首页 / 分类 / 详情 / 播放 / 搜索
# 更新：传媒35个/番号50个/探花16个 全部展平，女优系列保留
# ============================================================

from __future__ import print_function
import re
import json
import ssl

try:
    import html
except ImportError:
    import HTMLParser
    html = HTMLParser.HTMLParser()

try:
    from urllib.request import Request, urlopen
    from urllib.parse import urljoin, quote, unquote
except ImportError:
    from urllib2 import Request, urlopen
    from urlparse import urljoin
    from urllib import quote, unquote

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider:
        def init(self, extend=""): pass
        def homeContent(self, filter): pass
        def homeVideoContent(self): pass
        def categoryContent(self, tid, pg, filter, extend): pass
        def detailContent(self, ids): pass
        def playerContent(self, flag, id, vipFlags=None): pass
        def searchContent(self, key, quick, pg='1'): pass
        def isVideoFormat(self, url): pass
        def manualVideoCheck(self): pass
        def localProxy(self, param): pass


def clean_text(text):
    if not text:
        return ""
    try:
        text = html.unescape(str(text))
    except:
        try:
            text = html.unescape(str(text))
        except:
            pass
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fix_url(url, host):
    if not url:
        return ""
    url = url.strip()
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        return urljoin(host, url)
    if url.startswith(('http://', 'https://')):
        return url
    return urljoin(host, '/' + url)


class Spider(BaseSpider):

    def __init__(self):
        try:
            BaseSpider.__init__(self)
        except:
            pass
        self.host = "https://flos-ubn-669t.xflooow8s701.cc"
        self.name = "xfl_spider"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def init(self, extend=""):
        if extend and str(extend).startswith("http"):
            self.host = str(extend).rstrip("/")

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        url = str(url)
        return ".m3u8" in url or ".mp4" in url or ".flv" in url or ".ts" in url

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "video/MP2T", b"", {}]

    def _fetch(self, url, referer=None):
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.host, url)
        try:
            headers = {"User-Agent": self.user_agent}
            if referer:
                headers["Referer"] = referer
            req = Request(url, headers=headers)
            r = urlopen(req, timeout=15)
            return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print("[%s] 请求失败: %s" % (self.name, e))
            return ""

    def _parse_video_items(self, html_text):
        if not html_text:
            return []
        videos = []

        start_match = re.search(r'<div[^>]*class="[^"]*appel-max[^"]*"[^>]*>', html_text)
        if start_match:
            start_pos = start_match.end()
            depth = 0
            end_pos = start_pos
            i = start_pos
            while i < len(html_text):
                if html_text[i:i+4] == '<div':
                    depth += 1
                    i += 4
                elif html_text[i:i+6] == '</div>':
                    if depth == 0:
                        end_pos = i + 6
                        break
                    depth -= 1
                    i += 6
                else:
                    i += 1

            if end_pos > start_pos:
                container = html_text[start_pos:end_pos]
                pattern = r'<li[^>]*>.*?<a[^>]*href="/voddetail/(\d+)/"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?<h5>.*?<a[^>]*>(.*?)</a>.*?</h5>'
                matches = re.findall(pattern, container, re.DOTALL)
                for match in matches:
                    try:
                        if len(match) == 4:
                            vid, pic, alt, title = match
                            title = clean_text(title or alt)
                            pic = fix_url(pic, self.host)
                            if vid and title:
                                videos.append({
                                    "vod_id": vid,
                                    "vod_name": title,
                                    "vod_pic": pic,
                                    "vod_remarks": ""
                                })
                    except:
                        continue
                if videos:
                    return videos

        ul_match = re.search(r'<ul[^>]*class="[^"]*thumbnail-group[^"]*"[^>]*>(.*?)</ul>', html_text, re.DOTALL)
        if ul_match:
            ul_content = ul_match.group(1)
            pattern = r'<li[^>]*>.*?<a[^>]*href="/voddetail/(\d+)/"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?<h5>.*?<a[^>]*>(.*?)</a>.*?</h5>'
            matches = re.findall(pattern, ul_content, re.DOTALL)
            for match in matches:
                try:
                    if len(match) == 4:
                        vid, pic, alt, title = match
                        title = clean_text(title or alt)
                        pic = fix_url(pic, self.host)
                        if vid and title:
                            videos.append({
                                "vod_id": vid,
                                "vod_name": title,
                                "vod_pic": pic,
                                "vod_remarks": ""
                            })
                except:
                    continue

        return videos

    def _parse_extend(self, extend):
        if not extend:
            return {}
        if isinstance(extend, dict):
            return extend
        try:
            ext_str = str(extend).strip()
            if not ext_str or ext_str in ('None', 'null', '{}', '[]'):
                return {}
            try:
                return json.loads(ext_str)
            except:
                pass
            try:
                result = {}
                for pair in ext_str.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        result[k] = unquote(v) if 'unquote' in globals() else v
                return result
            except:
                pass
            try:
                parsed = eval(ext_str)
                if isinstance(parsed, dict):
                    return parsed
            except:
                pass
        except:
            pass
        try:
            d = dict(extend)
            if isinstance(d, dict):
                return d
        except:
            pass
        return {}

    # ============================================================
    # 首页分类 - 全部展平
    # ============================================================

    def homeContent(self, filter=True):
        classes = [
            # === 视频分区 ===
            {"type_id": "45", "type_name": "视频一区"},
            {"type_id": "55", "type_name": "国产乱伦"},
            {"type_id": "50", "type_name": "无码流出"},
            {"type_id": "51", "type_name": "日本高清"},
            {"type_id": "52", "type_name": "中文字幕"},
            {"type_id": "53", "type_name": "欧美极品"},
            {"type_id": "54", "type_name": "动漫精品"},
            {"type_id": "56", "type_name": "SM变态"},
            {"type_id": "57", "type_name": "自拍偷拍"},
            {"type_id": "46", "type_name": "视频二区"},
            {"type_id": "49", "type_name": "国产精品"},
            {"type_id": "65", "type_name": "国产热瓜"},
            {"type_id": "64", "type_name": "主播诱惑"},
            {"type_id": "63", "type_name": "良家少女"},
            {"type_id": "61", "type_name": "淫荡熟女"},
            {"type_id": "62", "type_name": "三级伦理"},
            {"type_id": "58", "type_name": "旗袍风情"},
            {"type_id": "59", "type_name": "岛国小女"},
            {"type_id": "47", "type_name": "视频三区"},
            {"type_id": "68", "type_name": "剧情解说"},
            {"type_id": "71", "type_name": "网红黑料"},
            {"type_id": "73", "type_name": "暴++小学生"},
            {"type_id": "70", "type_name": "同性世界"},
            {"type_id": "72", "type_name": "国产高清"},
            {"type_id": "69", "type_name": "美乳妹妹"},
            {"type_id": "67", "type_name": "黑料网曝"},
            {"type_id": "66", "type_name": "国产探花"},
            # === 传媒系列 35个 ===
            {"type_id": "201", "type_name": "综合传媒"},
            {"type_id": "202", "type_name": "麻豆传媒"},
            {"type_id": "203", "type_name": "葫芦影业"},
            {"type_id": "204", "type_name": "猫爪影像"},
            {"type_id": "205", "type_name": "天美传媒"},
            {"type_id": "206", "type_name": "果冻传媒"},
            {"type_id": "207", "type_name": "91制片厂"},
            {"type_id": "208", "type_name": "蜜桃传媒"},
            {"type_id": "209", "type_name": "精东影业"},
            {"type_id": "210", "type_name": "皇家华人"},
            {"type_id": "211", "type_name": "SWAG"},
            {"type_id": "212", "type_name": "JVID"},
            {"type_id": "213", "type_name": "逼哩逼哩"},
            {"type_id": "214", "type_name": "杏吧专区"},
            {"type_id": "215", "type_name": "兔子先生"},
            {"type_id": "216", "type_name": "PsychoPornTW"},
            {"type_id": "217", "type_name": "MINI传媒"},
            {"type_id": "218", "type_name": "微啪传媒"},
            {"type_id": "219", "type_name": "大象传媒"},
            {"type_id": "220", "type_name": "乌鸦传媒"},
            {"type_id": "221", "type_name": "乐播传媒"},
            {"type_id": "222", "type_name": "糖心VLOG"},
            {"type_id": "223", "type_name": "星空传媒"},
            {"type_id": "224", "type_name": "爱妃传媒"},
            {"type_id": "225", "type_name": "肉肉传媒"},
            {"type_id": "226", "type_name": "鲸鱼传媒"},
            {"type_id": "227", "type_name": "91传媒"},
            {"type_id": "228", "type_name": "扣扣传媒"},
            {"type_id": "229", "type_name": "开心鬼传媒"},
            {"type_id": "230", "type_name": "渡边传媒"},
            {"type_id": "231", "type_name": "换妻传媒"},
            {"type_id": "232", "type_name": "涩会传媒"},
            {"type_id": "233", "type_name": "胖子传媒"},
            {"type_id": "234", "type_name": "SA国际传媒"},
            {"type_id": "235", "type_name": "桃视频"},
            # === 日本番号 50个 ===
            {"type_id": "301", "type_name": "200GANA"},
            {"type_id": "302", "type_name": "300MIUM"},
            {"type_id": "303", "type_name": "SIRO"},
            {"type_id": "304", "type_name": "SSNI"},
            {"type_id": "305", "type_name": "259LUXU"},
            {"type_id": "306", "type_name": "261ARA"},
            {"type_id": "307", "type_name": "277DCV"},
            {"type_id": "308", "type_name": "300MAAN"},
            {"type_id": "309", "type_name": "300NTK"},
            {"type_id": "310", "type_name": "WANZ"},
            {"type_id": "311", "type_name": "328HMDN"},
            {"type_id": "312", "type_name": "332NAMA"},
            {"type_id": "313", "type_name": "336KNB"},
            {"type_id": "314", "type_name": "348NTR"},
            {"type_id": "315", "type_name": "390JAC"},
            {"type_id": "316", "type_name": "MIFD"},
            {"type_id": "317", "type_name": "428SUKE"},
            {"type_id": "318", "type_name": "DCV"},
            {"type_id": "319", "type_name": "GANA"},
            {"type_id": "320", "type_name": "IPX"},
            {"type_id": "321", "type_name": "PPT"},
            {"type_id": "322", "type_name": "SIV"},
            {"type_id": "323", "type_name": "PPB"},
            {"type_id": "324", "type_name": "MIDE"},
            {"type_id": "325", "type_name": "ULT"},
            {"type_id": "326", "type_name": "MUDR"},
            {"type_id": "327", "type_name": "RBD"},
            {"type_id": "328", "type_name": "ADN"},
            {"type_id": "329", "type_name": "AARM"},
            {"type_id": "330", "type_name": "LULU"},
            {"type_id": "331", "type_name": "MIMK"},
            {"type_id": "332", "type_name": "PPPD"},
            {"type_id": "333", "type_name": "ATID"},
            {"type_id": "334", "type_name": "STARS"},
            {"type_id": "335", "type_name": "EYAN"},
            {"type_id": "336", "type_name": "MRSS"},
            {"type_id": "337", "type_name": "NNPJ"},
            {"type_id": "338", "type_name": "MIAA"},
            {"type_id": "339", "type_name": "SSIS"},
            {"type_id": "340", "type_name": "DFDM"},
            {"type_id": "341", "type_name": "FSDSS"},
            {"type_id": "342", "type_name": "DLDSS"},
            {"type_id": "343", "type_name": "SQTE"},
            {"type_id": "344", "type_name": "EBOD"},
            {"type_id": "345", "type_name": "DVAJ"},
            {"type_id": "346", "type_name": "JUTA"},
            {"type_id": "347", "type_name": "REAL"},
            {"type_id": "348", "type_name": "XRW"},
            {"type_id": "349", "type_name": "OKSN"},
            {"type_id": "350", "type_name": "综合番号"},
            # === 探花系列 16个 ===
            {"type_id": "501", "type_name": "91沈先生"},
            {"type_id": "502", "type_name": "文轩探花"},
            {"type_id": "503", "type_name": "千人斩"},
            {"type_id": "504", "type_name": "太子探花"},
            {"type_id": "505", "type_name": "屌哥全国探花"},
            {"type_id": "506", "type_name": "鸭哥探花"},
            {"type_id": "507", "type_name": "9总全国探花"},
            {"type_id": "508", "type_name": "小天探花"},
            {"type_id": "509", "type_name": "李寻欢探花"},
            {"type_id": "510", "type_name": "小陈头星选"},
            {"type_id": "511", "type_name": "综合探花"},
            {"type_id": "512", "type_name": "主播探花"},
            {"type_id": "513", "type_name": "酒店"},
            {"type_id": "514", "type_name": "小宝寻花"},
            {"type_id": "515", "type_name": "午夜寻花"},
            {"type_id": "516", "type_name": "91系列"},
            # === 女优系列（保留） ===
            {"type_id": "sortjp", "type_name": "女优系列"},
        ]

        filters = {
            "sortjp": [
                {
                    "key": "class",
                    "name": "女优系列",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "夢乃愛華", "v": "401"},
                        {"n": "波多野结衣", "v": "402"},
                        {"n": "河北彩花", "v": "404"},
                        {"n": "桃乃木香奈", "v": "409"},
                        {"n": "相泽南", "v": "412"},
                        {"n": "Miru", "v": "414"},
                        {"n": "木下日葵", "v": "419"},
                        {"n": "明里紬", "v": "429"},
                        {"n": "鷲尾芽衣", "v": "446"},
                    ]
                }
            ]
        }

        return {
            "class": classes,
            "filters": filters
        }

    def homeVideoContent(self):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}
        html_text = self._fetch("/")
        if html_text:
            result["list"] = self._parse_video_items(html_text)
            result["total"] = len(result["list"])
        return result

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

        try:
            actual_tid = tid

            if tid == "sortjp":
                ext_dict = self._parse_extend(extend)
                sub_type = ext_dict.get("class", "") or ext_dict.get("sub_type", "")

                if sub_type:
                    actual_tid = str(sub_type)
                    print("[%s] 女优系列 -> %s" % (self.name, actual_tid))
                else:
                    actual_tid = "401"
                    print("[%s] 女优系列 -> 默认 401" % self.name)

                result["filters"] = [
                    {
                        "key": "class",
                        "name": "女优系列",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "夢乃愛華", "v": "401"},
                            {"n": "波多野结衣", "v": "402"},
                            {"n": "河北彩花", "v": "404"},
                            {"n": "桃乃木香奈", "v": "409"},
                            {"n": "相泽南", "v": "412"},
                            {"n": "Miru", "v": "414"},
                            {"n": "木下日葵", "v": "419"},
                            {"n": "明里紬", "v": "429"},
                            {"n": "鷲尾芽衣", "v": "446"},
                        ]
                    }
                ]

            pg_int = int(pg)
            if pg_int <= 1:
                url = "/vodtype/%s/" % actual_tid
            else:
                url = "/vodtype/%s-%s/" % (actual_tid, pg)

            print("[%s] 请求: %s" % (self.name, url))

            html_text = self._fetch(url)
            if not html_text:
                return result

            videos = self._parse_video_items(html_text)
            result["list"] = videos

            page_info = re.search(r'共\d+条数据,当前(\d+)/(\d+)页', html_text)
            if page_info:
                result["pagecount"] = int(page_info.group(2))
            else:
                page_links = re.findall(r'/vodtype/\d+-(\d+)/', html_text)
                if page_links:
                    result["pagecount"] = max([int(p) for p in page_links])
                else:
                    result["pagecount"] = 1

            result["total"] = len(videos)
            print("[%s] 返回 %s 个视频" % (self.name, len(videos)))

        except Exception as e:
            print("[%s] categoryContent 异常: %s" % (self.name, e))

        return result

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        result = {"list": []}

        if not vid:
            return result

        try:
            detail_url = "/voddetail/%s/" % vid
            html_text = self._fetch(detail_url)

            if not html_text:
                return result

            title = "视频 %s" % vid
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', html_text)
            if title_match:
                title = clean_text(title_match.group(1))

            pic = ""
            pic_match = re.search(r'<img[^>]*class="[^"]*detail-poster[^"]*"[^>]*src="([^"]+)"', html_text)
            if not pic_match:
                pic_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*alt="[^"]*"', html_text)
            if pic_match:
                pic = fix_url(pic_match.group(1), self.host)

            play_url = "/vodplay/%s-1-1/" % vid

            vod_data = {
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": "",
                "vod_play_from": "默认线路",
                "vod_play_url": "默认线路$%s" % play_url,
            }

            result["list"].append(vod_data)
        except Exception as e:
            print("[%s] detailContent 异常: %s" % (self.name, e))

        return result

    def playerContent(self, flag, id, vipFlags=None):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}

        try:
            if self.isVideoFormat(id):
                result["url"] = id
                result["header"] = json.dumps({
                    "Referer": self.host + "/",
                    "User-Agent": self.user_agent
                })
                return result

            if not id.startswith('http'):
                id = urljoin(self.host, id)

            print("[%s] 请求播放页: %s" % (self.name, id))

            html_text = self._fetch(id)
            if not html_text:
                result["url"] = id
                return result

            player_match = re.search(r'player_aaaa\s*=\s*(\{.*?\});', html_text, re.DOTALL)
            if player_match:
                try:
                    json_str = player_match.group(1).replace('\\/', '/')
                    player_data = json.loads(json_str)
                    play_url = player_data.get('url', '')
                    if play_url:
                        result["url"] = play_url
                        result["header"] = json.dumps({
                            "Referer": self.host + "/",
                            "User-Agent": self.user_agent
                        })
                        print("[%s] 提取到播放地址: %s" % (self.name, play_url))
                        return result
                except:
                    url_match = re.search(r'"url"\s*:\s*"([^"]+)"', player_match.group(1))
                    if url_match:
                        play_url = url_match.group(1).replace('\\/', '/')
                        if play_url:
                            result["url"] = play_url
                            result["header"] = json.dumps({
                                "Referer": self.host + "/",
                                "User-Agent": self.user_agent
                            })
                            return result

            url_match = re.search(r'"url"\s*:\s*"([^"]+)"', html_text)
            if url_match:
                play_url = url_match.group(1).replace('\\/', '/')
                if play_url:
                    result["url"] = play_url
                    result["header"] = json.dumps({
                        "Referer": self.host + "/",
                        "User-Agent": self.user_agent
                    })
                    return result

            m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html_text)
            if m3u8_match:
                result["url"] = m3u8_match.group(1)
                result["header"] = json.dumps({
                    "Referer": self.host + "/",
                    "User-Agent": self.user_agent
                })
                return result

            result["url"] = id
        except Exception as e:
            print("[%s] playerContent 异常: %s" % (self.name, e))
            result["url"] = id

        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

        if not key:
            return result

        try:
            search_url = "/vodsearch/-------------/?wd=%s" % quote(key)
            if int(pg) > 1:
                search_url += "&page=%s" % pg

            html_text = self._fetch(search_url)
            if html_text:
                videos = self._parse_video_items(html_text)
                result["list"] = videos
                result["total"] = len(videos)

                page_info = re.search(r'共\d+条数据,当前(\d+)/(\d+)页', html_text)
                if page_info:
                    result["pagecount"] = int(page_info.group(2))
                else:
                    page_links = re.findall(r'page=(\d+)', html_text)
                    if page_links:
                        result["pagecount"] = max([int(p) for p in page_links])
        except Exception as e:
            print("[%s] searchContent 异常: %s" % (self.name, e))

        return result
