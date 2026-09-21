# -*- coding: utf-8 -*-

# beeg.py - Beeg 源（FongMi Python 格式，全分类版）

import sys, re, json, base64, threading, time

import requests, urllib3

from http.server import HTTPServer, BaseHTTPRequestHandler

from socketserver import ThreadingMixIn

from urllib.parse import unquote, quote, urljoin, urlparse

urllib3.disable_warnings()

sys.path.append('..')

try:

    from base.spider import Spider as BaseSpider

except ImportError:

    class BaseSpider: pass

# ===== 图片代理 =====

_proxy_port = 0

_proxy_started = False

_proxy_session = requests.Session()

_proxy_session.verify = False

class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):

    daemon_threads = True

class _ProxyHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        try:

            real_url = unquote(self.path[1:])

            if not real_url or not real_url.startswith('http'):

                self.send_response(404); self.end_headers(); return

            r = _proxy_session.get(real_url, headers={

                'User-Agent': 'Mozilla/5.0',

                'Referer': 'https://beeg.com/'

            }, timeout=20, verify=False)

            ct = r.headers.get('Content-Type', 'image/jpeg')

            self.send_response(200)

            self.send_header('Content-Type', ct)

            self.send_header('Content-Length', len(r.content))

            self.send_header('Access-Control-Allow-Origin', '*')

            self.end_headers()

            self.wfile.write(r.content)

        except:

            self.send_response(404); self.end_headers()

    def log_message(self, format, *args): pass

def _start_proxy():

    global _proxy_port, _proxy_started

    if _proxy_started: return

    import socket

    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sk.bind(('127.0.0.1', 0))

    _proxy_port = sk.getsockname()[1]

    sk.close()

    server = _ThreadedHTTPServer(('127.0.0.1', _proxy_port), _ProxyHandler)

    threading.Thread(target=server.serve_forever, daemon=True).start()

    _proxy_started = True

# ===== Spider =====

class Spider(BaseSpider):

    session = requests.Session()

    API_BASE = 'https://store.externulls.com'

    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    CHANNELS = [

        {'name': 'Blacked', 'slug': 'blacked'},

        {'name': 'Vixen', 'slug': 'vixencom'},

        {'name': 'Team Skeet', 'slug': 'teamskeet'},

        {'name': 'Teen Mega World', 'slug': 'teenmegaworld'},

        {'name': 'Nubiles', 'slug': 'nubilesporn'},

        {'name': 'Wow Girls', 'slug': 'wowgirls'},

        {'name': 'Bratty Sis', 'slug': 'brattysis'},

        {'name': 'Adult Time', 'slug': 'adulttime'},

        {'name': 'Family Strokes', 'slug': 'familystrokes'},

        {'name': 'Ultra Films', 'slug': 'ultrafilms'},

        {'name': 'Nubile Films', 'slug': 'nubilefilms'},

        {'name': 'LetsDoeIt', 'slug': 'letsdoeit'},

        {'name': 'Family XXX', 'slug': 'familyxxx'},

        {'name': 'Tiny 4K', 'slug': 'tiny4k'},

        {'name': 'New Sensations', 'slug': 'newsensations'},

        {'name': 'Naughty America', 'slug': 'naughtyamerica'},

        {'name': 'Sis Loves Me', 'slug': 'sislovesme'},

        {'name': 'Pure Taboo', 'slug': 'puretaboo'},

        {'name': 'Step Siblings Caught', 'slug': 'stepsiblingscaught'},

        {'name': 'Moms Teach Sex', 'slug': 'momsteachsex'},

        {'name': 'Hot Wife XXX', 'slug': 'hotwifexxx'},

        {'name': 'Porn Force', 'slug': 'pornforce'},

        {'name': 'Dorcel Club', 'slug': 'dorcelclub'},

        {'name': 'Vixen Plus', 'slug': 'vixenplus'},

        {'name': 'My Family Pies', 'slug': 'myfamilypies'},

        {'name': "My Friend's Hot Mom", 'slug': 'myfriendshotmom'},

        {'name': 'Bare Back Studios', 'slug': 'barebackstudios'},

        {'name': 'NF Busty', 'slug': 'nfbusty'},

        {'name': 'Passion HD', 'slug': 'passionhd'},

        {'name': '21 Naturals', 'slug': '21naturals'},

        {'name': 'Teen Fidelity', 'slug': 'teenfidelity'},

        {'name': 'Tushy', 'slug': 'tushy'},

        {'name': 'Porn World', 'slug': 'pornworld'},

        {'name': 'Cum 4K', 'slug': 'cum4k'},

        {'name': 'My Pervy Family', 'slug': 'mypervyfamily'},

        {'name': 'Porn Fidelity', 'slug': 'pornfidelity'},

        {'name': 'NVG', 'slug': 'nvg'},

        {'name': 'Exploited College Girls', 'slug': 'exploitedcollegegirls'},

        {'name': 'Deeper', 'slug': 'deeperofficial'},

        {'name': 'Bellesa Plus', 'slug': 'bellesaplus'},

        {'name': 'Princess Cum', 'slug': 'princesscum'},

        {'name': 'White Boxxx', 'slug': 'whiteboxxx'},

        {'name': 'Pure Mature', 'slug': 'puremature'},

        {'name': 'Perv Mom', 'slug': 'pervmom'},

        {'name': 'Blacked Raw', 'slug': 'blackedraw'},

        {'name': 'Mom Wants to Breed', 'slug': 'momwantstobreed'},

        {'name': '21 Sextury', 'slug': '21sextury'},

        {'name': 'Hegre', 'slug': 'hegre'},

        {'name': 'Life Selector', 'slug': 'lifeselector'},

        {'name': 'Exxxtra Small', 'slug': 'exxtrasmall'},

        {'name': 'JAV HD', 'slug': 'javhd'},

        {'name': 'Girl Cum', 'slug': 'girlcumofficial'},

        {'name': 'Sex Art', 'slug': 'sexart'},

        {'name': "Tonight's Girlfriend", 'slug': 'tonightsgirlfriend'},

        {'name': 'Dad Crush', 'slug': 'dadcrush'},

        {'name': 'Lubed', 'slug': 'lubedcom'},

        {'name': 'VIP 4K', 'slug': 'vip4k'},

        {'name': 'Evil Angel', 'slug': 'evilangel'},

        {'name': 'JAV Hub', 'slug': 'javhub'},

        {'name': 'Caribbeancom', 'slug': 'caribbeancom'},

        {'name': "My Sister's Hot Friend", 'slug': 'mysistershotfriend'},

        {'name': 'Daughter Swap', 'slug': 'daughterswap'},

    ]

    MODELS = [

        {'name': 'Eva Elfie', 'slug': 'evaelfie'},

        {'name': 'Angela White', 'slug': 'angelawhite'},

        {'name': 'Dani Daniels', 'slug': 'danidaniels'},

        {'name': 'Mia Malkova', 'slug': 'miamalkova'},

        {'name': 'Riley Reid', 'slug': 'rileyreid'},

        {'name': 'Mila Lioness', 'slug': 'milalioness'},

        {'name': 'Alexa Grace', 'slug': 'alexagrace'},

        {'name': 'Alina Lopez', 'slug': 'alinalopez'},

        {'name': 'Comatozze', 'slug': 'comatozze'},

        {'name': 'Candy Love', 'slug': 'candylove'},

        {'name': 'Diana Rider', 'slug': 'dianarider'},

        {'name': 'Sweetie Fox', 'slug': 'sweetiefox'},

        {'name': 'Lana Rhoades', 'slug': 'lanarhoades'},

        {'name': 'Julie Jess', 'slug': 'juliejess'},

        {'name': 'Anny Walker', 'slug': 'annywalker'},

        {'name': 'Angel X', 'slug': 'angelx'},

        {'name': 'Shinaryen', 'slug': 'shinaryen'},

        {'name': 'Abella Danger', 'slug': 'abelladanger'},

        {'name': 'Sybil', 'slug': 'sybil'},

        {'name': 'Emilia Bunny', 'slug': 'emiliabunny'},

        {'name': 'Syndicete', 'slug': 'syndicete'},

        {'name': 'Jenny Kitty', 'slug': 'jennykitty'},

        {'name': 'Emily Willis', 'slug': 'emilywillis'},

        {'name': 'Elsa Jean', 'slug': 'elsajean'},

        {'name': 'Nicole Aniston', 'slug': 'nicoleaniston'},

        {'name': 'Fantasy Babe', 'slug': 'fantasybabe'},

        {'name': 'Lena Paul', 'slug': 'lenapaul'},

        {'name': 'Bonnie Blaze', 'slug': 'bonnieblaze'},

        {'name': 'Cory Chase', 'slug': 'corychase'},

        {'name': 'Martin & Paola', 'slug': 'martinpaola'},

        {'name': 'Dick For Lily', 'slug': 'dickforlily'},

        {'name': 'Gabbie Carter', 'slug': 'gabbiecarter'},

        {'name': 'Lexi Lore', 'slug': 'lexilore'},

        {'name': 'Kate Kuray', 'slug': 'katekuray'},

        {'name': 'Blake Blossom', 'slug': 'blakeblossom'},

        {'name': 'Carla Cute', 'slug': 'carlacute'},

        {'name': 'Hotties Two', 'slug': 'hottiestwo'},

        {'name': 'Adriana Chechik', 'slug': 'adrianachechik'},

        {'name': 'Yummy Mira', 'slug': 'yummymira'},

        {'name': 'Reislin', 'slug': 'reislin'},

        {'name': 'Anastangel', 'slug': 'anastangel'},

        {'name': 'Gina Valentina', 'slug': 'ginavalentina'},

        {'name': 'Kenzie Reeves', 'slug': 'kenzie_reeves'},

        {'name': 'Valentina Nappi', 'slug': 'valentinanappi'},

        {'name': 'Leah Meow', 'slug': 'leahmeow'},

        {'name': 'Carry Light', 'slug': 'carrylight'},

        {'name': 'Purple Bitch', 'slug': 'purplebitch'},

        {'name': 'Pink Loving', 'slug': 'pinkloving'},

        {'name': 'My Anny', 'slug': 'myanny'},

        {'name': 'Lil Karina', 'slug': 'lilkarina'},

        {'name': 'Melody Marks', 'slug': 'melodymarks'},

        {'name': 'Luxury Mur', 'slug': 'luxurymur'},

        {'name': 'Diana Daniels', 'slug': 'danadaniels'},

        {'name': 'Stacy Cruz', 'slug': 'stacycruz'},

        {'name': 'Allinika', 'slug': 'allinika'},

        {'name': 'Autumn Falls', 'slug': 'autumnfalls'},

        {'name': 'Sola Zola', 'slug': 'solazola'},

        {'name': 'Krystal Boyd', 'slug': 'krystalboyd'},

        {'name': 'Lexi Luna', 'slug': 'lexiluna'},

        {'name': 'Lauren Phillips', 'slug': 'laurenphillips'},

        {'name': 'Kera Bear', 'slug': 'kerabear'},

        {'name': 'Little Caprice', 'slug': 'littlecaprice'},

        {'name': 'Sia Siberia', 'slug': 'siasiberia'},

        {'name': 'Molly Red Wolf', 'slug': 'mollyredwolf'},

        {'name': 'Samantha Flair', 'slug': 'samanthaflair'},

        {'name': 'Luxury Girl', 'slug': 'luxurygirl'},

        {'name': 'Molly Little', 'slug': 'mollylittle'},

        {'name': 'Kelly Aleman', 'slug': 'kellyaleman'},

        {'name': 'Yinyleon', 'slug': 'yinyleon'},

        {'name': 'Liya Silver', 'slug': 'liyasilver'},

        {'name': 'Telari Love', 'slug': 'telarilove'},

        {'name': 'Skye Young', 'slug': 'skyeyoung'},

        {'name': 'Tru Kait', 'slug': 'trukait'},

        {'name': 'Eliza Ibarra', 'slug': 'elizaibarra'},

        {'name': 'Jenny Lux', 'slug': 'jennylux'},

        {'name': 'Anissa Kate', 'slug': 'anissakate'},

        {'name': 'Haley Reed', 'slug': 'haleyreed'},

        {'name': 'Kyler Quinn', 'slug': 'kylerquinn'},

        {'name': 'Skylar Vox', 'slug': 'skylarvox'},

        {'name': 'Leah Gotti', 'slug': 'leahgotti'},

        {'name': 'Lina Migurtt', 'slug': 'linamigurtt'},

        {'name': 'Dillion Harper', 'slug': 'dillionharper'},

        {'name': 'Brandi Love', 'slug': 'brandilove'},

        {'name': 'Jia Lissa', 'slug': 'jialissa'},

        {'name': 'Brooke Tilli', 'slug': 'brooketilli'},

        {'name': 'Miss Lexa', 'slug': 'misslexa'},

        {'name': 'Bunny Rabbits', 'slug': 'bunnyrabbits'},

        {'name': 'Leo Lulu', 'slug': 'leolulu'},

        {'name': 'Layla Ray', 'slug': 'laylaray'},

        {'name': 'Web To Love', 'slug': 'webtolove'},

        {'name': 'Nancy Ace', 'slug': 'nancyace'},

        {'name': 'Hansel & Grettel', 'slug': 'hanselgrettel'},

        {'name': 'Xreindeers', 'slug': 'xreindeers'},

        {'name': 'Tiffany Tatum', 'slug': 'tiffanystatum'},

        {'name': 'Mirari', 'slug': 'mirari'},

        {'name': 'Adria Rae', 'slug': 'adriarae'},

        {'name': 'Kristel Jack', 'slug': 'kristeljack'},

        {'name': 'Mila Solana', 'slug': 'milasolana'},

        {'name': 'Alexis Fawx', 'slug': 'alexisfawx'},

    ]

    def __init__(self):

        super().__init__()

        self._debug = True

    def _log(self, msg):

        if self._debug: print(f'[beeg] {msg}')

    def getName(self): return 'beeg'

    def isVideoFormat(self, url): return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self): return False

    def destroy(self): pass

    def localProxy(self, param): return [404, 'text/plain', '']

    def init(self, extend=''):

        self.session.verify = False

        self.session.headers.update({'User-Agent': self.UA})

        _start_proxy()

        return

    def _proxy_url(self, url):

        if not url: return ''

        if url.startswith('http://127.0.0.1'): return url

        return f'http://127.0.0.1:{_proxy_port}/{quote(url, safe="")}'

    def _api(self, url, extra_headers=None):

        h = {'User-Agent': self.UA}

        if extra_headers: h.update(extra_headers)

        try:

            r = self.session.get(url, headers=h, timeout=15, verify=False)

            return r.json()

        except Exception as e:

            self._log(f'API 请求失败: {url} - {e}')

            return None

    @staticmethod

    def _fmt_dur(seconds):

        if not seconds or seconds <= 0: return ''

        h = seconds // 3600

        m = (seconds % 3600) // 60

        s = seconds % 60

        if h > 0: return f'{h}:{m:02d}:{s:02d}'

        return f'{m}:{s:02d}'

    def _build_vod(self, video):

        try:

            fc_facts = (video.get('fc_facts') or [{}])[0]

            fact_id = fc_facts.get('id')

            file_data = video.get('file', {}).get('data', [])

            file_id = video.get('file', {}).get('id') or (file_data[0].get('cd_file') if file_data else None) or fact_id

            if not file_id: return None

            duration = video.get('file', {}).get('fl_duration', 0)

            height = video.get('file', {}).get('fl_height', 0)

            fc_thumbs = fc_facts.get('fc_thumbs', [])

            title = 'Untitled'

            for item in file_data:

                if item.get('cd_column') == 'sf_name':

                    title = item.get('cd_value') or title

                    break

            cover = ''

            if fc_thumbs:

                cover = f'https://thumbs.externulls.com/videos/{file_id}/{fc_thumbs[0]}.jpg'

            elif file_data and file_data[0].get('cd_file'):

                cover = f'https://img.externulls.com/{file_data[0]["cd_file"]}/preview_01.jpg'

            return {

                'vod_id': str(file_id),

                'vod_name': title,

                'vod_pic': self._proxy_url(cover),

                'vod_remarks': f'{height}p {self._fmt_dur(duration)}'.strip(),

            }

        except Exception as e:

            self._log(f'build_vod 失败: {e}')

            return None

    # ===== 首页/分类 =====

    def homeContent(self, filter):

        classes = [{'type_id': 'home', 'type_name': '首页'}]

        for ch in self.CHANNELS:

            classes.append({'type_id': ch['slug'], 'type_name': ch['name']})

        for m in self.MODELS:

            classes.append({'type_id': m['slug'], 'type_name': m['name']})

        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):

        data = self._api(f'{self.API_BASE}/tag/videos/index?limit=48&offset=0')

        items = []

        if isinstance(data, list):

            for v in data:

                vod = self._build_vod(v)

                if vod: items.append(vod)

        return {'list': items}

    def categoryContent(self, tid, pg, filter, extend):

        page = int(pg) if pg else 1

        offset = (page - 1) * 48

        url = f'{self.API_BASE}/tag/videos/{tid}?limit=48&offset={offset}'

        data = self._api(url)

        items = []

        if isinstance(data, list):

            for v in data:

                vod = self._build_vod(v)

                if vod: items.append(vod)

        return {

            'list': items,

            'page': page,

            'pagecount': page + 1,

            'limit': len(items),

            'total': page * 48 + 1 if items else 0

        }

    # ===== 详情 =====

    def detailContent(self, ids):

        vid = str(ids[0] if isinstance(ids, list) else ids)

        data = self._api(f'{self.API_BASE}/facts/file/{vid}', {

            'Origin': 'https://beeg.com',

            'Referer': 'https://beeg.com/'

        })

        if not data:

            return {'list': []}

        file = data.get('file', {})

        hls = file.get('hls_resources', {}) or {}

        qualities = []

        multi = hls.get('fl_cdn_multi')

        if multi:

            if not multi.startswith('http'):

                multi = f'https://video.beeg.com/{multi}'

            qualities.append(('自动(1080p)', multi, 99999))

        for key, value in hls.items():

            if value and key.startswith('fl_cdn_') and key != 'fl_cdn_multi':

                m = re.match(r'fl_cdn_(\d+)', key)

                height = int(m.group(1)) if m else 0

                url = value if value.startswith('http') else f'https://video.beeg.com/{value}'

                qualities.append((f'{height}p', url, height))

        qualities.sort(key=lambda x: x[2], reverse=True)

        play_urls = '#'.join([f'{name}${url}' for name, url, _ in qualities]) or f'默认${vid}'

        vod = {

            'vod_id': vid,

            'vod_name': file.get('fl_name', 'Video'),

            'vod_pic': '',

            'vod_remarks': '',

            'vod_play_from': 'Beeg',

            'vod_play_url': play_urls,

            'vod_content': ''

        }

        return {'list': [vod]}

    # ===== 播放 =====

    def playerContent(self, flag, id, vipFlags=None):

        self._log(f'playerContent: id={id[:120]}')

        return {

            'parse': 0,

            'url': id,

            'header': {

                'User-Agent': self.UA,

                'Referer': 'https://beeg.com/',

                'Origin': 'https://beeg.com'

            }

        }

    # ===== 搜索 =====

    def searchContent(self, key, quick, pg='1'):

        if not key:

            return {'list': []}

        page = int(pg) if pg else 1

        query_words = [w for w in re.split(r'[^a-z0-9]+', key.lower()) if len(w) >= 2]

        cards, seen = [], set()

        offset = (page - 1) * 48

        data = self._api(f'{self.API_BASE}/tag/videos/index?limit=48&offset={offset}')

        if isinstance(data, list):

            for v in data:

                vod = self._build_vod(v)

                if not vod or vod['vod_id'] in seen: continue

                normalized = re.sub(r'[^a-z0-9]', '', vod['vod_name'].lower())

                if all(w in normalized for w in query_words):

                    seen.add(vod['vod_id'])

                    cards.append(vod)

                    if len(cards) >= 48: break

        return {'list': cards, 'page': page, 'pagecount': page + 1, 'limit': len(cards), 'total': len(cards)}