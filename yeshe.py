#coding=utf-8
#!/usr/bin/python
import sys, os, time, re, json, base64, urllib.request, urllib.parse, urllib.error, ssl
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from base.spider import Spider
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"zh-CN,zh;q=0.9"}

class Spider(Spider):
    def getName(self):return "yeshe"
    def init(self, extend=""):
        self.H = "https://xn--9hsjt4-9k8ope792un7wa.hnsxdnyjyjcyjfkzx.org:7982"
        self.T = 20
    def isVideoFormat(self, u):return bool(re.search(r'\.(m3u8|mp4|flv|ts|mkv|avi)(\?|$)', u, re.I))
    def manualVideoCheck(self):return False

    def _get(self, url, timeout=20):
        req = urllib.request.Request(url, headers=dict(HEADERS))
        return urllib.request.urlopen(req, timeout=timeout, context=CTX).read().decode('utf-8', errors='replace')

    def _decode(self, raw):
        if not raw:return ""
        m = re.search(r'var\s+a\s*=\s*"(.+?)"', raw)
        if m:
            try:return base64.b64decode(m.group(1)).decode('utf-8', errors='replace')
            except:pass
        return raw

    def _req(self, url, n=0):
        if n >= 3:return None
        try:
            raw = self._get(url, self.T)
            if not raw or (raw[:2000].find('\u7cfb\u7edf\u63d0\u793a') >= 0):
                time.sleep(1);return self._req(url, n+1)
            return self._decode(raw)
        except:
            time.sleep(1);return self._req(url, n+1)

    def _cov(self, u):
        if not u:return ""
        if u.startswith("//"):u = "https:" + u
        if u.startswith("http"):return f"{self.getProxyUrl()}&url={urllib.parse.quote(u)}&type=img"
        return u

    CARD_RE = re.compile(r'<a\s+href="([^"]+)"\s*title="([^"]+)"[^>]*class="[^"]*module-poster-item[^"]*"[^>]*>(.*?)</a>', re.S)
    NOVEL = {"25","26","27","28","29","30"}
    NOVEL_PARENT = "6"
    CATE = {
        "\u89c6\u9891":{"id":"2","children":{"13":"AI\u77ed\u5267","11":"\u56fd\u4ea7\u89c6\u9891","12":"\u65e5\u672cAV","14":"\u6b27\u7f8e\u65e0\u7801","35":"\u97e9\u56fdBJ"}},
        "\u52a8\u6f2b":{"id":"1","children":{"7":"\u540c\u4eba\u4f5c\u54c1","8":"\u52a8\u753b\u5361\u901a","10":"3D\u52a8\u6f2b","9":"\u4e2d\u6587\u52a8\u6f2b","32":"\u91cc\u756a","33":"\u6ce1\u9762\u756a"}},
        "\u6709\u58f0":{"id":"3","children":{"15":"\u6709\u58f0\u5c0f\u8bf4","16":"\u6deb\u8bcd\u8273\u66f2","17":"\u6fc0\u60c5\u9a9a\u9ea6"}},
        "\u6f2b\u753b":{"id":"4","children":{"18":"\u97e9\u56fdH\u6f2b","19":"\u65e5\u672cH\u6f2b","31":"3D\u6f2b\u753b"}},
        "\u5199\u771f":{"id":"5","children":{"20":"\u79c0\u4eba\u7cfb\u5217","22":"\u7f51\u7ea2COS","21":"\u673a\u6784\u5957\u56fe","23":"\u5185\u8d2d\u79c1\u62cd","34":"AI\u7ed8\u56fe","24":"\u5404\u56fd\u5957\u56fe"}},
        "\u5c0f\u8bf4":{"id":"6","children":{"25":"\u90fd\u5e02\u751f\u6d3b","26":"\u5b66\u751f\u6821\u56ed","27":"\u5bb6\u5ead\u4e71\u4f26","28":"\u7384\u5e7b\u6b66\u4fa0","29":"\u7cfb\u7edf\u7a7f\u8d8a","30":"\u540c\u4eba\u6539\u7f16"}}
    }

    def homeContent(self, filter):
        cls = []
        filters = {}
        for p, i in self.CATE.items():
            tid = i["id"]
            # 子分类列表（带"全部"）
            ch = [{"type_id": "", "type_name": "全部"}] + [{"type_id": t, "type_name": n} for t, n in i["children"].items()]
            ch_alt = [{"id": "", "name": "全部"}] + [{"id": t, "name": n} for t, n in i["children"].items()]
            # 主分类：保留多种子分类字段格式，尽可能兼容不同客户端
            cls.append({
                "type_id": tid,
                "type_name": p,
                "type_flag": "0",
                "type_extend": ch,
                "type_list": ch,
                "child": ch_alt,
                "children": ch_alt,
                "ratio": 0.75
            })
            # 将子分类也作为独立 class 项追加（带 type_pid）
            # 这样不支持 type_extend 的客户端（如 Fengmi）也能直接看到并点击子分类
            for t, n in i["children"].items():
                cls.append({
                    "type_id": t,
                    "type_name": n,
                    "type_flag": "0",
                    "type_pid": tid,
                    "ratio": 0.75
                })
            # filters: TVBox分类页面筛选
            filters[tid] = [
                {
                    "key": "type_id",
                    "name": "分类",
                    "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": t} for t, n in i["children"].items()]
                }
            ]
        lst = []
        try:
            h = self._req(self.H + "/")
            if h: lst = self._cards(h)
        except: pass
        return {"class": cls, "filters": filters, "list": lst}

    def homeVideoContent(self):
        lst = []
        try:
            h = self._req(self.H + "/")
            if h:lst = self._cards(h)
        except:pass
        return {"list":lst}

    def _cards(self, html, tid=""):
        out = []
        for href, title, content in self.CARD_RE.findall(html):
            img = re.search(r'<img[^>]*src="([^"]+)"', content)
            pic = img.group(1) if img else ""
            tm = re.search(r'<div\s+class="time"[^>]*>([^<]+)</div>', content)
            rm = tm.group(1).strip() if tm else ""
            ym = re.search(r'<div\s+class="type"[^>]*>([^<]+)</div>', content)
            yn = ym.group(1).strip() if ym else ""
            if href.startswith("/play/"):
                vm = re.match(r'/play/(\d+)/(\d+)/(\d+)\.html', href)
                if vm:out.append({"vod_id":f"{tid}@{vm.group(1)}" if tid else vm.group(1),"vod_name":title,"vod_pic":self._cov(pic),"vod_remarks":rm or yn})
            elif href.startswith("/novel/"):
                vm = re.match(r'/novel/(\d+)\.html', href)
                if vm:out.append({"vod_id":f"novel@{vm.group(1)}","vod_name":title,"vod_pic":self._cov(pic),"vod_remarks":rm or yn})
            elif href.startswith("/detail/"):
                vm = re.match(r'/detail/(\d+)\.html', href)
                if vm:out.append({"vod_id":f"detail@{vm.group(1)}","vod_name":title,"vod_pic":self._cov(pic),"vod_remarks":rm or yn})
        return out

    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid)
        pg = int(pg)

        # 核心修复：如果 extend 里有子分类 type_id，优先使用子分类 id
        real_tid = tid
        if extend and isinstance(extend, dict):
            ext_tid = extend.get("type_id", "")
            if ext_tid and ext_tid != tid:
                real_tid = str(ext_tid)

        is_novel = real_tid == self.NOVEL_PARENT or real_tid in self.NOVEL
        path = "nfilter" if is_novel else "filter"
        base = f"{self.H}/{path}/{real_tid}"

        if pg == 1:
            url = f"{base}.html"
        else:
            url = f"{base}/page/{pg}.html"

        h = self._req(url)
        if not h and pg > 1:
            fallbacks = [
                f"{base}-{pg}.html",
                f"{base}/{pg}.html",
                f"{base}.html?page={pg}",
                f"{base}?page={pg}",
            ]
            for u in fallbacks:
                h = self._req(u)
                if h:
                    break

        lst = self._cards(h, real_tid) if h else []
        pagecount = 999 if lst else pg
        return {"list":lst,"page":pg,"pagecount":pagecount,"limit":30,"total":len(lst)}

    def detailContent(self, ids):
        fid = str(ids[0])
        if fid.startswith("novel@"):return self._d_novel(fid[6:])
        if fid.startswith("detail@"):return self._d_image(fid[7:])
        parts = fid.split("@")
        if len(parts) >= 3 and parts[0].isdigit():return self._d_video(fid)
        return self._d_video(fid)

    def _d_video(self, fid):
        parts = fid.split("@")
        vid = parts[1] if len(parts) >= 2 else parts[0]
        h = self._req(f"{self.H}/play/{vid}/1/1.html")
        if not h:return {"list":[]}
        p = self._pa(h)
        if not p or not p.get("url"):return {"list":[]}
        vd = p.get("vod_data",{})
        name = vd.get("vod_name","")
        pic = self._cov(vd.get("vod_pic",""))
        actor = vd.get("vod_actor","")
        director = vd.get("vod_director","")
        remarks = vd.get("vod_class","")
        from_name = p.get("from","yeshevideo")
        url = p["url"].replace("\\/","/")
        ep_matches = re.findall(r'<a[^>]*href="(/play/'+vid+r'/\d+/\d+\.html)"[^>]*class="link"[^>]*>([^<]+)', h)
        ep_list = []
        for ep_link, ep_name in ep_matches:
            nid_val = ep_link.split("/")[-1].replace('.html','')
            ep_url = re.sub(r'/(\d+)/play\.m3u8$', '/' + nid_val + '/play.m3u8', url)
            ep_list.append(f"\u7b2c{nid_val}\u96c6${ep_url}")
        if not ep_list:
            ep_list = [f"\u6b63\u7247${url}"]
        return {"list":[{"vod_id":fid,"vod_name":name,"vod_pic":pic,"vod_actor":actor,"vod_director":director,"vod_content":"","vod_play_from":from_name,"vod_play_url":"#".join(ep_list),"vod_remarks":remarks,"vod_tag":remarks}]}

    def _d_novel(self, nid):
        h = self._req(f"{self.H}/novel/{nid}.html")
        if not h:return {"list":[]}
        tn = re.search(r'<title>(.*?) - .*?</title>', h)
        oi = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', h)
        od = re.search(r'<meta[^>]*name="description"[^>]*content=["\']([^"\']+)["\']', h)
        ch = re.findall(r'<a[^>]*href="(/nchpter/' + nid + r'/\d+\.html)"[^>]*class="link"[^>]*>([^<]+)', h)
        cl = []
        for c in ch:
            nm = re.sub(r'<[^>]+>','',c[1]).strip()
            if nm:cl.append(f"{nm}${self.H}{c[0]}")
        return {"list":[{"vod_id":f"novel@{nid}","vod_name":tn.group(1).strip() if tn else f"\u5c0f\u8bf4_{nid}","vod_pic":self._cov(oi.group(1) if oi else ""),"vod_actor":"","vod_director":"","vod_content":od.group(1) if od else "","vod_play_from":"yeshevideo","vod_play_url":"#".join(cl) if cl else f"\u6b63\u6587${self.H}/novel/{nid}.html","vod_remarks":f"{len(cl)}\u7ae0","vod_tag":""}]}

    def _d_image(self, did):
        h = self._req(f"{self.H}/detail/{did}.html")
        if not h:return {"list":[]}
        tn = re.search(r'<title>(.*?) - .*?</title>', h)
        oi = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', h)
        od = re.search(r'<meta[^>]*name="description"[^>]*content=["\']([^"\']+)["\']', h)
        imgs = re.findall(r'(?:src|data-src)\s*=\s*"((?:https?://)?[^"\s]+\.(?:jpg|jpeg|png|webp))"', h)
        seen, il = set(), []
        for img in imgs:
            if img.startswith("//"):img = "https:" + img
            if img.startswith("http") and "yestyle" not in img and img not in seen:
                seen.add(img);il.append(f"\u7b2c{len(il)+1}\u5f20${self._cov(img)}")
        return {"list":[{"vod_id":f"detail@{did}","vod_name":tn.group(1).strip() if tn else f"\u56fe\u96c6_{did}","vod_pic":self._cov(oi.group(1) if oi else (il[0].split('$')[1] if il else "")),"vod_actor":"","vod_director":"","vod_content":od.group(1) if od else "","vod_play_from":"yeshevideo","vod_play_url":"#".join(il) if il else f"\u539f\u56fe${self.H}/detail/{did}.html","vod_remarks":f"{len(il)}\u5f20","vod_tag":""}]}

    def _pa(self, html):
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})</script>', html, re.S)
        if not m:return None
        raw = m.group(1).replace("\\/","/").replace('\\"','"')
        raw = re.sub(r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1),16)), raw)
        raw = raw.replace("\\\\","\\")
        try:return json.loads(raw)
        except:return {"url":""}

    def searchContent(self, key, quick, pg="1"):
        h = self._req(f"{self.H}/vod/search/wd/{urllib.parse.quote(key)}.html")
        lst = self._cards(h) if h else []
        return {"list":lst,"page":int(pg),"pagecount":1,"limit":30,"total":len(lst)}

    def searchContentPage(self, key, quick, pg):return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        id = id.replace("\\/","/")
        h = json.dumps({"User-Agent":HEADERS["User-Agent"],"Referer":self.H+"/","Origin":self.H})
        if id.startswith("http"):
            if ".m3u8" in id or self.isVideoFormat(id):return {"parse":0,"url":id,"header":h}
            if re.search(r'\.(jpg|jpeg|png|webp|gif|avif)$', id,re.I):return {"parse":0,"url":id,"header":h}
        return {"parse":1,"url":id,"header":""}

    def localProxy(self, param):
        try:
            url = param.get("url","") if isinstance(param, dict) else urllib.parse.unquote(re.search(r'url=([^&]+)', str(param)).group(1))
            if not url:return [404,"text/plain",b"Not Found",""]
            h = dict(HEADERS);h["Referer"] = self.H + "/"
            h["Origin"] = self.H
            h["Accept"] = "*/*"
            req = urllib.request.Request(url, headers=h)
            resp = urllib.request.urlopen(req, timeout=15, context=CTX)
            data = resp.read()
            ct = resp.headers.get("Content-Type","image/jpeg")
            return [resp.status, ct, data, ""]
        except Exception as e:
            return [500,"text/plain",str(e).encode("utf-8"),""]

    def liveContent(self, url):return {"list":[]}
    def action(self, action):pass
    def destroy(self):pass
