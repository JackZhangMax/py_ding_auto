import configparser

import flask
from flask import request, Response

import auto

server = flask.Flask(__name__)

# 读取配置
cf = configparser.ConfigParser(allow_no_value=True)
cf.read("./conf.ini", 'utf-8')


# 开始打卡
@server.route('/start', methods=['get', 'post'])
def start():
    auto.start()
    return '成功啦'


# 获取截图
@server.route('/getScreen', methods=['get'])
def get_screen():
    file_name = request.args.get('fileName')
    file = open(str(file_name), 'rb')
    resp = Response(file.read(), mimetype="image/png")
    file.close()
    return resp


# 切换状态
@server.route('/switchState', methods=['get'])
def switch_state():
    return auto.switch_state()


if __name__ == '__main__':
    server.run('0.0.0.0', int(cf.get('server', 'port')))
