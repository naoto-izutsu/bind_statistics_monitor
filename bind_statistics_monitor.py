#!/usr/bin/env python
# -*- encoding: utf-8 -*-

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

# ログの出力名を設定
logger = logging.getLogger(__name__)

# ログレベルの設定
logger.setLevel(20)

# ログのファイル出力先を設定
fh = logging.FileHandler('/home/naoto-izutsu/test.log')
logger.addHandler(fh)

# ログの出力形式の設定
formatter = logging.Formatter('time:%(asctime)s\tlinenum:%(lineno)d\tseverity:%(levelname)s\tmsg:%(message)s')
fh.setFormatter(formatter)

# BIND Statistics関連の設定
BIND_STATISTICS_URL = "http://127.0.0.1:8080/json"
ELEMENTS = ['nsstats','opcodes','qtypes','rcodes']

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
f = open("/home/naoto-izutsu/zabbix_sender_file.txt", 'w')

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

# zabbix_senderコマンド組み立て
zabbix_sender = '/usr/local/zabbix/bin/zabbix_sender -z localhost -i /home/naoto-izutsu/zabbix_sender_file.txt --with-timestamps'
zabbix_senders = zabbix_sender.split()

try:
    res = subprocess.check_call(zabbix_senders)
except:
    logger.warning('execution failed.')
    logger.warning('command:%s', zabbix_sender)
    logger.warning('command error:%s', res)
