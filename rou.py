# -*- coding: utf-8 -*-
"""
肉視頻 (rou.video) 爬虫 - 最终修复版 v7
核心发现：
1. 日本分类等视频播放入口在 TSR 页面的 ev 字段（base64 + 偏移解码）
2. /api/hls/ 返回 PNG 包装的 m3u8/TS（roUd 自定义块，可能 zlib），需 localProxy 解包
3. sources 通常只有 resolution，没有 url/folder
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
    host = 'https://rou.video'
    cdn_host = 'https://v.rn252.xyz'
    localProxyUrl = 'http://127.0.0.1:UndCover/proxy'
    # 可选：Cloudflare Worker 解包代理（部署 rou_hls_worker.js 后填入）
    # 例：'https://rou-hls.你的账号.workers.dev'
    # 也可通过 init(extend) 传入 JSON：{"worker":"https://..."}
    workerProxy = ''
    # 站点在配置里的 key，用于本地代理 do= 参数（必须与 json 配置 key 一致）
    siteKey = 'rou'
    session = requests.Session()
    _debug = True
    _categories = []
    _home_data = None

    def _log(self, msg):
        if self._debug:
            print(f'[rou] {msg}')

    def getName(self):
        return '肉視頻'

    def isVideoFormat(self, url):
        if not url:
            return False
        return '.m3u8' in url or '.mp4' in url or '.ts' in url or '/api/hls/' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        """ROU HLS PNG 包装代理（Pyramid/UndCover 兼容返回格式）。

        返回值约定（UndCover）：
          [code, contentType, action_or_body, content]
          action.type == 'string' 且 content 有值 → 直接返回文本/二进制
        """
        try:
            if isinstance(param, str):
                raw = param
                typ = 'rou'
            else:
                raw = param.get('url') or param.get('u') or ''
                typ = param.get('type') or 'rou'
            if not raw:
                return [400, 'text/plain', {'type': 'string'}, 'missing url']
            raw = unquote(str(raw))
            if not raw.startswith('http'):
                try:
                    pad = '=' * ((4 - len(raw) % 4) % 4)
                    decoded = base64.urlsafe_b64decode(raw + pad).decode('utf-8', errors='strict')
                    if decoded.startswith('http') or decoded.startswith('/'):
                        raw = decoded
                except Exception:
                    pass
            if raw.startswith('/'):
                raw = self.host + raw

            r = self.session.get(raw, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                'Referer': self.host + '/',
                'Origin': self.host,
            }, timeout=30, verify=False)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', {'type': 'string'}, '']
            body = r.content

            # PNG + roUd：flag&1 → zlib
            if body.startswith(b'\x89PNG\r\n\x1a\n'):
                n = 8
                payload = None
                while n + 12 <= len(body):
                    ln = int.from_bytes(body[n:n + 4], 'big')
                    typ4 = body[n + 4:n + 8]
                    data_start = n + 8
                    if data_start + ln > len(body):
                        break
                    if typ4 == b'roUd':
                        chunk = body[data_start:data_start + ln]
                        if not chunk:
                            break
                        flag = chunk[0]
                        payload = chunk[1:]
                        if flag & 1:
                            import zlib
                            payload = zlib.decompress(payload)
                        break
                    n = data_start + ln + 4
                if payload is None:
                    return [502, 'text/plain', {'type': 'string'}, 'ROU PNG 中没有 roUd 播放数据']
                body = payload

            content = body.decode('utf-8', errors='replace')
            if '#EXTM3U' in content or '#EXT-X-' in content:
                base = raw.rsplit('/', 1)[0] + '/'
                proxy_base = self._proxy_base()

                def proxy_url(u):
                    u = u.strip()
                    if not u or u.startswith('#'):
                        return u
                    absu = urljoin(base, u)
                    # 优先走 Worker；否则本地代理
                    if self.workerProxy:
                        return self.workerProxy.rstrip('/') + '?url=' + quote(absu, safe='')
                    token = base64.urlsafe_b64encode(absu.encode()).decode().rstrip('=')
                    return proxy_base + '&type=media&url=' + quote(token, safe='')

                lines = []
                for line in content.splitlines():
                    s = line.strip()
                    if s and not s.startswith('#'):
                        lines.append(proxy_url(s))
                    elif 'URI="' in line:
                        line = re.sub(
                            r'URI="([^"]+)"',
                            lambda m: 'URI="' + proxy_url(m.group(1)) + '"',
                            line,
                        )
                        lines.append(line)
                    else:
                        lines.append(line)
                content = '\n'.join(lines) + '\n'
                action = {'url': '', 'header': '', 'param': '', 'type': 'string', 'after': ''}
                return [200, 'application/vnd.apple.mpegurl', action, content]

            # 媒体分片：返回二进制
            action = {'url': '', 'header': '', 'param': '', 'type': 'string', 'after': ''}
            return [200, 'application/octet-stream', action, body]
        except Exception as e:
            self._log(f'localProxy异常: {e}')
            return [500, 'text/plain', {'type': 'string'}, str(e)]

    def _proxy_base(self):
        """本地代理前缀：do=站点key & api=python"""
        key = getattr(self, 'siteKey', 'rou') or 'rou'
        base = getattr(self, 'localProxyUrl', 'http://127.0.0.1:UndCover/proxy')
        if 'do=' in base:
            return base
        return f'{base}?do={key}&api=python'


    def _get_headers(self, referer=None):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer or self.host + '/',
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
                    self._log(f'被拦截 [{r.status_code}] 重试 {attempt + 1}')
                    continue
                else:
                    return ''
            except requests.exceptions.Timeout:
                self._log(f'超时重试 {attempt + 1}')
            except Exception as e:
                self._log(f'异常 {e} 重试 {attempt + 1}')
        return ''

    def _extract_next_data(self, html):
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                self._log(f'JSON 解析失败: {e}')
                return None
        return None

    def _print_structure(self, obj, depth=0, max_depth=3, prefix=''):
        if depth > max_depth:
            return
        if isinstance(obj, dict):
            for key in list(obj.keys())[:10]:
                value = obj[key]
                if isinstance(value, (dict, list)):
                    size = len(value)
                    self._log(f'{"  " * depth}{prefix}{key}: ({type(value).__name__}, size={size})')
                    self._print_structure(value, depth + 1, max_depth, prefix)
                else:
                    val_str = str(value)[:50]
                    self._log(f'{"  " * depth}{prefix}{key}: {val_str}')
        elif isinstance(obj, list) and len(obj) > 0:
            self._log(f'{"  " * depth}{prefix}[0]:')
            self._print_structure(obj[0], depth + 1, max_depth, prefix)

    def _find_video_list(self, obj, depth=0, max_depth=6):
        if depth > max_depth or not isinstance(obj, (dict, list)):
            return None
        if isinstance(obj, list):
            if len(obj) > 0 and isinstance(obj[0], dict):
                video_id_keys = ['id', 'vid', 'videoId', '_id', 'slug', 'uuid', 'postId']
                video_name_keys = ['name', 'nameZh', 'title', 'post_title', 'videoName', 'label']
                video_pic_keys = ['coverImageUrl', 'cover', 'poster', 'thumbnail', 'image', 'img', 'pic']
                has_id = any(k in obj[0] for k in video_id_keys)
                has_name = any(k in obj[0] for k in video_name_keys)
                has_pic = any(k in obj[0] for k in video_pic_keys)
                if has_id and (has_name or has_pic):
                    self._log(f'发现视频列表，长度 {len(obj)}, 字段: {list(obj[0].keys())[:8]}')
                    return obj
                play_keys = ['playUrl', 'videoUrl', 'play_url', 'streamUrl', 'm3u8', 'source', 'sources']
                if has_id and any(k in obj[0] for k in play_keys):
                    self._log(f'发现视频列表（含播放地址），长度 {len(obj)}')
                    return obj
            for item in obj:
                result = self._find_video_list(item, depth + 1, max_depth)
                if result:
                    return result
        elif isinstance(obj, dict):
            priority_keys = [
                'videos', 'list', 'items', 'results', 'posts', 'data', 'content',
                'videoList', 'video_list', 'postList', 'records', 'rows', 'entries',
                'latestVideos', 'popularVideos', 'trendingVideos', 'recommendedVideos',
            ]
            for key in priority_keys:
                if key in obj and isinstance(obj[key], list) and len(obj[key]) > 0:
                    if isinstance(obj[key][0], dict):
                        result = self._find_video_list(obj[key], depth + 1, max_depth)
                        if result:
                            return result
            for key, value in obj.items():
                result = self._find_video_list(value, depth + 1, max_depth)
                if result:
                    return result
        return None

    def _find_video_object(self, obj, depth=0, max_depth=6):
        if depth > max_depth or not isinstance(obj, (dict, list)):
            return None
        if isinstance(obj, dict):
            video_id_keys = ['id', 'vid', 'videoId', '_id', 'slug', 'uuid']
            play_keys = ['sources', 'source', 'playUrl', 'videoUrl', 'play_url', 'streamUrl', 'm3u8', 'ref']
            has_id = any(k in obj for k in video_id_keys)
            has_play = any(k in obj for k in play_keys)
            if has_id and has_play:
                return obj
            priority_keys = ['video', 'post', 'item', 'detail', 'data', 'info', 'content']
            for key in priority_keys:
                if key in obj:
                    result = self._find_video_object(obj[key], depth + 1, max_depth)
                    if result:
                        return result
            for key, value in obj.items():
                result = self._find_video_object(value, depth + 1, max_depth)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_video_object(item, depth + 1, max_depth)
                if result:
                    return result
        return None

    def _find_play_url(self, obj, depth=0, max_depth=6):
        if depth > max_depth:
            return None
        if isinstance(obj, str):
            if obj.startswith('http') and (
                '.m3u8' in obj or '.mp4' in obj or '/api/hls/' in obj
            ):
                return obj
            return None
        if isinstance(obj, dict):
            play_keys = [
                'playUrl', 'videoUrl', 'play_url', 'streamUrl', 'm3u8', 'url',
                'src', 'source', 'file', 'link', 'hls', 'play',
            ]
            for key in play_keys:
                if key in obj:
                    result = self._find_play_url(obj[key], depth + 1, max_depth)
                    if result:
                        return result
            for value in obj.values():
                result = self._find_play_url(value, depth + 1, max_depth)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_play_url(item, depth + 1, max_depth)
                if result:
                    return result
        return None

    def _parse_videos_from_html(self, html):
        videos = []
        pattern1 = r'<a[^>]*href="(/v/[^"]+)"[^>]*>(.*?)</a>'
        for m in re.finditer(pattern1, html, re.DOTALL):
            vid_url = m.group(1)
            content = m.group(2)
            vid = vid_url.replace('/v/', '').strip('/')
            title_match = re.search(
                r'<(?:span|p|h\d|div)[^>]*>([^<]{2,100})</(?:span|p|h\d|div)>',
                content,
            )
            title = title_match.group(1).strip() if title_match else vid
            img_match = re.search(
                r'<img[^>]*(?:src|data-src|data-original)="([^"]+)"',
                content,
            )
            pic = img_match.group(1) if img_match else ''
            if pic and pic.startswith('/'):
                pic = self.host + pic
            if vid and title:
                videos.append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': '',
                })
        if videos:
            self._log(f'从HTML方法1解析到 {len(videos)} 个视频')
            return videos
        pattern2 = r'"id"\s*:\s*"([^"]+)"[^}]*"name"\s*:\s*"([^"]+)"'
        for m in re.finditer(pattern2, html):
            vid = m.group(1)
            name = m.group(2)
            if len(name) > 1 and not name.startswith('http'):
                videos.append({
                    'vod_id': vid,
                    'vod_name': name,
                    'vod_pic': '',
                    'vod_remarks': '',
                })
        if videos:
            self._log(f'从HTML方法2解析到 {len(videos)} 个视频')
            return videos
        pattern3 = r'href="(/v/[^"]+)"[^>]*title="([^"]*)"'
        for m in re.finditer(pattern3, html):
            vid = m.group(1).replace('/v/', '').strip('/')
            title = m.group(2)
            if vid and title:
                videos.append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': '',
                    'vod_remarks': '',
                })
        if videos:
            self._log(f'从HTML方法3解析到 {len(videos)} 个视频')
        return videos

    def _parse_categories_from_home(self, html):
        cats = []
        pattern1 = r'<button[^>]*data-section="([^"]+)"[^>]*>([^<]+)</button>'
        for m in re.finditer(pattern1, html):
            section_id = m.group(1)
            name = m.group(2).strip()
            if name and len(name) < 20:
                cats.append({
                    'type_id': name,
                    'type_name': name,
                    'section': section_id,
                })
        if cats:
            return cats
        if self._home_data:
            def find_categories(obj, depth=0):
                if depth > 5 or not isinstance(obj, (dict, list)):
                    return None
                if isinstance(obj, list) and len(obj) > 0:
                    if isinstance(obj[0], dict):
                        cat_keys = ['name', 'slug', 'id', 'path', 'title']
                        match = sum(1 for k in cat_keys if k in obj[0])
                        if match >= 2:
                            return obj
                if isinstance(obj, dict):
                    for key in ['categories', 'categoryList', 'sections', 'nav', 'navigation', 'tabs']:
                        if key in obj:
                            result = find_categories(obj[key], depth + 1)
                            if result:
                                return result
                    for value in obj.values():
                        result = find_categories(value, depth + 1)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = find_categories(item, depth + 1)
                        if result:
                            return result
                return None

            cat_list = find_categories(self._home_data)
            if cat_list:
                for item in cat_list:
                    name = item.get('name') or item.get('title')
                    tid = item.get('slug') or item.get('id') or item.get('path') or name
                    if name:
                        cats.append({
                            'type_id': str(tid),
                            'type_name': str(name),
                        })
                if cats:
                    return cats
        return [
            {'type_id': '國產AV', 'type_name': '國產AV'},
            {'type_id': '探花', 'type_name': '探花'},
            {'type_id': '自拍流出', 'type_name': '自拍流出'},
            {'type_id': 'OnlyFans', 'type_name': 'OnlyFans'},
            {'type_id': '日本', 'type_name': '日本'},
            {'type_id': '麻豆傳媒', 'type_name': '麻豆傳媒'},
        ]

    def init(self, extend=''):
        self.session.headers.update(self._get_headers())
        # extend 可传 worker 地址或 JSON
        if extend:
            try:
                if isinstance(extend, str) and extend.strip().startswith('{'):
                    cfg = json.loads(extend)
                    if cfg.get('worker'):
                        self.workerProxy = str(cfg['worker']).rstrip('/')
                    if cfg.get('key'):
                        self.siteKey = str(cfg['key'])
                    if cfg.get('siteKey'):
                        self.siteKey = str(cfg['siteKey'])
                elif isinstance(extend, str) and extend.startswith('http'):
                    self.workerProxy = extend.rstrip('/')
            except Exception as e:
                self._log(f'init extend 解析失败: {e}')
        html = self._fetch(self.host + '/home')
        if html:
            self._home_data = self._extract_next_data(html)
            self._categories = self._parse_categories_from_home(html)
            self._log(f'分类加载完成，共 {len(self._categories)} 个')
            if self._home_data:
                self._log('__NEXT_DATA__ 结构:')
                self._print_structure(self._home_data, max_depth=3)

    def _convert_video_items(self, items):
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            vid = (
                item.get('id') or item.get('vid') or item.get('videoId')
                or item.get('_id') or item.get('slug') or item.get('uuid')
            )
            if not vid:
                continue
            name = (
                item.get('name') or item.get('nameZh') or item.get('title')
                or item.get('post_title') or item.get('videoName') or str(vid)
            )
            pic = (
                item.get('coverImageUrl') or item.get('cover') or item.get('poster')
                or item.get('thumbnail') or item.get('image') or item.get('img') or ''
            )
            remark = ''
            duration = item.get('duration') or item.get('length') or item.get('time')
            if duration:
                try:
                    seconds = int(float(duration))
                    mins = seconds // 60
                    secs = seconds % 60
                    remark = f'{mins}分{secs}秒' if mins > 0 else f'{secs}秒'
                except Exception:
                    remark = str(duration)
            if not remark and 'tags' in item and isinstance(item['tags'], list):
                remark = ', '.join(str(t) for t in item['tags'][:3])
            result.append({
                'vod_id': str(vid),
                'vod_name': str(name),
                'vod_pic': str(pic),
                'vod_remarks': remark,
            })
        return result

    def homeContent(self, filter=False):
        try:
            if not self._home_data:
                self.init()
            cats = self._categories
            items = []
            if self._home_data:
                video_list = self._find_video_list(self._home_data)
                if video_list:
                    items = self._convert_video_items(video_list[:20])
            if not items:
                self._log('__NEXT_DATA__ 中未找到视频，尝试从 HTML 解析')
                html = self._fetch(self.host + '/home')
                if html:
                    items = self._parse_videos_from_html(html)[:20]
            self._log(f'homeContent 返回 {len(cats)} 分类, {len(items)} 视频')
            return {'class': cats, 'list': items}
        except Exception as e:
            self._log(f'homeContent 异常: {e}')
            import traceback
            traceback.print_exc()
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        items = []
        if self._home_data:
            video_list = self._find_video_list(self._home_data)
            if video_list:
                items = self._convert_video_items(video_list[:20])
        if not items:
            html = self._fetch(self.host + '/home')
            if html:
                items = self._parse_videos_from_html(html)[:20]
        return {'list': items}

    def categoryContent(self, tid, pg, filter=False, extend=''):
        try:
            page = int(pg) if pg else 1
            tid_encoded = quote(tid, safe='')
            urls_to_try = [
                f'{self.host}/t/{tid_encoded}',
                f'{self.host}/t/{tid}',
                f'{self.host}/tag/{tid_encoded}',
            ]
            html = ''
            for url in urls_to_try:
                if page > 1:
                    url += f'?order=createdAt&page={page}'
                self._log(f'请求分类页: {url}')
                html = self._fetch(url, referer=self.host)
                if html:
                    break
            if not html:
                return {'list': [], 'page': page, 'pagecount': 1}
            data = self._extract_next_data(html)
            items = []
            total_pages = page
            if data:
                video_list = self._find_video_list(data)
                if video_list:
                    items = self._convert_video_items(video_list)
                    self._log(f'分类页从JSON解析到 {len(items)} 个视频')
            if not items:
                items = self._parse_videos_from_html(html)
                if items:
                    self._log(f'分类页从HTML解析到 {len(items)} 个视频')
            if f'page={page + 1}' in html or f'"page":{page + 1}' in html:
                total_pages = page + 1
            return {'list': items, 'page': page, 'pagecount': total_pages}
        except Exception as e:
            self._log(f'categoryContent 异常: {e}')
            import traceback
            traceback.print_exc()
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}

    def detailContent(self, ids):
        try:
            vid = str(ids[0] if isinstance(ids, list) else ids)
            url = f'{self.host}/v/{vid}'
            self._log(f'请求详情页: {url}')
            html = self._fetch(url, referer=self.host)
            if not html:
                return {'list': []}

            title = vid
            pic = ''
            video_data = self._extract_tsr_video_data(html)
            if video_data:
                title = video_data.get('nameZh') or video_data.get('name', vid)
                pic = video_data.get('coverImageUrl', '')
            if title == vid:
                title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                if title_match:
                    title = title_match.group(1).strip()
            if not pic:
                og_image = re.search(
                    r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
                    html,
                )
                if og_image:
                    pic = og_image.group(1)

            play_url = self._get_real_play_url(vid, html)

            if not play_url:
                self._log('未找到播放地址，使用解析模式')
                play_url = url
                needs_parse = True
            else:
                needs_parse = False

            vod_play_from = '解析' if needs_parse else '播放'
            flag = f'{vod_play_from}${play_url}'

            self._log(f'详情: {title}, 播放地址: {play_url}, 需要解析: {needs_parse}')
            return {'list': [{
                'vod_id': vid,
                'vod_name': str(title),
                'vod_pic': str(pic),
                'vod_play_from': vod_play_from,
                'vod_play_url': flag,
            }]}
        except Exception as e:
            self._log(f'detailContent 异常: {e}')
            import traceback
            traceback.print_exc()
            return {'list': []}

    # ========== ROU 新版播放数据：TSR / pageProps.ev ==========
    def _decode_rou_ev(self, ev):
        """解码 ROU 的 ev 载荷。

        日本分类等视频不把播放地址放进 sources.url，而是放在 ev.d 中，
        用 ev.k 做逐字节偏移后 JSON.parse。
        JS 逻辑：atob(d) 后每个字符 charCode - k。
        """
        if not isinstance(ev, dict):
            return None
        d = ev.get('d')
        k = ev.get('k')
        if not d or k is None:
            return None
        try:
            raw = base64.b64decode(d)
            decoded = ''.join(chr((b - int(k)) & 0xFFFF) for b in raw)
            return json.loads(decoded)
        except Exception as e:
            self._log(f'ROU ev 解码失败: {e}')
            return None

    def _extract_ev_from_html(self, html):
        """从页面 HTML（TSR 流式或 JSON）提取 ev={d,k}。

        当前站点详情页使用 TanStack Router 流式 SSR，形如：
          ev:$R[92]={d:"....",k:20}
        也兼容 "ev":{"d":"...","k":20} 的 JSON 写法。
        """
        if not html:
            return None
        m = re.search(r'ev(?::\$R\[\d+\])?=\{d:"([^"]+)",k:(\d+)\}', html)
        if m:
            return {'d': m.group(1), 'k': int(m.group(2))}
        m = re.search(r'ev(?::\$R\[\d+\])?=\{k:(\d+),d:"([^"]+)"\}', html)
        if m:
            return {'d': m.group(2), 'k': int(m.group(1))}
        m = re.search(
            r'"ev"\s*:\s*\{\s*"d"\s*:\s*"([^"]+)"\s*,\s*"k"\s*:\s*(\d+)\s*\}',
            html,
        )
        if m:
            return {'d': m.group(1), 'k': int(m.group(2))}
        return None

    def _normalize_play_url(self, video_url):
        if not video_url:
            return None
        video_url = str(video_url).replace('\\/', '/')
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        elif video_url.startswith('/'):
            video_url = self.host + video_url
        return video_url

    def _extract_ev_video_url(self, html):
        """从页面 ev 字段提取真实播放入口（日本分类核心路径）。"""
        try:
            ev = self._extract_ev_from_html(html)
            if not ev:
                data = self._extract_next_data(html)
                if isinstance(data, dict):
                    page_props = data.get('props', {}).get('pageProps', {})
                    if isinstance(page_props.get('ev'), dict):
                        ev = page_props['ev']

            if not ev:
                self._log('页面中未找到 ev 播放载荷')
                return None

            decoded = self._decode_rou_ev(ev)
            if not isinstance(decoded, dict):
                return None

            video_url = (
                decoded.get('videoUrl')
                or decoded.get('url')
                or decoded.get('m3u8')
                or decoded.get('hls')
            )
            if not video_url:
                self._log(f'ev 解码成功但无 videoUrl: {list(decoded.keys())}')
                return None

            video_url = self._normalize_play_url(video_url)
            self._log(f'从 ev 获取播放入口: {video_url}')
            if self._is_valid_play_url(video_url):
                return video_url
        except Exception as e:
            self._log(f'ev 播放地址提取失败: {e}')
        return None

    # ========== TSR 数据提取 ==========
    def _extract_tsr_video_data(self, html):
        """从 TanStack Router 流式SSR中提取视频数据"""
        video_match = re.search(r'video:\$R\[\d+\]=\{', html)
        if not video_match:
            video_match = re.search(r'l:\$R\[\d+\]=\{[^}]*video:', html)
            if not video_match:
                self._log('未找到 TSR video 对象')
                return None

        start = video_match.end() - 1
        depth = 0
        end = start
        for i in range(start, min(start + 10000, len(html))):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break

        obj_str = html[start:end + 1]
        self._log(f'TSR video obj length: {len(obj_str)}')

        video = {}
        for m in re.finditer(r'(\w+):"([^"]*)"', obj_str):
            key, val = m.group(1), m.group(2)
            if key in [
                'id', 'name', 'nameZh', 'ref', 'coverImageUrl', 'slug', 'type',
                'source', 'embed', 'player', 'iframe', 'url', 'src', 'file',
                'playUrl', 'videoUrl', 'streamUrl', 'm3u8', 'folder',
            ]:
                video[key] = val

        dur_match = re.search(r'duration:([\d.]+)', obj_str)
        if dur_match:
            video['duration'] = float(dur_match.group(1))

        sources_match = re.search(r'sources:\$R\[\d+\]=\[', obj_str)
        if not sources_match:
            sources_match = re.search(r'sources:\[', obj_str)

        if sources_match:
            src_start = sources_match.end() - 1
            depth = 0
            src_end = src_start
            for i in range(src_start, min(src_start + 5000, len(obj_str))):
                if obj_str[i] == '[':
                    depth += 1
                elif obj_str[i] == ']':
                    depth -= 1
                    if depth == 0:
                        src_end = i
                        break
            src_str = obj_str[src_start:src_end + 1]

            sources = []
            i = 0
            while i < len(src_str):
                if src_str[i] == '{':
                    d = 0
                    j = i
                    while j < len(src_str):
                        if src_str[j] == '{':
                            d += 1
                        elif src_str[j] == '}':
                            d -= 1
                            if d == 0:
                                break
                        j += 1
                    if j < len(src_str):
                        s = src_str[i + 1:j]
                        source = {}
                        for fm in re.finditer(r'(\w+):"([^"]*)"', s):
                            fk, fv = fm.group(1), fm.group(2)
                            source[fk] = fv
                        for fm in re.finditer(r'(\w+):(\d+)', s):
                            fk, fv = fm.group(1), fm.group(2)
                            if fk not in source:
                                try:
                                    source[fk] = int(fv)
                                except Exception:
                                    source[fk] = fv
                        if source:
                            sources.append(source)
                        i = j + 1
                    else:
                        break
                else:
                    i += 1

            if sources:
                video['sources'] = sources
                self._log(f'提取到 {len(sources)} 个 sources')
                for s in sources:
                    self._log(f'  source: {s}')

        self._log(f'提取的 video_data keys: {list(video.keys())}')
        return video if video else None

    def _is_valid_play_url(self, url):
        if not url:
            return False
        url_lower = url.lower()
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico']
        for ext in image_exts:
            if url_lower.endswith(ext):
                return False
        if '.m3u8.jpg' in url_lower or '.m3u8.png' in url_lower:
            return False
        # ROU 当前部分（尤其日本分类）使用 /api/hls/... 作为播放入口
        if '/api/hls/' in url_lower:
            return True
        video_exts = ['.m3u8', '.mp4', '.ts', '.flv', '.mkv', '.avi', '.m4s']
        for ext in video_exts:
            if ext in url_lower:
                return True
        return False

    def _build_cdn_url_from_folder(self, folder, resolution=720):
        """根据 folder 字段构造 CDN 播放地址（兼容旧数据）"""
        if not folder:
            return None

        possible_urls = [
            f'{self.cdn_host}/hls/{folder}/index.m3u8',
            f'{self.cdn_host}/hls/{folder}/playlist.m3u8',
            f'{self.cdn_host}/hls/{folder}/master.m3u8',
            f'{self.cdn_host}/video/{folder}/index.m3u8',
            f'{self.cdn_host}/video/{folder}/playlist.m3u8',
            f'{self.cdn_host}/m/{folder}/index.m3u8',
            f'{self.cdn_host}/m/{folder}/playlist.m3u8',
            f'{self.cdn_host}/{folder}/index.m3u8',
            f'{self.cdn_host}/{folder}/playlist.m3u8',
            f'{self.cdn_host}/hls/{folder}/video.mp4',
            f'{self.cdn_host}/video/{folder}/video.mp4',
        ]

        for url in possible_urls:
            try:
                self._log(f'尝试 CDN URL: {url}')
                r = self.session.head(
                    url,
                    headers=self._get_headers(),
                    timeout=10,
                    verify=False,
                    allow_redirects=True,
                )
                if r.status_code == 200:
                    content_type = r.headers.get('Content-Type', '')
                    self._log(f'  状态: 200, Content-Type: {content_type}')
                    if 'video' in content_type or 'mpegurl' in content_type or 'octet-stream' in content_type:
                        return url
                    if 'text' in content_type and '.m3u8' in url:
                        return url
            except Exception as e:
                self._log(f'  失败: {e}')
        return None

    def _get_play_url_from_ref(self, ref_url, depth=0):
        if not ref_url or depth > 3:
            return None
        try:
            self._log(f'尝试从ref获取 (depth={depth}): {ref_url}')
            html = self._fetch(ref_url, referer=self.host)
            if not html:
                return None

            m3u8_matches = re.findall(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)', html)
            for url in m3u8_matches:
                url = url.rstrip('",.;)')
                if self._is_valid_play_url(url):
                    self._log(f'找到有效m3u8: {url}')
                    return url

            preview_patterns = [
                r'(https?://[^\s"\'<>]+/videos_screenshots/[^\s"\'<>]+/preview\.m3u8\.jpg)',
                r'(https?://[^\s"\'<>]+/screenshots/[^\s"\'<>]+/preview\.m3u8\.jpg)',
            ]
            for pp in preview_patterns:
                pm = re.search(pp, html)
                if pm:
                    preview_url = pm.group(1)
                    real_urls = [
                        preview_url.replace('/videos_screenshots/', '/videos/').replace(
                            '/preview.m3u8.jpg', '.m3u8'
                        ),
                        preview_url.replace('.m3u8.jpg', '.m3u8'),
                    ]
                    for real_url in real_urls:
                        try:
                            r = self.session.head(
                                real_url,
                                headers=self._get_headers(ref_url),
                                timeout=10,
                                verify=False,
                                allow_redirects=True,
                            )
                            if r.status_code == 200:
                                self._log(f'从预览图推断: {real_url}')
                                return real_url
                        except Exception:
                            continue

            for tag_pat in [r'<video[^>]*src="([^"]+)"', r'<source[^>]*src="([^"]+)"']:
                src_match = re.search(tag_pat, html)
                if src_match:
                    src = src_match.group(1)
                    src = 'https:' + src if src.startswith('//') else src
                    if self._is_valid_play_url(src):
                        return src

            json_patterns = [
                r'"videoUrl"\s*:\s*"([^"]+)"',
                r'"playUrl"\s*:\s*"([^"]+)"',
                r'"streamUrl"\s*:\s*"([^"]+)"',
                r'"file"\s*:\s*"([^"]+)"',
                r'"src"\s*:\s*"([^"]+)"',
                r'"hls"\s*:\s*"([^"]+)"',
                r'"m3u8"\s*:\s*"([^"]+)"',
            ]
            for pattern in json_patterns:
                matches = re.findall(pattern, html)
                for url in matches:
                    url = url.replace('\\/', '/')
                    if url.startswith('//'):
                        url = 'https:' + url
                    if self._is_valid_play_url(url):
                        self._log(f'从JSON找到: {url}')
                        return url

            iframe_matches = re.findall(r'<iframe[^>]*src="([^"]+)"', html)
            for iframe_url in iframe_matches:
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                if iframe_url.startswith('http') and 'jable.tv' not in iframe_url and 'rou.video' not in iframe_url:
                    self._log(f'找到iframe，递归获取: {iframe_url}')
                    result = self._get_play_url_from_ref(iframe_url, depth + 1)
                    if result:
                        return result

        except Exception as e:
            self._log(f'ref获取失败: {e}')
        return None

    def _get_real_play_url(self, vid, html):
        """获取真实播放地址 - 多策略。

        优先读取 ROU 新版 TSR/ev.videoUrl；
        这是日本分类当前常见的播放数据位置。
        """
        # 策略0：ROU ev 载荷（日本分类等当前主流入口，TSR 流式页面）
        self._log('策略0: 从页面 ev 提取播放入口')
        ev_play_url = self._extract_ev_video_url(html)
        if ev_play_url:
            return ev_play_url

        # 策略0b：用 video id 直接拼 /api/hls/{vid}
        if vid:
            api_hls = f'{self.host}/api/hls/{vid}'
            self._log(f'策略0b: 尝试直接 /api/hls/ 入口 {api_hls}')
            try:
                r = self.session.head(
                    api_hls,
                    headers=self._get_headers(self.host + '/'),
                    timeout=10,
                    verify=False,
                    allow_redirects=True,
                )
                if r.status_code == 200:
                    self._log(f'策略0b 命中: {api_hls}')
                    return api_hls
            except Exception as e:
                self._log(f'策略0b 失败: {e}')

        video_data = self._extract_tsr_video_data(html)

        if not video_data:
            self._log('TSR 数据提取失败')
            return None

        # 策略1: 从 sources 中提取 url/file/src
        self._log('策略1: 从 sources 提取直接 URL')
        if video_data.get('sources'):
            for source in video_data['sources']:
                if isinstance(source, dict):
                    for fk in ['url', 'file', 'src', 'playUrl', 'link']:
                        if source.get(fk):
                            url = source[fk]
                            if url.startswith('//'):
                                url = 'https:' + url
                            if self._is_valid_play_url(url):
                                self._log(f'从sources获取: {url}')
                                return url

        # 策略2: 从 sources 中的 folder 构造 CDN 地址
        self._log('策略2: 从 folder 构造 CDN 地址')
        if video_data.get('sources'):
            for source in video_data['sources']:
                if isinstance(source, dict) and source.get('folder'):
                    folder = source['folder']
                    resolution = source.get('resolution', 720)
                    self._log(f'尝试从 folder 构造: {folder}, resolution: {resolution}')
                    url = self._build_cdn_url_from_folder(folder, resolution)
                    if url:
                        return url

        # 策略3: 使用 video_id 构造 CDN 地址
        self._log('策略3: 使用 video_id 构造 CDN 地址')
        url = self._build_cdn_url_from_folder(vid, 720)
        if url:
            return url

        # 策略4: 从 ref (jable.tv) 获取
        self._log('策略4: 从 ref (jable.tv) 获取')
        if video_data.get('ref'):
            ref_url = video_data['ref']
            if ref_url.startswith('//'):
                ref_url = 'https:' + ref_url
            if ref_url.startswith('http'):
                play_url = self._get_play_url_from_ref(ref_url)
                if play_url and self._is_valid_play_url(play_url):
                    return play_url

        # 策略5: 从HTML搜索m3u8
        self._log('策略5: 从 HTML 搜索 m3u8')
        m3u8_matches = re.findall(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)', html)
        for url in m3u8_matches:
            url = url.rstrip('",.;)')
            if self._is_valid_play_url(url):
                return url

        # 策略6: 从 __NEXT_DATA__ 中递归搜索
        self._log('策略6: 从 __NEXT_DATA__ 递归搜索')
        next_data = self._extract_next_data(html)
        if next_data:
            play_url = self._find_play_url(next_data)
            if play_url and self._is_valid_play_url(play_url):
                self._log(f'从__NEXT_DATA__找到: {play_url}')
                return play_url

        return None

    def playerContent(self, flag, id, vipFlags=None):
        # ROU 的 /api/hls/ 是 PNG 包装 HLS，必须经代理解包。
        # 优先 Cloudflare Worker；否则走本地 localProxy。
        play = str(id)
        if '/api/hls/' in play.lower():
            if self.workerProxy:
                proxy_url = self.workerProxy.rstrip('/') + '?url=' + quote(play, safe='')
            else:
                proxy_base = self._proxy_base()
                token = base64.urlsafe_b64encode(play.encode()).decode().rstrip('=')
                proxy_url = proxy_base + '&type=rou&url=' + quote(token, safe='')
            self._log(f'playerContent 代理: {proxy_url[:120]}...')
            return {
                'parse': 0,
                'playUrl': '',
                'url': proxy_url,
                'header': {
                    'Referer': self.host + '/',
                    'User-Agent': 'Mozilla/5.0',
                },
                'contentType': 'application/vnd.apple.mpegurl',
            }
        needs_parse = (flag == '解析')
        return {
            'parse': 1 if needs_parse else 0,
            'url': play,
            'header': {
                'Referer': self.host,
                'User-Agent': 'Mozilla/5.0',
            },
        }

    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if pg else 1
            urls_to_try = [
                f'{self.host}/search?keyword={quote(key)}&page={page}',
                f'{self.host}/search?q={quote(key)}&page={page}',
                f'{self.host}/search/{quote(key)}?page={page}',
            ]
            items = []
            for url in urls_to_try:
                self._log(f'尝试搜索: {url}')
                html = self._fetch(url, referer=self.host)
                if not html:
                    continue
                data = self._extract_next_data(html)
                if data:
                    video_list = self._find_video_list(data)
                    if video_list:
                        items = self._convert_video_items(video_list)
                        break
                if not items:
                    items = self._parse_videos_from_html(html)
                    if items:
                        break
            return {
                'list': items,
                'page': page,
                'pagecount': page + 1 if items else 1,
            }
        except Exception as e:
            self._log(f'searchContent 异常: {e}')
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}
