# 作者：千千量化  
# 市价网格策略说明：这是一个网格策略，在到达网格位置的时候下市价单进行增减仓操作，支持多空双向开仓，支持底仓模式
# wechat: ThousandTech

from fmex import Fmex
import logging
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import json
import requests

class NetStrategy:
    def __init__(self,exchange_name,api_key,seceret_key):
        # 系统参数
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.seceret_key = seceret_key
        self.last_price = 0
        self.mail_address = 'yunwarn@163.com'
        self.max_mail_num = 5
        self.now_mail_num = 0
        self.position = 0
        # 策略参数
        self.side_mode = 'short'  # 选择做多/做空模式
        self.first_hold_mode = False  # 选择启动时是否买入底仓
        self.symbol = 'BTCUSD_P' # 选择交易品种，Fmex仅支持BTC永续合约
        self.first_hold = 100 # 选择买入底仓数量
        self.step = 20 # 设置网格间距
        self.one_hand = 10 # 设置单个网格下单量
        self.net_num = self.first_hold / self.one_hand # 设置网格数量
        self.hold_limit = self.net_num * self.one_hand + self.first_hold # 计算最大持仓量量
        self.time_interval = 5 # 设置询价时间间隔

    # 设置日记记录
    def initLog(self):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        # log to txt
        formatter = logging.Formatter('[%(asctime)s] %(message)s')
        handler = logging.FileHandler("log_%s.txt" % time.strftime("%Y-%m-%d %H-%M-%S"))
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        # log to console
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        # add to log
        self.log.addHandler(handler)
        self.log.addHandler(console)
        self.log.info("网格策略启动")
        self.log.info("品种%s 模式%s 网格间距%d 底仓%d 单手下单量%d"%(self.symbol, self.side_mode, self.step, self.first_hold, self.one_hand))

    # 邮件提醒模块
    def mail_watcher(self, msg):
        mail_host = "smtp.qq.com"  # 设置服务器
        mail_user = "326658790"  # 用户名
        mail_pass = ""  # 口令

        sender = '326658790@qq.com'
        receivers = [self.mail_address]

        message = MIMEText(msg, 'plain', 'utf-8')
        message['From'] = Header("云端告警", 'utf-8')
        message['To'] = Header("我的邮箱", 'utf-8')

        subject = '云端告警邮件'
        message['Subject'] = Header(subject, 'utf-8')

        try:
            if self.now_mail_num < self.max_mail_num:
                smtpObj = smtplib.SMTP_SSL(host=mail_host)
                smtpObj.connect(mail_host, 465)
                smtpObj.login(mail_user, mail_pass)
                smtpObj.sendmail(sender, receivers, message.as_string())
                smtpObj.close()
                self.now_mail_num += 1
                time.sleep(1)
        except Exception as e:
            self.log.info(e)

    # 钉钉提醒模块
    def dingmessage(self, msg, at_all = False):
        webhook = ''
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
        # self.log.info(info.text)

    def run(self):

        # 启动日志
        self.initLog()

        # 登录交易所
        self.exchange = Fmex()
        self.exchange.auth(self.api_key, self.seceret_key)

        # 设置网格间距
        step = self.step

        # 获取市场价格
        orderbook = self.exchange.fetch_orderbook(symbol=self.symbol)
        best_bid, best_bid_amt = orderbook['data']['bids'][0], orderbook['data']['bids'][1]
        best_ask, best_ask_amt = orderbook['data']['asks'][0], orderbook['data']['asks'][1]

        # 检查当前仓位和持仓方向
        position = self.exchange.fetch_position()
        position_hold = position['data']['results'][0]['quantity']
        position_side = ''
        if position_hold > 0:
            position_side = position['data']['results'][0]['direction'].lower()

        # 如果空仓 买入底仓
        if position_hold == 0 and self.first_hold_mode:
            _symbol = self.symbol
            _type = 'limit'
            _amount = self.first_hold

            # 如果是做多模式
            if self.side_mode == 'long':
                _side = 'long'
                _price = best_ask + step
                result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)

            # 如果是做空模式
            if self.side_mode == 'short':
                _side = 'short'
                _price = best_bid  - step
                result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)

            # 提示下单结果
            self.log.info(result)

        elif position_hold > 0 and position_hold < self.first_hold and self.first_hold_mode:

            # 如果持有相同方向仓位 补足底仓
            _symbol = self.symbol
            _type = 'limit'
            _amount = self.first_hold - position_hold

            # 如果是做多模式
            if self.side_mode == 'long':
                _side = 'long'
                _price = best_ask  + step
                result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)

            # 如果是做空模式
            if self.side_mode == 'short':
                _side = 'short'
                _price = best_bid  - step
                result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)

            # 提示下单结果
            self.log.info(result)

        elif position_side is not '' and self.side_mode != position_side and self.first_hold_mode:

            # 如果持有相反仓位 提示需手动调整仓位
            self.log.info("当前持有相反方向底仓 请手动处理")
            return

        # 获取当前账户信息
        account = self.exchange.fetch_balance()
        self.coin = account['data']['BTC'][0] + account['data']['BTC'][1] + account['data']['BTC'][2]
        self.log.info('coin:'+str(self.coin))

        # 设置网格初始价格

        # 如果是做多模式
        if self.side_mode == 'long':
            self.last_price = best_ask
        # 如果是做空模式
        if self.side_mode == 'short':
            self.last_price = best_bid
        self.start_price = self.last_price

        # 记录循环次数
        loop = 0

        # 开启主循环
        while True:

            try:

                # 循环计数增加
                loop += 1

                # 获取当前账户信息
                account = self.exchange.fetch_balance()
                coin = account['data']['BTC'][0] + account['data']['BTC'][1] +account['data']['BTC'][2]

                # 获取市场价格
                orderbook = self.exchange.fetch_orderbook(symbol=self.symbol)
                best_bid,best_bid_amt = orderbook['data']['bids'][0], orderbook['data']['bids'][1]
                best_ask,best_ask_amt = orderbook['data']['asks'][0], orderbook['data']['asks'][1]
                mid_price = (best_ask+best_bid)/2
                
                # 显示当前状态
                msg = '>>当前网格位置 %d 浮动盈亏 %5.7f(%2.2f)  价格变动 %5.1f(%2.2f)'%(self.position, coin - self.coin, \
                    (coin - self.coin)/self.coin * 100, mid_price - self.start_price, \
                    (mid_price - self.start_price)/self.start_price * 100)
                self.log.info( msg )
                if loop % 60 == 0:
                    self.dingmessage( '网格策略当前余额为 %6.6f' %coin )

                # 当前价格所处位置
                # price = (best_ask + best_bid)/2
                # if price > self.last_price:
                #     if price > self.last_price + step / 2:
                #         self.log.info('|---o|')
                #     else:
                #         self.log.info('|--o-|')
                # else:
                #     if price < self.last_price - step / 2:
                #         self.log.info('|o---|')
                #     else:
                #         self.log.info('|-o--|')

                # 如果触碰下网格线
                if best_ask < self.last_price - step:

                    # 获取当前持仓
                    position = self.exchange.fetch_position()
                    position_hold = position['data']['results'][0]['quantity']
                    position_side = ''
                    if position_hold > 0:
                        position_side = position['data']['results'][0]['direction'].lower()
                    msg = '当前持仓数 %d  持仓方向 %s'%(position_hold, position_side)
                    self.log.info(msg)
                    self.dingmessage(msg)

                    # 如果可以做多
                    if position_hold < self.hold_limit:

                        # 进行做多
                        _symbol = self.symbol
                        _type = 'limit'
                        _amount = self.one_hand
                        _side = 'long'
                        _price = best_ask  + step
                        result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)
                        self.last_price = best_ask
                        msg = '触碰下网格 做多一手'
                        self.log.info(msg)
                        self.dingmessage(msg)
                        self.position -= 1

                    # 如果不能做多
                    if position_hold >= self.hold_limit:

                        # 做空进行对冲
                        _symbol = self.symbol
                        _type = 'limit'
                        _amount = position_hold * 2
                        _side = 'short'
                        _price = best_bid  - step
                        result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)
                        self.last_price = best_bid
                        msg = '价格趋势下跌 反手做空'
                        self.log.info(msg)
                        self.dingmessage(msg)
                        self.position = 0

                        # 检查对冲情况
                        while True:

                            # 提示
                            self.log.info('当前进入对冲状态')
                            
                            # 获取市场行情
                            orderbook = self.exchange.fetch_orderbook(symbol=self.symbol)
                            best_bid,best_bid_amt = orderbook['data']['bids'][0], orderbook['data']['bids'][1]
                            best_ask,best_ask_amt = orderbook['data']['asks'][0], orderbook['data']['asks'][1]

                            # 如果价格回归网格区间
                            if best_bid > self.last_price:

                                # 平对冲单
                                _symbol = self.symbol
                                _type = 'limit'
                                _amount = position_hold * 2
                                _side = 'long'
                                _price = best_ask  + step
                                _num = 2
                                for _ in range(_num):
                                    result = self.exchange.create_order(_symbol, _type, _side, _price, _amount/_num)
                                    self.last_price = best_ask
                                    msg = '价格回到对冲点 平对冲单'
                                    self.log.info(msg)
                                    self.dingmessage(msg)
                                    time.sleep(1)

                                # 重启网格
                                break

                            # 如果价格达到盈亏平衡点
                            if best_ask < self.last_price - step * 10:

                                # 平对冲单
                                _symbol = self.symbol
                                _type = 'limit'
                                _amount = position_hold * 2
                                _side = 'long'
                                _price = best_ask  + step
                                _num = 2
                                for _ in range(_num):
                                    result = self.exchange.create_order(_symbol, _type, _side, _price, _amount/_num)
                                    self.last_price = best_ask
                                    msg = '价格达到盈亏平衡点 平对冲单'
                                    self.log.info(msg)
                                    self.dingmessage(msg)
                                    time.sleep(1)

                                # 重启网格
                                break

                            # 休眠
                            time.sleep(self.time_interval)

                # 如果触碰上网格线
                if best_bid > self.last_price + step:

                    # 获取当前持仓
                    position = self.exchange.fetch_position()
                    position_hold = position['data']['results'][0]['quantity']
                    position_side = ''
                    if position_hold > 0:
                        position_side = position['data']['results'][0]['direction'].lower()
                    msg = '当前持仓数 %d  持仓方向 %s'%(position_hold, position_side)
                    self.log.info(msg)
                    self.dingmessage(msg)

                    # 如果可以做空
                    if position_hold < self.hold_limit:
                        
                        # 进行做空
                        _symbol = self.symbol
                        _type = 'limit'
                        _amount = self.one_hand
                        _side = 'short'
                        _price = best_bid  - step
                        result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)
                        self.last_price = best_bid
                        msg = '触碰上网格 做空一手'
                        self.log.info(msg)
                        self.dingmessage(msg)
                        self.position += 1

                    # 如果不能做空
                    if position_hold >= self.hold_limit:

                        # 做多进行对冲
                        _symbol = self.symbol
                        _type = 'limit'
                        _amount = position_hold * 2
                        _side = 'long'
                        _price = best_ask  + step
                        result = self.exchange.create_order(_symbol, _type, _side, _price, _amount)
                        self.last_price = best_ask
                        msg = '价格趋势上涨 反手做多'
                        self.log.info(msg)
                        self.dingmessage(msg)
                        self.position = 0

                        # 检查对冲情况
                        while True:

                            # 提示
                            self.log.info('当前进入对冲状态')
                            
                            # 获取市场行情
                            orderbook = self.exchange.fetch_orderbook(symbol=self.symbol)
                            best_bid,best_bid_amt = orderbook['data']['bids'][0], orderbook['data']['bids'][1]
                            best_ask,best_ask_amt = orderbook['data']['asks'][0], orderbook['data']['asks'][1]

                            # 如果价格回归网格区间
                            if best_ask < self.last_price:

                                # 平对冲单
                                _symbol = self.symbol
                                _type = 'limit'
                                _amount = position_hold * 2
                                _side = 'short'
                                _price = best_bid  - step
                                _num = 2
                                for _ in range(_num):
                                    result = self.exchange.create_order(_symbol, _type, _side, _price, _amount/_num)
                                    self.last_price = best_bid
                                    msg = '价格回到对冲点 平对冲单'
                                    self.log.info(msg)
                                    self.dingmessage(msg)
                                    time.sleep(1)

                                # 重启网格
                                break

                            # 如果价格达到盈亏平衡点
                            if best_ask > self.last_price + step * 10:

                                # 平对冲单
                                _symbol = self.symbol
                                _type = 'limit'
                                _amount = position_hold * 2
                                _side = 'short'
                                _price = best_bid  - step
                                _num = 2
                                for _ in range(_num):
                                    result = self.exchange.create_order(_symbol, _type, _side, _price, _amount/_num)
                                    self.last_price = best_bid
                                    msg = '价格达到盈亏平衡点 平对冲单'
                                    self.log.info(msg)
                                    self.dingmessage(msg)
                                    time.sleep(1)

                                # 重启网格
                                break

                            # 休眠
                            time.sleep(self.time_interval)

                # 如果没有触碰网格线
                if best_ask < self.last_price + step and best_bid > self.last_price - step:
                    
                    # 休眠 进入下个循环
                    time.sleep(self.time_interval)  

            except Exception as e:
                
                self.log.error(e)

                self.dingmessage('程序出错 请尽快处理', True)

if __name__ == '__main__':

    # fmex v3
    exchange_name = 'fmex'
    api_key = ''
    seceret_key = ''
    fee_ratio = 0

    # init Strategy class
    net = NetStrategy(exchange_name,api_key,seceret_key)
    net.run()


