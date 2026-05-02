from datamodel import TradingState, Order
import json
import numpy as np


class Trader:
    ACTIVE_SYMBOLS = [
            'GALAXY_SOUNDS_DARK_MATTER', #0 -
            'GALAXY_SOUNDS_BLACK_HOLES', #1 -
            'GALAXY_SOUNDS_PLANETARY_RINGS',#2 -
            'GALAXY_SOUNDS_SOLAR_WINDS', #3 -
            'GALAXY_SOUNDS_SOLAR_FLAMES', #4
            'SLEEP_POD_SUEDE', #5
            'SLEEP_POD_LAMB_WOOL', #6
            'SLEEP_POD_POLYESTER', #7
            'SLEEP_POD_NYLON', #8
            'SLEEP_POD_COTTON', #9
            'MICROCHIP_CIRCLE', #10
            'MICROCHIP_OVAL', #11
            'MICROCHIP_SQUARE', #12
            'MICROCHIP_RECTANGLE', #13
            'MICROCHIP_TRIANGLE', #14
            'PEBBLES_XS', #15
            'PEBBLES_S', #16
            'PEBBLES_M', #17
            'PEBBLES_L', #18
            'PEBBLES_XL', #19
            'ROBOT_VACUUMING', #20
            'ROBOT_MOPPING', #21
            'ROBOT_DISHES', #22
            'ROBOT_LAUNDRY', #23
            'ROBOT_IRONING', #24
            'UV_VISOR_YELLOW', #25
            'UV_VISOR_AMBER', #26
            'UV_VISOR_ORANGE', #27
            'UV_VISOR_RED', #28
            'UV_VISOR_MAGENTA', #29
            'TRANSLATOR_SPACE_GRAY', #30
            'TRANSLATOR_ASTRO_BLACK', #31
            'TRANSLATOR_ECLIPSE_CHARCOAL', #32
            'TRANSLATOR_GRAPHITE_MIST', #33
            'TRANSLATOR_VOID_BLUE', #34
            'PANEL_1X2', #35
            'PANEL_2X2', #36
            'PANEL_1X4', #37
            'PANEL_2X4', #38
            'PANEL_4X4', #39
            'OXYGEN_SHAKE_MORNING_BREATH', #40
            'OXYGEN_SHAKE_EVENING_BREATH', #41
            'OXYGEN_SHAKE_MINT', #42
            'OXYGEN_SHAKE_CHOCOLATE', #43
            'OXYGEN_SHAKE_GARLIC', #44
            'SNACKPACK_CHOCOLATE', #45
            'SNACKPACK_VANILLA', #46
            'SNACKPACK_PISTACHIO', #47
            'SNACKPACK_STRAWBERRY', #48
            'SNACKPACK_RASPBERRY' #49
    ]

    CONSTANTS = {
        "limit": 10,
        "gamma": 0.003,
        "alpha": 1,
    }

    logs = []

    def log(self, *new_log):
        for l in new_log:
            self.logs.append(l)

    def new_history(self):
        return {
            "prices": [],
            "res_price": [],
            "ema": None,
            "signal_strength": 0,
            "pending_extreme": "",
            "neutral_ticks": 0,
        }

    def ensure_history(self, hist):
        defaults = self.new_history()

        if not isinstance(hist, dict):
            hist = {}

        for key, value in defaults.items():
            if key not in hist:
                hist[key] = value.copy() if isinstance(value, list) else value

        return hist

    def basic_analysis(self, order_depth, prices, position, prev_ema, alpha, gamma):
        bid_prices = sorted(order_depth.buy_orders.keys(), reverse=True)
        ask_prices = sorted(order_depth.sell_orders.keys())

        if not bid_prices or not ask_prices:
            return None

        best_bid = bid_prices[0]
        best_ask = ask_prices[0]
        mid_price = (best_bid + best_ask) / 2

        prices.append(float(mid_price))

        total_vbid = 0
        total_vask = 0

        for i, bid_price in enumerate(bid_prices):
            total_vbid += order_depth.buy_orders[bid_price] * (1 / (1 + i))

        for i, ask_price in enumerate(ask_prices):
            total_vask += abs(order_depth.sell_orders[ask_price]) * (1 / (1 + i))

        if total_vbid + total_vask > 0:
            micro_price = (
                best_bid * total_vask + best_ask * total_vbid
            ) / (total_vbid + total_vask)
        else:
            micro_price = mid_price

        volatility = float(np.std(prices[-100:]))

        if len(prices) < 50:
            ema = float(np.mean(prices))
        elif len(prices) < 200:
            ema = float(np.mean(prices[-50:]))
        else:
            prev = prev_ema if prev_ema is not None else mid_price
            ema = float(mid_price * alpha + prev * (1 - alpha))

        res_price = float(ema - position * gamma * (volatility ** 2))

        self.log(best_bid, best_ask, mid_price, res_price, micro_price, volatility)

        return best_bid, best_ask, ema, res_price, volatility

    def trade_signal(self, hist, volatility):
        res = hist["res_price"]
        mids = hist["prices"]

        if len(res) < 30 or len(mids) < 8:
            signal = 0
            signal_strength = 0
            self.log(signal)
            return signal, signal_strength

        def slope(series, window):
            return (series[-1] - series[-window]) / (window - 1)

        short = 4
        medium = 10
        long = 25

        vel_short = slope(res, short)
        vel_medium = slope(res, medium)

        prev_vel_short = (res[-2] - res[-short - 1]) / (short - 1)
        accel = vel_short - prev_vel_short

        impulse_move = res[-1] - res[-long]
        impulse_size = abs(impulse_move)

        recent_res_changes = [
            abs(res[i] - res[i - 1])
            for i in range(len(res) - 20, len(res))
        ]

        avg_step = float(np.mean(recent_res_changes)) if recent_res_changes else 1
        impulse_threshold = max(volatility * 0.8, avg_step * 6, 3)

        large_selloff = impulse_move < -impulse_threshold
        large_rally = impulse_move > impulse_threshold

        downside_slowing = (
            vel_medium < 0
            and vel_short > vel_medium
            and accel > 0
        )

        upside_slowing = (
            vel_medium > 0
            and vel_short < vel_medium
            and accel < 0
        )

        mid_changes = [
            mids[-7] - mids[-8],
            mids[-6] - mids[-7],
            mids[-5] - mids[-6],
            mids[-4] - mids[-5],
            mids[-3] - mids[-4],
            mids[-2] - mids[-3],
            mids[-1] - mids[-2],
        ]

        mid_up_count = sum(1 for change in mid_changes if change > 0)
        mid_down_count = sum(1 for change in mid_changes if change < 0)

        mid_move = mids[-1] - mids[-8]
        min_mid_move = max(1, volatility * 0.12)

        mid_rising = mid_up_count >= 4 and mid_move >= min_mid_move
        mid_falling = mid_down_count >= 4 and mid_move <= -min_mid_move

        recent_high = max(res[-long:])
        recent_low = min(res[-long:])
        recent_range = recent_high - recent_low
        range_large = recent_range >= max(volatility * 1.2, 5)

        strong_minima = (
            large_selloff
            and downside_slowing
            and mid_rising
            and range_large
        )

        strong_maxima = (
            large_rally
            and upside_slowing
            and mid_falling
            and range_large
        )

        maxima_score = 0
        minima_score = 0

        if strong_maxima:
            maxima_score += impulse_size * 0.4 + abs(accel) * 2 + abs(mid_move) * 0.6

        if strong_minima:
            minima_score += impulse_size * 0.4 + abs(accel) * 2 + abs(mid_move) * 0.6

        min_strength = max(0.1, volatility * 0.02)

        # +1 means MAXIMA forming.
        # -1 means MINIMA forming.
        if maxima_score > minima_score and maxima_score > min_strength:
            signal = +1
            signal_strength = maxima_score
        elif minima_score > maxima_score and minima_score > min_strength:
            signal = -1
            signal_strength = minima_score
        else:
            signal = 0
            signal_strength = 0

        self.log(signal)
        return signal, signal_strength

    def update_extreme_phase(self, hist, signal):
        confirm_neutral_ticks = 4

        pending = hist.get("pending_extreme", "")
        neutral_ticks = hist.get("neutral_ticks", 0)

        if signal == +1:
            hist["pending_extreme"] = "MAXIMA"
            hist["neutral_ticks"] = 0
            return "FORMING_MAXIMA_HOLD"

        if signal == -1:
            hist["pending_extreme"] = "MINIMA"
            hist["neutral_ticks"] = 0
            return "FORMING_MINIMA_HOLD"

        if pending:
            neutral_ticks += 1
            hist["neutral_ticks"] = neutral_ticks

            if neutral_ticks >= confirm_neutral_ticks:
                event = "CONFIRMED_" + pending
                hist["pending_extreme"] = ""
                hist["neutral_ticks"] = 0
                return event

            return "TAKE?HOLD_" + pending

        hist["neutral_ticks"] = 0
        return "HOLD"

    def alpha_sniping(
        self,
        symbol,
        order_depth,
        signal,
        signal_strength,
        hist,
        res_price,
        orders,
        buy_volume,
        sell_volume,
        position,
        limit,
    ):
        ask_prices = sorted(order_depth.sell_orders.keys())
        bid_prices = sorted(order_depth.buy_orders.keys(), reverse=True)

        if not ask_prices or not bid_prices:
            self.log("INCOMPLETE_BOOK")
            return

        best_ask = ask_prices[0]
        best_bid = bid_prices[0]
        spread = best_ask - best_bid

        event = self.update_extreme_phase(hist, signal)
        event_log = event

        volatility = np.std(hist["prices"][-50:]) if len(hist["prices"]) > 2 else 1

        is_maxima_phase = event in [
            "FORMING_MAXIMA_HOLD",
            "TAKE?HOLD_MAXIMA",
            "CONFIRMED_MAXIMA",
        ]

        is_minima_phase = event in [
            "FORMING_MINIMA_HOLD",
            "TAKE?HOLD_MINIMA",
            "CONFIRMED_MINIMA",
        ]

        buy_left = max(0, buy_volume)
        sell_left = max(0, sell_volume)

        def take_asks(max_price, volume):
            filled = 0

            for ask_price in ask_prices:
                if ask_price > max_price or volume <= 0:
                    break

                vol = min(abs(order_depth.sell_orders[ask_price]), volume)

                if vol > 0:
                    orders.append(Order(symbol, ask_price, vol))
                    volume -= vol
                    filled += vol

            return filled

        def hit_bids(min_price, volume):
            filled = 0

            for bid_price in bid_prices:
                if bid_price < min_price or volume <= 0:
                    break

                vol = min(abs(order_depth.buy_orders[bid_price]), volume)

                if vol > 0:
                    orders.append(Order(symbol, bid_price, -vol))
                    volume -= vol
                    filled += vol

            return filled

        aggressive_size = 2
        mm_size = 5

        mispricing_threshold = max(spread * 0.6, volatility * 1.0, 6)

        if (
            best_ask <= res_price - mispricing_threshold
            and not is_maxima_phase
            and buy_left > 0
        ):
            volume = min(aggressive_size, buy_left, limit - position)
            filled = take_asks(int(res_price - mispricing_threshold), volume)

            if filled > 0:
                buy_left -= filled
                event_log += "|AGG_BUY_MISPRICE"

        if (
            best_bid >= res_price + mispricing_threshold
            and not is_minima_phase
            and sell_left > 0
        ):
            volume = min(aggressive_size, sell_left, limit + position)
            filled = hit_bids(int(res_price + mispricing_threshold), volume)

            if filled > 0:
                sell_left -= filled
                event_log += "|AGG_SELL_MISPRICE"

        edge = max(2, int(volatility * 0.8))

        my_bid = int(min(best_bid + 1, res_price - edge))
        my_ask = int(max(best_ask - 1, res_price + edge))

        if position > 0:
            my_bid -= 1 + position // 3
            my_ask -= 1
        elif position < 0:
            my_ask += 1 + abs(position) // 3
            my_bid += 1

        buy_size = min(mm_size, buy_left, limit - position)
        sell_size = min(mm_size, sell_left, limit + position)

        if is_maxima_phase:
            buy_size = 0
            my_ask = max(best_bid + 1, min(best_ask - 1, my_ask))

        elif is_minima_phase:
            sell_size = 0
            my_bid = min(best_ask - 1, max(best_bid + 1, my_bid))

        if buy_size > 0 and my_bid > 0 and my_bid < best_ask:
            orders.append(Order(symbol, my_bid, buy_size))
            event_log += "|MM_BID"

        if sell_size > 0 and my_ask > best_bid:
            orders.append(Order(symbol, my_ask, -sell_size))
            event_log += "|MM_ASK"

        self.log(event_log)

    def trader(self, symbol, constants, position, hist, order_depth, trader_orders):
        analysis = self.basic_analysis(
            order_depth=order_depth,
            prices=hist["prices"],
            position=position,
            alpha=constants["alpha"],
            gamma=constants["gamma"],
            prev_ema=hist.get("ema"),
        )

        if analysis is None:
            return

        best_bid, best_ask, ema, res_price, volatility = analysis

        hist["ema"] = ema
        hist["res_price"].append(res_price)

        signal, signal_strength = self.trade_signal(hist, volatility)
        hist["signal_strength"] = signal_strength

        limit = constants["limit"]

        buy_room = max(0, limit - position)
        sell_room = max(0, limit + position)

        self.alpha_sniping(
            symbol=symbol,
            order_depth=order_depth,
            position=position,
            signal=signal,
            signal_strength=signal_strength,
            hist=hist,
            res_price=res_price,
            orders=trader_orders,
            buy_volume=buy_room,
            sell_volume=sell_room,
            limit=limit,
        )

        if len(hist["res_price"]) > 80:
            hist["res_price"].pop(0)

        if len(hist["prices"]) > 100:
            hist["prices"].pop(0)

    def run(self, state: TradingState):
        self.logs = []

        result = {symbol: [] for symbol in state.order_depths.keys()}

        try:
            hist_data = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            hist_data = {}

        for symbol in self.ACTIVE_SYMBOLS:
            if symbol not in state.order_depths:
                continue

            hist_data[symbol] = self.ensure_history(hist_data.get(symbol, {}))

            self.trader(
                symbol=symbol,
                constants=self.CONSTANTS,
                position=state.position.get(symbol, 0),
                hist=hist_data[symbol],
                order_depth=state.order_depths[symbol],
                trader_orders=result[symbol],
            )

            self.log(state.timestamp)

        print(",".join(str(log) for log in self.logs))

        try:
            trader_data = json.dumps(hist_data)
        except Exception:
            trader_data = ""

        conversions = 0
        return result, conversions, trader_data
