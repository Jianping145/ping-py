# -*- coding: utf-8 -*-
# 123AV短视频 - CDN修复版 v2.6
# 修复：CDN域名变化 + 本地代理转圈圈

import sys
import re
import json
import urllib.parse
import threading
import time
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "123AV"

    def init(self, extend=''):
        self.home_url = 'https://123av.fun'
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        self._m3u8_cache = {}
        self._ts_cache = {}

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {
            'class': [
                {'type_id': 'publish-time/sort-desc', 'type_name': '最新发布'},
                {'type_id': 'view-count/sort-desc', 'type_name': '最多播放'},
                {'type_id': 'comment-count/sort-desc', 'type_name': '最多评论'},
                {'type_id': 'favorite-count/sort-desc', 'type_name': '最多收藏'},
                {'type_id': 'search/q-乱伦', 'type_name': '乱伦'},
                {'type_id': 'search/q-巨乳', 'type_name': '巨乳'},
                {'type_id': 'search/q-萝莉', 'type_name': '萝莉'},
                {'type_id': 'search/q-抖音风', 'type_name': '抖音风'},
                {'type_id': 'search/q-偷拍', 'type_name': '偷拍'},
                {'type_id': 'search/q-绿帽', 'type_name': '绿帽'},
                {'type_id': 'search/q-强奸', 'type_name': '强奸'},
                {'type_id': 'search/q-极品', 'type_name': '极品'},
                {'type_id': 'search/q-对白', 'type_name': '对白'},
                {'type_id': 'search/q-裸舞', 'type_name': '裸舞'},
                {'type_id': 'search/q-自慰', 'type_name': '自慰'},
                {'type_id': 'search/q-阿黑颜', 'type_name': '阿黑颜'},
                {'type_id': 'search/q-cos', 'type_name': 'COS'},
                {'type_id': 'search/q-厕所', 'type_name': '厕所'},
                {'type_id': 'search/q-户外', 'type_name': '户外'},
                {'type_id': 'search/q-大学生', 'type_name': '大学生'},
                {'type_id': 'search/q-抖音', 'type_name': '抖音'},
                {'type_id': 'search/q-大奶', 'type_name': '大奶'},
                {'type_id': 'search/q-性奴', 'type_name': '性奴'},
                {'type_id': 'search/q-校服', 'type_name': '校服'},
                {'type_id': 'search/q-药', 'type_name': '药'},
                {'type_id': 'search/q-黑人', 'type_name': '黑人'},
                {'type_id': 'search/q-熟女', 'type_name': '熟女'},
                {'type_id': 'search/q-足交', 'type_name': '足交'},
                {'type_id': 'search/q-马眼', 'type_name': '马眼'},
                {'type_id': 'search/q-单男', 'type_name': '单男'},
                {'type_id': 'search/q-晕', 'type_name': '晕'},
                {'type_id': 'search/q-新娘', 'type_name': '新娘'},
                {'type_id': 'search/q-TS', 'type_name': 'TS'},
                {'type_id': 'search/q-你好', 'type_name': '你好'},
                {'type_id': 'search/q-喷水', 'type_name': '喷水'},
                {'type_id': 'search/q-母子', 'type_name': '母子'},
                {'type_id': 'search/q-假装', 'type_name': '假装'},
                {'type_id': 'search/q-偷情', 'type_name': '偷情'},
                {'type_id': 'search/q-母狗', 'type_name': '母狗'},
            ],
            'filters': {}
        }

    def homeVideoContent(self):
        return self.categoryContent('publish-time/sort-desc', 1, {}, {})

    def _fetch_html(self, url):
        try:
            rsp = self.fetch(url, headers={
                "User-Agent": self.ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }, timeout=15)
            if rsp and hasattr(rsp, 'text') and rsp.text:
                return rsp.text
        except Exception as e:
            print(f'fetch error: {e}')
        return ''

    def _extract_video_list(self, html):
        """提取列表。"""
        videos = []
        if not html:
            return videos

        try:
            card_pattern = re.compile(
                r'<a\b([^>]*\bdata-id=["\']?(\d+)["\']?[^>]*)>(.*?)</a>',
                re.I | re.S
            )
            cards = card_pattern.findall(html)

            if not cards:
                card_pattern = re.compile(
                    r'<[^>]*\bdata-id=["\']?(\d+)["\']?[^>]*>.*?</[^>]+>',
                    re.I | re.S
                )

            seen = set()

            for attrs, vid, content in cards:
                try:
                    if vid in seen:
                        continue
                    seen.add(vid)

                    block = attrs + " " + content

                    src_match = re.search(
                        r'\bdata-src=["\']([^"\']+\.m3u8(?:\?[^"\']*)?)["\']',
                        block, re.I
                    )
                    poster_match = re.search(
                        r'\bdata-poster=["\']([^"\']+)["\']',
                        block, re.I
                    )
                    dur_match = re.search(
                        r'\bdata-duration=["\']?(\d+)["\']?',
                        block, re.I
                    )

                    title_match = re.search(
                        r'<xwya-video\b[^>]*\balt=["\']([^"\']*)["\']',
                        content, re.I
                    )
                    if not title_match:
                        title_match = re.search(
                            r'\btitle=["\']([^"\']*)["\']',
                            attrs, re.I
                        )
                    if not title_match:
                        title_match = re.search(
                            r'\baria-label=["\']([^"\']*)["\']',
                            attrs, re.I
                        )
                    title = title_match.group(1).strip() if title_match else ""

                    if not title:
                        plain = re.sub(r'<[^>]+>', ' ', content)
                        plain = re.sub(r'\s+', ' ', plain).strip()
                        title = plain[:120] if plain else f'视频{vid}'

                    poster = poster_match.group(1) if poster_match else ""

                    duration = int(dur_match.group(1)) if dur_match else 0
                    if duration >= 3600:
                        duration_str = f'{duration // 3600}:{(duration % 3600) // 60:02d}:{duration % 60:02d}'
                    else:
                        duration_str = f'{duration // 60:02d}:{duration % 60:02d}' if duration else ''

                    item = {
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': poster,
                        'vod_remarks': duration_str,
                    }

                    if src_match:
                        item['_m3u8'] = src_match.group(1)

                    videos.append(item)

                except Exception:
                    continue

        except Exception as e:
            print(f'_extract_video_list error: {e}')

        return videos

    def categoryContent(self, tid, page, filter, ext):
        """分类列表。"""
        video_list = []

        try:
            page = int(page or 1)
        except Exception:
            page = 1

        try:
            base_path = str(tid).strip().lstrip('/')

            if page <= 1:
                url = f'{self.home_url}/{base_path}'
            else:
                url = f'{self.home_url}/{base_path}/page-{page}'

            print(f'[123AV] category url: {url}')

            html = self._fetch_html(url)
            if not html:
                print(f'[123AV] empty html: {url}')
                return {
                    'list': [],
                    'page': page,
                    'pagecount': 0,
                    'limit': 20,
                    'total': 0
                }

            video_list = self._extract_video_list(html)

            if not video_list and page > 1:
                alt_urls = [
                    f'{self.home_url}/{base_path}?page={page}',
                    f'{self.home_url}/{base_path}?page_id={page}',
                ]
                for alt_url in alt_urls:
                    html2 = self._fetch_html(alt_url)
                    if html2:
                        video_list = self._extract_video_list(html2)
                        if video_list:
                            url = alt_url
                            print(f'[123AV] fallback category url: {url}')
                            break

        except Exception as e:
            print(f'categoryContent error: {e}')

        return {
            'list': video_list,
            'page': page,
            'pagecount': 999 if video_list else 0,
            'limit': 20,
            'total': 999 * 20 if video_list else 0
        }

    def detailContent(self, did):
        """视频详情 - 强化m3u8提取"""
        video_list = []
        try:
            vid = did[0] if isinstance(did, list) else did
            detail_url = f'{self.home_url}/detail/{vid}'

            if vid in self._m3u8_cache:
                m3u8_url = self._m3u8_cache[vid]
                print(f'[123AV] 使用缓存m3u8: {vid}')
                vod_pic = ''
                vod_name = f'视频{vid}'
                vod_content = ''
                duration_str = ''
            else:
                html = self._fetch_html(detail_url)
                m3u8_url = ''
                vod_pic = ''
                vod_name = ''
                vod_content = ''
                duration_str = ''

                if html:
                    print(f'[123AV] detail HTML长度: {len(html)}')

                    # 强化m3u8提取 - 支持任何CDN域名
                    m3u8_patterns = [
                        r'data-src=["\']([^"\']+\.m3u8[^"\']*)["\']',
                        r'<source[^>]+src=["\']([^"\']+\.m3u8[^"\']*)["\']',
                        r'<video[^>]+src=["\']([^"\']+\.m3u8[^"\']*)["\']',
                        r'["\'](https://[^"\']+/[^"\']+\.m3u8[^"\']*)["\']',
                        r'(https://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
                        r'["\'](/[^\s"\'<>]+\.m3u8[^\s"\'<>]*)["\']',
                    ]

                    for i, pattern in enumerate(m3u8_patterns, 1):
                        src_match = re.search(pattern, html, re.I)
                        if src_match:
                            m3u8_url = src_match.group(1)
                            print(f'[123AV] 方式{i}提取到m3u8: {m3u8_url[:100]}...')
                            break

                    # 如果找到相对路径，补全
                    if m3u8_url and m3u8_url.startswith('/'):
                        m3u8_url = 'https://static.123av.fun' + m3u8_url

                    if m3u8_url:
                        self._m3u8_cache[vid] = m3u8_url

                    # 提取封面
                    poster_patterns = [
                        r'data-poster=["\']([^"\']+)["\']',
                        r'property="og:image"\s+content=["\']([^"\']+)["\']',
                        r'<meta[^>]+og:image[^>]+content=["\']([^"\']+)["\']',
                    ]
                    for pattern in poster_patterns:
                        poster_match = re.search(pattern, html, re.I)
                        if poster_match:
                            vod_pic = poster_match.group(1)
                            break

                    # 提取标题
                    title_patterns = [
                        r'<h1[^>]*>([^<]+)</h1>',
                        r'property="og:title"\s+content=["\']([^"\']+)["\']',
                        r'<xwya-video[^>]*alt=["\']([^"\']*)["\']',
                        r'<title[^>]*>([^<]+)</title>',
                    ]
                    for pattern in title_patterns:
                        title_match = re.search(pattern, html, re.I)
                        if title_match:
                            vod_name = title_match.group(1).strip()
                            break

                    desc_match = re.search(r'property="og:description"\s+content=["\']([^"\']+)["\']', html)
                    vod_content = desc_match.group(1) if desc_match else ''

                    dur_match = re.search(r'data-duration=["\']?(\d+)["\']?', html)
                    if dur_match:
                        dur = int(dur_match.group(1))
                        if dur >= 3600:
                            duration_str = f'{dur // 3600}:{(dur % 3600) // 60:02d}:{dur % 60:02d}'
                        else:
                            duration_str = f'{dur // 60:02d}:{dur % 60:02d}'

            if m3u8_url:
                vod_play_url = f'正片${m3u8_url}'
                print(f'[123AV] 播放URL: {vod_play_url[:100]}...')
            else:
                vod_play_url = ''
                print(f'[123AV] 警告: 未提取到m3u8, vid={vid}')

            video_list.append({
                'vod_id': vid,
                'vod_name': vod_name,
                'vod_pic': vod_pic,
                'vod_remarks': duration_str,
                'vod_content': vod_content,
                'vod_play_from': '短视频',
                'vod_play_url': vod_play_url,
                'type_name': '短视频',
                'vod_year': '',
                'vod_area': '',
                'vod_director': '',
                'vod_actor': '',
            })

        except Exception as e:
            print(f'detailContent error: {e}')
            import traceback
            traceback.print_exc()

        return {
            'list': video_list,
            'parse': 0,
            'jx': 0
        }

    def searchContent(self, key, quick, page='1'):
        video_list = []
        try:
            encoded_key = urllib.parse.quote(key)
            url = f'{self.home_url}/search/{encoded_key}/page-{page}'
            html = self._fetch_html(url)
            video_list = self._extract_video_list(html)
        except Exception as e:
            print(f'searchContent error: {e}')

        return {
            'list': video_list,
            'page': int(page),
            'pagecount': 99,
            'limit': 20,
            'total': 99 * 20
        }

    def playerContent(self, flag, pid, vipFlags):
        """播放器内容 - 关键修复：直接播放，不用本地代理"""

        print(f'[123AV] playerContent called: flag={flag}, pid={pid[:80]}...')

        # 如果pid已经是m3u8地址，直接返回，不走代理
        if pid.startswith('http') and '.m3u8' in pid:
            print(f'[123AV] 直接播放m3u8: {pid[:80]}...')
            return {
                'parse': 0,
                'url': pid,  # 直接返回原始URL，不走代理
                'header': {
                    'User-Agent': self.ua,
                    'Referer': self.home_url + '/',
                    'Origin': self.home_url,
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity',
                    'Connection': 'keep-alive',
                }
            }

        # 如果是详情页URL或纯数字ID
        if '/detail/' in pid or pid.isdigit():
            vid = pid.split('/')[-1] if '/' in pid else pid
            print(f'[123AV] 从详情页获取m3u8: vid={vid}')

            if vid in self._m3u8_cache:
                m3u8 = self._m3u8_cache[vid]
                print(f'[123AV] 使用缓存m3u8')
                return {
                    'parse': 0,
                    'url': m3u8,  # 直接返回
                    'header': {
                        'User-Agent': self.ua,
                        'Referer': self.home_url + '/',
                        'Origin': self.home_url,
                        'Accept': '*/*',
                        'Accept-Encoding': 'identity',
                    }
                }

            detail_url = f'{self.home_url}/detail/{vid}'
            html = self._fetch_html(detail_url)
            if html:
                patterns = [
                    r'data-src=["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'<source[^>]+src=["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'["\'](https://[^"\']+/[^"\']+\.m3u8[^"\']*)["\']',
                    r'(https://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
                ]
                for pattern in patterns:
                    src_match = re.search(pattern, html, re.I)
                    if src_match:
                        m3u8 = src_match.group(1)
                        if m3u8.startswith('/'):
                            m3u8 = 'https://static.123av.fun' + m3u8
                        self._m3u8_cache[vid] = m3u8
                        print(f'[123AV] playerContent提取到m3u8: {m3u8[:80]}...')
                        return {
                            'parse': 0,
                            'url': m3u8,  # 直接返回
                            'header': {
                                'User-Agent': self.ua,
                                'Referer': self.home_url + '/',
                                'Origin': self.home_url,
                                'Accept': '*/*',
                                'Accept-Encoding': 'identity',
                            }
                        }

        # 默认返回
        print(f'[123AV] 使用外部解析: {pid[:50]}...')
        return {
            'parse': 1,
            'url': pid,
            'header': {
                'User-Agent': self.ua,
                'Referer': self.home_url + '/',
            }
        }

    def localProxy(self, params):
        """本地代理 - 简化版，避免转圈圈"""
        try:
            url = params.get('url', '')
            proxy_type = params.get('type', 'm3u8')

            if not url:
                return {}

            print(f'[123AV] localProxy: type={proxy_type}, url={url[:60]}...')

            import requests

            # 根据URL确定Referer
            referer = self.home_url + '/'
            if 'imgcaches.cc' in url:
                referer = 'https://123av.fun/'
            elif 'static.123av.fun' in url:
                referer = 'https://123av.fun/'

            headers = {
                'User-Agent': self.ua,
                'Referer': referer,
                'Origin': 'https://123av.fun',
            }

            # 检查ts缓存
            if proxy_type == 'ts' and url in self._ts_cache:
                print(f'[123AV] 命中ts缓存')
                return {
                    'code': 200,
                    'content': self._ts_cache[url],
                    'headers': {
                        'Content-Type': 'video/mp2t',
                        'Access-Control-Allow-Origin': '*',
                    }
                }

            # 下载
            rsp = requests.get(url, headers=headers, timeout=20, verify=False)

            if proxy_type == 'm3u8':
                content = rsp.text
                print(f'[123AV] m3u8 length: {len(content)}')

                if '#EXTM3U' in content:
                    lines = content.split('\n')
                    new_lines = []
                    ts_count = 0

                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # 处理相对路径
                            if line.startswith('/'):
                                base_url = url.split('/')[0] + '//' + url.split('/')[2]
                                ts_url = base_url + line
                            elif line.startswith('http'):
                                ts_url = line
                            else:
                                base = url.rsplit('/', 1)[0] + '/'
                                ts_url = base + line

                            proxy_line = f'http://127.0.0.1:9978/proxy?do=123av&type=ts&url={urllib.parse.quote(ts_url)}'
                            new_lines.append(proxy_line)
                            ts_count += 1
                        else:
                            new_lines.append(line)

                    content = '\n'.join(new_lines)
                    print(f'[123AV] 替换 {ts_count} 个ts链接')

                return {
                    'code': 200,
                    'content': content.encode('utf-8'),
                    'headers': {
                        'Content-Type': 'application/vnd.apple.mpegurl',
                        'Access-Control-Allow-Origin': '*',
                    }
                }
            else:
                # ts分片
                content = rsp.content
                print(f'[123AV] ts length: {len(content)}')

                # 缓存
                self._ts_cache[url] = content
                if len(self._ts_cache) > 30:
                    oldest = next(iter(self._ts_cache))
                    del self._ts_cache[oldest]

                return {
                    'code': 200,
                    'content': content,
                    'headers': {
                        'Content-Type': 'video/mp2t',
                        'Access-Control-Allow-Origin': '*',
                    }
                }

        except Exception as e:
            print(f'[123AV] localProxy error: {e}')
            return {}

    def destroy(self):
        self._ts_cache.clear()
        self._m3u8_cache.clear()
        return '正在Destroy'


if __name__ == '__main__':
    pass
