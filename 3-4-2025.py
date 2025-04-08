from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List

class Trader:

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        result = {}

        WINDOW_SIZE = 5  # Look at the last 5 trades for price trends
        VOLATILITY_THRESHOLD = 5  # Ignore trades if price fluctuates too much
        TREND_SENSITIVITY = 0.02  # Minimum trend change to act on

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Extract past trade prices
            past_trades = state.market_trades.get(product, [])
            past_prices = [trade.price for trade in past_trades[-WINDOW_SIZE:]]

            # Compute a Weighted Moving Average (WMA)
            if past_prices:
                weights = list(range(1, len(past_prices) + 1))
                fair_price = sum(p * w for p, w in zip(past_prices, weights)) / sum(weights)
            else:
                # Default to bid-ask midpoint if no past trades exist
                if order_depth.buy_orders and order_depth.sell_orders:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_ask = min(order_depth.sell_orders.keys())
                    fair_price = (best_bid + best_ask) / 2.2
                else:
                    fair_price = 2028  # Default fallback price
            
            acceptable_price = fair_price

            # Calculate price volatility
            if len(past_prices) >= 2:
                price_range = max(past_prices) - min(past_prices)
                if price_range > VOLATILITY_THRESHOLD:
                    print(f"Skipping {product} due to high volatility: {price_range}")
                    continue  # Avoid trading in high-volatility conditions
            
            # Calculate price trend
            if len(past_prices) >= 2:
                trend = (past_prices[-1] - past_prices[0]) / past_prices[0]  # % change
            else:
                trend = 0

            print(f"Product: {product}, Acceptable Price: {acceptable_price}, Trend: {trend}")

            # **BUY if price is below fair value and trend is UP**
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                if best_ask < acceptable_price and trend > TREND_SENSITIVITY:
                    print("BUY", str(-best_ask_amount) + "x", best_ask)
                    orders.append(Order(product, best_ask, -best_ask_amount))

            # **SELL if price is above fair value and trend is DOWN**
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                if best_bid > acceptable_price and trend < -TREND_SENSITIVITY:
                    print("SELL", str(best_bid_amount) + "x", best_bid)
                    orders.append(Order(product, best_bid, -best_bid_amount))

            result[product] = orders

        traderData = "SAMPLE"  # Store past data if needed
        conversions = 1
        return result, conversions, traderData
