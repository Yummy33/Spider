# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class GoodsListItem(Item):
    collection = 'goodslist'
    first_name = Field()
    first_url = Field()
    second_name = Field()
    third_name = Field()
    third_url = Field()
    goods_num = Field()
    sku = Field()
    image = Field()
    title = Field()
    attribute = Field()
    price = Field()
    score = Field()
    shop = Field()
    icons = Field()


class DetailGoodItem(Item):

    collection = 'detailgood'
    sku = Field()
    data = Field()
    commentCount = Field()
    goodCount = Field()
    generalCount = Field()
    poorCount = Field()
    productId = Field()
    goodRate = Field()
    comments = Field()
