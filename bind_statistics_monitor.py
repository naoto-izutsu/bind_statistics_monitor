#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import configparser
import logging
import json
import requests
import datetime
from datetime import datetime, date, timedelta
from datetime import datetime as dt
import time
import sys
import re
import subprocess

# Load configuration
inifile = configparser.SafeConfigParser()
inifile.read('bind_statistics_monitor.ini', encoding='utf-8')
LOG_PATH = inifile.get('Settings','LOG_PATH')
BIND_STATISTICS_URL = inifile.get('Settings','BIND_STATISTICS_URL')
ELEMENT = inifile.get('Settings', 'ELEMENT')
ELEMENTS = ELEMENT.split()
OUTPUT_ZABBIXSENDER_FILE = inifile.get('Settings', 'OUTPUT_ZABBIXSENDER_FILE')
ZABBIX_SENDER = inifile.get('Settings', 'ZABBIX_SENDER')

# ログの出力名を設定
logger = logging.getLogger(__name__)

# ログレベルの設定
logger.setLevel(20)

# ログのファイル出力先を設定
fh = logging.FileHandler(LOG_PATH)
logger.addHandler(fh)

# ログの出力形式の設定
formatter = logging.Formatter('time:%(asctime)s\tlinenum:%(lineno)d\tseverity:%(levelname)s\tmsg:%(message)s')
fh.setFormatter(formatter)

def bind_statistics_json_download():
    logger.info('Sending request to %s.', BIND_STATISTICS_URL)
    try:
        response = requests.get(BIND_STATISTICS_URL, timeout=3)
    except requests.exceptions.ConnectionError:
        logger.warning('Connection refused from %s.', BIND_STATISTICS_URL)
        sys.exit()

    if response.status_code != 200:
        logger.warning('The bind statistics page did\'t respond correctly to the request. http status code is %s.', response.status_code)
        print (BIND_STATISTICS_URL)
        print (response)
        sys.exit()

    return response.json()

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
                send_message = "zabbix_host bind_"+str(ELEMENT)+"_"+str(k)+" "+str(current_unix_time)+" "+str(v)+"\n"
                f.write(send_message)
    except KeyError:
        logger.info('There was no value corresponding to that %s.', ELEMENT)

f.close()

# zabbix_senderコマンドを実行する
zabbix_senders = ZABBIX_SENDER.split()
try:
    res = subprocess.check_call(zabbix_senders)
except:
    logger.warning('execution failed.')
    logger.warning('command:%s', ZABBIX_SENDER)
    logger.warning('command error:%s', res)
