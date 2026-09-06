# 蜜桃视频 T3 类型爬虫 (参照nww2.py框架重写)
# 网站: https://www.nht966hht.vip:9527
# API: AES-128-CBC (ZeroPadding) + MD5 签名加密

# coding=utf-8
# !/usr/bin/python

import sys
sys.path.append('..')

from base.spider import Spider
import requests
import json
import base64
import hashlib
import time
import re
import os
import string
import random
from urllib.parse import quote, unquote

try:
    from Crypto.Cipher import AES
except Exception:
    try:
        from Cryptodome.Cipher import AES
    except Exception:
        AES = None

TIMEOUT = 10

SITES = [
    {'name': 'nht966', 'host': 'https://www.nht966hht.vip:9527'},
    {'name': 'httre666', 'host': 'https://www.newhttestre666.cc'},
]

SIGN_KEY  = 'opum3_Loily$SV^6H'
BUNDLE_ID = 'com.ht9.web20.video'
BRAND_ID  = 'hongtao'
VERSION   = '1.0.0'
PROJECT_ID = '1'
PROXY_TYPE = 'mitao_img'


class Spider(Spider):

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.api_url = ''
        self.host = SITES[0]['host']
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "lang": "cn",
            "deviceType": "H5-android",
        }
        self._speed_test_done = False
        self._cached_host = ''
        self._cached_ts = 0
        self._speed_cache_ttl = 1800
        self._user_id = ''
        self._session_id = ''
        self._device_id = ''
        self._session_inited = False
        self._categories = []
        self._video_type_list = []
        self._session_cache = None
        self._session_cache_ttl = 1800

    def getName(self):
        return "蜜桃视频"

    def isVideoFormat(self, url):
        return url and ('.mp4' in url or '.m3u8' in url or '.ts' in url)

    def manualVideoCheck(self):
        return False

    # ============================================================
    # 多站点测速
    # ============================================================
    def _get_cached_site(self):
        try:
            if self._cached_host and (time.time() - self._cached_ts) < self._speed_cache_ttl:
                return self._cached_host, True
        except Exception:
            pass
        return '', False

    def _save_cached_site(self, host):
        try:
            self._cached_host = host
            self._cached_ts = time.time()
        except Exception:
            pass

    def _resolve_host(self, portal):
        try:
            r = requests.get(portal, headers=self.headers, timeout=TIMEOUT, verify=False)
            text = r.text or ''
            if 'targetSites' in text:
                m = re.search(r'targetSites\s*=\s*\[(.*?)\]', text, re.S)
                if m:
                    urls = re.findall(r'https?://[^\s"\',\]]+', m.group(1))
                    if urls:
                        return urls[0].rstrip('/')
                return ''
            if r.status_code == 200:
                return portal.rstrip('/')
        except Exception:
            pass
        return ''

    def _select_best_site(self):
        if self._speed_test_done:
            return
        cached_host, valid = self._get_cached_site()
        if valid:
            self.host = cached_host
            self._speed_test_done = True
            return
        resolved = ''
        for s in SITES:
            h = self._resolve_host(s['host'])
            if h:
                resolved = h
                break
        self.host = resolved or SITES[0]['host']
        self._speed_test_done = True
        if resolved:
            self._save_cached_site(resolved)

    # ============================================================
    # 会话缓存
    # ============================================================
    def _save_session_cache(self):
        try:
            self._session_cache = {
                'ts': time.time(),
                'user_id': self._user_id,
                'session_id': self._session_id,
                'device_id': self._device_id,
                'categories': self._categories,
                'video_type_list': self._video_type_list,
            }
        except Exception:
            pass

    def _load_session_cache(self):
        try:
            if self._session_cache is None:
                return False
            age = time.time() - self._session_cache.get('ts', 0)
            if age >= self._session_cache_ttl:
                return False
            self._user_id = self._session_cache.get('user_id', '')
            self._session_id = self._session_cache.get('session_id', '')
            self._device_id = self._session_cache.get('device_id', '')
            self._categories = self._session_cache.get('categories', [])
            self._video_type_list = self._session_cache.get('video_type_list', [])
            if not self._user_id or not self._session_id:
                return False
            return True
        except Exception:
            return False

    # ============================================================
    # AES
    # ============================================================
    @staticmethod
    def _zero_pad(data, block_size=16):
        pad_len = block_size - (len(data) % block_size)
        if pad_len == block_size:
            return data
        return data + b'\x00' * pad_len

    @staticmethod
    def _zero_unpad(data):
        return data.rstrip(b'\x00')

    def _gen_key(self, timestamp):
        ts = str(timestamp)
        return ts[-6:] + SIGN_KEY[:4] + BUNDLE_ID[:6]

    def _gen_iv(self):
        return BUNDLE_ID[-6:] + SIGN_KEY[-4:] + self._device_id[:6]

    def _aes_encrypt(self, plaintext, key_str, iv_str):
        if AES is None:
            raise ImportError('No AES module')
        key = key_str.encode('utf-8')
        iv = iv_str.encode('utf-8')
        cipher = AES.new(key, AES.MODE_CBC, iv)
        data = plaintext.encode('utf-8')
        padded = self._zero_pad(data)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode('utf-8')

    def _aes_decrypt(self, ciphertext_b64, key_str, iv_str):
        if AES is None:
            raise ImportError('No AES module')
        key = key_str.encode('utf-8')
        iv = iv_str.encode('utf-8')
        cipher = AES.new(key, AES.MODE_CBC, iv)
        cleaned = re.sub(r'\s', '', ciphertext_b64)
        encrypted = base64.b64decode(cleaned)
        decrypted = cipher.decrypt(encrypted)
        unpadded = self._zero_unpad(decrypted)
        return unpadded.decode('utf-8', errors='replace')

    def _generate_sign(self, params, api_path):
        sorted_keys = sorted(params.keys())
        concat = ''
        for k in sorted_keys:
            concat += str(params[k])
        raw = concat + SIGN_KEY + api_path
        return hashlib.md5(raw.encode('utf-8')).hexdigest().upper()

    @staticmethod
    def _generate_device_id():
        chars = string.ascii_lowercase + string.digits
        rand = ''.join(random.choice(chars) for _ in range(32))
        return 'H5-' + rand

    def _common_params(self):
        hostname = self.host.replace('https://', '').replace('http://', '')
        return {
            'timezone': 'Asia/Karachi',
            'version': VERSION,
            'channelId': 67,
            'channelId2': hostname,
            'brandId': BRAND_ID,
        }

    def _api_request(self, endpoint, params=None, skip_encrypt=False, _t=None):
        if params is None:
            params = {}
        timestamp = str(_t) if _t else str(int(time.time() * 1000))
        key_str = self._gen_key(timestamp)
        iv_str = self._gen_iv()
        full_params = self._common_params()
        full_params['t'] = timestamp
        full_params.update(params)
        full_params['sign'] = self._generate_sign(full_params, endpoint)
        api_url = self.host + endpoint
        headers = dict(self.headers)
        headers['t'] = timestamp
        if self._user_id:
            headers['userId'] = self._user_id
        if self._session_id:
            headers['sessionId'] = self._session_id
        headers['deviceId'] = self._device_id or ''
        headers['bundleId'] = BUNDLE_ID
        if skip_encrypt:
            body = json.dumps(full_params, ensure_ascii=False, separators=(',', ':'))
            headers['Content-Type'] = 'application/json'
            headers['encrypt'] = 'false'
        else:
            plain = json.dumps(full_params, ensure_ascii=False, separators=(',', ':'))
            body = self._aes_encrypt(plain, key_str, iv_str)
            headers['Content-Type'] = 'text/plain'
            headers['encrypt'] = 'true'
        try:
            r = self.session.post(api_url, data=body.encode('utf-8'),
                                  headers=headers, timeout=TIMEOUT, verify=False)
            resp = r.json()
            if resp.get('code') == 10000 and isinstance(resp.get('data'), str) and resp['data']:
                try:
                    decrypted = self._aes_decrypt(resp['data'], key_str, iv_str)
                    resp['data'] = json.loads(decrypted)
                except Exception:
                    pass
            return resp
        except Exception:
            return None

    def _ensure_session(self):
        if self._session_inited:
            return True
        if self._load_session_cache():
            self._session_inited = True
            if not self._video_type_list:
                appcfg = self._api_request('/ht/users/appConfig')
                if appcfg and appcfg.get('code') == 10000:
                    ac_data = appcfg.get('data', {})
                    if isinstance(ac_data, dict) and ac_data.get('appConfig'):
                        ac_cfg = ac_data['appConfig']
                        if isinstance(ac_cfg, dict) and ac_cfg.get('videoTypeList'):
                            self._video_type_list = ac_cfg['videoTypeList']
            return True
        if not self._device_id:
            self._device_id = self._generate_device_id()
        appcfg = self._api_request('/ht/users/appConfig')
        if appcfg and appcfg.get('code') == 10000:
            ac_data = appcfg.get('data', {})
            if isinstance(ac_data, dict) and ac_data.get('appConfig'):
                ac_cfg = ac_data['appConfig']
                if isinstance(ac_cfg, dict) and ac_cfg.get('videoTypeList'):
                    self._video_type_list = ac_cfg['videoTypeList']
        shared_t = int(time.time() * 1000)
        resp1 = self._api_request('/ht/users/initH5_1', _t=shared_t)
        if resp1 and resp1.get('code') == 10000:
            data = resp1.get('data', {})
            if data.get('deviceId'):
                self._device_id = data['deviceId']
            if data.get('typeTitleList'):
                self._categories = data['typeTitleList']
        self._api_request('/ht/users/initH5_2', _t=shared_t)
        resp = self._api_request('/ht/users/deviceLogin', {
            'bundleId': BUNDLE_ID,
            'brandId': BRAND_ID,
            'projectId': PROJECT_ID,
        })
        if resp and resp.get('code') == 10000:
            data = resp.get('data', {})
            self._user_id = data.get('userId', '')
            self._session_id = data.get('sessionId', '')
        self._session_inited = True
        self._save_session_cache()
        return True

    def get_proxy_image_url(self, img_url):
        if not img_url:
            return ''
        base_proxy = self.getProxyUrl()
        if not base_proxy:
            base_proxy = 'http://127.0.0.1:9980/proxy?do=py'
        # TVBox 框架路由 localProxy 必须依赖 api 参数定位爬虫实例
        if 'api=' not in base_proxy:
            api_url = getattr(self, 'api_url', '') or getattr(self, 'api', '') or getattr(self, 'extend', '')
            # 兜底：硬编码默认 api 地址（从日志确认）
            if not api_url:
                api_url = 'https://raw.githubusercontent.com/Jianping145/ping-py/refs/heads/main/蜜桃视频.py'
            if api_url and isinstance(api_url, str):
                # safe=':/' 保留 https:// 原样，只编码中文等特殊字符
                base_proxy += '&api=' + quote(api_url, safe=':/')
        return base_proxy + '&type=' + PROXY_TYPE + '&url=' + quote(img_url, safe='')

    def _fmt_duration(self, seconds):
        try:
            s = int(seconds or 0)
        except (TypeError, ValueError):
            return ''
        if s <= 0:
            return ''
        m, s = divmod(s, 60)
        return f"{m}:{s:02d}"

    def init(self, extend=""):
        self.extend = extend
        if extend and isinstance(extend, str) and extend.startswith('http'):
            self.api_url = extend
        cached_host, valid = self._get_cached_site()
        if valid:
            self.host = cached_host
            self._speed_test_done = True
        return True

    # ============================================================
    # 首页
    # ============================================================
    _CATEGORY_BLACKLIST = {'成人游戏', '漫画', '小说', '蜜穴女友', '一键脱衣', '春药商城', '同城交友', '吃瓜', '成人漫画', '女优', '专题'}

    def homeContent(self, filter):
        self._select_best_site()
        self._ensure_session()

        classes = []
        filters = {}

        if not self._categories:
            classes = [
                {'type_id': 'home', 'type_name': '首页'},
                {'type_id': 'actor', 'type_name': '女优'},
                {'type_id': 'topic', 'type_name': '专题'},
            ]
        else:
            for cat in self._categories:
                cid = str(cat.get('contentId', ''))
                title = cat.get('title', '')
                if not cid or not title or title in self._CATEGORY_BLACKLIST:
                    continue
                classes.append({'type_id': cid, 'type_name': title})
                cat_filters = []
                sub_cats = [v for v in self._video_type_list if str(v.get('typePid', '')) == cid]
                if sub_cats:
                    sub_values = [{'n': '全部', 'v': ''}]
                    for sc in sub_cats:
                        sc_id = str(sc.get('typeId', ''))
                        sc_name = sc.get('typeName', '')
                        if sc_id and sc_name:
                            sub_values.append({'n': sc_name, 'v': sc_id})
                    if len(sub_values) > 1:
                        cat_filters.append({'key': 'label', 'name': '分类', 'value': sub_values})
                first_level = [v for v in self._video_type_list
                               if str(v.get('typePid', '')) == '0' and str(v.get('typeId', '')) == cid]
                if first_level:
                    tags_str = first_level[0].get('tags', '')
                    if tags_str:
                        tag_list = [t.strip() for t in tags_str.split(',') if t.strip()]
                        if tag_list:
                            tag_values = [{'n': '全部', 'v': ''}]
                            for t in tag_list:
                                tag_values.append({'n': t, 'v': t})
                            cat_filters.append({'key': 'tag', 'name': '标签', 'value': tag_values})
                cat_filters.append({'key': 'sort', 'name': '排序', 'value': [
                    {'n': '最近更新', 'v': '0'},
                    {'n': '最多播放', 'v': '1'},
                    {'n': '最多收藏', 'v': '2'},
                ]})
                if cat_filters:
                    filters[cid] = cat_filters

            classes.append({'type_id': 'actor', 'type_name': '女优'})
            actors_filters = []
            actors_filters.append({'key': 'height', 'name': '身高', 'value': [
                {'n': '身高', 'v': ''},
            ] + [{'n': f'{h}cm', 'v': str(h)} for h in range(150, 165)]})
            actors_filters.append({'key': 'cup', 'name': '罩杯', 'value': [
                {'n': '罩杯', 'v': ''},
            ] + [{'n': f'{c}罩杯', 'v': c} for c in 'ABCDEFG']})
            actors_filters.append({'key': 'birthday', 'name': '年龄', 'value': [
                {'n': '年龄', 'v': ''},
            ] + [{'n': f'{y}年', 'v': str(y)} for y in range(2002, 1975, -1)]})
            actors_filters.append({'key': 'debut', 'name': '出道', 'value': [
                {'n': '出道', 'v': ''},
            ] + [{'n': f'{y}年', 'v': str(y)} for y in range(2025, 2000, -1)]})
            filters['actor'] = actors_filters
            classes.append({'type_id': 'topic', 'type_name': '专题'})

        home_videos = self.categoryContent('home', 1, '', {})
        return {
            'class': classes,
            'filters': filters,
            'list': home_videos.get('list', []),
        }

    def homeVideoContent(self, tid, pg, filter, extend):
        return self.categoryContent(tid or 'home', pg, filter, extend)

    # ============================================================
    # 分类列表
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid)
        pg = int(pg) if str(pg).isdigit() else 1

        self._select_best_site()
        self._ensure_session()
        vod_list = []

        if '@' in tid:
            real_tid = tid.replace('@', '')
            if real_tid.startswith('actor_'):
                actor_id = real_tid[len('actor_'):]
                detail_resp = self._api_request('/ht/content/queryActorDetail', {'actorId': actor_id})
                actor_name = ''
                if detail_resp and detail_resp.get('code') == 10000:
                    detail_data = detail_resp.get('data', {})
                    actor_info = (detail_data.get('actorDetail') or detail_data or {})
                    actor_name = (actor_info.get('actorName') or actor_info.get('actor_name') or '')
                if actor_name:
                    resp = self._api_request('/ht/content/search', {
                        'keywords': actor_name,
                        'pageNo': str(pg - 1),
                        'pageSize': '20',
                    })
                else:
                    resp = self._api_request('/ht/content/queryTypeVideosH5', {
                        'actorId': actor_id,
                        'pageNo': str(pg - 1),
                        'pageSize': '20',
                        'type': '1',
                    })
                if not resp or resp.get('code') != 10000:
                    return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
                data = resp.get('data', {})
                vod_list = self._extract_videos_from_data(data)
                total_page = int(data.get('totalPage') or data.get('total_page') or 1)
                return {'list': vod_list, 'page': pg, 'pagecount': max(total_page, 1),
                        'limit': len(vod_list), 'total': max(total_page, 1) * 20}
            elif real_tid.startswith('topic_'):
                topic_id = real_tid[len('topic_'):]
                resp = self._api_request('/ht/content/queryOriTopicVideos', {
                    'topicId': topic_id,
                    'pageNo': str(pg - 1),
                    'pageSize': '20',
                })
                if not resp or resp.get('code') != 10000:
                    return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
                data = resp.get('data', {})
                vod_list = self._extract_videos_from_data(data)
                total_page = int(data.get('totalPage') or data.get('total_page') or 1)
                return {'list': vod_list, 'page': pg, 'pagecount': max(total_page, 1),
                        'limit': len(vod_list), 'total': max(total_page, 1) * 20}
            else:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

        if tid == 'actor':
            api_params = {'pageNo': str(pg - 1), 'pageSize': '20'}
            if isinstance(extend, dict):
                _map = {'height': 'actorHeight', 'cup': 'cupSize', 'birthday': 'actorBirthday', 'debut': 'actorDebut'}
                for ek, ak in _map.items():
                    val = extend.get(ek, '')
                    if val:
                        api_params[ak] = val
            resp = self._api_request('/ht/content/getActors', api_params)
            if not resp or resp.get('code') != 10000:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            data = resp.get('data', {})
            vod_list = self._parse_actor_list(data)
            total_page = int(data.get('totalPage') or 1)
            return {'list': vod_list, 'page': pg, 'pagecount': total_page,
                    'limit': len(vod_list), 'total': total_page * 20}

        if tid == 'topic':
            resp = self._api_request('/ht/content/getOriTopicList', {
                'pageNo': str(pg - 1), 'pageSize': '20',
            })
            if not resp or resp.get('code') != 10000:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            data = resp.get('data', {})
            vod_list = self._parse_topic_list(data)
            return {'list': vod_list, 'page': pg, 'pagecount': 50,
                    'limit': len(vod_list), 'total': len(vod_list) * 50}

        if tid in ('home', 'new', 'hot'):
            sort_map = {'home': '1', 'new': '1', 'hot': '2'}
            resp = self._api_request('/ht/content/queryTypeVideosH5', {
                'pageNo': str(pg - 1),
                'pageSize': '20',
                'sort': sort_map.get(tid, '1'),
                'type': '1',
            })
            if not resp or resp.get('code') != 10000:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            data = resp.get('data', {})
            items = (data.get('typeVideoList') or data.get('list') or data.get('data') or data.get('videoList') or [])
            if isinstance(items, list):
                for v in items:
                    parsed = self._parse_video(v)
                    if parsed:
                        vod_list.append(parsed)
        else:
            api_params = {
                'pageNo': str(pg - 1),
                'pageSize': '20',
                'typeId': tid,
                'type': '1',
            }
            if isinstance(extend, dict):
                for key in ('label', 'tag', 'sort'):
                    val = extend.get(key, '')
                    if val:
                        api_params[key] = val
            resp = self._api_request('/ht/content/queryTypeVideosH5', api_params)
            if not resp or resp.get('code') != 10000:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            data = resp.get('data', {})
            items = (data.get('typeVideoList') or data.get('list') or data.get('data') or data.get('videoList') or [])
            if isinstance(items, list):
                for v in items:
                    parsed = self._parse_video(v)
                    if parsed:
                        vod_list.append(parsed)
        total_page = int(data.get('totalPage') or 1)
        return {
            'list': vod_list,
            'page': pg,
            'pagecount': total_page,
            'limit': len(vod_list),
            'total': total_page * 20,
        }

    def _extract_videos_from_data(self, data):
        if isinstance(data, list):
            items = data
        elif not isinstance(data, dict):
            return []
        else:
            items = (data.get('videoList') or data.get('list') or data.get('data')
                     or data.get('videos') or data.get('typeVideoList')
                     or data.get('topicVideoIdList') or data.get('searchList')
                     or data.get('contentList') or data.get('records')
                     or data.get('pageData') or [])
        if not isinstance(items, list):
            return []
        return [p for v in items if (p := self._parse_video(v))]

    @staticmethod
    def _try_get(item, *keys):
        for k in keys:
            v = item.get(k)
            if v is not None and v != '':
                return v
        return ''

    def _parse_actor_list(self, data):
        if isinstance(data, list):
            items = data
        elif not isinstance(data, dict):
            return []
        else:
            items = (data.get('actorList') or data.get('actors') or data.get('list')
                     or data.get('data') or [])
        if not isinstance(items, list):
            return []
        results = []
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            actor_id = str(self._try_get(item, 'actorId', 'contentId', 'id', 'artId', 'actor_id', 'userId'))
            actor_name = str(self._try_get(item, 'actorName', 'name', 'title', 'artName', 'actor_name', 'actor'))
            actor_img = str(self._try_get(item, 'actorPic', 'actorImg', 'img', 'avatar', 'cover',
                'imageUrl', 'headImg', 'head', 'photo', 'image', 'pic', 'actor_img'))
            actor_count = str(self._try_get(item, 'videoCount', 'contentCount', 'count', 'totalCount', 'total', 'video_count'))
            if not actor_id or actor_id in seen:
                continue
            seen.add(actor_id)
            if not actor_img:
                actor_img = self.host + '/favicon.ico'
            remarks = f'{actor_count}部' if actor_count else ''
            results.append({
                'vod_id': 'actor_' + actor_id + '@',
                'vod_name': actor_name or ('演员' + actor_id),
                'vod_pic': self.get_proxy_image_url(actor_img),
                'vod_tag': 'folder',
                'vod_remarks': remarks,
            })
        return results

    def _parse_topic_list(self, data):
        if isinstance(data, list):
            items = data
        elif not isinstance(data, dict):
            return []
        else:
            items = (data.get('topicList') or data.get('oriTopicList') or data.get('list')
                     or data.get('data') or data.get('topics') or [])
        if not isinstance(items, list):
            return []
        results = []
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            topic_id = str(self._try_get(item, 'topicId', 'id', 'contentId', 'oriTopicId', 'topic_id'))
            topic_name = str(self._try_get(item, 'topicName', 'name', 'title', 'oriTopicName', 'topic_name', 'topic'))
            topic_img = str(self._try_get(item, 'topicPic', 'topicImg', 'img', 'cover', 'imageUrl', 'pic',
                'thumb', 'image', 'topic_img', 'oriTopicImg'))
            topic_count = str(self._try_get(item, 'videoCount', 'count', 'contentCount', 'totalCount', 'total', 'video_count'))
            if not topic_id or topic_id in seen:
                continue
            seen.add(topic_id)
            if not topic_img:
                topic_img = self.host + '/favicon.ico'
            remarks = f'{topic_count}部' if topic_count else ''
            results.append({
                'vod_id': 'topic_' + topic_id + '@',
                'vod_name': topic_name or ('专题' + topic_id),
                'vod_pic': self.get_proxy_image_url(topic_img),
                'vod_tag': 'folder',
                'vod_remarks': remarks,
            })
        return results

    def _parse_video(self, item):
        if item.get('contentType') == 3 and item.get('jumpScheme'):
            return None
        vid = str(item.get('contentId') or item.get('id') or item.get('videoId') or '')
        title = item.get('title') or item.get('name') or item.get('videoTitle') or ''
        pic = item.get('img') or item.get('cover') or item.get('coverUrl') or item.get('pic') or item.get('imageUrl') or ''
        remarks = item.get('duration') or item.get('playCount') or item.get('remark') or ''
        if remarks and str(remarks).isdigit():
            remarks = self._fmt_duration(remarks)
        return {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': self.get_proxy_image_url(pic) if pic else '',
            'vod_remarks': str(remarks) if remarks else '',
        }

    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else ids
        self._select_best_site()
        self._ensure_session()
        resp = self._api_request('/ht/content/detail', {'contentId': str(did)})
        if not resp or resp.get('code') != 10000:
            return {'list': []}
        detail = resp.get('data', {})
        if not detail:
            return {'list': []}
        vd = detail.get('videoDetail') or {}
        title = (vd.get('title') or detail.get('title') or detail.get('name') or
                 detail.get('videoTitle') or '未知标题')
        pic = (vd.get('img') or vd.get('cover') or vd.get('coverUrl') or
               detail.get('img') or detail.get('cover') or
               detail.get('coverUrl') or detail.get('imageUrl') or '')
        desc = (vd.get('description') or vd.get('desc') or
                detail.get('description') or detail.get('desc') or detail.get('intro') or '')
        duration = vd.get('duration') or detail.get('duration', 0)
        actor = (vd.get('author') or vd.get('actor') or vd.get('actors') or
                 detail.get('actor') or detail.get('actors') or '')
        play_url = (detail.get('playUrl') or detail.get('videoUrl') or
                    detail.get('downUrl') or detail.get('url') or
                    detail.get('m3u8Url') or detail.get('sl') or '')
        vod_play_url = '播放$' + str(did)
        if play_url:
            vod_play_url = '播放$' + play_url
        return {'list': [{
            'vod_id': str(did),
            'vod_name': title,
            'vod_pic': self.get_proxy_image_url(pic) if pic else '',
            'vod_actor': str(actor) if actor else '',
            'vod_director': '',
            'vod_content': desc,
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': self._fmt_duration(duration),
            'vod_play_from': '蜜桃视频',
            'vod_play_url': vod_play_url,
            'type': 'video',
        }]}

    def searchContent(self, key, quick, pg="1"):
        self._select_best_site()
        self._ensure_session()
        pg = int(pg) if str(pg).isdigit() else 1
        resp = self._api_request('/ht/content/search', {
            'keywords': key,
            'pageNo': pg - 1,
            'pageSize': 20,
        })
        if not resp or resp.get('code') != 10000:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        data = resp.get('data', {})
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (data.get('searchList')
                  or data.get('list')
                  or data.get('data')
                  or data.get('videoList')
                  or data.get('records')
                  or data.get('resultList')
                  or data.get('content')
                  or [])
        else:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        if not isinstance(items, list):
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        vod_list = [p for v in items if (p := self._parse_video(v))]
        total_page = int(data.get('totalPage') or 1) if isinstance(data, dict) else max(1, len(vod_list) // 20)
        return {
            'list': vod_list,
            'page': pg,
            'pagecount': total_page,
            'limit': len(vod_list),
            'total': total_page * 20,
        }

    def playerContent(self, flag, id, vipFlags):
        url = id.split('$')[-1]
        if url.startswith('http'):
            return {
                'parse': 0,
                'url': url,
                'jx': 0,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': self.host + '/',
                },
            }
        self._select_best_site()
        self._ensure_session()
        resp = self._api_request('/ht/content/detail', {'contentId': url})
        if not resp or resp.get('code') != 10000:
            return {'parse': 0, 'url': '', 'jx': 0}
        detail = resp.get('data', {})
        play_url = (detail.get('playUrl') or detail.get('videoUrl') or
                    detail.get('downUrl') or detail.get('url') or
                    detail.get('m3u8Url') or detail.get('sl') or '')
        return {
            'parse': 0,
            'url': play_url,
            'jx': 0,
            'header': {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.host + '/',
            },
        }


    def localProxy(self, param):
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
        try:
            # 兼容 Chaquopy Java Map → Python dict
            if not isinstance(param, dict):
                try:
                    param = dict(param)
                except Exception:
                    param = {}
            ptype = str(param.get('type', '')).strip()
            purl = str(param.get('url', '')).strip()
            # 如果传了 type 但不匹配，返回 404
            if ptype and ptype != PROXY_TYPE:
                return [404, 'text/plain', b'not found']
            if not purl:
                return [400, 'text/plain', b'missing url']
            img_url = unquote(purl)
            headers = {
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36'),
                'Referer': self.host + '/',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            r = requests.get(img_url, headers=headers, timeout=TIMEOUT, verify=False)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', b'fetch failed']
            data = r.content
            if not data or len(data) < 8:
                return [404, 'text/plain', b'image too small']
            # 尝试 XOR 0x88 解密
            decoded = bytes(b ^ 0x88 for b in data)
            if decoded[:2] == b'\xff\xd8' or decoded[:4] == b'\x89PNG' or                (len(decoded) >= 12 and decoded[:4] == b'RIFF' and decoded[8:12] == b'WEBP'):
                data = decoded
            # 识别 MIME
            if data[:2] == b'\xff\xd8':
                mime = 'image/jpeg'
            elif data[:4] == b'\x89PNG':
                mime = 'image/png'
            elif len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
                mime = 'image/webp'
            elif data[:4] == b'GIF8':
                mime = 'image/gif'
            else:
                mime = r.headers.get('Content-Type', 'image/jpeg')
                if not mime or not mime.startswith('image/'):
                    mime = 'image/jpeg'
            return [200, mime, data, {'Content-Length': str(len(data))}]
        except Exception:
            return [500, 'text/plain', b'proxy error', {}]

    def proxy(self, param):
        return self.localProxy(param)
