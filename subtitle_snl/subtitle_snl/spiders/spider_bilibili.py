from __future__ import absolute_import

import scrapy
from pyquery import PyQuery as pq
from ..items import ProxyItem
from ..items import BilibiliVideoItem
import re
import json
from selenium import webdriver


class ProxySpider(scrapy.Spider):
    name = 'proxy'

    def start_requests(self):
        xici_proxy_base = 'https://www.xicidaili.com/nn/'

        for i in range(1, 11):
            # xici_proxy_url = xici_proxy_base+str(i)
            ip_net_url = f'http://www.ip3366.net/?stype=1&page={i}'
            # print(xici_https_url)
            # yield scrapy.Request(url=xici_proxy_url, meta={'size': i}, callback=self.parse, dont_filter=False)
            yield scrapy.Request(url=ip_net_url, meta={'url_index': i}, callback=self.parse, dont_filter=False)
            print(f'循环第{i}次')

    def parse(self, response):
        # page_encoding = response.encoding     utf-8
        proxy_page = response.text
        proxy_doc = pq(proxy_page)
        # ip_list = proxy_doc('#ip_list tr:gt(0)')
        ip_list = proxy_doc('tbody tr')
        for ip_item in ip_list.items('tr'):
            item = ProxyItem()
            # print(f"*****what it is:{ip_item.children('td').eq(2).text()}")     #caution:直接find是从1开始，eq()则会从0开始
            # item['ip'] = ip_item.find('td:nth-child(2)').text()
            item['ip'] = ip_item.find('td:nth-child(1)').text()
            # item['port'] = ip_item.find('td:nth-child(3)').text()
            item['port'] = ip_item.find('td:nth-child(2)').text()
            # item['location'] = ip_item.find('td:nth-child(4)').text()
            item['location'] = ip_item.find('td:nth-child(6)').text()
            # item['type'] = ip_item.find('td:nth-child(5)').text()
            item['type'] = ip_item.find('td:nth-child(3)').text()
            # item['kind'] = ip_item.find('td:nth-child(6)').text()
            item['kind'] = ip_item.find('td:nth-child(4)').text()
            print(f"*****ip:{item['ip']},port:{item['port']},location:{item['location']},type:{item['type']}")
            yield item


class BilibiliSpider(scrapy.Spider):
    name = 'bilibili_search'

    def __init__(self):
        print('bilibili crawl begin')

    def start_requests(self):
        first_url = 'https://search.bilibili.com/all?keyword=snl%20%20cc%E5%AD%97%E5%B9%95'
        yield scrapy.Request(url=first_url, callback=self.parse)

    def parse(self, response):
        bilibili_video_set_page = response.text
        bilibili_video_set_doc = pq(bilibili_video_set_page)
        video_list = bilibili_video_set_doc('.video-list')
        for video_item in video_list.items('li'):
            title = video_item.children('a').attr('title')
            if re.search('【[a-zA-Z0-9\u4E00-\u9FA5]*(SNL|snl)[a-zA-Z0-9\u4E00-\u9FA5]*】', title) is None:
                continue
            else:
                bv_item = BilibiliVideoItem()
                bv_item['title'] = title
                video_url = video_item.children('a').attr('href')
                bvid = re.search('video/(BV.{10})\\??', video_url).group(1)
                video_url_new = f"https://www.bilibili.com/video/{bvid}"
                bv_item['bvid'] = bvid
                bv_item['video_url'] = video_url_new
                video_info_url = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}"
                yield scrapy.Request(url=video_info_url, meta={'item': bv_item}, callback=self.parse2)

    def parse2(self, response):
        bv_item = response.meta['item']  # item对象中获得bv_id
        bvid = bv_item['bvid']
        video_data = response.text  # 回来的是一个HtmlResponse尝试拿request_url(记录response中的内容)
        dict_video_data = json.loads(video_data)
        cid = dict_video_data['data'][0]['cid']
        bv_item['cid'] = cid
        ask_for_subtitle_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}&cid={cid}"
        print(f"new request_url is :{ask_for_subtitle_url}")
        yield scrapy.Request(url=ask_for_subtitle_url, meta={'item': bv_item}, callback=self.get_subtitle_url)

    def get_subtitle_url(self, response):
        bv_item = response.meta['item']  # item对象中获得bv_id
        resp_data = json.loads(response.text)
        try:
            subtitle_url = resp_data['data']['subtitle']['list'][0]['subtitle_url']
            bv_item['subtitle_url'] = subtitle_url
            yield scrapy.Request(url=subtitle_url, meta={'item': bv_item}, callback=self.get_and_save_subtitle)     # caution:这是http请求
        except Exception as e:
            print("该视频无CC字幕")

    def get_and_save_subtitle(self, response):
        bv_item = response.meta['item']  # item对象中获得bv_id
        bvid = bv_item['bvid']
        try:
            correct_name = re.search('\d+\.[\u4e00-\u9fa5]+', bv_item['title']).group(1)     # 可用其它方式自拟标题
        except AttributeError as e:
            correct_name = bvid
        resp_text = response.text
        subtitle_data = json.loads(resp_text)
        subtitle_body = subtitle_data['body']
        fw = open(f'../../subtitle/subtitle_Blender/subtitle_{correct_name}.txt', 'a+', encoding='utf-8')
        str_u = '\n'
        for dio in subtitle_body:
            msg = f"from {dio['from']} to {dio['to']}:{dio['content'].replace(str_u,' ')} \n"
            print(msg)
            fw.writelines(msg)
        path = fw.name
        fw.close()
        # 还需要把路径存到数据库中
        bv_item['subtitle_local_url'] = path
        yield bv_item

    def closed(self, spider):
        print(f'spider {spider} closed')

