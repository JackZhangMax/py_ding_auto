import os
import subprocess
from log_config import log


def execute_command(command):
    log.info('执行命令 : ' + command)
    result = os.popen(command).read()
    log.info('返回结果 : {}', result)
    return result


def execute_adb_command(command):
    command = 'adb shell ' + command
    # time.sleep(1)
    return execute_command(command)


def execute_command_file(command, path):
    result = subprocess.Popen(command, stdout=open(path, 'wb'))
