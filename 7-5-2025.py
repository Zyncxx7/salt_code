from typing import Dict, List, Deque
from collections import deque
import json
import statistics

class Order:
    def __init__(self, symbol, price, quantity):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

class OrderDepth:
    def __init__(self):
        self.buy_orders = {}
        self.sell_orders = {}

class TradingState:
    def __init__(self, timestamp, order_depths, position):
        self.timestamp = timestamp
        self.order_depths = order_depths
        self.position = position

class Trader:
    def __init__(self):
        self.product_params = {
            'KELP': {
                'window_size': 8,
                'max_position': 50,
                'price_history': {'asks': deque(maxlen=10), 'bids': deque(maxlen=10)},
                'last_trade_price': 0.0,
                'decay_factor': 0.2
            },
            'RAINFOREST_RESIN': {
                'window_size': 10,
                'max_position': 50,
                'price_history': {'asks': deque(maxlen=10), 'bids': deque(maxlen=10)},
                'last_trade_price': 0.0,
                'decay_factor': 0.2
            },
            'SQUID_INK': {
                'window_size': 20,
                'max_position': 50,
                'price_history': {'mid_prices': deque(maxlen=20)},
                'last_trade_price': 0.0,
                'decay_factor': 0.2
            }
        }
        self.vwap_depth = 5

    def calculate_vwap(self, prices: List[float], volumes: List[int], fallback: float) -> float:
        depth = min(self.vwap_depth, len(prices), len(volumes))
        if depth == 0 or sum(volumes[:depth]) < 10:
            print(f"[VWAP] Insufficient depth or volume. Fallback used: {fallback}")
            return fallback
        vwap = sum(p*v for p,v in zip(prices[:depth], volumes[:depth])) / sum(volumes[:depth])
        print(f"[VWAP] VWAP calculated: {vwap:.2f}")
        return vwap

    def run(self, state: TradingState):
        result = {}
        
        print(f"\n--- RUN START: Timestamp {state.timestamp} ---")
        
        for product, order_depth in state.order_depths.items():
            print(f"\nProcessing product: {product}")
            if product not in self.product_params:
                print(f"Skipping unknown product: {product}")
                continue
                
            params = self.product_params[product]
            orders = []
            current_position = state.position.get(product, 0)
            print(f"Current Position: {current_position}")

            # Extract order book data
            bid_prices = sorted(order_depth.buy_orders.keys(), reverse=True)
            bid_volumes = [order_depth.buy_orders[p] for p in bid_prices]
            ask_prices = sorted(order_depth.sell_orders.keys())
            ask_volumes = [abs(order_depth.sell_orders[p]) for p in ask_prices]

            print(f"Top Bids: {bid_prices[:3]}")
            print(f"Top Asks: {ask_prices[:3]}")
            
            best_bid = bid_prices[0] if bid_prices else 0
            best_ask = ask_prices[0] if ask_prices else 0
            spread = best_ask - best_bid if best_ask and best_bid else 1.0
            print(f"Best Bid: {best_bid}, Best Ask: {best_ask}, Spread: {spread}")

            target_volume = 0
            valuation = 0

            # === STRATEGY: RAINFOREST_RESIN ===
            if product == 'RAINFOREST_RESIN':
                valuation = (best_bid + best_ask) / 2.01 if best_bid and best_ask else 0
                print(f"[RAINFOREST_RESIN] Valuation: {valuation:.2f}")

                if best_ask < valuation:
                    target_volume = min(sum(ask_volumes), params['max_position'] - current_position)
                    print(f"[RAINFOREST_RESIN] Buying signal: {target_volume} units")
                elif best_bid > valuation:
                    target_volume = -min(sum(bid_volumes), params['max_position'] + current_position)
                    print(f"[RAINFOREST_RESIN] Selling signal: {target_volume} units")

            # === STRATEGY: SQUID_INK ===
            elif product == 'SQUID_INK':
                mid_price = (best_bid + best_ask) / 2
                params['price_history']['mid_prices'].append(mid_price)
                print(f"[SQUID_INK] Mid Price Updated: {mid_price}")

                if len(params['price_history']['mid_prices']) == params['window_size']:
                    prices = list(params['price_history']['mid_prices'])
                    mean = statistics.mean(prices)
                    std = statistics.stdev(prices)
                    upper_band = mean + 2 * std
                    lower_band = mean - 2 * std
                    print(f"[SQUID_INK] Mean: {mean}, Std: {std}")
                    print(f"[SQUID_INK] Upper Band: {upper_band}, Lower Band: {lower_band}")

                    if mid_price < lower_band:
                        target_volume = min(sum(ask_volumes), params['max_position'] - current_position)
                        print(f"[SQUID_INK] Buy Signal: {target_volume} units")
                    elif mid_price > upper_band:
                        target_volume = -min(sum(bid_volumes), params['max_position'] + current_position)
                        print(f"[SQUID_INK] Sell Signal: {target_volume} units")

            # === STRATEGY: DEFAULT/KELP ===
            else:
                bid_vwap = self.calculate_vwap(bid_prices, bid_volumes, best_bid)
                ask_vwap = self.calculate_vwap(ask_prices, ask_volumes, best_ask)
                current_vwap = (bid_vwap + ask_vwap) / 2
                print(f"[{product}] VWAP Valuation: {current_vwap:.2f}")
                
                params['price_history']['asks'].append(best_ask)
                params['price_history']['bids'].append(best_bid)

                ask_history = params['price_history']['asks']
                bid_history = params['price_history']['bids']

                if len(ask_history) == params['window_size']:
                    if best_ask <= min(ask_history):
                        if best_ask < current_vwap - spread/2.1:
                            max_buy = min(sum(ask_volumes), params['max_position'] - current_position)
                            target_volume = max_buy
                            print(f"[{product}] Buy Signal: {target_volume} units")
                if len(bid_history) == params['window_size']:
                    if best_bid >= max(bid_history):
                        if best_bid > current_vwap + spread/2.1:
                            max_sell = min(sum(bid_volumes), params['max_position'] + current_position)
                            target_volume = -max_sell
                            print(f"[{product}] Sell Signal: {target_volume} units")

            # === Order Placement ===
            if target_volume > 0:
                print(f"Placing Buy Orders for {product}")
                cumulative = 0
                for ask_price in ask_prices:
                    if cumulative >= target_volume:
                        break
                    if ask_price > valuation:
                        continue
                    volume = min(abs(order_depth.sell_orders[ask_price]), target_volume - cumulative)
                    print(f"  Buying {volume} @ {ask_price}")
                    orders.append(Order(product, ask_price, int(2 * volume)))
                    cumulative += volume

            elif target_volume < 0:
                print(f"Placing Sell Orders for {product}")
                cumulative = 0
                for bid_price in bid_prices:
                    if cumulative >= abs(target_volume):
                        break
                    if bid_price < valuation:
                        continue
                    volume = min(order_depth.buy_orders[bid_price], abs(target_volume) - cumulative)
                    print(f"  Selling {volume} @ {bid_price}")
                    orders.append(Order(product, bid_price, int(-2 * volume)))
                    cumulative += volume

            if orders:
                params['last_trade_price'] = orders[0].price
                print(f"Updated last traded price: {params['last_trade_price']}")

            result[product] = orders

        print(f"--- RUN END ---\n")
        return result, 0, json.dumps({})
