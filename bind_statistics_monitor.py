#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import configparser
from logging import getLogger, StreamHandler, Formatter, FileHandler, DEBUG, INFO, WARNING
import json
import requests
import datetime
from datetime import datetime, date, timedelta
from datetime import datetime as dt
import time
import sys
import re
import subprocess

def set_logger(logFile, error_level):
    # ログの出力名を設定
    logger = getLogger(__name__)

    # ログレベルの設定
    logger.setLevel(error_level)

    # ログの出力形式の設定
    log_format = Formatter('time:%(asctime)s\tlinenum:%(lineno)d\tseverity:%(levelname)s\tmsg:%(message)s')

    # ファイル出力用ハンドラーを設定
    try:
        file_handler = FileHandler(logFile)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except PermissionError as e:
        #logger.warning('log file open error.', exc_info=True)
        logger.warning('log file open error. %s', e)
        sys.exit()
    except:
        logger.warning('exception occured during file handler set.')
        sys.exit()

    return logger

def bind_statistics_json_download():
    logger.info('Sending request to %s.', BIND_STATISTICS_URL)
    try:
        response = requests.get(BIND_STATISTICS_URL, timeout=3)
    except requests.exceptions.ConnectionError:
        logger.error('Connection refused from %s.', BIND_STATISTICS_URL)
        sys.exit()
    except:
        logger.error('exception occured during Connecting to %s.', BIND_STATISTICS_URL)
        sys.exit()

    if response.status_code != 200:
        logger.error('The bind statistics page did\'t respond correctly to the request. http status code is %s.', response.status_code)
        logger.error('URL:%s', BIND_STATISTICS_URL)
        logger.error('Response:%s', response)
        sys.exit()

    return response.json()

# Load configuration
inifile = configparser.SafeConfigParser()
inifile.read('/opt/tools/bind_statistics/conf/bind_statistics_monitor.ini', encoding='utf-8')
LOG_PATH = inifile.get('Settings','LOG_PATH')
LOG_LEVEL = inifile.get('Settings','LOG_LEVEL')
BIND_STATISTICS_URL = inifile.get('Settings','BIND_STATISTICS_URL')
ELEMENT = inifile.get('Settings', 'ELEMENT')
ELEMENTS = ELEMENT.split()
OUTPUT_ZABBIXSENDER_FILE = inifile.get('Settings', 'OUTPUT_ZABBIXSENDER_FILE')
ZABBIX_SERVER = inifile.get('Settings', 'ZABBIX_SERVER')
ZABBIX_HOST = inifile.get('Settings', 'ZABBIX_HOST')
ZABBIX_SENDER = inifile.get('Settings', 'ZABBIX_SENDER')
ZABBIX_SENDER_OPS = inifile.get('Settings', 'ZABBIX_SENDER_OPS')


# ログ設定
logger = set_logger(LOG_PATH, LOG_LEVEL)

# BINDのstatisticsをJSON形式でダウンロード
bind_statistics_json = bind_statistics_json_download()

# Statisticsページ内のcurrent-timeをunixtimeに変換
current_time = datetime.strptime(bind_statistics_json['current-time'], '%Y-%m-%dT%H:%M:%S.%fZ')
current_unix_time = current_time.strftime('%s')
logger.debug('current-time is %s.  It\'s %s in unixtime.', bind_statistics_json['current-time'], current_unix_time)

# ZabbixSenderに食べさせるファイルを作る
f = open(OUTPUT_ZABBIXSENDER_FILE, 'w')

for ELEMENT in ELEMENTS:
    logger.info('Getting value of %s.', ELEMENT)
    try:
        for k,v in bind_statistics_json[ELEMENT].items():
            if 'RESERVED' in k or re.match('[0-9][0-9]', k):
                logger.debug('The key %s was skipped.', k)
            else:
                send_message = str(ZABBIX_HOST)+" bind_"+str(ELEMENT)+"_"+str(k)+" "+str(current_unix_time)+" "+str(v)+"\n"
                f.write(send_message)
    except KeyError:
        logger.info('There was no value corresponding to that %s.', ELEMENT)

f.close()

# zabbix_senderコマンドを実行する
ZABBIX_SENDER_CMD = str(ZABBIX_SENDER)+" -z "+str(ZABBIX_SERVER)+" -i "+str(OUTPUT_ZABBIXSENDER_FILE)+" "+str(ZABBIX_SENDER_OPS) 
zabbix_senders = ZABBIX_SENDER_CMD.split()
try:
    res = subprocess.check_call(zabbix_senders)
    logger.info('zabbix_senders executed. %s', res)
except:
    logger.warning('execution failed.')
    logger.warning('command:%s', ZABBIX_SENDER)
    sys.exit()

