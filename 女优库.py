#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
whos.tv 女优数据爬虫 v8.7 —— 智能探查 + 快速增量

命令行参数:
  无参数                           全站爬取（遍历所有女优，每位爬取全部视频）
  "女优名"                         爬取指定单个女优的全部视频
  "女优名" 页数                    爬取指定女优指定页数的视频
  -1 列表.txt                      批量模式：从文本文件读取女优名单，依次爬取
  -1 列表.txt 页数                 批量模式并限制每位女优只爬指定页数
  --list 列表.txt                  同 -1
  -av                              排行榜模式：读取 https://whos.tv/ranking/actress
                                    按排名从高到低依次更新（有JSON的探查前N页，
                                    无JSON全量；遇到匹配页立即停止，N页全无则全量）
  --dir /输出目录                  指定输出文件的保存目录
  --login 用户名 密码              仅执行登录，保存Cookie后退出
  --register 用户名 密码 [邀请码]  仅执行注册，成功后退出
  --regen --dir /输出目录          从数据库重新生成所有女优JSON文件
  --help / -h                      显示帮助

输出文件（保存在 --dir 指定目录或 ./女优库输出/）:
  女优库汇总.db        SQLite数据库
  女优库全集.m3u       M3U播放列表（仅含m3u8直链）
  crawl_progress.json  爬取进度文件（断点续爬）
  actress_list_saved.json 女优列表缓存
  {女优名}.json        每个女优的TVBox格式JSON
"""

import os, sys, re, json, time, sqlite3, binascii, random, string
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Set
from urllib.parse import quote, unquote
from concurrent.futures import ThreadPoolExecutor, Future, wait as futures_wait, FIRST_COMPLETED
from threading import Lock, Event, Thread
import queue as _queue

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ╔══════════════════════════════════════════════════════════════╗
# ║                      配  置  层                              ║
# ╚══════════════════════════════════════════════════════════════╝

@dataclass
class Config:
    """全局配置，集中管理所有参数和路径"""
    # 网络
    base_url: str = "https://whos.tv"
    proxy_url: str = "http://127.0.0.1:10808"
    use_proxy: bool = False
    retries: int = 3
    timeout: int = 10

    # 爬取
    workers_video: int = 20
    consecutive_empty_limit: int = 10
    page_video: Optional[int] = None  # 命令行指定的页数限制

    # 排行榜探查页数配置
    ranking_probe_pages: int = 5   # 有本地JSON时先探查前N页找更新，0/负值=不限制
                                   # 遇到匹配页立即停止，N页全无则自动转为全量

    # 输出目录
    output_dir: str = ""

    @property
    def db_path(self) -> str:
        return os.path.join(self.output_dir, "女优库汇总.db")

    @property
    def m3u_path(self) -> str:
        return os.path.join(self.output_dir, "女优库全集.m3u")

    @property
    def progress_path(self) -> str:
        return os.path.join(self.output_dir, "crawl_progress.json")

    @property
    def actor_list_path(self) -> str:
        return os.path.join(self.output_dir, "actress_list_saved.json")

    @property
    def account_path(self) -> str:
        return os.path.join(self.output_dir, "account.json")

    @property
    def cookie_path(self) -> str:
        return os.path.join(self.output_dir, "cookies.json")

    def ensure_output_dir(self):
        os.makedirs(self.output_dir, exist_ok=True)

    def detect_proxy_from_env(self):
        env_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or ""
        if env_proxy:
            self.use_proxy = True
            self.proxy_url = env_proxy


# ╔══════════════════════════════════════════════════════════════╗
# ║                      工  具  函  数                          ║
# ╚══════════════════════════════════════════════════════════════╝

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]


def random_ua() -> str:
    """随机返回一个User-Agent"""
    return random.choice(USER_AGENTS)


def progress_bar(current: int, total: int, width: int = 25) -> str:
    """生成可视化进度条: [████░░░░░] 百分比%"""
    if total <= 0:
        return f"[{'.' * width}] 0%"
    percent = min(current / total * 100, 100.0)
    filled = int(width * current // total)
    filled = max(0, min(filled, width))
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percent:.0f}%"


def xor_decode(hex_str: str, key: int = 0x0E) -> str:
    """XOR解码封面URL"""
    raw = binascii.unhexlify(hex_str)
    return bytes(b ^ key for b in raw).decode("utf-8", errors="replace")


# ╔══════════════════════════════════════════════════════════════╗
# ║                    HTTP  客  户  端                          ║
# ╚══════════════════════════════════════════════════════════════╝

class HTTPClient:
    """封装所有HTTP请求，管理Session和Cookie"""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self._load_cookies()

    def _load_cookies(self):
        if os.path.exists(self.config.cookie_path):
            try:
                with open(self.config.cookie_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                from requests.cookies import cookiejar_from_dict
                self.session.cookies = cookiejar_from_dict(cookies)
            except Exception:
                pass

    def _save_cookies(self):
        try:
            cookie_dict = requests.utils.dict_from_cookiejar(self.session.cookies)
            with open(self.config.cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookie_dict, f, indent=2)
        except Exception as e:
            print(f"[警告] Cookie保存失败: {e}")

    @property
    def _proxies(self) -> Optional[dict]:
        if self.config.use_proxy and self.config.proxy_url:
            return {'http': self.config.proxy_url, 'https': self.config.proxy_url}
        return None

    def fetch_html(self, url: str) -> str:
        """获取HTML页面，带重试和自动重登录"""
        headers = {
            "User-Agent": random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Referer": self.config.base_url + "/",
        }
        for i in range(self.config.retries):
            try:
                resp = self.session.get(
                    url, headers=headers, proxies=self._proxies,
                    verify=False, timeout=self.config.timeout
                )
                if resp.status_code in (403, 429):
                    time.sleep((2 ** i) * random.uniform(2.0, 5.0))
                    continue
                if resp.status_code >= 400:
                    time.sleep((2 ** i) * random.uniform(1.0, 2.0))
                    continue
                if resp.status_code == 200 and "/login" in resp.url:
                    return ""
                return resp.text
            except Exception:
                if i < self.config.retries - 1:
                    time.sleep((2 ** i) * random.uniform(1.0, 2.0))
        return ""

    def api_call(self, method: str, path: str, data: dict = None) -> Optional[dict]:
        """调用API接口（登录/注册等）"""
        url = f"{self.config.base_url}{path}"
        headers = {
            "User-Agent": random_ua(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ja,en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Referer": self.config.base_url + "/",
            "Content-Type": "application/json",
        }
        for i in range(3):
            try:
                if method == "GET":
                    resp = self.session.get(
                        url, headers=headers, proxies=self._proxies,
                        verify=False, timeout=self.config.timeout
                    )
                else:
                    resp = self.session.post(
                        url, json=data, headers=headers, proxies=self._proxies,
                        verify=False, timeout=self.config.timeout
                    )
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    time.sleep(2 ** i * 2)
                else:
                    time.sleep(1)
            except Exception:
                time.sleep(1)
        return None

    def _load_account(self) -> Optional[dict]:
        if os.path.exists(self.config.account_path):
            try:
                with open(self.config.account_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None


# ╔══════════════════════════════════════════════════════════════╗
# ║                    认  证  管  理  器                        ║
# ╚══════════════════════════════════════════════════════════════╝

class AuthManager:
    """处理登录、注册、会话验证"""

    def __init__(self, config: Config, http: HTTPClient):
        self.config = config
        self.http = http

    def check_login(self) -> Optional[dict]:
        """验证当前Session是否已登录"""
        result = self.http.api_call("GET", "/api/user/profile")
        if result and result.get("code") == 200000 and result.get("data"):
            data = result["data"]
            nickname = data.get("nickname") or data.get("username", "")
            print(f"[✓] 当前已登录: {nickname}", flush=True)
            return data
        return None

    def login(self, username: str, password: str) -> bool:
        """登录并保存凭证"""
        print(f"[*] 登录 {username} ...", flush=True)
        result = self.http.api_call("POST", "/api/login", {"username": username, "password": password})
        if result and result.get("code") == 200000:
            print("[✓] 登录成功！", flush=True)
            self._save_account(username, password)
            self.http._save_cookies()
            return True
        msg = result.get("message") if result else "无法连接服务器"
        print(f"[✗] 登录失败: {msg}", flush=True)
        return False

    def register(self, username: str, password: str, invite_code: str = "") -> bool:
        """注册新账号"""
        data = {"username": username, "password": password}
        if invite_code:
            data["invite_code"] = invite_code
        print(f"[*] 注册账号 {username} ...", flush=True)
        result = self.http.api_call("POST", "/api/register", data)
        if result and result.get("code") == 200000:
            print("[✓] 注册成功！", flush=True)
            self.http._save_cookies()
            return True
        msg = result.get("message") if result else "无法连接服务器"
        print(f"[✗] 注册失败: {msg}", flush=True)
        return False

    def ensure_login(self, interactive: bool = True) -> bool:
        """确保已登录；interactive=True显示菜单，False自动注册"""
        if self.check_login():
            return True
        account = self.http._load_account()
        if account and account.get("username") and account.get("password"):
            print("[*] 尝试用保存的账号重新登录...")
            if self.login(account["username"], account["password"]):
                return True

        if interactive:
            return self._interactive_login()
        else:
            return self._auto_register()

    def _interactive_login(self) -> bool:
        print("=" * 50)
        print("  需要登录 whos.tv 账号")
        print("=" * 50)
        print("  1. 登录已有账号")
        print("  2. 注册新账号")
        print("  0. 退出")
        print("=" * 50)
        try:
            choice = input("  请选择 (0/1/2): ").strip()
        except (EOFError, KeyboardInterrupt):
            return False

        if choice == "1":
            try:
                u = input("  邮箱/用户名: ").strip()
                p = input("  密码: ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if u and p:
                return self.login(u, p)
        elif choice == "2":
            try:
                u = input("  用户名 (6-20字符): ").strip()
                p = input("  密码 (至少6位): ").strip()
                inv = input("  邀请码（选填）: ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if u and p and len(u) >= 6 and len(p) >= 6:
                if self.register(u, p, inv):
                    self._save_account(u, p)
                    return True
        return False

    def _auto_register(self) -> bool:
        """非交互式自动注册随机账号"""
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        auto_user = f"spider_{suffix}"
        auto_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        print(f"[*] 自动注册账号: {auto_user}")
        if self.register(auto_user, auto_pass):
            self._save_account(auto_user, auto_pass)
            return True
        print("[✗] 自动登录/注册均失败")
        return False

    def _save_account(self, username: str, password: str):
        try:
            with open(self.config.account_path, "w", encoding="utf-8") as f:
                json.dump({"username": username, "password": password}, f, indent=2)
        except Exception:
            pass


# ╔══════════════════════════════════════════════════════════════╗
# ║                    HTML  解  析  器                          ║
# ╚══════════════════════════════════════════════════════════════╝

class Parser:
    """所有HTML页面解析逻辑"""

    @staticmethod
    def parse_actor_list(html: str) -> List[str]:
        """从女优列表页解析女优名称"""
        names = set()
        for m in re.finditer(r'<a\s+href="/actresses/([^"/?]+)"', html):
            raw = m.group(1).strip()
            name = unquote(raw) if "%" in raw else raw
            if re.match(r"^page-\d+$", name, re.I):
                continue
            if name and not re.match(r"^[?&]", name) and not re.match(r"^[0-9a-f]{32}$", name, re.I):
                names.add(name)
        return sorted(names)

    @staticmethod
    def parse_ranking_actresses(html: str) -> List[str]:
        """从排行榜页面解析女优名称，保持排名顺序"""
        names = []
        seen = set()
        for m in re.finditer(r'<a\s+href="/actresses/([^"/?]+)"', html):
            raw = m.group(1).strip()
            name = unquote(raw) if "%" in raw else raw
            if name and not re.match(r"^(?:[?&]|page-\d+$|[0-9a-f]{32}$)", name, re.I):
                if name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    @staticmethod
    def detect_max_page(html: str) -> int:
        """从翻页控件检测最大页码"""
        pages = set()
        for m in re.finditer(r'/page-(\d+)', html):
            p = int(m.group(1))
            if 1 <= p <= 5000:
                pages.add(p)
        for m in re.finditer(r'[?&]page=(\d+)', html):
            p = int(m.group(1))
            if 1 <= p <= 500:
                pages.add(p)
        m = re.search(r'(?:Page|第)\s*(\d+)\s*(?:of|/)\s*(\d+)', html, re.I)
        if m:
            pages.add(int(m.group(2)))
        return max(pages) if pages else 1

    @staticmethod
    def parse_video_list(html: str) -> List[Tuple[str, str]]:
        """从视频列表页解析视频ID和加密封面"""
        videos = []
        seen = set()
        for m in re.finditer(r'<a\s+href="/videos/([^"]+)"[^>]*>.*?data-cover-src="([^"]*)"', html, re.DOTALL):
            vid = m.group(1).strip()
            enc = m.group(2).strip()
            if vid and vid not in seen:
                seen.add(vid)
                videos.append((vid, enc) if enc else (vid, ""))
        for m in re.finditer(r'<a\s+href="/videos/([^"]+)"[^>]*>', html):
            vid = m.group(1).strip()
            if vid and vid not in seen:
                seen.add(vid)
                videos.append((vid, ""))
        return videos

    @staticmethod
    def parse_total_works(html: str) -> Optional[int]:
        """从女优页面提取作品总数"""
        m = re.search(r'text-primary[^>]*>(\d+)</p>\s*<p[^>]*>作品数', html)
        if m:
            return int(m.group(1))
        m = re.search(r'(\d+)</p>\s*<p[^>]*>作品数', html)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def parse_actress_avatar(html: str) -> str:
        """提取女优头像URL"""
        m = re.search(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*avatar[^"\']*["\']', html, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r'<img[^>]*src=["\']([^"\']+(?:avatar|actress|face|head)[^"\']*)["\']', html, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.I)
        if m:
            return m.group(1).strip()
        return ""

    @staticmethod
    def parse_video_detail(html: str, video_id: str) -> dict:
        """从视频详情页解析完整信息"""
        info = {
            "vod_id": video_id, "vod_name": video_id, "vod_pic": "",
            "vod_actor": "", "vod_director": "whos.tv", "vod_play_from": "whos.tv",
            "vod_play_url": "", "vod_content": "", "vod_area": "", "vod_year": "",
            "vod_remarks": "HD高清", "vod_tag": "", "duration": "", "date": "",
            "m3u8": "", "cover": "", "tags": [], "actors": [],
        }
        if not html:
            return info

        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
        if m:
            info["vod_name"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        for p in [r"(?:时长|duration|runtime)[：:]\s*(\S+)", r"(\d+[：:]\d+)\s*(?:分|min)", r"(\d+)分(?:钟|)"]:
            m = re.search(p, html, re.I)
            if m:
                info["duration"] = m.group(1).strip()
                break

        for p in [r"(?:日期|date|release)[：:]\s*(\S+)", r"(\d{4}[-/]\d{2}[-/]\d{2})", r"(\d{4}年\d{1,2}月\d{1,2}日)"]:
            m = re.search(p, html, re.I)
            if m:
                info["date"] = m.group(1).strip()
                break

        for area in ["日本", "美国", "欧美", "韩国", "中国", "台湾", "香港"]:
            if area in html[:5000]:
                info["vod_area"] = area
                break

        m = re.search(r"(\d{4})\s*年", html)
        if m:
            info["vod_year"] = m.group(1)
        elif info["date"]:
            m2 = re.search(r"(\d{4})", info["date"])
            if m2:
                info["vod_year"] = m2.group(1)

        info["tags"] = re.findall(r'<a\s+href="/tags/([^"]+)"[^>]*>([^<]+)</a>', html)
        info["tags"] = [t[1].strip() if t[1].strip() else t[0] for t in info["tags"]]
        info["vod_tag"] = ",".join(sorted(set(info["tags"])))

        info["actors"] = re.findall(r'<a\s+href="/actresses/([^"]+)"[^>]*>([^<]+)</a>', html)
        info["actors"] = [a[1].strip() for a in info["actors"] if a[1].strip()]
        seen_a = set()
        info["actors"] = [a for a in info["actors"] if not (a in seen_a or seen_a.add(a))]
        info["vod_actor"] = ",".join(info["actors"])

        for p in [
            r"(?:剧情|介绍|简介|description|story)[：:]\s*([^<]+)",
            r'<meta\s+name="description"\s+content="([^"]+)"',
            r'<div[^>]*class="[^"]*desc(?:ription)?[^"]*"[^>]*>([^<]+)',
        ]:
            m = re.search(p, html, re.I)
            if m:
                info["vod_content"] = m.group(1).strip()
                break

        m = re.search(r'"([^"]+\.m3u8[^"]*)"', html)
        if m:
            info["m3u8"] = m.group(1).strip()
        info["vod_play_url"] = info["m3u8"] if info["m3u8"] else ""

        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.I)
        if m:
            info["cover"] = m.group(1).strip()
            info["vod_pic"] = info["cover"]

        return info


# ╔══════════════════════════════════════════════════════════════╗
# ║                    存  储  管  理  器                        ║
# ╚══════════════════════════════════════════════════════════════╝

class StorageManager:
    """数据库、JSON、M3U、进度文件的读写"""

    def __init__(self, config: Config):
        self.config = config
        self._m3u_lock = Lock()
        self._json_lock = Lock()
        self._progress_lock = Lock()
        self._db_lock = Lock()

    def init_db(self):
        """初始化SQLite数据库"""
        with self._db_lock:
            conn = sqlite3.connect(self.config.db_path, timeout=60)
            c = conn.cursor()
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA busy_timeout=30000")
            c.execute("""CREATE TABLE IF NOT EXISTS actress_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                video_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                update_time TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actress_id INTEGER,
                vod_id TEXT, vod_name TEXT, vod_pic TEXT, vod_actor TEXT,
                vod_director TEXT DEFAULT 'whos.tv',
                vod_play_from TEXT, vod_url TEXT,
                duration TEXT, tags TEXT, date TEXT, vod_content TEXT,
                vod_area TEXT, vod_year TEXT, vod_remarks TEXT, vod_tag TEXT,
                m3u8 TEXT,
                FOREIGN KEY(actress_id) REFERENCES actress_info(id)
            )""")
            conn.commit()
            conn.close()

    def save_video(self, actress_name: str, vinfo: dict):
        """保存一个视频详情到数据库"""
        for attempt in range(3):
            try:
                with self._db_lock:
                    conn = sqlite3.connect(self.config.db_path, timeout=60)
                    c = conn.cursor()
                    c.execute("PRAGMA journal_mode=WAL")
                    c.execute("PRAGMA synchronous=NORMAL")
                    c.execute("PRAGMA busy_timeout=30000")
                    c.execute("SELECT id FROM actress_info WHERE name=?", (actress_name,))
                    r = c.fetchone()
                    if r:
                        actress_id = r[0]
                    else:
                        c.execute(
                            "INSERT INTO actress_info (name, status, update_time) VALUES (?, 'running', datetime('now'))",
                            (actress_name,)
                        )
                        actress_id = c.lastrowid
                    tags_str = ",".join(vinfo.get("tags", []))
                    c.execute("""INSERT OR IGNORE INTO videos
                        (actress_id, vod_id, vod_name, vod_pic, vod_actor, vod_director,
                         vod_play_from, vod_url, duration, tags, date,
                         vod_content, vod_area, vod_year, vod_remarks, vod_tag, m3u8)
                        VALUES (?,?,?,?,?,'whos.tv',?,?,?,?,?,?,?,?,?,?,?)""",
                        (actress_id, vinfo.get("vod_id", ""), vinfo.get("vod_name", ""),
                         vinfo.get("vod_pic", ""), vinfo.get("vod_actor", ""), "whos.tv",
                         vinfo.get("vod_play_url", ""), vinfo.get("duration", ""), tags_str,
                         vinfo.get("date", ""), vinfo.get("vod_content", ""),
                         vinfo.get("vod_area", ""), vinfo.get("vod_year", ""),
                         vinfo.get("vod_remarks", "HD高清"), vinfo.get("vod_tag", ""),
                         vinfo.get("m3u8", "")))
                    c.execute(
                        "UPDATE actress_info SET video_count=(SELECT COUNT(*) FROM videos WHERE actress_id=?) WHERE id=?",
                        (actress_id, actress_id)
                    )
                    conn.commit()
                    conn.close()
                return
            except sqlite3.OperationalError as e:
                try:
                    conn.close()
                except Exception:
                    pass
                if "readonly" in str(e).lower() and attempt < 2:
                    time.sleep((attempt + 1) * 2.0)
                    continue
                raise

    def get_actress_videos(self, actress_name: str) -> List[tuple]:
        """获取女优的所有视频记录"""
        conn = sqlite3.connect(self.config.db_path, timeout=60)
        c = conn.cursor()
        c.execute("SELECT id FROM actress_info WHERE name=?", (actress_name,))
        r = c.fetchone()
        if not r:
            conn.close()
            return []
        c.execute("""SELECT vod_id, vod_name, vod_pic, vod_actor, vod_play_from, vod_url,
                     duration, tags, date, vod_content, vod_area, vod_year, vod_remarks, vod_tag, m3u8
                     FROM videos WHERE actress_id=? ORDER BY date DESC""", (r[0],))
        rows = c.fetchall()
        conn.close()
        return rows

    def get_all_actresses(self) -> List[Tuple[int, str]]:
        """获取所有女优的ID和名称"""
        if not os.path.exists(self.config.db_path):
            return []
        conn = sqlite3.connect(self.config.db_path, timeout=60)
        c = conn.cursor()
        c.execute("SELECT id, name FROM actress_info")
        rows = c.fetchall()
        conn.close()
        return rows

    def update_m3u(self, actress_name: str, vinfo: dict):
        """追加m3u8链接到M3U播放列表"""
        vod_id = vinfo.get("vod_id", "")
        m3u8 = vinfo.get("m3u8", "")
        if not m3u8:
            return
        with self._m3u_lock:
            if os.path.exists(self.config.m3u_path):
                with open(self.config.m3u_path, "r", encoding="utf-8") as f:
                    if vod_id in f.read():
                        return
            with open(self.config.m3u_path, "a", encoding="utf-8") as f:
                if os.path.getsize(self.config.m3u_path) == 0:
                    f.write("#EXTM3U\n#EXT-X-VERSION:3\n")
                f.write(f'#EXTINF:-1 tvg-logo="{vinfo.get("vod_pic", "")}" group-title="{actress_name}",{vod_id}\n')
                f.write(f"{m3u8}\n")

    def write_actress_json(self, actress_name: str, tvbox_list: List[dict]):
        """输出TVBox格式JSON"""
        with self._json_lock:
            fp = os.path.join(self.config.output_dir, f"{actress_name}.json")
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(
                    {"actress": actress_name, "list": tvbox_list, "count": len(tvbox_list)},
                    f, ensure_ascii=False, indent=2
                )

    def load_existing_video_ids(self, actress_name: str) -> Set[str]:
        """从本地JSON文件中读取已有的视频ID集合"""
        fp = os.path.join(self.config.output_dir, f"{actress_name}.json")
        if not os.path.exists(fp):
            return set()
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "list" in data:
                existing = [item["vod_id"] for item in data["list"]
                           if isinstance(item, dict) and "vod_id" in item]
                return set(existing)
        except Exception as e:
            print(f"[警告] 读取 {fp} 失败: {e}")
        return set()

    def load_progress(self) -> dict:
        if os.path.exists(self.config.progress_path):
            try:
                with open(self.config.progress_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_progress(self, progress: dict):
        with self._progress_lock:
            with open(self.config.progress_path, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

    def load_actor_list(self) -> Optional[List[str]]:
        if os.path.exists(self.config.actor_list_path):
            try:
                with open(self.config.actor_list_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def save_actor_list(self, names: List[str]):
        try:
            with open(self.config.actor_list_path, "w", encoding="utf-8") as f:
                json.dump(names, f, ensure_ascii=False, indent=2)
            print(f"[*] 演员库列表已保存到 {self.config.actor_list_path}")
        except Exception as e:
            print(f"[警告] 保存演员列表失败: {e}")

    @staticmethod
    def read_names_from_source(path: str) -> List[str]:
        """从文件或目录读取女优名单"""
        names = []
        if os.path.isdir(path):
            print(f"[*] 扫描目录 {path} 下的 .txt 文件...")
            txt_files = sorted([f for f in os.listdir(path) if f.endswith(".txt")])
            if not txt_files:
                print(f"[错误] 目录 {path} 下没有 .txt 文件")
                return []
            for fname in txt_files:
                n = StorageManager._read_names_file(os.path.join(path, fname))
                print(f"    {fname}: {len(n)} 个名字")
                names.extend(n)
        else:
            names = StorageManager._read_names_file(path)
        seen = set()
        result = []
        for n in names:
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result

    @staticmethod
    def _read_names_file(fpath: str) -> List[str]:
        names = []
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("//"):
                        names.append(line)
        except Exception as e:
            print(f"[警告] 无法读取 {fpath}: {e}")
        return names


# ╔══════════════════════════════════════════════════════════════╗
# ║                    爬  虫  引  擎                            ║
# ╚══════════════════════════════════════════════════════════════╝

class CrawlerEngine:
    """核心爬取逻辑：获取女优列表 + 爬取视频详情"""

    def __init__(self, config: Config, http: HTTPClient, storage: StorageManager):
        self.config = config
        self.http = http
        self.storage = storage
        self._actress_avatar_cache: Dict[str, str] = {}

    def fetch_actress_list(self) -> List[str]:
        """串行翻页获取全站女优名称"""
        print("[*] 开始爬取女优列表...")
        names = []
        page = 1
        while True:
            url = f"{self.config.base_url}/actresses/page-{page}" if page > 1 else f"{self.config.base_url}/actresses"
            html = self.http.fetch_html(url)
            if not html:
                break
            page_names = Parser.parse_actor_list(html)
            if not page_names:
                break
            names.extend(page_names)
            print(f"\r[*] 已获取 {len(names)} 位女优 ({page} 页)...", end="", flush=True)
            max_p = Parser.detect_max_page(html)
            if max_p and page >= max_p:
                break
            page += 1
        print(f"\n[✓] 共获取 {len(names)} 位女优")
        return names

    def fetch_ranking_actresses(self) -> List[str]:
        """爬取排行榜页面，返回按排名排序的女优列表"""
        url = f"{self.config.base_url}/ranking/actress"
        html = self.http.fetch_html(url)
        if not html:
            print("[✗] 无法获取排行榜页面")
            return []
        names = Parser.parse_ranking_actresses(html)
        print(f"[✓] 排行榜共 {len(names)} 位女优")
        return names

    def fetch_video_detail(self, video_id: str, cover_enc: str = "") -> Optional[dict]:
        """爬取单个视频详情页"""
        html = self.http.fetch_html(f"{self.config.base_url}/videos/{video_id}")
        info = Parser.parse_video_detail(html, video_id)
        if cover_enc and not info.get("cover"):
            try:
                decoded = xor_decode(cover_enc)
                if decoded:
                    info["cover"] = decoded
                    info["vod_pic"] = decoded
            except Exception:
                pass
        return info if html else None

    def crawl_actress_videos(self, name: str, progress: dict, max_pages: Optional[int] = None,
                               early_stop_max_pages: Optional[int] = None) -> dict:
        """爬取单个女优的所有视频，边翻页边下载

        Args:
            early_stop_max_pages: 探查模式页数限制。
                - 第一页有匹配 → 立即停止翻页
                - 第一页全无匹配 → 继续翻页到遇到匹配页或达到上限
                - 达到上限后仍无匹配 → 取消限制全量爬取
        """
        prog = progress.get(name, {})
        if not isinstance(prog, dict):
            prog = {}

        encoded_name = quote(name, safe='')
        html_first = self.http.fetch_html(f"{self.config.base_url}/actresses/{encoded_name}")
        if not html_first:
            print(f"[错误] 无法获取 {name} 首页，跳过")
            return progress

        total_works = Parser.parse_total_works(html_first)
        if not total_works:
            print(f"[✗] {name}: 页面未找到作品数，跳过")
            return progress

        avatar_url = Parser.parse_actress_avatar(html_first)
        self._actress_avatar_cache[name] = avatar_url

        max_page = Parser.detect_max_page(html_first)
        if max_pages is not None:
            total_pages = max_pages
        elif self.config.page_video is not None and self.config.page_video > 0:
            total_pages = min(self.config.page_video, max_page)
        else:
            total_pages = max_page

        scraped_set = set(prog.get("scraped_videos", []))
        already = len(scraped_set)

        if already >= total_works and total_works > 0:
            print(f"[✓] {name}: 所有视频已爬完 ({already}/{total_works})")
            prog.update(status="finished", total_video=total_works, success_video=already,
                        scraped_videos=list(scraped_set))
            progress[name] = prog
            self.storage.save_progress(progress)
            return progress

        # ── 生产者-消费者模式 ──
        task_q: _queue.Queue = _queue.Queue()
        submit_done = Event()

        # 保存初始已有视频ID集合（只读，不随本次新增改变）
        initial_existing = set(scraped_set)

        def _page_submitter():
            try:
                first_page_videos = Parser.parse_video_list(html_first)
                probe_limit = early_stop_max_pages  # 探查上限，可能为 None

                # ── 首页处理 ──
                if probe_limit is not None and first_page_videos:
                    first_all_existing = all(v in initial_existing for v, _ in first_page_videos)
                    first_any_existing = any(v in initial_existing for v, _ in first_page_videos)

                    # 全部已有 → 完全跳过
                    if first_all_existing:
                        submit_done.set()
                        return

                    # 提交第一页所有视频（消费者会过滤已有的）
                    for v, e in first_page_videos:
                        task_q.put((v, e))

                    # 部分已有 → 立即停止翻页（后续页只会更旧）
                    if first_any_existing:
                        submit_done.set()
                        return
                    # 全无匹配 → 继续翻页探查（不返回，fallthrough）
                else:
                    # 无探查限制（无JSON或配置为0），正常提交第一页
                    for v, e in first_page_videos:
                        task_q.put((v, e))

                # ── 后续翻页（仅当第一页全不匹配或未启用探查限制时执行） ──
                empty = 0
                pg = 2
                while pg <= total_pages:
                    # 如果超过探查页数上限且仍无匹配 → 取消限制全量
                    if probe_limit is not None and pg > probe_limit:
                        print(f"    [-] {name}: 前{probe_limit}页均无匹配，转为全量爬取", flush=True)
                        probe_limit = None  # 取消限制，继续翻页

                    url = f"{self.config.base_url}/actresses/{encoded_name}/page-{pg}"
                    html = self.http.fetch_html(url)
                    if not html:
                        empty += 1
                        if empty >= self.config.consecutive_empty_limit:
                            break
                        pg += 1
                        continue
                    empty = 0
                    page_videos = Parser.parse_video_list(html)

                    if page_videos:
                        has_match = any(v in initial_existing for v, _ in page_videos)
                        # 提交该页所有视频
                        for v, e in page_videos:
                            task_q.put((v, e))
                        # 有匹配 → 停止翻页（后续页全是更旧的）
                        if has_match:
                            break
                        # 全不匹配 → 继续翻页
                    pg += 1
            finally:
                submit_done.set()

        Thread(target=_page_submitter, daemon=True).start()

        completed: Set[str] = set(scraped_set)
        done = 0
        write_cnt = 0
        active: Dict[Future, str] = {}
        submitted: Set[str] = set(scraped_set)

        ex = ThreadPoolExecutor(max_workers=self.config.workers_video)
        try:
            while True:
                try:
                    while True:
                        v, e = task_q.get_nowait()
                        if v not in completed and v not in submitted:
                            submitted.add(v)
                            active[ex.submit(self.fetch_video_detail, v, e)] = v
                except _queue.Empty:
                    pass

                if active:
                    try:
                        done_set, _ = futures_wait(active.keys(), timeout=8, return_when=FIRST_COMPLETED)
                    except KeyboardInterrupt:
                        break
                    for f in list(done_set):
                        if not f.done():
                            continue
                        vid = active.pop(f)
                        try:
                            info = f.result(timeout=5)
                        except Exception:
                            info = None
                        done += 1
                        cur = already + done
                        if info and vid not in completed:
                            completed.add(vid)
                            self.storage.save_video(name, info)
                            self.storage.update_m3u(name, info)
                            write_cnt += 1
                            if write_cnt % 10 == 0:
                                prog.update(
                                    status="running", scraped_videos=list(completed),
                                    success_video=cur, total_video=total_works
                                )
                                progress[name] = prog
                                self.storage.save_progress(progress)
                        # 单行进度条（回车覆盖，兼容Android终端）
                        display_name = name[:8] + "…" if len(name) > 8 else name
                        line = f"[{display_name}]已爬取{cur}/{total_works}部 {progress_bar(cur, total_works)}"
                        os.write(1, f"\r\033[K{line}".encode())
                else:
                    time.sleep(0.2)

                if submit_done.is_set():
                    try:
                        while True:
                            v, e = task_q.get_nowait()
                            if v not in completed and v not in submitted:
                                submitted.add(v)
                                active[ex.submit(self.fetch_video_detail, v, e)] = v
                    except _queue.Empty:
                        pass
                    if not active:
                        break
        finally:
            for f in active:
                f.cancel()
            ex.shutdown(wait=False, cancel_futures=True)

        # 清除进度条（回车清行），为下一个女优的输出做准备
        os.write(1, b"\r\033[K")

        prog.update(
            status="finished", total_video=total_works, success_video=len(completed),
            scraped_videos=list(completed)
        )
        progress[name] = prog
        self.storage.save_progress(progress)

        self._generate_actress_json(name)
        return progress

    def _generate_actress_json(self, name: str):
        """为单个女优生成TVBox格式JSON"""
        try:
            rows = self.storage.get_actress_videos(name)
            tvbox_list = [{
                "vod_id": r[0], "vod_name": r[1], "vod_pic": r[2],
                "vod_actor": r[3], "vod_play_from": r[4], "vod_play_url": r[5],
                "duration": r[6], "tags": r[7], "date": r[8],
                "vod_content": r[9], "vod_area": r[10], "vod_year": r[11],
                "vod_remarks": r[12], "vod_tag": r[13], "m3u8": r[14],
            } for r in rows]
            self.storage.write_actress_json(name, tvbox_list)
            print(f"[✓] {name}: JSON已生成 ({len(tvbox_list)} 部)")
        except Exception as e:
            print(f"[警告] {name} JSON生成失败: {e}")

    def regen_all_jsons(self):
        """从数据库重建所有女优JSON"""
        if not os.path.exists(self.config.db_path):
            print(f"[✗] 数据库不存在: {self.config.db_path}")
            return
        actresses = self.storage.get_all_actresses()
        print(f"[*] 数据库中共 {len(actresses)} 位女优，开始重新生成JSON...")
        for aid, aname in actresses:
            rows = self.storage.get_actress_videos(aname)
            tvbox_list = [{
                "vod_id": r[0], "vod_name": r[1], "vod_pic": r[2],
                "vod_actor": r[3], "vod_play_from": r[4], "vod_play_url": r[5],
                "duration": r[6], "tags": r[7], "date": r[8],
                "vod_content": r[9], "vod_area": r[10], "vod_year": r[11],
                "vod_remarks": r[12], "vod_tag": r[13], "m3u8": r[14],
            } for r in rows]
            self.storage.write_actress_json(aname, tvbox_list)
            print(f"  [✓] {aname} ({len(tvbox_list)} 部)")
        print("[✓] 全部JSON重新生成完成！")


# ╔══════════════════════════════════════════════════════════════╗
# ║                    任  务  调  度  器                        ║
# ╚══════════════════════════════════════════════════════════════╝

class TaskRunner:
    """协调各项爬取任务：单女优、批量、全站、排行榜"""

    def __init__(self, config: Config, http: HTTPClient, storage: StorageManager,
                 auth: AuthManager, engine: CrawlerEngine):
        self.config = config
        self.http = http
        self.storage = storage
        self.auth = auth
        self.engine = engine

    def run_single(self, name: str, pages: Optional[int] = None):
        """爬取单个女优"""
        progress = self.storage.load_progress()
        print(f"[*] 开始爬取: {name}")
        try:
            progress = self.engine.crawl_actress_videos(name, progress, max_pages=pages)
        except Exception as e:
            print(f"[✗] {name} 爬取异常: {e}")
            import traceback
            traceback.print_exc()
        print("[✓] 完成")

    def run_batch(self, list_path: str, pages: Optional[int] = None):
        """从名单文件批量爬取"""
        names = StorageManager.read_names_from_source(list_path)
        if not names:
            print("[✗] 列表为空或无法读取")
            return
        print(f"[*] 共 {len(names)} 位女优待爬取")
        progress = self.storage.load_progress()
        total = len(names)
        for idx, name in enumerate(names, 1):
            print(f"\n{'=' * 60}")
            print(f"[{idx}/{total}] 开始爬取: {name}")
            print(f"{'=' * 60}")
            try:
                progress = self.engine.crawl_actress_videos(name, progress, max_pages=pages)
            except Exception as e:
                print(f"[✗] {name} 爬取异常: {e}")
                import traceback
                traceback.print_exc()
                prog = progress.get(name, {})
                prog["status"] = "error"
                progress[name] = prog
                self.storage.save_progress(progress)
        print("\n[✓] 批量爬取完成！")

    def run_ranking(self):
        """按排行榜从高到低依次爬取女优视频（智能探查 + 快速增量）"""
        names = self.engine.fetch_ranking_actresses()
        if not names:
            print("[✗] 未能获取排行榜名单，退出")
            return
        # 保存排行榜名单
        self.storage.save_actor_list(names)

        progress = self.storage.load_progress()
        total = len(names)
        print(f"[*] 共 {total} 位女优，按排名从高到低依次增量更新")
        for idx, name in enumerate(names, 1):
            print(f"\n{'=' * 60}")
            print(f"[{idx}/{total}] [{name}]")
            print(f"{'=' * 60}")

            # 读取本地已有 JSON，将其中的 video_id 注入 progress 的 scraped_videos
            existing_ids = self.storage.load_existing_video_ids(name)
            has_local_existing = bool(existing_ids)
            if existing_ids:
                prog = progress.get(name, {})
                if not isinstance(prog, dict):
                    prog = {}
                scraped = set(prog.get("scraped_videos", []))
                old_count = len(scraped)
                scraped.update(existing_ids)
                if len(scraped) > old_count:
                    prog["scraped_videos"] = list(scraped)
                    progress[name] = prog
                    print(f"    [-] 合并本地JSON已有 {len(existing_ids)} 个视频ID，"
                          f"跳过已爬取的 {len(scraped)} 个")

            try:
                # 有本地 JSON 才使用探查模式，无 JSON 则全量爬取
                if has_local_existing:
                    early_stop_pages = self.config.ranking_probe_pages
                    if early_stop_pages <= 0:
                        early_stop_pages = None
                    progress = self.engine.crawl_actress_videos(name, progress,
                                                                early_stop_max_pages=early_stop_pages)
                else:
                    progress = self.engine.crawl_actress_videos(name, progress)
            except Exception as e:
                print(f"[✗] {name} 爬取异常: {e}")
                import traceback; traceback.print_exc()
                prog = progress.get(name, {})
                if isinstance(prog, dict):
                    prog["status"] = "error"
                else:
                    prog = {"status": "error"}
                progress[name] = prog
                self.storage.save_progress(progress)
        print("\n[✓] 排行榜更新完成！")

    def run_all(self):
        """全站爬取"""
        names = self.engine.fetch_actress_list()
        if not names:
            print("[✗] 未能获取任何女优，退出")
            return
        self.storage.save_actor_list(names)
        progress = self.storage.load_progress()
        total = len(names)
        for idx, name in enumerate(names, 1):
            print(f"\n{'=' * 60}")
            print(f"[{idx}/{total}] 开始爬取: {name}")
            print(f"{'=' * 60}")
            try:
                progress = self.engine.crawl_actress_videos(name, progress)
            except Exception as e:
                print(f"[✗] {name} 爬取异常: {e}")
                import traceback
                traceback.print_exc()
                prog = progress.get(name, {})
                prog["status"] = "error"
                progress[name] = prog
                self.storage.save_progress(progress)
        print("\n[✓] 全站爬取完成！")


# ╔══════════════════════════════════════════════════════════════╗
# ║                    CLI  入  口                               ║
# ╚══════════════════════════════════════════════════════════════╝

def parse_args(raw_args: List[str]) -> Tuple[dict, List[str]]:
    """
    解析命令行参数，分离 --dir 等控制参数与位置参数
    返回: (options_dict, remaining_args)
    """
    options = {"dir": None}
    remaining = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg == "--dir":
            if i + 1 < len(raw_args):
                options["dir"] = raw_args[i + 1]
                i += 2
                continue
        remaining.append(arg)
        i += 1
    return options, remaining


def main():
    args = sys.argv[1:]

    opts, args = parse_args(args)

    custom_dir = opts["dir"]
    if custom_dir:
        output_dir = custom_dir
    else:
        output_dir = os.path.join(os.getcwd(), "女优库输出")

    config = Config(output_dir=output_dir)
    config.detect_proxy_from_env()
    config.ensure_output_dir()

    http = HTTPClient(config)
    auth = AuthManager(config, http)
    storage = StorageManager(config)
    engine = CrawlerEngine(config, http, storage)
    runner = TaskRunner(config, http, storage, auth, engine)

    print(f"[*] 输出目录: {config.output_dir}")
    storage.init_db()

    if "--login" in args:
        idx = args.index("--login")
        if idx + 2 < len(args):
            auth.login(args[idx + 1], args[idx + 2])
        else:
            print("[✗] --login 需要 用户名 密码")
        sys.exit(0)

    if "--register" in args:
        idx = args.index("--register")
        if idx + 2 < len(args):
            inv = args[idx + 3] if idx + 3 < len(args) else ""
            auth.register(args[idx + 1], args[idx + 2], inv)
        else:
            print("[✗] --register 需要 用户名 密码 [邀请码]")
        sys.exit(0)

    if "--regen" in args:
        engine.regen_all_jsons()
        sys.exit(0)

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    # 排行榜模式
    if "-av" in args:
        if not auth.ensure_login(interactive=True):
            print("[✗] 无法登录，退出")
            sys.exit(1)
        runner.run_ranking()
        sys.exit(0)

    # 批量模式（-1 或 --list）
    if len(args) >= 2 and args[0] in ("-1", "--list"):
        list_path = args[1]
        pages = int(args[2]) if len(args) >= 3 and args[2].isdigit() else None
        if not auth.ensure_login(interactive=False):
            print("[✗] 无法登录，退出")
            sys.exit(1)
        runner.run_batch(list_path, pages)
        sys.exit(0)
    elif len(args) >= 1 and args[0] in ("-1", "--list"):
        print("[✗] 请提供列表文件路径")
        sys.exit(1)

    # 单女优模式
    if len(args) >= 1 and not args[0].startswith("-"):
        name = args[0]
        pages = int(args[1]) if len(args) >= 2 and args[1].isdigit() else None
        config.page_video = pages
        if not auth.ensure_login(interactive=True):
            print("[✗] 无法登录，退出")
            sys.exit(1)
        runner.run_single(name, pages)
        sys.exit(0)

    # 全站模式（无参数）
    if not auth.ensure_login(interactive=False):
        print("[✗] 无法登录，退出")
        sys.exit(1)
    runner.run_all()


if __name__ == "__main__":
    main()