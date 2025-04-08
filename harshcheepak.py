from typing import Dict, List
from collections import deque
import json
import numpy as np

class Order:
    def __init__(self, symbol, price, quantity):  # fixed typo: _init_ → __init__
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

class OrderDepth:
    def __init__(self):  # fixed typo
        self.buy_orders = {}
        self.sell_orders = {}

class TradingState:
    def __init__(self, timestamp, order_depths, position):  # fixed typo
        self.timestamp = timestamp
        self.order_depths = order_depths
        self.position = position

class Trader:
    def __init__(self):  # fixed typo
        self.product_params = {
        'KELP': {
            'strategy': 'keltner',
            'valuation_strategy': 'ema',  # 'true_value', 'vwap', 'mid', etc.
            'true_value': 2000.0,  # only used if valuation_strategy == 'true_value'
            'window_size': 3,
            'max_position': 50,
            'price_history': deque(maxlen=50),
            'ema': None,
            'buy_price': None
        },
        'RAINFOREST_RESIN': {
            'strategy': 'zscore',
            'valuation_strategy': 'ema',
            'true_value': 10000.0,
            'window_size': 3,
            'max_position': 50,
            'price_history': deque(maxlen=50),
            'ema': None
        },
        'SQUID_INK': {
            'strategy': 'bollinger',
            'valuation_strategy': 'ema',  # Best bid + best ask / 2
            'true_value': 2000.0,
            'window_size': 3,
            'max_position': 50,
            'price_history': deque(maxlen=50),
            'ema': None
        }
    }


    def get_mid_price(self, product, order_depth):
        params = self.product_params[product]
        strategy = params.get('valuation_strategy', 'ema')

        bids = order_depth.buy_orders
        asks = order_depth.sell_orders
        best_bid = max(bids) if bids else 0
        best_ask = min(asks) if asks else 0

        mid_price = (best_bid + best_ask) / 1.9 if best_bid and best_ask else 0

        if strategy == 'true_value':
            return params.get('true_value', mid_price)

        elif strategy == 'mid':
            return mid_price

        elif strategy == 'vwap':
            bid_prices = sorted(bids.keys(), reverse=True)
            bid_volumes = [bids[p] for p in bid_prices]
            ask_prices = sorted(asks.keys())
            ask_volumes = [abs(asks[p]) for p in ask_prices]

            vwap_bid = self.calculate_vwap(bid_prices, bid_volumes, best_bid)
            vwap_ask = self.calculate_vwap(ask_prices, ask_volumes, best_ask)
            return (vwap_bid + vwap_ask) / 2

        elif strategy == 'ema':
            if product=='KELP':
                alpha = 2 / (params['window_size'] + 1)
            elif product=='RAINFOREST_RESIN':
                alpha = 2 / (params['window_size'] + 1)
            elif product=="SQUID_INK":
                alpha = 2 / (params['window_size'] + 1)
            if params.get('ema') is None:
                params['ema'] = mid_price
            else:
                params['ema'] = alpha * mid_price + (1 - alpha) * params['ema']
            return params['ema']

        return mid_price  # fallback


    def bollinger_strategy(self, product, mid_price, state):
        p = self.product_params[product]
        p['price_history'].append(mid_price)
        if len(p['price_history']) < p['window_size']:
            return []

        prices = list(p['price_history'])
        mean = np.mean(prices)
        std = np.std(prices)
        upper = mean + 2 * std
        lower = mean - 2 * std

        print(f"[{product}] Bollinger Bands: mean={mean:.2f}, upper={upper:.2f}, lower={lower:.2f}")

        orders = []
        current_position = state.position.get(product, 0)

        if mid_price < lower:
            qty = min(20, p['max_position'] - current_position)
            print(f"[{product}] Bollinger Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))

        elif mid_price > upper:
            qty = min(20, p['max_position'] + current_position)
            print(f"[{product}] Bollinger Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def breakout_strategy(self, product, mid_price, state):
        p = self.product_params[product]
        p['price_history'].append(mid_price)
        if len(p['price_history']) < p['window_size']:
            return []

        prices = list(p['price_history'])[:-1]
        high = max(prices)
        low = min(prices)

        print(f"[{product}] Breakout: high={high:.2f}, low={low:.2f}, current={mid_price:.2f}")

        orders = []
        current_position = state.position.get(product, 0)

        if mid_price > high:
            qty = min(10, p['max_position'] - current_position)
            print(f"[{product}] Breakout Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif mid_price < low:
            qty = min(10, p['max_position'] + current_position)
            print(f"[{product}] Breakout Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def moving_average_strategy(self, product, mid_price, state):
        p = self.product_params[product]
        p['price_history'].append(mid_price)
        if len(p['price_history']) < p['window_size']:
            return []

        avg = np.mean(p['price_history'])

        print(f"[{product}] Moving Average: mean={avg:.2f}, current={mid_price:.2f}")

        orders = []
        current_position = state.position.get(product, 0)

        if mid_price > avg:
            qty = min(10, p['max_position'] - current_position)
            print(f"[{product}] MA Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif mid_price < avg:
            qty = min(10, p['max_position'] + current_position)
            print(f"[{product}] MA Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def zscore_strategy(self, product, mid_price, state):
        p = self.product_params[product]
        p['price_history'].append(mid_price)
        if len(p['price_history']) < p['window_size']:
            return []

        mean = np.mean(p['price_history'])
        std = np.std(p['price_history'])
        z = (mid_price - mean) / std if std else 0
        print(f"[{product}] Z-Score: {z:.2f}")

        orders = []
        current_position = state.position.get(product, 0)

        if z < -1:
            qty = min(20, p['max_position'] - current_position)
            print(f"[{product}] Z-Score Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif z > 1:
            qty = min(20, p['max_position'] + current_position)
            print(f"[{product}] Z-Score Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def crossover_strategy(self, product, mid_price, state):
        p = self.product_params[product]
        p['price_history'].append(mid_price)
        if len(p['price_history']) < 7:
            return []

        short = np.mean(list(p['price_history'])[-3:])
        long = np.mean(list(p['price_history'])[-7:])
        print(f"[{product}] Crossover: short={short:.2f}, long={long:.2f}")

        orders = []
        current_position = state.position.get(product, 0)

        if short > long:
            qty = min(10, p['max_position'] - current_position)
            print(f"[{product}] Crossover Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif short < long:
            qty = min(10, p['max_position'] + current_position)
            print(f"[{product}] Crossover Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def momentum_strategy(self, product, mid_price, state):
        p = self.product_params[product]
        p['price_history'].append(mid_price)

        if len(p['price_history']) < 4:
            return []

        changes = [p['price_history'][i] - p['price_history'][i - 1] for i in range(1, len(p['price_history']))]
        #print(f"[{product}] Momentum changes: {changes[-4:]}")

        orders = []
        current_position = state.position.get(product, 0)

        # Initialize buy price if not already done
        if 'buy_price' not in p:
            p['buy_price'] = None

        # Buy logic: upward momentum and we aren't max long yet
        if changes[-1] > 0 and changes[-2] > 0 and current_position < p['max_position']:
            qty = self.get_position_size(product, mid_price)
            orders.append(Order(product, int(mid_price), qty))
            p['buy_price'] = mid_price
            #print(f"[{product}] Momentum BUY {qty} @ {mid_price}")

        # Sell logic: 3 consecutive drops or triggered stop-loss
        elif (all(c < 0 for c in changes[-3:]) or
            (p['buy_price'] and mid_price < 0.8 * p['buy_price'])) and current_position > 0:
            qty = current_position  # Sell all current long
            orders.append(Order(product, int(mid_price), -qty))
            #print(f"[{product}] Momentum SELL {qty} @ {mid_price}")
            p['buy_price'] = None

        return orders


    def fair_price_mm_strategy(self, product, order_depth, state):
        best_bid = max(order_depth.buy_orders.keys(), default=0)
        best_ask = min(order_depth.sell_orders.keys(), default=0)
        if best_bid == 0 or best_ask == 0:
            return []

        fair_price = (best_bid + best_ask) / 2
        print(f"[{product}] Fair Price MM: best_bid={best_bid}, best_ask={best_ask}, fair_price={fair_price}")

        orders = []
        current_position = state.position.get(product, 0)
        max_position = self.product_params[product]['max_position']

        buy_qty = min(10, max_position - current_position)
        sell_qty = min(10, max_position + current_position)

        orders.append(Order(product, int(fair_price - 1), buy_qty))
        orders.append(Order(product, int(fair_price + 1), -sell_qty))

        print(f"[{product}] Market Making Buy {buy_qty} at {int(fair_price - 1)}")
        print(f"[{product}] Market Making Sell {sell_qty} at {int(fair_price + 1)}")
        return orders

    def trend_follow_sl_strategy(self, product, mid_price, state):
        import numpy as np
        p = self.product_params[product]
        p['price_history'].append(mid_price)

        if 'cooldown' not in p:
            p['cooldown'] = 0
        if 'trailing_stop' not in p:
            p['trailing_stop'] = None

        if p['cooldown'] > 0:
            print(f"[{product}] In cooldown: {p['cooldown']} ticks remaining")
            p['cooldown'] -= 1
            return []

        if len(p['price_history']) < p['window_size']:
            return []

        prices = list(p['price_history'])
        returns = np.diff(prices)
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        atr = np.mean(np.abs(returns))

        print(f"[{product}] Trend slope: {slope:.4f}, ATR: {atr:.2f}")

        orders = []
        current_position = state.position.get(product, 0)

        # Entry condition
        if slope > 0.2 and current_position <= 0:
            qty = min(10, p['max_position'] - current_position)
            orders.append(Order(product, int(mid_price), qty))
            p['buy_price'] = mid_price
            p['trailing_stop'] = mid_price - 1.5 * atr
            print(f"[{product}] Buy {qty} @ {mid_price}, Trail Stop @ {p['trailing_stop']:.2f}")

        # Exit logic if in position
        if p.get('buy_price') and current_position > 0:
            # Update trailing stop
            new_trailing = mid_price - 1.5 * atr
            if new_trailing > p['trailing_stop']:
                p['trailing_stop'] = new_trailing
                print(f"[{product}] Trailing stop updated to {p['trailing_stop']:.2f}")

            # Stop-loss or take-profit
            if mid_price < p['trailing_stop']:
                qty = current_position
                orders.append(Order(product, int(mid_price), -qty))
                print(f"[{product}] TRAILING STOP SELL {qty} @ {mid_price}")
                p['buy_price'] = None
                p['trailing_stop'] = None
                p['cooldown'] = 5  # wait 5 ticks before re-entering

        return orders

        return orders
    def orderbook_imbalance_strategy(self, product, order_depth, state):
        orders = []
        bids = order_depth.buy_orders
        asks = order_depth.sell_orders
        best_bid = max(bids.keys(), default=0)
        best_ask = min(asks.keys(), default=0)
        bid_volume = sum(bids.values())
        ask_volume = sum(abs(v) for v in asks.values())
        total_volume = bid_volume + ask_volume
        imbalance = (bid_volume - ask_volume) / total_volume if total_volume != 0 else 0
        print(f"[{product}] Orderbook Imbalance: {imbalance:.2f}")

        current_position = state.position.get(product, 0)
        max_position = self.product_params[product]['max_position']

        if imbalance > 0.3:
            volume = min(max_position - current_position, 10)
            orders.append(Order(product, best_ask, volume))
            print(f"[{product}] Buying {volume} at {best_ask} due to OB imbalance")
        elif imbalance < -0.3:
            volume = min(max_position + current_position, 10)
            orders.append(Order(product, best_bid, -volume))
            print(f"[{product}] Selling {volume} at {best_bid} due to OB imbalance")

        return orders

    def keltner_channel_strategy(self, product, mid_price, state):
        p = self.product_params[product]
        p['price_history'].append(mid_price)
        if len(p['price_history']) < 10:
            return []

        ema = sum(p['price_history']) / len(p['price_history'])
        atr = sum(abs(p['price_history'][i] - p['price_history'][i - 1]) for i in range(1, len(p['price_history']))) / (len(p['price_history']) - 1)
        upper_band = ema + 1.5 * atr
        lower_band = ema - 1.5 * atr

        print(f"[{product}] Keltner Channel: EMA={ema:.2f}, ATR={atr:.2f}, Upper={upper_band:.2f}, Lower={lower_band:.2f}")

        orders = []
        current_position = state.position.get(product, 0)
        max_position = p['max_position']

        if mid_price < lower_band:
            qty = min(10, max_position - current_position)
            orders.append(Order(product, int(mid_price), qty))
            print(f"[{product}] Buy {qty} at {mid_price} (Below Keltner Lower Band)")
        elif mid_price > upper_band:
            qty = min(10, max_position + current_position)
            orders.append(Order(product, int(mid_price), -qty))
            print(f"[{product}] Sell {qty} at {mid_price} (Above Keltner Upper Band)")

        return orders

        return orders
    def run(self, state: TradingState):
        result = {}
        for product, order_depth in state.order_depths.items():
            if product not in self.product_params:
                continue

            strategy = self.product_params[product]['strategy']
            mid_price = self.get_mid_price(product, order_depth)
            print(f"\n=== {product} @ {mid_price:.2f} using {strategy} strategy ===")

            if strategy == 'zscore':
                result[product] = self.zscore_strategy(product, mid_price, state)
            elif strategy == 'crossover':
                result[product] = self.crossover_strategy(product, mid_price, state)
            elif strategy == 'momentum':
                result[product] = self.momentum_strategy(product, mid_price, state)
            elif strategy == 'bollinger':
                result[product] = self.bollinger_strategy(product, mid_price, state)
            elif strategy == 'breakout':
                result[product] = self.breakout_strategy(product, mid_price, state)
            elif strategy == 'moving_average':
                result[product] = self.moving_average_strategy(product, mid_price, state)
            elif strategy == 'fair_price_mm':
                result[product] = self.fair_price_mm_strategy(product, order_depth, state)
            elif strategy == 'trend_follow_sl':
                result[product] = self.trend_follow_sl_strategy(product, mid_price, state)
            elif strategy == 'orderbook_imbalance':
                result[product] = self.orderbook_imbalance_strategy(product, order_depth, state)
            elif strategy == 'keltner_channel':
                result[product] = self.keltner_channel_strategy(product, mid_price, state)
            elif strategy == 'trend_follow_sl':
                result[product] = self.trend_follow_sl_strategy(product, mid_price, state)
            else:
                result[product] = []

        return result, 0, json.dumps({})
