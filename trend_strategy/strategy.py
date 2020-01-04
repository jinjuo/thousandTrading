# 从二次封装的okex API接口导入相关类
# 也可以替换成其他交易所的接口，比如：huobi、binance、bitmex等等
import okex.spot_api as spot
import okex.swap_api as swap
import okex.futures_api as future
import okex.account_api as account
# 导入日志记录模块
import logging
# 导入时间记录模块
import time
# 导入数学计算模块
import math
# 导入科学计算模块
import numpy
# 导入json格式模块
import json
# 导入talib指标计算模块
import talib
# 导入pandas科学计算模块
import pandas
# 导入smtp邮箱协议模块
import smtplib
from email.mime.text import MIMEText
from email.header import Header
# 导入网络请求模块 钉钉报警
import requests

# 策略主类
class strategy():
    # 实例化类的时候 会执行以下代码
    def __init__(self, name,api_key,seceret_key,passphrase,instrument_id,mode,granularity,leverate):
        self.version = "version：1.1.3"
        self.name = name
        self.api_key = api_key
        self.seceret_key = seceret_key
        self.passphrase = passphrase
        self.instrument_id =instrument_id
        self.mode = mode
        self.total_coin = ''
        self.ding_time = 0
        self.long_rate_history = []
        self.short_rate_history = []
        self.take_limit = 10
        self.one_hand = 1
        self.win_cut = 0.2
        self.loss_cut = -0.1
        self.drawback_cut = 0.5
        self.kd, self.kk, self.pd, self.pk = 0, 0, 0, 0
        self.leverate = leverate
        self.granularity = granularity
        self.mail_time = 0
        self.jump_mode = 'None'
        self.jump_price = 0

    # 启动日志记录
    def InitLog(self):
        level = logging.INFO
        self.log = logging.getLogger(__name__)
        self.log.setLevel(level)
        handler = logging.FileHandler("运行日志%s.txt" %time.strftime("%Y-%m-%d %H-%M-%S"))
        handler.setLevel(level)
        formatter = logging.Formatter('[%(asctime)s] %(message)s')
        handler.setFormatter(formatter)
        console = logging.StreamHandler()
        console.setLevel(level)
        self.log.addHandler(handler)
        self.log.addHandler(console)
        self.PrintConfig()
    
    # 钉钉报警方法
    def dingmessage(self, msg, at_all):
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=9c1cf30275ac4fe57b41c05263a56c800aeec5ba4efe589737321a6af28c4f08'
        header = {
            "Content-Type": "application/json",
            "Charset": "UTF-8"
        }
        tex = '>' + msg
        message ={

            "msgtype": "text",
            "text": {
                "content": tex
            },
            "at": {

                "isAtAll": at_all
            }

        }
        message_json = json.dumps(message)
        info = requests.post(url=webhook,data=message_json,headers=header)
        print(info.text)

    # 打印当前策略参数
    def PrintConfig(self):
        self.dingmessage('启动程序：'+self.name, False)
        self.log.info('启动程序：'+self.name)
        self.log.info("版本：%s" % self.version)
        self.log.info("当前模式：%s" % self.mode)
        self.log.info("最大持仓量：%s" % self.take_limit)
        self.log.info("K线类别：%s" % self.granularity)
        self.log.info("单次开仓数量：%s" % self.one_hand)
        self.log.info("止盈比例：%s" % self.win_cut)
        self.log.info("止损比例:%s" % self.loss_cut)

    # 实例化交易所API接口
    def LogIn(self):
        # self.spot = spot.SpotAPI(self.api_key, self.seceret_key, self.passphrase, True)
        self.swap = swap.SwapAPI(self.api_key, self.seceret_key, self.passphrase, True)
        # self.future = future.FutureAPI(self.api_key, self.seceret_key, self.passphrase, True)

    # 盘前准备
    def BeforeTrade(self):
        pass

    # 计算指标
    def GetTaLib(self):
        # sar
        self.sar = talib.SAR(self.high, self.low, acceleration=0.05, maximum=0.2)
        # boll
        self.upper, self.middle, self.lower = talib.BBANDS(self.close, timeperiod=200, nbdevup=2, nbdevdn=2, matype=talib.MA_Type.SMA)
        # self.log.info([round(self.upper[-1],4), round(self.middle[-1],4), round(self.lower[-1],4)])
        # macd
        self.macd, self.macd_signal, self.macd_hist = talib.MACD(self.close, fastperiod=12, slowperiod=26, signalperiod=9)
        # self.log.info([self.macd[-1], self.macd_signal[-1], self.macd_hist[-1]])
        # rsi
        self.rsi6 = talib.RSI(self.close,6)
        self.rsi12 = talib.RSI(self.close,12)
        self.rsi24 = talib.RSI(self.close,24)
        # ema
        self.emafast = talib.EMA(self.close,12)
        self.emaslow = talib.EMA(self.close,24)
        # atr up-> vol high
        self.atr = talib.ATR(self.high,self.low,self.close, timeperiod=14)
        # DC up -> up
        N1 = 10
        N2 = 10
        # self.DC_kd = max(numpy.max(self.open[-N1:-2]), numpy.max(self.close[-N1:-2]))
        # self.DC_kk = min(numpy.min(self.open[-N1:-2]), numpy.min(self.close[-N1:-2]))
        # self.DC_pd = min(numpy.min(self.open[-N2:-2]), numpy.min(self.close[-N2:-2]))
        # self.DC_pk = max(numpy.max(self.open[-N2:-2]), numpy.max(self.close[-N2:-2]))

        self.DC_kd = numpy.max(self.high[-N1:-2])
        self.DC_kk = numpy.min(self.low[-N1:-2])
        self.DC_pd = numpy.min(self.low[-N2:-2])
        self.DC_pk = numpy.max(self.high[-N2:-2])
        # adx up -> trend high
        self.ADX = talib.ADX(self.high, self.low, self.close, timeperiod=14)
        # emv up->up low->low
        a = pandas.DataFrame((self.high + self.low) / 2)
        b = a.shift(1)
        c = pandas.DataFrame(self.high - self.low)
        vol = pandas.DataFrame(self.vol)
        em = (a - b) * c / vol * 1000000
        emv = em.rolling(14).sum()
        self.emv = emv._values
        self.maemv = emv.rolling(9).mean()._values
        # cci
        self.cci = talib.CCI(self.high, self.low, self.close, timeperiod=14)

    # 获取K线
    def GetKline(self):
        kline = self.swap.get_kline(self.instrument_id, granularity=self.granularity, start='', end='')
        # get close high  low vol
        kline = numpy.array(kline)
        open = kline[:, -6]
        high = kline[:, -5]
        low = kline[:, -4]
        close = kline[:, -3]
        vol = kline[:, -2]
        # transpose
        open = open[::-1]
        high = high[::-1]
        low = low[::-1]
        close = close[::-1]
        vol = vol[::-1]
        self.open = open.astype(numpy.float64)
        self.high = high.astype(numpy.float64)
        self.low = low.astype(numpy.float64)
        self.close = close.astype(numpy.float64)
        self.vol = vol.astype(numpy.float64)
        self.close_price = self.close[-1]
        self.log.info("最新价格： %5.4f" % (self.close_price))

    # 选择指定的策略执行
    def HandleBar(self, mode):
        if "boll" in mode:self.StrategyBoll()
        if "rsi" in mode: self.StrategyRsi()
        if "dc" in mode:self.StrategyDC()
        if "sar" in mode:self.StrategySar()
        if 'cci' in mode:self.StrategyCCI()
        if 'jump' in mode:self.StrategyJump()
        if 'boll_break' in mode:self.StrategyBollBreak()

    # 检查当前风控
    def CheckRisks(self):
        # get leverage
        leverage = float(self.position['holding'][0]['leverage'])
        win_cut = self.win_cut
        loss_cut = self.loss_cut
        drawback_cut = self.drawback_cut
        long_rate = 0
        short_rate = 0
        if self.long_avg_cost:
            long_rate = ((self.close_price - self.long_avg_cost) / self.long_avg_cost) * leverage
            self.log.info("多单盈利： %5.2f %%" % round(long_rate * 100, 2))
        if self.short_avg_cost:
            short_rate = ((self.short_avg_cost - self.close_price) / self.short_avg_cost) * leverage
            self.log.info("空单盈利： %5.2f %%" % round(short_rate * 100, 2))
        if long_rate > 0:
            self.long_rate_history.append(long_rate)
            long_drawback = (max(self.long_rate_history) - long_rate) / max(self.long_rate_history)
            if long_drawback > drawback_cut and max(self.long_rate_history) > win_cut / 4:
                msg = "回撤过大，平多"
                self.log.info(msg)
                self.pd += self.one_hand
        else:
            self.long_rate_history.clear()
        if short_rate > 0:
            self.short_rate_history.append(short_rate)
            short_drawback = (max(self.short_rate_history) - short_rate) / max(self.short_rate_history)
            if short_drawback > drawback_cut and max(self.short_rate_history) > win_cut / 4:
                msg = "回撤过大，平空"
                self.log.info(msg)
                self.pk += self.one_hand
        else:
            self.short_rate_history.clear()
        # handle risks
        if long_rate < loss_cut or long_rate > win_cut:
            msg = "警告： 马上平多"
            self.dingmessage(msg, True)
            self.log.info(msg)
            self.pd += self.buy_available
        if short_rate < loss_cut or short_rate > win_cut:
            msg = "警告： 马上平空"
            self.dingmessage(msg, True)
            self.log.info(msg)
            self.pk += self.sell_available

    # 获取当前持仓
    def GetPosition(self):
        self.position = self.swap.get_specific_position(self.instrument_id)
        self.buy_amount = 0
        self.sell_amount = 0
        self.buy_available = 0
        self.sell_available = 0
        self.long_avg_cost = 0
        self.short_avg_cost = 0
        for data in self.position['holding']:
            if data['side'] == "long":
                self.buy_amount = int(data['position'])
                self.buy_available = int(data['avail_position'])
                if float(data['avg_cost'])>0:
                    self.long_avg_cost = float(data['avg_cost'])
            if data['side'] == "short":
                self.sell_amount = int(data['position'])
                self.sell_available = int(data['avail_position'])
                if float(data['avg_cost'])>0:
                    self.short_avg_cost = float(data['avg_cost'])
        self.log.info("当前持仓:  多仓/可平 %d/%d  空仓/可平 %d/%d" \
                      % (self.buy_amount,self.buy_available,self.sell_amount,self.sell_available))

    # 移动止盈
    def lottery(self):
        time.sleep(0.1)
        self.log.info('挂止盈单')
        self.GetPosition()
        if self.buy_available  >= 1 * self.one_hand:self.TakeOrders("pd", self.close_price * 1.001, self.one_hand*1, "0")
        if self.buy_available  >= 3 * self.one_hand:self.TakeOrders("pd", self.close_price * 1.002, self.one_hand*2, "0")
        if self.buy_available  >= 6 * self.one_hand:self.TakeOrders("pd", self.close_price * 1.003, self.one_hand*3, "0")
        if self.buy_available  >=10 * self.one_hand:self.TakeOrders("pd", self.close_price * 1.004, self.one_hand*4, "0")
        if self.buy_available  >=15 * self.one_hand:self.TakeOrders("pd", self.close_price * 1.005, self.one_hand*5, "0")
        if self.sell_available >= 1 * self.one_hand:self.TakeOrders("pk", self.close_price * 0.999, self.one_hand*1, "0")
        if self.sell_available >= 3 * self.one_hand:self.TakeOrders("pk", self.close_price * 0.998, self.one_hand*2, "0")
        if self.sell_available >= 6 * self.one_hand:self.TakeOrders("pk", self.close_price * 0.997, self.one_hand*3, "0")
        if self.sell_available >=10 * self.one_hand:self.TakeOrders("pk", self.close_price * 0.996, self.one_hand*4, "0")
        if self.sell_available >=15 * self.one_hand:self.TakeOrders("pk", self.close_price * 0.995, self.one_hand*5, "0")

    # 检查当前订单情况
    def check_orders(self,status):
        # get orders list
        # status:-1:remove 0:wait 1:part 2:full
        # return:orders_id
        orders_id = []
        result = self.swap.get_order_list(status, self.instrument_id, '', '', '')
        # remove orders
        if result['order_info']:
            for index in range(len(result['order_info'])):
                orders_id.append(result['order_info'][index]['order_id'])
        return orders_id

    # 撤销指定订单
    def remove_orders(self, orders_id):
        result = []
        for id in orders_id:
            result.append(self.swap.revoke_order(instrument_id=self.instrument_id, order_id=id))
        return result

    # 撤销所有订单
    def CleanOrders(self):
        orders_id = self.check_orders("1")
        self.remove_orders(orders_id)
        orders_id = self.check_orders("0")
        self.remove_orders(orders_id)

    # 处理下单信号
    def HandleOrders(self):
        self.log.info('处理下单信号：')
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        self.kd, self.kk, self.pd, self.pk = 0, 0, 0, 0
        if kd + kk + pd + pk > 0:
            self.log.info('提示： kd:%d  kk:%d  pd:%d  pk:%d'%(kd, kk, pd, pk))
        if pd > 0:kd = 0
        if pk > 0:kk = 0
        self.log.info('提示： kd:%d  kk:%d  pd:%d  pk:%d'%(kd, kk, pd, pk))
        if kd > 0:
            self.dingmessage('提示： 开仓请注意！', True)
            self.TakeOrders("kd", self.close_price, kd, "1")
        if kk > 0:
            self.dingmessage('提示： 开仓请注意！', True)
            self.TakeOrders("kk", self.close_price, kk, "1")
        if pd > 0:
            self.TakeOrders("pd", self.close_price, pd, "1")
        if pk > 0:
            self.TakeOrders("pk", self.close_price, pk, "1")
        
    # 下单函数
    def TakeOrders(self,signal,price,amount,match_price):
        result=[]
        amount = int(amount)
        try:
            if amount > 0:
                if signal == "sykd" and self.buy_amount < self.take_limit/2:
                    result = self.swap.take_order(self.instrument_id, str(amount), '1', str(price), '',match_price)
                if signal == "sykk" and self.sell_amount < self.take_limit/2:
                    result = self.swap.take_order(self.instrument_id, str(amount), '2', str(price), '',match_price)
                if signal == "kd" and self.buy_amount < self.take_limit:
                    result = self.swap.take_order(self.instrument_id, str(amount), '1', str(price), '',match_price)
                if signal == "kk" and self.sell_amount < self.take_limit:
                    result = self.swap.take_order(self.instrument_id, str(amount), '2', str(price), '',match_price)
                if signal == "pd" and self.buy_available > 0:
                    if amount <= self.buy_available: 
                        result = self.swap.take_order(self.instrument_id, str(amount), '3', str(price), '',match_price)
                    if amount > self.buy_available:
                        result = self.swap.take_order(self.instrument_id, str(self.buy_available), '3', str(price), '',match_price)
                if signal == "pk" and self.sell_available > 0:
                    if amount <= self.sell_available:
                        result = self.swap.take_order(self.instrument_id, str(amount), '4', str(price), '',match_price)
                    if amount > self.sell_available:
                        result = self.swap.take_order(self.instrument_id, str(self.sell_available), '4', str(price), '',match_price)
                if signal == "sypd" and self.buy_available > self.take_limit/2:
                    result = self.swap.take_order(self.instrument_id, str(amount), '3', str(price), '',match_price)
                if signal == "sypk" and self.sell_available > self.take_limit/2:
                    result = self.swap.take_order(self.instrument_id, str(amount), '4', str(price), '',match_price)
                self.log.info("开始下单： %s  %s张" % (signal, str(amount)))
                self.log.info(result)
        except Exception as e:
            self.log.info(e)

    # 检查K线形态
    def CheckKline(self):
        open = self.open[-2]
        close = self.close[-2]
        high = self.high[-2]
        low = self.low[-2]
        vol = self.vol[-2]
        vol_ma = self.vol[-10:-2].mean()
        amp = high - low
        amp_ma = (self.high[-10:-2] - self.low[-10:-2]).mean()
        if vol > 2 * vol_ma and amp/amp_ma > 1:
            if open > close:
                if (high - open) > (open - close) or (high - open) > 0.5:
                    self.log.info('提示： 发现长上影线')
                    self.pd += self.one_hand
                if (close - low) > (open - close) or (close - low) > 0.5:
                    self.log.info('提示： 发现长下影线')
                    self.pk += self.one_hand
            if close > open:
                if (high - close) > (close - open) or (high - close) > 0.5:
                    self.log.info('提示： 发现长上影线')
                    self.pd += self.one_hand
                if (open - low) > (close - open) or (open - low) > 0.5:
                    self.log.info('提示： 发现长下影线')
                    self.pk += self.one_hand

    def StrategyBollBreak(self):
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        upper = self.upper
        middle = self.middle
        lower = self.lower
        close = self.close
        if close[-1] > upper[-1] and close[-2] < upper[-2] and self.buy_amount == 0:
            self.kd += self.one_hand
        if close[-1] < middle[-1] and close[-2] > middle[-2] and self.buy_amount > 0:
            self.pd += self.one_hand
        if close[-1] < lower[-1] and close[-2] > lower[-2] and self.sell_amount == 0:
            self.kk += self.one_hand
        if close[-1] > middle[-1] and close[-2] < middle[-2]  and self.sell_amount > 0:
            self.pk += self.one_hand
        self.log.info('策略： BOLL BREAK  信号： kd:%d  kk:%d  pd:%d  pk:%d'%(self.kd - kd, self.kk- kk, self.pd - pd, self.pk - pk))

    # BOLL策略
    def StrategyBoll(self):
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        upper = self.upper
        middle = self.middle
        lower = self.lower
        rsi = self.rsi6
        atr = self.atr
        trend_cur = upper[-2] - lower[-2]
        trend_pre = upper[-3] - lower[-3]
        if upper[-2] > upper[-3] and middle[-2] > middle[-3] and lower[-2] < lower[-3]\
                and rsi[-2] < 70 and rsi[-2] > 50 and rsi[-2] > rsi[-3] and rsi[-1] < 80 and rsi[-1] > rsi[-2]\
                and atr[-2] > atr[-3] and trend_cur > trend_pre:
            self.kd += self.one_hand
            self.pk += self.one_hand
            if atr[-1] > atr[-2] and rsi[-1] < 60 and rsi[-1] > 50:
                self.kd += self.one_hand
        if upper[-2] > upper[-3] and middle[-2] < middle[-3] and lower[-2] < lower[-3]\
                and rsi[-2] > 30 and rsi[-2] < 50 and rsi[-2] < rsi[-3] and rsi[-1] > 20 and rsi[-1] < rsi[-2]\
                and atr[-2] > atr[-3] and trend_cur > trend_pre:
            self.kk += self.one_hand
            self.pd += self.one_hand
            if atr[-1] > atr[-2] and rsi[-1] > 40 and rsi[-1] < 50:
                self.kk += self.one_hand
        if upper[-2] < upper[-3] or lower[-2] > lower[-3]:
            if trend_cur < trend_pre and middle[-2] > middle[-3]:
                self.pk += self.one_hand
            if trend_cur < trend_pre and middle[-2] < middle[-3]:
                self.pd += self.one_hand
        self.log.info('策略： BOLL  信号： kd:%d  kk:%d  pd:%d  pk:%d'%(self.kd - kd, self.kk- kk, self.pd - pd, self.pk - pk))

    # RSI策略
    def StrategyRsi(self):
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        rsi6 = self.rsi6
        rsi24 = self.rsi24
        if rsi6[-2] > 50 and rsi6[-2] < 70 and rsi6[-2] > rsi24[-2] and rsi6[-3] < rsi24[-3]:
            self.kd += self.one_hand
        if rsi6[-2] < 50 and rsi6[-2] > 30 and rsi6[-2] < rsi24[-3] and rsi6[-3] > rsi24[-3]:
            self.kk += self.one_hand
        if rsi6[-2] > 95:
            self.pd += self.one_hand
        if rsi6[-2] < 5:
            self.pk += self.one_hand
        if rsi6[-2] > rsi24[-2] and rsi6[-3] < rsi24[-3]:
            self.pk += self.one_hand
        if rsi6[-2] < rsi24[-2] and rsi6[-3] > rsi24[-3]:
            self.pd += self.one_hand
        self.log.info('策略： RSI  信号： kd:%d  kk:%d  pd:%d  pk:%d'%(self.kd - kd, self.kk- kk, self.pd - pd, self.pk - pk))

    # CCI策略
    def StrategyCCI(self):
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        cci = self.cci
        if cci[-2] > 100 and cci[-3] < 100:
            self.pd += self.one_hand
        if cci[-2] < -100 and cci[-3] > -100:
            self.pk += self.one_hand
        if cci[-2] < 100 and cci[-3] > 100:
            self.kk += self.one_hand
        if cci[-2] > -100 and cci[-3] < -100:
            self.kd += self.one_hand
        self.log.info('策略： CCI  信号： kd:%d  kk:%d  pd:%d  pk:%d'%(self.kd - kd, self.kk- kk, self.pd - pd, self.pk - pk))

    # JUMP策略
    def StrategyJump(self):
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        step = self.close_price * 0.003
        # 正向
        if self.jump_mode == 'None':
            if self.close_price > self.high[-2]:
                # self.kd += self.one_hand
                self.jump_mode = 'long'
                self.jump_price = self.close_price
            if self.close_price < self.low[-2]:
                # self.kk += self.one_hand
                self.jump_mode = 'short'
                self.jump_price = self.close_price
        if self.jump_mode == 'long':
            if self.sell_amount > 0:self.pk += self.one_hand
            if self.close_price >= self.jump_price + step:
                self.kd += self.one_hand
                self.jump_price = self.close_price
            if self.close_price < self.jump_price - step:
                self.kk += self.one_hand
                self.pd += self.buy_amount
                self.jump_price = self.close_price
                self.jump_mode = 'short'
        if self.jump_mode == 'short':
            if self.buy_amount > 0:self.pd += self.one_hand
            if self.close_price <= self.jump_price - step:
                self.kk += self.one_hand
                self.jump_price = self.close_price
            if self.close_price > self.jump_price + step:
                self.kd += self.one_hand
                self.pk += self.sell_amount
                self.jump_price = self.close_price
                self.jump_mode = 'long'
        self.log.info('策略： JUMP  信号： kd:%d  kk:%d  pd:%d  pk:%d'%(self.kd - kd, self.kk- kk, self.pd - pd, self.pk - pk))        
        self.log.info('mode:%s  price:%f'%(self.jump_mode, self.jump_price))

    # DC通道策略
    def StrategyDC(self):
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        upp_kd = self.DC_kd
        upp_pk = self.DC_pk
        low_kk = self.DC_kk
        low_pd = self.DC_pd
        close = self.close[-1]
        # 
        if close > upp_kd:
            self.kd += self.one_hand
        if close < low_kk :
            self.kk += self.one_hand
        if close < low_pd:
            self.pd += self.one_hand
        if close > upp_pk:
            self.pk += self.one_hand
        self.log.info('策略： DC  信号： kd:%d  kk:%d  pd:%d  pk:%d'%(self.kd - kd, self.kk- kk, self.pd - pd, self.pk - pk))

    # SAR策略
    def StrategySar(self):
        kd, kk, pd, pk = self.kd, self.kk, self.pd, self.pk
        last_close = self.close[-2]
        pre_last_close = self.close[-3]
        sar = self.sar
        if last_close > sar[-2] and pre_last_close < sar[-3]:
            self.pk += self.one_hand
            self.kd += self.one_hand
        if last_close < sar[-2] and pre_last_close > sar[-3]:
            self.pd += self.one_hand
            self.kk += self.one_hand
        self.log.info('策略： SAR  信号： kd:%d  kk:%d  pd:%d  pk:%d'%(self.kd - kd, self.kk- kk, self.pd - pd, self.pk - pk))

    # 获取账号信息
    def GetAccount(self):
        result = self.swap.get_coin_account(self.instrument_id)
        if result["info"]["equity"] == "":
            self.log.warning("Can not get MyWallet!")
        else:
            self.total_coin = result["info"]["equity"]
            self.log.info("%s %s" %(self.instrument_id, self.total_coin))
            if time.time() - self.ding_time > 5 * 60:
                self.ding_time = time.time()
                self.dingmessage('%s %s'%(self.instrument_id, self.total_coin), False)

    # 策略运行主函数
    def Run(self):
        time.sleep(time.time()%int(self.granularity))
        self.LogIn()
        self.InitLog()
        # result = self.swap.set_leverage(self.instrument_id, self.leverate, "3")
        # self.log.info(result)
        while True:
            try:
                # 记录本次循环开始时间
                start_time = time.time()
                # 记录当前时间
                self.log.info("---===当前时间：%s===---" % time.strftime("%Y-%m-%d %H:%M:%S"))
                # 撤销上一轮全部挂单
                self.CleanOrders()
                # 获取账户信息
                self.GetAccount()
                # 获取仓位信息
                self.GetPosition()
                # 获取k线信息
                self.GetKline()
                # 计算技术指标
                self.GetTaLib()
                # 产生择时信号
                self.HandleBar(self.mode)
                # 检查k线形态 
                self.CheckKline()
                # 检查风控
                self.CheckRisks()
                # 处理下单信号
                self.HandleOrders()
                # 撤销全部订单 
                self.CleanOrders()
                # 刮彩票
                self.lottery()
                # 日志空行
                self.log.info(" ")
                # 记录本次循环结束时间
                end_time = time.time()
                # 计算本次循环耗费的时间
                spend_time = end_time - start_time
                # 睡眠指定时间后进入下一次循环
                time.sleep(int(self.granularity) - spend_time)
            except Exception:
                # 将程序错误信息报警
                self.log.error("警告 趋势策略出现错误", exc_info=True)
                self.dingmessage('警告 趋势策略出现错误', True)
                time.sleep(int(self.granularity))

# 公众号： 千千的量化世界
# 回复：目录 策略 趋势追踪   获取本代码
# 感谢大家对千千量化的支持与厚爱 将持续做好开源 为大家带来更多的干货

# 程序开始的地方
if __name__ == '__main__':
    # 账号
    api_key = ''
    # 密码
    seceret_key = ''
    # 二级密码
    passphrase = 'qwer1234'
    # 选择策略
    mode = ['boll_break', 'jump', 'rsi']
    # 时间粒度 s
    granularity = "3600"
    # 杠杆
    leverate = "5"
    # 交易对
    instrument_id = "ETH-USD-SWAP"
    # 策略名称
    name = "趋势追踪者"
    # 实例化类
    my_strategy = strategy(name, api_key, seceret_key, passphrase, instrument_id, mode, granularity, leverate)
    # 运行类的主逻辑函数
    my_strategy.Run()