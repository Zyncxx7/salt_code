from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List

class Trader:

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        result = {}

        WINDOW_SIZE = 5  # Number of trades to look back
        VOLATILITY_THRESHOLD = 5  # Max price fluctuation to consider
        TREND_SENSITIVITY = 0.02  # Minimum trend % to consider

        for product in state.order_depths:
            print(f"\n--- Processing {product} ---")
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            past_trades = state.market_trades.get(product, [])
            past_prices = [trade.price for trade in past_trades[-WINDOW_SIZE:]]

            print(f"Last {len(past_prices)} trade prices: {past_prices}")

            # Weighted Moving Average (WMA)
            if past_prices:
                weights = list(range(1, len(past_prices) + 1))
                weighted_sum = sum(p * w for p, w in zip(past_prices, weights))
                fair_price = weighted_sum / sum(weights)
                print(f"Calculated Weighted Moving Average (fair price): {fair_price}")
            else:
                if order_depth.buy_orders and order_depth.sell_orders:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_ask = min(order_depth.sell_orders.keys())
                    fair_price = (best_bid + best_ask) / 2
                    print(f"No trades found. Using bid-ask midpoint as fair price: {fair_price}")
                else:
                    fair_price = 2028
                    print("No trades or order book available. Using default fallback price: 2028")

            acceptable_price = fair_price

            # Volatility check
            if len(past_prices) >= 2:
                price_range = max(past_prices) - min(past_prices)
                print(f"Volatility (price range): {price_range}")
                if price_range > VOLATILITY_THRESHOLD:
                    print(f"High volatility (> {VOLATILITY_THRESHOLD}). Skipping trading for {product}")
                    continue

            # Trend analysis
            if len(past_prices) >= 2:
                trend = (past_prices[-1] - past_prices[0]) / past_prices[0]
                print(f"Trend over last {WINDOW_SIZE} trades: {trend * 100:.2f}%")
            else:
                trend = 0
                print("Insufficient data for trend analysis.")

            # --- Decision: BUY ---
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                print(f"Best Ask: {best_ask}, Amount: {best_ask_amount}")
                if best_ask < acceptable_price and trend > TREND_SENSITIVITY:
                    print(f"BUY decision made at {best_ask} since price < fair ({acceptable_price}) and trend is positive.")
                    orders.append(Order(product, best_ask, -best_ask_amount))
                else:
                    print("No BUY: Conditions not met.")

            # --- Decision: SELL ---
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                print(f"Best Bid: {best_bid}, Amount: {best_bid_amount}")
                if best_bid > acceptable_price and trend < -TREND_SENSITIVITY:
                    print(f"SELL decision made at {best_bid} since price > fair ({acceptable_price}) and trend is negative.")
                    orders.append(Order(product, best_bid, -best_bid_amount))
                else:
                    print("No SELL: Conditions not met.")

            result[product] = orders

        traderData = "SAMPLE"
        conversions = 1
        return result, conversions, traderData
