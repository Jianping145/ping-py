#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
追剧狂飙 (DramaRush) 爬虫 - 无代理直链版
国内直连，无需代理，优化加载速度
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
    host = 'https://ai.dramarush.tv'
    session = requests.Session()
    _debug = True

    # 缓存
    cache = {}
    fallback = []
    eps = {}
    cursor = {}
    seen_page = {}

    def _log(self, msg):
        if self._debug:
            print('[dramarush] ' + str(msg))

    def getName(self):
        return '追剧狂飙'

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
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer or self.host + '/'
        }

    def _enc(self, o):
        return quote(json.dumps({"json": o}, ensure_ascii=False, separators=(",", ":")), safe="")

    def _api(self, name, data=None):
        try:
            url = self.host + '/api/trpc/' + name
            if data is not None:
                url += '?input=' + self._enc(data)

            self._log('API请求: ' + name)
            r = self.session.get(url, headers=self._get_headers(), timeout=12, verify=False)

            if r.status_code != 200:
                return {} if data is not None else []

            result = r.json()
            return result.get('result', {}).get('data', {}).get('json', {} if data is not None else [])
        except Exception as e:
            self._log('API异常: ' + str(e))
            return {} if data is not None else []

    def _unesc(self, s):
        return (s or '').replace('\u0026', '&').replace('\/', '/')

    def _fix(self, u):
        if not u:
            return ''
        if u.startswith('/'):
            return self.host + u
        return u

    def _img_min(self, u):
        if not u or '_minimize.' in u:
            return u or ''
        q = ''
        p = u
        if '?' in u:
            p, q = u.split('?', 1)
            q = '?' + q
        i = p.rfind('.')
        return (p[:i] + '_minimize.webp' + q) if i > p.rfind('/') else u

    def _pic(self, v, x):
        a = [v.get('cover'), v.get('poster'), x.get('vod_pic')]
        b = []
        for u in a:
            if not u or 'dc/img/828ed491f008e85d9caef01a.jpg' in u:
                continue
            if 'cdn.shorttv.online/lsj/' in u:
                u = u.replace('https://cdn.shorttv.online/lsj/', 'https://raw.shorttv.online/lsj/')
            b.append(self._img_min(u))
        return b[0] if b else ''

    def _it(self, x):
        if not isinstance(x, dict):
            return {}
        v = x.get('drama') or x
        vid = str(v.get('id') or x.get('id') or '')
        if not vid:
            return {}

        return {
            'vod_id': vid,
            'vod_name': v.get('title') or x.get('vod_name') or vid,
            'vod_pic': self._pic(v, x),
            'vod_remarks': str(v.get('totalEpisodes') or '').strip() + '集' if v.get('totalEpisodes') else x.get('vod_remarks', ''),
            'vod_content': v.get('description') or x.get('vod_content', ''),
            'trailerUrl': self._fix(x.get('trailerUrl', '')),
            'firstEpisodeId': x.get('firstEpisodeId') or ''
        }

    def _items(self, d, mode='all', need_pic=False):
        arr = d.get('items', []) if isinstance(d, dict) else d if isinstance(d, list) else []
        out = []
        seen_id = set()
        seen_name = set()

        for x in arr:
            if not isinstance(x, dict):
                continue
            v = x.get('drama') if isinstance(x, dict) else {}
            if not isinstance(v, dict):
                v = x
            tags = [str(t.get('name') or '') for t in v.get('tags', []) if isinstance(t, dict)] if isinstance(v, dict) else []
            adult = any(t.startswith('adult-') or '不伦' in t or '偷情' in t or '成人' in t for t in tags)
            if mode == 'normal' and adult:
                continue
            it = self._it(x)
            name = re.sub(r'\s+', '', it.get('vod_name', ''))
            if need_pic and not it.get('vod_pic'):
                continue
            if it.get('vod_id') and name and it['vod_id'] not in seen_id and name not in seen_name:
                seen_id.add(it['vod_id'])
                seen_name.add(name)
                self.cache[it['vod_id']] = it
                out.append({k: it.get(k, '') for k in ['vod_id', 'vod_name', 'vod_pic', 'vod_remarks']})
        return out

    def _fallback_items(self):
        out = []
        seen = set()
        for x in self.fallback:
            name = re.sub(r'\s+', '', x['vod_name'])
            if name not in seen:
                seen.add(name)
                self.cache[x['vod_id']] = x
                out.append({k: x.get(k, '') for k in ['vod_id', 'vod_name', 'vod_pic', 'vod_remarks']})
        return out

    def _list(self, tid='t-5jxcit', pg=1):
        pg = int(pg)
        mp = {
            't-5jxcit': {'categorySlug': 't-5jxcit'},
            'adult_short': {'tagSlug': 'adult'},
            'normal_short': {'contentKind': 'SHORT_DRAMA'},
        }
        if pg == 1:
            self.cursor[tid] = {}
            self.seen_page[tid] = set()
        cur = self.cursor.get(tid, {}).get(pg)
        if pg > 1 and not cur:
            return []
        mode = 'normal' if tid == 'normal_short' else 'all'
        seen = self.seen_page.setdefault(tid, set())
        out = []
        nxt = ''

        if tid in ['recommend', 'all', '']:
            d = self._api('feed.recommend', {'limit': 12})
            nxt = d.get('nextCursor') if isinstance(d, dict) else ''
            li = self._items(d)
            for x in li:
                k = x.get('vod_id') or re.sub(r'\s+', '', x.get('vod_name', ''))
                if k and k not in seen:
                    seen.add(k)
                    out.append(x)
        else:
            data = dict({'limit': 12}, **mp.get(tid, {'categorySlug': tid}))
            if cur:
                data['cursor'] = cur
            for _ in range(8):
                d = self._api('feed.browse', data)
                if not d:
                    break
                nxt = d.get('nextCursor') if isinstance(d, dict) else ''
                li = self._items(d, mode, tid == 'normal_short')
                for x in li:
                    k = x.get('vod_id') or re.sub(r'\s+', '', x.get('vod_name', ''))
                    if k and k not in seen:
                        seen.add(k)
                        out.append(x)
                        if len(out) >= 12:
                            break
                if len(out) >= 12 or not nxt:
                    break
                data['cursor'] = nxt

        if nxt:
            self.cursor.setdefault(tid, {})[pg + 1] = nxt
        return out

    def _episodes(self, vid):
        if vid in self.eps:
            return self.eps[vid]
        d = self._api('episode.watch', {'dramaId': vid, 'episodeNumber': 1})
        arr = d.get('episodes', []) if isinstance(d, dict) else []
        self.eps[vid] = arr
        return arr

    def init(self, extend=''):
        self.session.headers.update(self._get_headers())
        self._log('初始化完成')

    def homeContent(self, filter=False):
        try:
            cls = [
                {'type_id': 'adult_short', 'type_name': '成人短剧'},
                {'type_id': 'normal_short', 'type_name': '正规短剧'},
                {'type_id': 't-5jxcit', 'type_name': '短剧'},
            ]
            li = self._list('recommend') or self._list('t-5jxcit') or self._fallback_items()
            return {'class': cls, 'list': li, 'filters': {}}
        except Exception as e:
            self._log('homeContent 异常: ' + str(e))
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        li = self._list('recommend') or self._fallback_items()
        return {'list': li}

    def categoryContent(self, tid, pg, filter=False, extend=''):
        try:
            pg = int(pg)
            li = self._list(tid, pg)
            has_next = bool(self.cursor.get(tid, {}).get(pg + 1))
            return {
                'page': pg,
                'pagecount': pg + 1 if has_next else pg,
                'limit': 12,
                'total': pg * 12 + (12 if has_next else 0),
                'count': len(li),
                'list': li
            }
        except Exception as e:
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}

    def detailContent(self, ids):
        try:
            out = []
            if not self.cache:
                self._list('t-5jxcit')
            for vid in ids:
                vid = str(vid)
                it = self.cache.get(vid) or {
                    'vod_id': vid, 'vod_name': vid, 'vod_pic': '',
                    'vod_remarks': '12集', 'vod_content': '', 'firstEpisodeId': ''
                }
                m = re.search(r'(\d+)', it.get('vod_remarks', ''))
                total = max(1, min(int(m.group(1)) if m else 12, 80))
                eps = self._episodes(vid)
                if eps:
                    play_items = []
                    for i in range(1, total + 1):
                        ep_id = eps[i-1].get('id', '') if i-1 < len(eps) and isinstance(eps[i-1], dict) else ''
                        play_items.append('第' + str(i) + '集$' + vid + '/' + str(i) + '/' + ep_id)
                    play = '#'.join(play_items)
                else:
                    play = '第1集$' + vid + '/1/' + it.get('firstEpisodeId', '')
                out.append({
                    'vod_id': vid, 'vod_name': it.get('vod_name', vid),
                    'vod_pic': it.get('vod_pic', ''), 'vod_remarks': it.get('vod_remarks', ''),
                    'vod_content': it.get('vod_content', ''),
                    'vod_play_from': '直连', 'vod_play_url': play
                })
            return {'list': out}
        except Exception as e:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        """播放 - 智能选择 MP4 或 HLS"""
        vid, ep, eid = (str(id).split('/') + ['1', ''])[:3]
        url = ''

        self._log('playerContent: vid=' + vid + ', ep=' + ep + ', eid=' + eid)

        # 先获取 HLS（作为兜底）
        hls_url = ''
        try:
            d = self._api('episode.watch', {'dramaId': vid, 'episodeNumber': int(ep)})
            if d and isinstance(d, dict):
                episode = d.get('episode', {})
                if isinstance(episode, dict):
                    hls = episode.get('hlsUrl', '')
                    if hls:
                        hls = hls.replace('\u0026', '&').replace('\/', '/')
                        if hls.startswith('/'):
                            hls_url = self.host + hls
                        else:
                            hls_url = hls
        except Exception as e:
            self._log('episode.watch 失败: ' + str(e))

        # 优先尝试 MP4，检测是否存在
        if eid:
            mp4_url = 'https://raw.shorttv.online/uploads/direct/' + eid + '/video.mp4'
            try:
                r = self.session.head(mp4_url, timeout=5, verify=False, allow_redirects=True)
                if r.status_code == 200 and int(r.headers.get('content-length', 0)) > 10000:
                    url = mp4_url
                    self._log('MP4 直链可用: ' + url[:60])
                else:
                    self._log('MP4 不可用 (status=' + str(r.status_code) + ')')
            except Exception as e:
                self._log('MP4 检测失败: ' + str(e))

        # MP4 不可用则使用 HLS
        if not url and hls_url:
            url = hls_url
            self._log('使用 HLS: ' + url[:60])

        # 都没有则尝试 MP4（可能 404，但至少有响应）
        if not url and eid:
            url = 'https://raw.shorttv.online/uploads/direct/' + eid + '/video.mp4'

        if url:
            self._log('直链播放: ' + url[:80])
            return {
                'parse': 0,
                'url': url,
                'header': json.dumps({
                    'User-Agent': self._get_headers()['User-Agent'],
                    'Referer': self.host + '/zh/'
                })
            }

        return {
            'parse': 1,
            'url': '',
            'header': '{}'
        }

    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if pg else 1
            data = self._api('feed.browse', {'q': str(key), 'limit': 12})
            items = self._items(data)
            return {
                'list': items, 'page': page, 'pagecount': 999,
                'limit': len(items), 'total': 9999
            }
        except Exception as e:
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}
