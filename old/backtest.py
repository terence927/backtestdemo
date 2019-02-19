# -*- coding: utf-8 -*-
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
import pandas as pd
import math


myclient = pymongo.MongoClient("mongodb://0.tcp.ngrok.io:10139")
mydb = myclient["5sec_DB"] 
mycol = mydb["HSI"]
mytarget = mydb["58905"]
nxttarget = mydb["57000"]
data = pd.DataFrame.from_csv('HSI.csv')
targetdata = pd.DataFrame.from_csv('58905-24.csv')
nxttargetdata = pd.DataFrame.from_csv('57000-24.csv')
nxt = 1
data = data.reindex(index=data.index[::-1])
#print (targetdata)
currentprice = 0
buyprice = 0.0
buyqty = 0.0
globalchange = 0
high =[]
low=[]
close=[]
maxchange = 0
buyfreeze = 0
sellfreeze = 0
omoney = 100000.0
money = omoney
count=0
maxqty = 0
lotratio = 1
maxqty = 420000
stopmoney = omoney
gainratio = 0.2
lossratio = -0.2
losscount = 1
highest = 0
lowest = 999999
lots = 1
buystart = 0
sellstart = 0
def get_price(): 
    global currentprice
    if nxt == 1:
        currentprice = data['close'].iloc[0]
    elif nxt == 0:
        currentprice = nxttargetdata['close'].iloc[0]
        print (currentprice)
def buy(ratio):
    global buyprice, buyfreeze, buyqty,money,count, maxchange, maxqty,currentprice
    if (buyqty + ratio )> maxqty:
        ratio = maxqty - buyqty
    else:
        count+=1
        money-=currentprice*ratio
        buyprice = (buyprice*buyqty+currentprice*ratio)/(buyqty+ratio)
        buyqty+=ratio
        if buyqty > maxqty:
            maxqty = buyqty
        total = (currentprice * buyqty) + money
        change = (total - omoney)
        if change < 0 and change < maxchange:
            maxchange = change
        print (data.index.get_level_values(0)[0], " buy at ",currentprice," x",ratio,". Total: ",total)
        buyfreeze += 5

def sell(ratio):
    global globalchange, have, maxchange, sellfreeze, buyprice, buyqty,money,count,currentprice
    if (buyqty>0):
        count+=1
        if (buyqty-ratio)> 0:
            money+=currentprice*ratio
            buyprice = (buyprice*buyqty-currentprice*ratio)/(buyqty-ratio)
            buyqty-=ratio
        else:
            ratio = buyqty
            money+=currentprice*buyqty
            buyprice = 0
            buyqty = 0
        total = (currentprice * buyqty) + money
        change = (total - omoney)
        if change < 0 and change < maxchange:
            maxchange = change
        print(data.index.get_level_values(0)[0], " sell at ",currentprice," x",ratio,". Total: ",total)
        sellfreeze += 5
        

def get5sec():
    global highest,lowest
    global high,low,close,data,targetdata,nxttargetdata
    high = np.append(high,data['high'].iloc[0])
    low = np.append(low,data['low'].iloc[0])
    close = np.append(close,data['close'].iloc[0])
    data = data.drop(data.index[0])
    targetdata = targetdata.drop(targetdata.index[0])
    nxttargetdata = nxttargetdata.drop(nxttargetdata.index[0])
    if data['high'].iloc[0] > highest:
        highest = data['high'].iloc[0]
    if data['low'].iloc[0] > lowest:
        lowest = data['low'].iloc[0]        
    #make_order('00700',price) #thread
def changetarget():
    global gainratio,lossratio,nxt
    if nxt == 1:
        nxt == 0
    elif nxt == 0:
        nxt == 1
    gainratio = 0.02
    lossratio = -0.02

def strategy():
    global buyfreeze,sellfreeze,stopmoney,gainratio,lossratio,highest,lowest,losscount,buystart,sellstart
    period = 8
    std0 = np.std(close[-period-1:-1])
    std1 = np.std(close[-period:])
    if std1 == 0:
        std1 = 1
    volatility = (std1 - std0) / std1
    if volatility < 0.1:
        volatility = 0.1
    

    fast_ma = talib.MA(close,period)
    middle_ma = talib.MA(close,1.5*period)
    slow_ma = talib.MA(close,5*period)

    period = int(period * (1 + volatility))

    adxr = talib.ADXR(high,low,close,period)
    pdi = talib.PLUS_DI(high,low,close,period)
    mdi = talib.MINUS_DI(high,low,close,period)

    myatr = talib.ATR(high,low,close,60)[-1]
    #sar = talib.SAR(high,low,acceleration=1, maximum=10)[-1]
    #print(highest,myatr)
    #print(adxr[-1])
    #print(data['time'].iloc[0])
    t = pd.to_datetime(str(data.index.get_level_values(0)[0]))
    time = t.strftime('%H:%M:%S')
    sellthird =0
    sellsec = 0
    sellall = 0
    if  (time >= '15:00:00' and time <'15:10:00'):
        sellthird = 1
    if  (time >= '15:10:00' and time <'15:40:00'):
        sellsec = 1
    if  (time >= '15:40:00' and time <'16:00:00'):
        sellall = 1
    if lossratio >= 0:
        print("change target:", buyqty)
        a = int(buyqty/12000)*lots
        sell(buyqty)
        stopmoney = (currentprice * buyqty) + money
        #changetarget()
        if (data['close'].iloc[0] >= highest - 0.1*myatr*(1+gainratio)*(1+gainratio)):
            lossratio = -0.2
        else:
            return None
    if (data['close'].iloc[0] <= highest - 7*myatr*(1+lossratio)*(1+lossratio)) and buyqty>0:
        print("&&&&&&&&&&&&&&&&&stop loss",myatr,data['close'].iloc[0],highest)
        lossratio += 0.05
        gainratio = 0.2
        a = int(buyqty/12000)*lots
        sell(buyqty)
        highest = 0
        buystart = 0
        sellstart =0
        return None
    elif (data['close'].iloc[0] >= highest - 0.1*myatr*(1+gainratio)*(1+gainratio)) and buyqty>0:
        print("=================stop gain",myatr,data['close'].iloc[0],highest)
        gainratio += 0.1
        lossratio = -0.2
        a = int(buyqty/12000)*lots
        sell(buyqty)
        lowest = 999999
        buystart = 0
        sellstart =0
        return None
    elif sellfreeze == 2 and sellstart == 1:
        x = int(lotratio*((pdi[-1]-mdi[-1])/10)*(1+sellthird)*(1+sellsec))+(50*sellall)
        if x>0:
            sell(5*lots)
        sellfreeze=0
        sellstart =0
    elif buyfreeze ==  2 and buystart == 1:
        x = int(lotratio*(mdi[-1]-pdi[-1])/10*(1-sellsec)*(1-sellall))
        if x > 0:
            buy(5*lots)
        buyfreeze=0
        buystart =0
    elif adxr[-1]>=30 and pdi[-1]>mdi[-1] and fast_ma[-1]>middle_ma[-1]>=slow_ma[-1]:
        if sellstart == 0:
            sellfreeze += 1
            sellstart = 1
    elif adxr[-1]>=30 and mdi[-1]>pdi[-1] and fast_ma[-1]<middle_ma[-1]<=slow_ma[-1]:
        if buystart == 0:
            buyfreeze += 1
            buystart = 1
    elif buystart == 1:
        buyfreeze += 1
    elif sellstart == 1:
        sellfreeze += 1
        #print(myatr)
        #stopmoney = (currentprice * buyqty) + money
        #highest = data['high'].iloc[0]
        #lossratio = lossratio + losscount*losscount*0.001

        #lossratio +=0.005
    """
    elif ((currentprice * buyqty) + money - stopmoney) / stopmoney>= 10000000:
        print("stop gain : ", buyqty)
        a = int(buyqty/12000)*lots
        sell(buyqty)
        stopmoney = (currentprice * buyqty) + money
        gainratio +=0.008       #greater risk at wave
        losscount = 0
        #lossratio -=0.001
    elif ((currentprice * buyqty) + money - stopmoney) / stopmoney < 100000000:
        print("stop loss : ", buyqty)
        a = int(buyqty/12000)*lots
        sell(buyqty)
        stopmoney = (currentprice * buyqty) + money
        lossratio +=0.005
        #gainratio -=0.002
    """

    #if buyfreeze>0:
        #buyfreeze -= 1
    #if sellfreeze>0:
        #sellfreeze -= 1

def restart():
        global gainratio,lossratio,buyqty,gain
        gainratio = gainconstant
        lossratio = lossconstant
        buyqty = 0
        gain = 0
if __name__ == "__main__":
    i=0
    while (i<3350):
        get_price()
        get5sec()
        i+=1 
        if (i>66):
            strategy()
            high = np.delete(high,[0])
            low = np.delete(low,[0])
            close = np.delete(close,[0])
        else:
            print("sample size:",i)
    print ("Total gain: ",(currentprice * buyqty) + money - omoney)
    print ("Max change: ",maxchange)
    print ("count: ", count)
    print ("still have: ", buyqty)
    print ("maxqty: ",maxqty)
    print ("money: ", money)