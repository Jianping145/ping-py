#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色爱阁 (seaige9.fit) 爬虫 - 最终修复版
兼容: peekpro / 蜂蜜影视 / TVBox 全系
核心: player_data → m3u8直链，直接播放
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
    host = 'https://www.seaige9.fit'
    session = requests.Session()
    _debug = True

    def _log(self, msg):
        if self._debug:
            print('[seige] ' + str(msg))

    def getName(self):
        return '色爱阁'

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

    def _extract_player_data(self, html):
        if not html:
            return None
        match = re.search(r'var\s+player_data\s*=\s*(\{[^}]+\})', html, re.DOTALL)
        if match:
            try:
                json_str = match.group(1)
                json_str = json_str.replace('\\/', '/')
                data = json.loads(json_str)
                return data
            except Exception as e:
                self._log('player_data 解析失败: ' + str(e))
        return None

    def _extract_videos_from_html(self, html):
        videos = []
        cards = re.findall(r'<div class="video-card">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
        for card in cards:
            play_match = re.search(r'href="(/cn/home/web/index\.php/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"', card)
            if not play_match:
                continue
            play_url, vid, sid, nid = play_match.groups()
            img_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', card)
            pic = img_match.group(1) if img_match else ''
            alt = img_match.group(2) if img_match else ''
            title_match = re.search(r'<div class="video-title">(.*?)</div>', card, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            else:
                title = alt or '视频' + vid
            videos.append({
                'vod_id': vid + '_' + sid + '_' + nid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': ''
            })
        if not videos:
            links = re.findall(r'href="(/cn/home/web/index\.php/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"', html)
            for play_url, vid, sid, nid in links:
                videos.append({
                    'vod_id': vid + '_' + sid + '_' + nid,
                    'vod_name': '视频' + vid,
                    'vod_pic': '',
                    'vod_remarks': ''
                })
        return videos

    def init(self, extend=''):
        self.session.headers.update(self._get_headers())
        self._log('初始化完成')

    def homeContent(self, filter=False):
        try:
            cats = [
                {'type_id': '20', 'type_name': '亚洲情色'},
                {'type_id': '21', 'type_name': '制服师生'},
                {'type_id': '22', 'type_name': '卡通动漫'},
                {'type_id': '23', 'type_name': '三级伦理'},
                {'type_id': '24', 'type_name': '强奸乱伦'},
                {'type_id': '25', 'type_name': '偷拍自拍'},
                {'type_id': '26', 'type_name': '中文字幕'},
                {'type_id': '27', 'type_name': '欧美性爱'},
                {'type_id': '28', 'type_name': '人妻熟女'},
                {'type_id': '29', 'type_name': '无码专区'},
            ]
            html = self._fetch(self.host + '/cn/home/web/index.php/vod/search/by/time_add.html')
            items = self._extract_videos_from_html(html)[:20] if html else []
            self._log('homeContent: 分类 ' + str(len(cats)) + ', 视频 ' + str(len(items)))
            return {'class': cats, 'list': items}
        except Exception as e:
            self._log('homeContent 异常: ' + str(e))
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        html = self._fetch(self.host + '/cn/home/web/index.php/vod/search/by/time_add.html')
        items = self._extract_videos_from_html(html)[:20] if html else []
        return {'list': items}

    def categoryContent(self, tid, pg, filter=False, extend=''):
        try:
            page = int(pg) if pg else 1
            tid = str(tid or '').strip()
            if page == 1:
                url = self.host + '/cn/home/web/index.php/vod/type/id/' + tid + '.html'
            else:
                url = self.host + '/cn/home/web/index.php/vod/type/id/' + tid + '/page/' + str(page) + '.html'
            self._log('请求分类页: ' + url)
            html = self._fetch(url)
            if not html:
                return {'list': [], 'page': page, 'pagecount': 1}
            items = self._extract_videos_from_html(html)
            has_next = '/page/' + str(page + 1) + '.html' in html
            self._log('分类页解析到 ' + str(len(items)) + ' 个视频')
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
            self._log('详情页: ' + vod_id)

            # 解析 vod_id: {vid}_{sid}_{nid}
            parts = vod_id.split('_')
            if len(parts) >= 3:
                video_id = parts[0]
                sid = parts[1]
                nid = parts[2]
            else:
                video_id = vod_id
                sid = '1'
                nid = '1'

            self._log('解析: video_id=' + video_id + ', sid=' + sid + ', nid=' + nid)

            url = self.host + '/cn/home/web/index.php/vod/play/id/' + video_id + '/sid/' + sid + '/nid/' + nid + '.html'
            self._log('请求播放页: ' + url)

            html = self._fetch(url)
            if not html:
                self._log('播放页获取失败')
                return {'list': []}

            player_data = self._extract_player_data(html)

            title = '视频' + video_id
            pic = ''
            m3u8_url = ''

            if player_data:
                m3u8_url = player_data.get('url', '')
                title = player_data.get('title', title)
                self._log('player_data: url=' + (m3u8_url[:60] if m3u8_url else 'empty') + '...')

            if not m3u8_url:
                m3u8_match = re.search(r"(https?://[^\"'<>\s]+\.m3u8[^\"'<>\s]*)", html)
                if m3u8_match:
                    m3u8_url = m3u8_match.group(1)
                    self._log('从HTML找到m3u8: ' + m3u8_url[:60] + '...')

            og_image = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
            if og_image:
                pic = og_image.group(1)

            self._log('详情: ' + title + ', m3u8: ' + (m3u8_url[:60] if m3u8_url else '未找到') + '...')

            # 关键：直接返回 m3u8 直链，不走代理
            return {'list': [{
                'vod_id': vod_id,
                'vod_name': str(title),
                'vod_pic': str(pic),
                'vod_play_from': '直链',
                'vod_play_url': '第1集$' + m3u8_url
            }]}
        except Exception as e:
            self._log('detailContent 异常: ' + str(e))
            return {'list': []}

    def playerContent(self, flag, id, vipFlags=None):
        play_id = str(id or '')
        self._log('playerContent: ' + play_id[:60] + '...')

        # 关键：直接返回原始 URL，不做任何包装
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
            urls_to_try = [
                self.host + '/cn/home/web/index.php/vod/search/wd/' + keyword + '.html',
                self.host + '/cn/home/web/index.php/vod/search.html?wd=' + keyword,
            ]
            items = []
            for url in urls_to_try:
                self._log('尝试搜索: ' + url)
                html = self._fetch(url)
                if html:
                    items = self._extract_videos_from_html(html)
                    if items:
                        break
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
