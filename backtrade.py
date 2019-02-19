from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt
buyfreeze=0
sellfreeze=0
buysignal=0
sellsignal=0
# Create a Stratey
class TestStrategy(bt.Strategy):
    params = (
        ('maperiod', 12),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
        #print('Portfolio Value: %.2f' % cerebro.broker.getvalue(), self.position.size)

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None
        period = 15
        # Add a MovingAverageSimple indicator
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod)
        self.middle_ma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod*2)
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod*5)

        # Indicators for the plotting show
        #bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        #bt.indicators.WeightedMovingAverage(self.datas[0], period=25,subplot=True)
        #bt.indicators.StochasticSlow(self.datas[0])

        #bt.indicators.MACDHisto(self.datas[0])
        self.rsi = bt.indicators.RSI(self.datas[0])
        self.adxr = bt.talib.ADXR(self.data.high, self.data.low, self.data.close,
                          timeperiod=period)
        self.pdi = bt.talib.PLUS_DI(self.data.high, self.data.low, self.data.close,
                          timeperiod=period)
        self.mdi = bt.talib.MINUS_DI(self.data.high, self.data.low, self.data.close,
                          timeperiod=period)
        #bt.indicators.SmoothedMovingAverage(rsi, period=10)
        #bt.indicators.ATR(self.datas[0], plot=False)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        global buysignal,sellsignal,buyfreeze,sellfreeze
        # Simply log the closing price of the series from the reference
        #self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one

        # Check if we are in the market
        #if not self.position:
        if buyfreeze>0:
            buyfreeze-=1
        if sellfreeze>0:
            sellfreeze-=1
        if self.order:
            return

            # Not yet ... we MIGHT BUY if ...
        if self.adxr>=28 and self.pdi<self.mdi and self.fast_ma<self.middle_ma<=self.slow_ma:
            if buyfreeze==0:
                # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                lots = int((self.mdi-self.pdi)/10)
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy(size=lots)
                buyfreeze=10

        #else:

        if self.adxr>=36 and self.pdi>self.mdi and self.fast_ma>self.middle_ma>=self.slow_ma:
            if sellfreeze==0:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                lots = int((self.pdi-self.mdi)/10)
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell(size=lots*2)
                sellfreeze=10


if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'datas/HSI.txt')

    # Create a Data Feed
    data = bt.feeds.GenericCSVData(
    dataname=datapath,

    fromdate=datetime.datetime(2000, 1, 1),
    todate=datetime.datetime(2016, 12, 31),

    nullvalue=0.0,

    dtformat=('%Y-%m-%d'),

    datetime=0,
    high=2,
    low=3,
    open=1,
    close=4,
    volume=5,
    openinterest=-1
	)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(1000000)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)

    # Set the commission
    cerebro.broker.setcommission(commission=0.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name = 'SharpeRatio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')
    # Run over everything
    results = cerebro.run()
    strat = results[0]
    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    print('SR:', strat.analyzers.SharpeRatio.get_analysis())
    print('DW:', strat.analyzers.DW.get_analysis())
    # Plot the result
    cerebro.plot()