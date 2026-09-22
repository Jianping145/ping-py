#coding=utf-8
# -*- coding: utf-8 -*-
# 蜂蜜影视 / FongMi Python 源 - Pornhub
# 配置示例:
# {
#   "key": "py_pornhub",
#   "name": "Pornhub",
#   "type": 3,
#   "api": "py_pornhub",
#   "searchable": 1,
#   "quickSearch": 1,
#   "filterable": 0,
#   "ext": "https://你的地址/py_pornhub.py"
# }
# 或本地: "ext": "file:///storage/emulated/0/xxx/py_pornhub.py"

import re
import json
import sys

try:
    from base.spider import Spider
except Exception:
    class Spider(object):
        def init(self, extend=""):
            pass

        def fetch(self, url, headers=None, timeout=15):
            import requests
            return requests.get(url, headers=headers or {}, timeout=timeout, verify=False)

        def log(self, msg):
            print(msg)


class Spider(Spider):
    def init(self, extend=""):
        self.host = 'https://cn.pornhub.com'
        self.api = 'https://www.pornhub.com/webmasters'
        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        self.api_headers = {
            'User-Agent': self.ua,
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.pornhub.com/',
        }
        self.page_headers = {
            'User-Agent': self.ua,
            'Cookie': 'age_verified=1; accessAgeDisclaimerPH=1; accessPH=1; platform=pc',
            'Referer': self.host + '/',
        }
        # type_id: o:排序 | cat:分类名 | path:路径 | q:搜索词
        self.tabs = [
            {'type_id': 'o:featured', 'type_name': '精选'},
            {'type_id': 'o:newest', 'type_name': '最新'},
            {'type_id': 'o:mostviewed', 'type_name': '最多观看'},
            {'type_id': 'o:rating', 'type_name': '最高评分'},
            {'type_id': 'path:/categories/teen', 'type_name': 'Teen'},
            {'type_id': 'path:/hd', 'type_name': 'HD'},
            {'type_id': 'cat:college-18', 'type_name': 'College'},
            {'type_id': 'cat:pornstar', 'type_name': 'Pornstar'},
            {'type_id': 'cat:babe', 'type_name': 'Babe'},
            {'type_id': 'cat:hentai', 'type_name': 'Hentai'},
            {'type_id': 'cat:sfw', 'type_name': 'SFW'},
            {'type_id': 'cat:popular-with-women', 'type_name': '女生爱看'},
            {'type_id': 'cat:transgender', 'type_name': 'Transgender'},
            {'type_id': 'q:深喉', 'type_name': '深喉'},
            {'type_id': 'q:ai生成', 'type_name': 'AI生成'},
            {'type_id': 'cat:60fps-1', 'type_name': '60FPS'},
            {'type_id': 'cat:threesome', 'type_name': '3P'},
            {'type_id': 'cat:orgy', 'type_name': '群交'},
            {'type_id': 'cat:asian', 'type_name': '亚洲'},
            {'type_id': 'cat:japanese', 'type_name': '日本'},
            {'type_id': 'cat:cosplay', 'type_name': 'Cosplay'},
            {'type_id': 'cat:russian', 'type_name': '俄罗斯'},
            {'type_id': 'cat:creampie', 'type_name': '内射'},
            {'type_id': 'cat:public', 'type_name': '公开'},
            {'type_id': 'cat:hardcore', 'type_name': '重口'},
            {'type_id': 'cat:indian', 'type_name': '印度'},
            {'type_id': 'cat:bisexual-male', 'type_name': '双性恋男'},
            {'type_id': 'cat:casting', 'type_name': '选角'},
            {'type_id': 'cat:gaming', 'type_name': '游戏'},
            {'type_id': 'cat:double-penetration', 'type_name': '双插'},
            {'type_id': 'cat:blowjob', 'type_name': '口交'},
            {'type_id': 'cat:behind-the-scenes', 'type_name': '花絮'},
            {'type_id': 'cat:compilation', 'type_name': '合集'},
            {'type_id': 'cat:lesbian', 'type_name': '女同'},
            {'type_id': 'cat:solo-female', 'type_name': '女独'},
            {'type_id': 'cat:female-orgasm', 'type_name': '高潮'},
            {'type_id': 'cat:cuckold', 'type_name': '绿帽'},
            {'type_id': 'cat:cumshot', 'type_name': '颜射'},
            {'type_id': 'cat:big-tits', 'type_name': '巨乳'},
            {'type_id': 'cat:big-dick', 'type_name': '大鸡吧'},
            {'type_id': 'cat:verified-couples', 'type_name': '认证情侣'},
            {'type_id': 'cat:verified-models', 'type_name': '认证模特'},
            {'type_id': 'cat:verified-amateurs', 'type_name': '认证素人'},
            {'type_id': 'cat:brazilian', 'type_name': '巴西'},
            {'type_id': 'cat:german', 'type_name': '德国'},
            {'type_id': 'cat:toys', 'type_name': '玩具'},
            {'type_id': 'cat:fetish', 'type_name': '恋物'},
            {'type_id': 'cat:italian', 'type_name': '意大利'},
            {'type_id': 'cat:handjob', 'type_name': '手交'},
            {'type_id': 'cat:masturbation', 'type_name': '自慰'},
            {'type_id': 'cat:latina', 'type_name': '拉丁'},
            {'type_id': 'cat:fisting', 'type_name': '拳交'},
            {'type_id': 'cat:bondage', 'type_name': '束缚'},
            {'type_id': 'cat:czech', 'type_name': '捷克'},
            {'type_id': 'cat:school-18', 'type_name': '学校'},
            {'type_id': 'cat:euro', 'type_name': '欧洲'},
            {'type_id': 'cat:french', 'type_name': '法国'},
            {'type_id': 'cat:romantic', 'type_name': '浪漫'},
            {'type_id': 'cat:brunette', 'type_name': '黑发'},
            {'type_id': 'cat:parody', 'type_name': '恶搞'},
            {'type_id': 'cat:squirt', 'type_name': '潮吹'},
            {'type_id': 'cat:babysitter-18', 'type_name': '保姆'},
            {'type_id': 'cat:anal', 'type_name': '肛交'},
            {'type_id': 'cat:exclusive', 'type_name': '独家'},
            {'type_id': 'cat:reality', 'type_name': '真实'},
            {'type_id': 'cat:pov', 'type_name': 'POV'},
            {'type_id': 'cat:rough-sex', 'type_name': '粗暴'},
            {'type_id': 'cat:amateur', 'type_name': '业余'},
            {'type_id': 'cat:red-head', 'type_name': '红发'},
            {'type_id': 'cat:tattooed-women', 'type_name': '纹身女'},
            {'type_id': 'cat:step-fantasy', 'type_name': '继亲幻想'},
            {'type_id': 'cat:old-young-18', 'type_name': '老少'},
            {'type_id': 'cat:muscular-men', 'type_name': '肌肉男'},
            {'type_id': 'cat:big-ass', 'type_name': '大屁股'},
            {'type_id': 'cat:pussy-licking', 'type_name': '舔阴'},
            {'type_id': 'cat:british', 'type_name': '英国'},
            {'type_id': 'cat:webcam', 'type_name': 'Webcam'},
            {'type_id': 'cat:role-play', 'type_name': '角色扮演'},
            {'type_id': 'cat:small-tits', 'type_name': '贫乳'},
            {'type_id': 'cat:interracial', 'type_name': '跨种族'},
            {'type_id': 'cat:gangbang', 'type_name': '轮奸'},
            {'type_id': 'cat:milf', 'type_name': '熟女'},
            {'type_id': 'cat:blonde', 'type_name': '金发'},
            {'type_id': 'cat:arab', 'type_name': '阿拉伯'},
            {'type_id': 'cat:bukkake', 'type_name': 'Bukkake'},
            {'type_id': 'cat:korean', 'type_name': '韩国'},
            {'type_id': 'cat:ebony', 'type_name': '黑人女'},
            {'type_id': 'cat:music', 'type_name': '音乐'},
            {'type_id': 'cat:vintage', 'type_name': '复古'},
            {'type_id': 'cat:deepthroat', 'type_name': '深喉分类'},
            {'type_id': 'cat:ai', 'type_name': 'AI分类'},
        ]

    def getName(self):
        return 'Pornhub'

    def getDependence(self):
        return []

    def homeContent(self, filter):
        return {'class': self.tabs}

    def homeVideoContent(self):
        return self.categoryContent('o:featured', '1', False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            tid = str(tid or 'o:featured').strip()
            if not tid or tid in ('undefined', 'null'):
                tid = 'o:featured'

            if tid.startswith('path:'):
                path = tid[5:]
                if not path.startswith('/'):
                    path = '/' + path
                url = self.host + path
                if page > 1:
                    url += ('&' if '?' in url else '?') + 'page=' + str(page)
                videos = self._list_from_html(url)
            elif tid.startswith('c:') or tid.isdigit():
                cid = tid[2:] if tid.startswith('c:') else tid
                url = self.host + '/video?c=' + cid
                if page > 1:
                    url += '&page=' + str(page)
                videos = self._list_from_html(url)
            else:
                url = self._api_url(tid, page)
                videos = self._list_from_api(url)

            return {
                'list': videos,
                'page': page,
                'pagecount': page + 1 if len(videos) >= 20 else page,
                'limit': 30,
                'total': page * 30 + 1 if videos else 0,
            }
        except Exception as e:
            self.log('[PH] category error: ' + str(e))
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 30, 'total': 0}

    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            vid = re.sub(r'^.*viewkey=', '', str(vid), flags=re.I)
            vid = re.sub(r'[^a-z0-9]', '', vid, flags=re.I)
            title = 'Pornhub'
            pic = ''

            try:
                r = self.fetch(self.api + '/video_by_id?id=' + vid, headers=self.api_headers, timeout=15)
                data = r.json() if hasattr(r, 'json') else json.loads(r.text)
                video = data.get('video') or data or {}
                if video.get('title'):
                    title = video['title']
                pic = video.get('thumb') or video.get('default_thumb') or ''
            except Exception as e:
                self.log('[PH] video_by_id fail: ' + str(e))

            page_url = self.host + '/view_video.php?viewkey=' + vid
            r = self.fetch(page_url, headers=self.page_headers, timeout=20)
            html = r.text if hasattr(r, 'text') else str(r.content)
            play_parts = []
            m = re.search(r'var\s+flashvars_\d+\s*=\s*(\{[\s\S]*?\});', html)
            if m:
                flash = json.loads(m.group(1))
                if flash.get('video_title'):
                    title = flash['video_title']
                if flash.get('image_url'):
                    pic = flash['image_url']
                defs = flash.get('mediaDefinitions') or []
                hls = [d for d in defs if d.get('format') == 'hls' and d.get('videoUrl')]
                hls.sort(key=lambda x: int(x.get('quality') or 0), reverse=True)
                for d in hls:
                    play_parts.append(str(d.get('quality')) + 'p$' + d['videoUrl'])
            if not play_parts:
                play_parts.append('网页$' + page_url)

            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '',
                'vod_content': '',
                'vod_play_from': 'Pornhub',
                'vod_play_url': '#'.join(play_parts),
            }
            return {'list': [vod]}
        except Exception as e:
            self.log('[PH] detail error: ' + str(e))
            return {'list': []}

    def searchContent(self, key, quick, pg='1'):
        try:
            if not key:
                return {'list': []}
            page = int(pg) if str(pg).isdigit() else 1
            from urllib.parse import quote
            url = self.api + '/search?search=' + quote(key) + '&page=' + str(page) + '&thumbsize=large'
            videos = self._list_from_api(url)
            return {'list': videos}
        except Exception as e:
            self.log('[PH] search error: ' + str(e))
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            if 'view_video.php' in str(id):
                return {'parse': 1, 'url': id, 'header': ''}
            header = {
                'User-Agent': self.ua,
                'Referer': self.host + '/',
                'Origin': self.host,
            }
            return {
                'parse': 0,
                'url': id,
                'header': json.dumps(header),
            }
        except Exception as e:
            self.log('[PH] play error: ' + str(e))
            return {'parse': 0, 'url': ''}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def destroy(self):
        pass

    # ---------- 内部方法 ----------

    def _api_url(self, tid, page):
        from urllib.parse import quote
        if tid.startswith('o:'):
            ordering = tid[2:]
            return self.api + '/search?ordering=' + quote(ordering) + '&page=' + str(page) + '&thumbsize=large'
        if tid.startswith('q:'):
            kw = tid[2:]
            return self.api + '/search?search=' + quote(kw) + '&page=' + str(page) + '&thumbsize=large'
        if tid.startswith('cat:'):
            cat = tid[4:]
            return self.api + '/search?category=' + quote(cat) + '&page=' + str(page) + '&thumbsize=large'
        # 兼容旧 id
        mapping = {
            'featured': 'featured', 'sy': 'featured', 'home': 'featured',
            'cm': 'newest', 'newest': 'newest',
            'mv': 'mostviewed', 'mostviewed': 'mostviewed',
            'tr': 'rating', 'ht': 'rating', 'rating': 'rating',
        }
        ordering = mapping.get(tid, tid)
        return self.api + '/search?ordering=' + quote(ordering) + '&page=' + str(page) + '&thumbsize=large'

    def _list_from_api(self, url):
        self.log('[PH] api url=' + url)
        r = self.fetch(url, headers=self.api_headers, timeout=15)
        try:
            data = r.json() if hasattr(r, 'json') else json.loads(r.text)
        except Exception:
            text = r.text if hasattr(r, 'text') else ''
            self.log('[PH] json fail: ' + text[:100])
            return []
        videos = data.get('videos') if isinstance(data, dict) else data
        if not isinstance(videos, list):
            videos = []
        return self._videos_to_list(videos)

    def _list_from_html(self, url):
        self.log('[PH] html url=' + url)
        r = self.fetch(url, headers=self.page_headers, timeout=20)
        html = r.text if hasattr(r, 'text') else str(r.content)
        return self._parse_html_list(html)

    def _videos_to_list(self, videos):
        result = []
        for v in videos:
            vid = ''
            if v.get('video_id'):
                vid = str(v['video_id'])
            elif v.get('vkey'):
                vid = str(v['vkey'])
            elif v.get('url'):
                m = re.search(r'viewkey=([a-z0-9]+)', str(v['url']), re.I)
                if m:
                    vid = m.group(1)
            if not vid:
                continue
            parts = []
            if v.get('duration'):
                parts.append(str(v['duration']))
            if v.get('views'):
                parts.append(str(v['views']))
            if v.get('rating'):
                parts.append(str(v['rating']))
            result.append({
                'vod_id': vid,
                'vod_name': v.get('title') or 'Video',
                'vod_pic': v.get('thumb') or v.get('default_thumb') or '',
                'vod_remarks': ' · '.join(parts),
            })
        self.log('[PH] list=' + str(len(result)))
        return result

    def _parse_html_list(self, html):
        result = []
        if not html:
            return result
        blocks = re.split(r'<li[^>]*class="[^"]*(?:videoBox|pcVideoListItem)[^"]*"', html, flags=re.I)
        for block in blocks[1:]:
            end = block.find('</li>')
            if 0 < end < 10000:
                block = block[:end]
            href_m = re.search(r'href="(/view_video\.php\?viewkey=[a-z0-9]+)"', block, re.I)
            if not href_m:
                continue
            href = href_m.group(1)
            id_m = re.search(r'viewkey=([a-z0-9]+)', href, re.I)
            vid = id_m.group(1) if id_m else href
            title_m = re.search(r'title="([^"]{2,})"', block, re.I)
            title = self._decode_html(title_m.group(1)) if title_m else 'Video'
            cover = ''
            img_m = (
                re.search(r'data-mediumthumb="(https?://[^"]+)"', block, re.I)
                or re.search(r'data-image="(https?://[^"]+)"', block, re.I)
                or re.search(r'src="(https?://[^"]*(?:phncdn|pix-)[^"]*)"', block, re.I)
            )
            if img_m:
                cover = img_m.group(1)
            result.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': cover,
                'vod_remarks': '',
            })
        self.log('[PH] html list=' + str(len(result)))
        return result

    def _decode_html(self, s):
        s = str(s or '')
        s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        s = s.replace('&quot;', '"').replace('&#39;', "'")
        return s
