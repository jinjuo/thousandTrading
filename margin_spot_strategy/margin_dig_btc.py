#作者：千千量化
#高频交易程序，历史业绩最高一天80%，最低一天20%，最大回撤5%，平均3天翻一倍
#原理比较简单，现在已经不赚了，千万不要盲目实盘去跑，原因就不说了，免费开源，有兴趣看看
#这个策略实盘的时候是加了现货杠杆，10个账号，4个币对，总共40个机器人在20台服务器上运行，另外还有一个风控监控程序独立运行
from fcoin3 import Fcoin
import ccxt
import time
import logging
import threading
import random

class MyThread(threading.Thread):
    def __init__(self, func, args=()):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result 
        except:
            return {'asks':[[0, 0]],'bids':[[0, 0]]}


# super params
SYMBOL = 'BTC/USDT'
symbol = 'btcusdt'
price_increment = 0.1
level = 10
ratio = 10
interval = 0.2
s_amount = 0.02
min_amount = 0.005

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] %(message)s')
handler = logging.FileHandler("btc_%s.txt" % time.strftime("%Y-%m-%d %H-%M-%S"))
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(console)
logger.addHandler(handler)

f = open('accounts.txt')
lines = f.readlines()
acct_id = int(lines[-1])
api_key = lines[acct_id*2 - 2].strip('\n')
seceret_key = lines[acct_id*2 - 1].strip('\n')
fcoin = Fcoin()
fcoin.auth(api_key, seceret_key)  # fcoin.margin_buy('ethusdt', 0.01, 10)
ex0 = ccxt.fcoin()
ex1 = ccxt.okex3()
ex2 = ccxt.binance()
ex3 = ccxt.huobipro()
type = 'limit'
pre_trend = 0
pre_price_1 = 0
pre_price_2 = 0
pre_price_3 = 0
pre_price_4 = 0
pre_price_5 = 0
buy_id = []
sell_id = []
loop = 0
while True:
    try:
        amount = s_amount + random.randint(0, 99) / 100000
        # cancel order
        for id in buy_id: 
            try:
                result = fcoin.cancel_order(id)
                if result == None:logger.info('closing')
                if result['status'] == 0:logger.info('canceled')
            except:
                pass
        for id in sell_id:
            try:
                result = fcoin.cancel_order(id)
                if result == None:logger.info('closing')
                if result['status'] == 0:logger.info('canceled')
            except:
                pass
        buy_id = []
        sell_id = []

        # fetch orderbook
        t = []
        result = []
        t.append(MyThread(ex0.fetch_order_book, args=(SYMBOL,)))
        t.append(MyThread(ex1.fetch_order_book, args=(SYMBOL,)))
        t.append(MyThread(ex2.fetch_order_book, args=(SYMBOL,)))
        t.append(MyThread(ex3.fetch_order_book, args=(SYMBOL,)))
        for i in t:
            i.setDaemon(True)
            i.start()
        for i in t:
            i.join()
            result.append(i.get_result())
        price_bid = result[0]['bids'][0][0]
        price_ask = result[0]['asks'][0][0]
        price = (price_bid + price_ask) / 2
        price_1 = (result[1]['bids'][0][0] + result[1]['asks'][0][0]) / 2
        price_2 = (result[2]['bids'][0][0] + result[2]['asks'][0][0]) / 2
        price_3 = (result[3]['bids'][0][0] + result[3]['asks'][0][0]) / 2
        bidq0, askq0 = result[0]['bids'][0][1], result[0]['asks'][0][1]
        bidq1, askq1 = result[1]['bids'][0][1], result[1]['asks'][0][1]
        bidq2, askq2 = result[2]['bids'][0][1], result[2]['asks'][0][1]
        bidq3, askq3 = result[3]['bids'][0][1], result[3]['asks'][0][1]
        # choose trend
        trend, trend1, trend2, trend3 = 0, 0, 0, 0
        if price_1 > pre_price_1 + level * price_increment: trend1 = 1
        if price_2 > pre_price_2 + level * price_increment: trend2 = 1
        if price_3 > pre_price_3 + level * price_increment: trend3 = 1
        if price_1 < pre_price_1 - level * price_increment: trend1 = -1
        if price_2 < pre_price_2 - level * price_increment: trend2 = -1
        if price_3 < pre_price_3 - level * price_increment: trend3 = -1
        trend = trend1 + trend2 + trend3
        # logger.info('***%s   ||   trend:%d    price:%4.3f   ||   trend1:%d    trend2:%d    trend3:%d' % (
        # time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), trend, price, trend1, trend2, trend3))

        # create order
        if trend > 0 and loop > 0:
            try:
                result = fcoin.margin_buy(symbol, round(price_bid + ratio * price_increment, 1), round(amount, 4))
                buy_id.append(result['data'])
                logger.info('>> buy   ' + str(price_bid) + '   ' + str(amount))
            except Exception as e:
                try:
                    # balance = fcoin.get_margin_balance()
                    # for i in balance['data']:
                    #     if i['currency']=='usdt':USDT_amount = float(i['available'])
                    #     if i['currency']=='btc':BTC_amount = float(i['available'])
                    # buy_amount =  USDT_amount/price_ask -0.00001
                    # if buy_amount > min_amount:
                    result = fcoin.margin_buy(symbol, round(price_bid + ratio * price_increment, 1), round(min_amount, 4))
                    buy_id.append(result['data'])
                    logger.info('>> buy   ' + str(price_bid) + '   ' + str(min_amount))
                except:
                    pass
        if trend < 0 and loop > 0:
            try:
                result = fcoin.margin_sell(symbol, round(price_ask - ratio * price_increment, 1), round(amount, 4))
                sell_id.append(result['data'])
                logger.info('>> sell   ' + str(price_ask) + '   ' + str(amount))
            except Exception as e:
                try:
                    # balance = fcoin.get_margin_balance()
                    # for i in balance['data']:
                    #     if i['currency']=='usdt':USDT_amount = float(i['available'])
                    #     if i['currency']=='btc':BTC_amount = float(i['available'])
                    # sell_amount =  BTC_amount -0.00001
                    # if sell_amount> min_amount:
                    result = fcoin.margin_sell(symbol, round(price_ask - ratio * price_increment, 1), round(min_amount, 4))
                    sell_id.append(result['data'])
                    logger.info('>> sell   ' + str(price_ask) + '   ' + str(min_amount))
                except:
                    pass

        # record price
        pre_price_1 = price_1
        pre_price_2 = price_2
        pre_price_3 = price_3
        pre_trend = trend

        # sleep
        time.sleep(interval)

        # 
        loop += 1

    except Exception as e:
        logger.error(e)
