#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from datetime import datetime, date, timedelta
from logging import getLogger, StreamHandler, Formatter, FileHandler, DEBUG, INFO, WARNING
import configparser
import json
import pytz
import re
import requests
import subprocess
import sys

def set_logger(logFile, error_level):
    # ログの出力名を設定
    logger = getLogger(__name__)

    # ログレベルの設定
    logger.setLevel(error_level)

    # ログの出力形式の設定
    log_format = Formatter('time:%(asctime)s\tfilename:%(filename)s\tlinenum:%(lineno)d\tseverity:%(levelname)s\tmsg:%(message)s')

    # ファイル出力用ハンドラーを設定
    try:
        file_handler = FileHandler(logFile)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning('exception occured during file handler set. %s', e)
        sys.exit()

    return logger

# BIND StatisticsページからJson形式で情報をダウンロードする関数
def bind_statistics_json_download():
    logger.info('Sending request to %s.', BIND_STATISTICS_URL)
    try:
        response = requests.get(BIND_STATISTICS_URL, timeout=3)
        logger.info('response from %s. response_time=%s', BIND_STATISTICS_URL, response.elapsed.total_seconds())
    except Exception as e:
        logger.error('exception occured during Connecting to %s. %s', BIND_STATISTICS_URL, e)
        sys.exit()

    if response.status_code != 200:
        logger.error('The bind statistics page did\'t respond correctly to the request. http_status_code=%s response_time=%s', response.status_code, response.elapsed.total_seconds())
        logger.error('URL:%s', BIND_STATISTICS_URL)
        logger.error('Response:%s', response)
        sys.exit()

    return response.json()

if __name__ == '__main__':
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

    # 処理開始ログ出力
    logger.info('Start %s.', __file__)

    # BINDのstatisticsをJSON形式でダウンロード
    bind_statistics_json = bind_statistics_json_download()

    # Statisticsページ内のcurrent-timeをunixtimeに変換
    current_time = datetime.strptime(bind_statistics_json['current-time'], '%Y-%m-%dT%H:%M:%S.%fZ')
    current_time_jst = pytz.utc.localize(current_time).astimezone(pytz.timezone("Asia/Tokyo"))
    current_time_jst_unix = str(current_time_jst.timestamp()).split(".")[0]

    # ZabbixSenderに食べさせるファイルを作る
    f = open(OUTPUT_ZABBIXSENDER_FILE, 'w')

    for ELEMENT in ELEMENTS:
        logger.info('Getting value of %s.', ELEMENT)
        try:
            for k,v in bind_statistics_json[ELEMENT].items():
                if 'RESERVED' in k or re.match('[0-9][0-9]', k):
                    logger.debug('The key %s was skipped.', k)
                else:
                    send_message = str(ZABBIX_HOST)+" bind_"+str(ELEMENT)+"_"+str(k)+" "+str(current_time_jst_unix)+" "+str(v)+"\n"
                    f.write(send_message)
        except Exception as e:
            logger.warning('Failed to get the value of ELEMENT=%s. %s', ELEMENT, e)

    f.close()

    # zabbix_senderコマンドを実行する
    ZABBIX_SENDER_CMD = str(ZABBIX_SENDER)+" -z "+str(ZABBIX_SERVER)+" -i "+str(OUTPUT_ZABBIXSENDER_FILE)+" "+str(ZABBIX_SENDER_OPS) 
    zabbix_senders = ZABBIX_SENDER_CMD.split()

    try:
        res = subprocess.check_output(zabbix_senders)
        logger.info('executed zabbix_sender. %s', res)
    except Exception as e:
        logger.error('Command execution failed. %s', e)
        sys.exit()

    # 処理終了ログ出力
    logger.info('End %s.', __file__)
