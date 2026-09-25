# -*- coding: utf-8 -*-

import json
import re
import sys
from base64 import b64decode, b64encode
from requests import Session
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.host = self.gethost()
        self.headers['referer'] = f'{self.host}/'
        self.session = Session()
        self.session.headers.update(self.headers)
        self.categories_cache = None
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    def homeContent(self, filter):
        result = {}
        classes = [
            {'type_name': '最新', 'type_id': '/newest'},
            {'type_name': '最佳', 'type_id': '/best'},
            {'type_name': '4K', 'type_id': '/4k'},
            {'type_name': '类别', 'type_id': '/categories'},
            {'type_name': '频道', 'type_id': '/channels'},
            {'type_name': '明星', 'type_id': '/pornstars'},
        ]
        result['class'] = classes
        return result

    def homeVideoContent(self):
        data = self.getInitialData('/newest')
        return {'list': self.parseVideos(data, 'layoutPage.videoListProps.videoThumbProps')}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999

        tid = str(tid or '').strip()
        if not tid:
            tid = '/newest'

        # 处理二级/三级分类
        if tid.startswith('two_click_'):
            path = tid.replace('two_click_', '')
            return self.categoryDetail(path, pg)
        elif tid.startswith('one_click_'):
            catId = tid.replace('one_click_', '')
            return self.categorySub(catId)

        # 构建URL
        url = tid
        if int(pg) > 1:
            url = url + ('&' if '?' in url else '/') + str(pg)

        data = self.getInitialData(url)

        if tid == '/channels':
            vdata = self.parseChannels(data)
        elif tid == '/categories':
            vdata = self.parseCategories(data)
        elif tid == '/pornstars':
            vdata = self.parsePornstars(data)
        elif tid == '/4k':
            vdata = self.parseVideos(data, 'layoutPage.trendingVideoListProps.videoThumbProps')
        else:
            vdata = self.parseVideos(data, 'layoutPage.videoListProps.videoThumbProps')

        result['list'] = vdata
        return result

    def categoryDetail(self, path, pg):
        """处理频道二级、类别三级、明星二级"""
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999

        url = path if path.startswith('http') else path
        if int(pg) > 1:
            url = url + ('&' if '?' in url else '/') + str(pg)

        data = self.getInitialData(url)
        vdata = []

        if '/channels/' in path:
            vdata = self.parseVideos(data, 'layoutPage.videoListProps.videoThumbProps')
        elif '/categories/' in path:
            vdata = self.parseVideos(data, 'pagesCategoryComponent.trendingVideoListProps.videoThumbProps')
        elif '/pornstars/' in path:
            vdata = self.parseVideos(data, 'newestVideoSectionComponent.videoListProps.videoThumbProps')
            if not vdata:
                vdata = self.parseVideos(data, 'trendingVideoSectionComponent.videoListProps.videoThumbProps')
        else:
            # 通用：尝试多个位置
            vdata = self.parseVideos(data, 'layoutPage.videoListProps.videoThumbProps')
            if not vdata:
                vdata = self.parseVideos(data, 'layoutPage.trendingVideoListProps.videoThumbProps')
            if not vdata:
                vdata = self.parseVideos(data, 'pagesCategoryComponent.trendingVideoListProps.videoThumbProps')
            if not vdata:
                vdata = self.parseVideos(data, 'newestVideoSectionComponent.videoListProps.videoThumbProps')

        result['list'] = vdata
        return result

    def categorySub(self, catId):
        """处理类别二级分类"""
        result = {}
        result['page'] = 1
        result['pagecount'] = 1
        result['limit'] = 90
        result['total'] = 999999

        if not self.categories_cache:
            self.categories_cache = self.getInitialData('/categories')

        vdata = []
        try:
            assignable = self.categories_cache['layoutPage']['store']['popular']['assignable']
            for item in assignable:
                if str(item.get('id')) == str(catId):
                    for sub in item.get('items', []):
                        vdata.append({
                            'vod_id': f"two_click_{sub.get('url', '')}",
                            'vod_name': sub.get('name', ''),
                            'vod_pic': sub.get('thumb', ''),
                            'vod_tag': 'folder',
                            'style': {'ratio': 1.33, 'type': 'rect'}
                        })
                    break
        except Exception as e:
            print(f"categorySub error: {e}")

        result['list'] = vdata
        return result

    def detailContent(self, ids):
        url = ids[0] if isinstance(ids, list) else ids
        url = str(url).strip()
        if not url.startswith('http'):
            url = self.host + url

        html = self.fetchHtml(url)

        # 获取标题
        title = 'Xhamster'
        title_m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
        if title_m:
            title = self.decodeHtml(title_m.group(1))

        # 获取封面
        pic = ''
        pic_m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html)
        if pic_m:
            pic = pic_m.group(1)

        # 获取播放地址 - 更灵活地匹配preload link
        play_url = ''
        link_m = re.search(r'<link[^>]*rel=["\']preload["\'][^>]*href=["\']([^"\']*m3u8[^"\']*)["\']', html)
        if not link_m:
            link_m = re.search(r'href=["\']([^"\']*m3u8[^"\']*)["\']', html)
        if link_m:
            play_url = link_m.group(1)

        # 构建播放地址 - 检测可用分辨率
        play_url_str = ''
        if play_url:
            headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': f'{self.host}/',
            }
            qualities = ['2160p', '1080p', '720p', '480p', '360p', '240p']
            play_urls = []
            available_qualities = []

            for q in qualities:
                q_url = play_url.replace('_TPL_', q)
                if self.testUrl(q_url, headers):
                    play_urls.append(f"{q}$666_{q_url}")
                    available_qualities.append(q)

            if play_urls:
                play_url_str = '#'.join(play_urls)
                # 如果没有4K，在标题中添加提示
                if '2160p' not in available_qualities:
                    title = title + ' [无4K]'
            else:
                # 所有分辨率都不可用，使用默认480p
                play_url_str = f"480p$666_{play_url.replace('_TPL_', '480p')}"
        else:
            play_url_str = f"嗅探${url}"

        vod = {
            'vod_id': ids[0] if isinstance(ids, list) else ids,
            'vod_name': title,
            'vod_pic': pic,
            'vod_play_from': 'Xhamster',
            'vod_play_url': play_url_str
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f'/search/{key}?page={pg}'
        data = self.getInitialData(url)
        vdata = self.parseVideos(data, 'layoutPage.videoListProps.videoThumbProps')
        return {'list': vdata, 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        p, url = 1, id
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'origin': self.host,
            'referer': f'{self.host}/',
        }
        if id.startswith("666_"):
            p, url = 0, id[4:]
        return {'parse': p, 'url': url, 'header': headers}

    def testUrl(self, url, headers):
        """测试URL是否可访问"""
        try:
            resp = self.session.head(url, headers=headers, timeout=5, allow_redirects=True)
            return resp.status_code == 200
        except:
            try:
                resp = self.session.get(url, headers=headers, timeout=5, stream=True)
                return resp.status_code == 200
            except:
                return False

    def localProxy(self, param):
        pass

    def gethost(self):
        try:
            response = self.fetch('https://zh.xhamster1.desi/', headers=self.headers, allow_redirects=False)
            return response.headers.get('Location', 'https://zh.xhamster1.desi/')
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://zh.xhamster1.desi/"

    # ========== 工具方法 ==========

    def getInitialData(self, path=''):
        """获取页面并解析initials JSON数据"""
        h = '' if path.startswith('http') else self.host
        url = f'{h}{path}'
        response = self.session.get(url)
        html = response.text

        # 解析initials JSON
        m = re.search(r'initials=({[\s\S]*?});</script>', html)
        if not m:
            m = re.search(r'initials=({[\s\S]*?});', html)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
        return {}

    def fetchHtml(self, url):
        """获取页面HTML"""
        response = self.session.get(url)
        return response.text

    def parseVideos(self, data, path):
        """从指定路径解析视频列表"""
        vlist = []
        if not data:
            return vlist

        try:
            keys = path.split('.')
            obj = data
            for k in keys:
                if obj is None:
                    return vlist
                obj = obj.get(k)

            if obj and isinstance(obj, list):
                for v in obj:
                    vlist.append({
                        'vod_id': v.get('pageURL', ''),
                        'vod_name': v.get('title', 'Video'),
                        'vod_pic': v.get('thumbURL') or v.get('imageURL', ''),
                        'vod_remarks': self.formatDuration(v.get('duration')),
                        'vod_year': str(v.get('views', '')) if v.get('views') else '',
                        'style': {'ratio': 1.33, 'type': 'rect'}
                    })
        except Exception as e:
            print(f"parseVideos error: {e}")

        return vlist

    def parseChannels(self, data):
        """解析频道列表"""
        vlist = []
        if not data or 'channels' not in data:
            return vlist

        for ch in data['channels']:
            vlist.append({
                'vod_id': f"two_click_{ch.get('channelURL', '')}",
                'vod_name': ch.get('channelName', ''),
                'vod_pic': ch.get('siteLogoURL') or ch.get('thumbURL', ''),
                'vod_remarks': f"videos:{ch.get('videoCount', 0)}",
                'vod_tag': 'folder',
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    def parseCategories(self, data):
        """解析类别列表"""
        vlist = []
        if not data or 'layoutPage' not in data:
            return vlist

        try:
            assignable = data['layoutPage']['store']['popular']['assignable']
            for item in assignable:
                vlist.append({
                    'vod_id': f"one_click_{item.get('id')}",
                    'vod_name': item.get('name', ''),
                    'vod_pic': '',
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
            self.categories_cache = data
        except Exception as e:
            print(f"parseCategories error: {e}")

        return vlist

    def parsePornstars(self, data):
        """解析明星列表"""
        vlist = []
        if not data or 'layoutPage' not in data:
            return vlist

        try:
            stars = data['layoutPage']['pornstarListProps']['pornstars']
            for star in stars:
                vlist.append({
                    'vod_id': f"two_click_{star.get('pageURL', '')}",
                    'vod_name': star.get('name', ''),
                    'vod_pic': star.get('imageThumbUrl') or star.get('logoThumbUrl', ''),
                    'vod_remarks': star.get('translatedCountryName', ''),
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        except Exception as e:
            print(f"parsePornstars error: {e}")

        return vlist

    def formatDuration(self, seconds):
        """格式化时长"""
        if not seconds:
            return ''
        m = seconds // 60
        s = seconds % 60
        return f"{m}:{s:02d}"

    def decodeHtml(self, s):
        """解码HTML实体"""
        return (s or '').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
