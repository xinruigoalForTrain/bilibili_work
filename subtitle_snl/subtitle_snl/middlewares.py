# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html

import scrapy
from scrapy import signals
from scrapy.http import HtmlResponse
from fake_useragent import UserAgent
import re
import requests
import MySQLdb as db
import traceback
import time
import json
import copy
from selenium import webdriver


class SubtitleSnlSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Response, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class RandomUserAgentMiddleWare(object):
    def __init__(self):
        self.connection = db.connect(host='127.0.0.1', port=3306, user='root', passwd='XinRuiGOAL!895', db='source', charset='utf8')
        print('connection opened')
        self.cursor = self.connection.cursor()
        self.res_temp = ''     # 递归调用最终得到的值会被前面调用的值（None）覆盖
        self.https_list = []
        self.http_list = []
        self.ua = UserAgent()

    def __del__(self):
        self.connection.close()
        print('connection closed XXX')      # 在移除中间件的时候关闭数据库连接

    def process_request(self, request, spider):
        print(f"spider name:{spider.name},spider request:{request.url}, url type is {type(request.url)}")
        fake_ua = self.ua.random
        print(f"fake-ua is :{fake_ua}")
        proxy_kind = request.url.split(':')[0].strip()
        # proxy = self.get_random_proxy(request.url, fake_ua)
        proxy = self.get_u_proxy(request.url, fake_ua)
        print(f'the proxy will be:{proxy}，kind of proxy is {type(proxy)}')
        if request.url == 'https://search.bilibili.com/all?keyword=snl%20%20cc%E5%AD%97%E5%B9%95':
            # profile = webdriver.FirefoxProfile()
            # profile.set_preference("network.proxy.type", 1)
            # profile.set_preference("network.proxy.http", proxy.split(":")[0].strip())
            # profile.set_preference("network.proxy.http_port", int(proxy.split(":")[1].strip()))
            # if proxy_kind == 'https':
            #     profile.set_preference('network.proxy.ssl', proxy.split(":")[0].strip())
            #     profile.set_preference('network.proxy.ssl', int(proxy.split(":")[1].strip()))
            chrome_opt = webdriver.ChromeOptions()
            chrome_opt.add_argument(f'user-agent={fake_ua}')
            if proxy is not None:
                chrome_opt.add_argument(f"--proxy-server={proxy}")
            chrome_opt.add_argument('blink-settings=imagesEnabled=false')     # 无图加载（可用）
            chrome_opt.add_argument('--disable-infobars')     # 禁止策略化？
            chrome_opt.add_argument('--no-sandbox')     # 解决DevToolsActivePort文件不存在导致报错？
            chrome_opt.add_argument('--incognito')     # 无痕模式
            chrome_opt.add_argument('--disable-gpu')     # 可应对部分情况下的超时
            prefs = {
                "profile.default_content_setting_values":
                    {
                        "notifications": 2
                    },
                "profile.managed_default_content_settings.images": 2
            }
            chrome_opt.add_experimental_option("prefs", prefs)  # 设置浏览器不出现通知
            chrome_opt.add_experimental_option("excludeSwitches", ['enable-automation'])     # 不太明白
            # https不受信任ssl问题
            chrome_opt.add_argument("service_args = ['–ignore - ssl - errors = true', '–ssl - protocol = TLSv1']")
            browser = webdriver.Chrome(executable_path='F:/bilibili_work/chromedriver.exe', chrome_options=chrome_opt)
            browser.implicitly_wait(25)     # 全局配置，只要一处就够了
            try:
                browser.get(url=request.url)
            except requests.exceptions.RequestException as e:
                invalid_id = proxy.split(":")[0].strip()
                invalid_port = proxy.split(":")[1].strip()
                sql_invalid = f'delete from proxy_pool where ip = "{invalid_id}" and port = {invalid_port}'
                self.cursor.execute(sql_invalid)
                print(f"Get Error:{e},proxy need change")
                browser.close()
                return request
            resp = browser.page_source
            final_resp = self.get_next_page(browser, resp)
            return HtmlResponse(url=request.url, body=final_resp, encoding='utf-8', request=request)
        else:
            request.headers['User-Agent'] = fake_ua
            if proxy is not None:
                if proxy_kind == 'https':
                    proxy_str = f'https://{proxy}'
                else:
                    proxy_str = f'http://{proxy}'
                request.meta['proxy'] = proxy_str
            else:
                print('use yours')
                request.meta['proxy'] = None     # 不加不行？
            # return scrapy.http.Response(url=request.url)

    def process_response(self, request, response, spider):
        resp_code = response.status
        if resp_code >= 300:
            print(f"{request.url} have get error({resp_code}),check your proxy")
        return response

    def process_exception(self, request, exception, spider):
        print(f"{request.url} have get error {exception},please try it again or change proxy")     # webdriver打开的页面直接在request中捕获异常并重试
        return request

    """
        直接从IP站点获取代理（即取即用）
    """
    def filling_proxies_list(self, proxies_kind):
        print('Give me five')
        if proxies_kind == 'https':
            proxy_url = 'http://http.tiqu.qingjuhe.cn/getip?num=5&type=2&pack=51687&port=11&lb=1&pb=4&regions='
        else:
            proxy_url = 'http://http.tiqu.qingjuhe.cn/getip?num=5&type=2&pack=51687&port=1&lb=1&pb=4&regions='
        resp = requests.get(proxy_url)
        proxy_data = json.loads(resp.text)
        proxies_list = proxy_data['data']
        return proxies_list

    def get_u_proxy(self, url, fake_ua):
        proxies_kind = url.split(':')[0].strip()
        proxies_list = []     # 不能在此处进行任何优先赋值
        if proxies_kind == 'https':
            proxies_list = self.https_list     # 从全局变量中读取最好直接赋值（浅拷贝）
        else:
            proxies_list = self.http_list
        print(f'{len(proxies_list)} proxies are wait in line')
        if len(proxies_list) == 0:
            proxies_list = self.filling_proxies_list(proxies_kind)
            if proxies_kind == 'http':
                self.http_list = copy.deepcopy(proxies_list)     # 生成新的代理列表交还给全局变量时必须用深拷贝
            else:
                self.https_list = copy.deepcopy(proxies_list)
        pre_proxy = proxies_list[0]
        ip_n = pre_proxy['ip']
        port_n = pre_proxy['port']
        # u_proxy = {'https': f'https://{ip_n}:{port_n}'}
        u_proxy = self.check_ip_valid(ip_n, port_n, proxies_kind, url, fake_ua)
        if not u_proxy:
            proxies_list.pop(0)     # 前方使用浅拷贝，则此处可直接从现存列表中移除
            print(f"{pre_proxy} pop from proxies_list")
            self.get_u_proxy(url, fake_ua)
        else:
            self.res_temp = u_proxy
        u_proxy = self.res_temp
        return u_proxy

    """
        从数据库中维护的IP池获取代理
    """
    def get_random_proxy(self, url, fake_ua):
        proxy_kind = url.split(':')[0].strip()
        # sql = f'select id,ip,port from proxy_pool where `type` = "1" and kind = "{proxy_kind}" order by `status` desc ,rand() limit 1'
        # 实际工作中请勿对status排序（或取得更多有效代理时可以）
        sql = f'select id,ip,port from proxy_pool where `type` = "1" and kind = "{proxy_kind}" order by rand() limit 1'
        self.cursor.execute(sql)
        ip_info = self.cursor.fetchone()
        print(f'imagine result:{ip_info}')
        if ip_info is None:
            # 防止没有查到的时候（返回结果为一个空的元组，但打印出来是None），连接无法关闭，数据也不会真的删除
            self.connection.commit()
            print('所有代理均已阵亡，请及时补充，proxy change commit')     # 统一在拿到返回后关闭连接
            return None
        ip = ip_info[1]
        port = ip_info[2]
        res = self.check_ip_valid(ip, port, proxy_kind, url, fake_ua)
        if not res:
            sql_del_ip = f'delete from proxy_pool where id = {ip_info[0]}'
            self.cursor.execute(sql_del_ip)
            print(f'invalid Ip {ip_info[0]} have deleted')
            self.get_random_proxy(url, fake_ua)
        else:
            try:
                # print(f'the effective proxy is {res},id = {ip_info[0]} ')
                sql_effective = f'update proxy_pool set `status` = 1 where id = {ip_info[0]}'
                self.cursor.execute(sql_effective)
                self.connection.commit()
                print('proxy change commit 2')
                self.res_temp = res
            except Exception as ex:
                traceback.print_exc()
        # print(f"final-proxy is :{res}")
        res = self.res_temp
        return res

    """
        检验代理是否有效
    """
    def check_ip_valid(self, ip, port, proxy_kind, url, fake_ua):
        domain = re.search('https?://[^/]*/', url).group()     # 需要验证的地址(只验证主站)
        print(f'main site is:{domain}')
        headers = {'user-agent':fake_ua}
        proxy_dict = {'http': f"http://{ip}:{port}"}
        if proxy_kind == "https":
            proxy_dict = {'https': f"https://{ip}:{port}"}
        retry_times = 0
        while True:
            try:
                resp = requests.get(domain, proxies=proxy_dict, headers=headers, timeout=(10, 25), stream=True)
            except Exception as e:
                if retry_times > 5:
                    return None
                else:
                    retry_times += 1
            else:
                code = resp.status_code
                if int(code) < 400:     # 部分请求可能遇到重定向
                    # print('Get it')
                    break
                else:
                    print(f"err_code:{code}")
                    return None
        print(f'{proxy_dict} is effective,oh yeah~')
        return f"{ip}:{port}"

    def get_next_page(self, browser, page_html):
        has_next_page = True
        this_page_html = page_html
        while has_next_page:
            time.sleep(5)     # 确认页面加载完成后翻页可删除
            try:
                # btn_next_page = browser.find_element_by_class_name('icon-arrowdown3')     无效，不理解
                # btn_next_page.click()
                js = 'var next_page_btn = document.getElementsByClassName("icon-arrowdown3")[0].click()'
                print('crawl next page,Go!')
                browser.execute_script(js)
                next_page_source = browser.page_source
                page_html += next_page_source
                this_page_html = next_page_source
            except Exception as ex:
                print('no next page more')
                has_next_page = False
        return page_html


class SubtitleSnlDownloaderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
