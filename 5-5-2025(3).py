from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import numpy as np

class Trader:
    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        result = {}

        WINDOW_SIZE = 14
        VOLATILITY_THRESHOLD = 5
        RSI_OVERBOUGHT = 60
        RSI_OVERSOLD = 40
        BB_MULTIPLIER = 2
        POSITION_LIMIT = 50  # Limit per product

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Historical prices
            past_trades = state.market_trades.get(product, [])
            past_prices = [trade.price for trade in past_trades[-WINDOW_SIZE:]]

            if len(past_prices) < 2:
                continue

            np_prices = np.array(past_prices)
            mean_price = np.mean(np_prices)
            std_dev = np.std(np_prices)

            # Bollinger Bands
            upper_band = mean_price + BB_MULTIPLIER * std_dev
            lower_band = mean_price - BB_MULTIPLIER * std_dev

            # RSI
            deltas = np.diff(np_prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains) if np.any(gains) else 1e-5
            avg_loss = np.mean(losses) if np.any(losses) else 1e-5
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # Momentum
            roc = (np_prices[-1] - np_prices[0]) / np_prices[0]

            print(f"Product: {product}, Mean: {mean_price:.2f}, RSI: {rsi:.2f}, ROC: {roc:.4f}")

            fair_price = mean_price
            acceptable_price = fair_price

            # Skip if too volatile
            if np.max(np_prices) - np.min(np_prices) > VOLATILITY_THRESHOLD:
                print(f"Skipping {product} due to high volatility.")
                continue

            current_position = state.position.get(product, 0)

            # BUY: oversold or under lower band — expect bounce back
            if order_depth.sell_orders:
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_amount = order_depth.sell_orders[best_ask]

                buy_volume = min(best_ask_amount, POSITION_LIMIT - current_position)
                if buy_volume > 0 and (
                    best_ask < lower_band or
                    rsi < RSI_OVERSOLD or
                    (roc < 0 and best_ask < acceptable_price)
                ):
                    print("INVERTED BUY", str(buy_volume) + "x", best_ask)
                    orders.append(Order(product, best_ask, buy_volume))

            # SELL: overbought or above upper band — expect mean reversion
            if order_depth.buy_orders:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_amount = order_depth.buy_orders[best_bid]

                sell_volume = min(best_bid_amount, current_position + POSITION_LIMIT)
                if sell_volume > 0 and (
                    best_bid > upper_band or
                    rsi > RSI_OVERBOUGHT or
                    (roc > 0 and best_bid > acceptable_price)
                ):
                    print("INVERTED SELL", str(-sell_volume) + "x", best_bid)
                    orders.append(Order(product, best_bid, -sell_volume))

            result[product] = orders

        traderData = "SAMPLE"
        conversions = 1
        return result, conversions, traderData
