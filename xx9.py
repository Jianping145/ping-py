# -*- coding: utf-8 -*-
# xx9 爬虫 v3
# 日志结论：
# - 列表/详情/播放地址均正常
# - 图片：proxy?do=py 失败 → 加强 localProxy + 直链双轨
# - 播放：国线 key 在 tigerstx.* 易超时 → 海线1优先

import json
import time
import base64
import random
from urllib.parse import quote, unquote

from base.spider import Spider

try:
    from Crypto.Cipher import AES
except Exception:
    try:
        from Cryptodome.Cipher import AES
    except Exception:
        AES = None


class Spider(Spider):

    GATEWAY_POOL = [
        "https://api.t06z4yrtesm736.xyz/fast-endecode/main/request",
        "https://pl5kjl.jas49cht5sqrwet.xyz/fast-endecode/main/request",
        "https://pl5kjl.m93abv5upsv4s8f.xyz/fast-endecode/main/request",
        "https://api.y7hvaad8g.xyz/fast-endecode/main/request",
    ]

    KEYS = {
        0: "G7i3OPcfNhBnAYpc",
        1: "84UZNK33cSVylz6Y",
        2: "jeSWRcTwHyAKwJDB",
        3: "i1hvJx9vuRt5zEBS",
        4: "1Yy1KOa75R7cnmkg",
        6: "T0RVp7KIPamrtQ33",
        8: "ugvseZc5Kkj8ecmV",
        9: "G7i3OPcfNhBnAYpc",
    }
    REM = 2
    ADS_CODE = "DFH"

    # 海线优先（用户实测 allmusiclub 可播；国线 tigerstx 常超时）
    PLAY_LINES = [
        ("海线1", "https://allmusiclub.almusiclub.com"),
        ("国线1", "https://rr.rxjhwl.com"),
        ("国线2", "https://ww.wealwelloa.com"),
        ("国线3", "https://gg.gmdalian.com"),
    ]

    PIC_BASE = "https://qv1.almusiclub.com"

    UA = ("Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

    # 44 个完整分组（groupIds）
    THEMES = [
        ("1", "其他精选"),
        ("2", "国产原创大厂"),
        ("3", "国产JK萝莉"),
        ("4", "国产sm女王"),
        ("5", "国产网红主播"),
        ("6", "国产女同男同"),
        ("7", "国产街拍街顶"),
        ("8", "国产强奸迷奸"),
        ("9", "国产OL丝袜"),
        ("10", "国产乱伦人妻"),
        ("11", "国产其他分类"),
        ("12", "国产偷拍自拍"),
        ("13", "日韩OL人妻"),
        ("14", "日韩强奸迷奸"),
        ("15", "日韩学生素人"),
        ("16", "日韩群交喷射"),
        ("17", "日韩偷拍街拍"),
        ("18", "日韩其他分类"),
        ("19", "日韩同性乐园"),
        ("20", "日韩网红主播"),
        ("22", "日韩肛交sm"),
        ("23", "日韩无码经典"),
        ("24", "日韩中文字幕"),
        ("25", "经典三级片"),
        ("26", "欧美萝莉cos"),
        ("27", "欧美群交混战"),
        ("28", "欧美sm虐待"),
        ("29", "欧美大厂剧情"),
        ("30", "欧美巨乳熟女"),
        ("32", "欧美同性乐园"),
        ("33", "欧美偷拍街拍"),
        ("34", "动漫有码"),
        ("35", "动漫无码"),
        ("36", "动漫字幕"),
        ("37", "动漫3D"),
        ("38", "天堂东南亚"),
        ("39", "印巴裔阿拉伯斯拉夫"),
        ("40", "日韩女优大厂"),
        ("41", "绿帽偷情"),
        ("42", "欧美素人网红"),
        ("43", "欧美肛交口交"),
        ("44", "欧美绿帽偷情"),
        ("45", "欧美黑屌爆操"),
        ("50", "欧美强奸野战"),
    ]

    def init(self, extend=""):
        self._jwt = None
        self._jwt_ts = 0
        self._access = None
        self._access_ts = 0
        # extend 可传 pic_proxy=0 强制直链封面
        self._force_direct_pic = False
        if extend and "pic_proxy=0" in str(extend):
            self._force_direct_pic = True
        return

    def getName(self):
        return "xx9"

    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower()
        return ".m3u8" in u or ".mp4" in u

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    def _pad(self, b):
        n = 16 - (len(b) % 16)
        return b + bytes([n]) * n

    def _unpad(self, b):
        if not b:
            return b
        return b[:-b[-1]]

    def _enc(self, obj, key):
        if AES is None:
            raise RuntimeError("需要 pycryptodome")
        raw = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        c = AES.new(key.encode('utf-8'), AES.MODE_ECB)
        return base64.b64encode(c.encrypt(self._pad(raw))).decode()

    def _dec(self, b64, key):
        if AES is None:
            raise RuntimeError("需要 pycryptodome")
        c = AES.new(key.encode('utf-8'), AES.MODE_ECB)
        raw = self._unpad(c.decrypt(base64.b64decode(b64)))
        return raw.decode('utf-8')

    def _mktime(self):
        t = int(time.time() * 1000)
        return t - (t % 10) + self.REM

    def _rnd(self, n):
        cs = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.choice(cs) for _ in range(n))

    def _call(self, uri, method, params=None, body=None, use_jwt=True, use_access=False, _retry=True):
        key = self.KEYS[self.REM]
        plain = {"method": method, "uri": uri}
        if body is not None:
            plain["body"] = body
        else:
            plain["params"] = params if params is not None else {}
        payload = {"data": self._enc(plain, key), "time": self._mktime()}
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.UA,
            "Origin": "https://xx9.com",
            "Referer": "https://xx9.com/",
            "Accept": "application/json, text/plain, */*",
        }
        if use_jwt:
            jwt = self._get_jwt()
            if jwt:
                headers["jwtToken"] = jwt
        if use_access:
            acc = self._get_access()
            if acc:
                headers["accessToken"] = acc

        text = None
        for gw in self.GATEWAY_POOL:
            try:
                rsp = self.post(gw, json=payload, headers=headers)
                if rsp is None:
                    continue
                text = rsp.text if hasattr(rsp, "text") else str(rsp)
                if text:
                    break
            except Exception:
                continue
        if not text:
            return {}
        try:
            j = json.loads(text)
        except Exception:
            return {}
        if isinstance(j, dict) and isinstance(j.get("data"), str) and j.get("data") and ("time" in j):
            try:
                j = json.loads(self._dec(j["data"], key))
            except Exception:
                return j
        if use_access and _retry and isinstance(j, dict):
            code = str(j.get("code") or "")
            if code in ("1032", "1019"):
                self._access = None
                self._access_ts = 0
                return self._call(uri, method, params=params, body=body,
                                  use_jwt=use_jwt, use_access=use_access, _retry=False)
        return j

    def _get_jwt(self):
        now = time.time()
        if self._jwt and (now - self._jwt_ts) < 3600:
            return self._jwt
        try:
            r = self._call("app/jwt-token", 1, params={"adsCode": self.ADS_CODE}, use_jwt=False)
            jwt = r.get("result") if isinstance(r, dict) else None
            if jwt:
                self._jwt = jwt
                self._jwt_ts = now
        except Exception:
            pass
        return self._jwt

    def _get_access(self):
        now = time.time()
        if self._access and (now - self._access_ts) < 1800:
            return self._access
        try:
            body = {
                "osType": "h5",
                "sign": self._rnd(32),
                "machineCode": "chrome",
                "version": "xx9.com",
            }
            r = self._call("user/register/free", 2, body=body, use_jwt=True, use_access=False)
            res = r.get("result") if isinstance(r, dict) else None
            acc = res.get("accessToken") if isinstance(res, dict) else None
            if acc:
                self._access = acc
                self._access_ts = now
        except Exception:
            pass
        return self._access

    def _abs_pic(self, p):
        if not p:
            return ""
        p = str(p).strip()
        if p.startswith("http://") or p.startswith("https://"):
            return p
        if not p.startswith("/"):
            p = "/" + p
        return self.PIC_BASE + p

    def _pic(self, p):
        # 官网实际图片 CDN：qv1.almusiclub.com（手机可访问）
        full = self._abs_pic(p)
        return full or ""


    def localProxy(self, param):
        """代拉封面：纯标准库 urllib，避免 requests 在壳内不可用"""
        try:
            if not isinstance(param, dict):
                param = {}
            url = (param.get("url") or param.get("src") or param.get("pic")
                   or param.get("value") or param.get("path") or "")
            url = unquote(str(url)).strip()
            if not url:
                return [400, "text/plain", b"no url"]
            if not url.startswith("http"):
                url = self._abs_pic(url)

            headers = {
                "User-Agent": self.UA,
                "Referer": "https://xx9.com/",
                "Origin": "https://xx9.com",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            }

            body = None
            ctype = "image/jpeg"
            # 1) urllib（标准库）
            try:
                import ssl
                import urllib.request
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    body = resp.read()
                    ctype = resp.headers.get("Content-Type") or ctype
            except Exception:
                body = None
            # 2) requests 兜底
            if body is None:
                try:
                    import requests as reqlib
                    r = reqlib.get(url, headers=headers, timeout=20, verify=False)
                    if r.status_code == 200 and r.content:
                        body = r.content
                        ctype = r.headers.get("Content-Type") or ctype
                except Exception:
                    body = None
            # 3) 框架 fetch
            if body is None and hasattr(self, "fetch"):
                try:
                    rsp = self.fetch(url, headers=headers)
                    if rsp is not None and hasattr(rsp, "content") and rsp.content:
                        body = rsp.content
                        if hasattr(rsp, "headers"):
                            ctype = rsp.headers.get("Content-Type") or ctype
                except Exception:
                    body = None

            if not body:
                return [404, "text/plain", b"empty image"]
            if "text" in (ctype or "") or "json" in (ctype or "") or "html" in (ctype or ""):
                ctype = "image/jpeg"
            return [200, ctype, body]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8", errors="ignore")]


    def _vod_list_item(self, it):
        vid = it.get("id") or it.get("vodId")
        title = (it.get("title") or "").strip()
        pic = self._pic(it.get("vodPic") or it.get("scroll") or it.get("gif") or "")
        dur = it.get("vodDuration")
        remark = ""
        if isinstance(dur, (int, float)) and dur > 0:
            m, s = divmod(int(dur), 60)
            remark = "%d:%02d" % (m, s)
        return {
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": remark,
        }

    def _search(self, params):
        r = self._call("cms/vod/search", 2, params=params)
        data = r.get("data") if isinstance(r, dict) else None
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("list") or data.get("records") or []
        total = r.get("total") if isinstance(r, dict) else 0
        return items, (total or 0)

    def homeContent(self, filter):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self.THEMES]
        filters = {}
        sort_filter = {
            "key": "sort",
            "name": "排序",
            "value": [{"n": "最新", "v": "1"}, {"n": "最热", "v": "2"}],
        }
        for tid, _ in self.THEMES:
            filters[tid] = [sort_filter]
        result = {"class": classes, "filters": filters}
        try:
            result["list"] = self.homeVideoContent().get("list", [])
        except Exception:
            result["list"] = []
        return result

    def homeVideoContent(self):
        items, _ = self._search({
            "groupIds": self.THEMES[0][0],
            "page": 1, "pageSize": 30,
            "explore": False, "sortType": 1,
        })
        return {"list": [self._vod_list_item(it) for it in items]}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        sort_type = 1
        if isinstance(extend, dict) and extend.get("sort"):
            try:
                sort_type = int(extend.get("sort"))
            except Exception:
                sort_type = 1
        page_size = 30
        items, total = self._search({
            "groupIds": str(tid),
            "page": page, "pageSize": page_size,
            "explore": False, "sortType": sort_type,
        })
        vod = [self._vod_list_item(it) for it in items]
        pagecount = 9999
        if total:
            pagecount = (int(total) + page_size - 1) // page_size
        return {
            "list": vod,
            "page": page,
            "pagecount": pagecount,
            "limit": page_size,
            "total": int(total) if total else len(vod),
        }

    def detailContent(self, ids):
        vid = str(ids[0])
        r = self._call("cms/vod/detail/%s" % vid, 1, params={"needCdnAuth": True}, use_access=True)
        res = r.get("result") if isinstance(r, dict) else None
        vod = res.get("vod", res) if isinstance(res, dict) else {}
        if not isinstance(vod, dict) or not vod:
            return {"list": []}

        title = (vod.get("title") or "").strip()
        pic = self._pic(vod.get("vodPic") or vod.get("scroll") or vod.get("gif") or "")
        intro = vod.get("vodIntro") or ""
        tags = vod.get("tags")
        tag_str = ",".join(tags) if isinstance(tags, list) else ""
        dur = vod.get("vodDuration")
        remark = ""
        if isinstance(dur, (int, float)) and dur > 0:
            m, s = divmod(int(dur), 60)
            remark = "时长 %d:%02d" % (m, s)

        full = vod.get("vodFullPlayUrl")
        n_parts = len(full) if isinstance(full, list) and full else 1
        froms, urls = [], []
        for name, _domain in self.PLAY_LINES:
            if n_parts <= 1:
                eps = ["正片$%s|0" % vid]
            else:
                eps = ["P%d$%s|%d" % (i + 1, vid, i) for i in range(n_parts)]
            froms.append(name)
            urls.append("#".join(eps))

        return {"list": [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": remark,
            "vod_content": intro or tag_str,
            "vod_tag": tag_str,
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
        }]}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        items, _ = self._search({
            "title": key,
            "page": page, "pageSize": 30,
            "explore": False, "sortType": 1,
        })
        return {"list": [self._vod_list_item(it) for it in items]}

    def playerContent(self, flag, id, vipFlags):
        vid = str(id)
        idx = 0
        if "|" in vid:
            vid, sidx = vid.split("|", 1)
            try:
                idx = int(sidx)
            except Exception:
                idx = 0

        domain = self.PLAY_LINES[0][1]
        for name, dom in self.PLAY_LINES:
            if name == flag:
                domain = dom
                break

        play_url = ""
        try:
            r = self._call("cms/vod/detail/%s" % vid, 1, params={"needCdnAuth": True}, use_access=True)
            res = r.get("result") if isinstance(r, dict) else None
            vod = res.get("vod", res) if isinstance(res, dict) else {}
            if not isinstance(vod, dict):
                vod = {}
            addr = None
            full = vod.get("vodFullPlayUrl")
            if isinstance(full, list) and full:
                if idx >= len(full):
                    idx = 0
                item = full[idx]
                addr = item.get("addr") if isinstance(item, dict) else item
            if not addr:
                addr = vod.get("preview") or vod.get("mp4") or vod.get("newAddr")
            if addr:
                addr = str(addr).strip()
                if addr.startswith("http"):
                    play_url = addr
                else:
                    if not addr.startswith("/"):
                        addr = "/" + addr
                    play_url = domain + addr
        except Exception:
            play_url = ""

        # MPV 需要这些头；分片/密钥在 tigers* 域，靠播放器跟随 Header
        return {
            "parse": 0,
            "playUrl": "",
            "url": play_url,
            "header": {
                "User-Agent": self.UA,
                "Referer": "https://xx9.com/",
                "Origin": "https://xx9.com",
            },
        }
