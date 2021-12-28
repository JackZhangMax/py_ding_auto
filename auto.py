import configparser
import datetime
import os
import random
import time
import traceback
from decimal import *
from threading import Thread
from log_config import log

import aircv
import cv2
import easyocr
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from we_chat import WeChat

import command

status = True
lock = True
width = None
length = None

# 读取配置
cf = configparser.ConfigParser(allow_no_value=True)
cf.read("conf.ini", 'utf-8')

# easyocr配置
reader = easyocr.Reader(['ch_sim'])
# 定时设置
scheduler = BackgroundScheduler(timezone='Asia/Shanghai')


# 异步配置
def async_n(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()

    return wrapper


@async_n
def start():
    global status, lock
    if negation_bool(status) or negation_bool(lock):
        notify('打卡已手动关闭', '')
        log.info(f'exit! status = {str(status)}, lock = {str(lock)}')
        return
    lock = False
    try:
        check_device_status()
        get_physical_size()
        unlock()
        log.info('设备已解锁')
        home()
        countdown(2)
        kill_ding()
        open_ding()
        log.info('已打开钉钉')
        check_result()
        log.info('识别结果完成,即将结束钉钉进程')
        kill_ding()
        lock_screen()
        lock = True
    except Exception as a:
        lock = True
        log.error(traceback.format_exc())
        notify('打卡失败', a.args[0])
        kill_ding()


# 检查设备状态
def check_device_status():
    output = command.execute_command('adb devices')
    if '*' not in output and len(output) < 30:
        raise Exception('设备不在线')


def get_physical_size():
    global length, width
    if length is None:
        output = command.execute_adb_command("wm size")
        value = output[15:len(output) - 1]
        physical_size = value.split('x')
        width = Decimal(physical_size[0])
        length = Decimal(physical_size[1])


# 解锁手机
def unlock():
    # 判断屏幕是否已点亮
    if 'state=OFF' in command.execute_adb_command('"dumpsys power | grep \'Display Power: state=\'"'):
        command.execute_adb_command('input keyevent 26')
        countdown(2)
    # 判断是否已解锁
    if 'isStatusBarKeyguard=true' in command.execute_adb_command('"dumpsys window | grep isStatusBarKeyguard"'):
        command.execute_adb_command('input keyevent 82')
        countdown(2)
        command.execute_adb_command('input text ' + str(cf.get('device', 'password')))
        countdown(2)
    # 保存截图
    save_screenshot('unlock')


def home():
    command.execute_adb_command('input keyevent 3')
    countdown(1)
    command.execute_adb_command('input keyevent 3')
    save_screenshot('home')


def open_ding():
    # 点击钉钉
    command.execute_adb_command(
        "input tap " + location(Decimal(cf.get('device', 'coordinate_x')), Decimal(cf.get('device', 'coordinate_y'))))
    # 判断是否已登录
    if 'SignUpWithPwdActivity' in command.execute_adb_command('"dumpsys activity top | grep ACTIVITY"'):
        # 点击密码框
        command.execute_adb_command('input tap ' + location(0.208, 0.379))
        countdown(3)
        # 输入密码
        command.execute_adb_command('input text ' + cf.get('ding_config', 'password'))
        countdown(2)
        # 返回
        command.execute_adb_command('input keyevent 4')
        countdown(3)
        # 点击同意协议
        command.execute_adb_command('input tap ' + location(0.096, 0.551))
        # 点击登录
        command.execute_adb_command('input tap ' + location(0.465, 0.455))
    save_screenshot('open_ding')


# 检查打卡结果
def check_result():
    countdown(6)
    # 点击工作台
    command.execute_adb_command("input tap " + location(0.486, 0.961))
    # 休眠五秒
    countdown(5)
    # 截图
    workbench_screen_path = save_screenshot('workbench')
    countdown(2)
    # 查找考勤打卡位置
    x, y = match_img(workbench_screen_path, 'clock_in_btn.png')
    command.execute_adb_command('input tap ' + str(x) + ' ' + str(y))
    countdown(6)
    check_original = save_screenshot('checkOriginal')
    countdown(2)
    # 裁剪图片
    img = cv2.imread(check_original)
    cropped = img[int(length * Decimal(0.273)):int(length * Decimal(0.371)),
              int(width * Decimal(0.069)):int(width * Decimal(0.903))]
    crop_path = get_file_path() + get_file_name('crop')
    cv2.imwrite(crop_path, cropped)
    ocr_result = ocr(crop_path)
    log.info('识别结果:{}', str(ocr_result))
    result_list = [x for x in ocr_result if '已打卡' in x]
    # 发送通知
    if len(result_list) > 0:
        notify('打卡成功' + str(len(result_list)) + '次', '内容:' + ",".join(str(i) for i in result_list))
    else:
        notify('打卡失败', '', cf.get('penetrate', 'penetrate_url') + '/getScreen/' + workbench_screen_path)


def negation_bool(b):
    b = bool(1 - b)
    return b


def countdown(s):
    time.sleep(s)


def location(x, y):
    return str(float(Decimal(x) * width)) + ' ' + str(
        float(Decimal(y) * length))


def match_img(original_img_src, pending_img_src, threshold=0.9):
    original_img = aircv.imread(original_img_src)
    pending_img = aircv.imread(pending_img_src)
    match_result = aircv.find_template(original_img, pending_img, threshold)
    return match_result['result']


def save_screenshot(name):
    screen_path = get_file_path()
    file_name = get_file_name(name)
    command.execute_command_file('adb exec-out screencap -p', screen_path + file_name)
    return screen_path + file_name


def get_file_path():
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    day = datetime.datetime.now().day
    file_path = 'screen/' + str(year) + '/' + str(month) + '/' + str(day) + '/'
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    return file_path


def get_file_name(name):
    time_str = time.strftime('%H%M%S', time.localtime())
    return name + time_str + '.png'


def ocr(img_path):
    result = reader.readtext(img_path)
    result_list = []
    for i in result:
        result_list.append(i[1])

    return result_list


def notify(title, content, url=None):
    if url is None:
        requests.get(cf.get('notify', 'bark_url') + title + '/' + content)
        WeChat.send_data(WeChat(), title + '\n' + content)
    else:
        requests.get(cf.get('notify', 'bark_url') + title + '?url=' + url)
        WeChat.send_data(WeChat(), title + '\n' + url)


def kill_ding():
    command.execute_adb_command('am force-stop com.alibaba.android.rimet')


@scheduler.scheduled_job('cron', day_of_week='*', hour=9, minute=20)
def start_timer():
    if get_working_day():
        log.info('上班打卡初始化')
        sleep_time = random.uniform(10, 420)
        send_initialization_notify(sleep_time)
        time.sleep(sleep_time)
        start()
    else:
        log.info('今天不上班')


@scheduler.scheduled_job('cron', day_of_week='*', hour=6, minute=30)
def off_work_timer():
    if get_working_day():
        log.info('下班打卡初始化')
        sleep_time = random.uniform(10, 1800)
        send_initialization_notify(sleep_time)
        time.sleep(sleep_time)
        start()
    else:
        log.info('今天不上班')


# 获取今天是否是节假日
def get_working_day():
    try:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        resp = requests.get('https://timor.tech/api/holiday/info/' + date_str)
        day_type = resp.json()['type']['type']
        return day_type == 0 or day_type == 3
    except Exception as Argument:
        log.error('获取节假日失败:' + Argument.args[0])
        return True


def send_initialization_notify(sleep_time):
    # 获取打卡开始时间
    time_str = (datetime.datetime.now() + datetime.timedelta(seconds=sleep_time)).strftime('%H:%M:%S')
    # 发送初始化通知
    notify('打卡任务初始化', '预计' + time_str + '开始')


@async_n
def start_penetrate():
    # 启动内网穿透
    penetrate_path = cf.get('penetrate', 'penetrate_path')
    if penetrate_path is not None:
        command.execute_command('frpc -c ' + penetrate_path)


# 锁屏
def lock_screen():
    command.execute_adb_command("input keyevent 26")


scheduler.start()

start_penetrate()


def switch_state():
    global status
    status = negation_bool(status)
    return str(status)
