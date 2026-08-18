#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 4KPorno FongMi硬编码测试版 v27
# 完全不依赖网络，用于排查FongMi兼容性问题

import sys
import re
import json

class Spider:
    def __init__(self):
        pass

    def init(self, extend=""):
        return True

    def homeContent(self, filter=False):
        # 硬编码返回分类，不依赖任何网络请求
        classes = [
            {"type_name": "\u6700\u65b0\u66f4\u65b0", "type_id": "latest"},
            {"type_name": "\u6700\u9ad8\u8bc4\u5206", "type_id": "top"},
            {"type_name": "\u6700\u53d7\u6b22\u8fce", "type_id": "popular"},
            {"type_name": "\u4e9a\u6d32\u7684", "type_id": "asian"},
            {"type_name": "\u5927\u5c41\u80a1", "type_id": "big-ass"},
            {"type_name": "\u5927\u5976", "type_id": "big-tits"},
        ]
        return {"class": classes, "filters": {}}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        # 硬编码返回视频列表
        videos = [
            {"vod_id": "test1", "vod_name": "\u6d4b\u8bd5\u89c6\u98911", "vod_pic": "", "vod_remarks": "HD"},
            {"vod_id": "test2", "vod_name": "\u6d4b\u8bd5\u89c6\u98912", "vod_pic": "", "vod_remarks": "4K"},
            {"vod_id": "test3", "vod_name": "\u6d4b\u8bd5\u89c6\u98913", "vod_pic": "", "vod_remarks": "1080P"},
        ]
        return {
            "list": videos,
            "page": 1,
            "pagecount": 1,
            "limit": 3,
            "total": 3,
        }

    def detailContent(self, ids):
        return {
            "list": [{
                "vod_id": "test1",
                "vod_name": "\u6d4b\u8bd5\u89c6\u9891",
                "vod_pic": "",
                "vod_content": "\u8fd9\u662f\u6d4b\u8bd5\u5185\u5bb9",
                "vod_play_from": "4KPorno",
                "vod_play_url": "\u6b63\u7247$https://www.4kporno.xxx",
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "url": "https://www.4kporno.xxx",
            "header": "",
        }

    def searchContent(self, key, quick, pg="1"):
        return self.categoryContent(tid="search", pg=pg, filter=False, extend="")

    def localProxy(self, param):
        return [200, "text/plain", ""]

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False
