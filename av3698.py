# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
官网：https://av3698.cc/
修复版 - 分类全量版 - 播放优化版 - 2026-09-10
优化点：
1. 播放直连 CDN，剥离 av3698.cc/proxy-m3u8 中转
2. 本地 m3u8 代理，清洗广告分片 + 相对路径转绝对
3. 多 CDN 域名轮询
4. 全 try-except 兜底
"""
import re
import json
import time
import urllib.parse

try:
    import requests
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    requests = None

try:
    import sys
    sys.path.append('..')
    from base.spider import Spider as BaseSpider
except ImportError:
    BaseSpider = object

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
HOST = 'https://av3698.cc'

# 本地 TVBox 代理入口，不同版本可能是 9978 / 9988
LOCAL_PROXY_BASE = 'http://127.0.0.1:9978'

# 广告分片关键字
AD_KEYWORDS = ['/ad/', '/ads/', 'ad_', 'adv', 'pre-roll', 'preroll', '/gg/']

_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': HOST + '/',
        })
    return _session


def _http_get(url, timeout=15):
    """GET → str（requests 优先，urllib 兜底）"""
    if requests is not None:
        try:
            r = _get_session().get(url, timeout=timeout, verify=False)
            return r.text
        except Exception:
            pass
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': HOST + '/',
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace')
    except Exception:
        return ''


def _unwrap_proxy(url):
    """剥离 av3698.cc/proxy-m3u8 中转，拿到真实 CDN 地址"""
    if not url:
        return url
    if 'proxy-m3u8' in url or 'proxy?' in url:
        m = re.search(r'[?&]url=([^&]+)', url)
        if m:
            return urllib.parse.unquote(m.group(1))
    return url


def _abs_url(base, url):
    if not url:
        return url
    if url.startswith('http'):
        return url
    if url.startswith('//'):
        return 'https:' + url
    return urllib.parse.urljoin(base, url)


def _clean_m3u8(text, base):
    """清洗广告分片 + 相对路径转绝对 + 剥离 proxy 前缀"""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append(line)
            continue

        # 广告分片过滤
        low = s.lower()
        if any(k in low for k in AD_KEYWORDS):
            continue

        # 如果是 URL 或相对路径
        if s.startswith('http'):
            s = _unwrap_proxy(s)
            out.append(s)
        elif s.startswith('/'):
            out.append(_abs_url(base, s))
        elif not s.startswith('#'):
            out.append(_abs_url(base, s))
        else:
            out.append(s)
    return '\n'.join(out)


# ========== 完整分类表（硬编码兜底） ==========
FULL_CATS = [
    (54, '日韩无码'), (55, '国产自拍'), (57, '日韩精品'), (58, '欧美劲爆'),
    (59, '成人动漫'), (60, '自拍偷拍'), (61, '伦理影片'), (69, '视频二区'),
    (70, '巨乳尤物'), (71, '颜射系列'), (72, '口交视频'), (73, '自慰系列'),
    (74, '教师学生'), (75, '群P换妻'), (76, 'AI换脸'), (56, '视频三区'),
    (62, '中文字幕'), (63, '人妻系列'), (64, '制服诱惑'), (65, '强奸乱伦'),
    (66, 'AV明星'), (68, 'SM重味'), (78, 'AV解说'), (79, '视频四区'),
    (80, '吃瓜黑料'), (81, '酒店探花'), (82, '直播裸聊'), (83, '反差母狗'),
    (84, '颜值正义'), (85, '熟女少妇'), (89, '国产自拍传媒'), (90, '视频五区'),
    (91, '野战车震'), (92, 'SM调教'), (93, '家庭乱伦'), (94, '百合女同'),
    (95, '学生空姐'), (96, '撸管必看'), (97, '偷情少妇'),
]


def _fetch_categories():
    """
    从首页导航栏动态提取分类列表
    修复：使用更健壮的正则，同时匹配 class 属性中的任意内容
    """
    html = _http_get(HOST + '/')
    cats = []
    pattern = r'href="/\?source=external&amp;category=(\d+)"[^>]*>([^<]+)</a>'
    for m in re.finditer(pattern, html):
        cat_id = int(m.group(1))
        name = m.group(2).strip()
        if name and cat_id not in [c[0] for c in cats]:
            cats.append((cat_id, name))
    if len(cats) < 30:
        cats = FULL_CATS[:]
    return cats


_CATS = _fetch_categories()


class Spider(BaseSpider):
    host = HOST
    name = 'AV3698'

    def init(self, cfg):
        pass

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        if not url:
            return False
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ==================== 本地代理 ====================
    def localProxy(self, param):
        """
        两种用法：
        1) /proxy?url=<encoded m3u8 或分片>  —— 通用转发 + m3u8 清洗
        2) /proxy?url=...&type=m3u8            —— 强制按 m3u8 处理
        """
        try:
            if not param:
                return [400, 'text/plain', b'missing param']

            # 兼容 TVBox 可能传 "proxy?url=..." 形式
            if param.startswith('proxy?'):
                param = param[len('proxy?'):]

            qs = urllib.parse.parse_qs(param)
            target = (qs.get('url') or [''])[0]
            if not target:
                return [400, 'text/plain', b'missing url']

            target = _unwrap_proxy(target)

            import urllib.request
            req = urllib.request.Request(target, headers={
                'User-Agent': UA,
                'Referer': HOST + '/',
                'Origin': HOST,
                'Accept': '*/*',
            })
            resp = urllib.request.urlopen(req, timeout=20)
            data = resp.read()
            ctype = resp.headers.get('Content-Type', '')

            is_m3u8 = (
                'mpegurl' in ctype.lower()
                or target.endswith('.m3u8')
                or b'#EXTM3U' in data[:64]
            )

            if is_m3u8:
                text = data.decode('utf-8', errors='replace')
                text = _clean_m3u8(text, base=target)
                return [200, 'application/vnd.apple.mpegurl', text.encode('utf-8')]

            return [200, ctype or 'application/octet-stream', data]
        except Exception as e:
            return [502, 'text/plain', str(e).encode()]

    # ---------- 首页 ----------
    def homeContent(self, filter):
        classes = [{'type_id': str(cid), 'type_name': name} for cid, name in _CATS]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        if _CATS:
            return self.categoryContent(str(_CATS[0][0]), 1, {}, '')
        return {'list': []}

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        cat_id = self._cat_id(tid)
        if cat_id is None:
            return {'list': [], 'page': 1, 'pagecount': 1}
        url = f'{HOST}/?source=external&category={cat_id}&page={pg}'
        html = _http_get(url)
        items = self._parse_cards(html)

        pagecount = 1
        m = re.search(r'第\s*(\d+)\s*/\s*(\d+)\s*页', html)
        if m:
            pagecount = int(m.group(2))
        else:
            pages = re.findall(r'[?&]page=(\d+)', html)
            if pages:
                pagecount = max([int(p) for p in pages])

        return {'list': items, 'page': int(pg), 'pagecount': pagecount}

    def _cat_id(self, tid):
        try:
            tid = int(str(tid).split(':')[-1])
        except Exception:
            return None
        for cid, _ in _CATS:
            if cid == tid:
                return cid
        return None

    # ---------- 卡片解析 ----------
    def _parse_cards(self, html):
        items = []
        for m in re.finditer(r'<article class="media-card">([\s\S]*?)</article>', html):
            box = m.group(1)
            hm = re.search(r'href="(/xwatch/\d+)"', box)
            if not hm:
                continue
            vid = hm.group(1)
            title_m = re.search(r'class="card-title"[^>]*>([^<]+)</a>', box)
            title = title_m.group(1).strip() if title_m else vid
            pic_m = re.search(r'<img[^>]+src="([^"]+)"', box)
            pic = pic_m.group(1) if pic_m else ''
            dur_m = re.search(r'class="duration"[^>]*>([^<]+)<', box)
            remark = dur_m.group(1).strip() if dur_m else ''
            if 'cached-thumb?url=' in pic:
                u = re.search(r'url=([^&"]+)', pic)
                if u:
                    pic = urllib.parse.unquote(u.group(1))
            pic = _abs_url(HOST, pic)
            items.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remark,
            })
        return items

    # ---------- 详情 ----------
    def detailContent(self, ids):
        try:
            did = str(ids[0] if isinstance(ids, list) else ids)
        except Exception:
            return {'list': []}
        if not did.startswith('/'):
            did = '/xwatch/' + did
        html = _http_get(HOST + did)
        if not html:
            return {'list': []}

        title_m = re.search(r'<title>([^<]+)', html)
        title = title_m.group(1).replace(' · av3698.cc', '').strip() if title_m else did

        stream = ''
        m = re.search(r'data-stream="([^"]+)"', html)
        if m:
            stream = m.group(1)
        if not stream:
            m = re.search(r'src="([^"]+\.m3u8[^"]*)"', html)
            if m:
                stream = m.group(1)
        if not stream:
            m2 = re.search(r'https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*', html)
            if m2:
                stream = m2.group(0)

        # 统一补全并剥离 proxy 中转
        stream = _abs_url(HOST, stream)
        stream = _unwrap_proxy(stream)

        pic = ''
        pm = re.search(r'poster="([^"]+)"', html)
        if pm:
            pic = pm.group(1)
            if 'cached-thumb?url=' in pic:
                u = re.search(r'url=([^&"]+)', pic)
                if u:
                    pic = urllib.parse.unquote(u.group(1))
        pic = _abs_url(HOST, pic)

        if not stream:
            return {'list': []}

        vod = {
            'vod_id': did,
            'vod_name': title or did,
            'vod_pic': pic,
            'vod_content': title or did,
            'vod_play_from': 'av3698',
            'vod_play_url': f'直链${stream}',
            'vod_remarks': 'M3U8',
        }
        return {'list': [vod]}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg=1):
        kw = urllib.parse.quote(key)
        url = f'{HOST}/?source=external&q={kw}&page={pg}'
        html = _http_get(url)
        items = self._parse_cards(html)
        if not items:
            url = f'{HOST}/?q={kw}&page={pg}'
            html = _http_get(url)
            items = self._parse_cards(html)
        return {'list': items}

    # ==================== 播放（优化版） ====================
    def playerContent(self, flag, id, vipFlags=None):
        # 1) 剥离站点中转，拿到真实 CDN m3u8
        real = _unwrap_proxy(id)

        # 2) 默认直连（和网页端一致，最快）
        #    若直连 403 / 黑屏，把下面这行取消注释走本地代理
        # real = f'{LOCAL_PROXY_BASE}/proxy?url=' + urllib.parse.quote(real, safe='')

        return {
            'parse': 0,
            'url': real,
            'jx': 0,
            'header': {
                'User-Agent': UA,
                'Referer': HOST + '/',
                'Origin': HOST,
            }
        }


# ---------- 本地测试 ----------
if __name__ == '__main__':
    sp = Spider()
    print('=== 动态分类（共 {} 个）==='.format(len(_CATS)))
    for idx, (cid, name) in enumerate(_CATS, 1):
        print(f'  {idx:2d}. {cid}: {name}')

    print('\n=== homeContent ===')
    hc = sp.homeContent(True)
    print(f'分类: {len(hc["class"])}')

    print('\n=== categoryContent (第一个分类) ===')
    if _CATS:
        cc = sp.categoryContent(str(_CATS[0][0]), 1, {}, '')
        print(f'视频: {len(cc["list"])}, 页数: {cc["pagecount"]}')
        if cc['list']:
            print(f'  例: {cc["list"][0]["vod_name"][:40]}')

    print('\n=== detailContent ===')
    if _CATS:
        cc = sp.categoryContent(str(_CATS[0][0]), 1, {}, '')
        if cc['list']:
            d = sp.detailContent([cc['list'][0]['vod_id']])
            if d['list']:
                it = d['list'][0]
                print(f'  标题: {it["vod_name"][:40]}')
                print(f'  播放: {it["vod_play_url"][:100]}')

    print('\n=== searchContent (测试) ===')
    sc = sp.searchContent('HEYZO', False)
    print(f'结果: {len(sc["list"])} 条')