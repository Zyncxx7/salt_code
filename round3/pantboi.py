from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Dict, List
import math
import numpy as np
from collections import deque
import json
from typing import Any
import statistics

##############      ALL IMPORTS     ##############


##############      LOGGER STUFF    ############## 


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()

#########   END OF LOGGER ########

# products = ['KELP', 'RAINFOREST_RESIN', 'SQUID_INK', 'JAMS','DJEMBES','PICNIC_BASKET1','PICNIC_BASKET2','CROISSANTS']
# products=['DJEMBES']
# products = ['RAINFOREST_RESIN' , 'KELP']
products=[]
pair_products = [('DJEMBES', 'CROISSANTS')]
# pair_products=[]

#########  PRODUCT PARAMS ########
pair_params = {
    ('DJEMBES', 'CROISSANTS'): {
        'lookback': 100,          # Historical spread data points
        'hedge_ratio': 0,         # Will be calculated dynamically
        'entry_threshold': 2.0,   # Enter when spread z-score exceeds this value
        'exit_threshold': 0.5,    # Exit when spread z-score falls below this value
        'max_position': 20,       # Maximum position size per product
        'cooldown': 5,            # Wait periods between trades
        'history': deque(maxlen=100),  # History of spread values
        'current_state': "NEUTRAL"     # Current trading state
    }
}

max_position = {
    'KELP' : 50, 
    'RAINFOREST_RESIN' : 50, 
    'SQUID_INK' : 50, 
    'JAMS' : 350, 
    'CROISSANTS' : 250, 
    'DJEMBES' : 60, 
    'PICNIC_BASKET1' : 60, 
    'PICNIC_BASKET2' : 100,
}

price_history = {
    'KELP' : deque(maxlen=20), 
    'RAINFOREST_RESIN' : deque(maxlen=20), 
    'SQUID_INK' : deque(maxlen=20), 
    'JAMS' : deque(maxlen=20), 
    'CROISSANTS' : deque(maxlen=20), 
    'DJEMBES' : deque(maxlen=20), 
    'PICNIC_BASKET1' : deque(maxlen=20), 
    'PICNIC_BASKET2' : deque(maxlen=20), 
}

cooldown = {
    'KELP' : 0, 
    'RAINFOREST_RESIN' : 0, 
    'SQUID_INK' : 0, 
    'JAMS' : 0, 
    'CROISSANTS' : 0, 
    'DJEMBES' : 0, 
    'PICNIC_BASKET1' : 0, 
    'PICNIC_BASKET2' : 0, 
}

cooldown_period = {
    'KELP' : 5, 
    'RAINFOREST_RESIN' : 5, 
    'SQUID_INK' : 5, 
    'JAMS' : 5, 
    'CROISSANTS' : 5, 
    'DJEMBES' : 5, 
    'PICNIC_BASKET1' : 5, 
    'PICNIC_BASKET2' : 5, 
}

mid_price = {
    'KELP' : 0, 
    'RAINFOREST_RESIN' : 0, 
    'SQUID_INK' : 0, 
    'JAMS' : 0, 
    'CROISSANTS' : 0, 
    'DJEMBES' : 0, 
    'PICNIC_BASKET1' : 0, 
    'PICNIC_BASKET2' : 0, 
}

######## BOLLINGER PARAMS ########
b_window_size = {
    'KELP' : 20, 
    'RAINFOREST_RESIN' : 20, 
    'SQUID_INK' : 10, 
    'JAMS' : 20, 
    'CROISSANTS' : 20, 
    'DJEMBES' : 20, 
    'PICNIC_BASKET1' : 20, 
    'PICNIC_BASKET2' : 20, 
}  


######## EMA PARAMS ###########
ema_alpha = {
    'KELP' : 0.7, 
    'RAINFOREST_RESIN' : 0.7, ##
    'SQUID_INK' : 0.6, ##best value 0.89 for historycal
    'JAMS' : 0.8, ##best value 0.8 for hystorical
    'CROISSANTS' : 0.95, 
    'DJEMBES' : 0.5, 
    'PICNIC_BASKET1' : 0.5, 
    'PICNIC_BASKET2' : 0.5, 
}  

###### ZSCORE PARAMS ##########
z_max_volume = {
    'KELP' : 25, 
    'RAINFOREST_RESIN' : 25, 
    'SQUID_INK' : 25, 
    'JAMS' : 25, 
    'CROISSANTS' : 25, 
    'DJEMBES' : 25, 
    'PICNIC_BASKET1' : 25, 
    'PICNIC_BASKET2' : 25, 
}

###### CROSSOVER PARAMS ######
cross_windows = {
    'KELP' : {'short' : 3, 'long' : 7}, 
    'RAINFOREST_RESIN' : {'short' : 3, 'long' : 7}, 
    'SQUID_INK' : {'short' : 3, 'long' : 7}, 
    'JAMS' : {'short' : 3, 'long' : 7}, 
    'CROISSANTS' : {'short' : 3, 'long' : 7}, 
    'DJEMBES' : {'short' : 3, 'long' : 7}, 
    'PICNIC_BASKET1' : {'short' : 3, 'long' : 7}, 
    'PICNIC_BASKET2' : {'short' : 3, 'long' : 7}, 
}

###### MOMENTUM PARAMS ######
mom_max_vol = {
    'KELP' : 10, 
    'RAINFOREST_RESIN' : 10, 
    'SQUID_INK' : 10, 
    'JAMS' : 10, 
    'CROISSANTS' : 10, 
    'DJEMBES' : 10, 
    'PICNIC_BASKET1' : 10, 
    'PICNIC_BASKET2' : 10, 
}


###### FAIR_MM PARAMS ######
fmm_max_vol = {
    'KELP' : 10, 
    'RAINFOREST_RESIN' : 10, 
    'SQUID_INK' : 10, 
    'JAMS' : 10, 
    'CROISSANTS' : 10, 
    'DJEMBES' : 10, 
    'PICNIC_BASKET1' : 10, 
    'PICNIC_BASKET2' : 10, 
}

###### TRENDFOLLOW PARAMS #######
tf_max_vol = {
    'KELP' : 10, 
    'RAINFOREST_RESIN' : 10, 
    'SQUID_INK' : 10, 
    'JAMS' : 10, 
    'CROISSANTS' : 10, 
    'DJEMBES' : 10, 
    'PICNIC_BASKET1' : 10, 
    'PICNIC_BASKET2' : 10, 
}

###### ORDERBOOK IMBALANCE PARAMS #########
obimb_max_vol = {
    'KELP' : 10, 
    'RAINFOREST_RESIN' : 10, 
    'SQUID_INK' : 10, 
    'JAMS' : 10, 
    'CROISSANTS' : 10, 
    'DJEMBES' : 10, 
    'PICNIC_BASKET1' : 10, 
    'PICNIC_BASKET2' : 10, 
}

imbalance_thresholds = {
    'KELP' : 0.3, 
    'RAINFOREST_RESIN' : 0.3, 
    'SQUID_INK' : 0.3, 
    'JAMS' : 0.3, 
    'CROISSANTS' : 0.3, 
    'DJEMBES' : 0.3, 
    'PICNIC_BASKET1' : 0.3, 
    'PICNIC_BASKET2' : 0.3, 
}

###### KELNER PARAMS #######
kel_max_vol = {
    'KELP' : 10, 
    'RAINFOREST_RESIN' : 10, 
    'SQUID_INK' : 10, 
    'JAMS' : 10, 
    'CROISSANTS' : 10, 
    'DJEMBES' : 10, 
    'PICNIC_BASKET1' : 10, 
    'PICNIC_BASKET2' : 10, 
}

kel_atr_scale = {
    'KELP' : 1.5, 
    'RAINFOREST_RESIN' : 1.5, 
    'SQUID_INK' : 1.5, 
    'JAMS' : 1.5, 
    'CROISSANTS' : 1.5, 
    'DJEMBES' : 1.5, 
    'PICNIC_BASKET1' : 1.5, 
    'PICNIC_BASKET2' : 1.5, 
}


###### AVELLANEDA PARAMS ##########
trading_time = 1e6

gamma = {
    'KELP' : 1e-9, 
    'RAINFOREST_RESIN' : 1e-9, 
    'SQUID_INK' : 1e-9, 
    'JAMS' : 1e-9, 
    'CROISSANTS' : 1e-9, 
    'DJEMBES' : 1e-9, 
    'PICNIC_BASKET1' : 1e-9, 
    'PICNIC_BASKET2' : 1e-9, 
}

deviation_threshold = {
    'KELP' : 35, 
    'RAINFOREST_RESIN' : 45, 
    'SQUID_INK' : 30, 
    'JAMS' : 40, 
    'CROISSANTS' : 40, 
    'DJEMBES' : 40, 
    'PICNIC_BASKET1' : 40, 
    'PICNIC_BASKET2' : 40, 
}
############# END OF PARAMS ###############


class Trader:
    def __init__(self):
        """ Storing all the params locally for speed """
        self.products = list(products)
        self.product_params = {'max_position' : dict(max_position), 
                               'b_window_size' : dict(b_window_size), 
                               'ema_alpha' : dict(ema_alpha), 
                               'z_max_volume' : dict(z_max_volume), 
                               'cross_windows' : dict(cross_windows), 
                               'mom_max_vol' : dict(mom_max_vol), 
                               'fmm_max_vol' : dict(fmm_max_vol), 
                               'tf_max_vol' : dict(tf_max_vol), 
                               'obimb_max_vol' : dict(obimb_max_vol), 
                               'imbalance_thresholds' : dict(imbalance_thresholds), 
                               'kel_max_vol' : dict(kel_max_vol), 
                               'kel_atr_scale' : dict(kel_atr_scale), 
                               'trading_time' : trading_time, 
                               'price_history' : dict(price_history), 
                               'cooldown' : dict(cooldown), 
                               'cooldown_period' : dict(cooldown_period), 
                               'mid_price' : dict(mid_price), 
                               'gamma' : dict(gamma), 
                               'alpha' : dict(ema_alpha), 
                               'deviation_threshold' : dict(deviation_threshold),
                                'pair_products': pair_products,
                                'pair_params': pair_params,
                               }
        self.product_strategy = {
                'KELP' : 'AVELLANEDA',              ##curentbest IDK
                'RAINFOREST_RESIN' : 'AVELLANEDA',  ##curentbest AVELLANEDA
                'SQUID_INK' : 'BOLLINGER',         ##curentbest BOLLINGER
                'JAMS' : 'AVELLANEDA',              ##curentbest IDK
                'CROISSANTS' : 'PAIR_TRADING',        ##curentbest IDK
                'DJEMBES' : 'PAIR_TRADING',           ##curentbest IDK
                'PICNIC_BASKET1' : 'AVELLANEDA',    ##curentbest IDK
                'PICNIC_BASKET2' : 'AVELLANEDA',    ##curentbest IDK
                'PICNIC_BASKET1': 'PAIR_TRADING',
                'CROISSANTS': 'PAIR_TRADING',
            }
        self.strategy = {
            'AVELLANEDA' : self.avellaneda,
            'BOLLINGER' : self.bollinger_strategy,
            'BREAKOUT' : self.breakout_strategy,
            'MOVEAVG' : self.moving_average_strategy,
            'ZSCORE' : self.zscore_strategy,
            'CROSSOVER' : self.crossover_strategy,
            'MOMENTUM' : self.momentum_strategy,
            'FAIRPRICE' : self.fair_price_mm_strategy,
            'IMBALANCE' : self.orderbook_imbalance_strategy,
            'PAIR_TRADING': self.pair_trading_strategy,
            'KELTNER' : self.keltner_channel_strategy,
        }
        
    
    def run(self, state: TradingState):
        result = {}
        # conversions = []
        for product in products:
            if product not in state.listings:
                continue
            order = self.strategy[self.product_strategy[product]](product, state.order_depths[product], state.position.get(product,0), state.timestamp)
            if len(order) > 0:
                result[product] = order
            # conversions.append(converts)
            
        for pair in pair_products:
            product1, product2 = pair
            # if product1 not in state.listings or product2 not in state.listings:
            #     continue 
            order1,order2 = self.pair_trading_strategy(product1,product2, state.order_depths[product1],state.order_depths[product2], state.position.get(product1,0),state.position.get(product2,0), state.timestamp)
            if len(order1) > 0:
                result[product1] = order1
            if len(order2) > 0:
                result[product2] = order2
            

        logger.flush(state, result, 0, "")
        return result, 0, ""



    ######### STRATEGIES #######
    def avellaneda(self, product, order_depth, current_position, timestamp):
        orders = []
        
        # Get order book prices
        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2

        self.product_params['price_history'][product].append(mid_price)
        realized_vol = self.calculate_volatility(self.product_params['price_history'][product])
        effective_sigma = realized_vol
        
        k = self.calculate_k(order_depth, mid_price)
        gamma = max(self.product_params['gamma'][product]/(1+ 20 * realized_vol), 1e-10)

        # Spread calculation with dynamic volatility
        time_left = (self.product_params['trading_time'] - timestamp)/self.product_params['trading_time']
        spread = (gamma * (effective_sigma**2) * time_left) + \
            (2/gamma) * math.log(1 + gamma/k)            
        market_spread = best_ask - best_bid

        rest_price = mid_price - current_position * gamma * (effective_sigma**2) * time_left
        
        bid_price = int(rest_price - spread/2)
        ask_price = int(rest_price + spread/2)

        # inventory_ratio = abs(current_position) / self.product_params['max_position'][product]
        # aggression_factor = 1 + 3.5*inventory_ratio  # ranges from 1 to 3

        # 2. Add new limit orders if no matches
        num_levels = 3  # Number of price levels
        level_spacing = min(spread , market_spread)/(2*num_levels)
        
        # Clear existing positions if needed
        # print(self.product_params['max_position'][product])
        remaining_buy = self.product_params['max_position'][product] - current_position
        remaining_sell = self.product_params['max_position'][product] + current_position

        status, ewma_mid = self.detect_fake(product, mid_price)

        if status == "cooldown":
            # logger.print(f"{product} in cooldown — not quoting")
            return [] # Don't quote during cooldown

        elif status == "fake":
            # logger.print(f"{product} FAKE detected at {mid_price}, smoothed {ewma_mid}")
            # Reversion bet: fade the move
            # position = state.position.get(product, 0)
            
            if mid_price < ewma_mid:
                # Price spiked down — BUY
                orders.append(Order(product, int(mid_price), remaining_buy))
            else:
                # Price spiked up — SELL
                orders.append(Order(product, int(mid_price), -remaining_sell))

                return orders


        # 1. Take existing liquidity
        for ask, vol in sorted(order_depth.sell_orders.items()):
            if ask <= bid_price:
                max_buy = min(self.product_params['max_position'][product] - current_position, -vol)
                if max_buy > 0:
                    orders.append(Order(product, ask, max_buy))
                    remaining_buy -= max_buy
                    current_position += max_buy

        for bid, vol in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid >= ask_price:
                max_sell = min(self.product_params['max_position'][product] + current_position, vol)
                if max_sell > 0:
                    orders.append(Order(product, bid, -max_sell))
                    remaining_sell -=max_sell
                    current_position -= max_sell


        if remaining_buy > 0 or remaining_sell > 0:
            for i in range(num_levels):
                # Calculate level prices
                bid_level_price = int(rest_price - (i + 1) * level_spacing)
                ask_level_price = int(rest_price + (i + 1) * level_spacing)
                
                # Calculate size for each level (decreasing with distance)
                level_factor = (num_levels - i) / num_levels
                bid_size = int(remaining_buy * level_factor / num_levels)
                ask_size = int(remaining_sell * level_factor / num_levels)
                
                # Place orders if size > 0
                if bid_size > 0:
                    orders.append(Order(product, bid_level_price, bid_size))
                if ask_size > 0:
                    orders.append(Order(product, ask_level_price, -ask_size))

        # logger.print("-----------------------",bid_price, ask_price, rest_price,k,"------------------------")
    
        return orders

    def bollinger_strategy(self, product, order_depth, current_position, timestamp):
        p = self.product_params
        orders = []

        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # logger.print("-----------------------",product,best_ask,best_bid,"------------------------")
        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2
        p['price_history'][product].append(mid_price)
        logger.print("-----------------------",product, len(p['price_history'][product]),p['b_window_size'][product],"------------------------")
        if len(p['price_history'][product]) < p['b_window_size'][product]:
            return []

        prices = list(p['price_history'][product])
        # mean = np.mean(prices)    #idk using mean is asssss here and giving max loss
        std = np.std(prices)
        spread = (1+ 100 * std)* std/2
        market_spread = best_ask - best_bid

        # inventory_ratio = abs(current_position) / self.product_params['max_position'][product]
        # aggression_factor = 1 + 3.5*inventory_ratio  # ranges from 1 to 3

        # 2. Add new limit orders if no matches
        num_levels = 3  # Number of price levels
        level_spacing = min(spread , market_spread)/(2*num_levels)
        
        # Clear existing positions if needed
        # print(self.product_params['max_position'][product])
        remaining_buy = self.product_params['max_position'][product] - current_position
        remaining_sell = self.product_params['max_position'][product] + current_position

        status, ewma_mid = self.detect_fake(product, mid_price)

        logger.print(mid_price, ewma_mid)
        rest_price = ewma_mid
        
        bid_price = int(rest_price - spread/2)
        ask_price = int(rest_price + spread/2)
        if status == "cooldown":
            logger.print(f"{product} in cooldown — not quoting")
            return [] # Don't quote during cooldown

        elif status == "fake":
            logger.print(f"{product} FAKE detected at {mid_price}, smoothed {ewma_mid}")
            # Reversion bet: fade the move
            # position = state.position.get(product, 0)
            
            # logger.print("FAKE DETECTED")
            if mid_price < ewma_mid:
                # Price spiked down — BUY
                orders.append(Order(product, int(mid_price), remaining_buy))
            else:
                # Price spiked up — SELL
                orders.append(Order(product, int(mid_price), -remaining_sell))

                return orders


        # 1. Take existing liquidity
        for ask, vol in sorted(order_depth.sell_orders.items()):
            if ask <= bid_price:
                max_buy = min(self.product_params['max_position'][product] - current_position, -vol)
                if max_buy > 0:
                    orders.append(Order(product, ask, -max_buy))
                    remaining_buy -= max_buy
                    current_position += max_buy

        for bid, vol in sorted(order_depth.buy_orders.items(), reverse=True):
            if bid >= ask_price:
                max_sell = min(self.product_params['max_position'][product] + current_position, vol)
                if max_sell > 0:
                    orders.append(Order(product, bid, max_sell))
                    remaining_sell -=max_sell
                    current_position -= max_sell


        if remaining_buy > 0 or remaining_sell > 0:
            for i in range(num_levels):
                # Calculate level prices
                bid_level_price = int(rest_price - (i + 1) * level_spacing)
                ask_level_price = int(rest_price + (i + 1) * level_spacing)
                
                # Calculate size for each level (decreasing with distance)
                level_factor = (num_levels - i) / num_levels
                bid_size = int(remaining_buy * level_factor / num_levels)
                ask_size = int(remaining_sell * level_factor / num_levels)
                
                # Place orders if size > 0
                if bid_size > 0:
                    orders.append(Order(product, bid_level_price, bid_size))
                if ask_size > 0:
                    orders.append(Order(product, ask_level_price, -ask_size))

        # logger.print("-----------------------",bid_price, ask_price, rest_price,k,"------------------------")
    
        return orders


    def breakout_strategy(self, product, order_depth, current_position, timestamp):
        p = self.product_params
        p['price_history'][product].append(mid_price)
        if len(p['price_history'][product]) < p['b_window_size'][product]:
            return []

        prices = list(p['price_history'][product])[:-1]
        high = max(prices)
        low = min(prices)

        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2
        #logger.print(f"[{product}] Breakout: high={high:.2f}, low={low:.2f}, current={mid_price:.2f}")

        orders = []

        if mid_price > high:
            qty = min(10, p['max_position'][product] - current_position)
            #logger.print(f"[{product}] Breakout Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif mid_price < low:
            qty = min(10, p['max_position'][product] + current_position)
            #logger.print(f"[{product}] Breakout Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def moving_average_strategy(self, product, order_depth, current_position, timestamp):
        p = self.product_params
        p['price_history'][product].append(mid_price)
        if len(p['price_history'][product]) < p['b_window_size'][product]:
            return []

        avg = np.mean(p['price_history'][product])

        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2
        #logger.print(f"[{product}] Moving Average: mean={avg:.2f}, current={mid_price:.2f}")

        orders = []

        if mid_price > avg:
            qty = min(10, p['max_position'][product] - current_position)
            #logger.print(f"[{product}] MA Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif mid_price < avg:
            qty = min(10, p['max_position'][product] + current_position)
            #logger.print(f"[{product}] MA Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def zscore_strategy(self, product, order_depth, current_position, timestamp):
        p = self.product_params
        p['price_history'][product].append(mid_price)
        if len(p['price_history'][product]) < p['b_window_size'][product]:
            return []

        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2

        mean = np.mean(p['price_history'][product])
        std = np.std(p['price_history'][product])
        z = (mid_price - mean) / std if std else 0
        #logger.print(f"[{product}] Z-Score: {z:.2f}")

        orders = []

        if z < 1:
            qty = min(25, p['max_position'][product] - current_position)
            #logger.print(f"[{product}] Z-Score Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif z > 1:
            qty = min(25, p['max_position'][product] + current_position)
            #logger.print(f"[{product}] Z-Score Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def crossover_strategy(self, product, order_depth, current_position, timestamp):
        #logger.print(f"[{product}] Crossover: short={short:.2f}, long={long:.2f}")

        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2
        p = self.product_params
        p['price_history'][product].append(mid_price)
        if len(p['price_history'][product]) < 7:
            return []

        short = np.mean(list(p['price_history'][product])[-p['cross_windows'][product]['short']:])
        long = np.mean(list(p['price_history'][product])[-p['cross_windows'][product]['long']:])
        orders = []

        if short > long:
            qty = min(10, p['max_position'][product] - current_position)
            #logger.print(f"[{product}] Crossover Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif short < long:
            qty = min(10, p['max_position'][product] + current_position)
            #logger.print(f"[{product}] Crossover Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def momentum_strategy(self, product, order_depth, current_position, timestamp):
        p = self.product_params
        if len(p['price_history'][product]) < 4:
            return []

        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2

        p['price_history'][product].append(mid_price)

        changes = [p['price_history'][product][i] - p['price_history'][product][i - 1] for i in range(1, len(p['price_history'][product]))]
        #logger.print(f"[{product}] Momentum changes: {changes[-4:]}")

        orders = []

        if changes[-1] > 0 and changes[-2] > 0:
            qty = min(10, p['max_position'][product] - current_position)
            p['buy_price'][product] = mid_price
            #logger.print(f"[{product}] Momentum Buy {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), qty))
        elif all(c < 0 for c in changes[-3:]) or (p['buy_price'][product] and mid_price < 0.8 * p['buy_price'][product]):
            qty = min(10, p['max_position'][product] + current_position)
            p['buy_price'][product] = None
            #logger.print(f"[{product}] Momentum Sell {qty} at {mid_price}")
            orders.append(Order(product, int(mid_price), -qty))

        return orders

    def fair_price_mm_strategy(self, product, order_depth, current_position, timestamp):
        best_bid = max(order_depth.buy_orders.keys(), default=0)
        best_ask = min(order_depth.sell_orders.keys(), default=0)
        if best_bid == 0 or best_ask == 0:
            return []

        fair_price = (best_bid + best_ask) / 2
        #logger.print(f"[{product}] Fair Price MM: best_bid={best_bid}, best_ask={best_ask}, fair_price={fair_price}")

        orders = []
        max_position = self.product_params[product]['max_position']

        buy_qty = min(10, max_position - current_position)
        sell_qty = min(10, max_position + current_position)

        orders.append(Order(product, int(fair_price - 1), buy_qty))
        orders.append(Order(product, int(fair_price + 1), -sell_qty))

        #logger.print(f"[{product}] Market Making Buy {buy_qty} at {int(fair_price - 1)}")
        #logger.print(f"[{product}] Market Making Sell {sell_qty} at {int(fair_price + 1)}")
        return orders

    def orderbook_imbalance_strategy(self, product, order_depth, current_position, timestamp):
        orders = []
        bids = order_depth.buy_orders
        asks = order_depth.sell_orders
        best_bid = max(bids.keys(), default=0)
        best_ask = min(asks.keys(), default=0)
        bid_volume = sum(bids.values())
        ask_volume = sum(abs(v) for v in asks.values())
        total_volume = bid_volume + ask_volume
        imbalance = (bid_volume - ask_volume) / total_volume if total_volume != 0 else 0
        ##logger.print(f"[{product}] Orderbook Imbalance: {imbalance:.2f}")

        max_position = self.product_params[product]['max_position']

        if imbalance > self.product_params['imbalance_thresholds'][product]:
            volume = min(max_position - current_position, 10)
            orders.append(Order(product, best_ask, volume))
            ##logger.print(f"[{product}] Buying {volume} at {best_ask} due to OB imbalance")
        elif imbalance < -self.product_params['imbalance_thresholds'][product]:
            volume = min(max_position + current_position, 10)
            orders.append(Order(product, best_bid, -volume))
            ##logger.print(f"[{product}] Selling {volume} at {best_bid} due to OB imbalance")

        return orders

    def keltner_channel_strategy(self, product, order_depth, current_position, timestamp):
        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return []
            
        mid_price = (best_bid + best_ask) / 2
        
        p = self.product_params
        p['price_history'][product].append(mid_price)
        if len(p['price_history'][product]) < 10:
            return []

        ema = sum(p['price_history'][product]) / len(p['price_history'][product])
        # atr = sum(abs(p['price_history'][product][i] - p['price_history'][product][i - 1]) for i in range(1, len(p['price_history'][product]))) / (len(p['price_history'][product]) - 1)
        atr=np.std(self.product_params['price_history'][product])
        upper_band = ema + 1.5* atr
        lower_band = ema - 1.5* atr
        #
        # #logger.print(f"[{product}] Keltner Channel: EMA={ema:.2f}, ATR={atr:.2f}, Upper={upper_band:.2f}, Lower={lower_band:.2f}")

        orders = []
        max_position = p['max_position'][product]

        if mid_price < lower_band:
            qty = min(10, max_position - current_position)
            orders.append(Order(product, int(mid_price), qty))
            ##logger.print(f"[{product}] Buy {qty} at {mid_price} (Below Keltner Lower Band)")
        elif mid_price > upper_band:
            qty = min(10, max_position + current_position)
            orders.append(Order(product, int(mid_price), -qty))
            ##logger.print(f"[{product}] Sell {qty} at {mid_price} (Above Keltner Upper Band)")

        return orders

    def pair_trading_strategy(self, product1, product2, order_depth1, order_depth2, current_position1, current_position2, timestamp):
        # Only execute for the first product in each pair to avoid duplicate orders
        orders1 = []
        orders2 = []
        p = self.product_params
        
        pair_key = (product1, product2)
        params = self.product_params['pair_params'][pair_key]
        
        # Get prices for both products
        depth1 = order_depth1  # Already passed in
        depth2 = order_depth2
        
        # Calculate mid prices for product1
        if order_depth1.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth1.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth1.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth1.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth1.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth1.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return [], []
            
        mid1 = (best_bid + best_ask) / 2

        if order_depth2.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth2.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth2.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth2.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth2.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth2.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return [], []
            
        mid2 = (best_bid + best_ask) / 2
        
        mean1 = np.mean(p['price_history'][product1])
        std1 = np.std(p['price_history'][product1])
        z1 = abs((mid1/mean1)- std1 )
        
        mean2 = np.mean(p['price_history'][product2])
        std2 = np.std(p['price_history'][product2])
        z2 = abs(mid2/mean2-std2)
        # Store price pair
        params['history'].append((mid1, mid2))

    # Safety check: Ensure both order books have data
        if not order_depth1.buy_orders or not order_depth1.sell_orders or not order_depth2.buy_orders or not order_depth2.sell_orders:
            return [], []  # Skip if we don't have price data
        
        # Calculate relative performance to determine which product is outperforming
        window_size = 5  # Look at last 5 data points for performance comparison
        
        # if len(params['history']) >= window_size:
        #     # Get price data from window_size periods ago
        #     p1_start, p2_start = params['history'][-window_size]
        #     p1_end, p2_end = params['history'][-1]
            
        #     # Calculate percentage changes
        #     p1_change = (p1_end / p1_start) - 1
        #     p2_change = (p2_end / p2_start) - 1
            
            # Determine which product is outperforming
        outperforming = product1 if z1 > z2 else product2
        underperforming = product2 if outperforming == product1 else product1
            
        remaining_buy1 = self.product_params['max_position'][product1] - current_position1
        remaining_sell1 = self.product_params['max_position'][product1] + current_position1

        remaining_buy2 = self.product_params['max_position'][product2] - current_position2
        remaining_sell2 = self.product_params['max_position'][product2] + current_position2
        
        if z1>1:
            orders2.append(Order(product2, int(mid2), remaining_buy2))
        elif z1<1:
            orders2.append(Order(product2, int(mid2), -remaining_sell2))
        
        if z2>1:
            orders1.append(Order(product1, int(mid1), remaining_buy1))
        elif z2<1:
            orders1.append(Order(product1, int(mid1), -remaining_sell1))

        
        return orders1, orders2


    ####### END OF STRATEGIES #########













    ###### ALL UTILITY FUNCTIONS #######

    def calculate_volatility(self, price_history: deque) -> float:              
        """Calculates volatility / sigma parameter on the fly"""
        if len(price_history) < 2:
            return 0  # Not enough data
        
        returns = []
        prev_price = price_history[0]
        for price in list(price_history)[1:]:
            returns.append(math.log(price / prev_price))
            prev_price = price
            
        if len(returns) < 1:
            return 0
            
        std_dev = np.std(returns)
        return std_dev
        
    def calculate_k(self, order_depth: OrderDepth, mid_price: float) -> float:
        """ Calculates OrderBook Depth / K Param on the fly"""
        
        def estimate_k_from_side(levels, side: str) -> float | None:
            deltas = []
            log_volumes = []
            for price, volume in levels:
                if side == "bid" and volume <= 0:
                    continue
                if side == "ask" and volume >= 0:
                    continue
                vol = abs(volume)
                delta = abs(price - mid_price)
                if vol > 0 and delta > 0:
                    deltas.append(delta)
                    log_volumes.append(math.log(vol))
            
            if len(deltas) >= 2:
                # Fit log(volume) = log(V0) - k * delta  -->  y = -k * x + b
                A = np.vstack([deltas, np.ones(len(deltas))]).T
                slope, _ = np.linalg.lstsq(A, -np.array(log_volumes), rcond=None)[0]
                if 0.01 <= slope <= 10:  # Optional sanity check
                    return slope
            return None

        bids = sorted(order_depth.buy_orders.items(), reverse=True)[:5]
        asks = sorted(order_depth.sell_orders.items())[:5]

        k_values = []
        k_bid = estimate_k_from_side(bids, "bid")
        if k_bid is not None:
            k_values.append(k_bid)

        k_ask = estimate_k_from_side(asks, "ask")
        if k_ask is not None:
            k_values.append(k_ask)

        return float(np.mean(k_values)) if k_values else 1.5  # Default fallback

    def detect_fake(self, product, mid_price): 
        """ Detects a fake crash / drop like in round 1 day 1 dataset 

            Also returns the smoothed out mid_price for safe algo logic     
        
            """
        smoothed = self.product_params['mid_price'][product]
        ewma_mid = self.product_params['alpha'][product] * mid_price + (1 - self.product_params['alpha'][product]) * smoothed
        self.product_params['mid_price'][product] = ewma_mid
        
        deviation = abs(mid_price - ewma_mid)

        # Cooldown active? Don't quote
        if self.product_params['cooldown'][product] > 0:
            self.product_params['cooldown'][product] -= 1
            return "cooldown", ewma_mid

        # Detect large deviation without trade confirmation (simplified condition)
        if deviation > self.product_params['deviation_threshold'][product] :
            self.product_params['cooldown'][product] = self.product_params['cooldown_period'][product]
            return "fake", ewma_mid

        return "normal", ewma_mid

    def volume_weighted_mid(self, order_depth: OrderDepth, product):
        if order_depth.buy_orders:
            # Find bid with maximum volume
            max_bid_volume = max(order_depth.buy_orders.values())
            candidate_bids = [price for price, vol in order_depth.buy_orders.items() if vol == max_bid_volume]
            best_bid = max(candidate_bids)  # Highest price among max volume bids
        else:
            best_bid = 0

        if order_depth.sell_orders:
            # Find ask with maximum volume (using absolute value)
            max_ask_volume = max(abs(vol) for vol in order_depth.sell_orders.values())
            candidate_asks = [price for price, vol in order_depth.sell_orders.items() if abs(vol) == max_ask_volume]
            best_ask = min(candidate_asks)  # Lowest price among max volume asks
        else:
            best_ask = float('inf')

        # Only proceed if we have valid prices
        if best_bid == 0 or best_ask == float('inf'):
            return self.self.product_params['mid_price'][product][product]
            
        mid_price = (best_bid + best_ask) / 2

        return mid_price

