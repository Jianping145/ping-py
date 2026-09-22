# exporntoons.py

import json

import re

import requests

from urllib.parse import quote

UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/604.1.14 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1'

SITE = 'https://exporntoons.net'

TAG_CLASSES = [

    {"type_id": 'video/shemale+film+retro', "type_name": 'Shemale Film Retro'},

    {"type_id": 'video/japenese+mom+n+son', "type_name": 'Japanese Mom N Son'},

    {"type_id": 'video/pis+japen', "type_name": 'Pis Japon'},

    {"type_id": 'video/sport', "type_name": 'Sport'},

    {"type_id": 'video/riley+reid+gangbang', "type_name": 'Riley Reid Gangbang'},

    {"type_id": 'video/full+2010+movies', "type_name": 'Full 2010 Movies'},

    {"type_id": 'video/mivd+212', "type_name": 'Mivd 212'},

    {"type_id": 'video/dldss+385+yuko+ono', "type_name": 'Dldss 385 Yuko Ono'},

    {"type_id": 'video/34+g+tits', "type_name": '34 G Tits'},

    {"type_id": 'video/lily+blossom', "type_name": 'Lily Blossom'},

    {"type_id": 'video/cu+ada+infiel', "type_name": 'Cu Ada Infiel'},

    {"type_id": 'video/voueur+sister', "type_name": 'Voyeur Sister'},

    {"type_id": 'video/virginty+burden', "type_name": 'Virginity Burden'},

    {"type_id": 'video/hindhi+oyo+uncut', "type_name": 'Hindi Oyo Uncut'},

    {"type_id": 'video/liza+evanz', "type_name": 'Liza Evanz'},

    {"type_id": 'video/sissy+chastity', "type_name": 'Sissy Chastity'},

    {"type_id": 'video/solo+orgazam', "type_name": 'Solo Orgasm'},

    {"type_id": 'video/photoshoot+amateur', "type_name": 'Photoshoot Amateur'},

    {"type_id": 'video/adriana+rodrigues', "type_name": 'Adriana Rodrigues'},

    {"type_id": 'video/carry+light', "type_name": 'Carry Light'},

    {"type_id": 'video/all+converter', "type_name": 'All Converter'},

    {"type_id": 'video/michiru+kujo', "type_name": 'Michiru Kujo'},

    {"type_id": 'video/kala+khatta', "type_name": 'Kala Khatta'},

    {"type_id": 'video/graphic+response', "type_name": 'Graphic Response'},

    {"type_id": 'video/mia+aniston', "type_name": 'Mia Aniston'},

    {"type_id": 'video/snos+039+yu+tano', "type_name": 'Snos 039 Yu Tano'},

    {"type_id": 'video/eva+elfie+anal', "type_name": 'Eva Elfie Anal'},

    {"type_id": 'video/bizarre', "type_name": 'Bizarre'},

    {"type_id": 'video/shahad+part+1', "type_name": 'Shahad Part 1'},

    {"type_id": 'video/la+pubertad', "type_name": 'La Pubertad'},

    {"type_id": 'video/gia+derza+anal', "type_name": 'Gia Derza Anal'},

    {"type_id": 'video/maneka', "type_name": 'Maneka'},

    {"type_id": 'video/grateful+girlfriend', "type_name": 'Grateful Girlfriend'},

    {"type_id": 'video/shay+sights+son', "type_name": 'Shay Sights Son'},

    {"type_id": 'video/devil+doll+2007', "type_name": 'Devil Doll 2007'},

    {"type_id": 'video/asia+vargas', "type_name": 'Asia Vargas'},

    {"type_id": 'video/love+lance', "type_name": 'Love Lance'},

    {"type_id": 'video/thetm+va', "type_name": 'Thetm Va'},

    {"type_id": 'video/sissy+hypno', "type_name": 'Sissy Hypno'},

    {"type_id": 'video/brutal+tough+mature', "type_name": 'Brutal Tough Mature'},

    {"type_id": 'video/sanvida+part+2', "type_name": 'Sanvida Part 2'},

    {"type_id": 'video/teanna+trump', "type_name": 'Teanna Trump'},

    {"type_id": 'video/tiffany+lee+rea', "type_name": 'Tiffany Lee Rea'},

    {"type_id": 'video/tuscarora+nevada', "type_name": 'Tuscarora Nevada'},

    {"type_id": 'video/liloostich', "type_name": 'Liloostich'},

    {"type_id": 'video/diluxe', "type_name": 'Diluxe'},

    {"type_id": 'video/butte+county', "type_name": 'Butte County'},

    {"type_id": 'video/j+monte', "type_name": 'J Monte'},

    {"type_id": 'video/adams', "type_name": 'Adams'},

    {"type_id": 'video/vec+489+chiharu+ito', "type_name": 'Vec 489 Chiharu Ito'},

    {"type_id": 'video/asian+daddy', "type_name": 'Asian Daddy'},

    {"type_id": 'video/dwporn+com', "type_name": 'Dwporn Com'},

    {"type_id": 'video/fsdss+778', "type_name": 'Fsdss 778'},

    {"type_id": 'video/m+6month', "type_name": 'M 6Month'},

    {"type_id": 'video/childhood+games', "type_name": 'Childhood Games'},

    {"type_id": 'video/lilian+la+virgen', "type_name": 'Lilian La Virgen'},

    {"type_id": 'video/my+girlfried+mother', "type_name": 'My Girlfriend Mother'},

    {"type_id": 'video/aiav+004', "type_name": 'Aiav 004'},

    {"type_id": 'video/angelawhite', "type_name": 'Angela White'},

    {"type_id": 'video/hot+erotic+2002', "type_name": 'Hot Erotic 2002'},

    {"type_id": 'video/yoch+012', "type_name": 'Yoch 012'},

    {"type_id": 'video/video+mp4a', "type_name": 'Video Mp4A'},

    {"type_id": 'video/lingam+pump', "type_name": 'Lingam Pump'},

    {"type_id": 'video/homeporn+swx+vid', "type_name": 'Homeporn Swx Vid'},

    {"type_id": 'video/amandeep', "type_name": 'Amandeep'},

    {"type_id": 'video/sdmf+052', "type_name": 'Sdmf 052'},

    {"type_id": 'video/nadia+white', "type_name": 'Nadia White'},

    {"type_id": 'video/primal+afterparty', "type_name": 'Primal Afterparty'},

    {"type_id": 'video/seduced+bye+cougar', "type_name": 'Seduced By Cougar'},

    {"type_id": 'video/amateur+blowjob', "type_name": 'Amateur Blowjob'},

    {"type_id": 'video/cabina+voyeurs', "type_name": 'Cabina Voyeurs'},

    {"type_id": 'video/silk1941', "type_name": 'Silk1941'},

    {"type_id": 'video/ariana+marie+anal', "type_name": 'Ariana Marie Anal'},

    {"type_id": 'video/female+worship', "type_name": 'Female Worship'},

    {"type_id": 'video/bully', "type_name": 'Bully'},

    {"type_id": 'video/cum+inside+mature', "type_name": 'Cum Inside Mature'},

    {"type_id": 'video/sleeping+loads+cum', "type_name": 'Sleeping Loads Cum'},

    {"type_id": 'video/asmr+network', "type_name": 'Asmr Network'},

    {"type_id": 'video/mhs+829', "type_name": 'Mhs 829'},

    {"type_id": 'video/royd+303', "type_name": 'Royd 303'},

    {"type_id": 'video/dass+079+uncensored', "type_name": 'Dass 079 Uncensored'},

    {"type_id": 'video/lexxy+voodoo', "type_name": 'Lexxy Voodoo'},

    {"type_id": 'video/flm+japon', "type_name": 'Flm Japon'},

    {"type_id": 'video/nara+ford', "type_name": 'Nara Ford'},

    {"type_id": 'video/cuckold+vintag', "type_name": 'Cuckold Vintage'},

    {"type_id": 'video/mimi+lili', "type_name": 'Mimi Lili'},

    {"type_id": 'video/adolescent+jav', "type_name": 'Adolescent Jav'},

    {"type_id": 'video/piss+asiticas', "type_name": 'Piss Asiticas'},

    {"type_id": 'video/fc2ppv+4556190', "type_name": 'Fc2Ppv 4556190'}

]

class Spider:

    def __init__(self):

        pass

    def req(self, url, headers=None):

        if headers is None:

            headers = {}

        try:

            r = requests.get(url, headers=headers, timeout=15)

            r.raise_for_status()

            return r.text

        except Exception as e:

            print(f"req error: {e}")

            return ""

    def init(self, cfg):

        return json.dumps({"code": 0, "msg": "success"})

    def homeContent(self, filter=None):

        classes = [

            {"type_id": 'now', "type_name": '最新'},

            {"type_id": 'recent', "type_name": '最近'}

        ]

        for item in TAG_CLASSES:

            classes.append(item)

        return json.dumps({"class": classes})

    def homeVideoContent(self):

        return self.categoryContent('now', 1, None, None)

    def categoryContent(self, tid, pg, filter, extend):

        try:

            page = int(pg) if pg else 1

            url = SITE + '/' + tid

            if page > 1:

                url += '?p=' + str(page)

            print('category url: ' + url)

            headers = {'User-Agent': UA, 'Referer': SITE + '/'}

            html = self.req(url, headers)

            list_data = self.parseList(html)

            if len(list_data) == 0 and not tid.startswith('video/') and tid != 'now':

                print('category empty, fallback to now')

                fallback_url = SITE + '/now'

                if page > 1:

                    fallback_url += '?p=' + str(page)

                html2 = self.req(fallback_url, headers)

                list_data = self.parseList(html2)

            print('category list count: ' + str(len(list_data)))

            return json.dumps({

                "list": list_data,

                "page": page,

                "pagecount": page + 1 if len(list_data) > 0 else page,

                "total": 9999 if len(list_data) > 0 else 0

            })

        except Exception as e:

            print('category error: ' + str(e))

            return json.dumps({"list": [], "page": 1, "pagecount": 1, "total": 0})

    def detailContent(self, ids):

        try:

            id = ids[0] if isinstance(ids, list) else ids

            url = id if id.startswith('http') else SITE + '/watch/' + id

            print('detail url: ' + url)

            headers = {'User-Agent': UA, 'Referer': SITE + '/'}

            html = self.req(url, headers)

            print('detail html length: ' + str(len(html)))

            title_match = re.search(r'<title>([^<]+)</title>', html, re.I)

            if title_match:

                title = re.sub(r'\s*[-|]\s*ExPornToons.*$', '', title_match.group(1), flags=re.I).strip()

            else:

                title = 'Video'

            pic_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)

            pic = pic_match.group(1) if pic_match else ''

            id_parts = re.sub(r'^.*\/watch\/', '', id).split('_')

            id_part1 = id_parts[0] if len(id_parts) > 0 else ''

            id_part2 = id_parts[1] if len(id_parts) > 1 else ''

            print('filter idPart1: ' + id_part1 + ', idPart2: ' + id_part2)

            quality_map = {}

            cdn_regex = re.compile(r'(https?://[^"\'\s\\<>]*pvvstream\.pro[^"\'\s\\<>]*)')

            for m in cdn_regex.finditer(html):

                u = m.group(1).replace('&amp;', '&')

                if id_part1 and id_part1 not in u:

                    continue

                if id_part2 and id_part2 not in u:

                    continue

                q_match = re.search(r'vid_(\d+)p', u) or re.search(r'/(\d+)p/', u) or re.search(r'_(\d+)p\.', u)

                if not q_match:

                    continue

                q_num = int(q_match.group(1))

                if not q_num or q_num < 360:

                    continue

                if q_num not in quality_map:

                    quality_map[q_num] = u

            qualities = sorted(quality_map.keys(), reverse=True)

            play_urls = []

            for q in qualities:

                play_urls.append(f'{q}p${quality_map[q]}')

            print('detail qualities: ' + ','.join(map(str, qualities)))

            if not play_urls:

                vf_regex = re.compile(r'(https?://[^"\'\s\\<>]*/videofile/[^"\'\s\\<>]+\.mp4[^"\'\s\\<>]*)')

                for m in vf_regex.finditer(html):

                    u = m.group(1).replace('&amp;', '&')

                    if id_part1 and id_part1 not in u:

                        continue

                    play_urls.append('播放$' + u)

                    break

            vod = {

                "vod_id": id,

                "vod_name": title,

                "vod_pic": pic,

                "vod_remarks": "",

                "vod_content": "",

                "vod_play_from": "ExPornToons",

                "vod_play_url": '#'.join(play_urls) if play_urls else '默认$' + id

            }

            return json.dumps({"list": [vod]})

        except Exception as e:

            print('detail error: ' + str(e))

            return json.dumps({"list": []})

    def playerContent(self, flag, id, vipFlags=None):

        try:

            print('play url: ' + id)

            return json.dumps({

                "url": id,

                "header": json.dumps({

                    "User-Agent": UA,

                    "Referer": SITE + '/',

                    "Origin": SITE

                })

            })

        except Exception as e:

            return json.dumps({"url": ""})

    def searchContent(self, wd, quick=None):

        try:

            if not wd:

                return json.dumps({"list": []})

            keyword = re.sub(r'\s+', '+', wd)

            url = SITE + '/video/' + quote(keyword)

            print('search url: ' + url)

            headers = {'User-Agent': UA, 'Referer': SITE + '/'}

            html = self.req(url, headers)

            list_data = self.parseList(html)

            print('search list count: ' + str(len(list_data)))

            return json.dumps({"list": list_data})

        except Exception as e:

            print('search error: ' + str(e))

            return json.dumps({"list": []})

    def parseList(self, html):

        list_data = []

        seen = set()

        card_regex = re.compile(r'<a[^>]+href=["\']([^"\']*\/watch\/[^"\']+)["\'][^>]*>([\s\S]*?)</a>', re.I)

        for m in card_regex.finditer(html):

            href = m.group(1)

            inner = m.group(2)

            if href in seen:

                continue

            seen.add(href)

            img_match = re.search(r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)["\']', inner, re.I)

            pic = img_match.group(1).replace('&amp;', '&') if img_match else ''

            if pic.startswith('data:image/gif'):

                pic = ''

            title_match = re.search(r'alt=["\']([^"\']+)["\']', inner, re.I) or re.search(r'title=["\']([^"\']+)["\']', inner, re.I)

            title = title_match.group(1).strip() if title_match else ''

            if not title:

                a_title = re.search(r'title=["\']([^"\']+)["\']', m.group(0), re.I)

                if a_title:

                    title = a_title.group(1).strip()

            if not title:

                title = re.sub(r'<[^>]+>', '', inner).strip()[:200]

            if not title:

                continue

            vod_id = re.sub(r'^.*\/watch\/', '', href)

            vod_id = re.sub(r'[\/?#].*$', '', vod_id)

            list_data.append({

                "vod_id": vod_id,

                "vod_name": title,

                "vod_pic": pic,

                "vod_remarks": ""

            })

        return list_data