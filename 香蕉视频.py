# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import time
import urllib.parse
import re
import requests
from lxml import etree

class Spider(Spider):

    def getName(self):
        return "香蕉视频"

    def init(self, extend=""):
        # 主域名列表，按优先级排列（同类站点常换域名，预留备用）
        self.host_list = [
            "https://618013.xyz",
            "https://618041.xyz",
            "https://618042.xyz",
            "https://618043.xyz",
        ]
        self.host = self.host_list[0]
        self.api_host = "https://h5.xxoo168.org"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': self.host,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        self.log(f"香蕉视频爬虫初始化完成，主站: {self.host}")

    def html(self, content):
        """将HTML内容转换为可查询的对象"""
        if not content:
            self.log("HTML内容为空")
            return None
        try:
            # 如果内容是bytes，先解码
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            return etree.HTML(content)
        except Exception as e:
            self.log(f"HTML解析失败: {str(e)}")
            return None

    def regStr(self, pattern, string, index=1):
        """正则表达式提取字符串"""
        try:
            match = re.search(pattern, string, re.IGNORECASE)
            if match and len(match.groups()) >= index:
                return match.group(index)
        except:
            pass
        return ""

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        """获取首页内容和分类"""
        result = {}
        classes = [
            {'type_id': '618013.xyz_1', 'type_name': '全部视频'},
            {'type_id': '618013.xyz_13', 'type_name': '香蕉精品'},
            {'type_id': '618013.xyz_22', 'type_name': '制服诱惑'},
            {'type_id': '618013.xyz_6', 'type_name': '国产视频'},
            {'type_id': '618013.xyz_8', 'type_name': '清纯少女'},
            {'type_id': '618013.xyz_9', 'type_name': '辣妹大奶'},
            {'type_id': '618013.xyz_10', 'type_name': '女同专属'},
            {'type_id': '618013.xyz_11', 'type_name': '素人出演'},
            {'type_id': '618013.xyz_12', 'type_name': '角色扮演'},
            {'type_id': '618013.xyz_20', 'type_name': '人妻熟女'},
            {'type_id': '618013.xyz_23', 'type_name': '日韩剧情'},
            {'type_id': '618013.xyz_21', 'type_name': '经典伦理'},
            {'type_id': '618013.xyz_7', 'type_name': '成人动漫'},
            {'type_id': '618013.xyz_14', 'type_name': '精品二区'},
            {'type_id': '618013.xyz_40', 'type_name': '精品三区'},
            {'type_id': '618013.xyz_53', 'type_name': '动漫中字'},
            {'type_id': '618013.xyz_52', 'type_name': '日本无码'},
            {'type_id': '618013.xyz_33', 'type_name': '中文字幕'},
            {'type_id': '618013.xyz_44', 'type_name': '国产传媒'},
            {'type_id': '618013.xyz_32', 'type_name': '国产自拍'}
        ]
        result['class'] = classes
        try:
            rsp = self.fetch(self.host, headers=self.headers, timeout=15)
            if not rsp or rsp.status_code != 200:
                self.log(f"首页请求失败，状态码: {rsp.status_code if rsp else 'None'}")
                result['list'] = []
                return result
            self.log(f"首页响应状态码: {rsp.status_code}, 内容长度: {len(rsp.text) if hasattr(rsp, 'text') else 0}")
            doc = self.html(rsp.text)
            videos = self._get_videos(doc, limit=20)
            self.log(f"首页解析到 {len(videos)} 个视频")
            result['list'] = videos
        except Exception as e:
            self.log(f"首页获取出错: {str(e)}")
            result['list'] = []
        return result

    def homeVideoContent(self):
        """分类定义 - 兼容性方法"""
        return {
            'class': [
                {'type_id': '618013.xyz_1', 'type_name': '全部视频'},
                {'type_id': '618013.xyz_13', 'type_name': '香蕉精品'},
                {'type_id': '618013.xyz_22', 'type_name': '制服诱惑'},
                {'type_id': '618013.xyz_6', 'type_name': '国产视频'},
                {'type_id': '618013.xyz_8', 'type_name': '清纯少女'},
                {'type_id': '618013.xyz_9', 'type_name': '辣妹大奶'},
                {'type_id': '618013.xyz_10', 'type_name': '女同专属'},
                {'type_id': '618013.xyz_11', 'type_name': '素人出演'},
                {'type_id': '618013.xyz_12', 'type_name': '角色扮演'},
                {'type_id': '618013.xyz_20', 'type_name': '人妻熟女'},
                {'type_id': '618013.xyz_23', 'type_name': '日韩剧情'},
                {'type_id': '618013.xyz_21', 'type_name': '经典伦理'},
                {'type_id': '618013.xyz_7', 'type_name': '成人动漫'},
                {'type_id': '618013.xyz_14', 'type_name': '精品二区'},
                {'type_id': '618013.xyz_40', 'type_name': '精品三区'},
                {'type_id': '618013.xyz_53', 'type_name': '动漫中字'},
                {'type_id': '618013.xyz_52', 'type_name': '日本无码'},
                {'type_id': '618013.xyz_33', 'type_name': '中文字幕'},
                {'type_id': '618013.xyz_44', 'type_name': '国产传媒'},
                {'type_id': '618013.xyz_32', 'type_name': '国产自拍'}
            ]
        }

    def categoryContent(self, tid, pg, filter, extend):
        """分类内容 - 增强版，增加错误处理和日志"""
        try:
            domain, type_id = tid.split('_')
            url = f"https://{domain}/index.php/vod/type/id/{type_id}.html"
            if pg and str(pg) != '1':
                url = url.replace('.html', f'/page/{pg}.html')

            self.log(f"访问分类URL: {url}")

            # 更新Referer为当前请求域名
            headers = self.headers.copy()
            headers['Referer'] = f"https://{domain}/"

            rsp = self.fetch(url, headers=headers, timeout=15)

            if not rsp:
                self.log("分类请求无响应")
                return {'list': [], 'page': int(pg), 'pagecount': 0, 'limit': 20, 'total': 0}

            self.log(f"分类响应状态码: {rsp.status_code}")

            if rsp.status_code != 200:
                self.log(f"分类请求失败，状态码: {rsp.status_code}")
                # 尝试打印部分响应内容用于调试
                if hasattr(rsp, 'text') and rsp.text:
                    preview = rsp.text[:200] if len(rsp.text) > 200 else rsp.text
                    self.log(f"响应内容预览: {preview}")
                return {'list': [], 'page': int(pg), 'pagecount': 0, 'limit': 20, 'total': 0}

            content = rsp.text if hasattr(rsp, 'text') else ''
            self.log(f"分类响应内容长度: {len(content)}")

            if not content or len(content) < 100:
                self.log("分类响应内容为空或太短")
                return {'list': [], 'page': int(pg), 'pagecount': 0, 'limit': 20, 'total': 0}

            doc = self.html(content)
            if doc is None:
                self.log("分类HTML解析失败")
                return {'list': [], 'page': int(pg), 'pagecount': 0, 'limit': 20, 'total': 0}

            videos = self._get_videos(doc, limit=20)
            self.log(f"分类解析到 {len(videos)} 个视频")

            # 如果解析不到视频，尝试打印HTML片段用于调试
            if not videos:
                html_preview = content[:500] if len(content) > 500 else content
                self.log(f"未解析到视频，HTML前500字符: {html_preview}")

            # 使用固定页数设置
            pagecount = 999
            total = 19980

            return {
                'list': videos,
                'page': int(pg),
                'pagecount': pagecount,
                'limit': 20,
                'total': total
            }
        except Exception as e:
            self.log(f"分类内容获取出错: {str(e)}")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}")
            return {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 0, 'limit': 20, 'total': 0}

    def searchContent(self, key, quick, pg="1"):
        """搜索功能"""
        try:
            search_url = f"{self.host}/index.php/vod/search.html?wd={urllib.parse.quote(key)}&page={pg}"
            self.log(f"搜索URL: {search_url}")
            rsp = self.fetch(search_url, headers=self.headers, timeout=15)
            if not rsp or rsp.status_code != 200:
                return {'list': []}
            doc = self.html(rsp.text)
            videos = self._get_videos(doc)
            return {'list': videos}
        except Exception as e:
            self.log(f"搜索出错: {str(e)}")
            return {'list': []}

    def detailContent(self, ids):
        """详情页面"""
        try:
            vid = ids[0]
            if '_' in vid:
                domain, video_id = vid.split('_')
                detail_url = f"https://{domain}/index.php/vod/detail/id/{video_id}.html"
            else:
                detail_url = f"{self.host}/index.php/vod/detail/id/{vid}.html"
            self.log(f"访问详情URL: {detail_url}")
            rsp = self.fetch(detail_url, headers=self.headers, timeout=15)
            if not rsp or rsp.status_code != 200:
                return {'list': []}
            doc = self.html(rsp.text)
            video_info = self._get_detail(doc, vid)
            return {'list': [video_info]} if video_info else {'list': []}
        except Exception as e:
            self.log(f"详情获取出错: {str(e)}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        """播放链接 - 直接使用API获取视频地址"""
        try:
            self.log(f"获取播放链接: flag={flag}, id={id}")

            if '_' in id:
                _, video_id = id.split('_')
            else:
                video_id = id

            self.log(f"视频ID: {video_id}")

            api_url = f"{self.api_host}/api/v2/vod/reqplay/{video_id}"
            self.log(f"请求API获取视频地址: {api_url}")

            api_headers = self.headers.copy()
            api_headers.update({
                'Referer': f"{self.host}/",
                'Origin': self.host,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
            })

            api_response = self.fetch(api_url, headers=api_headers, timeout=15)
            if api_response and api_response.status_code == 200:
                try:
                    data = api_response.json()
                    self.log(f"API响应: {json.dumps(data, ensure_ascii=False)[:200]}")

                    if data.get('retcode') == 3:
                        video_url = data.get('data', {}).get('httpurl_preview', '')
                    else:
                        video_url = data.get('data', {}).get('httpurl', '')

                    if video_url:
                        video_url = video_url.replace('?300', '')
                        self.log(f"从API获取到视频地址: {video_url}")
                        return {'parse': 0, 'playUrl': '', 'url': video_url}
                    else:
                        self.log("API响应中没有找到视频地址")
                except Exception as e:
                    self.log(f"API响应解析失败: {str(e)}")
            else:
                self.log(f"API请求失败，状态码: {api_response.status_code if api_response else '无响应'}")

            # 如果API请求失败，回退到原来的方法
            if '_' in id:
                domain, play_id = id.split('_')
                play_url = f"https://{domain}/html/kkyd.html?m={play_id}"
            else:
                play_url = f"{self.host}/html/kkyd.html?m={id}"

            self.log(f"回退到播放页面: {play_url}")
            return {'parse': 1, 'playUrl': '', 'url': play_url}

        except Exception as e:
            self.log(f"播放链接获取出错: {str(e)}")
            if '_' in id:
                domain, play_id = id.split('_')
                play_url = f"https://{domain}/html/kkyd.html?m={play_id}"
            else:
                play_url = f"{self.host}/html/kkyd.html?m={id}"
            return {'parse': 1, 'playUrl': '', 'url': play_url}

    # ========== 辅助方法 ==========

    def _get_videos(self, doc, limit=None):
        """获取影片列表 - 增强版，支持多种选择器"""
        try:
            if doc is None:
                self.log("_get_videos: doc为None")
                return []

            videos = []

            # 尝试多种XPath选择器（网站可能改版类名）
            selectors = [
                '//a[@class="vodbox"]',
                '//a[contains(@class, "vodbox")]',
                '//div[contains(@class, "vodbox")]//a',
                '//div[@class="video-item"]//a',
                '//div[@class="item"]//a',
                '//li//a[contains(@href, "m=")]',
                '//a[contains(@href, "/vod/detail/id/")]',
            ]

            elements = []
            used_selector = ""
            for selector in selectors:
                elements = doc.xpath(selector)
                if elements:
                    used_selector = selector
                    break

            self.log(f"使用选择器 [{used_selector}] 找到 {len(elements)} 个元素")

            for elem in elements:
                video = self._extract_video(elem)
                if video:
                    videos.append(video)

            self.log(f"成功提取 {len(videos)} 个视频信息")
            return videos[:limit] if limit and videos else videos
        except Exception as e:
            self.log(f"获取影片列表出错: {str(e)}")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}")
            return []

    def _extract_video(self, element):
        """提取影片信息 - 增强版，增加容错"""
        try:
            # 1. 提取影片链接
            link_list = element.xpath('./@href')
            if not link_list:
                # 尝试从父元素获取
                link_list = element.xpath('.//@href')

            if not link_list:
                return None

            link = link_list[0]
            if link.startswith('/'):
                link = self.host + link

            # 2. 提取vod_id
            vod_id = self.regStr(r'm=(\d+)', link)
            if not vod_id:
                vod_id = self.regStr(r'/id/(\d+)\.html', link)
            if not vod_id:
                vod_id = str(hash(link) % 1000000)

            # 3. 提取标题 - 尝试多种方式
            title = ""
            title_selectors = [
                './p[@class="km-script"]/text()',
                './/p[contains(@class, "script")]/text()',
                './/p/text()',
                './/h3/text()',
                './/h4/text()',
                './/h5/text()',
                './/span[@class="title"]/text()',
                './/img/@alt',
                './@title',
                './/text()',
            ]

            for selector in title_selectors:
                title_elem = element.xpath(selector)
                if title_elem:
                    title = title_elem[0].strip() if isinstance(title_elem[0], str) else str(title_elem[0]).strip()
                    if title:
                        break

            if not title:
                self.log(f"未找到标题元素，跳过该视频, link={link}")
                return None

            # 尝试解密标题（如果是加密格式）
            if title and len(title) > 0:
                decrypted = self._decrypt_title(title)
                if decrypted and decrypted != title:
                    title = decrypted

            # 4. 提取封面图
            pic = ""
            pic_selectors = [
                './/img/@data-original',
                './/img/@src',
                './/img/@data-src',
                './/div[@class="img"]//img/@src',
            ]
            for selector in pic_selectors:
                pic_elem = element.xpath(selector)
                if pic_elem:
                    pic = pic_elem[0]
                    break

            # 补全图片URL
            if pic:
                if pic.startswith('//'):
                    pic = 'https:' + pic
                elif pic.startswith('/'):
                    pic = self.host + pic

            # 5. 提取时长/备注
            remarks = ""
            remarks_selectors = [
                './/span[@class="time"]/text()',
                './/span[@class="duration"]/text()',
                './/p[@class="meta"]/text()',
            ]
            for selector in remarks_selectors:
                rem_elem = element.xpath(selector)
                if rem_elem:
                    remarks = rem_elem[0].strip()
                    break

            return {
                'vod_id': f"618013.xyz_{vod_id}",
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'vod_year': ''
            }
        except Exception as e:
            self.log(f"提取影片信息出错: {str(e)}")
            return None

    def _decrypt_title(self, encrypted_text):
        """解密标题 - 使用网站的解密算法"""
        try:
            if not encrypted_text:
                return encrypted_text
            decrypted_chars = []
            for char in encrypted_text:
                code_point = ord(char)
                decrypted_code = code_point ^ 128
                decrypted_char = chr(decrypted_code)
                decrypted_chars.append(decrypted_char)
            decrypted_text = ''.join(decrypted_chars)
            return decrypted_text
        except Exception as e:
            self.log(f"标题解密失败: {str(e)}")
            return encrypted_text

    def _get_detail(self, doc, vid):
        """获取详情信息 (优化版)"""
        try:
            title = self._get_text(doc, ['//h1/text()', '//title/text()', '//h2/text()'])
            pic = self._get_text(doc, ['//div[@class="dyimg"]//img/@src', '//img[@class="poster"]/@src', '//div[@class="thumb"]//img/@src'])
            if pic and pic.startswith('/'):
                pic = self.host + pic
            desc = self._get_text(doc, ['//div[@class="yp_context"]/text()', '//div[@class="introduction"]//text()', '//div[@class="desc"]//text()'])
            actor = self._get_text(doc, ['//span[contains(text(),"主演")]/following-sibling::*/text()', '//span[contains(text(),"演员")]/following-sibling::*/text()'])
            director = self._get_text(doc, ['//span[contains(text(),"导演")]/following-sibling::*/text()'])

            play_from = []
            play_urls = []

            # 尝试查找播放源
            play_links = doc.xpath('//a[contains(@href, "m=")]')
            if not play_links:
                play_links = doc.xpath('//a[contains(@href, "/vod/play/id/")]')

            if play_links:
                episodes = []
                for link in play_links:
                    ep_title = link.xpath('./text()')
                    ep_href = link.xpath('./@href')[0] if link.xpath('./@href') else ''
                    if ep_title:
                        ep_title = ep_title[0].strip()
                        play_id = self.regStr(r'm=(\d+)', ep_href)
                        if not play_id:
                            play_id = self.regStr(r'/id/(\d+)', ep_href)
                        if play_id:
                            episodes.append(f"{ep_title}${play_id}")

                if episodes:
                    play_from.append("默认播放源")
                    play_urls.append('#'.join(episodes))

            if not play_from:
                self.log("未找到播放源元素，使用默认")
                return {
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'type_name': '',
                    'vod_year': '',
                    'vod_area': '',
                    'vod_remarks': '',
                    'vod_actor': actor,
                    'vod_director': director,
                    'vod_content': desc,
                    'vod_play_from': '默认播放源',
                    'vod_play_url': f"第1集${vid}"
                }

            return {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': '',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_urls)
            }
        except Exception as e:
            self.log(f"获取详情出错: {str(e)}")
            return None

    def _get_text(self, doc, selectors):
        """通用文本提取"""
        if doc is None:
            return ''
        for selector in selectors:
            try:
                texts = doc.xpath(selector)
                for text in texts:
                    if text and str(text).strip():
                        return str(text).strip()
            except:
                continue
        return ''
