# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import pymongo
from jdproject.items import GoodsListItem, DetailGoodItem


class JdspiderPipeline():
    """
    数据存储
    """
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DB')
        )

    def open_spider(self, spider):
        """
        启动爬虫
        :param spider: 京东爬虫
        :return:
        """
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.db[GoodsListItem.collection].create_index([('sku', pymongo.ASCENDING)])
        self.db[DetailGoodItem.collection].create_index([('sku', pymongo.ASCENDING)])

    def close_spider(self, spider):
        """
        关闭爬虫
        :param spider:
        :return:
        """
        self.client.close()

    def process_item(self, item, spider):
        """
        存储数据
        :param item: 解析的数据
        :param spider: 京东爬虫
        :return: 解析的数据
        """
        self.db[item.collection].update_many({'sku': item.get('sku')}, {'$set': item}, True)
        return item
