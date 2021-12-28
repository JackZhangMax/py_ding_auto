#!/usr/bin/env python
# -*- coding: utf-8 -*-
import configparser
import requests
import json
from datetime import datetime, timedelta

# 读取配置
cf = configparser.ConfigParser(allow_no_value=True)
cf.read("conf.ini", 'utf-8')


class AccessToken:
    # 过期时间
    expire_time = None
    access_token = ''

    def __init__(self, __expire_time=None, __access_token=None):
        self.access_token = __access_token
        self.expire_time = __expire_time


class WeChat:
    access_token = AccessToken()

    def __init__(self):
        self.CORP_ID = cf.get('notify', 'work_wechat_corpId')  # 企业ID，在管理后台获取
        self.SECRET = cf.get('notify', 'work_wechat_secret')  # 自建应用的Secret，每个自建应用里都有单独的secret
        self.AGENT_ID = cf.get('notify', 'work_wechat_agentId')  # 应用ID，在后台应用中获取
        self.TO_USER = cf.get('notify', 'work_wechat_userId')  # 接收者用户名,多个用户用|分割

    def _get_access_token(self):
        url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
        values = {'corpid': self.CORP_ID,
                  'corpsecret': self.SECRET,
                  }
        req = requests.post(url, params=values)
        data = json.loads(req.text)
        return data["access_token"]

    def get_access_token(self):
        global access_token
        if self.access_token.access_token is None or datetime.now() > self.access_token.expire_time:
            __access_token = self._get_access_token()
            access_token = AccessToken(datetime.now() + timedelta(seconds=7200), __access_token)
        return access_token.access_token

    def send_data(self, message):
        send_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + self.get_access_token()
        send_values = {
            "touser": self.TO_USER,
            "msgtype": "text",
            "agentid": self.AGENT_ID,
            "text": {
                "content": message
            },
            "safe": "0"
        }
        send_msges = (bytes(json.dumps(send_values), 'utf-8'))
        resp = requests.post(send_url, send_msges)
        resp = resp.json()  # 当返回的数据是json串的时候直接用.json即可将respone转换成字典
        return resp["errmsg"]


