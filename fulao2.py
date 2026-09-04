# -*- coding: utf-8 -*-
# Fulao2 TVBox 爬虫 - 遮天九秘 v14 诊断版
# 新增：备用线路、请求头日志、Token强制刷新、错误回显

import sys, json, base64, gzip, urllib.parse, threading, time, socket, re
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

# ==================== 配置 ====================
API_DOMAIN = "https://api-al.uio2.fun"
IMG_DOMAIN = "https://images.uio2.fun"
PROXY_PORT = 8899

STREAM_HOSTS = [
    ("VIP高速1", "https://stream.uio2.fun"),
    ("海外线路", "https://stream.ass6.store"),   # 备用线路
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
# ==============================================

_M3U8_CACHE = {}
_CACHE_LOCK = threading.Lock()
_SERVER_STARTED = False
_LOG = []

# ==================== 全局 Token ====================
_global_token = ""
_global_token_lock = threading.Lock()
_spider_instance = None

def set_global_token(tok):
    global _global_token
    with _global_token_lock:
        _global_token = tok

def get_global_token():
    with _global_token_lock:
        return _global_token

def refresh_global_token():
    """强制通过 Spider 刷新 Token"""
    global _spider_instance
    if _spider_instance is not None:
        try:
            # 清除旧Token，强制重新获取
            _spider_instance.token = ""
            if _spider_instance._get_token():
                return True
        except Exception as e:
            _log("[refresh_token] 异常: %s" % e)
    else:
        _log("[refresh_token] Spider实例未注册")
    return False

def ensure_global_token():
    """确保 Token 有效，若无效则刷新"""
    tok = get_global_token()
    if not tok:
        _log("[ensure_token] Token为空，强制刷新")
        return refresh_global_token()
    return True
# ==============================================

def _log(msg):
    line = "[Fulao2] %s %s" % (time.strftime("%H:%M:%S"), msg)
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


# ==================== 工具函数 ====================

def _abs_url(url, default_host=None):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    host = default_host or STREAM_HOSTS[0][1]
    if url.startswith("/"):
        return host + url
    return host + "/" + url


def _has_signature(url):
    return "expire=" in url or "hash=" in url or "token=" in url or "jwt=" in url


def _decrypt_m3u8_data(text):
    t = text.strip() if isinstance(text, str) else ""
    if t.startswith("#EXTM3U"):
        return text
    try:
        ct = base64.b64decode(text)
        iv = bytes(a ^ b for a, b in zip(
            AES.new(RESP_KEY, AES.MODE_ECB).decrypt(ct[:16]),
            b'#EXTM3U\n#EXT-X-V',
        ))
        raw = unpad(AES.new(RESP_KEY, AES.MODE_CBC, iv).decrypt(ct), 16)
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        decoded = raw.decode('utf-8', errors='ignore')
        if decoded.strip().startswith("#EXTM3U"):
            return decoded
    except Exception:
        pass
    try:
        ct = base64.b64decode(text)
        iv_str = hashlib.md5(b"m3u8").hexdigest()[8:24]
        iv = iv_str.encode()
        raw = unpad(AES.new(RESP_KEY_NEW, AES.MODE_CBC, iv).decrypt(ct), 16)
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        decoded = raw.decode('utf-8', errors='ignore')
        if decoded.strip().startswith("#EXTM3U"):
            return decoded
    except Exception:
        pass
    return None


def _rewrite_m3u8_urls(m3u8_text, base_url):
    global PROXY_PORT
    proxy_base = "http://127.0.0.1:%d/" % PROXY_PORT
    lines = m3u8_text.split("\n")
    result = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            result.append(line)
            continue
        if line_stripped.startswith("#EXT-X-KEY") or line_stripped.startswith("#EXT-X-SESSION-KEY"):
            def rk(m):
                abs_uri = _abs_url(m.group(1), base_url)
                q = urllib.parse.quote(abs_uri, safe="")
                return 'URI="%sts?url=%s"' % (proxy_base, q)
            line = re.sub(r'URI="([^"]+)"', rk, line)
            result.append(line)
            continue
        if line_stripped.startswith("#EXT-X-MAP"):
            def rm(m):
                abs_uri = _abs_url(m.group(1), base_url)
                q = urllib.parse.quote(abs_uri, safe="")
                return 'URI="%sts?url=%s"' % (proxy_base, q)
            line = re.sub(r'URI="([^"]+)"', rm, line)
            result.append(line)
            continue
        if line_stripped.startswith("#EXT-X-MEDIA"):
            def rmed(m):
                abs_uri = _abs_url(m.group(1), base_url)
                q = urllib.parse.quote(abs_uri, safe="")
                return 'URI="%sm3u8?url=%s"' % (proxy_base, q)
            line = re.sub(r'URI="([^"]+)"', rmed, line)
            result.append(line)
            continue
        if line_stripped.startswith("#EXT-X-I-FRAME-STREAM-INF"):
            def rifr(m):
                abs_uri = _abs_url(m.group(1), base_url)
                q = urllib.parse.quote(abs_uri, safe="")
                return 'URI="%sm3u8?url=%s"' % (proxy_base, q)
            line = re.sub(r'URI="([^"]+)"', rifr, line)
            result.append(line)
            continue
        if not line_stripped.startswith("#"):
            abs_url = _abs_url(line_stripped, base_url)
            if abs_url:
                ep = "m3u8" if ".m3u8" in abs_url.lower() else "ts"
                q = urllib.parse.quote(abs_url, safe="")
                result.append("%s%s?url=%s" % (proxy_base, ep, q))
            else:
                result.append(line)
            continue
        result.append(line)
    return "\n".join(result)


# ==================== 代理 HTTP 服务 ====================

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/m3u8":
                cdn_url = urllib.parse.unquote(qs.get("url", [""])[0])
                vid_key = urllib.parse.unquote(qs.get("vid", [""])[0])
                if cdn_url or vid_key:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                    self.send_header("Connection", "close")
                    self._cors()
                    self.end_headers()
                else:
                    self.send_response(400)
                    self.end_headers()
            elif parsed.path == "/ts":
                cdn_url = urllib.parse.unquote(qs.get("url", [""])[0])
                if cdn_url:
                    self.send_response(200)
                    self.send_header("Content-Type", "video/mp2t")
                    self.send_header("Connection", "close")
                    self._cors()
                    self.end_headers()
                else:
                    self.send_response(400)
                    self.end_headers()
            elif parsed.path == "/img":
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Connection", "close")
                self.end_headers()
            elif parsed.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Connection", "close")
                self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            _log("[proxy_HEAD] ERR %s:%s" % (type(e).__name__, e))
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/m3u8":
                self._do_m3u8(qs)
            elif parsed.path == "/ts":
                self._do_ts(qs)
            elif parsed.path == "/img":
                self._do_img(qs)
            elif parsed.path == "/health":
                self._do_health(qs)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            _log("[proxy_GET] ERR %s:%s" % (type(e).__name__, e))
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode())

    def _err_m3u8(self, msg):
        # 将错误信息写入 m3u8 注释，某些播放器可显示
        err = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n#EXTINF:1.0,\nhttp://127.0.0.1/error?msg=%s\n#EXT-X-ENDLIST\n" % urllib.parse.quote(msg)
        data = err.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _make_cdn_headers(self, extra=None):
        """确保 Token 有效并构造头部"""
        # 强制刷新 Token（每次请求前刷新，确保最新）
        refresh_global_token()
        tok = get_global_token()
        headers = {
            "User-Agent": UA_CDN,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }
        try:
            api_host = urllib.parse.urlparse(API_DOMAIN).netloc
            headers["Referer"] = "https://" + api_host + "/"
            headers["Origin"] = "https://" + api_host
        except Exception:
            pass
        if tok:
            headers["Cookie"] = "jwt=%s" % tok
            headers["Authorization"] = "Bearer %s" % tok
        else:
            _log("[make_headers] ⚠️ Token 为空")
        if extra:
            headers.update(extra)
        return headers

    def _do_m3u8(self, qs):
        cdn_url = urllib.parse.unquote(qs.get("url", [""])[0])
        vid_key = urllib.parse.unquote(qs.get("vid", [""])[0])

        # 缓存模式
        if vid_key and not cdn_url:
            content = ""
            for _ in range(40):
                with _CACHE_LOCK:
                    content = _M3U8_CACHE.get(vid_key, "")
                if content:
                    break
                time.sleep(0.5)
            if content:
                data = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self._cors()
                self.end_headers()
                self.wfile.write(data)
                _log("[proxy_m3u8] 缓存命中 vid=%s" % vid_key)
                return
            else:
                self._err_m3u8("Cache miss: %s" % vid_key)
                return

        if not cdn_url:
            self._err_m3u8("Missing URL")
            return

        _log("[proxy_m3u8] 请求CDN: %s" % cdn_url[:120])

        # 尝试主线路，若403则自动切换备用线路
        hosts_to_try = STREAM_HOSTS  # 列表
        for idx, (label, host) in enumerate(hosts_to_try):
            # 如果CDN URL已经包含host，则直接用，否则替换host
            # 注意：cdn_url可能来自API，已经包含完整域名，但我们可能需要将域名替换为备用
            # 简单做法：尝试用备用host替换原host
            if idx == 0:
                target_url = cdn_url  # 第一次用原样
            else:
                # 将cdn_url中的第一个域名替换为备用host
                # 提取原host
                parsed = urllib.parse.urlparse(cdn_url)
                # 替换netloc为备用host
                new_parsed = parsed._replace(netloc=urllib.parse.urlparse(host).netloc)
                target_url = urllib.parse.urlunparse(new_parsed)
                _log("[proxy_m3u8] 尝试备用线路: %s" % target_url[:120])

            headers = self._make_cdn_headers()
            headers["x-info"] = X_INFO_PLAY

            # 打印脱敏头部（仅显示前几位）
            safe_headers = {k: (v[:10]+"..." if k in ("Cookie","Authorization") else v) for k,v in headers.items()}
            _log("[proxy_m3u8] Headers: %s" % json.dumps(safe_headers, ensure_ascii=False))

            try:
                resp = requests.get(target_url, headers=headers, timeout=20, verify=False, allow_redirects=True)
                preview = resp.text[:100].replace(chr(10), " ").replace(chr(13), " ")
                _log("[proxy_m3u8] 线路%s状态=%d len=%d preview=%s" % (label, resp.status_code, len(resp.content), preview))

                if resp.status_code in (401, 403):
                    _log("[proxy_m3u8] 认证失败，尝试刷新Token并重试")
                    if refresh_global_token():
                        # 重试一次当前线路
                        headers = self._make_cdn_headers()
                        headers["x-info"] = X_INFO_PLAY
                        resp2 = requests.get(target_url, headers=headers, timeout=20, verify=False)
                        if resp2.status_code == 200:
                            resp = resp2
                        else:
                            _log("[proxy_m3u8] 刷新后仍失败")
                            continue  # 尝试下一条线路
                    else:
                        continue

                if resp.status_code != 200:
                    _log("[proxy_m3u8] 线路%s 失败，状态码 %d" % (label, resp.status_code))
                    continue  # 尝试下一条线路

                # 成功 -> 解密/重写
                text = _decrypt_m3u8_data(resp.text)
                if text:
                    text = _rewrite_m3u8_urls(text, target_url)
                    data = text.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self._cors()
                    self.end_headers()
                    self.wfile.write(data)
                    _log("[proxy_m3u8] ✅ 成功 (线路%s)" % label)
                    return

                if resp.text.strip().startswith("#EXTM3U"):
                    text = _rewrite_m3u8_urls(resp.text, target_url)
                    data = text.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self._cors()
                    self.end_headers()
                    self.wfile.write(data)
                    _log("[proxy_m3u8] ✅ 成功 (原始m3u8) 线路%s" % label)
                    return

                _log("[proxy_m3u8] 无效内容，尝试下一条线路")
                continue

            except Exception as e:
                _log("[proxy_m3u8] 异常 %s:%s" % (type(e).__name__, e))
                continue

        # 所有线路均失败
        self._err_m3u8("AllLinesFailed_403")
        _log("[proxy_m3u8] ❌ 所有线路均失败")

    def _do_ts(self, qs):
        cdn_url = urllib.parse.unquote(qs.get("url", [""])[0])
        if not cdn_url:
            self.send_response(400)
            self.end_headers()
            return

        headers = self._make_cdn_headers()
        rng = self.headers.get("Range", "")
        if rng:
            headers["Range"] = rng

        try:
            resp = requests.get(cdn_url, headers=headers, timeout=20, verify=False, allow_redirects=True, stream=True)
            _log("[proxy_ts] status=%d url=%s" % (resp.status_code, cdn_url[:80]))
            self.send_response(resp.status_code)
            for k, v in resp.headers.items():
                kl = k.lower()
                if kl in ["content-type", "content-length", "cache-control", "accept-ranges", "content-range", "etag"]:
                    self.send_header(k, v)
            self.send_header("Connection", "close")
            self._cors()
            self.end_headers()
            if resp.status_code in [200, 206]:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        self.wfile.write(chunk)
        except Exception as e:
            _log("[proxy_ts] EXC %s:%s" % (type(e).__name__, e))
            self.send_response(502)
            self.end_headers()

    def _do_img(self, qs):
        url = urllib.parse.unquote(qs.get("url", [""])[0])
        try:
            r = requests.get(url, headers={"User-Agent": UA_IMG, "Accept-Encoding": "gzip", "Connection": "Keep-Alive"}, verify=False, timeout=10, allow_redirects=True)
            raw = r.content
            try:
                body = unpad(AES.new(IMG_KEY, AES.MODE_CBC, IMG_IV).decrypt(raw), 16)
            except Exception:
                body = raw
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            _log("[img_proxy] ERR %s" % e)
            self.send_response(502)
            self.end_headers()

    def _do_health(self, qs):
        data = b"OK"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)


class _ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _find_port(start=PROXY_PORT, max_try=10):
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
        PROXY_PORT = _find_port(PROXY_PORT)
        srv = _ThreadedServer(("127.0.0.1", PROXY_PORT), _Handler)
        t = threading.Thread(target=srv.serve_forever)
        t.daemon = True
        t.start()
        _SERVER_STARTED = True
        _log("代理服务已启动 127.0.0.1:%d" % PROXY_PORT)
    except Exception as e:
        _log("代理服务启动失败: %s" % e)


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
        global _spider_instance
        _spider_instance = self
        _start_server()
        _log("[init] 源初始化完成 代理端口=%d" % PROXY_PORT)

    def getName(self):
        return "Fulao2"

    def isVideoFormat(self, u):
        return True

    def manualVideoCheck(self):
        return False

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
                ct = base64.b64decode(text)
                iv_str = hashlib.md5(b"vtag").hexdigest()[8:24]
                iv = iv_str.encode()
                raw = unpad(AES.new(RESP_KEY_NEW, AES.MODE_CBC, iv).decrypt(ct), 16)
                if raw[:2] == b'\x1f\x8b':
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode())
            except Exception:
                try:
                    return json.loads(text)
                except:
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
                r = self.sess.post(url, data="payload=" + urllib.parse.quote(enc), headers=h, timeout=5)
            else:
                r = self.sess.get(url + "?payload=" + urllib.parse.quote(enc), headers=h, timeout=5)
            _log("[api] %s status=%d len=%d" % (path, r.status_code, len(r.text)))
            if r.status_code == 200:
                decrypted = self._decrypt_resp(r.text)
                if decrypted is None:
                    _log("[api] %s decrypt_fail raw=%s" % (path, r.text[:80]))
                else:
                    _log("[api] %s keys=%s" % (path, list(decrypted.keys()) if isinstance(decrypted, dict) else 'non-dict'))
                return decrypted
            _log("[api] %s err_status=%d body=%s" % (path, r.status_code, r.text[:150]))
            return None
        except Exception as e:
            _log("[api_err] %s %s:%s" % (path, type(e).__name__, e))
            return None

    def _get_token(self):
        if self.token:
            return True
        _log("[token] 开始获取...")
        diag = []
        try:
            data = self._api("POST", "v1/register/token")
            if data and "response" in data:
                resp = data["response"]
                self.token = resp.get("token", resp.get("access_token", ""))
                if self.token:
                    self.sess.headers["authorization"] = "Bearer " + self.token
                    set_global_token(self.token)
                    _log("[token] 旧接口成功 token=%s..." % self.token[:15])
                    return True
        except Exception as e:
            _log("[token] 旧接口异常: %s" % e)
            diag.append("old_exc:%s" % type(e).__name__)

        for attempt in range(3):
            try:
                r1 = self.sess.get(API_DOMAIN + "/v1/verify/code", timeout=8)
                if r1.status_code != 200:
                    diag.append("vc=%d" % r1.status_code)
                    time.sleep(1)
                    continue
                hash_val = r1.text.strip().strip('()').strip('"').strip("'").strip()
                if len(hash_val) != 32:
                    diag.append("hlen=%d" % len(hash_val))
                    time.sleep(1)
                    continue
                enc = self._encrypt_payload("v1/register/guest", {"hash": hash_val})
                r2 = self.sess.post(API_DOMAIN + "/v1/register/guest", data="payload=" + urllib.parse.quote(enc), headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=8)
                if r2.status_code != 200:
                    diag.append("rg=%d" % r2.status_code)
                    time.sleep(1)
                    continue
                x_vtag = ""
                for k, v in r2.headers.items():
                    if k.lower() == "x-vtag":
                        x_vtag = v
                        break
                if not x_vtag:
                    old_data = self._decrypt_resp(r2.text)
                    if old_data and "response" in old_data:
                        self.token = old_data["response"].get("token", "")
                        if self.token:
                            self.sess.headers["authorization"] = "Bearer " + self.token
                            set_global_token(self.token)
                            _log("[token] 旧解密成功")
                            return True
                    diag.append("old_decrypt_fail")
                    time.sleep(1)
                    continue
                iv_str = hashlib.md5(x_vtag.encode()).hexdigest()[8:24]
                iv = iv_str.encode()
                ct = base64.b64decode(r2.text)
                raw = unpad(AES.new(RESP_KEY_NEW, AES.MODE_CBC, iv).decrypt(ct), 16)
                guest_data = json.loads(raw.decode())
                if "response" in guest_data:
                    self.token = guest_data["response"].get("token", "")
                    if self.token:
                        self.sess.headers["authorization"] = "Bearer " + self.token
                        set_global_token(self.token)
                        _log("[token] Guest成功 token=%s..." % self.token[:15])
                        return True
                    diag.append("token_empty")
                else:
                    diag.append("no_resp:%s" % list(guest_data.keys()))
            except Exception as e:
                _log("[token] guest异常: %s:%s" % (type(e).__name__, e))
                diag.append("guest_exc:%s" % type(e).__name__)
            time.sleep(1)

        _log("[token] 所有方式均失败")
        self._token_diag = ";".join(diag)
        return False

    def _img_url(self, path):
        if not path:
            return ""
        full = path if path.startswith("http") else IMG_DOMAIN + ("" if path.startswith("/") else "/") + path
        return "http://127.0.0.1:%d/img?url=%s" % (PROXY_PORT, urllib.parse.quote(full, safe=""))

    def _fetch_m3u8(self, vid, h_label, h_host, quality, xinfo=None, direct_url=None):
        cache_key = vid + "_" + h_label + "_" + quality
        with _CACHE_LOCK:
            if cache_key in _M3U8_CACHE:
                return cache_key, "cached"
        if not direct_url:
            return None, "NOURL"
        url = _abs_url(direct_url, h_host)

        headers = {
            "User-Agent": UA_CDN,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }
        try:
            api_host = urllib.parse.urlparse(API_DOMAIN).netloc
            headers["Referer"] = "https://" + api_host + "/"
            headers["Origin"] = "https://" + api_host
        except Exception:
            pass
        tok = get_global_token()
        if tok:
            headers["Cookie"] = "jwt=%s" % tok
            headers["Authorization"] = "Bearer %s" % tok
        if xinfo:
            headers["x-info"] = xinfo

        _log("[_fetch_m3u8] 预加载: %s" % url[:90])
        try:
            resp = self.sess.get(url, headers=headers, timeout=20, allow_redirects=True)
            preview = resp.text[:100].replace(chr(10), " ").replace(chr(13), " ")
            _log("[_fetch_m3u8] status=%d len=%d preview=%s" % (resp.status_code, len(resp.content), preview))
            if resp.status_code == 200:
                text = _decrypt_m3u8_data(resp.text)
                if text:
                    text = _rewrite_m3u8_urls(text, url)
                    with _CACHE_LOCK:
                        _M3U8_CACHE[cache_key] = text
                    return cache_key, "GOK:%d" % text.count(chr(10))
                if resp.text.strip().startswith("#EXTM3U"):
                    text = _rewrite_m3u8_urls(resp.text, url)
                    with _CACHE_LOCK:
                        _M3U8_CACHE[cache_key] = text
                    return cache_key, "GOK_RAW:%d" % text.count(chr(10))
                return None, "Gfail:%s" % preview
            return None, "GS%d" % resp.status_code
        except Exception as e:
            _log("[_fetch_m3u8] 异常: %s:%s" % (type(e).__name__, e))
            return None, "GE%s" % type(e).__name__[:4]

    def _proxy_url(self, cdn_url):
        return "http://127.0.0.1:%d/m3u8?url=%s" % (PROXY_PORT, urllib.parse.quote(cdn_url, safe=""))

    def homeContent(self, filter=False):
        classes = []
        try:
            data = self._api("GET", "v2/menu/type")
        except Exception as e:
            _log("[homeContent] API异常: %s" % e)
            data = None
        if data and "response" in data:
            seen = set()
            for group in ["pixeled", "unpixeled"]:
                for item in data["response"].get(group, []):
                    t = item.get("title", "")
                    if t in TARGET_CATEGORIES and t not in seen:
                        seen.add(t)
                        classes.append({"type_id": str(item["id"]), "type_name": t})
        if not classes:
            _log("[homeContent] fallback分类")
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
        data = self._api("GET", "v1/menu/1/layout", xinfo=X_INFO_CENSOR)
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
                    videos.append({"vod_id": str(vid), "vod_name": title, "vod_pic": self._img_url(raw_pic), "vod_remarks": actor})
                    if len(videos) >= 30:
                        break
                if len(videos) >= 30:
                    break
        return {"list": videos}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        if not self.token:
            self._get_token()
        data = self._api("GET", "v1/menu/" + str(tid) + "/layout", xinfo=X_INFO_CENSOR)
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
                    videos.append({"vod_id": str(vid), "vod_name": title, "vod_pic": self._img_url(raw_pic), "vod_remarks": actor})
        return {"list": videos, "page": pg, "pagecount": 99, "limit": len(videos) or 20}

    def detailContent(self, ids):
        vid = str(ids[0])
        diag = "D%s" % vid
        _log("[detail] vid=%s" % vid)

        if not self.token:
            ok = self._get_token()
            diag += "|T%s" % ("OK" if ok else "NO")
        else:
            diag += "|TOK"

        info = self._api("GET", "v1/video/info/" + vid, xinfo=X_INFO_PLAY)
        if not info:
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
        desc = ""
        actor = ""
        tags = ""

        if info and isinstance(info, dict) and "response" in info:
            r = info["response"]
            vu = r.get("video_urls", {})
            if isinstance(vu, dict):
                for k, v in vu.items():
                    if isinstance(v, str) and v:
                        video_urls[k] = v
            raw_pic = r.get("cover_url") or r.get("cover") or r.get("thumb", "")
            title = r.get("video_title", "")
            desc = r.get("video_description", "")
            a = r.get("actor", [])
            actor = "、".join(a) if isinstance(a, list) else str(a)
            tg = r.get("video_tags", [])
            tags = " ".join(tg) if isinstance(tg, list) else str(tg)
            diag += "|t=%s" % title[:10]
        else:
            diag += "|Ierr"
            title = "视频%s" % vid

        from_parts = []
        url_groups = []

        if video_urls:
            fb_parts = []
            for k in ["full", "intro", "preview"]:
                if k in video_urls and video_urls[k]:
                    vurl = video_urls[k]
                    abs_url = _abs_url(vurl)
                    is_m3u8 = ".m3u8" in abs_url.lower() or not abs_url.lower().endswith((".mp4", ".mkv", ".flv"))
                    if is_m3u8:
                        h_label, h_host = STREAM_HOSTS[0]
                        cache_key, status = self._fetch_m3u8(vid, h_label, h_host, k, xinfo=X_INFO_PLAY, direct_url=vurl)
                        _log("[detail] _fetch_m3u8 k=%s status=%s" % (k, status))
                        if cache_key and (status.startswith("GOK") or status == "cached"):
                            proxy_url = "http://127.0.0.1:%d/m3u8?vid=%s" % (PROXY_PORT, urllib.parse.quote(cache_key, safe=""))
                            fb_parts.append("%s$%s" % (k, proxy_url))
                            diag += "|%s=cached" % k
                        else:
                            proxy_url = self._proxy_url(abs_url)
                            fb_parts.append("%s$%s" % (k, proxy_url))
                            diag += "|%s=proxy_live|%s" % (k, status)
                    else:
                        fb_parts.append("%s$%s" % (k, abs_url))
                        diag += "|%s=direct" % k
            if fb_parts:
                from_parts = ["Fulao2"]
                url_groups = ["$$$".join(fb_parts)]

        if not from_parts:
            _log("[detail] 无播放地址 %s" % diag)
            return {"list": [{"vod_id": vid, "vod_name": title or "视频%s" % vid, "vod_pic": self._img_url(raw_pic), "vod_remarks": diag[:100], "vod_content": desc or tags or "暂无描述", "vod_actor": actor, "vod_play_from": "暂无", "vod_play_url": "暂无$http://127.0.0.1"}]}

        diag += "|OK"
        _log("[detail] 成功 %s" % diag)
        return {"list": [{"vod_id": vid, "vod_name": title or "视频%s" % vid, "vod_pic": self._img_url(raw_pic), "vod_remarks": diag, "vod_content": desc or tags or "暂无描述", "vod_actor": actor, "vod_play_from": "$$$".join(from_parts), "vod_play_url": ":::".join(url_groups)}]}

    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith("http://127.0.0.1"):
            return {"parse": 0, "url": id, "header": ""}
        header_dict = {"User-Agent": UA_CDN}
        try:
            api_host = urllib.parse.urlparse(API_DOMAIN).netloc
            header_dict["Referer"] = "https://" + api_host + "/"
            header_dict["Origin"] = "https://" + api_host
        except Exception:
            pass
        tok = get_global_token()
        if tok:
            header_dict["Cookie"] = "jwt=%s" % tok
            header_dict["Authorization"] = "Bearer %s" % tok
        return {"parse": 0, "url": id, "header": json.dumps(header_dict, ensure_ascii=False), "ua": header_dict.get("User-Agent", ""), "referer": header_dict.get("Referer", "")}

    def localProxy(self, param):
        pass

    def searchContent(self, key, quick=False, pg=1):
        if not self.token:
            self._get_token()
        enc_key = urllib.parse.quote(key)
        data = self._api("GET", "v1/search?q=%s&page=%d" % (enc_key, pg), xinfo=X_INFO_CENSOR)
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
                videos.append({"vod_id": str(vid), "vod_name": title, "vod_pic": self._img_url(raw_pic), "vod_remarks": actor})
        return {"list": videos, "page": pg, "pagecount": 99, "limit": len(videos) or 20}