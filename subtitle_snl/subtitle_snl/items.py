# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ProxyItem(scrapy.Item):
    # define the fields for your item here like:
    ip = scrapy.Field()
    port = scrapy.Field()
    location = scrapy.Field()
    type = scrapy.Field()
    kind = scrapy.Field()


class BilibiliVideoItem(scrapy.Item):
    bvid = scrapy.Field()
    cid = scrapy.Field()
    title = scrapy.Field()
    video_url = scrapy.Field()
    subtitle_url = scrapy.Field()
    subtitle_local_url = scrapy.Field()
