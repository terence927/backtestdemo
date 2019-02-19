# -*- coding: utf-8 -*-
"""
sell check have

"""
import os
import sys
from time import sleep
import threading

sys.path.append(os.path.split(os.path.abspath(os.path.pardir))[0])

import futuquant as ft
import easyquotation

import talib
import numpy as np

import pymongo

ip = '127.0.0.1'
port = 11111
unlock_password = "123258"    
trade_env = ft.TrdEnv.SIMULATE
quotation  = easyquotation.use("hkquote") 
quote_ctx = ft.OpenQuoteContext(host=ip, port=port)
trade_ctx = ft.OpenHKTradeContext(host=ip, port=port)
high = np.array([])
low = np.array([])
close = np.array([])
currentprice = []
canceltime = 8
buyfreeze = 2
sellfreeze = 2
lot_size = 10000
maxqty = 380000     #change every day
buyqty = 0
money = 100000       #change every day
stopmoney = money
gain =0
destcode = ['HSI','58905','57000']
nexttarget = destcode[2]
target = destcode[1]
gainconstant = 0.022
lossconstant = -0.02
gainratio = gainconstant
lossratio = lossconstant

is_unlock_trade = False
is_fire_trade = False
while not is_fire_trade:
        if not is_unlock_trade:
            print("unlocking trade...")
            ret_code, ret_data = trade_ctx.unlock_trade(unlock_password)
            is_unlock_trade = (ret_code == ft.RET_OK)
            is_fire_trade = True
            if not is_unlock_trade:
                print("请求交易解锁失败：{}".format(ret_data))
                break
            break

def insertDB(code,record):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["5sec_DB"]
    mycol = mydb[code]
    mycol.insert_one(record)

def get_price(test_code):
    global currentprice
    data = quotation.real(test_code)
    currentprice = data

def buy(code,ratio):
    test_code = "HK."+code
    qty = lot_size * ratio
    if qty + buyqty > maxqty:
        qty = maxqty - buyqty
    if qty > 0:
        price = currentprice[code]['price']
        order_id = 0
        order_status = ''
        print (currentprice[code]['time'], " buy at ",price," x",ratio)
        trade_ctx = ft.OpenHKTradeContext(host=ip, port=port)
        ret_code, ret_data = trade_ctx.place_order(price=price, qty=qty, code=test_code, trd_side=ft.TrdSide.BUY,
                                                   order_type=ft.OrderType.NORMAL, trd_env=trade_env, acc_id=0)
        trade_ctx.close()
        print('下单ret={} data={}'.format(ret_code, ret_data))
        if ret_code == ft.RET_OK:
            row = ret_data.iloc[0]
            order_id = row['order_id']
            order_status = ret_data.iloc[0]['order_status']
        buyfreeze += 2
        sleep(canceltime)
        if order_status == ft.OrderStatus.FILLED_ALL:
            return True
        if order_id:
            trade_ctx = ft.OpenHKTradeContext(host=ip, port=port)
            ret_code, ret_data = trade_ctx.order_list_query(order_id=order_id, status_filter_list=[], code='',
                                                                start='', end='', trd_env=trade_env, acc_id=0)
            order_status = ret_data.iloc[0]['order_status']
            print("cancel order...")
            ret_code, ret_data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.CANCEL, order_id=order_id,
                                price=price, qty=qty, adjust_limit=0, trd_env=trade_env, acc_id=0)
            print("撤单ret={} data={}".format(ret_code, ret_data))
            trade_ctx.close()

def sell(code,ratio):
        global stopmoney
        stock_code = "HK."+code
        qty = lot_size * ratio
        if qty > buyqty:
            qty = buyqty
        price = currentprice[code]['price']
        print (currentprice[code]['time'], " sell at ",price," x",ratio)
        trade_ctx = ft.OpenHKTradeContext(host=ip, port=port)
        ret_code, ret_data = trade_ctx.place_order(price=price, qty=qty, code=stock_code,
                                          trd_side=ft.TrdSide.SELL, trd_env=trade_env, order_type=ft.OrderType.NORMAL)
        trade_ctx.close()
        order_status = ''
        order_id = 0
        if ret_code == ft.RET_OK:
            row = ret_data.iloc[0]
            order_id = row['order_id']
            order_status = ret_data.iloc[0]['order_status']
        sellfreeze += 2
        sleep(canceltime)
        if order_status == ft.OrderStatus.FILLED_ALL and qty == buyqty:
            stopmoney = gain + money
            print("stopmoney: ",stopmoney)
            return True
        if order_id:
                trade_ctx = ft.OpenHKTradeContext(host=ip, port=port)
                ret_code, ret_data = trade_ctx.order_list_query(order_id=order_id, status_filter_list=[], code='',
                                                                start='', end='', trd_env=trade_env, acc_id=0)
                order_status = ret_data.iloc[0]['order_status']
                print("cancel order...")
                ret_code, ret_data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.CANCEL, order_id=order_id,
                                price=price, qty=qty, adjust_limit=0, trd_env=trade_env, acc_id=0)
                print("撤单ret={} data={}".format(ret_code, ret_data))
                trade_ctx.close()

def get5sec(code):
    global high,low,close, buyqty, gain
    highv = -1.0
    lowv = 999999.0
    closev = 0.0
    highg = -1.0
    lowg = 999999.0
    closeg = 0.0
    trade_ctx = ft.OpenHKTradeContext(host=ip, port=port)
    ret_code, ret_data = trade_ctx.position_list_query(code=target, pl_ratio_min=None, pl_ratio_max=None, trd_env=trade_env, acc_id=0)
    trade_ctx.close()
    if (len(ret_data.index)>0):
        buyqty = ret_data.iloc[0]['qty']
        gain = ret_data.iloc[0]['today_pl_val']

    for i in range(5):
        get_price(code)
        price = currentprice['HSI']['price']
        if (price>highv):
            highv = price 
        else:
            lowv = price
        closev = price

        priceg = currentprice[code[1]]['price']
        if (priceg>highg):
            highg = priceg
        else:
            lowg = priceg
        closeg = priceg

        priceh = currentprice[code[2]]['price']
        if (priceh>highh):
            highh = priceh
        else:
            lowh = priceh
        closeh = priceh 
        sleep(0.95)
    high = np.append(high,highv)
    low = np.append(low,lowv)
    close = np.append(close,closev)
    date=currentprice['HSI']['time'].split(" ")[0]
    time=currentprice['HSI']['time'].split(" ")[1]
    #print(closev)
    insertDB(code[0],{"time":time,"high":highv,"low":lowv,"close":closev,"date":date})
    insertDB(code[1],{"time":time,"high":highg,"low":lowg,"close":closeg,"date":date})
    insertDB(code[2],{"time":time,"high":highh,"low":lowh,"close":closeh,"date":date})
    #make_order('00700',price) #thread #list code

def changetarget():
        global gainratio,lossratio,target,nexttarget,buyqty,gain
        print ("change target")
        tmp = target
        target = nexttarget
        nexttarget = tmp
        gainratio = gainconstant
        lossratio = lossconstant
        buyqty = 0
        gain = 0

def strategy(code): #single code
    global buyfreeze,sellfreeze,stopmoney,gainratio,lossratio
    if lossratio > -0.005:
        changetarget()
        return None
    period = 8
    std0 = np.std(close[-period-1:-1])
    std1 = np.std(close[-period:])
    if std1 == 0:
        std1 = 1
    volatility = (std1 - std0) / std1
    if volatility < 0.1:
        volatility = 0.1
    
    fast_ma = talib.MA(close,)
    middle_ma = talib.MA(close,1.5*period)
    slow_ma = talib.MA(close,5*period)

    period = int(period * (1 + volatility))

    adxr = talib.ADXR(high,low,close,period)
    pdi = talib.PLUS_DI(high,low,close,period)
    mdi = talib.MINUS_DI(high,low,close,period)

    time=currentprice['HSI']['time'].split(" ")[1]
    sellthird =0
    sellsec = 0
    sellall = 0
    if (time >= '15:00:00' and time <'15:10:00'):
        sellthird = 1
    if (time >= '15:10:00' and time <'15:40:00'):
        sellsec = 1
    if (time >= '15:40:00' and time <'16:00:00'):
        sellall = 1
    if adxr[-1]>=50 and pdi[-1]>mdi[-1] and fast_ma[-1]>middle_ma[-1]>=slow_ma[-1]:
        if sellfreeze<=0:
            x = int(lotratio*((pdi[-1]-mdi[-1])/10)*(1+sellthird)*(1+sellsec))+(10*sellall)
            if x>0:
                t = threading.Thread(target=sell, args=(code,x,))
                t.start()
                t.join()
    elif adxr[-1]>=50 and mdi[-1]>pdi[-1] and fast_ma[-1]<middle_ma[-1]<=slow_ma[-1]:
        if buyfreeze<=0:
            x = int(lotratio*(mdi[-1]-pdi[-1])/10*(1-sellsec)*(1-sellall))
            if x > 0:
                t = threading.Thread(target=buy, args=(code,x,))
                t.start()
                t.join()
    elif gain / stopmoney> 0.022:
        print("stop gain : ", buyqty)
        gainratio +=0.008
        t = threading.Thread(target=sell, args=(code,maxqty,))
        t.start()
        t.join()
    elif gain / stopmoney < -0.02:
        print("stop loss : ", buyqty)
        lossratio +=0.002
        t = threading.Thread(target=sell, args=(code,maxqty,))  #sell status check
        t.start()
        t.join()
    if buyfreeze>0:
        buyfreeze -= 1
    if sellfreeze>0:
        sellfreeze -= 1

if __name__ == "__main__":
    i=0
    while (12==1):
        t = threading.Thread(target=get5sec, args=(destcode,))
        t.start()
        t.join()
        i+=1
        if (i>55):
            t2 = threading.Thread(target=strategy, args=(target,))
            t2.start()
            t2.join()
            #strategy(target)
            high = np.delete(high,[0])
            low = np.delete(low,[0])
            close = np.delete(close,[0])
        else:
            print("sample size:",i)