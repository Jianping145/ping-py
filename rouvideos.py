# -*- coding: utf-8 -*-
"""
肉視頻 (rou.video) 爬虫 - 最终修复版 v7
核心发现：日本/麻豆播放入口在 TSR HTML 的 ev 中，解码得 /api/hls/{vid}；
该地址与分片均为 PNG+roUd 包装，需 localProxy 解包。
修复：
1. 顶层 import base64 / zlib；PNG 魔数用真实字节
2. 从 TSR HTML 提取 ev（不再依赖 __NEXT_DATA__）
3. localProxy 解码 urlsafe_b64 token；分片解包后 Content-Type=video/mp2t
4. 代理入口改用 getProxyUrl()（适配 T4/FongMi），禁止写死 UndCover
"""
import sys
import re
import json
import base64
import zlib
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
    session = requests.Session()
    _debug = True
    _categories = []
    _home_data = None

    def _log(self, msg):
        if self._debug:
            print(f'[rou] {msg}')

    def _get_proxy_base(self):
        """获取壳提供的本地代理入口。

        T4 / FongMi / Pyramid 都应由 getProxyUrl() 注入，禁止写死 UndCover。
        返回值通常已带 ?do=py，后续参数用 & 拼接。
        """
        try:
            if hasattr(self, 'getProxyUrl') and callable(self.getProxyUrl):
                base = self.getProxyUrl()
                if base:
                    return str(base).rstrip('&?')
        except Exception as e:
            self._log(f'getProxyUrl 失败: {e}')
        # 兼容少数旧壳
        for attr in ('t4_api', 'localProxyUrl'):
            v = getattr(self, attr, None)
            if v:
                return str(v).rstrip('&?')
        return 'http://127.0.0.1:9978/proxy?do=py'

    def _make_proxy_url(self, typ, real_url):
        """构造走 localProxy 的播放/分片地址。"""
        proxy_base = self._get_proxy_base()
        token = base64.urlsafe_b64encode(str(real_url).encode()).decode().rstrip('=')
        sep = '&' if '?' in proxy_base else '?'
        return f'{proxy_base}{sep}type={quote(str(typ), safe="")}&url={quote(token, safe="")}'

    def getName(self):
        return '肉視頻'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return (
            '.m3u8' in u or '.mp4' in u or '.ts' in u
            or '/api/hls/' in u
            or 'type=rou' in u
            or 'type=media' in u
            or 'do=py' in u
        )

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        """ROU HLS PNG 包装代理。

        日本分类当前的 /api/hls/ 返回的不是普通 m3u8/TS，而是 PNG，
        真正的播放数据放在自定义 roUd chunk 中。原生播放器无法直接播放
        这种 PNG 包装，所以这里解包，并把 m3u8 中的媒体/密钥 URL 再代理一次。
        """
        try:
            if isinstance(param, str):
                # 兼容少数运行环境直接传字符串
                raw = param
                typ = 'rou'
            else:
                raw = param.get('url') or param.get('u') or ''
                typ = param.get('type') or 'rou'
            if not raw:
                return [400, 'text/plain', '', '']
            raw = unquote(str(raw))

            # playerContent / m3u8 重写传入的是 urlsafe_b64(真实URL)，需先解码
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
                'Origin': self.host,
            }, timeout=30, verify=False)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', '', '']
            body = r.content

            # PNG + roUd 自定义块：flag&1 时 payload 为 zlib/deflate。
            # 注意：必须是真实 PNG 魔数字节，不能写成转义字符串。
            if body.startswith(b'\x89PNG\r\n\x1a\n'):
                n = 8
                payload = None
                while n + 12 <= len(body):
                    ln = int.from_bytes(body[n:n+4], 'big')
                    typ4 = body[n+4:n+8]
                    data_start = n + 8
                    if data_start + ln > len(body):
                        break
                    if typ4 == b'roUd':
                        chunk = body[data_start:data_start+ln]
                        if not chunk:
                            break
                        flag = chunk[0]
                        payload = chunk[1:]
                        if flag & 1:
                            payload = zlib.decompress(payload)
                        break
                    n = data_start + ln + 4
                if payload is None:
                    return [502, 'text/plain', 'ROU PNG 中没有 roUd 播放数据', '']
                body = payload

            # m3u8：把绝对/相对媒体 URI 改成同一 localProxy 的媒体代理。
            content = body.decode('utf-8', errors='replace')
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
                    # 普通 TS/fMP4 segment URI
                    if s and not s.startswith('#'):
                        lines.append(proxy_url(s))
                    elif 'URI="' in line:
                        # EXT-X-KEY 等标签中的 URI
                        line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + proxy_url(m.group(1)) + '"', line)
                        lines.append(line)
                    else:
                        lines.append(line)
                content = '\n'.join(lines) + '\n'
                return [200, 'application/vnd.apple.mpegurl', content, '']

            # 媒体片段/密钥等：返回解包后的原始二进制。
            # PNG 解包后的 TS 不能再带 image/png，否则部分播放器拒播。
            ctype = r.headers.get('Content-Type', 'application/octet-stream') or 'application/octet-stream'
            if isinstance(body, (bytes, bytearray)) and body[:1] == b'G':
                ctype = 'video/mp2t'
            elif isinstance(body, (bytes, bytearray)) and body.startswith(b'\x00\x00\x00') and b'ftyp' in body[:32]:
                ctype = 'video/mp4'
            elif 'image/' in ctype.lower() and isinstance(body, (bytes, bytearray)) and not body.startswith(b'\x89PNG'):
                ctype = 'application/octet-stream'
            return [200, ctype, body, '']
        except Exception as e:
            self._log(f'localProxy异常: {e}')
            return [500, 'text/plain', str(e), '']

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

    def _extract_next_data(self, html):
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
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
                    self._log(f'{"  "*depth}{prefix}{key}: ({type(value).__name__}, size={size})')
                    self._print_structure(value, depth + 1, max_depth, prefix)
                else:
                    val_str = str(value)[:50]
                    self._log(f'{"  "*depth}{prefix}{key}: {val_str}')
        elif isinstance(obj, list) and len(obj) > 0:
            self._log(f'{"  "*depth}{prefix}[0]:')
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
                'latestVideos', 'popularVideos', 'trendingVideos', 'recommendedVideos'
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
            play_keys = ['playUrl', 'videoUrl', 'play_url', 'streamUrl', 'm3u8', 'url', 'src', 'source', 'file', 'link', 'hls', 'play']
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

    def _parse_videos_from_tsr(self, html):
        """从 TSR 流提取视频卡片（含系列页 episode 结构）。"""
        videos = []
        seen = set()
        # id + name + 可选 coverImageUrl / episode / duration
        for m in re.finditer(
            r'id:"([a-z0-9]+)",name:"([^"]+)"(?:,episode:(\d+))?(?:,duration:([\d.]+))?(?:[^}]{0,400}?coverImageUrl:"([^"]+)")?',
            html,
        ):
            vid, name, ep, dur, pic = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or ''
            # 过滤系列本体（有 episodeCount 无 episode 的大对象已用 name 作系列名，视频有 episode 或 /v/ 关联）
            if vid in seen:
                continue
            # 跳过明显是系列而非单集：后续还有 episodeCount 且无 episode 字段的由 name 判断
            ctx = html[m.start():m.start() + 120]
            if 'episodeCount:' in ctx and 'episode:' not in ctx[:80]:
                continue
            seen.add(vid)
            remark = ''
            if ep:
                remark = f'第{ep}集'
            elif dur:
                try:
                    sec = int(float(dur))
                    remark = f'{sec // 60}分{sec % 60}秒' if sec >= 60 else f'{sec}秒'
                except Exception:
                    pass
            videos.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remark,
            })
        if videos:
            self._log(f'从TSR解析到 {len(videos)} 个视频')
        return videos

    def _parse_videos_from_html(self, html):
        videos = self._parse_videos_from_tsr(html)
        if videos:
            return videos
        videos = []
        pattern1 = r'<a[^>]*href="(/v/[^"]+)"[^>]*>(.*?)</a>'
        for m in re.finditer(pattern1, html, re.DOTALL):
            vid_url = m.group(1)
            content = m.group(2)
            vid = vid_url.replace('/v/', '').strip('/')
            title_match = re.search(r'<(?:span|p|h\d|div)[^>]*>([^<]{2,100})</(?:span|p|h\d|div)>', content)
            title = title_match.group(1).strip() if title_match else vid
            img_match = re.search(r'<img[^>]*(?:src|data-src|data-original)="([^"]+)"', content)
            pic = img_match.group(1) if img_match else ''
            if pic and pic.startswith('/'):
                pic = self.host + pic
            if vid and title:
                videos.append({
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': ''
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
                    'vod_remarks': ''
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
                    'vod_remarks': ''
                })
        if videos:
            self._log(f'从HTML方法3解析到 {len(videos)} 个视频')
        return videos

    def _parse_tags_from_cat(self, html):
        """从 /cat 提取全部标签 [{type_id,type_name}, ...]。"""
        tags = []
        seen = set()
        if not html:
            return tags
        for m in re.finditer(r'href="/t/([^"#?]+)"', html):
            tid = unquote(m.group(1)).strip()
            if not tid or tid in seen:
                continue
            tail = html[m.end():m.end() + 180]
            tm = re.search(r'>([^<]{1,40})<', tail)
            name = (tm.group(1).strip() if tm else tid)
            if name in ('更多 →', '更多', ''):
                name = tid
            seen.add(tid)
            tags.append({'type_id': tid, 'type_name': name})
        return tags

    def _parse_series_from_page(self, html):
        """从 /series 提取系列 [{id,name}, ...]。"""
        series = []
        if not html:
            return series
        m = re.search(r'list:\$R\[\d+\]=\[', html)
        blob = ''
        if m:
            start = m.end() - 1
            depth = 0
            end = start
            for i in range(start, min(start + 80000, len(html))):
                if html[i] == '[':
                    depth += 1
                elif html[i] == ']':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            blob = html[start:end + 1]
        else:
            blob = html
        for om in re.finditer(r'\{id:"([a-z0-9]+)",name:"([^"]*)"[^}]*?nameZh:"([^"]*)"', blob):
            sid, name, name_zh = om.group(1), om.group(2), om.group(3)
            series.append({'id': sid, 'name': name_zh or name or sid})
        if not series:
            ids = re.findall(r'id:"([a-z0-9]{20,})"', blob)
            names = re.findall(r'nameZh:"([^"]+)"', blob) or re.findall(r'name:"([^"]+)"', blob)
            for i, sid in enumerate(ids):
                series.append({'id': sid, 'name': names[i] if i < len(names) else sid})
        return series

    def _order_filter(self):
        return {
            'key': 'order',
            'name': '排序',
            'value': [
                {'n': '最新', 'v': 'createdAt'},
                {'n': '最热', 'v': 'likeCount'},
                {'n': '播放', 'v': 'viewCount'},
            ],
        }

    def _build_filters(self, tags, series):
        """多维筛选：主分类共用排序；标签/系列/厂商有独立维度。"""
        tag_values = [{'n': '全部', 'v': ''}] + [
            {'n': t['type_name'], 'v': t['type_id']} for t in tags
        ]
        series_values = [{'n': '全部', 'v': ''}] + [
            {'n': s['name'], 'v': s['id']} for s in series
        ]
        group_keywords = {
            '國產AV': ['國產', '麻豆', '果凍', '天美', '精東', '杏吧', '91', '皇家', '起點', '大象', '蜜桃', '香蕉', '星空', '蘿莉', '扣扣', '愛神', '性視界', 'SA', 'MD', 'MSD', 'MCY', 'MKY', 'MPG', 'FLIXKO', '貓爪'],
            '探花': ['探花', '尋花', '沈先生', '大神', '鴨哥', '錘子', '全國', 'ISO'],
            '自拍流出': ['自拍', '流出', '素人'],
            'OnlyFans': ['OnlyFans', 'fansly', 'HongKong', 'Bunny', 'Nana', 'Doll'],
            '日本': ['日本', '中文字幕', 'fc2', 'JAV'],
            '麻豆傳媒': ['麻豆', 'MD', 'MSD', 'MCY', 'MKY', 'MPG', 'MDX', 'MDS', 'MDWP', 'FLIXKO'],
            '中文字幕': ['中文字幕', '字幕'],
            'AI短劇': ['AI', '短劇', '劇情'],
        }
        order = self._order_filter()
        filters = {}
        main_ids = ['國產AV', '探花', '自拍流出', 'OnlyFans', '日本', '麻豆傳媒', '中文字幕', 'AI短劇']
        for mid in main_ids:
            kws = group_keywords.get(mid, [])
            sub = [{'n': '全部', 'v': ''}]
            seen = set()
            for t in tags:
                n = t['type_name']
                if any(k.lower() in n.lower() or k.lower() in t['type_id'].lower() for k in kws):
                    if t['type_id'] not in seen and t['type_id'] != mid:
                        seen.add(t['type_id'])
                        sub.append({'n': n, 'v': t['type_id']})
            f = [order]
            if len(sub) > 1:
                f.append({'key': 'tag', 'name': '标签', 'value': sub[:80]})
            filters[mid] = f
        filters['tags'] = [
            order,
            {'key': 'tag', 'name': '标签', 'value': tag_values[:200]},
        ]
        filters['series'] = [
            {'key': 'series', 'name': '系列', 'value': series_values},
        ]
        studio = [{'n': '全部', 'v': ''}]
        for t in tags:
            n = t['type_name']
            if any(x in n for x in ('傳媒', '影業', '製片', '工作室', 'Mosaic', '社')):
                studio.append({'n': n, 'v': t['type_id']})
        filters['studio'] = [
            order,
            {'key': 'tag', 'name': '厂商', 'value': studio},
        ]
        return filters

    def _load_all_categories(self):
        """多维分类：主分类 + filters（标签/系列/厂商/排序）。"""
        cat_html = self._fetch(self.host + '/cat', referer=self.host)
        tags = self._parse_tags_from_cat(cat_html)
        series_html = self._fetch(self.host + '/series', referer=self.host)
        series = self._parse_series_from_page(series_html)
        self._all_tags = tags
        self._all_series = series
        main = [
            {'type_id': '國產AV', 'type_name': '國產AV'},
            {'type_id': '探花', 'type_name': '探花'},
            {'type_id': '自拍流出', 'type_name': '自拍流出'},
            {'type_id': 'OnlyFans', 'type_name': 'OnlyFans'},
            {'type_id': '日本', 'type_name': '日本'},
            {'type_id': '麻豆傳媒', 'type_name': '麻豆傳媒'},
            {'type_id': '中文字幕', 'type_name': '中文字幕'},
            {'type_id': 'AI短劇', 'type_name': 'AI短劇'},
            {'type_id': 'studio', 'type_name': '厂商工作室'},
            {'type_id': 'series', 'type_name': '系列合集'},
            {'type_id': 'tags', 'type_name': '标签大全'},
        ]
        self._filters = self._build_filters(tags, series)
        return main

    def init(self, extend=''):
        self.session.headers.update(self._get_headers())
        self._all_tags = []
        self._all_series = []
        self._filters = {}
        html = self._fetch(self.host + '/home')
        if html:
            self._home_data = self._extract_next_data(html)
        self._categories = self._load_all_categories()
        self._log(
            f'多维分类: 主类 {len(self._categories)} | 标签 {len(getattr(self, "_all_tags", []))} | '
            f'系列 {len(getattr(self, "_all_series", []))}'
        )

    def _convert_video_items(self, items):
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            vid = (item.get('id') or item.get('vid') or item.get('videoId') or
                   item.get('_id') or item.get('slug') or item.get('uuid'))
            if not vid:
                continue
            name = (item.get('name') or item.get('nameZh') or item.get('title') or
                    item.get('post_title') or item.get('videoName') or str(vid))
            pic = (item.get('coverImageUrl') or item.get('cover') or item.get('poster') or
                   item.get('thumbnail') or item.get('image') or item.get('img') or '')
            remark = ''
            duration = item.get('duration') or item.get('length') or item.get('time')
            if duration:
                try:
                    seconds = int(float(duration))
                    mins = seconds // 60
                    secs = seconds % 60
                    remark = f'{mins}分{secs}秒' if mins > 0 else f'{secs}秒'
                except:
                    remark = str(duration)
            if not remark and 'tags' in item and isinstance(item['tags'], list):
                remark = ', '.join(str(t) for t in item['tags'][:3])
            result.append({
                'vod_id': str(vid),
                'vod_name': str(name),
                'vod_pic': str(pic),
                'vod_remarks': remark
            })
        return result

    def homeContent(self, filter=False):
        try:
            if not self._categories:
                self.init()
            cats = self._categories or []
            filters = getattr(self, '_filters', {}) or {}
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
            self._log(f'homeContent 主类 {len(cats)}, filters {len(filters)}, 视频 {len(items)}')
            result = {'class': cats, 'list': items}
            if filter and filters:
                result['filters'] = filters
            # 多数壳只要有 filters 字段就会展示多维筛选
            elif filters:
                result['filters'] = filters
            return result
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

    def _parse_extend(self, extend):
        """解析壳传入的筛选参数（dict 或 JSON 字符串）。"""
        if not extend:
            return {}
        if isinstance(extend, dict):
            return extend
        if isinstance(extend, str):
            extend = extend.strip()
            if not extend:
                return {}
            try:
                obj = json.loads(extend)
                return obj if isinstance(obj, dict) else {}
            except Exception:
                return {}
        return {}

    def categoryContent(self, tid, pg, filter=False, extend=''):
        try:
            page = int(pg) if pg else 1
            tid = str(tid or '').strip()
            ext = self._parse_extend(extend)
            order = str(ext.get('order') or 'createdAt')
            tag = str(ext.get('tag') or '').strip()
            series_id = str(ext.get('series') or '').strip()

            # 解析最终请求目标
            # 1) 系列合集 + 选了系列 → /s/{id}
            # 2) 选了子标签 → /t/{tag}
            # 3) 主分类 / 标签大全默认 → /t/{tid}（tags/studio 无默认标签时走首页热门）
            is_series = False
            if tid == 'series' or tid.startswith('s/'):
                is_series = True
                sid = series_id or (tid[2:] if tid.startswith('s/') else '')
                if sid:
                    urls_to_try = [f'{self.host}/s/{sid}', f'{self.host}/s/{quote(sid, safe="")}']
                else:
                    # 未选具体系列：展示系列列表里各系列的封面视频意义不大，改为 series 首页
                    urls_to_try = [f'{self.host}/series']
            elif tag:
                urls_to_try = [
                    f'{self.host}/t/{quote(tag, safe="")}',
                    f'{self.host}/t/{tag}',
                ]
            elif tid in ('tags', 'studio'):
                # 未选标签时用「國產AV」兜底，避免空列表
                fallback = '國產AV'
                urls_to_try = [
                    f'{self.host}/t/{quote(fallback, safe="")}',
                    f'{self.host}/home',
                ]
            else:
                urls_to_try = [
                    f'{self.host}/t/{quote(tid, safe="")}',
                    f'{self.host}/t/{tid}',
                    f'{self.host}/tag/{quote(tid, safe="")}',
                ]

            html = ''
            used_url = ''
            for url in urls_to_try:
                if page > 1 and not is_series:
                    sep = '&' if '?' in url else '?'
                    url = f'{url}{sep}order={quote(order, safe="")}&page={page}'
                elif not is_series and order and order != 'createdAt':
                    sep = '&' if '?' in url else '?'
                    url = f'{url}{sep}order={quote(order, safe="")}'
                self._log(f'请求分类页: {url} (tid={tid}, tag={tag}, series={series_id}, order={order})')
                html = self._fetch(url, referer=self.host)
                if html and len(html) > 5000:
                    used_url = url
                    break
            if not html:
                return {'list': [], 'page': page, 'pagecount': 1, 'limit': 30, 'total': 0}

            # 系列列表页：把系列当“视频卡片”返回，点进去用 detail 不合适；改为展开第一个有视频的系列
            items = []
            if is_series and not series_id and '/series' in used_url:
                series = getattr(self, '_all_series', None) or self._parse_series_from_page(html)
                for s in series:
                    items.append({
                        'vod_id': f"series:{s['id']}",  # detail 可识别；播放仍靠单集
                        'vod_name': s['name'],
                        'vod_pic': '',
                        'vod_remarks': '系列',
                    })
                return {
                    'list': items,
                    'page': 1,
                    'pagecount': 1,
                    'limit': len(items),
                    'total': len(items),
                }

            data = self._extract_next_data(html)
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
            return {
                'list': items,
                'page': page,
                'pagecount': total_pages,
                'limit': 30,
                'total': len(items) * total_pages,
            }
        except Exception as e:
            self._log(f'categoryContent 异常: {e}')
            import traceback
            traceback.print_exc()
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}

    def detailContent(self, ids):
        try:
            vid = str(ids[0] if isinstance(ids, list) else ids)
            # 系列卡片：series:{id} → 拉 /s/{id} 把各集编成播放列表
            if vid.startswith('series:'):
                sid = vid.split(':', 1)[1]
                html = self._fetch(f'{self.host}/s/{sid}', referer=self.host)
                eps = self._parse_videos_from_html(html) if html else []
                title = next((s['name'] for s in (getattr(self, '_all_series', []) or []) if s['id'] == sid), sid)
                if eps:
                    title = eps[0].get('vod_name', title).split('·')[0].strip() or title
                play_urls = []
                for i, ep in enumerate(eps, 1):
                    name = ep.get('vod_name') or f'第{i}集'
                    play_urls.append(f"{name}${ep['vod_id']}")
                return {'list': [{
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': (eps[0].get('vod_pic') if eps else ''),
                    'vod_play_from': '系列',
                    'vod_play_url': '#'.join(play_urls) if play_urls else f'正片${sid}',
                }]}

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
                og_image = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
                if og_image:
                    pic = og_image.group(1)

            # ===== 核心修复：多策略获取播放地址 =====
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

    # ========== ROU 新版播放数据：pageProps.ev / TSR ev ==========
    def _decode_rou_ev(self, ev):
        """解码 ROU 的 ev 对象。

        日本/麻豆等分类不把播放地址放在 sources.url，而是放在 ev.d 中，
        用 ev.k 做逐字节偏移后 JSON.parse，得到 videoUrl=/api/hls/{vid}。
        """
        if not isinstance(ev, dict):
            return None
        d = ev.get('d')
        k = ev.get('k')
        if not d or k is None:
            return None
        try:
            raw = base64.b64decode(d)
            # JS 端逻辑：atob(d) 后每个字符 charCode - k，再 JSON.parse
            decoded = ''.join(chr((b - int(k)) & 0xFFFF) for b in raw)
            return json.loads(decoded)
        except Exception as e:
            self._log(f'ROU ev 解码失败: {e}')
            return None

    def _normalize_play_url(self, video_url):
        if not video_url:
            return None
        video_url = str(video_url).replace('\\/', '/').strip()
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        elif video_url.startswith('/'):
            video_url = self.host + video_url
        return video_url if self._is_valid_play_url(video_url) else None

    def _extract_ev_from_html(self, html):
        """从 TSR 流式 HTML 中提取 ev:{d,k}（当前日本/麻豆详情页无 __NEXT_DATA__）。"""
        if not html:
            return None
        # 常见形态：ev:$R[92]={d:"...",k:38}
        m = re.search(r'ev:\$R\[\d+\]=\{d:"([^"]+)",k:(\d+)\}', html)
        if not m:
            m = re.search(r'ev:\$R\[\d+\]=\{d:"([^"]+)"[^}]*?k:(\d+)', html)
        if not m:
            # 兜底：任意 ev={d:"...",k:N}
            m = re.search(r'ev[=:]\s*(?:\$R\[\d+\]=)?\{d:"([^"]+)"[^}]*?k:(\d+)', html)
        if not m:
            return None
        return {'d': m.group(1), 'k': int(m.group(2))}

    def _extract_nextdata_video_url(self, html):
        """从 __NEXT_DATA__ 或 TSR HTML 的 ev 提取真实播放入口（/api/hls/...）。"""
        # 路径1：__NEXT_DATA__.props.pageProps.ev
        data = self._extract_next_data(html)
        if isinstance(data, dict):
            try:
                page_props = data.get('props', {}).get('pageProps', {})
                ev = page_props.get('ev')
                decoded = self._decode_rou_ev(ev) if isinstance(ev, dict) else None
                if isinstance(decoded, dict):
                    video_url = decoded.get('videoUrl') or decoded.get('url') or decoded.get('m3u8')
                    video_url = self._normalize_play_url(video_url)
                    if video_url:
                        self._log(f'从 Next.js ev 获取播放入口: {video_url}')
                        return video_url
            except Exception as e:
                self._log(f'Next.js ev 播放地址提取失败: {e}')

        # 路径2：TSR 流式 HTML 中的 ev（日本/麻豆当前主路径）
        try:
            ev = self._extract_ev_from_html(html)
            if ev:
                decoded = self._decode_rou_ev(ev)
                if isinstance(decoded, dict):
                    video_url = decoded.get('videoUrl') or decoded.get('url') or decoded.get('m3u8')
                    video_url = self._normalize_play_url(video_url)
                    if video_url:
                        self._log(f'从 TSR HTML ev 获取播放入口: {video_url}')
                        return video_url
        except Exception as e:
            self._log(f'TSR HTML ev 播放地址提取失败: {e}')

        # 路径3：详情页直接构造 /api/hls/{vid}（vid 在 URL 或 TSR video.id）
        try:
            vid_m = re.search(r'/v/([a-zA-Z0-9_-]+)', html) or re.search(
                r'video:\$R\[\d+\]=\{id:"([a-zA-Z0-9_-]+)"', html
            )
            if vid_m:
                candidate = f'{self.host}/api/hls/{vid_m.group(1)}'
                self._log(f'兜底构造 /api/hls 入口: {candidate}')
                return candidate
        except Exception:
            pass
        return None

    # ========== 核心修复：TSR 数据提取 - 正确解析嵌套结构 ==========
    def _extract_tsr_video_data(self, html):
        """从 TanStack Router 流式SSR中提取视频数据"""
        # 查找 video 对象
        video_match = re.search(r'video:\$R\[\d+\]=\{', html)
        if not video_match:
            # 尝试从 l: 字段查找（分类页结构）
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

        obj_str = html[start:end+1]
        self._log(f'TSR video obj length: {len(obj_str)}')

        video = {}
        # 提取所有字符串字段
        for m in re.finditer(r'(\w+):"([^"]*)"', obj_str):
            key, val = m.group(1), m.group(2)
            if key in ['id', 'name', 'nameZh', 'ref', 'coverImageUrl', 'slug', 'type', 
                       'source', 'embed', 'player', 'iframe', 'url', 'src', 'file',
                       'playUrl', 'videoUrl', 'streamUrl', 'm3u8', 'folder']:
                video[key] = val

        # 提取数字字段
        dur_match = re.search(r'duration:([\d.]+)', obj_str)
        if dur_match:
            video['duration'] = float(dur_match.group(1))

        # 提取 sources 数组 - 使用平衡括号
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
            src_str = obj_str[src_start:src_end+1]

            # 提取每个 source 对象 - 使用平衡括号
            sources = []
            i = 0
            while i < len(src_str):
                if src_str[i] == '{':
                    # 找到匹配的 }
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
                        s = src_str[i+1:j]
                        source = {}
                        # 提取所有字段
                        for fm in re.finditer(r'(\w+):"([^"]*)"', s):
                            fk, fv = fm.group(1), fm.group(2)
                            source[fk] = fv
                        # 提取数字字段
                        for fm in re.finditer(r'(\w+):(\d+)', s):
                            fk, fv = fm.group(1), fm.group(2)
                            if fk not in source:
                                try:
                                    source[fk] = int(fv)
                                except:
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
        # ROU 当前部分（尤其日本分类）使用 /api/hls/... 作为播放入口，
        # URL 本身不一定带 .m3u8 后缀，因此不能只按扩展名判断。
        if '/api/hls/' in url_lower:
            return True
        video_exts = ['.m3u8', '.mp4', '.ts', '.flv', '.mkv', '.avi', '.m4s']
        for ext in video_exts:
            if ext in url_lower:
                return True
        return False

    # ========== 核心修复：从 folder 构造 CDN 播放地址 ==========
    def _build_cdn_url_from_folder(self, folder, resolution=720):
        """根据 folder 字段构造 CDN 播放地址"""
        if not folder:
            return None

        # 基于观察到的 URL 模式构造
        # 封面图: https://v.rn252.xyz/m/xxx/rs:fit:1280:0:0:0/wm:1/czM6Ly9yb3V2L2hscy97Zm9sZGVyfS9jb3Zlci5qcGc.jpg
        # 推测播放地址可能在类似路径下

        possible_urls = [
            # 模式1: 直接的 HLS 路径
            f'{self.cdn_host}/hls/{folder}/index.m3u8',
            f'{self.cdn_host}/hls/{folder}/playlist.m3u8',
            f'{self.cdn_host}/hls/{folder}/master.m3u8',
            # 模式2: video 路径
            f'{self.cdn_host}/video/{folder}/index.m3u8',
            f'{self.cdn_host}/video/{folder}/playlist.m3u8',
            # 模式3: m 路径（与图片相同前缀）
            f'{self.cdn_host}/m/{folder}/index.m3u8',
            f'{self.cdn_host}/m/{folder}/playlist.m3u8',
            # 模式4: 直接使用 folder 作为路径
            f'{self.cdn_host}/{folder}/index.m3u8',
            f'{self.cdn_host}/{folder}/playlist.m3u8',
            # 模式5: mp4 直链
            f'{self.cdn_host}/hls/{folder}/video.mp4',
            f'{self.cdn_host}/video/{folder}/video.mp4',
        ]

        for url in possible_urls:
            try:
                self._log(f'尝试 CDN URL: {url}')
                r = self.session.head(url, headers=self._get_headers(), timeout=10, verify=False, allow_redirects=True)
                if r.status_code == 200:
                    content_type = r.headers.get('Content-Type', '')
                    self._log(f'  状态: 200, Content-Type: {content_type}')
                    # 检查是否是视频内容
                    if 'video' in content_type or 'mpegurl' in content_type or 'octet-stream' in content_type:
                        return url
                    # 有些 CDN 返回 text/plain 但实际是 m3u8
                    if 'text' in content_type and '.m3u8' in url:
                        return url
            except Exception as e:
                self._log(f'  失败: {e}')
        return None

    # ========== 核心修复：从 ref (jable.tv) 获取播放地址 ==========
    def _get_play_url_from_ref(self, ref_url, depth=0):
        if not ref_url or depth > 3:
            return None
        try:
            self._log(f'尝试从ref获取 (depth={depth}): {ref_url}')
            html = self._fetch(ref_url, referer=self.host)
            if not html:
                return None

            # 方法1: 搜索所有m3u8地址
            m3u8_matches = re.findall(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)', html)
            for url in m3u8_matches:
                url = url.rstrip('",.;)')
                if self._is_valid_play_url(url):
                    self._log(f'找到有效m3u8: {url}')
                    return url

            # 方法2: 从预览图推断真实地址
            preview_patterns = [
                r'(https?://[^\s"\'<>]+/videos_screenshots/[^\s"\'<>]+/preview\.m3u8\.jpg)',
                r'(https?://[^\s"\'<>]+/screenshots/[^\s"\'<>]+/preview\.m3u8\.jpg)',
            ]
            for pp in preview_patterns:
                pm = re.search(pp, html)
                if pm:
                    preview_url = pm.group(1)
                    real_urls = [
                        preview_url.replace('/videos_screenshots/', '/videos/').replace('/preview.m3u8.jpg', '.m3u8'),
                        preview_url.replace('.m3u8.jpg', '.m3u8'),
                    ]
                    for real_url in real_urls:
                        try:
                            r = self.session.head(real_url, headers=self._get_headers(ref_url), timeout=10, verify=False, allow_redirects=True)
                            if r.status_code == 200:
                                self._log(f'从预览图推断: {real_url}')
                                return real_url
                        except:
                            continue

            # 方法3: 搜索 video/source 标签
            for tag_pat in [r'<video[^>]*src="([^"]+)"', r'<source[^>]*src="([^"]+)"']:
                src_match = re.search(tag_pat, html)
                if src_match:
                    src = src_match.group(1)
                    src = 'https:' + src if src.startswith('//') else src
                    if self._is_valid_play_url(src):
                        return src

            # 方法4: 搜索JSON中的播放地址
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

            # 方法5: 搜索iframe并递归
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

    # ========== 核心修复：多策略获取播放地址 ==========
    def _get_real_play_url(self, vid, html):
        """获取真实播放地址 - 多策略。

        优先读取 ROU 新版 Next.js 的 pageProps.ev.videoUrl；
        这是日本分类当前常见的播放数据位置。
        """

        # 策略0：新版 ROU 的 Next.js pageProps.ev.videoUrl
        self._log('策略0: 从 Next.js pageProps.ev 提取播放入口')
        ev_play_url = self._extract_nextdata_video_url(html)
        if ev_play_url:
            return ev_play_url

        # 提取 TSR 数据（兼容旧版/其它分类）
        video_data = self._extract_tsr_video_data(html)

        if not video_data:
            self._log('TSR 数据提取失败')
            return None

        # 策略1: 从 sources 中提取 url/file/src（如果有的话）
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
        # ROU 的 /api/hls/ 是 PNG 包装 HLS，必须走本地代理解包；
        # 片源 TS 也是 PNG+roUd，由 localProxy 递归解包。
        # 代理入口必须用 getProxyUrl()（T4/FongMi），不能写死 UndCover。
        play_id = str(id or '')
        # 系列选集可能只传视频 id，需解析真实 /api/hls/
        if play_id and not play_id.startswith('http') and not play_id.startswith('/') and '/api/hls/' not in play_id:
            if re.match(r'^[a-z0-9]{10,}$', play_id):
                detail_html = self._fetch(f'{self.host}/v/{play_id}', referer=self.host)
                real = self._get_real_play_url(play_id, detail_html or '') if detail_html else None
                play_id = real or f'{self.host}/api/hls/{play_id}'
        if play_id.startswith('/'):
            play_id = self.host + play_id
        if '/api/hls/' in play_id.lower():
            proxy_url = self._make_proxy_url('rou', play_id)
            self._log(f'playerContent 代理地址: {proxy_url}')
            return {
                'parse': 0,
                'playUrl': '',
                'url': proxy_url,
                'header': {
                    'Referer': self.host + '/',
                    'Origin': self.host,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                },
                'contentType': 'application/vnd.apple.mpegurl',
            }
        needs_parse = (flag == '解析')
        return {
            'parse': 1 if needs_parse else 0,
            'url': play_id,
            'header': {
                'Referer': self.host + '/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
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
            return {'list': items, 'page': page, 'pagecount': page + 1 if items else 1}
        except Exception as e:
            self._log(f'searchContent 异常: {e}')
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1}
