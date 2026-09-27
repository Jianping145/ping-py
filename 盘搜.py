# -*- coding: utf-8 -*-
"""
盘搜-海报13 (PeekPro版)
首页: TMDB weekly trending 电影/剧集海报
详情: TMDB详细信息 + 自动在详情页搜索盘搜网盘资源（详情页内完成搜索）
搜索: 支持顶部搜索框手动搜索盘搜网盘资源
"""
import sys, json, time, base64, re, hashlib
import requests
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.append('..')
from base.spider import Spider

TMDB_IMG = "https://image.tmdb.org/t/p/w500"
TMDB_API = "https://api.themoviedb.org/3"
DF_API_KEY = "tmdbkey"

# 盘类型中文名映射
PAN_NAME_MAP = {
    "quark": "夸克网盘", "115": "115网盘", "aliyun": "阿里云盘",
    "baidu": "百度网盘", "uc": "UC网盘", "tianyi": "天翼云盘",
    "xunlei": "迅雷云盘", "123": "123云盘", "mobile": "移动云盘",
    "pikpak": "PikPak", "magnet": "磁力链接", "ed2k": "电驴",
    "ali": "阿里云盘", "a115": "115网盘", "a123": "123云盘", "guangya": "光鸭"
}
# 盘排序优先级
PAN_ORDER = ["夸克网盘", "115网盘", "阿里云盘", "百度网盘", "UC网盘",
             "迅雷云盘", "123云盘", "天翼云盘", "磁力链接"]


class PanSouSpider(Spider):

    def __init__(self):
        super().__init__()
        self.base_url = "https://so.252035.xyz"
        self.tmdb_key = DF_API_KEY
        self.tmdb_lang = "zh-CN"
        self.proxy = ""
        self.src = "all"
        self.cloud_types = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Content-Type": "application/json"
        })
        retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def init(self, ext):
        try:
            cfg = {}
            if ext:
                if isinstance(ext, dict):
                    cfg = ext
                elif isinstance(ext, str):
                    cfg = json.loads(ext)
            self.base_url = (cfg.get("server") or cfg.get("api") or self.base_url).rstrip("/")
            self.tmdb_key = cfg.get("tmdb_api_key") or cfg.get("tmdb_key") or self.tmdb_key
            self.tmdb_lang = cfg.get("tmdb_language") or self.tmdb_lang
            self.proxy = cfg.get("proxy", "")
            self.src = cfg.get("src", "all")
            self.cloud_types = cfg.get("cloud_types") or []
            if self.proxy:
                self.session.proxies = {"http": self.proxy, "https": self.proxy}
        except:
            pass

    def getName(self):
        return "PanSou"
    def isVideoFormat(self, url):
        return False
    def manualVideoCheck(self):
        return False

    # ========== TMDB 工具 ==========
    def _tmdb_get(self, path, params=None):
        p = {"api_key": self.tmdb_key, "language": self.tmdb_lang}
        if params: p.update(params)
        try:
            r = self.session.get(TMDB_API + path, params=p, timeout=12)
            r.raise_for_status()
            return r.json()
        except:
            return None

    def _tmdb_img(self, path):
        if not path: return ""
        return TMDB_IMG + path if not path.startswith("http") else path

    def _tmdb_trending(self, mtype="movie", page=1):
        return self._tmdb_get(f"/trending/{mtype}/week", {"page": page})

    def _tmdb_detail(self, mtype, tid):
        return self._tmdb_get(f"/{mtype}/{tid}", {"append_to_response": "credits"})

    def _tmdb_search_multi(self, q):
        return self._tmdb_get("/search/multi", {"query": q, "page": 1})

    def _get_pan_name(self, api_type):
        if api_type in PAN_NAME_MAP:
            return PAN_NAME_MAP[api_type]
        for v in PAN_NAME_MAP.values():
            if v == api_type:
                return v
        simple = {"ali": "阿里云盘", "a115": "115网盘", "a123": "123云盘",
                   "quark": "夸克网盘", "baidu": "百度网盘", "uc": "UC网盘",
                   "xunlei": "迅雷云盘", "tianyi": "天翼云盘", "mobile": "移动云盘",
                   "115": "115网盘", "123": "123云盘", "aliyun": "阿里云盘"}
        if api_type in simple:
            return simple[api_type]
        return api_type or "网盘"

    # ========== 首页 ==========
    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "tmdb_movie", "type_name": "🔥 热门电影"},
                {"type_id": "tmdb_tv", "type_name": "🔥 热门剧集"},
                {"type_id": "tmdb_movie_hot", "type_name": "🎬 热映"},
                {"type_id": "search_page", "type_name": "🔍 网盘搜资源"}
            ],
            "list": []
        }

    def homeVideoContent(self):
        try:
            data = self._tmdb_trending("movie", 1)
            if data and data.get("results"):
                items = data["results"][:18]
                lst = []
                for it in items:
                    tid = it.get("id")
                    title = it.get("title") or ""
                    poster = self._tmdb_img(it.get("poster_path"))
                    date = it.get("release_date") or ""
                    year = date[:4] if len(date) >= 4 else ""
                    rating = str(round(it.get("vote_average", 0), 1))
                    lst.append({
                        "vod_id": f"tmdb_m_{tid}",
                        "vod_name": title,
                        "vod_pic": poster,
                        "vod_remarks": f"{year} ⭐{rating}"
                    })
                return {"list": lst}
        except:
            pass
        return {"list": []}

    # ========== 分类页 ==========
    def categoryContent(self, cid, page, filter, ext):
        try:
            pg = int(page) if page else 1
        except:
            pg = 1

        if cid == "tmdb_movie":
            mtype, data = "movie", self._tmdb_trending("movie", pg)
        elif cid == "tmdb_tv":
            mtype, data = "tv", self._tmdb_trending("tv", pg)
        elif cid == "tmdb_movie_hot":
            mtype, data = "movie", self._tmdb_get("/movie/now_playing", {"page": pg, "region": "CN"})
        elif cid == "search_page":
            return {
                "list": [{"vod_id": "tips", "vod_name": "请使用顶部搜索功能搜索资源", "vod_pic": ""}],
                "page": 1, "pagecount": 1, "limit": 1, "total": 1
            }
        else:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

        if data and data.get("results"):
            tp = data.get("total_pages", 1)
            lst = []
            prefix = "tmdb_m" if mtype == "movie" else "tmdb_tv"
            for it in data["results"]:
                tid = it.get("id")
                title = it.get("title") or it.get("name") or ""
                poster = self._tmdb_img(it.get("poster_path"))
                date = it.get("release_date") or it.get("first_air_date") or ""
                year = date[:4] if len(date) >= 4 else ""
                rating = str(round(it.get("vote_average", 0), 1))
                lst.append({
                    "vod_id": f"{prefix}_{tid}",
                    "vod_name": title,
                    "vod_pic": poster,
                    "vod_remarks": f"{year} ⭐{rating}"
                })
            return {"list": lst, "page": pg, "pagecount": tp, "limit": 20,
                    "total": data.get("total_results", 0)}
        return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

    # ========== 搜索 ==========
    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, kw, ps):
        try:
            pg = int(ps) if ps else 1
        except:
            pg = 1
        res = {"list": [], "page": pg, "pagecount": 1, "limit": 40, "total": 0}
        if not kw: return res
        try:
            items = self._pan_request(kw)
            total = len(items)
            start = (pg - 1) * 40
            end = start + 40
            page_items = items[start:end]
            lst = [self._build_pan_item(it, kw) for it in page_items]
            res.update({"list": lst, "total": total,
                        "pagecount": max(1, (total + 39) // 40)})
        except:
            pass
        return res

    # ========== PanSou API ==========
    def _pan_request(self, kw):
        try:
            url = self.base_url + "/api/search"
            params = {"kw": kw, "res": "merge", "src": self.src}
            if self.cloud_types:
                params["cloud_types"] = ",".join(self.cloud_types)
            r = self.session.get(url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
        except:
            return []
        items = []
        if isinstance(data.get("data"), dict):
            merged = data["data"].get("merged_by_type", {}) or {}
        else:
            merged = data.get("merged_by_type", {}) or {}
        if not isinstance(merged, dict):
            return items
        for atype, links in merged.items():
            if not isinstance(links, list):
                continue
            pname = self._get_pan_name(atype)
            for ln in links:
                if not isinstance(ln, dict):
                    continue
                url = ln.get("url") or ""
                if not url:
                    continue
                items.append({
                    "api_type": atype,
                    "pan_name": pname,
                    "url": url,
                    "password": ln.get("password") or "",
                    "note": ln.get("note") or kw,
                    "datetime": ln.get("datetime") or "",
                    "source": ln.get("source") or ""
                })
        # 去重
        seen = set()
        out = []
        for it in items:
            k = f"{it['api_type']}|{it['url']}".lower().replace(" ", "")
            if k not in seen:
                seen.add(k)
                out.append(it)
        return out

    def _build_pan_item(self, it, kw):
        pname = it.get("pan_name", "网盘")
        note = it.get("note") or kw
        if len(note) > 40: note = note[:40] + "..."
        password = it.get("password", "")
        rem = [pname]
        if password: rem.append(f"码:{password}")
        return {
            "vod_id": self._b64e(it),
            "vod_name": note,
            "vod_pic": "",
            "vod_remarks": "|".join(rem)
        }

    def _b64e(self, data):
        return base64.urlsafe_b64encode(json.dumps(data, ensure_ascii=False).encode()).decode().rstrip("=")

    def _b64d(self, s):
        s = str(s) + "=" * (-len(str(s)) % 4)
        return json.loads(base64.urlsafe_b64decode(s.encode()).decode())

    # ========== 详情页：TMDB信息 + 自动盘搜（在详情页完成搜索） ==========
    def detailContent(self, did):
        res = {"list": []}
        if not did or not did[0]: return res
        vid = did[0]

        if vid.startswith("tmdb_"):
            return self._detail_tmdb(vid)

        # 普通盘搜资源（搜索结果中点击）
        try:
            it = self._b64d(vid)
        except:
            return res
        return self._detail_pan(it)

    def _parse_tmdb_vid(self, vid):
        try:
            parts = vid.split("_", 2)
            if len(parts) != 3: return None, None
            pfx = f"{parts[0]}_{parts[1]}"
            tid = parts[2]
            if pfx == "tmdb_m": return "movie", tid
            if pfx == "tmdb_tv": return "tv", tid
            return None, None
        except:
            return None, None

    def _detail_tmdb(self, vid):
        mtype, tid = self._parse_tmdb_vid(vid)
        if not mtype or not tid:
            return {"list": []}

        detail = self._tmdb_detail(mtype, tid)
        if not detail:
            return {"list": [{"vod_id": vid, "vod_name": "获取详情失败", "vod_pic": ""}]}

        title = detail.get("title") or detail.get("name") or ""
        orig = detail.get("original_title") or detail.get("original_name") or ""
        poster = self._tmdb_img(detail.get("poster_path"))
        backdrop = self._tmdb_img(detail.get("backdrop_path"))
        date = detail.get("release_date") or detail.get("first_air_date") or ""
        year = date[:4] if len(date) >= 4 else ""
        rating = str(round(detail.get("vote_average", 0), 1))
        overview = detail.get("overview") or ""

        # 时长
        runtime_str = ""
        if mtype == "movie":
            rt = detail.get("runtime", 0)
            if rt: runtime_str = f"{rt}分钟"
        else:
            eps = detail.get("number_of_episodes", 0)
            seas = detail.get("number_of_seasons", 0)
            if seas: runtime_str = f"{seas}季 {eps}集"

        # 类型
        genres = [g.get("name", "") for g in detail.get("genres", [])]
        genre_str = " / ".join(genres) if genres else ""

        # 演职人员
        credits = detail.get("credits", {})
        cast = credits.get("cast", [])[:8]
        cast_names = [c.get("name", "") for c in cast]
        cast_str = " / ".join(cast_names)
        crew = credits.get("crew", [])
        directors = [c.get("name", "") for c in crew if c.get("job") == "Director"]
        director_str = " / ".join(directors[:3])

        # TMDB信息文本
        info_lines = []
        info_lines.append(f"🎬 片名：{title}")
        if orig and orig != title: info_lines.append(f"📝 原名：{orig}")
        info_lines.append(f"📅 年份：{year}")
        info_lines.append(f"⭐ 评分：{rating}/10")
        if genre_str: info_lines.append(f"🏷️ 类型：{genre_str}")
        if runtime_str: info_lines.append(f"⏱ 时长：{runtime_str}")
        if director_str: info_lines.append(f"🎥 导演：{director_str}")
        if cast_str: info_lines.append(f"👤 主演：{cast_str}")
        if overview: info_lines.append(f"\n📖 剧情简介：\n{overview}")
        content = "\n".join(info_lines)

        if mtype == "tv":
            seasons = detail.get("seasons", [])
            if seasons:
                seas_names = [s.get("name", "") for s in seasons[:15] if s.get("name")]
                if seas_names:
                    for sn in seas_names:
                        content += f"\n📺 {sn}"

        # ===== 在详情页内自动搜索盘搜资源 =====
        play_from_list = []
        play_url_list = []

        search_kws = [title]
        if orig and orig != title:
            search_kws.append(orig)

        all_pan = []
        seen_urls = set()
        for kw in search_kws:
            try:
                items = self._pan_request(kw)
                for it in items:
                    uk = it["url"].lower().replace(" ", "")
                    if uk not in seen_urls:
                        seen_urls.add(uk)
                        all_pan.append(it)
            except:
                pass

        # 分组排序
        groups = {}
        for it in all_pan:
            pn = it["pan_name"]
            groups.setdefault(pn, []).append(it)

        ordered = []
        for pref in PAN_ORDER:
            if pref in groups:
                ordered.append(pref)
                del groups[pref]
        for pn in sorted(groups.keys()):
            ordered.append(pn)

        # 构建播放列表
        # 先放一个总入口
        total_count = len(all_pan)
        play_from_list.append("🔍盘搜资源")
        play_url_list.append(f"共{total_count}个网盘链接$pan_search_head")

        used_ids = set()
        for pn in ordered:
            its = groups.get(pn) or []
            for idx, it in enumerate(its[:12]):
                note = it.get("note") or title
                if len(note) > 25: note = note[:25] + ".."
                url = it["url"]
                pwd = it["password"]
                api_type = it["api_type"]

                final_url = url
                if pwd and api_type not in ["magnet", "ed2k"]:
                    if "?" in final_url: final_url += f"&pwd={pwd}"
                    else: final_url += f"?pwd={pwd}"

                pid_data = {"t": api_type, "u": final_url, "p": pwd}
                pid_str = self._b64e(pid_data)
                if pid_str in used_ids: continue
                used_ids.add(pid_str)

                label = pn
                if pwd: label += f"🔑{pwd}"
                display = f"[{label}] {note}"
                play_from_list.append(label)
                play_url_list.append(f"{display}${pid_str}")

        if not all_pan:
            play_from_list.append("盘搜资源")
            play_url_list.append(f"未搜到网盘资源$no_resource")
            content += "\n\n⚠️ 未搜到网盘资源，请使用搜索功能搜索完整片名"

        vod_play_from = "$$$".join(play_from_list)
        vod_play_url = "$$$".join(play_url_list)

        vod_item = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": poster or backdrop,
            "type_name": "电影" if mtype == "movie" else "剧集",
            "vod_year": year,
            "vod_area": "",
            "vod_remarks": f"⭐{rating} {year}",
            "vod_actor": cast_str,
            "vod_director": director_str,
            "vod_content": content,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }
        return {"list": [vod_item]}

    # ========== 单盘资源详情（搜索结果中点击进入） ==========
    def _detail_pan(self, it):
        res = {"list": []}
        pname = it.get("pan_name", "网盘")
        title = it.get("note", f"{pname}资源")
        url = it.get("url", "")
        pwd = it.get("password", "")
        final_url = url
        if pwd:
            if "?" in final_url: final_url += f"&pwd={pwd}"
            else: final_url += f"?pwd={pwd}"

        pid_data = {"t": it.get("api_type", ""), "u": final_url, "p": pwd}
        pid = self._b64e(pid_data)
        play_n = pname + (f" 🔑{pwd}" if pwd else "")

        content_parts = [f"资源名称：{title}", f"网盘类型：{pname}", f"链接：{url}"]
        if pwd: content_parts.append(f"提取码：{pwd}")
        if it.get("datetime"): content_parts.append(f"时间：{it['datetime']}")
        if it.get("source"): content_parts.append(f"来源：{it['source']}")

        res["list"].append({
            "vod_id": it.get("id") or self._b64e(it),
            "vod_name": title,
            "vod_pic": "",
            "type_name": pname,
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": pname,
            "vod_actor": it.get("source", ""),
            "vod_director": "PanSou",
            "vod_content": "\n".join(content_parts),
            "vod_play_from": pname,
            "vod_play_url": f"{play_n}${pid}"
        })
        return res

    # ========== 播放 ==========
    def playerContent(self, flag, pid, vipFlags):
        res = {"parse": 0, "playUrl": "", "url": "", "header": {"User-Agent": "okhttp/3.15"}}
        if not pid or pid in ["no_resource", "pan_search_head"]: return res
        try:
            data = self._b64d(pid)
            url = data.get("u", "")
            if url: res["url"] = url
        except:
            res["url"] = str(pid)
        return res

    def localProxy(self, param):
        return None


Spider = PanSouSpider
