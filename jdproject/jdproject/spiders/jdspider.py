# -*- coding: utf-8 -*-
import json
import re
import time
from copy import deepcopy
from urllib.parse import quote

from retrying import retry
from scrapy import Request, Spider
from jdproject.items import GoodsListItem, DetailGoodItem


class JdSpider(Spider):
    """
    京东爬虫
    """
    name = 'jdspider'
    allowed_domains = ['jd.com', 'dc.3.cn']
    start_urls = ['https://dc.3.cn/category/get']

    def parse(self, response):
        """
        解析首页函数
        :param response: 返回的是第一分类数据，第二分类数据，第三分类数据
        :return: 请求第三分类商品列表
        """
        result = response.body.decode('gbk')
        # result = re.findall(r'getCategoryCallback.*?formatted\((.*)\)', str(response.body.decode('gbk')))[0]
        all_data = json.loads(result)['data']
        item = GoodsListItem()
        for data in all_data:
            # print('全部数据分组', all)
            if data['s']:
                for first in data['s']:
                    # print(first)
                    # 第一分类数据
                    first_data = first['n'].split('|')
                    item['first_name'] = [f for f in first_data if f][-2]
                    item['first_url'] = 'https://' + [f for f in first_data if f][0]
                    if first['s']:
                        for second in first['s']:
                            # 第二分类数据
                            second_name_str = second['n'].split('|')
                            item['second_name'] = [s for s in second_name_str if s][-2]
                            if second['s']:
                                for third in second['s']:
                                    # 第三分类数据
                                    third_data = third['n'].split('|')
                                    item['third_name'] = [t for t in third_data if t][-2]
                                    if re.findall(r'\d+-\d+-\d+', third_data[0]):
                                        item['goods_num'] = third_data[0].replace('-', ',')
                                        item['third_url'] = 'https://list.jd.com/list.html?cat=' + item['goods_num']
                                    elif 'jd.com' in third_data[0]:
                                        item['goods_num'] = re.findall(r'(\d+,\d+,\d+)', third_data[0])
                                        item['third_url'] = 'https://' + third_data[0]
                                    else:
                                        continue
                                    # print(item)
                                    yield Request(
                                        item['third_url'],
                                        callback=self.parse_page,
                                        meta={'item': deepcopy(item)},
                                    )

    @retry(stop_max_attempt_number=3)
    def parse_page(self, response):
        """
        解析页面数量函数
        :param response: 获得商品列表页面内容
        :return:请求详情页面地址
        """
        item = response.meta.get('item')
        num = item['goods_num']
        page = re.findall(r's.init\(\d+.*?(\d+),', response.text, re.S)
        page = int(page[0]) if page else 2
        max_page = int(page / 2) + 1 if not page % 2 else page // 2 + 2
        # print(max_page)
        for i in range(1, max_page):
            if i % 2 == 0:
                detail_url = 'https://list.jd.com/listNew.php?cat=' + quote(str(num)) + \
                             '&page={page}&s={s}&scrolling=y&log_id={time_str:.4f}&tpl=3_M&isList=1'.format(
                                 page=i, s=(i - 1) * 26, time_str=time.time()
                             )
            else:
                detail_url = 'https://list.jd.com/list.html?cat=' + quote(str(num)) + \
                             '&page={page}&s={s}&click=0'.format(page=i, s=(i - 1) * 26)
            yield Request(
                detail_url,
                callback=self.parse_detail,
                meta={'item': deepcopy(item)}
            )

    @retry(stop_max_attempt_number=3)
    def parse_detail(self, response):
        """
        解析商品列表页面内容函数
        :param response: 返回商品列表内容页面
        :return: 请求单个商品详情页面地址
        """
        item = response.meta.get('item')
        lis = response.xpath('//li[contains(@class, "gl-item")]')
        for li in lis:
            item['sku'] = li.xpath('./@data-sku').extract_first()
            item['image'] = response.urljoin(li.xpath('.//div[class="p-img"]//img/@src').extract_first())
            item['title'] = li.xpath('.//div[contains(@class, "p-name")]/a/em/text()').extract_first().strip()
            item['attribute'] = li.xpath('.//span[@class="p-attribute"]//text()').extract()
            item['price'] = li.xpath('.//div[@class="p-price"]//i/text()').extract_first()
            item['score'] = li.xpath('.//span[@class="buy-score"]/em/text()').extract_first()
            item['shop'] = li.xpath('.//a[contains(@class, "curr-shop")]/text()').extract_first()
            item['icons'] = li.xpath('.//div[@class="p-icons"]//text()').extract()
            goods_url = response.urljoin(li.xpath('.//div[@class="p-img"]/a/@href').extract_first())
            self.parse_data(item)
            yield item
            yield Request(
                goods_url,
                callback=self.parse_goods,
                meta={"item": deepcopy(item)}
            )

    @retry(stop_max_attempt_number=3)
    def parse_goods(self, response):
        """
        解析单个商品内部详情函数
        :param response: 单个商品详情函数
        :return: 请求评论页面地址
        """
        # item = response.meta.get('item')
        detail_item = DetailGoodItem()
        sku_data = response.xpath('//ul[contains(@class, "parameter2")]//li/text()').extract()
        sku = [x for x in sku_data if x and re.findall(r'商品编号：(.*?)', x) or re.findall(r'商品编码：(\d+)', x)]
        # 先判断是否存在，然后如果存在并且是列表格式，取第一个内容，然后把商品编码：几个字去掉
        detail_item['sku'] = sku[0][5:] if sku and isinstance(sku, list) else ''
        detail = response.xpath('//div[@class="p-parameter-list"]')
        detail_list = []
        if detail:
            for d in detail:
                data = dict()
                data['first'] = d.xpath('./h3/text()')[0]
                data['second'] = {}
                clearfixs = d.xpath('.//dl[@class="clearfix"]')
                if clearfixs:
                    for c in clearfixs:
                        key = c.xpath('./dt/text()')[0]
                        data['second'][key] = c.xpath('./dd[last()]/text()')[0]
                    detail_list.append(data)
                detail_item['data'] = detail_list
        yield detail_item
        comment_url = 'https://club.jd.com/comment/productPageComments.action?productId={sku}&score=0&sortType=5&page=0&pageSize=10'.format(sku=detail_item['sku'])
        yield Request(
            comment_url,
            callback=self.parse_comment,
            meta={'detail_item': deepcopy(detail_item)}
        )

    @retry(stop_max_attempt_number=3)
    def parse_comment(self, response):
        """
        解析评论内容页面
        :param response:评论内容页面
        :return: 返回单个商品的所有内容及请求翻页地址
        """
        detail_item = response.meta.get('detail_item')
        if response.text:
            good_data = json.loads(response.text)
            detail_item['commentCount'] = good_data['productCommentSummary']['commentCount']
            page_num = good_data['maxPage'] + 1
            detail_item['goodCount'] = good_data['productCommentSummary']['goodCount']
            detail_item['generalCount'] = good_data['productCommentSummary']['generalCount']
            detail_item['poorCount'] = good_data['productCommentSummary']['poorCount']
            detail_item['productId'] = good_data['productCommentSummary']['productId']
            goodRate = good_data['productCommentSummary']['goodRate']
            detail_item['goodRate'] = '{:.0%}'.format(goodRate)
            comments = []
            if good_data['comments']:
                for c in good_data['comments']:
                    comments.append(c['content'])
                detail_item['comments'] = comments
                yield detail_item
            next_url = 'https://club.jd.com/comment/productPageComments.action?productId={sku}&score=0&sortType=5&page={page}&pageSize=10'.format(
                sku=detail_item['productId'],
                page=page_num
            )
            yield Request(
                next_url,
                callback=self.parse_comment,

            )

    def parse_data(self, data):
        """
        处理异常数据函数
        :param data: 第一分类，第二分类，第三分类及商品列表数据
        :return: 返回处理之后的数据
        """
        attribute_str = data['attribute']
        attribute = [x.strip() for x in attribute_str if attribute_str]
        data['attribute'] = ','.join([x for x in attribute if x])
        icons_str = data['icons']
        icons = [x.strip() for x in icons_str if icons_str]
        data['icons'] = ','.join([x for x in icons if x])
        return data
