from typing import Dict, List
from collections import deque
import json
import numpy as np
import statistics

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
        # 'KELP': {
        #     'strategy': 'keltner',
        #     'valuation_strategy': 'ema',  # 'true_value', 'vwap', 'mid', etc.
        #     'true_value': 2000.0,  # only used if valuation_strategy == 'true_value'
        #     'window_size': 3,
        #     'max_position': 50,
        #     'price_history': deque(maxlen=50),
        #     'ema': None,
        #     'buy_price': None
        # },
        'RAINFOREST_RESIN': {
            'strategy': 'market_maker',
            'valuation_strategy': 'true_value',
            'true_value': 10000.0,
            'window_size': 3,
            'max_position': 50,
            'price_history': deque(maxlen=50),
            'ema': 10000,
            'spread': 1.8,
            'order_size': 50, 
            'skew_sensitivity': 0.01
        },
        # 'SQUID_INK': {
        #     'strategy': 'bollinger',
        #     'valuation_strategy': 'ema',  # Best bid + best ask / 2
        #     'true_value': 2000.0,
        #     'window_size': 3,
        #     'max_position': 50,
        #     'price_history': deque(maxlen=50),
        #     'ema': None
        # }
    }
    def calculate_vwap(self, prices, volumes, fallback_price):
        total_volume = sum(volumes)
        if total_volume == 0:
            return fallback_price  # fallback in case there's no volume
        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_volume
        return vwap


    def get_mid_price(self, product, order_depth):
        params = self.product_params[product]
        strategy = params.get('valuation_strategy', 'ema')

        bids = order_depth.buy_orders
        asks = order_depth.sell_orders
        best_bid = max(bids) if bids else 0
        best_ask = min(asks) if asks else 0

        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0

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
            alpha = 2 / (params['window_size'] + 1)
            if params.get('ema') is None:
                params['ema'] = mid_price
            else:
                params['ema'] = alpha * mid_price + (1 - alpha) * params['ema']
            return params['ema']

        return mid_price  # fallback
    # Add this in your Trader class
    def market_maker_strategy(self, product, mid_price, state, order_depth):
        p = self.product_params[product]
        orders = []

        price_history = p['price_history']
        price_history.append(mid_price)
        if len(price_history) < 5:
            return []

        position = state.position.get(product, 0)
        max_position = p.get('max_position', 50)

        # === Dynamic Spread based on volatility ===
        recent_returns = [price_history[-i] - price_history[-i - 1] for i in range(1, 5)]
        volatility = max(1, statistics.stdev(recent_returns))  # avoid zero
        base_spread = p.get('base_spread', 2)
        spread = base_spread + 0.02 * volatility  # wider in volatility

        # === Dynamic Skew based on inventory and trend ===
        skew_sensitivity = p.get('skew_sensitivity', 0.1)
        price_trend = sum(recent_returns[-2:])
        skew = skew_sensitivity * position - 0.2 * price_trend

        # === Fixed Order Size ===
        order_size = p.get('order_size', 5)

        # Calculate bid/ask prices
        bid_price = int(mid_price - spread / 2 - skew)
        ask_price = int(mid_price + spread / 2 - skew)

        # Limit quantity to not exceed max position
        bid_qty = min(order_size, max_position - position)
        ask_qty = min(order_size, max_position + position)

        if bid_qty > 0:
            print(f"[{product}] MM Buy {bid_qty} @ {bid_price} (skew: {skew:.2f}, spread: {spread:.2f})")
            orders.append(Order(product, bid_price, bid_qty))

        if ask_qty > 0:
            print(f"[{product}] MM Sell {ask_qty} @ {ask_price} (skew: {skew:.2f}, spread: {spread:.2f})")
            orders.append(Order(product, ask_price, -ask_qty))

        return orders
    # def market_maker_strategy(self, product, mid_price, state, order_depth):
    #     p = self.product_params[product]
    #     orders = []

    #     # Basic config
    #     spread = p.get('spread', 2)
    #     order_size = p.get('order_size', 5)
    #     max_position = p.get('max_position', 50)
    #     position = state.position.get(product, 0)

    #     # Skew factor: how much to shift bid/ask prices based on inventory
    #     skew_sensitivity = p.get('skew_sensitivity', 0.1)
    #     skew = skew_sensitivity * position

    #     # Apply skew to bid and ask prices
    #     bid_price = int(mid_price - spread / 2 - skew)
    #     ask_price = int(mid_price + spread / 2 - skew)

    #     # Adjust order sizes to avoid exceeding max position
    #     bid_qty = min(order_size, max_position - position)
    #     ask_qty = min(order_size, max_position + position)

    #     if bid_qty > 0:
    #         print(f"[{product}] MM Buy {bid_qty} @ {bid_price} (skew: {skew})")
    #         orders.append(Order(product, bid_price, bid_qty))

    #     if ask_qty > 0:
    #         print(f"[{product}] MM Sell {ask_qty} @ {ask_price} (skew: {skew})")
    #         orders.append(Order(product, ask_price, -ask_qty))

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
            qty = min(10, p['max_position'] - current_position)
            print(f"[{product}] Bollinger Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))

        elif mid_price > upper:
            qty = min(10, p['max_position'] + current_position)
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

        if z < -0.9:
            qty = min(25, p['max_position'] - current_position)
            print(f"[{product}] Z-Score Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif z > 0.9:
            qty = min(25, p['max_position'] + current_position)
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
        print(f"[{product}] Momentum changes: {changes[-4:]}")

        orders = []
        current_position = state.position.get(product, 0)

        if changes[-1] > 0 and changes[-2] > 0:
            qty = min(10, p['max_position'] - current_position)
            p['buy_price'] = mid_price
            print(f"[{product}] Momentum Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif all(c < 0 for c in changes[-3:]) or (p['buy_price'] and mid_price < 0.8 * p['buy_price']):
            qty = min(10, p['max_position'] + current_position)
            p['buy_price'] = None
            print(f"[{product}] Momentum Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

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
        p = self.product_params[product]
        p['price_history'].append(mid_price)
        if len(p['price_history']) < 3:
            return []

        changes = [p['price_history'][-i] - p['price_history'][-i - 1] for i in range(1, 3)]
        print(f"[{product}] Trend SL changes: {changes[::-1]}")

        orders = []
        current_position = state.position.get(product, 0)

        if changes[-1] > 0 and changes[-2] > 0:
            qty = min(10, p['max_position'] - current_position)
            p['buy_price'] = mid_price
            print(f"[{product}] Trend Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))

        elif p.get('buy_price') and mid_price < 0.8 * p['buy_price']:
            qty = min(10, p['max_position'] + current_position)
            print(f"[{product}] Trend Stop Loss Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))
            p['buy_price'] = None

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
            elif strategy == 'stable_mm':
                result[product] = self.crossover_strategy(product, mid_price, state)
            elif strategy == 'market_maker':
                result[product] = self.market_maker_strategy(product, mid_price, state, order_depth)
            else:
                result[product] = []


        return result, 0, json.dumps({})