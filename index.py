# -*- codeing: UTF-8 _*_

import sys
import os
import re
import pickle
import time
from urllib import parse
from urllib import request
#from config import config
from html.parser import HTMLParser
from random import random

# 标签页html
tagHtmlSrc = ''
# 正则-提取分类
extractCategory = re.compile(r'[\s\·\n]+')
# 正则-提取标签
extractTag = re.compile(r'[(\d)\s\n]+')
# tag_list
tagList = []
# User-Agent列表，随机使用不同的浏览器头跳过反爬虫机制
UserAgents = [
  'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6',
  'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.12 Safari/535.11',
  'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)'
]
# 请求分类接口
with request.urlopen('https://book.douban.com/tag/?view=type&icn=index-sorttags-all') as dbTag:
  data = dbTag.read()
  tagHtmlSrc = data.decode('utf-8')

# 请求书单列表
def getBook(tag, start):
  data = ''
  req = request.Request('https://book.douban.com/tag/%s?start=%s&type=T' % (parse.quote(tag), str(start)))
  # 添加请求头
  req.add_header('User-Agent', UserAgents[start % len(UserAgents)])

  with request.urlopen(req) as bookList:
    data = bookList.read().decode('utf-8')
  return data

# 解析tag页
class MyTagHTMLParser(HTMLParser):
  title_text = False
  td_text = False

  def __init__(self, *, convert_charrefs=True):
    HTMLParser.__init__(self)
    self.category = {}

  def handle_starttag(self, tag, attr):
    # 是否开始解析大分类
    if tag == 'a' and len(attr) >= 2 and attr[1][1] == 'tag-title-wrapper':
      self.title_text = True
    # 是否开始解析标签
    if tag == 'td' and len(self.category) > 0:
      self.td_text = True

  def handle_endtag(self, tag):
    # 停止解析
    if tag == 'a':
      self.title_text = False
    
    if tag == 'td':
      self.td_text = False

  def handle_data(self, data):

    if self.title_text and not re.sub(extractCategory, '', data) == '':
      # 添加分类
      self.category[re.sub(extractCategory, '', data)] = []

    if self.td_text and not re.sub(extractTag, '', data) == '':
      # 分类添加标签
      key = list(self.category.keys())[-1]
      self.category[key].append(re.sub(extractTag, '', data))

# 解析书单
class MyBookHTMLParser(HTMLParser):

  def __init__(self, *, convert_charrefs=True):
    HTMLParser.__init__(self)
    self.cutItem = False
  
  def handle_starttag(self, tag, attrs):
    pass
  
  def handle_endtag(self, tag):
    pass
  
  def handle_data(self, data):
    pass

# 爬虫主体
def bookSpider(category, tag):
  # 页码
  pageNum = 0

  def crawing(num):
    parserBook = MyBookHTMLParser()

    parserBook.feed(getBook(tag, num))

    parserBook.close()
    print(getBook(tag,num))
    #延时
    time.sleep(random() * 5)
    # 是否切换条例
    if parserBook.cutItem:
      num = num + 20
      crawing()
    else:
      return
  
  crawing(pageNum)
  return


# 开始爬取
def startSpider():
  for x in tagList:
    for n in tagList[x]:
      bookSpider(x, n)

if __name__ == '__main__':

  parserTag = MyTagHTMLParser()

  parserTag.feed(tagHtmlSrc)

  parserTag.close()

  tagList = parserTag.category

  startSpider()




