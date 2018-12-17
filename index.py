# -*- codeing: UTF-8 _*_

import sys
import os
import re
import pickle
import time
import json
import urllib
import socket
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
# 正则-移除空格回车换行
formatNull = re.compile(r'[\s\n\r]+')
# tag_list
tagList = []
# 爬取结果， 仅存储单个标签的内容，防止内存占用过大
results = []
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
  try:
    with request.urlopen(req, timeout=60) as bookList:
      data = bookList.read().decode('utf-8')

  except:
    print('查询接口异常: 重新开始请求标签 %s start %s' % (tag, start))
    data = getBook(tag, start)
      

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

  # 解析标签

  def __init__(self, *, convert_charrefs=True):
    HTMLParser.__init__(self)
    self.cutItem = False
    self.item = {
      'name': ''
    }
    # 判断是否在书籍条目的范围内
    self.is_item = False
    self.itemList = []
    # 解析内容
    self.h2_text = False
    self.pub_text = False
    self.rat_text = False
    self.pl_text = False
    self.ir_text = False
  
  def handle_starttag(self, tag, attrs):

    if tag == 'li' and len(attrs) > 0 and attrs[0][1] == 'subject-item':
      self.is_item = True

    if self.is_item:

      if tag == 'img':
        self.item['imgSrc'] = attrs[1][1]

      if tag == 'h2':
        self.h2_text = True

      if len(attrs) > 0 and attrs[0][1] == 'pub':
        self.pub_text = True

      if len(attrs) > 0 and 'allstar' in attrs[0][1]:
        self.item['allStar'] = attrs[0][1][:8]

      if len(attrs) > 0 and attrs[0][1] == 'rating_nums':
        self.rat_text = True

      if len(attrs) > 0 and attrs[0][1] == 'pl':
        self.pl_text = True

      if tag == 'p':
        self.ir_text = True
      
  def handle_endtag(self, tag):
    if self.is_item:
      if tag == 'h2':
        self.h2_text = False
      if tag == 'div' and self.pub_text == True:
        self.pub_text = False
      if tag == 'span':
        self.rat_text = False
        self.pl_text = False
      if tag == 'p':
        self.ir_text = False
      if tag == 'li':
        # 还原状态
        self.is_item = False
        self.itemList.append(self.item.copy()) 
        self.item = {
          'name': ''
        }
  def handle_data(self, data):
    if re.sub(formatNull, '', data) == '没有找到符合条件的图书':
      print('开始切换标签')
      self.cutItem = True
    # 获取书名
    if self.h2_text:
      self.item['name'] = self.item['name'] + re.sub(formatNull,'',data)
    # 获取书籍信息
    if self.pub_text:
      self.item['msg'] = re.sub(formatNull,'',data)
    # 获取评分
    if self.rat_text:
      self.item['grade'] = re.sub(formatNull,'',data)
    # 获取评论人数
    if self.pl_text:
      matchList = re.findall('\d+',re.sub(formatNull,'',data))
      # 筛选评论人数
      self.item['comment_num'] = matchList[0] if (isinstance(matchList, list) and len(matchList) > 0) else 0
    # 获取简介
    if self.ir_text:
      self.item['introduction'] = re.sub(formatNull,'',data)
  
  
# 爬虫主体
def bookSpider(category, tag):
  # 页码
  pageNum = 0

  def crawing(num):
    # 开始解析
    parserBook = MyBookHTMLParser()

    parserBook.feed(getBook(tag, num))

    parserBook.close()
    # 合并进结果集
    results.extend(parserBook.itemList)

    print('%s-%s  start-%s 结束' % (category, tag, num))
    #延时
    time.sleep(int(random() * 5))
    # 是否切换条例
    if not parserBook.cutItem:
      print('开始查询下一页')
      num = num + 20
      crawing(num)
    else:
      # 结果集写入文件
      writeToJson(category, tag, json.dumps(results, ensure_ascii=False, indent=2))
      return
  
  crawing(pageNum)
  return

def writeToJson(category, tag, data):
  with open(os.path.join(os.path.abspath('.'), category + '/' + tag + '.json'), 'a', encoding = 'utf-8') as jsonFile:
    jsonFile.write(data)

# 开始爬取
def startSpider():
  # 开始位置
  if len(sys.argv) > 1:
    ARGTAG = sys.argv[1]
  else:
    ARGTAG = False
  for x in tagList:
    for n in tagList[x]:
      # 每一个新标签开始时清空结果集
      # 命名为全局变量，虽然已声明全局变量results，但是如果在这里初始化results, python会认为你创建了一个局部变量
      global results
      results = []
      if ARGTAG and ARGTAG == n:
        # 如果从某一节点开始爬取
        bookSpider(x, n)
        ARGTAG = False
      elif not ARGTAG:
        bookSpider(x, n)

if __name__ == '__main__':

  parserTag = MyTagHTMLParser()

  parserTag.feed(tagHtmlSrc)

  parserTag.close()

  tagList = parserTag.category

  startSpider()




