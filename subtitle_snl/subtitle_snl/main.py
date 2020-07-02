#!/usr/bin/env python
# -*- coding:utf-8 -*-

from scrapy.cmdline import execute
import os
import sys

if __name__ == '__main__':
    # 添加当前项目的绝对地址
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    # param3为爬虫名
    # execute(['scrapy', 'crawl', 'proxy'])
    execute(['scrapy', 'crawl', 'bilibili_search'])

