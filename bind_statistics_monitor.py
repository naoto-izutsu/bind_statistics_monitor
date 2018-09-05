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

logger.info('info')
logger.warning('warning')


BIND_STATISTICS_URL = "http://127.0.0.1:8080/json"
ELEMENTS = ['nsstats','opcodes','qtypes','rcodes']

def bind_statistics_json_download():
    try:
        response = requests.get(BIND_STATISTICS_URL, timeout=3)
    except requests.exceptions.ConnectionError:
        print ("Connection refused.")
        logger.warning('Connection refused.')
        sys.exit()

    if response.status_code != 200:
        print ("Don't access BIND Statistics Page.")
        print (BIND_STATISTICS_URL)
        print (response)
        sys.exit()

    return response.json()

# BINDのstatisticsをJSON形式でダウンロード
bind_statistics_json = bind_statistics_json_download()

# 
current_time = datetime.strptime(bind_statistics_json['current-time'], '%Y-%m-%dT%H:%M:%S.%fZ')
current_unix_time = current_time.strftime('%s')

f = open("/home/naoto-izutsu/zabbix_sender_file.txt", 'w')

for ELEMENT in ELEMENTS:
    try:
        for k,v in bind_statistics_json[ELEMENT].items():
            if 'RESERVED' in k or re.match('[0-9][0-9]', k):
                logger.info('skip RESERVED')
            else:
                send_message = "zabbix_host bind_"+str(ELEMENT)+"_"+str(k)+" "+str(current_unix_time)+" "+str(v)+"\n"
                f.write(send_message)
    except KeyError:
        print ("KeyError")

f.close()
