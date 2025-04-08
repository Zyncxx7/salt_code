from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import numpy as np

class Trader:

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        result = {}

        WINDOW_SIZE = 14  # Longer window for momentum indicators
        VOLATILITY_THRESHOLD = 5  # Threshold for price range to avoid erratic markets
        RSI_OVERBOUGHT = 70
        RSI_OVERSOLD = 30
        BB_MULTIPLIER = 2  # For Bollinger Bands

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Get historical prices
            past_trades = state.market_trades.get(product, [])
            past_prices = [trade.price for trade in past_trades[-WINDOW_SIZE:]]

            # Skip if insufficient data
            if len(past_prices) < 2:
                continue

            np_prices = np.array(past_prices)
            mean_price = np.mean(np_prices)
            std_dev = np.std(np_prices)

            # Bollinger Bands
            upper_band = mean_price + BB_MULTIPLIER * std_dev
            lower_band = mean_price - BB_MULTIPLIER * std_dev

            # RSI calculation
            deltas = np.diff(np_prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains) if np.any(gains) else 1e-5
            avg_loss = np.mean(losses) if np.any(losses) else 1e-5
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # Momentum (Rate of Change)
            roc = (np_prices[-1] - np_prices[0]) / np_prices[0]

            print(f"Product: {product}, Price Mean: {mean_price:.2f}, RSI: {rsi:.2f}, ROC: {roc:.4f}")

            # Define fair price as moving average
            fair_price = mean_price
            acceptable_price = fair_price

            # Volatility check
            if np.max(np_prices) - np.min(np_prices) > VOLATILITY_THRESHOLD:
                print(f"Skipping {product} due to high volatility.")
                continue

            # Buy signal
            if len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_amount = order_depth.sell_orders[best_ask]

                # Buy if price is low and RSI indicates oversold and positive momentum
                if (
                    best_ask < lower_band or
                    rsi < RSI_OVERSOLD or
                    (roc > 0 and best_ask < acceptable_price)
                ):
                    print("BUY", str(-best_ask_amount) + "x", best_ask)
                    orders.append(Order(product, best_ask, -best_ask_amount))

            # Sell signal
            if len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_amount = order_depth.buy_orders[best_bid]

                # Sell if price is high and RSI indicates overbought and negative momentum
                if (
                    best_bid > upper_band or
                    rsi > RSI_OVERBOUGHT or
                    (roc < 0 and best_bid > acceptable_price)
                ):
                    print("SELL", str(best_bid_amount) + "x", best_bid)
                    orders.append(Order(product, best_bid, -best_bid_amount))

            result[product] = orders

        traderData = "SAMPLE"
        conversions = 1
        return result, conversions, traderData
