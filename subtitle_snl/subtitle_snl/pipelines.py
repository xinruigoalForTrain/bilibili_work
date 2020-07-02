# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import MySQLdb as db


class SubtitleSnlPipeline(object):
    def __init__(self):
        self.connection = db.connect(host='127.0.0.1', user='root', passwd='XinRuiGOAL!895', db='source', charset='utf8')

    def process_item(self, item, spider):
        if spider.name == 'proxy':
            print(f'$$$$$$$$$$$$$$$$$$$$$$$$$ per option: {item["ip"]}:{item["port"]},oh yeah~')
            with self.connection.cursor() as cursor:
                sql = 'insert into proxy_pool (ip,port,location,`type`,`kind`) values(%s,%s,%s,%s,%s);'
                proxy_type = '0'     # 透明代理
                # if item['type'] == '高匿':
                if item['type'] == '高匿代理IP':
                    proxy_type = '1'
                args = (item['ip'], item['port'], item['location'], proxy_type, item['kind'])
                spider.logger.info(args)
                cursor.execute(sql, args)
                self.connection.commit()
        elif spider.name == 'bilibili_search':
            print(f"save video info:{item['title']}")
            bv_id = item["bvid"]
            title = item["title"]
            video_url = item["video_url"]
            cid = item['cid']
            subtitle_url = item['subtitle_url']
            subtitle_local_url = item['subtitle_local_url']
            with self.connection.cursor() as cursor:
                sql = f'insert into bilibili_video (cid,bvid,title,video_url,subtitle_url,subtitle_local_url) ' \
                    f'values ("{cid}", "{bv_id}", "{title}", "{video_url}", "{subtitle_url}", "{subtitle_local_url}")'
                cursor.execute(sql)
                self.connection.commit()

    def close_spider(self, spider):
        self.connection.close()
        print("spider closed,and connection closed here")
