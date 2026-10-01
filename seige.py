#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色爱阁 (seaige9.fit) 爬虫 - 参考 rouvideos 架构
核心: player_data JSON → m3u8直链，无需 PNG 解包
"""

import sys
import re
import json
import base64
import requests
import urllib3
import time
import random
from urllib.parse import quote, urljoin, unquote

urllib3.disable_warnings()
sys.path.append('..')
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    host = 'https://www.seaige9.fit'
    session = requests.Session()
    _debug = True
    _categories = []

    def _log(self, msg):
        if self._debug:
            print(f'[seige] {msg}')

    def _get_proxy_base(self):
        """获取壳提供的本地代理入口"""
        try:
            if hasattr(self, 'getProxyUrl') and callable(self.getProxyUrl):
                base = self.getProxyUrl()
                if base:
                    return str(base).rstrip('&?')
        except Exception as e:
            self._log(f'getProxyUrl 失败: {e}')
        for attr in ('t4_api', 'localProxyUrl'):
            v = getattr(self, attr, None)
            if v:
                return str(v).rstrip('&?')
        return 'http://127.0.0.1:9978/proxy?do=py'

    def _make_proxy_url(self, typ, real_url):
        """构造走 localProxy 的播放地址"""
        proxy_base = self._get_proxy_base()
        token = base64.urlsafe_b64encode(str(real_url).encode()).decode().rstrip('=')
        sep = '&' if '?' in proxy_base else '?'
        return f'{proxy_base}{sep}type={quote(str(typ), safe="")}&url={quote(token, safe="")}'

    def getName(self):
        return '色爱阁'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return '.m3u8' in u or '.mp4' in u or '.ts' in u or 'type=media' in u or 'do=py' in u

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        """本地代理 - 色爱阁无需 PNG 解包，直接转发 m3u8"""
        try:
            if isinstance(param, str):
                raw = param
                typ = 'media'
            else:
                raw = param.get('url') or param.get('u') or ''
                typ = param.get('type') or 'media'
            if not raw:
                return [400, 'text/plain', '']
            raw = unquote(str(raw))

            # 解码 base64
            if not raw.startswith('http'):
                try:
                    pad = '=' * (-len(raw) % 4)
                    decoded = base64.urlsafe_b64decode(raw + pad).decode('utf-8', errors='replace')
                    if decoded.startswith('http'):
                        raw = decoded
                except Exception:
                    pass

            r = self.session.get(raw, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                'Referer': self.host + '/',
            }, timeout=30, verify=False)

            if r.status_code != 200:
                return [r.status_code, 'text/plain', '']

            body = r.content
            content = body.decode('utf-8', errors='replace')

            # m3u8: 重写分片 URL 走代理
            if '#EXTM3U' in content or '#EXT-X-' in content:
                base = raw.rsplit('/', 1)[0] + '/'

                def proxy_url(u):
                    u = u.strip()
                    if not u or u.startswith('#'):
                        return u
                    absu = urljoin(base, u)
                    return self._make_proxy_url('media', absu)

                lines = []
                for line in content.splitlines():
                    s = line.strip()
                    if s and not s.startswith('#'):
                        lines.append(proxy_url(s))
                    elif 'URI="' in line:
                        line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + proxy_url(m.group(1)) + '"', line)
                        lines.append(line)
                    else:
                        lines.append(line)
                content = '\n'.join(lines) + '\n'
                return [200, 'application/vnd.apple.mpegurl', content]

            # 媒体分片: 直接返回
            ctype = r.headers.get('Content-Type', 'application/octet-stream')
            if body[:1] == b'G':
                ctype = 'video/mp2t'
            return [200, ctype, body]
        except Exception as e:
            self._log(f'localProxy异常: {e}')
            return [500, 'text/plain', str(e)]

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
                    self._log(f'被拦截 [{r.status_code}] 重试 {attempt+1}')
                    continue
                else:
                    return ''
            except requests.exceptions.Timeout:
                self._log(f'超时重试 {attempt+1}')
            except Exception as e:
                self._log(f'异常 {e} 重试 {attempt+1}')
        return ''

    def _extract_player_data(self, html):
        """提取 player_data JSON"""
        if not html:
            return None

        # 匹配: var player_data={...}
        match = re.search(r'var\s+player_data\s*=\s*(\{[^}]+\})', html, re.DOTALL)
        if match:
            try:
                json_str = match.group(1)
                # 处理转义的斜杠
                json_str = json_str.replace('\\/', '/')
                data = json.loads(json_str)
                return data
            except Exception as e:
                self._log(f'player_data 解析失败: {e}')
        return None

    def _extract_videos_from_html(self, html):
        """从 HTML 提取视频列表"""
        videos = []

        # 模式1: video-card 结构
        cards = re.findall(r'<div class="video-card">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
        for card in cards:
            # 提取播放链接
            play_match = re.search(r'href="(/cn/home/web/index\.php/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"', card)
            if not play_match:
                continue

            play_url, vid, sid, nid = play_match.groups()

            # 提取图片
            img_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', card)
            pic = img_match.group(1) if img_match else ''
            alt = img_match.group(2) if img_match else ''

            # 提取标题
            title_match = re.search(r'<div class="video-title">(.*?)</div>', card, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            else:
                title = alt or f'视频{vid}'

            videos.append({
                'vod_id': f'{vid}_{sid}_{nid}',
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': ''
            })

        # 模式2: 宽松匹配（如果模式1失败）
        if not videos:
            links = re.findall(r'href="(/cn/home/web/index\.php/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"', html)
            for play_url, vid, sid, nid in links:
                videos.append({
                    'vod_id': f'{vid}_{sid}_{nid}',
                    'vod_name': f'视频{vid}',
                    'vod_pic': '',
                    'vod_remarks': ''
                })

        return videos

    def init(self, extend=''):
        self.session.headers.update(self._get_headers())
        self._categories = [
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
        self._log(f'初始化完成，分类 {len(self._categories)} 个')

    def homeContent(self, filter=False):
        try:
            cats = self._categories or []

            # 获取首页视频
            html = self._fetch(self.host + '/cn/home/web/index.php/vod/search/by/time_add.html')
            items = self._extract_videos_from_html(html)[:20] if html else []

            self._log(f'homeContent: 分类 {len(cats)}, 视频 {len(items)}')

            result = {'class': cats, 'list': items}
            return result
        except Exception as e:
            self._log(f'homeContent 异常: {e}')
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        html = self._fetch(self.host + '/cn/home/web/index.php/vod/search/by/time_add.html')
        items = self._extract_videos_from_html(html)[:20] if html else []
        return {'list': items}

    def categoryContent(self, tid, pg, filter=False, extend=''):
        try:
            page = int(pg) if pg else 1
            tid = str(tid or '').strip()

            # 构建URL
            if page == 1:
                url = f'{self.host}/cn/home/web/index.php/vod/type/id/{tid}.html'
            else:
                url = f'{self.host}/cn/home/web/index.php/vod/type/id/{tid}/page/{page}.html'

            self._log(f'请求分类页: {url}')

            html = self._fetch(url)
            if not html:
                return {'list': [], 'page': page, 'pagecount': 1}

            items = self._extract_videos_from_html(html)

            # 判断是否有下一页
            has_next = f'/page/{page + 1}.html' in html

            self._log(f'分类页解析到 {len(items)} 个视频')

            return {
                'list': items,
                'page': page,
                'pagecount': 999 if has_next or len(items) >= 10 else page,
                'limit': len(items),
                'total': 9999
            }
        except Exception as e:
            self._log(f'categoryContent 异常: {e}')
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}

    def detailContent(self, ids):
        try:
            vid = str(ids[0] if isinstance(ids, list) else ids)
            self._log(f'详情页: {vid}')

            # 解析 vid: {video_id}_{sid}_{nid}
            parts = vid.split('_')
            if len(parts) >= 3:
                video_id, sid, nid = parts[0], parts[1], parts[2]
            else:
                video_id, sid, nid = vid, '1', '1'

            # 构建播放页URL
            url = f'{self.host}/cn/home/web/index.php/vod/play/id/{video_id}/sid/{sid}/nid/{nid}.html'
            self._log(f'请求播放页: {url}')

            html = self._fetch(url)
            if not html:
                return {'list': []}

            # 提取 player_data
            player_data = self._extract_player_data(html)

            title = f'视频{video_id}'
            pic = ''
            m3u8_url = ''

            if player_data:
                m3u8_url = player_data.get('url', '')
                title = player_data.get('title', title)
                encrypt = player_data.get('encrypt', 0)

                self._log(f'player_data: encrypt={encrypt}, url={m3u8_url[:60] if m3u8_url else "empty"}...')

                if encrypt != 0:
                    self._log(f'警告: 检测到加密 encrypt={encrypt}')

            # 备用：直接从HTML找m3u8
            if not m3u8_url:
                m3u8_match = re.search(r"(https?://[^\"'<>\s]+\.m3u8[^\"'<>\s]*)", html)
                if m3u8_match:
                    m3u8_url = m3u8_match.group(1)

            # 提取封面
            og_image = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
            if og_image:
                pic = og_image.group(1)

            # 构造播放URL（走代理）
            if m3u8_url:
                play_url = self._make_proxy_url('media', m3u8_url)
            else:
                play_url = url

            self._log(f'详情: {title}, 播放: {play_url[:60]}...')

            return {'list': [{
                'vod_id': vid,
                'vod_name': str(title),
                'vod_pic': str(pic),
                'vod_play_from': '直链',
                'vod_play_url': f'第1集${play_url}'
            }]}
        except Exception as e:
            self._log(f'detailContent 异常: {e}')
            return {'list': []}

    def playerContent(self, flag, id, vipFlags=None):
        play_id = str(id or '')

        # 如果是代理URL，直接返回
        if 'do=py' in play_id or 'type=media' in play_id:
            return {
                'parse': 0,
                'url': play_id,
                'header': {
                    'Referer': self.host + '/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                }
            }

        # 如果是m3u8直链，包装为代理
        if '.m3u8' in play_id:
            proxy_url = self._make_proxy_url('media', play_id)
            return {
                'parse': 0,
                'url': proxy_url,
                'header': {
                    'Referer': self.host + '/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                }
            }

        # 默认
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
                f'{self.host}/cn/home/web/index.php/vod/search/wd/{keyword}.html',
                f'{self.host}/cn/home/web/index.php/vod/search.html?wd={keyword}',
            ]

            items = []
            for url in urls_to_try:
                self._log(f'尝试搜索: {url}')
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
            self._log(f'searchContent 异常: {e}')
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}
