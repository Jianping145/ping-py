# -*- coding: utf-8 -*-
import sys, json, base64, gzip, urllib.parse, threading, time, socket
import hashlib
import warnings
warnings.filterwarnings("ignore")

sys.path.append('..')
try:
    from base.spider import Spider as _B
except ImportError:
    class _B: pass
try:
    import requests
except ImportError:
    requests = None

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# ==================== 配置（新版域名）====================
API_DOMAIN = "https://api-al.uio2.fun"
IMG_DOMAIN = "https://images.uio2.fun"
PROXY_PORT = 8899

STREAM_HOSTS = [
    ("VIP高速1", "https://stream.uio2.fun"),
    ("海外线路", "https://stream.ass6.store"),
]

REQ_KEY = base64.b64decode("euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs=")
RESP_KEY = b"db6f7f9e5d7a770e0e3497a7d7a077f5"
RESP_KEY_NEW = b"3a0fd42302f0aada8abc0529a2bde5aa"

IMG_KEY = base64.b64decode("svOEKGb5WD0ezmHE4FXCVQ==")
IMG_IV = base64.b64decode("4B7eYzHTevzHvgVZfWVNIg==")

UA_APP = "Fulao2/Android 2.40; Lenovo TB-J606F"
UA_CDN = "com.ilulutv.fulao2.main.MyApplication/2.40 (Linux;Android 11) ExoPlayerLib/2.11.1"
UA_IMG = "Dalvik/2.1.0 (Linux; U; Android 11; Lenovo TB-J606F Build/RKQ1.210303.002)"

TARGET_CATEGORIES = ["推荐", "H动画", "最新", "抢先看", "中字", "NTR", "火爆", "FC2", "91大神", "传媒"]

X_INFO_LAUNCH = "eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIyLjQwIn0="
X_INFO_CENSOR = "eyJjcGFnZSI6ImNlbnNvciIsInBsYXRmb3JtIjoyLCJwcGFnZSI6ImxhdW5jaCIsInZlcnNpb24iOiIyLjQwIn0="
X_INFO_PLAY = "eyJjcGFnZSI6InBsYXkiLCJwbGF0Zm9ybSI6MiwicHBhZ2UiOiJjZW5zb3IiLCJ2ZXJzaW9uIjoiMi40MCJ9"

QUALITIES = [("480", "高清"), ("240", "标清")]
# ==============================================

_M3U8_CACHE = {}
_CACHE_LOCK = threading.Lock()
_SERVER_STARTED = False
_LOG = []

def _log(msg):
    line = f"[Fulao2] {time.strftime('%H:%M:%S')} {msg}"
    _LOG.append(line)
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except:
        pass
    try:
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except:
        pass


# ==================== 内置 HTTP 服务 ====================

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/m3u8":
                key = urllib.parse.unquote(qs.get("vid", [""])[0])
                content = ""
                for _ in range(40):
                    with _CACHE_LOCK:
                        content = _M3U8_CACHE.get(key, "")
                    if content:
                        break
                    time.sleep(0.5)

                if content:
                    data = content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.end_headers()

            elif parsed.path == "/img":
                url = urllib.parse.unquote(qs.get("url", [""])[0])
                try:
                    r = requests.get(
                        url,
                        headers={
                            "User-Agent": UA_IMG,
                            "Accept-Encoding": "gzip",
                            "Connection": "Keep-Alive",
                            "Referer": "https://webal.quipa.website/",
                        },
                        verify=False,
                        timeout=10,
                        allow_redirects=True,
                    )
                    raw = r.content
                    try:
                        body = unpad(AES.new(IMG_KEY, AES.MODE_CBC, IMG_IV).decrypt(raw), 16)
                    except Exception:
                        body = raw
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as e:
                    _log(f"[img_proxy] 失败: {e}")
                    self.send_response(502)
                    self.end_headers()

            else:
                self.send_response(404)
                self.end_headers()

        except Exception:
            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass


class _ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _find_available_port(start=PROXY_PORT, max_try=10):
    for p in range(start, start + max_try):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            continue
    return start


def _start_server():
    global _SERVER_STARTED, PROXY_PORT
    if _SERVER_STARTED:
        return
    try:
        PROXY_PORT = _find_available_port(PROXY_PORT)
        srv = _ThreadedServer(("127.0.0.1", PROXY_PORT), _Handler)
        t = threading.Thread(target=srv.serve_forever)
        t.daemon = True
        t.start()
        _SERVER_STARTED = True
        _log(f"代理服务已启动 127.0.0.1:{PROXY_PORT}")
    except Exception as e:
        _log(f"代理服务启动失败: {e}")


# ==================== Spider ====================

class Spider(_B):

    def init(self, e=""):
        self.token = ""
        self.sess = requests.Session()
        self.sess.verify = False
        self.sess.headers.update({
            "user-agent": UA_APP,
            "authorization": "Bearer ",
            "accept-encoding": "gzip",
            "x-info": X_INFO_LAUNCH,
        })
        _start_server()
        _log("[init] 源初始化完成，token将在首次需要时获取")

    def getName(self):
        return "Fulao2"

    def isVideoFormat(self, u):
        return True

    def manualVideoCheck(self):
        return False

    # ==================== 加解密（保持v22原样）====================

    def _encrypt_payload(self, path, extra=None):
        payload = {
            "path": path,
            "device_id": "aeffaaa7-166c-4545-8971-c669ff59f611",
            "utm_medium": "",
            "model": "LENOVOLenovo TB-J606F",
            "universal_id": "3027776cc331ee45",
            "platform": "Android",
            "key": "f7787644a1f6b8e41a580fdfb4501acb9c095dda346567fa82a15c68a55b4ce1",
            "timestamp": str(int(time.time())),
        }
        if extra:
            payload.update(extra)
        payload_str = json.dumps(payload, separators=(',', ':'))
        iv = base64.b64decode("B3nBQVSgjRuC09mgsdbgIg==")
        ct = AES.new(REQ_KEY, AES.MODE_CBC, iv).encrypt(pad(payload_str.encode(), 16))
        return base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()

    def _decrypt_resp(self, text):
        try:
            ct = base64.b64decode(text)
            iv = bytes(a ^ b for a, b in zip(
                AES.new(RESP_KEY, AES.MODE_ECB).decrypt(ct[:16]),
                b'{"status":{"code'.ljust(16, b'\x00'),
            ))
            raw = unpad(AES.new(RESP_KEY, AES.MODE_CBC, iv).decrypt(ct), 16)
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return json.loads(raw.decode())
        except Exception:
            try:
                return json.loads(text)
            except:
                return None

    def _decrypt_m3u8(self, text):
        try:
            ct = base64.b64decode(text)
            iv = bytes(a ^ b for a, b in zip(
                AES.new(RESP_KEY, AES.MODE_ECB).decrypt(ct[:16]),
                b'#EXTM3U\n#EXT-X-V',
            ))
            raw = unpad(AES.new(RESP_KEY, AES.MODE_CBC, iv).decrypt(ct), 16)
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return raw.decode('utf-8', errors='ignore')
        except Exception:
            if text.strip().startswith("#EXTM3U"):
                return text
            return None

    def _api(self, method, path, xinfo=None):
        enc = self._encrypt_payload(path)
        url = API_DOMAIN + "/" + path
        h = {}
        if xinfo:
            h["x-info"] = xinfo
        try:
            if method == "POST":
                h["content-type"] = "application/x-www-form-urlencoded"
                r = self.sess.post(
                    url,
                    data="payload=" + urllib.parse.quote(enc),
                    headers=h,
                    timeout=5,
                )
            else:
                full_url = url + "?payload=" + urllib.parse.quote(enc)
                r = self.sess.get(
                    full_url,
                    headers=h,
                    timeout=5,
                )
            _log(f"[api] {path} status={r.status_code} len={len(r.text)}")
            if r.status_code == 200:
                decrypted = self._decrypt_resp(r.text)
                if decrypted is None:
                    _log(f"[api] {path} 解密失败，原始前100字={r.text[:100]}")
                else:
                    _log(f"[api] {path} 解密keys={list(decrypted.keys()) if isinstance(decrypted, dict) else '非字典'}")
                return decrypted
            _log(f"[api] {path} 状态码={r.status_code} body={r.text[:200]}")
            return None
        except Exception as e:
            _log(f"[api_err] {path} {type(e).__name__}: {e}")
            return None

    # ==================== Token（完全独立 + 重试机制）====================

    def _get_token(self):
        """获取token，失败不崩溃"""
        if self.token:
            return True

        _log("[token] 开始获取token...")
        diag = []

        # 尝试旧接口
        try:
            _log("[token] 尝试旧接口 /v1/register/token")
            data = self._api("POST", "v1/register/token")
            if data and "response" in data:
                resp = data["response"]
                self.token = resp.get("token", resp.get("access_token", ""))
                if self.token:
                    self.sess.headers["authorization"] = "Bearer " + self.token
                    _log(f"[token] 旧接口成功! token={self.token[:15]}...")
                    return True
        except Exception as e:
            _log(f"[token] 旧接口异常: {e}")
            diag.append(f"旧接口异常:{type(e).__name__}")

        # 新版 guest 注册（使用self.sess保持cookie一致性，重试3次）
        for attempt in range(3):
            try:
                _log(f"[token] 尝试新版guest注册 (第{attempt+1}次)")

                # Step 1: verify/code（使用self.sess，保持cookie）
                _log("[token] -> GET /v1/verify/code")
                r1 = self.sess.get(
                    API_DOMAIN + "/v1/verify/code",
                    headers={
                        "Referer": "https://webal.quipa.website/",
                        "Origin": "https://webal.quipa.website",
                    },
                    timeout=8,
                )
                _log(f"[token] verify/code status={r1.status_code}")

                if r1.status_code != 200:
                    _log(f"[token] verify/code 失败={r1.status_code}")
                    diag.append(f"verify/code={r1.status_code}")
                    time.sleep(1)
                    continue

                body = r1.text.strip()
                _log(f"[token] verify/code body={body[:60]}")

                hash_val = body.strip('()').strip('"').strip("'").strip()
                if len(hash_val) != 32:
                    _log(f"[token] hash长度异常({len(hash_val)})")
                    diag.append(f"hash_len={len(hash_val)}")
                    time.sleep(1)
                    continue

                _log(f"[token] hash={hash_val[:10]}...")

                # Step 2: register/guest（使用self.sess）
                _log("[token] -> POST /v1/register/guest")
                enc = self._encrypt_payload("v1/register/guest", {"hash": hash_val})
                r2 = self.sess.post(
                    API_DOMAIN + "/v1/register/guest",
                    data="payload=" + urllib.parse.quote(enc),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": "https://webal.quipa.website/",
                        "Origin": "https://webal.quipa.website",
                    },
                    timeout=8,
                )
                _log(f"[token] guest status={r2.status_code}")

                if r2.status_code != 200:
                    _log(f"[token] guest 注册失败={r2.status_code}")
                    diag.append(f"guest={r2.status_code}")
                    time.sleep(1)
                    continue

                # 提取 x-vtag
                x_vtag = ""
                for k, v in r2.headers.items():
                    if k.lower() == "x-vtag":
                        x_vtag = v
                        break
                _log(f"[token] x-vtag={x_vtag}")

                if not x_vtag:
                    _log("[token] 无x-vtag，尝试旧解密")
                    old_data = self._decrypt_resp(r2.text)
                    if old_data and "response" in old_data:
                        self.token = old_data["response"].get("token", "")
                        if self.token:
                            self.sess.headers["authorization"] = "Bearer " + self.token
                            _log(f"[token] 旧解密成功!")
                            return True
                    _log("[token] 旧解密失败")
                    diag.append("旧解密失败")
                    time.sleep(1)
                    continue

                # 新版解密
                _log("[token] 使用新版AES解密")
                iv_str = hashlib.md5(x_vtag.encode()).hexdigest()[8:24]
                iv = iv_str.encode()
                ct = base64.b64decode(r2.text)
                raw = unpad(AES.new(RESP_KEY_NEW, AES.MODE_CBC, iv).decrypt(ct), 16)
                guest_data = json.loads(raw.decode())

                if "response" in guest_data:
                    self.token = guest_data["response"].get("token", "")
                    if self.token:
                        self.sess.headers["authorization"] = "Bearer " + self.token
                        _log(f"[token] Guest成功! token={self.token[:15]}...")
                        return True
                    else:
                        _log("[token] guest响应中token为空")
                        diag.append("token为空")
                else:
                    _log(f"[token] guest响应无response: {list(guest_data.keys())}")
                    diag.append(f"无response:{list(guest_data.keys())}")

            except Exception as e:
                _log(f"[token] guest异常: {type(e).__name__}:{e}")
                diag.append(f"guest_exc:{type(e).__name__}")

            time.sleep(1)

        _log("[token] 所有方式均失败")
        self._token_diag = ";".join(diag)
        return False

    # ==================== 封面 ====================

    def _img_url(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            full = path
        else:
            full = IMG_DOMAIN + ("" if path.startswith("/") else "/") + path
        return (
            "http://127.0.0.1:" + str(PROXY_PORT)
            + "/img?url=" + urllib.parse.quote(full, safe="")
        )

    # ==================== m3u8 获取（保持v22原样，detailContent不再调用）====================

    def _fetch_m3u8(self, vid, h_label, h_host, quality, xinfo=None, direct_url=None):
        cache_key = vid + "_" + h_label + "_" + quality
        with _CACHE_LOCK:
            if cache_key in _M3U8_CACHE:
                return cache_key, "cached"

        headers = {
            "Referer": "https://webal.quipa.website/",
            "Origin": "https://webal.quipa.website",
        }
        if xinfo:
            headers["x-info"] = xinfo

        # 如果提供了直接URL，先尝试GET（多种参数格式）
        if direct_url:
            urls_to_try = [
                direct_url,  # 原格式（已带token）
                direct_url.replace("?token=", "?jwt="),  # 尝试jwt参数
                direct_url.replace("?token=", "?"),  # 尝试不带token
            ]
            for idx, url in enumerate(urls_to_try):
                try:
                    resp = self.sess.get(url, headers=headers, timeout=5, allow_redirects=True)
                    if resp.status_code == 200:
                        text = self._decrypt_m3u8(resp.text)
                        if not text and resp.text.strip().startswith("#EXTM3U"):
                            text = resp.text
                        if text:
                            with _CACHE_LOCK:
                                _M3U8_CACHE[cache_key] = text
                            return cache_key, f"GOK{idx}:{text.count(chr(10))}"
                        else:
                            rp = resp.text[:15].replace(chr(10), "").replace(chr(13), "")
                            return None, f"Gfail{idx}:{rp}"
                    elif resp.status_code == 404:
                        continue
                    else:
                        return None, f"GS{resp.status_code}"
                except Exception as e:
                    return None, f"GE{type(e).__name__[:4]}"

            # GET 全部404，尝试 POST + payload 加密
            try:
                # 从 direct_url 提取 path
                parsed = urllib.parse.urlparse(direct_url)
                path = parsed.path.lstrip("/")
                enc = self._encrypt_payload(path)
                post_url = API_DOMAIN + "/" + path
                h = dict(headers)
                h["content-type"] = "application/x-www-form-urlencoded"
                resp = self.sess.post(
                    post_url,
                    data="payload=" + urllib.parse.quote(enc),
                    headers=h,
                    timeout=5,
                )
                if resp.status_code == 200:
                    text = self._decrypt_m3u8(resp.text)
                    if text:
                        with _CACHE_LOCK:
                            _M3U8_CACHE[cache_key] = text
                        return cache_key, f"POK:{text.count(chr(10))}"
                    else:
                        rp = resp.text[:15].replace(chr(10), "").replace(chr(13), "")
                        return None, f"Pfail:{rp}"
                else:
                    return None, f"PS{resp.status_code}"
            except Exception as e:
                return None, f"PE{type(e).__name__[:4]}"

        return None, "NOURL"

    def _play_url(self, cache_key):
        return (
            "http://127.0.0.1:" + str(PROXY_PORT)
            + "/m3u8?vid=" + urllib.parse.quote(cache_key, safe="")
        )

    # ==================== 首页分类 ====================

    def homeContent(self, filter=False):
        classes = []
        try:
            data = self._api("GET", "v2/menu/type")
        except Exception as e:
            _log(f"[homeContent] API异常: {e}")
            data = None
        if data and "response" in data:
            seen = set()
            for group in ["pixeled", "unpixeled"]:
                for item in data["response"].get(group, []):
                    t = item.get("title", "")
                    if t in TARGET_CATEGORIES and t not in seen:
                        seen.add(t)
                        classes.append({
                            "type_id": str(item["id"]),
                            "type_name": t,
                        })
        if not classes:
            _log("[homeContent] API返回空分类，使用fallback")
            classes = [
                {"type_id": "1", "type_name": "推荐"},
                {"type_id": "18", "type_name": "H动画"},
                {"type_id": "4", "type_name": "最新"},
                {"type_id": "16", "type_name": "抢先看"},
                {"type_id": "8", "type_name": "中字"},
                {"type_id": "15", "type_name": "NTR"},
                {"type_id": "6", "type_name": "火爆"},
                {"type_id": "19", "type_name": "FC2"},
                {"type_id": "14", "type_name": "91大神"},
                {"type_id": "11", "type_name": "传媒"},
            ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        if not self.token:
            self._get_token()
        _log(f"[homeVideoContent] token={'有' if self.token else '无'}")
        data = self._api("GET", "v1/menu/1/layout", xinfo=X_INFO_CENSOR)
        if data is None:
            _log("[homeVideoContent] API返回None")
        videos = []
        if data and "response" in data:
            for layout in data["response"]:
                items = layout.get("data", [])
                if isinstance(items, dict):
                    items = [items]
                if not isinstance(items, list):
                    continue
                for v in items:
                    vid = v.get("video_id")
                    title = v.get("video_title", "")
                    if not vid or not title:
                        continue
                    raw_pic = v.get("cover") or v.get("thumb", "")
                    actor = v.get("actor", "")
                    if isinstance(actor, list):
                        actor = "、".join(actor)
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": title,
                        "vod_pic": self._img_url(raw_pic),
                        "vod_remarks": actor,
                    })
                    if len(videos) >= 30:
                        break
                if len(videos) >= 30:
                    break
        return {"list": videos}

    # ==================== 分类列表 ====================

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        if not self.token:
            self._get_token()
        _log(f"[categoryContent] tid={tid} pg={pg} token={'有' if self.token else '无'}")
        data = self._api("GET", "v1/menu/" + str(tid) + "/layout", xinfo=X_INFO_CENSOR)
        if data is None:
            _log(f"[categoryContent] API返回None，tid={tid}")
        elif "response" not in data:
            _log(f"[categoryContent] API无response字段，返回keys={list(data.keys()) if isinstance(data, dict) else '非字典'}")
        videos = []
        if data and "response" in data:
            for layout in data["response"]:
                items = layout.get("data", [])
                if isinstance(items, dict):
                    items = [items]
                if not isinstance(items, list):
                    continue
                for v in items:
                    vid = v.get("video_id")
                    title = v.get("video_title", "")
                    if not vid or not title:
                        continue
                    raw_pic = v.get("cover") or v.get("thumb", "")
                    actor = v.get("actor", "")
                    if isinstance(actor, list):
                        actor = "、".join(actor)
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": title,
                        "vod_pic": self._img_url(raw_pic),
                        "vod_remarks": actor,
                    })
        return {
            "list": videos,
            "page": pg,
            "pagecount": 99,
            "limit": len(videos) or 20,
        }

    # ==================== 视频详情（v28: 不调用_fetch_m3u8，直接返回直链）====================

    def detailContent(self, ids):
        vid = str(ids[0])
        diag = f"D{vid}"
        _log(f"[detail] vid={vid}")

        # 确保token
        if not self.token:
            ok = self._get_token()
            diag += f"|T{'OK' if ok else 'NO'}"
        else:
            diag += "|TOK"

        # 获取info（5秒超时）
        info = self._api("GET", "v1/video/info/" + vid, xinfo=X_INFO_PLAY)
        if not info:
            # 快速重试一次
            self.token = ""
            self.sess.headers["authorization"] = "Bearer "
            self._get_token()
            info = self._api("GET", "v1/video/info/" + vid, xinfo=X_INFO_PLAY)
            diag += "|I2"
        else:
            diag += "|I1"

        video_urls = {}
        raw_pic = ""
        title = ""
        number = ""
        desc = ""
        actor = ""
        tags = ""

        if info and isinstance(info, dict) and "response" in info:
            r = info["response"]
            # 提取video_urls并拼接完整URL（使用stream host）
            vu = r.get("video_urls", {})
            if isinstance(vu, dict):
                for k, v in vu.items():
                    if isinstance(v, str):
                        if v.startswith("/"):
                            # 使用stream host拼接
                            stream_host = STREAM_HOSTS[0][1]
                            video_urls[k] = stream_host + v + ("&token=" if "?" in v else "?token=") + self.token
                        else:
                            video_urls[k] = v
            raw_pic = r.get("cover_url") or r.get("cover") or r.get("thumb", "")
            title = r.get("video_title", "")
            number = r.get("video_number", "")
            desc = r.get("video_description", "")
            a = r.get("actor", [])
            actor = "、".join(a) if isinstance(a, list) else str(a)
            tg = r.get("video_tags", [])
            tags = " ".join(tg) if isinstance(tg, list) else str(tg)
            diag += f"|t={title[:10]}"
            if video_urls:
                vu_preview = "|".join([f"{k}={str(v)[:20]}" for k, v in video_urls.items()])
                diag += f"|{vu_preview}"
        else:
            diag += "|Ierr"
            title = f"视频{vid}"

        # ===== 关键修复：不调用_fetch_m3u8，直接构造播放源 =====
        # 避免stream host连接超时导致TVBox转圈
        from_parts = []
        url_groups = []

        if video_urls:
            fb_parts = []
            for k in ["full", "intro", "preview"]:
                if k in video_urls and video_urls[k]:
                    fb_parts.append(f"{k}${video_urls[k]}")
            if fb_parts:
                from_parts = ["直接播放"]
                url_groups = ["$$$".join(fb_parts)]
                diag += "|FB=direct"

        if not from_parts:
            _log(f"[detail] 无播放地址 {diag}")
            return {"list": [{
                "vod_id": vid,
                "vod_name": title or f"视频{vid}",
                "vod_pic": self._img_url(raw_pic),
                "vod_remarks": diag[:100],
                "vod_content": desc or tags or "暂无描述",
                "vod_actor": actor,
                "vod_play_from": "暂无",
                "vod_play_url": "暂无$http://127.0.0.1",
            }]}

        diag += "|OK"
        _log(f"[detail] 成功 {diag}")

        return {"list": [{
            "vod_id": vid,
            "vod_name": title or f"视频{vid}",
            "vod_pic": self._img_url(raw_pic),
            "vod_remarks": diag,
            "vod_content": desc or tags or "暂无描述",
            "vod_actor": actor,
            "vod_play_from": "$$$".join(from_parts),
            "vod_play_url": ":::".join(url_groups),
        }]}

    # ==================== 播放（v28: 修复header使用真实token）====================

    def playerContent(self, flag, id, vipFlags=None):
        cookie_val = f"jwt={self.token}" if self.token else ""
        return {
            "parse": 0,
            "url": id,
            "header": json.dumps({
                "User-Agent": UA_CDN,
                "Cookie": cookie_val,
            }),
        }

    def localProxy(self, param):
        pass

    def searchContent(self, key, quick=False, pg=1):
        if not self.token:
            self._get_token()
        enc_key = urllib.parse.quote(key)
        data = self._api("GET", f"v1/search?q={enc_key}&page={pg}", xinfo=X_INFO_CENSOR)
        videos = []
        if data and "response" in data:
            items = data["response"].get("data", [])
            if isinstance(items, dict):
                items = [items]
            if not isinstance(items, list):
                items = []
            for v in items:
                vid = v.get("video_id")
                title = v.get("video_title", "")
                if not vid or not title:
                    continue
                raw_pic = v.get("cover") or v.get("thumb", "")
                actor = v.get("actor", "")
                if isinstance(actor, list):
                    actor = "、".join(actor)
                videos.append({
                    "vod_id": str(vid),
                    "vod_name": title,
                    "vod_pic": self._img_url(raw_pic),
                    "vod_remarks": actor,
                })
        return {
            "list": videos,
            "page": pg,
            "pagecount": 99,
            "limit": len(videos) or 20,
        }
