import time
import logging
import requests
import jwt
import uuid
import hashlib
import math
import os
import pyupbit
import pandas as pd
import numpy
 
from urllib.parse import urlencode
from decimal import Decimal
from datetime import datetime
 
# Keys
access_key = 'here'
secret_key = 'here'
server_url = 'https://api.upbit.com'
line_target_url = 'https://notify-api.line.me/api/notify'
line_token = 'here'
 
# 상수 설정
min_order_amt = 5000
 
 
# -----------------------------------------------------------------------------
# - Name : set_loglevel
# - Desc : 로그레벨 설정
# - Input
#   1) level : 로그레벨
#     1. D(d) : DEBUG
#     2. E(e) : ERROR
#     3. 그외(기본) : INFO
# - Output
# -----------------------------------------------------------------------------
def set_loglevel(level):
    try:
 
        # ---------------------------------------------------------------------
        # 로그레벨 : DEBUG
        # ---------------------------------------------------------------------
        if level.upper() == "D":
            logging.basicConfig(
                format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]:%(message)s',
                datefmt='%Y/%m/%d %I:%M:%S %p',
                level=logging.DEBUG
            )
        # ---------------------------------------------------------------------
        # 로그레벨 : ERROR
        # ---------------------------------------------------------------------
        elif level.upper() == "E":
            logging.basicConfig(
                format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]:%(message)s',
                datefmt='%Y/%m/%d %I:%M:%S %p',
                level=logging.ERROR
            )
        # ---------------------------------------------------------------------
        # 로그레벨 : INFO
        # ---------------------------------------------------------------------
        else:
            # -----------------------------------------------------------------------------
            # 로깅 설정
            # 로그레벨(DEBUG, INFO, WARNING, ERROR, CRITICAL)
            # -----------------------------------------------------------------------------
            logging.basicConfig(
                format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]:%(message)s',
                datefmt='%Y/%m/%d %I:%M:%S %p',
                level=logging.INFO
            )
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : send_request
# - Desc : 리퀘스트 처리
# - Input
#   1) reqType : 요청 타입
#   2) reqUrl : 요청 URL
#   3) reqParam : 요청 파라메타
#   4) reqHeader : 요청 헤더
# - Output
#   4) reponse : 응답 데이터
# -----------------------------------------------------------------------------
def send_request(reqType, reqUrl, reqParam, reqHeader):
    try:
 
        # 요청 가능회수 확보를 위해 기다리는 시간(초)
        err_sleep_time = 0.3
 
        # 요청에 대한 응답을 받을 때까지 반복 수행
        while True:
 
            # 요청 처리
            response = requests.request(reqType, reqUrl, params=reqParam, headers=reqHeader)
 
            # 요청 가능회수 추출
            if 'Remaining-Req' in response.headers:
 
                hearder_info = response.headers['Remaining-Req']
                start_idx = hearder_info.find("sec=")
                end_idx = len(hearder_info)
                remain_sec = hearder_info[int(start_idx):int(end_idx)].replace('sec=', '')
            else:
                logging.error("헤더 정보 이상")
                logging.error(response.headers)
                break
 
            # 요청 가능회수가 3개 미만이면 요청 가능회수 확보를 위해 일정시간 대기
            if int(remain_sec) < 3:
                logging.debug("요청 가능회수 한도 도달! 남은횟수:" + str(remain_sec))
                time.sleep(err_sleep_time)
 
            # 정상 응답
            if response.status_code == 200 or response.status_code == 201:
                break
            # 요청 가능회수 초과인 경우
            elif response.status_code == 429:
                logging.error("요청 가능회수 초과!:" + str(response.status_code))
                time.sleep(err_sleep_time)
            # 그 외 오류
            else:
                logging.error("기타 에러:" + str(response.status_code))
                logging.error(response.status_code)
                logging.error(response)
                break
 
            # 요청 가능회수 초과 에러 발생시에는 다시 요청
            logging.info("[restRequest] 요청 재처리중...")
 
        return response
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_items
# - Desc : 전체 종목 리스트 조회
# - Input
#   1) market : 대상 마켓(콤마 구분자:KRW,BTC,USDT)
#   2) except_item : 제외 종목(콤마 구분자:BTC,ETH)
# - Output
#   1) 전체 리스트 : 리스트
# -----------------------------------------------------------------------------
def get_items(market, except_item):
    try:
 
        # 조회결과 리턴용
        rtn_list = []
 
        # 마켓 데이터
        markets = market.split(',')
 
        # 제외 데이터
        except_items = except_item.split(',')
 
        url = "https://api.upbit.com/v1/market/all"
        querystring = {"isDetails": "false"}
        response = send_request("GET", url, querystring, "")
        data = response.json()
 
        # 조회 마켓만 추출
        for data_for in data:
            for market_for in markets:
                if data_for['market'].split('-')[0] == market_for:
                    rtn_list.append(data_for)
 
        # 제외 종목 제거
        for rtnlist_for in rtn_list[:]:
            for exceptItemFor in except_items:
                for marketFor in markets:
                    if rtnlist_for['market'] == marketFor + '-' + exceptItemFor:
                        rtn_list.remove(rtnlist_for)
 
        return rtn_list
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : buycoin_mp
# - Desc : 시장가 매수
# - Input
#   1) target_item : 대상종목
#   2) buy_amount : 매수금액
# - Output
#   1) rtn_data : 매수결과
# -----------------------------------------------------------------------------
def buycoin_mp(target_item, buy_amount):
    try:
 
        query = {
            'market': target_item,
            'side': 'bid',
            'price': buy_amount,
            'ord_type': 'price',
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        logging.info("")
        logging.info("----------------------------------------------")
        logging.info("시장가 매수 요청 완료! 결과:")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : buycoin_tg
# - Desc : 지정가 매수
# - Input
#   1) target_item : 대상종목
#   2) buy_amount : 매수금액
#   3) buy_price : 매수가격
# - Output
#   1) rtn_data : 매수요청결과
# -----------------------------------------------------------------------------
def buycoin_tg(target_item, buy_amount, buy_price):
    try:
 
        # 매수수량 계산
        vol = Decimal(str(buy_amount)) / Decimal(str(buy_price))
 
        query = {
            'market': target_item,
            'side': 'bid',
            'volume': vol,
            'price': buy_price,
            'ord_type': 'limit',
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        logging.info("")
        logging.info("----------------------------------------------")
        logging.info("지정가 매수요청 완료!")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : sellcoin_mp
# - Desc : 시장가 매도
# - Input
#   1) target_item : 대상종목
#   2) cancel_yn : 기존 주문 취소 여부
# - Output
#   1) rtn_data : 매도결과
# -----------------------------------------------------------------------------
# 시장가 매도
def sellcoin_mp(target_item, cancel_yn):
    try:
 
        if cancel_yn == 'Y':
            # 기존 주문이 있으면 취소
            cancel_order(target_item, "SELL")
 
        # 잔고 조회
        cur_balance = get_balance(target_item)
 
        query = {
            'market': target_item,
            'side': 'ask',
            'volume': cur_balance,
            'ord_type': 'market',
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        logging.info("")
        logging.info("----------------------------------------------")
        logging.info("시장가 매도 요청 완료! 결과:")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : sellcoin_tg
# - Desc : 지정가 매도
# - Input
#   1) target_item : 대상종목
#   2) sell_price : 매도희망금액
# - Output
#   1) rtn_data : 매도결과
# -----------------------------------------------------------------------------
def sellcoin_tg(target_item, sell_price):
    try:
 
        # 잔고 조회
        cur_balance = get_balance(target_item)
 
        query = {
            'market': target_item,
            'side': 'ask',
            'volume': cur_balance,
            'price': sell_price,
            'ord_type': 'limit',
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        logging.info("")
        logging.info("----------------------------------------------")
        logging.info("지정가 매도 설정 완료!")
        logging.info(rtn_data)
        logging.info("----------------------------------------------")
 
        return rtn_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_balance
# - Desc : 주문가능 잔고 조회
# - Input
#   1) target_item : 대상 종목
# - Output
#   2) rtn_balance : 주문가능 잔고
# -----------------------------------------------------------------------------
def get_balance(target_item):
    try:
 
        # 주문가능 잔고 리턴용
        rtn_balance = 0
 
        # 최대 재시도 횟수
        max_cnt = 0
 
        # 잔고가 조회 될 때까지 반복
        while True:
 
            # 조회 회수 증가
            max_cnt = max_cnt + 1
 
            payload = {
                'access_key': access_key,
                'nonce': str(uuid.uuid4()),
            }
 
            jwt_token = jwt.encode(payload, secret_key)
            authorize_token = 'Bearer {}'.format(jwt_token)
            headers = {"Authorization": authorize_token}
 
            res = send_request("GET", server_url + "/v1/accounts", "", headers)
            my_asset = res.json()
 
            # 해당 종목에 대한 잔고 조회
            # 잔고는 마켓에 상관없이 전체 잔고가 조회됨
            for myasset_for in my_asset:
                if myasset_for['currency'] == target_item.split('-')[1]:
                    rtn_balance = myasset_for['balance']
 
            # 잔고가 0 이상일때까지 반복
            if Decimal(str(rtn_balance)) > Decimal(str(0)):
                break
 
            # 최대 100회 수행
            if max_cnt > 100:
                break
 
            logging.info("[주문가능 잔고 리턴용] 요청 재처리중...")
 
        return rtn_balance
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_candle
# - Desc : 캔들 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 조회 범위
# - Output
#   1) 캔들 정보 배열
# -----------------------------------------------------------------------------
def get_candle(target_item, tick_kind, inq_range):
    try:
 
        # ----------------------------------------
        # Tick 별 호출 URL 설정
        # ----------------------------------------
        # 분붕
        if tick_kind == "1" or tick_kind == "3" or tick_kind == "5" or tick_kind == "10" or tick_kind == "15" or tick_kind == "30" or tick_kind == "60" or tick_kind == "240":
            target_url = "minutes/" + tick_kind
        # 일봉
        elif tick_kind == "D":
            target_url = "days"
        # 주봉
        elif tick_kind == "W":
            target_url = "weeks"
        # 월봉
        elif tick_kind == "M":
            target_url = "months"
        # 잘못된 입력
        else:
            raise Exception("잘못된 틱 종류:" + str(tick_kind))
 
        logging.debug(target_url)
 
        # ----------------------------------------
        # Tick 조회
        # ----------------------------------------
        querystring = {"market": target_item, "count": inq_range}
        res = send_request("GET", server_url + "/v1/candles/" + target_url, querystring, "")
        candle_data = res.json()
 
        logging.debug(candle_data)
 
        return candle_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_targetprice
# - Desc : 호가단위 금액 계산
# - Input
#   1) cal_type : H:호가로, R:비율로
#   2) st_price : 기준가격
#   3) chg_val : 변화단위
# - Output
#   1) rtn_price : 계산된 금액
# -----------------------------------------------------------------------------
def get_targetprice(cal_type, st_price, chg_val):
    try:
        # 계산된 가격
        rtn_price = st_price
 
        # 호가단위로 계산
        if cal_type.upper() == "H":
 
            for i in range(0, abs(int(chg_val))):
 
                hoga_val = get_hoga(rtn_price)
 
                if Decimal(str(chg_val)) > 0:
                    rtn_price = Decimal(str(rtn_price)) + Decimal(str(hoga_val))
                elif Decimal(str(chg_val)) < 0:
                    rtn_price = Decimal(str(rtn_price)) - Decimal(str(hoga_val))
                else:
                    break
 
        # 비율로 계산
        elif cal_type.upper() == "R":
 
            while True:
 
                # 호가단위 추출
                hoga_val = get_hoga(st_price)
 
                if Decimal(str(chg_val)) > 0:
                    rtn_price = Decimal(str(rtn_price)) + Decimal(str(hoga_val))
                elif Decimal(str(chg_val)) < 0:
                    rtn_price = Decimal(str(rtn_price)) - Decimal(str(hoga_val))
                else:
                    break
 
                if Decimal(str(chg_val)) > 0:
                    if Decimal(str(rtn_price)) >= Decimal(str(st_price)) * (
                            Decimal(str(1)) + (Decimal(str(chg_val))) / Decimal(str(100))):
                        break
                elif Decimal(str(chg_val)) < 0:
                    if Decimal(str(rtn_price)) <= Decimal(str(st_price)) * (
                            Decimal(str(1)) + (Decimal(str(chg_val))) / Decimal(str(100))):
                        break
 
        return rtn_price
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_hoga
# - Desc : 호가 금액 계산
# - Input
#   1) cur_price : 현재가격
# - Output
#   1) hoga_val : 호가단위
# -----------------------------------------------------------------------------
def get_hoga(cur_price):
    try:
 
        # 호가 단위
        if Decimal(str(cur_price)) < 10:
            hoga_val = 0.01
        elif Decimal(str(cur_price)) < 100:
            hoga_val = 0.1
        elif Decimal(str(cur_price)) < 1000:
            hoga_val = 1
        elif Decimal(str(cur_price)) < 10000:
            hoga_val = 5
        elif Decimal(str(cur_price)) < 100000:
            hoga_val = 10
        elif Decimal(str(cur_price)) < 500000:
            hoga_val = 50
        elif Decimal(str(cur_price)) < 1000000:
            hoga_val = 100
        elif Decimal(str(cur_price)) < 2000000:
            hoga_val = 500
        else:
            hoga_val = 1000
 
        return hoga_val
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_krwbal
# - Desc : KRW 잔고 조회
# - Input
# - Output
#   1) KRW 잔고 Dictionary
#     1. krw_balance : KRW 잔고
#     2. fee : 수수료
#     3. available_krw : 매수가능 KRW잔고(수수료를 고려한 금액)
# -----------------------------------------------------------------------------
def get_krwbal():
    try:
 
        # 잔고 리턴용
        rtn_balance = {}
 
        # 수수료 0.05%(업비트 기준)
        fee_rate = 0.05
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("GET", server_url + "/v1/accounts", "", headers)
 
        data = res.json()
 
        logging.debug(data)
 
        for dataFor in data:
            if (dataFor['currency']) == "KRW":
                krw_balance = math.floor(Decimal(str(dataFor['balance'])))
 
        # 잔고가 있는 경우만
        if Decimal(str(krw_balance)) > Decimal(str(0)):
            # 수수료
            fee = math.ceil(Decimal(str(krw_balance)) * (Decimal(str(fee_rate)) / Decimal(str(100))))
 
            # 매수가능금액
            available_krw = math.floor(Decimal(str(krw_balance)) - Decimal(str(fee)))
 
        else:
            # 수수료
            fee = 0
 
            # 매수가능금액
            available_krw = 0
 
        # 결과 조립
        rtn_balance['krw_balance'] = krw_balance
        rtn_balance['fee'] = fee
        rtn_balance['available_krw'] = available_krw
 
        return rtn_balance
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_accounts
# - Desc : 잔고정보 조회
# - Input
#   1) except_yn : KRW 및 소액 제외
#   2) market_code : 마켓코드 추가(매도시 필요)
# - Output
#   1) 잔고 정보
# -----------------------------------------------------------------------------
# 계좌 조회
def get_accounts(except_yn, market_code):
    try:
 
        rtn_data = []
 
        # 해당 마켓에 존재하는 종목 리스트만 추출
        market_item_list = get_items(market_code, '')
 
        # 소액 제외 기준
        min_price = 5000
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("GET", server_url + "/v1/accounts", "", headers)
        account_data = res.json()
 
        for account_data_for in account_data:
            for market_item_list_for in market_item_list:
 
                # 해당 마켓에 있는 종목만 조합
                if market_code + '-' + account_data_for['currency'] == market_item_list_for['market']:
 
                    # KRW 및 소액 제외
                    if except_yn == "Y" or except_yn == "y":
                        if account_data_for['currency'] != "KRW" and Decimal(str(account_data_for['avg_buy_price'])) * (
                                Decimal(str(account_data_for['balance'])) + Decimal(
                            str(account_data_for['locked']))) >= Decimal(str(min_price)):
                            rtn_data.append(
                                {'market': market_code + '-' + account_data_for['currency'],
                                 'balance': account_data_for['balance'],
                                 'locked': account_data_for['locked'],
                                 'avg_buy_price': account_data_for['avg_buy_price'],
                                 'avg_buy_price_modified': account_data_for['avg_buy_price_modified']})
                    else:
                        if account_data_for['currency'] != "KRW":
                            rtn_data.append(
                                {'market': market_code + '-' + account_data_for['currency'],
                                 'balance': account_data_for['balance'],
                                 'locked': account_data_for['locked'],
                                 'avg_buy_price': account_data_for['avg_buy_price'],
                                 'avg_buy_price_modified': account_data_for['avg_buy_price_modified']})
 
        return rtn_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : chg_account_to_comma
# - Desc : 잔고 종목 리스트를 콤마리스트로 변경
# - Input
#   1) account_data : 잔고 데이터
# - Output
#   1) 종목 리스트(콤마 구분자)
# -----------------------------------------------------------------------------
def chg_account_to_comma(account_data):
    try:
 
        rtn_data = ""
 
        for account_data_for in account_data:
 
            if rtn_data == '':
                rtn_data = rtn_data + account_data_for['market']
            else:
                rtn_data = rtn_data + ',' + account_data_for['market']
 
        return rtn_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_ticker
# - Desc : 현재가 조회
# - Input
#   1) target_itemlist : 대상 종목(콤마 구분자)
# - Output
#   2) 현재가 데이터
# -----------------------------------------------------------------------------
def get_ticker(target_itemlist):
    try:
 
        url = "https://api.upbit.com/v1/ticker"
 
        querystring = {"markets": target_itemlist}
        response = send_request("GET", url, querystring, "")
 
        rtn_data = response.json()
 
        return rtn_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : cancel_order
# - Desc : 미체결 주문 취소
# - Input
#   1) target_item : 대상종목
#   2) side : 매수/매도 구분(BUY/bid:매수, SELL/ask:매도, ALL:전체)
# - Output
# -----------------------------------------------------------------------------
def cancel_order(target_item, side):
    try:
 
        # 미체결 주문 조회
        order_data = get_order(target_item)
 
        # 매수/매도 구분
        for order_data_for in order_data:
 
            if side == "BUY" or side == "buy":
                if order_data_for['side'] == "ask":
                    order_data.remove(order_data_for)
            elif side == "SELL" or side == "sell":
                if order_data_for['side'] == "bid":
                    order_data.remove(order_data_for)
 
        # 미체결 주문이 있으면
        if len(order_data) > 0:
 
            # 미체결 주문내역 전체 취소
            for order_data_for in order_data:
                cancel_order_uuid(order_data_for['uuid'])
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : cancel_order_uuid
# - Desc : 미체결 주문 취소 by UUID
# - Input
#   1) order_uuid : 주문 키
# - Output
#   1) 주문 내역 취소
# -----------------------------------------------------------------------------
def cancel_order_uuid(order_uuid):
    try:
 
        query = {
            'uuid': order_uuid,
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("DELETE", server_url + "/v1/order", query, headers)
        rtn_data = res.json()
 
        return rtn_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_order
# - Desc : 미체결 주문 조회
# - Input
#   1) target_item : 대상종목
# - Output
#   1) 미체결 주문 내역
# -----------------------------------------------------------------------------
def get_order(target_item):
    try:
        query = {
            'market': target_item,
            'state': 'wait',
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("GET", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        return rtn_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_order
# - Desc : 미체결 주문 조회
# - Input
#   1) side : 주문상태
# - Output
#   1) 주문 내역 리스트
# -----------------------------------------------------------------------------
def get_order_list(side):
    try:
        query = {
            'state': side,
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("GET", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        return rtn_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_rsi
# - Desc : RSI 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 조회 범위
# - Output
#   1) RSI 값
# -----------------------------------------------------------------------------
def get_rsi(target_item, tick_kind, inq_range):
    try:
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        df = pd.DataFrame(candle_data)
        df = df.reindex(index=df.index[::-1]).reset_index()
 
        df['close'] = df["trade_price"]
 
        # RSI 계산
        def rsi(ohlc: pd.DataFrame, period: int = 14):
            ohlc["close"] = ohlc["close"]
            delta = ohlc["close"].diff()
 
            up, down = delta.copy(), delta.copy()
            up[up < 0] = 0
            down[down > 0] = 0
 
            _gain = up.ewm(com=(period - 1), min_periods=period).mean()
            _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
 
            RS = _gain / _loss
            return pd.Series(100 - (100 / (1 + RS)), name="RSI")
 
        rsi = round(rsi(df, 14).iloc[-1], 4)
 
        return rsi
 
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_mfi
# - Desc : MFI 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 캔들 조회 범위
#   4) loop_cnt : 지표 반복계산 횟수
# - Output
#   1) MFI 값
# -----------------------------------------------------------------------------
def get_mfi(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # MFI 데이터 리턴용
        mfi_list = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
 
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
 
            df['typical_price'] = (df['trade_price'] + df['high_price'] + df['low_price']) / 3
            df['money_flow'] = df['typical_price'] * df['candle_acc_trade_volume']
 
            positive_mf = 0
            negative_mf = 0
 
            for i in range(0, 14):
 
                if df["typical_price"][i] > df["typical_price"][i + 1]:
                    positive_mf = positive_mf + df["money_flow"][i]
                elif df["typical_price"][i] < df["typical_price"][i + 1]:
                    negative_mf = negative_mf + df["money_flow"][i]
 
            if negative_mf > 0:
                mfi = 100 - (100 / (1 + (positive_mf / negative_mf)))
            else:
                mfi = 100 - (100 / (1 + (positive_mf)))
 
            mfi_list.append({"type": "MFI", "DT": dfDt[0], "MFI": round(mfi, 4)})
 
        return mfi_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_macd
# - Desc : MACD 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 캔들 조회 범위
#   4) loop_cnt : 지표 반복계산 횟수
# - Output
#   1) MACD 값
# -----------------------------------------------------------------------------
def get_macd(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # MACD 데이터 리턴용
        macd_list = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])
 
        df = pd.DataFrame(candle_datas[0])
        df = df.iloc[::-1]
        df = df['trade_price']
 
        # MACD 계산
        exp1 = df.ewm(span=12, adjust=False).mean()
        exp2 = df.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        exp3 = macd.ewm(span=9, adjust=False).mean()
 
        for i in range(0, int(loop_cnt)):
            macd_list.append(
                {"type": "MACD", "DT": candle_datas[0][i]['candle_date_time_kst'], "MACD": round(macd[i], 4),
                 "SIGNAL": round(exp3[i], 4),
                 "OCL": round(macd[i] - exp3[i], 4)})
 
        return macd_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_bb
# - Desc : 볼린저밴드 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 캔들 조회 범위
#   4) loop_cnt : 지표 반복계산 횟수
# - Output
#   1) 볼린저 밴드 값
# -----------------------------------------------------------------------------
def get_bb(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # 볼린저밴드 데이터 리턴용
        bb_list = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df['trade_price'].iloc[::-1]
 
            # 표준편차(곱)
            unit = 2
 
            band1 = unit * numpy.std(df[len(df) - 20:len(df)])
            bb_center = numpy.mean(df[len(df) - 20:len(df)])
            band_high = bb_center + band1
            band_low = bb_center - band1
 
            bb_list.append({"type": "BB", "DT": dfDt[0], "BBH": round(band_high, 4), "BBM": round(bb_center, 4),
                            "BBL": round(band_low, 4)})
 
        return bb_list
 
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_williams
# - Desc : 윌리암스 %R 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 캔들 조회 범위
#   4) loop_cnt : 지표 반복계산 횟수
# - Output
#   1) 윌리암스 %R 값
# -----------------------------------------------------------------------------
def get_williamsR(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # 윌리암스R 데이터 리턴용
        williams_list = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.iloc[:14]
 
            # 계산식
            # %R = (Highest High - Close)/(Highest High - Lowest Low) * -100
            hh = numpy.max(df['high_price'])
            ll = numpy.min(df['low_price'])
            cp = df['trade_price'][0]
 
            w = (hh - cp) / (hh - ll) * -100
 
            williams_list.append(
                {"type": "WILLIAMS", "DT": dfDt[0], "HH": round(hh, 4), "LL": round(ll, 4), "CP": round(cp, 4),
                 "W": round(w, 4)})
 
        return williams_list
 
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_rsi
# - Desc : RSI 조회
# - Input
#   1) candle_data : 캔들 정보
# - Output
#   1) RSI 값
# -----------------------------------------------------------------------------
def get_rsi(candle_datas):
    try:
 
        # RSI 데이터 리턴용
        rsi_data = []
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.reindex(index=df.index[::-1]).reset_index()
 
            df['close'] = df["trade_price"]
 
            # RSI 계산
            def rsi(ohlc: pd.DataFrame, period: int = 14):
                ohlc["close"] = ohlc["close"]
                delta = ohlc["close"].diff()
 
                up, down = delta.copy(), delta.copy()
                up[up < 0] = 0
                down[down > 0] = 0
 
                _gain = up.ewm(com=(period - 1), min_periods=period).mean()
                _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
 
                RS = _gain / _loss
                return pd.Series(100 - (100 / (1 + RS)), name="RSI")
 
            rsi = round(rsi(df, 14).iloc[-1], 4)
            rsi_data.append({"type": "RSI", "DT": dfDt[0], "RSI": rsi})
 
        return rsi_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_mfi
# - Desc : MFI 조회
# - Input
#   1) candle_datas : 캔들 정보
# - Output
#   1) MFI 값
# -----------------------------------------------------------------------------
def get_mfi(candle_datas):
    try:
 
        # MFI 데이터 리턴용
        mfi_list = []
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
 
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
 
            df['typical_price'] = (df['trade_price'] + df['high_price'] + df['low_price']) / 3
            df['money_flow'] = df['typical_price'] * df['candle_acc_trade_volume']
 
            positive_mf = 0
            negative_mf = 0
 
            for i in range(0, 14):
 
                if df["typical_price"][i] > df["typical_price"][i + 1]:
                    positive_mf = positive_mf + df["money_flow"][i]
                elif df["typical_price"][i] < df["typical_price"][i + 1]:
                    negative_mf = negative_mf + df["money_flow"][i]
 
            if negative_mf > 0:
                mfi = 100 - (100 / (1 + (positive_mf / negative_mf)))
            else:
                mfi = 100 - (100 / (1 + (positive_mf)))
 
            mfi_list.append({"type": "MFI", "DT": dfDt[0], "MFI": round(mfi, 4)})
 
        return mfi_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_macd
# - Desc : MACD 조회
# - Input
#   1) candle_datas : 캔들 정보
#   2) loop_cnt : 반복 횟수
# - Output
#   1) MACD 값
# -----------------------------------------------------------------------------
def get_macd(candle_datas, loop_cnt):
    try:
 
        # MACD 데이터 리턴용
        macd_list = []
 
        df = pd.DataFrame(candle_datas[0])
        df = df.iloc[::-1]
        df = df['trade_price']
 
        # MACD 계산
        exp1 = df.ewm(span=12, adjust=False).mean()
        exp2 = df.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        exp3 = macd.ewm(span=9, adjust=False).mean()
 
        for i in range(0, int(loop_cnt)):
            macd_list.append(
                {"type": "MACD", "DT": candle_datas[0][i]['candle_date_time_kst'], "MACD": round(macd[i], 4),
                 "SIGNAL": round(exp3[i], 4),
                 "OCL": round(macd[i] - exp3[i], 4)})
 
        return macd_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_ma
# - Desc : MA 조회
# - Input
#   1) candle_datas : 캔들 정보
#   2) loop_cnt : 반복 횟수
# - Output
#   1) MA 값
# -----------------------------------------------------------------------------
def get_ma(candle_datas, loop_cnt):
    try:
        # MA 데이터 리턴용
        ma_list = []
 
        df = pd.DataFrame(candle_datas[0])
        df = df.iloc[::-1]
        df = df['trade_price']
 
        # MA 계산
 
        ma5 = df.rolling(window=5).mean()
        ma10 = df.rolling(window=10).mean()
        ma20 = df.rolling(window=20).mean()
        ma60 = df.rolling(window=60).mean()
        ma120 = df.rolling(window=120).mean()
 
        for i in range(0, int(loop_cnt)):
            ma_list.append(
                {"type": "MA", "DT": candle_datas[0][i]['candle_date_time_kst'], "MA5": ma5[i], "MA10": ma10[i],
                 "MA20": ma20[i], "MA60": ma60[i], "MA120": ma120[i]
                    , "MA_5_10": str(Decimal(str(ma5[i])) - Decimal(str(ma10[i])))
                    , "MA_10_20": str(Decimal(str(ma10[i])) - Decimal(str(ma20[i])))
                    , "MA_20_60": str(Decimal(str(ma20[i])) - Decimal(str(ma60[i])))
                    , "MA_60_120": str(Decimal(str(ma60[i])) - Decimal(str(ma120[i])))})
 
        return ma_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_bb
# - Desc : 볼린저밴드 조회
# - Input
#   1) candle_datas : 캔들 정보
# - Output
#   1) 볼린저 밴드 값
# -----------------------------------------------------------------------------
def get_bb(candle_datas):
    try:
 
        # 볼린저밴드 데이터 리턴용
        bb_list = []
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df['trade_price'].iloc[::-1]
 
            # 표준편차(곱)
            unit = 2
 
            band1 = unit * numpy.std(df[len(df) - 20:len(df)])
            bb_center = numpy.mean(df[len(df) - 20:len(df)])
            band_high = bb_center + band1
            band_low = bb_center - band1
 
            bb_list.append({"type": "BB", "DT": dfDt[0], "BBH": round(band_high, 4), "BBM": round(bb_center, 4),
                            "BBL": round(band_low, 4)})
 
        return bb_list
 
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_williams
# - Desc : 윌리암스 %R 조회
# - Input
#   1) candle_datas : 캔들 정보
# - Output
#   1) 윌리암스 %R 값
# -----------------------------------------------------------------------------
def get_williams(candle_datas):
    try:
 
        # 윌리암스R 데이터 리턴용
        williams_list = []
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df.iloc[:14]
 
            # 계산식
            # %R = (Highest High - Close)/(Highest High - Lowest Low) * -100
            hh = numpy.max(df['high_price'])
            ll = numpy.min(df['low_price'])
            cp = df['trade_price'][0]
 
            w = (hh - cp) / (hh - ll) * -100
 
            williams_list.append(
                {"type": "WILLIAMS", "DT": dfDt[0], "HH": round(hh, 4), "LL": round(ll, 4), "CP": round(cp, 4),
                 "W": round(w, 4)})
 
        return williams_list
 
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_cci
# - Desc : CCI 조회
# - Input
#   1) candle_data : 캔들 정보
#   2) loop_cnt : 조회 건수
# - Output
#   1) CCI 값
# -----------------------------------------------------------------------------
def get_cci(candle_data, loop_cnt):
    try:
 
        cci_val = 20
 
        # CCI 데이터 리턴용
        cci_list = []
 
        # 사용하지 않는 캔들 갯수 정리(속도 개선)
        del candle_data[cci_val * 2:]
 
        # 오름차순 정렬
        df = pd.DataFrame(candle_data)
        ordered_df = df.sort_values(by=['candle_date_time_kst'], ascending=[True])
 
        # 계산식 : (Typical Price - Simple Moving Average) / (0.015 * Mean absolute Deviation)
        ordered_df['TP'] = (ordered_df['high_price'] + ordered_df['low_price'] + ordered_df['trade_price']) / 3
        ordered_df['SMA'] = ordered_df['TP'].rolling(window=cci_val).mean()
        ordered_df['MAD'] = ordered_df['TP'].rolling(window=cci_val).apply(lambda x: pd.Series(x).mad())
        ordered_df['CCI'] = (ordered_df['TP'] - ordered_df['SMA']) / (0.015 * ordered_df['MAD'])
 
        # 개수만큼 조립
        for i in range(0, loop_cnt):
            cci_list.append({"type": "CCI", "DT": ordered_df['candle_date_time_kst'].loc[i],
                             "CCI": round(ordered_df['CCI'].loc[i], 4)})
 
        return cci_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_indicators
# - Desc : 보조지표 조회
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 캔들 조회 범위
#   4) loop_cnt : 지표 반복계산 횟수
# - Output
#   1) RSI
#   2) MFI
#   3) MACD
#   4) BB
#   5) WILLIAMS %R
#   6) CCI
# -----------------------------------------------------------------------------
def get_indicators(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 보조지표 리턴용
        indicator_data = []
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        if len(candle_data) >= 30:
 
            # 조회 횟수별 candle 데이터 조합
            for i in range(0, int(loop_cnt)):
                candle_datas.append(candle_data[i:int(len(candle_data))])
 
            # RSI 정보 조회
            rsi_data = get_rsi(candle_datas)
 
            # MFI 정보 조회
            mfi_data = get_mfi(candle_datas)
 
            # MACD 정보 조회
            macd_data = get_macd(candle_datas, loop_cnt)
 
            # BB 정보 조회
            bb_data = get_bb(candle_datas)
 
            # WILLIAMS %R 조회
            williams_data = get_williams(candle_datas)
 
            # MA 정보 조회
            ma_data = get_ma(candle_datas, loop_cnt)
 
            # CCI 정보 조회
            cci_data = get_cci(candle_data, loop_cnt)
 
            if len(rsi_data) > 0:
                indicator_data.append(rsi_data)
 
            if len(mfi_data) > 0:
                indicator_data.append(mfi_data)
 
            if len(macd_data) > 0:
                indicator_data.append(macd_data)
 
            if len(bb_data) > 0:
                indicator_data.append(bb_data)
 
            if len(williams_data) > 0:
                indicator_data.append(williams_data)
 
            if len(ma_data) > 0:
                indicator_data.append(ma_data)
 
            if len(cci_data) > 0:
                indicator_data.append(cci_data)
 
        return indicator_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_order_status
# - Desc : 주문 조회(상태별)
# - Input
#   1) target_item : 대상종목
#   2) status : 주문상태(wait : 체결 대기, watch : 예약주문 대기, done : 전체 체결 완료, cancel : 주문 취소)
# - Output
#   1) 주문 내역
# -----------------------------------------------------------------------------
def get_order_status(target_item, status):
    try:
 
        query = {
            'market': target_item,
            'state': status,
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("GET", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
 
        return rtn_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : orderby_dict
# - Desc : 딕셔너리 정렬
# - Input
#   1) target_dict : 정렬 대상 딕셔너리
#   2) target_column : 정렬 대상 딕셔너리
#   3) order_by : 정렬방식(False:오름차순, True,내림차순)
# - Output
#   1) 정렬된 딕서너리
# -----------------------------------------------------------------------------
def orderby_dict(target_dict, target_column, order_by):
    try:
 
        rtn_dict = sorted(target_dict, key=(lambda x: x[target_column]), reverse=order_by)
 
        return rtn_dict
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : filter_dict
# - Desc : 딕셔너리 필터링
# - Input
#   1) target_dict : 정렬 대상 딕셔너리
#   2) target_column : 정렬 대상 컬럼
#   3) filter : 필터
# - Output
#   1) 필터링된 딕서너리
# -----------------------------------------------------------------------------
def filter_dict(target_dict, target_column, filter):
    try:
 
        for target_dict_for in target_dict[:]:
            if target_dict_for[target_column] != filter:
                target_dict.remove(target_dict_for)
 
        return target_dict
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_order_chance
# - Desc : 주문 가능정보 조회
# - Input
#   1) target_item : 대상종목
# - Output
#   1) 주문 가능 정보
# -----------------------------------------------------------------------------
def get_order_chance(target_item):
    try:
        query = {
            'market': target_item,
        }
 
        query_string = urlencode(query).encode()
 
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
 
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
 
        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}
 
        res = send_request("GET", server_url + "/v1/orders/chance", query, headers)
        rtn_data = res.json()
 
        return rtn_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_max_min
# - Desc : MAX/MIN 값 조회
# - Input
#   1) candle_datas : 캔들 정보
#   2) col_name : 대상 컬럼
# - Output
#   1) MAX 값
#   2) MIN 값
# -----------------------------------------------------------------------------
def get_max(candle_data, col_name_high, col_name_low):
    try:
        # MA 데이터 리턴용
        max_min_list = []
 
        df = pd.DataFrame(candle_data)
        df = df.iloc[::-1]
 
        # MAX 계산
 
        max = numpy.max(df[col_name_high])
        min = numpy.min(df[col_name_low])
 
        max_min_list.append(
            {"MAX": max, "MIN": min})
 
        return max_min_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : send_line_msg
# - Desc : 라인 메세지 전송
# - Input
#   1) message : 메세지
# - Output
#   1) response : 발송결과(200:정상)
# -----------------------------------------------------------------------------
def send_line_message(message):
    try:
        headers = {'Authorization': 'Bearer ' + line_token}
        data = {'message': message}
 
        response = requests.post(line_target_url, headers=headers, data=data)
 
        logging.debug(response)
 
        return response
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : get_indicator_sel
# - Desc : 보조지표 조회(원하는 지표만)
# - Input
#   1) target_item : 대상 종목
#   2) tick_kind : 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월)
#   3) inq_range : 캔들 조회 범위
#   4) loop_cnt : 지표 반복계산 횟수
#   5) 보조지표 : 리스트
# - Output
#   1) 보조지표
# -----------------------------------------------------------------------------
def get_indicator_sel(target_item, tick_kind, inq_range, loop_cnt, indi_type):
    try:
 
        # 보조지표 리턴용
        indicator_data = {}
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        if len(candle_data) >= 30:
 
            # 조회 횟수별 candle 데이터 조합
            for i in range(0, int(loop_cnt)):
                candle_datas.append(candle_data[i:int(len(candle_data))])
 
            if 'RSI' in indi_type:
                # RSI 정보 조회
                rsi_data = get_rsi(candle_datas)
                indicator_data['RSI'] = rsi_data
 
            if 'MFI' in indi_type:
                # MFI 정보 조회
                mfi_data = get_mfi(candle_datas)
                indicator_data['MFI'] = mfi_data
 
            if 'MACD' in indi_type:
                # MACD 정보 조회
                macd_data = get_macd(candle_datas, loop_cnt)
                indicator_data['MACD'] = macd_data
 
            if 'BB' in indi_type:
                # BB 정보 조회
                bb_data = get_bb(candle_datas)
                indicator_data['BB'] = bb_data
 
            if 'WILLIAMS' in indi_type:
                # WILLIAMS %R 조회
                williams_data = get_williams(candle_datas)
                indicator_data['WILLIAMS'] = williams_data
 
            if 'MA' in indi_type:
                # MA 정보 조회
                ma_data = get_ma(candle_datas, loop_cnt)
                indicator_data['MA'] = ma_data
 
            if 'CCI' in indi_type:
                # CCI 정보 조회
                cci_data = get_cci(candle_data, loop_cnt)
                indicator_data['CCI'] = cci_data
 
            if 'CANDLE' in indi_type:
                indicator_data['CANDLE'] = candle_data
 
        return indicator_data
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : send_msg
# - Desc : 메세지 전송
# - Input
#   1) sent_list : 메세지 발송 내역
#   2) key : 메세지 키
#   3) contents : 메세지 내용
#   4) msg_intval : 메세지 발송주기
# - Output
#   1) sent_list : 메세지 발송 내역
# -----------------------------------------------------------------------------
def send_msg(sent_list, key, contents, msg_intval):
    try:
 
        # msg_intval = 'N' 이면 메세지 발송하지 않음
        if msg_intval.upper() != 'N':
 
            # 발송여부 체크
            sent_yn = False
 
            # 발송이력
            sent_dt = ''
 
            # 발송내역에 해당 키 존재 시 발송 이력 추출
            for sent_list_for in sent_list:
                if key in sent_list_for.values():
                    sent_yn = True
                    sent_dt = datetime.strptime(sent_list_for['SENT_DT'], '%Y-%m-%d %H:%M:%S')
 
            # 기 발송 건
            if sent_yn:
 
                logging.info('기존 발송 건')
 
                # 현재 시간 추출
                current_dt = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
 
                # 시간 차이 추출
                diff = current_dt - sent_dt
 
                # 발송 시간이 지난 경우에는 메세지 발송
                if diff.seconds >= int(msg_intval):
 
                    logging.info('발송 주기 도래 건으로 메시지 발송 처리!')
 
                    # 메세지 발송
                    send_line_message(contents)
 
                    # 기존 메시지 발송이력 삭제
                    for sent_list_for in sent_list[:]:
                        if key in sent_list_for.values():
                            sent_list.remove(sent_list_for)
 
                    # 새로운 발송이력 추가
                    sent_list.append({'KEY': key, 'SENT_DT': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
 
                else:
                    logging.info('발송 주기 미 도래 건!')
 
            # 최초 발송 건
            else:
                logging.info('최초 발송 건')
 
                # 메세지 발송
                send_line_message(contents)
 
                # 새로운 발송이력 추가
                sent_list.append({'KEY': key, 'SENT_DT': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
 
        return sent_list
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : read_file
# - Desc : 파일 읽기
# - Input
# 1. name : 파일 명
# - Output
# 1. 파일 내용
# -----------------------------------------------------------------------------
def read_file(name):
    try:
 
        path = './conf/' + str(name) + '.txt'
 
        f = open(path, 'r')
        line = f.readline()
        f.close()
 
        logging.debug(line)
 
        contents = line
 
        return contents
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

import time
import os
import sys
import logging
import traceback
 
from decimal import Decimal
 
# 공통 모듈 Import
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module import upbit
 
 
# -----------------------------------------------------------------------------
# - Name : start_buytrade
# - Desc : 매수 로직
# - Input
# 1) buy_amt : 매수금액
# -----------------------------------------------------------------------------
def start_buytrade(buy_amt):
    try:
 
        # ----------------------------------------------------------------------
        # 반복 수행
        # ----------------------------------------------------------------------
        while True:
 
            logging.info("*********************************************************")
            logging.info("1. 로그레벨 : " + str(log_level))
            logging.info("2. 매수금액 : " + str(buy_amt))
            logging.info("*********************************************************")
 
            # -----------------------------------------------------------------
            # 전체 종목 리스트 추출
            # -----------------------------------------------------------------
            target_items = upbit.get_items('KRW', '')
 
            # -----------------------------------------------------------------
            # 종목별 체크
            # -----------------------------------------------------------------
            for target_item in target_items:
 
                rsi_val = False
                mfi_val = False
                ocl_val = False
 
                logging.info('체크중....[' + str(target_item['market']) + ']')
 
                # -------------------------------------------------------------
                # 종목별 보조지표를 조회
                # 1. 조회 기준 : 일캔들, 최근 5개 지표 조회
                # 2. 속도를 위해 원하는 지표만 조회(RSI, MFI, MACD, CANDLE)
                # -------------------------------------------------------------
                indicators = upbit.get_indicator_sel(target_item['market'], 'D', 200, 5, ['RSI', 'MFI', 'MACD', 'CANDLE'])
 
                # --------------------------------------------------------------
                # 최근 상장하여 캔들 갯수 부족으로 보조 지표를 구하기 어려운 건은 제외
                # --------------------------------------------------------------
                if 'CANDLE' not in indicators or len(indicators['CANDLE']) < 200:
                    logging.info('캔들 데이터 부족으로 데이터 산출 불가...[' + str(target_item['market']) + ']')
                    continue
 
                # --------------------------------------------------------------
                # 보조 지표 추출
                # --------------------------------------------------------------
                rsi = indicators['RSI']
                mfi = indicators['MFI']
                macd = indicators['MACD']
                candle = indicators['CANDLE']
 
                # --------------------------------------------------------------
                # 매수 로직
                # 1. RSI : 2일전 < 30미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # 2. MFI : 2일전 < 20미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # 3. MACD(OCL) : 3일전 < 0, 2일전 < 0, 1일전 < 0, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # --------------------------------------------------------------
 
                # --------------------------------------------------------------
                # RSI : 2일전 < 30미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # rsi[0]['RSI'] : 현재
                # rsi[1]['RSI'] : 1일전
                # rsi[2]['RSI'] : 2일전
                # rsi[3]['RSI'] : 3일전
                # --------------------------------------------------------------
                if (Decimal(str(rsi[0]['RSI'])) > Decimal(str(rsi[1]['RSI'])) > Decimal(str(rsi[2]['RSI']))
                        and Decimal(str(rsi[3]['RSI'])) > Decimal(str(rsi[2]['RSI']))
                        and Decimal(str(rsi[2]['RSI'])) < Decimal(str(30))):
                    rsi_val = True
 
                # --------------------------------------------------------------
                # MFI : 2일전 < 20미만, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # mfi[0]['MFI'] : 현재
                # mfi[1]['MFI'] : 1일전
                # mfi[2]['MFI'] : 2일전
                # mfi[3]['MFI'] : 3일전
                # --------------------------------------------------------------
                if (Decimal(str(mfi[0]['MFI'])) > Decimal(str(mfi[1]['MFI'])) > Decimal(str(mfi[2]['MFI']))
                        and Decimal(str(mfi[3]['MFI'])) > Decimal(str(mfi[2]['MFI']))
                        and Decimal(str(mfi[2]['MFI'])) < Decimal(str(20))):
                    mfi_val = True
 
                # --------------------------------------------------------------
                # MACD(OCL) : 3일전 < 0, 2일전 < 0, 1일전 < 0, 3일전 > 2일전, 1일전 > 2일전, 현재 > 1일전
                # macd[0]['OCL'] : 현재
                # macd[1]['OCL'] : 1일전
                # macd[2]['OCL'] : 2일전
                # macd[3]['OCL'] : 3일전
                # --------------------------------------------------------------
                if (Decimal(str(macd[0]['OCL'])) > Decimal(str(macd[1]['OCL'])) > Decimal(str(macd[2]['OCL']))
                        and Decimal(str(macd[3]['OCL'])) > Decimal(str(macd[2]['OCL']))
                        and Decimal(str(macd[1]['OCL'])) < Decimal(str(0))
                        and Decimal(str(macd[2]['OCL'])) < Decimal(str(0))
                        and Decimal(str(macd[3]['OCL'])) < Decimal(str(0))):
                    ocl_val = True
 
                # --------------------------------------------------------------
                # 매수대상 발견
                # --------------------------------------------------------------
                if rsi_val and mfi_val and ocl_val:
                    logging.info('매수대상 발견....[' + str(target_item['market']) + ']')
                    logging.info('RSI : ' + str(rsi))
                    logging.info('MFI : ' + str(mfi))
                    logging.info('MACD : ' + str(macd))
 
                    # ------------------------------------------------------------------
                    # 기매수 여부 판단
                    # ------------------------------------------------------------------
                    accounts = upbit.get_accounts('Y', 'KRW')
                    account = list(filter(lambda x: x.get('market') == target_item['market'], accounts))
 
                    # 이미 매수한 종목이면 다시 매수하지 않음
                    # sell_bot.py에서 매도 처리되면 보유 종목에서 사라지고 다시 매수 가능
                    if len(account) > 0:
                        logging.info('기 매수 종목으로 매수하지 않음....[' + str(target_item['market']) + ']')
                        continue
 
                    # ------------------------------------------------------------------
                    # 매수금액 설정
                    # 1. M : 수수료를 제외한 최대 가능 KRW 금액만큼 매수
                    # 2. 금액 : 입력한 금액만큼 매수
                    # ------------------------------------------------------------------
                    available_amt = upbit.get_krwbal()['available_krw']
 
                    if buy_amt == 'M':
                        buy_amt = available_amt
 
                    # ------------------------------------------------------------------
                    # 입력 금액이 주문 가능금액보다 작으면 종료
                    # ------------------------------------------------------------------
                    if Decimal(str(available_amt)) < Decimal(str(buy_amt)):
                        logging.info('주문 가능금액[' + str(available_amt) + ']이 입력한 주문금액[' + str(buy_amt) + '] 보다 작습니다.')
                        continue
 
                    # ------------------------------------------------------------------
                    # 최소 주문 금액(업비트 기준 5000원) 이상일 때만 매수로직 수행
                    # ------------------------------------------------------------------
                    if Decimal(str(buy_amt)) < Decimal(str(upbit.min_order_amt)):
                        logging.info('주문금액[' + str(buy_amt) + ']이 최소 주문금액[' + str(upbit.min_order_amt) + '] 보다 작습니다.')
                        continue
 
                    # ------------------------------------------------------------------
                    # 시장가 매수
                    # 실제 매수 로직은 안전을 위해 주석처리 하였습니다.
                    # 실제 매매를 원하시면 테스트를 충분히 거친 후 주석을 해제하시면 됩니다.
                    # ------------------------------------------------------------------
                    logging.info('시장가 매수 시작! [' + str(target_item['market']) + ']')
                    # rtn_buycoin_mp = upbit.buycoin_mp(target_item['market'], buy_amt)
                    logging.info('시장가 매수 종료! [' + str(target_item['market']) + ']')
                    # logging.info(rtn_buycoin_mp)
 
    # ---------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : main
# - Desc : 메인
# -----------------------------------------------------------------------------
if __name__ == '__main__':
 
    # noinspection PyBroadException
    try:
 
        # ---------------------------------------------------------------------
        # 입력 받을 변수
        #
        # 1. 로그레벨
        #   1) 레벨 값 : D:DEBUG, E:ERROR, 그 외:INFO
        #
        # 2. 매수금액
        #   1) M : 수수료를 제외한 최대 가능 금액으로 매수
        #   2) 금액 : 입력한 금액만 매수(수수료 포함)
        #
        # 3. 매수 제외종목
        #   1) 종목코드(콤마구분자) : BTC,ETH
        # ---------------------------------------------------------------------
 
        # 1. 로그레벨
        log_level = input("로그레벨(D:DEBUG, E:ERROR, 그 외:INFO) : ").upper()
        buy_amt = input("매수금액(M:최대, 10000:1만원) : ").upper()
 
        upbit.set_loglevel(log_level)
 
        logging.info("*********************************************************")
        logging.info("1. 로그레벨 : " + str(log_level))
        logging.info("2. 매수금액 : " + str(buy_amt))
        logging.info("*********************************************************")
 
        # 매수 로직 시작
        start_buytrade(buy_amt)
 
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)
 
    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)

import time
import os
import sys
import logging
import traceback
import pandas as pd
import numpy
import dateutil.parser
 
from decimal import Decimal
from datetime import datetime
 
# 공통 모듈 Import
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from module import upbit
 
 
# -----------------------------------------------------------------------------
# - Name : start_selltrade
# - Desc : 매도 로직
# - Input
# 1) sell_pcnt : 매도 수익률
# 2) dcnt_pcnt : 고점대비 하락률
# -----------------------------------------------------------------------------
def start_selltrade(sell_pcnt, dcnt_pcnt):
    try:
 
        # ----------------------------------------------------------------------
        # 반복 수행
        # ----------------------------------------------------------------------
        while True:
 
            # ------------------------------------------------------------------
            # 보유 종목조회
            # ------------------------------------------------------------------
            target_items = upbit.get_accounts('Y', 'KRW')
 
            # ------------------------------------------------------------------
            # 보유 종목 현재가 조회
            # ------------------------------------------------------------------
            target_items_comma = upbit.chg_account_to_comma(target_items)
            tickers = upbit.get_ticker(target_items_comma)
 
            # -----------------------------------------------------------------
            # 보유 종목별 진행
            # -----------------------------------------------------------------
            for target_item in target_items:
                for ticker in tickers:
                    if target_item['market'] == ticker['market']:
 
                        # -------------------------------------------------
                        # 고점을 계산하기 위해 최근 매수일시 조회
                        # 1. 해당 종목에 대한 거래 조회(done, cancel)
                        # 2. 거래일시를 최근순으로 정렬
                        # 3. 매수 거래만 필터링
                        # 4. 가장 최근 거래일자부터 현재까지 고점을 조회
                        # -------------------------------------------------
                        order_done = upbit.get_order_status(target_item['market'], 'done') + upbit.get_order_status(target_item['market'], 'cancel')
                        order_done_sorted = upbit.orderby_dict(order_done, 'created_at', True)
                        order_done_filtered = upbit.filter_dict(order_done_sorted, 'side', 'bid')
 
                        # -------------------------------------------------
                        # 매수 직후 나타나는 오류 체크용 마지막 매수 시간 차이 계산
                        # -------------------------------------------------
                        # 마지막 매수 시간
                        last_buy_dt = datetime.strptime(dateutil.parser.parse(order_done_filtered[0]['created_at']).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
 
                        # 현재 시간 추출
                        current_dt = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
 
                        # 시간 차이 추출
                        diff = current_dt - last_buy_dt
 
                        # 매수 후 1분간은 진행하지 않음(업비트 오류 방지 용)
                        if diff.seconds < 60:
                            logging.info('- 매수 직후 발생하는 오류를 방지하기 위해 진행하지 않음!!!')
                            logging.info('------------------------------------------------------')
                            continue
 
                        # -----------------------------------------------------
                        # 수익률 계산
                        # ((현재가 - 평균매수가) / 평균매수가) * 100
                        # -----------------------------------------------------
                        rev_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(target_item['avg_buy_price']))) / Decimal(str(target_item['avg_buy_price']))) * 100, 2)
 
                        logging.info('')
                        logging.info('------------------------------------------------------')
                        logging.info('- 종목:' + str(target_item['market']))
                        logging.info('- 평균매수가:' + str(target_item['avg_buy_price']))
                        logging.info('- 현재가:' + str(ticker['trade_price']))
                        logging.info('- 수익률:' + str(rev_pcnt))
 
                        # -----------------------------------------------------
                        # 현재 수익률이 매도 수익률 이상인 경우에만 진행
                        # -----------------------------------------------------
                        if Decimal(str(rev_pcnt)) < Decimal(str(sell_pcnt)):
                            logging.info('- 현재 수익률이 매도 수익률 보다 낮아 진행하지 않음!!!')
                            logging.info('------------------------------------------------------')
                            continue
 
                        # ------------------------------------------------------------------
                        # 캔들 조회
                        # ------------------------------------------------------------------
                        candles = upbit.get_candle(target_item['market'], '60', 200)
 
                        # ------------------------------------------------------------------
                        # 최근 매수일자 다음날부터 현재까지의 최고가를 계산
                        # ------------------------------------------------------------------
                        df = pd.DataFrame(candles)
                        mask = df['candle_date_time_kst'] > order_done_filtered[0]['created_at']
                        filtered_df = df.loc[mask]
                        highest_high_price = numpy.max(filtered_df['high_price'])
 
                        # -----------------------------------------------------
                        # 고점대비 하락률
                        # ((현재가 - 최고가) / 최고가) * 100
                        # -----------------------------------------------------
                        cur_dcnt_pcnt = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(highest_high_price))) / Decimal(str(highest_high_price))) * 100, 2)
 
                        logging.info('- 매수 후 최고가:' + str(highest_high_price))
                        logging.info('- 고점대비 하락률:' + str(cur_dcnt_pcnt))
                        logging.info('- 최종 매수시간:' + str(last_buy_dt))
                        
                        if Decimal(str(cur_dcnt_pcnt)) < Decimal(str(dcnt_pcnt)):
                                
                            # ------------------------------------------------------------------
                            # 시장가 매도
                            # 실제 매도 로직은 안전을 위해 주석처리 하였습니다.
                            # 실제 매매를 원하시면 테스트를 충분히 거친 후 주석을 해제하시면 됩니다.
                            # ------------------------------------------------------------------
                            logging.info('시장가 매도 시작! [' + str(target_item['market']) + ']')
                            #rtn_sellcoin_mp = upbit.sellcoin_mp(target_item['market'], 'Y')
                            logging.info('시장가 매도 종료! [' + str(target_item['market']) + ']')
                            #logging.info(rtn_sellcoin_mp)
                            logging.info('------------------------------------------------------')
 
                        else:
                            logging.info('- 고점 대비 하락률 조건에 맞지 않아 매도하지 않음!!!')
                            logging.info('------------------------------------------------------')
 
 
    # ---------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : main
# - Desc : 메인
# -----------------------------------------------------------------------------
if __name__ == '__main__':
 
    # noinspection PyBroadException
    try:
 
        # ---------------------------------------------------------------------
        # 입력 받을 변수
        #
        # 1. 로그레벨
        #   1) 레벨 값 : D:DEBUG, E:ERROR, 그 외:INFO
        #
        # 2. 매도 수익률
        #   1) 2% = 2로 입력
        #
        # 3. 고점대비 하락률
        #   1) 1% = 1로 입력
        # ---------------------------------------------------------------------
 
        # 1. 로그레벨
        log_level = input("로그레벨(D:DEBUG, E:ERROR, 그 외:INFO) : ").upper()
        sell_pcnt = input("매도 수익률(ex:2%=2) : ")
        dcnt_pcnt = input("고점대비 하락률(ex:-1%=-1) : ")
 
        upbit.set_loglevel(log_level)
 
        logging.info("*********************************************************")
        logging.info("1. 로그레벨 : " + str(log_level))
        logging.info("2. 매도 수익률 : " + str(sell_pcnt))
        logging.info("3. 고점대비 하락률 : " + str(dcnt_pcnt))
        logging.info("*********************************************************")
 
        # 매수 로직 시작
        start_selltrade(sell_pcnt, dcnt_pcnt)
 
 
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)
 
    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)

 
import sys
import logging
import traceback
import time
 
from module import upbit
from datetime import datetime
from decimal import Decimal
 
# -----------------------------------------------------------------------------
# - Name : start_mon
# - Desc : 모니터링 로직
# - Input
# - Output
# -----------------------------------------------------------------------------
def start_monitoring():
    try:
 
        # 프로그램 시작 메세지 발송
        message = '\n\n[프로그램 시작 안내]'
        message = message + '\n\n잔고 모니터링 프로그램이 시작 되었습니다!'
        message = message + '\n\n- 현재시간:' + str(datetime.today().strftime('%Y-%m-%d %H:%M:%S'))
 
        # 프로그램 시작 메세지 발송
        upbit.send_line_message(message)
 
        # ---------------------------------------------------------------------
        # 알림 발송 용 변수
        # ---------------------------------------------------------------------
        sent_list = []
        # ---------------------------------------------------------------------
 
        # 반복 조회
        while True:
 
            # -----------------------------------------------------------------
            # 잔고 계산용 변수
            # -----------------------------------------------------------------
            cur_price_sum = 0  # 현재 가격(전체 합계용)
            avg_buy_price_sum = 0  # 매수 금액(전체 합계용)
            # -----------------------------------------------------------------
 
            # 보유 종목 잔고 조회
            accounts = upbit.get_accounts('Y', 'KRW')
 
            # 보유 종목이 없으면 진행하지 않음
            if len(accounts) <= 0:
                logging.info('보유잔고 없음!')
                time.sleep(1)
                continue
 
            # 보유 종목 현재 가격 조회
            accounts_comma = upbit.chg_account_to_comma(accounts)
            tickers = upbit.get_ticker(accounts_comma)
 
            # 종목별 진행
            for account in accounts:
                for ticker in tickers:
                    if account['market'] == ticker['market']:
 
                        # -------------------------------------------------------------
                        # 개별 변동률 계산
                        # -------------------------------------------------------------
                        chg_rate = round(((Decimal(str(ticker['trade_price'])) - Decimal(str(account['avg_buy_price']))) / Decimal(str(account['avg_buy_price']))) * Decimal(str(100)), 2)
 
                        # 개별 종목 10% 이상 상승 시 메세지 발송(1시간 간격)
                        if Decimal(str(chg_rate)) >= Decimal(str(10)):
                            logging.info("PCNT-UP 조건 만족![" + str(account['market']) + "]")
                            logging.info("변동률:[" + str(chg_rate) + "]")
 
                            # 알림 Key 조립
                            msg_key = {'TYPE': 'PCNT-UP', 'ITEM': account['market']}
 
                            # 메세지 조립
                            message = '\n\n[보유종목 상승안내!]'
                            message = message + '\n\n- 대상종목:' + str(account['market'])
                            message = message + '\n- 현재가:' + str(ticker['trade_price'])
                            message = message + '\n- 변동률:' + str(chg_rate)
 
                            # 메세지 발송(1시간:3600초 간격)
                            sent_list = upbit.send_msg(sent_list, msg_key, message, '3600')
 
                        # 개별 종목 10% 이상 하락 시 메세지 발송(1시간 간격)
                        if Decimal(str(chg_rate)) <= Decimal(str(-10)):
                            logging.info("PCNT-DOWN 조건 만족![" + str(account['market']) + "]")
                            logging.info("변동률:[" + str(chg_rate) + "]")
 
                            # 알림 Key 조립
                            msg_key = {'TYPE': 'PCNT-DOWN', 'ITEM': account['market']}
 
                            # 메세지 조립
                            message = '\n\n[보유종목 하락안내!]'
                            message = message + '\n\n- 대상종목:' + str(account['market'])
                            message = message + '\n- 현재가:' + str(ticker['trade_price'])
                            message = message + '\n- 변동률:' + str(chg_rate)
 
                            # 메세지 발송(1시간:3600초 간격)
                            sent_list = upbit.send_msg(sent_list, msg_key, message, '3600')
 
                        # -------------------------------------------------------------
                        # 전체 수익률 계산
                        # -------------------------------------------------------------
                        # 현재가격 합계(평가금액)
                        cur_price_sum = Decimal(str(cur_price_sum)) + (Decimal(str(ticker['trade_price'])) * Decimal(str(account['balance'])))
 
                        # 매수금액 합계
                        avg_buy_price_sum = Decimal(str(avg_buy_price_sum)) + (Decimal(str(account['avg_buy_price'])) * Decimal(str(account['balance'])))
 
            # 전체 수익률
            overall_amt = cur_price_sum - avg_buy_price_sum
            overall_revenue = round(((cur_price_sum - avg_buy_price_sum) / avg_buy_price_sum) * Decimal(str(100)), 2)
 
            logging.info('')
            logging.info('전체 매수금액:' + '{:0,.0f}'.format(round(avg_buy_price_sum, 0)) + '원')
            logging.info('전체 평가금액:' + '{:0,.0f}'.format(round(cur_price_sum, 0)) + '원')
            logging.info('전체 변동금액:' + '{:0,.0f}'.format(round(overall_amt, 0)) + '원')
            logging.info('전체 수익률:' + str(overall_revenue) + '%')
            logging.info('')
 
            # 전체 자산 5%이상 상승 시 메세지 발송
            if Decimal(str(overall_revenue)) >= Decimal(str(5)):
                logging.info("OVERALL-PCNT-UP 조건 만족!")
 
                # 알림 Key 조립
                msg_key = {'TYPE': 'OVERALL-PCNT-UP', 'ITEM': 'OVERALL'}
 
                # 메세지 조립
                message = '\n\n[전체 자산 상승안내]'
                message = message + '\n\n- 전체 매수금액:' + '{:0,.0f}'.format(round(avg_buy_price_sum, 0)) + '원'
                message = message + '\n- 전체 평가금액:' + '{:0,.0f}'.format(round(cur_price_sum, 0)) + '원'
                message = message + '\n- 전체 변동금액:' + '{:0,.0f}'.format(round(overall_amt, 0)) + '원'
                message = message + '\n- 전체 수익률:' + str(overall_revenue) + '%'
 
                # 메세지 발송(1시간:3600초 간격)
                sent_list = upbit.send_msg(sent_list, msg_key, message, '3600')
 
            # 전체 자산 5%이상 하락 시 메세지 발송
            if Decimal(str(overall_revenue)) <= Decimal(str(-5)):
                logging.info("OVERALL-PCNT-DOWN 조건 만족!")
 
                # 알림 Key 조립
                msg_key = {'TYPE': 'OVERALL-PCNT-DOWN', 'ITEM': 'OVERALL'}
 
                # 메세지 조립
                message = '\n\n[전체 자산하락안내]'
                message = message + '\n\n- 전체 매수금액:' + '{:0,.0f}'.format(round(avg_buy_price_sum, 0)) + '원'
                message = message + '\n- 전체 평가금액:' + '{:0,.0f}'.format(round(cur_price_sum, 0)) + '원'
                message = message + '\n- 전체 변동금액:' + '{:0,.0f}'.format(round(overall_amt, 0)) + '원'
                message = message + '\n- 전체 수익률:' + str(overall_revenue) + '%'
 
                # 메세지 발송(1시간:3600초 간격)
                sent_list = upbit.send_msg(sent_list, msg_key, message, '3600')
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise
 
 
# -----------------------------------------------------------------------------
# - Name : main
# - Desc : 메인
# -----------------------------------------------------------------------------
if __name__ == '__main__':
 
    # noinspection PyBroadException
    try:
        # 로그레벨 설정(DEBUG)
        upbit.set_loglevel('I')
 
        # 모니터링 프로그램 시작
        start_monitoring()
 
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-100)
 
    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(-200)       