from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import numpy as np

class Trader:

    def __init__(self):
        self.position = {}  # track position per product
        self.cooldowns = {}

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        result = {}

        WINDOW = 20
        BB_MULT = 2
        RSI_PERIOD = 14
        RSI_OVERSOLD = 30
        RSI_OVERBOUGHT = 70
        MAX_POSITION = 20  # customize this
        VOLATILITY_THRESHOLD = 5
        COOLDOWN_PERIOD = 3

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            self.position.setdefault(product, 0)
            self.cooldowns.setdefault(product, 0)

            if self.cooldowns[product] > 0:
                self.cooldowns[product] -= 1
                continue

            past_trades = state.market_trades.get(product, [])
            prices = [trade.price for trade in past_trades[-WINDOW:]]

            if len(prices) < RSI_PERIOD:
                continue

            np_prices = np.array(prices)
            mean = np.mean(np_prices)
            std = np.std(np_prices)

            upper_band = mean + BB_MULT * std
            lower_band = mean - BB_MULT * std

            deltas = np.diff(np_prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains) if np.any(gains) else 1e-5
            avg_loss = np.mean(losses) if np.any(losses) else 1e-5
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            roc = (np_prices[-1] - np_prices[0]) / np_prices[0]
            fair_price = mean

            # Volatility filter
            if np.max(np_prices) - np.min(np_prices) > VOLATILITY_THRESHOLD:
                print(f"Skipping {product} due to volatility.")
                continue

            print(f"[{product}] Price: {np_prices[-1]}, BB: [{lower_band:.2f}, {upper_band:.2f}], RSI: {rsi:.2f}, ROC: {roc:.2f}, Position: {self.position[product]}")

            # BUY when price below lower band AND RSI < oversold AND ROC is negative
            if len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_vol = order_depth.sell_orders[best_ask]

                if (
                    best_ask < lower_band and
                    rsi < RSI_OVERSOLD and
                    roc < 0 and
                    self.position[product] < MAX_POSITION
                ):
                    buy_volume = min(-best_ask_vol, MAX_POSITION - self.position[product])
                    orders.append(Order(product, best_ask, buy_volume))
                    self.position[product] += buy_volume
                    self.cooldowns[product] = COOLDOWN_PERIOD
                    print(f"BUY {buy_volume}@{best_ask}")

            # SELL when price above upper band AND RSI > overbought AND ROC is positive
            if len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_vol = order_depth.buy_orders[best_bid]

                if (
                    best_bid > upper_band and
                    rsi > RSI_OVERBOUGHT and
                    roc > 0 and
                    self.position[product] > -MAX_POSITION
                ):
                    sell_volume = min(best_bid_vol, self.position[product] + MAX_POSITION)
                    orders.append(Order(product, best_bid, -sell_volume))
                    self.position[product] -= sell_volume
                    self.cooldowns[product] = COOLDOWN_PERIOD
                    print(f"SELL {sell_volume}@{best_bid}")

            result[product] = orders

        traderData = "ACTIVE"
        conversions = 1
        return result, conversions, traderData
