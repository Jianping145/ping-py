# -*- coding: utf-8 -*-
# 顺丰快递 多源 v6
# 修复登录路径 clusery → cluser（原规则正确路径）

import sys
import json
import base64
sys.path.append('..')
from base.spider import Spider

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False

class Spider(Spider):
    def init(self, extend=""):
        self.ua = 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        self.aes_key = b'GcgzsKdDZTumABNz7uujrCfPIk9TQ355'
        # 注意：原规则 devicesinfo 末尾有逗号，这里保持标准 JSON
        self.device_info = '{"manufacturer":"LGE","sdkVersionCode":"25","isRooted":"true","androidID":"576e795af3ef9961","model":"Nexus5"}'
        self.last_error = ""
        self.last_raw = ""

        self.sites = {
            "jkf": {
                "name": "JKF",
                "domain": "https://52.76.94.4/front/",
                "num": "60",
                "loginToken": "ac913c3ebd2545e484002ab9dfcd0486.egRl3CMWikZHmM+4CfJsK1QqvytrDO5/u2wJRNvknb/0jQ6zlYKt7CAr/ewo/dZJV1ElCrfR6ekx7W5cuYyZBsWlM+ytflreozuop9yq9fthcb1Xg1LQGue00PeguRhKd2FlRkf0N2z1KAFzqDYoVq+mZ3qCxY21.3ca5881a612505e5d6653e7e1ddf746f",
                "loginPost": "H9TyInuJYlfOZGUf7lggG0s1dU1U9TdbXNz+VBubVWg4QdWqF14Ix7MBAT9vIgqLt7OPOHKrYWjOpHMyBalujl8JHiefNVQ9y6y1sBSXHhNDtQkyMTjllywCeT7X3C/Sj5D+IYDUETratKVfsK656wipj13qh3SsruwHZ55gV7o=",
            },
            "vaga": {
                "name": "Vaga",
                "domain": "https://1ahos2.7ekysucd.top/front/",
                "num": "62",
                "loginToken": "13ebf81564c1422c806c9728ae1f6aed.lcVQSRzJOp17PJ2DoPd0huFmieiy3h68ExadSGc7KbnBPniYOmjsCNoj6tB8I8PmO8t2SSUHE3XlTuAp4E1q1E/CSRW1FxFEa2ifvUFnrZX4NJTGeYFC4LldjCzgWLhAtzANbEIq+cYZ6lNUL4Wfz75tYMSyqF21.a70bdf435441edee5df88397173e2599",
                "loginPost": "RI9CPg0edIQSVAmOqqtTtgb1maEpjHMsG0y0svZp3+R84DQsYSPllVygOKOqdMW67dgBfyUKZC2rcZguvssRaoaV6N1jTUjxKgpZL7NHonPM/BvmGzRiZBrAeKestL05TztVZmzYSVIX+E1UhmHU9h4VxMUcY8NIZbj14saMjB4=",
            },
            "fansly": {
                "name": "fansly",
                "domain": "https://13.229.32.61/front/",
                "num": "20",
                "loginToken": "b641db4ce3c34f8c83c3747143bb3e25.eLHNkdDl1Fbf2xcoyuUCCdFBE1psSQFe374/O2t5wETjodJS+2oiwI/OjCea9SXwb9EQLHRXucS1fxniRoN5ramEm5Apfrhoht7FKNnQ0ZzNt66ZBvgk63d3RCBPn6EYslZRjkR+oETprJsxqjX5C0vsClc8rxXp.ecf9650fb0b94a86b80fe40cd846ea4a",
                "loginPost": "bABJaeKig/9VsABVyzz+6ANEbLMWJb3FcgHNVXkusRM14Q3/S0P+fDcBt2fVtiEg2Z+1U9Ye8Y4mFkf5TuiQ1NyNOUdhpjzEZQQxZHD96r7alGO/A1FvY8urGervMChiO/MKuMXaJIQg00ARUYQr9eZuCFFK1GMGO00rSZS4Zgs=",
            },
            "youtube": {
                "name": "YouTube",
                "domain": "https://52.77.6.19/front/",
                "num": "39",
                "loginToken": "7ce8178aa70e49fdaff5c5d5d28141e9.rpnAX5AFyhPxQ7FZZel8HXElotGDjC+5URAw/kpqvvMk30wyn03Rkqqk96rMJ9tLttqLV9Hg4tZvRgB/J5fly6rv7dpS7H25i8ay9Gg/VTZkXbi3lLrwVPxi5gI5yfKhw8hwZZ+6BM202jO7DEY3A0miSMpVhM00r6ZneoLFjbU=.d637e553325c88a09b82e67c3e0acc42",
                "loginPost": "ho9u0MIXAY14IWgUt/z4kJqZltbdhuixHSRVUMm+iaAlfAtyuBZZb1TEb/aokF5RHiEIvBrh9/h0TKE8G0VFQS/aVbRfIKEeF65K7m1b8fb5QrMCfeNWmOp070Mcu69rabdm36Yp+LWkPmD9ufviNMkPL3t9EiFM21HlWDP43E8=",
            },
            "cnselect": {
                "name": "中国好黄站",
                "domain": "https://52.77.6.19/front/",
                "num": "61",
                "loginToken": "d6124311dfe640149d68b629a9811190.YZjmCEI4kjU+dBx3m3FlVqzc8cy31N3cpuz3XNCvJrPvS0/M2aMQ1qbn0vGCx/ZCGHLMyo6lCtlVWEDhJUouu2osVOLd7/LeMANHz5bGalTDzLuQhgfGhKdQxBGF654UQ2yHaL0M/y41oKv98gA0mA/ZEdsQPhB1.b40e5912e3120ecd6e15eaa6f55943ca",
                "loginPost": "Cd3OZdsAT/mpJSWk1t8+Ib8HGH8XaWK2jNbvYVnHWjoAd+aWjoaSl3+uCHADuVPunUKROXG+D2FgKhiG0NA4IbZ8nEcDcMHjYn+ULPgGpxnB2yrxekN3SpwwTnn3BVX1wP/1Khfv+JDRLi6C1nnw0H3oxHk5qBuxR1may9bq0KA=",
            },
            "madou": {
                "name": "麻豆传媒",
                "domain": "https://mc9l2.7v5cf5n8.top/front/",
                "num": "76",
                "loginToken": "8fbac9a6e9f54a1fb7f742082cc8ac1e.5bOmOXybxa619ZUU62egqYhtPocUTl3wYLhfMwPrR3W1+qs9ZQ9Gex9w9sT1rq3TmBjsqGuFcUeBsWHLirc1o4qWjD1EGepKjYzALy6ROEGz25x9TWiQmvqk2anQy3CFdXYKA9761OjzN1i4W3eQt7O4q4ikaYuk.e6c999f22e52d2ff79d5f46d2ff63314",
                "loginPost": "MsOwAB1FAQvDN2WJRmbHhkHS6qdLuoImb55c5hdOmyKGX4RUn6OzbBEYfvRbacX3fsiC5wkCM3WQdMqCiVH8IM6u74OPu5rjh0NlKPSBJV/7f75GVaLbxnDzsKYCGgc7/rg1UtAO4++YefyBxQqjIGIKgPZRF1fZlx7Mb9vpTuY=",
            },
            "heiliaochigua": {"name": "黑料吃瓜网", "domain": "", "num": ""},
            "xingba": {"name": "杏吧论坛", "domain": "", "num": ""},
            "seli": {"name": "涩里", "domain": "", "num": ""},
            "smeeth": {"name": "smeetH", "domain": "", "num": ""},
            "tre": {"name": "TRE", "domain": "", "num": ""},
            "18jin": {"name": "18禁", "domain": "", "num": ""},
            "tangbure": {"name": "汤不热", "domain": "", "num": ""},
            "soul": {"name": "soul", "domain": "", "num": ""},
            "jvid": {
                "name": "JVID",
                "domain": "https://52.76.94.4/front/",
                "num": "57",
                "loginToken": "80b6350fd4ca45e588a6c875499c56cd.h2NWYNnsiRmfh3SzYsxtvnIJrdkddlVSdaSlVuSX5Qs5jlVMOEFKjyK52p+Q+5Tz4tUAA3oR3ChbAkJV9+EDeeFj/ITZ9oe3sDoFxvQbrB2y7EHimUW3WkXPJUYwLDZYU3MYiMFPQIe0JVrjGqQLez3soXUWiGMm.2bc666e814bf4f28f59cfcd79cf733cb",
                "loginPost": "jkkhe4KlxVMIpvk/cuWPEs3bdyFLYJbXTPGpeJ504+jCDSnTMdhagevWxbKVwluwx8LDTI8ejw2tTzZPfnLOCwA9OMs5ceMoNDJRnWhKwSWuKfcvS7R1CoPXJMk48wNnBxpAhb/ZVkIolR7m/q/m+t3xrTH+wHhZhPLlt+yJLWs",
            },
            "xxoo": {
                "name": "XXOO",
                "domain": "https://52.77.6.19/front/",
                "num": "41",
                "loginToken": "e62ec9c5404847cd8fc8b473522471ff./cIyDi0vCLBMn7CBgYFJ9vXUX/H+IcsM8LcJ+IOS2Cmthpw+Iqa1FU2wov28Vm8IHRN+JzKpB3ZuZ4/LrHUV1X8ud3lWiwCILJydLYa4G130IYNenCFaTVYQ4NXQdjpDPiFNW4biZZk2pVDFbBUyVjR0Y6G5L90g.126a7d3fe9d1006bd3a73b53a057482a",
                "loginPost": "V+TJPvwEPS/eGrHn5ly2sp1pH7WY7KOtP3PWb20sXnnTepcAQNV6t6iG69pZrImNxZpLZW7ZlDUo4V5+8LxNXJWlYwNNOWHAyRAxRj11bPx3D/AZNGNd8N+vPhOP/lyfhb2TV9t+ZEGkQT1ekZyxFZgul+/Q+2EbzIS7IzVL3Ts=",
            },
            "jinitaimei": {
                "name": "鸡你太美",
                "domain": "https://52.77.6.19/front/",
                "num": "24",
                "loginToken": "24c05bdf78c54405af5575407ad967a5.mAAn34jlz8tUoO15Ois6tjvTqDdDeQaCbcnCqyaIWRWEr75zk6dynI8J4fU/2VU2dGJtaNI5jmuivPTXa8Q2DcSX5ijh4bq8qClQ8tG3jRj9LoM3oGt3xnx2Ill8ftNBHwd+TWPEuLyjNMz5EkMzpDDjSoSU3sbR.93b919a319e236cd6ee0bc54238b0a91",
                "loginPost": "LR3thP94vG8yTpfVst0GQ2aEu3reyn1NBp0W85FP82Jg4oXz8125zv25mqR2sw+Tdl8s+z3ua+V0ODaF/0KeBsfs4hD64J1PTpj6okueF/NnK4a6QIAYikemupbgyVPl1gTeflOQ8t8m3xUavyJh6+uiQOChz29qUBjefVs1Z2Y=",
            },
            "kanpian": {"name": "看片不迷路", "domain": "", "num": ""},
            "madoushipin": {"name": "麻豆视频", "domain": "", "num": ""},
            "huashengwei": {"name": "花生味", "domain": "", "num": ""},
            "yuepa": {"name": "约啪", "domain": "", "num": ""},
            "onlyfans": {
                "name": "onlyfans",
                "domain": "https://54.169.23.247/front/",
                "num": "59",
                "loginToken": "106cf434b8ba4f34ace2e71607b95612.4vPsY//CpzYTM6/aWA1BtyFM+4sQnpot9YCP5TYPu7OSn7UAI42N/UCRfzRva1eqPrsomrfoKedlCU6Si0oP5u3VPZsNhuNLU5+GfDpoYuOXbOvNQedpF454dR64aeyy6iiw/s12tH046pKwNgzons7U4dX3RrLY.5189fdb1d94b26d28c1e69d3bc37b2a9",
                "loginPost": "GRln/4Fg/G30zCFUbu9dZ1i//F4meqs7/JaRdDF9JN3J3cRd3AcHwhk3/4k+NKAJ9cGdmq5KEBiYTxNQzmsEf+u59XDvf1sEybLtuA12K+f/QLOplDKB9WqUA7Qz78xjNDdvQpV+apB3o9KY7GgtlAbWzlgU6xkK6JUwL2YR58g=",
            },
            "caoliu": {"name": "草榴社区", "domain": "", "num": ""},
            "pornhub": {"name": "PornHub", "domain": "", "num": ""},
            "selifan": {"name": "涩里番", "domain": "", "num": ""},
            "aplusv": {
                "name": "A+V",
                "domain": "https://13.229.32.61/front/",
                "num": "46",
                "loginToken": "62efe7f184394d1e9a4de18a9aa39856.wXJ7Zz375FEuCDP1YxBCRcq5v4mjN3wZYMp6yiFw74kNveSeLSsw2QXq+R0/JMyhg+4GdqCBJl0G9kuJgXnts6NomlRQgVHGsv7k3bIKrXguHrATOHcHtQtLcQe3g/Okt86gkbNYL0Svbxutn5qmj6vlLLIgbLl0.bf39881e8a379791a610e8c343baa16b",
                "loginPost": "mWH0OU9JSP5sQZsELuPkk91RklKnn1Z2Dn5BnXzkmdb0HrjO0hdvY+4BYvLgnS2YWqe5VQXdVwImcxAuz5bu81sOeLbi8iuYeIK0TnrdE72VwIxnH9EoeyQ8XmCCAE/BXIJZ7EzSQbP8Lxu+vh2KTSrOiR2SffrmQ4EUjT1PpjI=",
            },
            "tiktok": {
                "name": "tiktok",
                "domain": "https://18.140.20.60/front/",
                "num": "45",
                "loginToken": "aa2cf8f01d7f4c5a86b131ee1d638605.CXVq6GH6VQja/d3m7u0LtDuwKkCS9j/gpfmtjqUYc5vPQwy+9utd49KpZgPKfyERMz50TMOCSFjsvNQr6lPHs/mY8cbSuRJZVYyd308dbpNiUKXfPDNlLcW0BY9s9uoSjRIVid0k3dx+DtC2EddgSZQgMxDaMXLp.cdea2aebaab0db1347955c3a6fcd9ae7",
                "loginPost": "lhLyF/ukNEmzkVgmjpU1mo6745IJnGKG5fbsXjhJotQCaD82LFtRt2BN5gVdTryKzxvQK/TpbMmCyhMjkiIcGN9RbKqNXwchRXideLLsLLIxShemg0jnzPatPHPx4eQq1Gi3lA2EwR6n2gcRc4zAxRqKsOgXEpmBrw9neJlR0/c=",
            },
            "swag": {
                "name": "SWAG",
                "domain": "https://18.140.20.60/front/",
                "num": "54",
                "loginToken": "db1b1a64bf3d4504bca5a910e3b7aa13.7TDGsDGXTEfMaoIdPdAdDBb6/74FQSe17kg5d4dO6i87k0CPJVNmwQ9ct/9AN7IaNy0q8a33OODO03iPGcU81Kwz7ldmSJBUc3qjQTlxMqXDeuirlfZoiiNKL5Al7KtfmVH6pu+3EjQM+rDfdLggVP2JfMDFKyCS.81213b1df9d1896ab7c7ab61ad7ea27d",
                "loginPost": "f/McWqt3qQmO1valgxO9cg6KSKjCLTlrefZ/zhmkW0WzIK/byg0hIZEEM8pDKJ+kDjQKHaJQaI/37JL4gCOr/u7ZhHAqjMdefe1M8nsIeyIe0UqhVAc9jvPcbceUwRaSNHXuacmxQYyIWXhp/YU+n6UajDp9EAgxOJqrit5fvcA=",
            },
            "madoubuke": {"name": "麻豆不可", "domain": "", "num": ""},
            "91pro": {"name": "91Pro", "domain": "", "num": ""},
            "yourporn": {"name": "YourPorn", "domain": "", "num": ""},
            "sesedaren": {"name": "色色达人", "domain": "", "num": ""},
            "chiguashipin": {"name": "吃瓜视频", "domain": "", "num": ""},
        }

    def err(self, msg):
        self.last_error = str(msg)[:150]
        return self.last_error

    def aes_decrypt(self, data):
        if not HAS_CRYPTO or not data:
            return None
        try:
            cipher = AES.new(self.aes_key, AES.MODE_ECB)
            raw = base64.b64decode(data)
            return unpad(cipher.decrypt(raw), AES.block_size).decode('utf-8')
        except Exception as e:
            self.err(f"AES失败:{e}")
            return None

    def http_post(self, url, headers=None, data=None, timeout=12, silent=False):
        if not HAS_REQUESTS:
            if not silent:
                self.err("缺少requests")
            return None
        headers = headers or {}
        headers.setdefault('User-Agent', self.ua)
        try:
            r = requests.post(url, headers=headers, data=data, timeout=timeout, verify=False)
            return r.text
        except Exception as e:
            if not silent:
                self.err(f"POST失败:{e}")
            return None

    def get_host(self, site):
        domain = (site.get("domain") or "").strip()
        if domain:
            return domain.rstrip('/') + '/'
        self.err("无可用域名")
        return None

    def do_login(self, host, site):
        """原规则路径：/cluser/c/user/mac/login（注意是 cluser 不是 clusery）"""
        token = site.get("loginToken") or ""
        if not site.get("loginPost"):
            return token
        # 关键修复：路径正确为 cluser
        url = host + "cluser/c/user/mac/login"
        headers = {
            'User-Agent': self.ua,
            'Content-Type': 'application/json;charset=UTF-8',
            'devicesinfo': self.device_info,
            'token': token,
            'macct': 'sf' + str(site.get('num', '')),
            'ver': '2131',
            'os': '1'
        }
        body = json.dumps({"encrypt": site["loginPost"]})
        text = self.http_post(url, headers=headers, data=body, silent=True)
        if not text:
            return token
        dec = self.aes_decrypt(text)
        if not dec:
            return token
        try:
            data = json.loads(dec)
            new_token = (data.get("data") or {}).get("token")
            if new_token:
                return new_token
        except:
            pass
        return token

    def get_cdn(self, host, token, site):
        """原规则 CDN 请求用的是原始 loginToken"""
        url = host + "system/cdnline/getCdnLineByMerAcct"
        headers = {
            'User-Agent': self.ua,
            'Content-Type': 'application/json;charset=UTF-8',
            'devicesinfo': self.device_info,
            'token': site.get("loginToken") or token,  # 原规则用 loginToken
            'macct': 'sf' + str(site.get('num', '')),
            'ver': '2131',
            'os': '1'
        }
        text = self.http_post(url, headers=headers, data="{}", silent=True)
        if not text:
            return ""
        dec = self.aes_decrypt(text)
        if not dec:
            return ""
        try:
            data = json.loads(dec)
            arr = data.get("data") or []
            if arr and isinstance(arr, list):
                return (arr[0] or {}).get("cdnLine", "") or ""
        except:
            pass
        return ""

    def fetch_list(self, host, token, site, page=1):
        """返回 (list, total_count)"""
        url = host + "media/listMediaBySearchType"
        headers = {
            'User-Agent': self.ua,
            'Content-Type': 'application/json;charset=UTF-8',
            'devicesinfo': self.device_info,
            'token': token,
            'macct': 'sf' + str(site.get('num', '')),
            'ver': '2131',
            'os': '1'
        }
        body = json.dumps({
            "mediaType": "1",
            "orderType": "SORT_PUBLISH",
            "pageNo": str(page),
            "pageSize": "20",
            "publishStatus": "1",
            "userId": "1730377227164069888"
        })
        text = self.http_post(url, headers=headers, data=body)
        if not text:
            return [], 0
        self.last_raw = text[:400]

        if text.strip().startswith('{'):
            try:
                data = json.loads(text)
            except Exception as e:
                self.err(f"明文JSON失败:{e}")
                return [], 0
        else:
            dec = self.aes_decrypt(text)
            if not dec:
                self.err("列表解密失败(Token过期?)")
                return [], 0
            self.last_raw = dec[:400]
            try:
                data = json.loads(dec)
            except Exception as e:
                self.err(f"解密JSON失败:{e}")
                return [], 0

        d = data.get("data")
        if d is None:
            code = data.get("code")
            msg = data.get("msg") or data.get("message") or data.get("error") or ""
            self.err(f"data=null code={code} msg={msg}")
            return [], 0
        if not isinstance(d, dict):
            self.err(f"data类型异常:{type(d)}")
            return [], 0
        lst = d.get("dataList")
        if lst is None:
            lst = d.get("list") or d.get("records") or []
        if not isinstance(lst, list):
            lst = []
        total = d.get("total") or d.get("totalCount") or 0
        try:
            total = int(total)
        except Exception:
            total = 0
        return lst, total

    def make_error_item(self, msg):
        return [{
            "vod_id": "error",
            "vod_name": f"❌ {msg}",
            "vod_pic": "",
            "vod_remarks": "错误提示"
        }]

    def getName(self):
        return "顺丰多源"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        classes = [{"type_name": v["name"], "type_id": k} for k, v in self.sites.items()]
        return {"class": classes}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        # 始终给足够大的 pagecount，避免客户端提前停止上滑
        result = {
            "list": [],
            "page": page,
            "pagecount": 9999,
            "limit": 20,
            "total": 999999
        }
        self.last_error = ""
        self.last_raw = ""

        site = self.sites.get(tid)
        if not site:
            if page == 1:
                result["list"] = self.make_error_item(f"未知站点 {tid}")
            return result
        if not site.get("num"):
            if page == 1:
                result["list"] = self.make_error_item(f"{site.get('name','')} 未配置完整参数")
            return result
        if not HAS_CRYPTO:
            if page == 1:
                result["list"] = self.make_error_item("缺少 pycryptodome")
            return result
        if not HAS_REQUESTS:
            if page == 1:
                result["list"] = self.make_error_item("缺少 requests")
            return result

        host = self.get_host(site)
        if not host:
            if page == 1:
                result["list"] = self.make_error_item("无法获取域名")
            return result

        # 登录/CDN 失败不阻断，继续用原 token
        self.last_error = ""
        token = self.do_login(host, site)
        self.last_error = ""
        cdn = self.get_cdn(host, token, site)
        self.last_error = ""

        items, total = self.fetch_list(host, token, site, page)

        if self.last_error and not items:
            if page == 1:
                result["list"] = self.make_error_item(self.last_error)
            return result
        if not items:
            # 没有更多数据
            result["pagecount"] = page
            if page == 1:
                result["list"] = self.make_error_item("接口返回空列表")
            return result

        videos = []
        for item in items:
            video = item.get("video") or item or {}
            pay = str(item.get("payType", "0"))
            pay_map = {"1": "限免", "2": "金币", "4": "VIP"}
            pay_str = pay_map.get(pay, "")
            duration = video.get("videoDuration") or 0
            try:
                duration = int(duration)
                h, m, s = duration // 3600, (duration % 3600) // 60, duration % 60
                time_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            except Exception:
                time_str = ""
            title = video.get("videoTitle") or video.get("title") or "未知"
            vurl = video.get("videoUrl") or video.get("url") or ""
            cover = video.get("videoCoverImg") or video.get("cover") or ""
            if cdn and cover and not str(cover).startswith("http"):
                pic = cdn.rstrip("/") + "/" + str(cover).lstrip("/")
            else:
                pic = cover
            if cdn and vurl and not str(vurl).startswith("http"):
                full_url = cdn.rstrip("/") + "/" + str(vurl).lstrip("/")
            else:
                full_url = vurl or ""
            videos.append({
                "vod_id": tid + "###" + full_url + "###" + title,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": f"{pay_str} {time_str}".strip()
            })
        result["list"] = videos
        if total > 0:
            result["total"] = total
            # 至少保证 pagecount > 当前页，直到真正没有数据
            pc = max(1, (total + 19) // 20)
            result["pagecount"] = max(pc, page + 1) if len(videos) >= 20 else max(pc, page)
        elif len(videos) >= 20:
            result["pagecount"] = page + 1  # 还有可能有下一页
        else:
            result["pagecount"] = page
        return result

    def detailContent(self, ids):
        raw = ids[0] if ids else ""
        if raw == "error":
            return {"list": [{"vod_id": "error", "vod_name": "错误提示", "vod_play_from": "提示", "vod_play_url": "无$"}]}
        parts = raw.split("###")
        if len(parts) < 3:
            return {"list": []}
        tid, play_url, title = parts[0], parts[1], parts[2]
        return {
            "list": [{
                "vod_id": raw,
                "vod_name": title,
                "vod_pic": "",
                "vod_content": title,
                "vod_play_from": "顺丰",
                "vod_play_url": "正片$" + play_url
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": pg}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id, "header": {"User-Agent": self.ua}}

    def localProxy(self, param):
        return []
