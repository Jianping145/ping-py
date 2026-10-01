#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
91lol.im 好色TV 爬虫 - 蜂蜜影视兼容版
"""

import sys
import re
import json
import requests
import urllib3
import time
import random
from urllib.parse import quote

urllib3.disable_warnings()
sys.path.append('..')
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    host = 'https://91lol.im'
    session = requests.Session()
    _debug = True

    def _log(self, msg):
        if self._debug:
            print('[91lol] ' + str(msg))

    def getName(self):
        return '好色TV'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return '.m3u8' in u or '.mp4' in u or '.ts' in u

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return [200, 'application/json', json.dumps({'code': 0})]

    def _get_headers(self, referer=None):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer or self.host + '/'
        }

    def _fetch(self, url, referer=None, retries=3):
        for attempt in range(retries):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(0.5, 1.5))
                r = self.session.get(url, headers=self._get_headers(referer), timeout=30, verify=False)
                r.encoding = 'utf-8'
                if r.status_code == 200:
                    return r.text
                elif r.status_code in [403, 429, 503]:
                    self._log('被拦截 [' + str(r.status_code) + '] 重试 ' + str(attempt+1))
                    continue
                else:
                    return ''
            except Exception as e:
                self._log('异常 ' + str(e) + ' 重试 ' + str(attempt+1))
        return ''

    def _extract_videos_from_html(self, html):
        videos = []

        # 匹配视频卡片
        pattern = (
            '<div class="thumbnail">\s*'
            '<a[^>]*href="video-(\d+)\.htm"[^>]*>\s*'
            '<div class="image"[^>]*style="background-image: url\(([^)]+)\)"[^>]*title="([^"]*)"[^>]*>'
            '(.*?)'
            '</div>\s*</a>\s*'
            '<div class="caption title">\s*<h5><a[^>]*>([^<]+)</a></h5>'
        )

        matches = re.findall(pattern, html, re.DOTALL)

        for match in matches:
            vid, pic, title_attr, overlay, title = match
            pic = pic.strip("'\"")

            # 提取时长
            duration_match = re.search(r'<var class="duration">\s*([^<]+)</var>', overlay)
            duration = duration_match.group(1).strip() if duration_match else ''

            # 检查HD标记
            is_hd = 'hd-thumbnail' in overlay

            remark = duration
            if is_hd:
                remark = 'HD ' + remark if remark else 'HD'

            videos.append({
                'vod_id': str(vid),
                'vod_name': title.strip(),
                'vod_pic': pic,
                'vod_remarks': remark
            })

        # 备用模式
        if not videos:
            pattern2 = 'href="video-(\d+)\.htm"[^>]*>\s*<div class="image"[^>]*style="background-image: url\(([^)]+)\)"'
            matches2 = re.findall(pattern2, html)
            for vid, pic in matches2:
                pic = pic.strip("'\"")
                videos.append({
                    'vod_id': str(vid),
                    'vod_name': '视频' + vid,
                    'vod_pic': pic,
                    'vod_remarks': ''
                })

        return videos

    def _extract_play_url(self, html):
        if not html:
            return ''

        # 方法1: source 标签
        source_match = re.search(r'<source[^>]+src="([^"]+)"', html)
        if source_match:
            return source_match.group(1)

        # 方法2: video 标签
        video_match = re.search(r'<video[^>]+src="([^"]+)"', html)
        if video_match:
            return video_match.group(1)

        # 方法3: JS 变量
        js_patterns = [
            r'var\s+videoUrl\s*=\s*["\']([^"\']+)["\']',
            r'var\s+video_url\s*=\s*["\']([^"\']+)["\']',
            r'var\s+src\s*=\s*["\']([^"\']+)["\']',
        ]
        for pattern in js_patterns:
            match = re.search(pattern, html)
            if match:
                url = match.group(1)
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = self.host + url
                return url

        # 方法4: m3u8/mp4 直链
        video_match = re.search(r'(https?://[^"\'<>\s]+\.(?:m3u8|mp4|ts)(?:\?[^"\'<>\s]*)?)', html)
        if video_match:
            return video_match.group(1)

        return ''

    def init(self, extend=''):
        self.session.headers.update(self._get_headers())
        self._log('初始化完成')

    def homeContent(self, filter=False):
        try:
            cats = [
                {'type_id': 'list', 'type_name': '最新'},
                {'type_id': 'top7_list', 'type_name': '周榜'},
                {'type_id': 'top_list', 'type_name': '月榜'},
                {'type_id': '5min_list', 'type_name': '5分钟+'},
                {'type_id': 'long_list', 'type_name': '10分钟+'},
            ]
            html = self._fetch(self.host + '/list-1.htm')
            items = self._extract_videos_from_html(html)[:20] if html else []
            return {'class': cats, 'list': items}
        except Exception as e:
            self._log('homeContent 异常: ' + str(e))
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        html = self._fetch(self.host + '/list-1.htm')
        items = self._extract_videos_from_html(html)[:20] if html else []
        return {'list': items}

    def categoryContent(self, tid, pg, filter=False, extend=''):
        try:
            page = int(pg) if pg else 1
            tid = str(tid or 'list').strip()
            url = self.host + '/' + tid + '-' + str(page) + '.htm'
            self._log('请求分类页: ' + url)
            html = self._fetch(url)
            if not html:
                return {'list': [], 'page': page, 'pagecount': 1}
            items = self._extract_videos_from_html(html)
            has_next = (tid + '-' + str(page + 1) + '.htm') in html
            return {
                'list': items,
                'page': page,
                'pagecount': 999 if has_next or len(items) >= 10 else page,
                'limit': len(items),
                'total': 9999
            }
        except Exception as e:
            self._log('categoryContent 异常: ' + str(e))
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}

    def detailContent(self, ids):
        try:
            vod_id = str(ids[0] if isinstance(ids, list) else ids)
            url = self.host + '/video-' + vod_id + '.htm'
            self._log('请求详情页: ' + url)
            html = self._fetch(url)
            if not html:
                return {'list': []}

            # 提取标题
            title = '视频' + vod_id
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title_tag = re.search(r'<title>([^<]+)</title>', html)
                if title_tag:
                    title = title_tag.group(1).strip()
                    title = re.sub(r'[-_].*好色.*$', '', title).strip()

            # 提取封面
            pic = ''
            og_image = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
            if og_image:
                pic = og_image.group(1)

            # 提取播放地址
            play_url = self._extract_play_url(html)

            self._log('详情: ' + title + ', 播放: ' + (play_url[:60] if play_url else '未找到') + '...')

            return {'list': [{
                'vod_id': vod_id,
                'vod_name': str(title),
                'vod_pic': str(pic),
                'vod_play_from': '直链',
                'vod_play_url': '第1集$' + play_url
            }]}
        except Exception as e:
            self._log('detailContent 异常: ' + str(e))
            return {'list': []}

    def playerContent(self, flag, id, vipFlags=None):
        play_id = str(id or '')
        return {
            'parse': 0,
            'url': play_id,
            'header': {
                'Referer': self.host + '/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
            }
        }

    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if pg else 1
            keyword = quote(str(key))
            url = self.host + '/search.htm?search=' + keyword
            self._log('尝试搜索: ' + url)
            html = self._fetch(url)
            items = self._extract_videos_from_html(html) if html else []
            return {
                'list': items,
                'page': page,
                'pagecount': 999,
                'limit': len(items),
                'total': 9999
            }
        except Exception as e:
            self._log('searchContent 异常: ' + str(e))
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}
