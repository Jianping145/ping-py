import sys
import re
import requests
from bs4 import BeautifulSoup
from base.spider import Spider
from urllib.parse import urljoin, quote, unquote

class Spider(Spider):
    def getName(self):
        return "WhosTV"

    def init(self, extend=""):
        self.host = "https://whos.tv"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": self.host
        }

    def _decode_cover(self, encoded):
        """解密 data-cover-src（还原前端 coolDecrypt 函数）"""
        if not encoded:
            return ""
        try:
            key_hex = encoded[-2:]
            key = int(key_hex, 16)
            data_hex = encoded[:-2]
            chars = []
            for i in range(0, len(data_hex), 2):
                byte_val = int(data_hex[i:i+2], 16)
                chars.append(chr(byte_val ^ key))
            return ''.join(chars)
        except:
            return ""


    def homeContent(self, filter):
        result = {}
        result['class'] = [
            {'type_name': '影片库', 'type_id': '/videos'},
            {'type_name': '女优库', 'type_id': '/actresses'},
            {'type_name': '服装', 'type_id': '/frames/type-clothes?dim=1'},
            {'type_name': '地点', 'type_id': '/frames/type-location?dim=2'},
            {'type_name': '特写', 'type_id': '/frames/type-closeup?dim=3'},
            {'type_name': '姿势', 'type_id': '/frames/type-pose?dim=4'},
            {'type_name': '行为', 'type_id': '/frames/type-action?dim=5'},
            {'type_name': '表情', 'type_id': '/frames/type-expression?dim=6'},
            {'type_name': '道具', 'type_id': '/frames/type-prop?dim=7'},
            {'type_name': '其他', 'type_id': '/frames/type-other?dim=8'},
        ]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        # 处理带查询参数的分页，例如 /frames/type-clothes?dim=1 → /frames/type-clothes/page-2?dim=1
        if '?' in tid:
            path, query = tid.split('?', 1)
            url = f"{self.host}{path}"
            if int(pg) > 1:
                url += f"/page-{pg}"
            url += f"?{query}"
        else:
            url = f"{self.host}{tid}"
            if int(pg) > 1:
                url += f"/page-{pg}"

        rsp = self.fetch(url, headers=self.header)
        soup = BeautifulSoup(rsp.text, 'html.parser')
        videos = []

        # 女优名录页
        if tid == "/actresses":
            items = soup.find_all('a', href=re.compile(r'^/actresses/.'))
            for item in items:
                img = item.find('img')
                if not img:
                    continue
                name = img.get('alt', '').strip()
                href = item.get('href')
                if not name or href == "/actresses" or "page-" in href:
                    continue
                pic_url = img.get('src', '')
                count_text = ""
                icon_span = item.find('span', class_=re.compile(r'icon-\[lucide--film\]'))
                if icon_span:
                    parent_flex = icon_span.find_parent('span', class_='flex')
                    if parent_flex:
                        count_text = parent_flex.get_text(strip=True) + "部作品"
                videos.append({
                    "vod_id": href,
                    "vod_name": name,
                    "vod_pic": pic_url,
                    "vod_remarks": count_text if count_text else "作品集",
                    "vod_tag": "folder"
                })
        # 女优个人页作品列表：结构为 a[href=/videos/xxx] + data-cover-src + h3
        elif tid.startswith("/actresses/"):
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a.get("href") or ""
                if "/videos/" not in href:
                    continue
                if href.startswith("http"):
                    href = href.replace(self.host, "")
                if not href.startswith("/"):
                    href = "/" + href
                href = href.split("?")[0].split("#")[0]
                if href in seen or href.rstrip("/").endswith("/videos"):
                    continue
                slug = href.split("/")[-1]
                if not slug or slug.startswith("page-"):
                    continue
                h3 = a.find("h3")
                v_name = h3.get_text(strip=True) if h3 else slug.upper()
                real_pic = ""
                div_cover = a.find("div", attrs={"data-cover-src": True})
                if div_cover:
                    real_pic = self._decode_cover(div_cover.get("data-cover-src"))
                if not real_pic:
                    img = a.find("img")
                    if img:
                        real_pic = img.get("src") or img.get("data-src") or ""
                seen.add(href)
                videos.append({
                    "vod_id": href,
                    "vod_name": v_name,
                    "vod_pic": real_pic,
                    "vod_remarks": slug
                })
            # 兜底：从原文抽 /videos/slug
            if not videos:
                for m in re.finditer(r'/videos/([A-Za-z0-9][A-Za-z0-9\-_]{1,80})', rsp.text):
                    slug = m.group(1)
                    if slug.startswith("page-"):
                        continue
                    href = "/videos/" + slug.lower()
                    if href in seen:
                        continue
                    seen.add(href)
                    videos.append({
                        "vod_id": href,
                        "vod_name": slug.upper(),
                        "vod_pic": "",
                        "vod_remarks": slug
                    })
        # 影片网格页 / 帧分类页
        else:
            items = soup.find_all('a', href=re.compile(r'(?:^|/)(videos|frames)/[^"\s]+'))
            for item in items:
                h3 = item.find('h3')
                v_name = h3.get_text(strip=True) if h3 else (item.get('title') or item.get('alt') or '')
                if not v_name:
                    # 有些帧卡片 a 标签内只有图片，标题在兄弟或父级
                    parent = item.parent
                    if parent:
                        h3 = parent.find('h3')
                        if h3:
                            v_name = h3.get_text(strip=True)
                if not v_name:
                    continue
                real_pic = ""
                # 优先使用 data-cover-src 解密（影片页常用）
                div_cover = item.find('div', attrs={'data-cover-src': True}) or (item.parent.find('div', attrs={'data-cover-src': True}) if item.parent else None)
                if div_cover:
                    encoded = div_cover.get('data-cover-src')
                    real_pic = self._decode_cover(encoded)
                # 帧分类页可能使用普通 img 或 data-src / data-lazy-src
                if not real_pic:
                    img = item.find('img') or (item.parent.find('img') if item.parent else None)
                    if img:
                        real_pic = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original') or ""
                # 再尝试 background-image 或 style 中的 url
                if not real_pic:
                    for cand in [item, item.parent] if item.parent else [item]:
                        style_div = cand.find(attrs={'style': re.compile(r'background-image|url\(')}) if hasattr(cand, 'find') else None
                        if style_div:
                            style = style_div.get('style', '')
                            m = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
                            if m:
                                real_pic = m.group(1)
                                break
                        # 自身 style
                        style = cand.get('style', '') if hasattr(cand, 'get') else ''
                        if style:
                            m = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
                            if m:
                                real_pic = m.group(1)
                                break
                # 最后尝试任意带 data-*-src / cover 的属性
                if not real_pic:
                    search_roots = [item]
                    if item.parent:
                        search_roots.append(item.parent)
                    for root in search_roots:
                        for tag in root.find_all(True):
                            for attr, val in list(tag.attrs.items()):
                                if isinstance(val, str) and ('src' in attr.lower() or 'cover' in attr.lower()) and (val.startswith('http') or val.startswith('/')):
                                    real_pic = val
                                    break
                            if real_pic:
                                break
                        if real_pic:
                            break
                href = item.get('href', '') or ''
                if href.startswith('http'):
                    href = href.replace(self.host, '')
                if href and not href.startswith('/'):
                    href = '/' + href

                remarks = self.regStr(v_name, r'([A-Z0-9]+-[0-9]+)')
                # 帧分类：标题形如「SOAN-002 · 0:25:20」，没有独立播放源
                # 必须改成 /videos/番号，才能走和「影片库」一样的详情与播放
                if '/frames/' in href or (tid and '/frames/' in str(tid)):
                    if '·' in v_name:
                        parts = [p.strip() for p in v_name.split('·')]
                        code = parts[0]
                        if len(parts) > 1:
                            remarks = parts[-1]
                    else:
                        mcode = re.search(r'([A-Za-z0-9][A-Za-z0-9\-_]{2,80})', v_name)
                        code = remarks or (mcode.group(1) if mcode else "")
                    if code:
                        # 去掉可能的多余空格，统一小写路径
                        code = re.sub(r'\s+', '', code)
                        href = '/videos/' + code.lower()
                    # 若仍拿不到番号，保留原 frame 链接，详情里再兜底

                videos.append({
                    "vod_id": href,
                    "vod_name": v_name,
                    "vod_pic": real_pic,
                    "vod_remarks": remarks if remarks else ""
                })

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 999
        result['limit'] = len(videos)
        result['total'] = 9999

        if tid.startswith("/actresses/"):
            h1_tag = soup.find('h1')
            if h1_tag:
                result['type_name'] = h1_tag.get_text(strip=True)
        return result

    def detailContent(self, ids):
        vodId = ids[0]
        if vodId.startswith("/actresses/"):
            return self.categoryContent(vodId, "1", None, None)

        url = self.host + vodId
        rsp = self.fetch(url, headers=self.header)
        soup = BeautifulSoup(rsp.text, 'html.parser')

        title_meta = soup.find('meta', property="og:title")
        title = title_meta.get('content') if title_meta else ""
        if not title:
            h1 = soup.find('h1')
            title = h1.get_text(strip=True) if h1 else vodId
        # 验证页/加载页不能当详情
        if title in ("请稍候...", "请稍候…", "Just a moment...", "Just a moment…"):
            title = vodId

        pic_meta = soup.find('meta', property="og:image")
        pic = pic_meta.get('content') if pic_meta else ""

        def _pick_play(page_soup, raw_text):
            source = page_soup.find('source', type="application/x-mpegURL")
            if source and source.get('src'):
                return source.get('src')
            source = page_soup.find('source', src=True)
            if source and source.get('src'):
                return source.get('src')
            video_tag = page_soup.find('video', src=True)
            if video_tag and video_tag.get('src'):
                return video_tag.get('src')
            m = re.search(r'https?://[^"\'\s>]+\.m3u8[^"\'\s>]*', raw_text or "")
            return m.group(0) if m else ""

        play_url = ""
        start_seconds = 0

        # 帧详情页：需要跳转到对应影片页拿 m3u8，并解析起始时间
        if vodId.startswith("/frames/"):
            # 从标题或页面提取时间戳 0:01:05 / 1:22:45
            time_match = re.search(r'(\d{1,2}):(\d{2}):(\d{2})', title) or re.search(r'(\d{1,2}):(\d{2}):(\d{2})', rsp.text[:5000])
            if time_match:
                h, m, s = map(int, time_match.groups())
                start_seconds = h * 3600 + m * 60 + s

            # 优先找「从此帧播放」链接（通常指向影片页）
            play_btn = soup.find('a', string=re.compile(r'从此帧播放|Play from this frame|從此影格播放|从此影格播放'))
            video_path = None
            if play_btn and play_btn.get('href'):
                video_path = play_btn.get('href')
            if not video_path:
                # 页面上常见的影片链接
                video_link = soup.find('a', href=re.compile(r'^/videos/[^"\s]+'))
                if video_link:
                    video_path = video_link.get('href')
            if not video_path:
                # 从标题前缀提取番号，拼成 /videos/xxx
                code_match = re.search(r'^([A-Za-z0-9\-]+)', title.strip())
                if code_match:
                    video_path = f"/videos/{code_match.group(1).lower()}"

            if video_path:
                if video_path.startswith('http'):
                    video_path = video_path.replace(self.host, '')
                if not video_path.startswith('/'):
                    video_path = '/' + video_path
                # 去掉可能的 query / hash，保留路径
                video_path = video_path.split('?')[0].split('#')[0]

                # 拉取影片页获取真正的播放地址
                v_rsp = self.fetch(self.host + video_path, headers=self.header)
                v_soup = BeautifulSoup(v_rsp.text, 'html.parser')
                play_url = _pick_play(v_soup, v_rsp.text)

                # 补充演员/标签（用影片页的更全）
                actor_tags = v_soup.select('a[href^="/actresses/"]')
                actors = ",".join([a.get_text(strip=True) for a in actor_tags if a.get_text(strip=True)])
                tag_tags = v_soup.select('a[href^="/tags/"] span.truncate')
                tags = ",".join([t.get_text(strip=True) for t in tag_tags])
            else:
                actors = ""
                tags = ""
        else:
            play_url = _pick_play(soup, rsp.text)

            actor_tags = soup.select('a[href^="/actresses/"]')
            actors = ",".join([a.get_text(strip=True) for a in actor_tags if a.get_text(strip=True)])
            tag_tags = soup.select('a[href^="/tags/"] span.truncate')
            tags = ",".join([t.get_text(strip=True) for t in tag_tags])

        # 若有起始时间，尝试追加到播放地址（部分播放器支持 #t= 或 ?t=）
        if play_url and start_seconds > 0:
            # 多数 HLS 播放器支持 #t=seconds
            if '#' not in play_url:
                play_url = play_url + f"#t={start_seconds}"
            else:
                play_url = play_url + f"&t={start_seconds}"

        vod = {
            "vod_id": vodId,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": tags,
            "vod_actor": actors,
            "vod_content": title,
            "vod_play_from": "WhosTV",
            "vod_play_url": "全高清$" + play_url if play_url else ""
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": "https://whos.tv/",
                "Origin": "https://whos.tv"
            }
        }

    def searchContent(self, key, quick):
        url = f"{self.host}/result?serach={key}"
        rsp = self.fetch(url, headers=self.header)
        soup = BeautifulSoup(rsp.text, 'html.parser')
        videos = []

        items = soup.find_all('a', href=re.compile(r'^/videos/.'))
        for item in items:
            h3 = item.find('h3')
            if h3:
                v_name = h3.get_text(strip=True)
                div_cover = item.find('div', attrs={'data-cover-src': True})
                if div_cover:
                    encoded = div_cover.get('data-cover-src')
                    real_pic = self._decode_cover(encoded)
                else:
                    real_pic = ""
                real_pic = real_pic
                remarks = self.regStr(v_name, r'([A-Z0-9]+-[0-9]+)')
                videos.append({
                    "vod_id": item.get('href'),
                    "vod_name": v_name,
                    "vod_pic": real_pic,
                    "vod_remarks": remarks if remarks else ""
                })
        return {"list": videos}
