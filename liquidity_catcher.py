"""
Liquidity Catcher Strategy
==========================

A Python implementation of the Liquidity Catcher strategy (originally MQL5).
This strategy trades based on Market Structure Shifts (BOS) and Swing Points,
filtered by an EMA Trend Bias.

Key Components:
- Swing High/Low Detection: Identifies pivots prices.
- Market Structure: Tracks Higher Highs/Lows (Bullish) and Lower Highs/Lows (Bearish).
- BOS (Break of Structure): Detects when price breaks key structure levels.
- EMA Bias: Filters trades based on trend direction.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from strategy_interface import BaseStrategy, Signal, SignalType

@dataclass
class SwingPoint:
    price: float
    index: int
    timestamp: any
    is_high: bool

@dataclass
class MarketStructure:
    is_bullish: bool = False
    bos_detected: bool = False
    bos_confirmed: bool = False
    bos_level: float = 0.0
    last_higher_low: float = 0.0
    last_lower_high: float = 0.0
    confirmation_bars: int = 0
    
    def reset(self):
        self.is_bullish = False
        self.bos_detected = False
        self.bos_confirmed = False
        self.bos_level = 0.0
        self.last_higher_low = 0.0
        self.last_lower_high = 0.0
        self.confirmation_bars = 0

class LiquidityCatcherStrategy(BaseStrategy):
    """
    Liquidity Catcher Strategy tailored for Python BacktestEngine.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize strategy with optional parameters.
        Parameters passed here will be used as defaults for initialize().
        """
        super().__init__()
        self.default_params = kwargs
        
    def initialize(self, **kwargs) -> None:
        """
        Initialize strategy parameters.
        
        Args:
            pivot_length (int): Lookback for swing detection (InpPivotLength). Default: 14
            ema_period (int): Period for EMA Bias (InpEMAPeriod). Default: 200
            risk_percent (float): Risk % per trade (InpRiskPercent). Default: 0.5
            max_risk_usd (float): Max $ risk per trade (InpMaxRiskPerTradeUSD). Default: 100.0
            sl_mode (str): 'ATR' or 'SWING' (InpSLMode). Default: 'ATR'
            atr_period (int): ATR period (InpATRPeriod). Default: 14
            sl_atr_multiplier (float): ATR multiplier (InpATRMul). Default: 1.2
            swing_buffer_pips (float): Buffer pips for swing SL (InpSwingBufferPips). Default: 5.0
            fallback_sl_pips (int): Fallback SL in pips (InpStopLossPips). Default: 50
            min_risk_reward (float): Minimum Risk:Reward (InpMinRiskReward). Default: 1.5
            fallback_tp_pips (int): Fallback TP in pips (InpTPPips). Default: 100
            use_breakeven (bool): Move to BE (InpUseBreakeven). Default: True
            breakeven_trigger_pct (float): % of TP to trigger BE (InpBreakevenPercent). Default: 50.0
            breakeven_plus_pips (int): Pips to add to BE (InpBreakevenPlusPips). Default: 2
            partial_close_pct (float): % to close (InpPartialClosePercent). Default: 50.0
            min_pivots_for_bos (int): Min pivots to confirm structure (InpMinPivotsForBOS). Default: 3
            bos_confirmation_bars (int): Bars to confirm BOS (InpBOSConfirmationBars). Default: 3
            require_higher_low (bool): Require HL for Buy (InpRequireHigherLow). Default: True
            min_bos_break_pips (float): Min pips break for BOS (InpMinBOSBreakPips). Default: 5.0
            min_bars_between_trades (int): Min bars delay (InpMinBarsBetweenTrades). Default: 5
            max_daily_trades (int): Max trades/day (InpMaxDailyTrades). Default: 3
            max_spread_pips (float): Max spread (InpMaxSpreadPips). Default: 2.5
            enable_prints (bool): Debug prints (InpEnablePrints). Default: True
            magic_number (int): Unique ID (InpMagicNumber). Default: 789456
            trade_comment (str): Trade comment (InpTradeComment). Default: "BOS_Entry"
            pip_value (float): Value of one pip. Default: 0.0001
        """
        # Combine defaults from __init__ with any arguments passed directly to initialize
        params = {**self.default_params, **kwargs}
        
        # --- Core Parameters ---
        self.pivot_length = params.get('pivot_length', 14)
        self.ema_period = params.get('ema_period', 200)
        self.require_bias = params.get('require_bias', True)
        self.bias_method = params.get('bias_method', 'SIMPLE') # Keep for compatibility
        
        # --- Risk & Money Management ---
        self.risk_percent = params.get('risk_percent', 0.5)
        self.max_risk_usd = params.get('max_risk_usd', 100.0)
        
        # --- SL/TP Settings ---
        self.sl_mode = params.get('sl_mode', 'ATR')
        self.atr_period = params.get('atr_period', 14)
        self.sl_atr_multiplier = params.get('sl_atr_multiplier', 1.2)
        self.swing_buffer_pips = params.get('swing_buffer_pips', 5.0)
        self.fallback_sl_pips = params.get('fallback_sl_pips', 50)
        self.min_risk_reward = params.get('min_risk_reward', 1.5)
        self.fallback_tp_pips = params.get('fallback_tp_pips', 100)
        
        # --- Trade Management ---
        self.use_breakeven = params.get('use_breakeven', True)
        self.breakeven_trigger_pct = params.get('breakeven_trigger_pct', 50.0)
        self.breakeven_plus_pips = params.get('breakeven_plus_pips', 2)
        self.partial_close_pct = params.get('partial_close_pct', 50.0)
        
        # --- Strategy Logic ---
        self.min_pivots_for_bos = params.get('min_pivots_for_bos', 3)
        self.bos_confirmation_bars = params.get('bos_confirmation_bars', 3)
        self.require_higher_low = params.get('require_higher_low', True)
        self.min_bos_break_pips = params.get('min_bos_break_pips', 5.0)
        self.min_bars_between_trades = params.get('min_bars_between_trades', 5)
        self.max_daily_trades = params.get('max_daily_trades', 3)
        self.max_spread_pips = params.get('max_spread_pips', 2.5)
        self.pip_value = params.get('pip_value', 0.0001)
        
        # --- Misc ---
        self.enable_prints = params.get('enable_prints', True)
        self.magic_number = params.get('magic_number', 789456)
        self.trade_comment = params.get('trade_comment', "BOS_Entry")

        # State initialization
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.bullish_structure = MarketStructure()
        self.bearish_structure = MarketStructure()
        
        self.last_trade_index = -1
        self.daily_trade_count = 0
        self.current_day = None
        
        if self.enable_prints:
            print(f"LiquidityCatcher Initialized: EMA={self.ema_period}, Pivot={self.pivot_length}, Risk={self.risk_percent}%")

    def get_name(self) -> str:
        return "Liquidity Catcher Python"

    def on_bar(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Main strategy logic executed on every bar.
        """
        if len(data) < self.ema_period + 50:
            return None
            
        current_idx = len(data) - 1
        current_price = data['Close'].iloc[-1]
        current_time = data.index[-1]
        
        # Check day change for max daily trades
        if self.current_day != current_time.date():
            self.current_day = current_time.date()
            self.daily_trade_count = 0
            
        # Filter: Max Daily Trades
        if self.daily_trade_count >= self.max_daily_trades:
            return None
            
        # Filter: Min Bars Between Trades
        if self.last_trade_index != -1 and (current_idx - self.last_trade_index) < self.min_bars_between_trades:
            return None
        
        # 1. Update Indicators
        ema = data['Close'].ewm(span=self.ema_period, adjust=False).mean()
        current_ema = ema.iloc[-1]
        
        # 2. Detect Swings (Pivots)
        # We check if a pivot formed 'pivot_length' bars ago.
        # This is because we need future bars to confirm it was a pivot.
        self._detect_swings(data, current_idx)
        
        # 3. Analyze Market Structure (HH/HL, LH/LL)
        self._analyze_structure()
        
        # 4. Detect Break of Structure (BOS)
        self._detect_bos(data)
        
        # 5. Check Bias
        bias = self._get_bias(current_price, current_ema, ema)
        if bias == 0:
            return None
            
        # 6. Check Signals
        signal = None
        
        # We only check for signals if we have confirmed structure or valid setups
        # MQL5: CheckBuySetupBOS / CheckSellSetupBOS
        
        # --- BUY SETUP ---
        if bias == 1:
            signal = self._check_buy_setup(data, current_price, current_time)
            
        # --- SELL SETUP ---
        if bias == -1 and signal is None:
            signal = self._check_sell_setup(data, current_price, current_time)
            
        return signal

    def _get_bias(self, price: float, ema: float, ema_series: pd.Series) -> int:
        """
        Determine market bias based on EMA.
        Returns: 1 (Bullish), -1 (Bearish), 0 (Neutral)
        """
        if self.bias_method == 'SIMPLE':
            # Simple price vs EMA
            return 1 if price > ema else -1
            
        elif self.bias_method == 'SLOPE':
            # Check EMA slope
            if len(ema_series) < 2: return 0
            prev_ema = ema_series.iloc[-2]
            return 1 if ema > prev_ema else -1
            
        elif self.bias_method == 'ORIGINAL':
            # MQL5 original logic: price must be outside a small band
            # if(price > ema * 1.0005) return 1;
            # if(price < ema * 0.9995) return -1;
            upper_band = ema * 1.0005
            lower_band = ema * 0.9995
            
            if price > upper_band: return 1
            if price < lower_band: return -1
            return 0
            
        return 0

    def _detect_swings(self, data: pd.DataFrame, current_idx: int):
        """
        Check if a swing point is confirmed at index (current - pivot_length).
        """
        lookback = self.pivot_length
        if current_idx < lookback * 2 + 1:
            return
            
        # The candidate pivot bar is 'lookback' bars ago from now
        candidate_idx = current_idx - lookback
        
        # Data slice centered on candidate
        # Range: [candidate - lookback, candidate + lookback] inclusive
        start_check = candidate_idx - lookback
        end_check = candidate_idx + lookback
        
        # Check High (Swing High)
        highs = data['High'].iloc[start_check : end_check + 1]
        candidate_high = data['High'].iloc[candidate_idx]
        
        if candidate_high == highs.max():
            # Check strictly if it's the unique max or just a max
            # MQL5 usually checks if it's highest.
            # Avoid duplicates if multiple bars equal max? MQL5 FindPivotHigh checks bounds.
            # Assuming simple max for now.
            
            # Add to swing highs
            sp = SwingPoint(candidate_high, candidate_idx, data.index[candidate_idx], True)
            self.swing_highs.insert(0, sp) # Start of list is newest
            if len(self.swing_highs) > 50: self.swing_highs.pop()
            
        # Check Low (Swing Low)
        lows = data['Low'].iloc[start_check : end_check + 1]
        candidate_low = data['Low'].iloc[candidate_idx]
        
        if candidate_low == lows.min():
            sp = SwingPoint(candidate_low, candidate_idx, data.index[candidate_idx], False)
            self.swing_lows.insert(0, sp)
            if len(self.swing_lows) > 50: self.swing_lows.pop()

    def _analyze_structure(self):
        """
        Analyze recent swings to determine if we are tracking HH/HL or LH/LL.
        """
        # Need at least 2 swings of each
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return

        # Bullish Structure: Higher Highs AND Higher Lows
        recent_high = self.swing_highs[0].price
        prev_high = self.swing_highs[1].price
        recent_low = self.swing_lows[0].price
        prev_low = self.swing_lows[1].price
        
        is_hh = recent_high > prev_high
        is_hl = recent_low > prev_low
        
        if is_hh and is_hl:
            self.bullish_structure.is_bullish = True
            self.bullish_structure.last_higher_low = recent_low
            
        # Bearish Structure: Lower Highs AND Lower Lows
        is_lh = recent_high < prev_high
        is_ll = recent_low < prev_low
        
        if is_lh and is_ll:
            self.bearish_structure.is_bullish = False # Confirmed bearish
            self.bearish_structure.last_lower_high = recent_high

    def _detect_bos(self, data: pd.DataFrame):
        """
        Detect Break of Structure events.
        """
        current_price = data['Close'].iloc[-1]
        
        # --- Bullish BOS Logic ---
        # Break above the last Lower High (which was the structure point in bearish trend)
        if not self.bullish_structure.bos_detected:
            if len(self.swing_highs) >= 2:
                last_lower_high = self.swing_highs[0].price
                # MQL5 check: if logic requires us to be 'in bearish structure' first?
                # "Precisamos estar em estrutura bearish primeiro" (We need to be in bearish structure first)
                # But simplified: if we break a significant high.
                
                # Check confirmation: Close > Last LH
            # Check confirmation: Close > Last LH
                # Apply min break pips filter
                break_threshold = last_lower_high + (self.min_bos_break_pips * self.pip_value)
                
                if current_price > break_threshold:
                    self.bullish_structure.bos_detected = True
                    self.bullish_structure.bos_level = last_lower_high
                    self.bullish_structure.confirmation_bars = 0
                    self.bullish_structure.bos_confirmed = False
        else:
            self.bullish_structure.confirmation_bars += 1
            if self.bullish_structure.confirmation_bars > self.bos_confirmation_bars:
                 self.bullish_structure.bos_confirmed = True
            
            # Reset if structure fails (handled by reversal logic or simpler timeouts)
            # For now keeping simple timeout
            if self.bullish_structure.confirmation_bars > 50: # Timeout hardcoded
                 self.bullish_structure.reset()

        # --- Bearish BOS Logic ---
        # Break below the last Higher Low
        if not self.bearish_structure.bos_detected:
            if len(self.swing_lows) >= 2:
                last_higher_low = self.swing_lows[0].price
                
            # Check confirmation: Close < Last HL
                break_threshold = last_higher_low - (self.min_bos_break_pips * self.pip_value)
                
                if current_price < break_threshold:
                    self.bearish_structure.bos_detected = True
                    self.bearish_structure.bos_level = last_higher_low
                    self.bearish_structure.confirmation_bars = 0
                    self.bearish_structure.bos_confirmed = False
        else:
            self.bearish_structure.confirmation_bars += 1
            if self.bearish_structure.confirmation_bars > self.bos_confirmation_bars:
                self.bearish_structure.bos_confirmed = True

            if self.bearish_structure.confirmation_bars > 50:
                self.bearish_structure.reset()

    def _check_buy_setup(self, data: pd.DataFrame, price: float, time: any) -> Optional[Signal]:
        """
        Check for Buy entry conditions.
        """
        # Must have detected a BOS upwards
        if not self.bullish_structure.bos_detected:
            return None
            
        # MQL5: "More flexible entry: allow entries above BOS level"
        # Condition 1: Candle confirmation (Bullish Close)
        open_price = data['Open'].iloc[-1]
        if not (price > open_price):
            return None
            
        # Condition 2: Price > Entry Zone (BOS Level or HL)
        entry_zone = self.bullish_structure.last_higher_low
        
        # Logic: Require HL
        if self.require_higher_low and entry_zone == 0:
            return None
            
        if entry_zone == 0: entry_zone = self.bullish_structure.bos_level
        
        if price < entry_zone:
            return None
            
        # SL Calculation
        sl = self._calculate_sl(is_buy=True, price=price, ref_level=self.bullish_structure.last_higher_low, data=data)
        
        # TP Calculation
        tp = 0.0
        # Target recent swing high
        if len(self.swing_highs) > 0 and self.swing_highs[0].price > price:
            tp = self.swing_highs[0].price
        else:
            risk = price - sl
            tp = price + (risk * self.min_risk_reward)
            
        # RR Check
        risk = price - sl
        reward = tp - price
        if risk <= 0: return None
        rr = reward / risk
        
        if rr < self.min_risk_reward:
             return None
             
        # Generate Signal
        # Reset BOS detected to avoid double entry on same setup? MQL5 does strict reset.
        self.bullish_structure.bos_detected = False 
        
        self.last_trade_index = len(data) - 1
        
        return Signal(
            signal_type=SignalType.BUY,
            timestamp=time,
            price=price,
            metadata={'sl': sl, 'tp': tp, 'rr': rr}
        )

    def _check_sell_setup(self, data: pd.DataFrame, price: float, time: any) -> Optional[Signal]:
        """
        Check for Sell entry conditions.
        """
        if not self.bearish_structure.bos_detected:
            return None
            
        open_price = data['Open'].iloc[-1]
        # Bearish Candle Confirmation
        if not (price < open_price):
            return None
            
        entry_zone = self.bearish_structure.last_lower_high
        
        # Logic: Require LH (Symmetric to HL)
        if self.require_higher_low and entry_zone == 0:
            return None
            
        if entry_zone == 0: entry_zone = self.bearish_structure.bos_level
        
        # Price should be BELOW the entry zone
        if price > entry_zone:
            return None
            
        sl = self._calculate_sl(is_buy=False, price=price, ref_level=self.bearish_structure.last_lower_high, data=data)
        
        tp = 0.0
        if len(self.swing_lows) > 0 and self.swing_lows[0].price < price:
            tp = self.swing_lows[0].price
        else:
            risk = sl - price
            tp = price - (risk * self.min_risk_reward)
            
        risk = sl - price
        reward = price - tp
        if risk <= 0: return None
        rr = reward / risk
        
        if rr < self.min_risk_reward:
            return None
            
        self.bearish_structure.bos_detected = False
        
        self.last_trade_index = len(data) - 1
        
        return Signal(
            signal_type=SignalType.SELL,
            timestamp=time,
            price=price,
            metadata={'sl': sl, 'tp': tp, 'rr': rr}
        )

    def _calculate_sl(self, is_buy: bool, price: float, ref_level: float, data: pd.DataFrame) -> float:
        """
        Calculate Stop Loss based on Swing level or ATR.
        """
        sl = 0.0
        pip_v = self.pip_value
        
        # 1. Try Swing Level
        if self.sl_mode == 'SWING' and ref_level > 0:
            buffer = self.swing_buffer_pips * pip_v
            if is_buy:
                sl = ref_level - buffer
            else:
                sl = ref_level + buffer
                
        # 2. ATR Calculation (used if mode is ATR or SWING invalid)
        high_low = data['High'] - data['Low']
        high_close = (data['High'] - data['Close'].shift()).abs()
        low_close = (data['Low'] - data['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_series = tr.rolling(window=self.atr_period).mean()
        
        if len(atr_series) > 0:
            atr = atr_series.iloc[-1]
        else:
            atr = 0.0
        
        if atr > 0:
            atr_sl_dist = atr * self.sl_atr_multiplier
            
            if self.sl_mode == 'ATR' or sl == 0:
                # Use ATR SL
                if is_buy:
                    sl = price - atr_sl_dist
                else:
                    sl = price + atr_sl_dist
            elif self.sl_mode == 'SWING':
                # Validating Swing SL limits with ATR could be added here
                # For now, if Swing is chosen and valid, we use it.
                pass

        # 3. Fallback fixed pips if everything failed
        if sl == 0:
            fixed_dist = self.fallback_sl_pips * pip_v
            if is_buy:
                sl = price - fixed_dist
            else:
                sl = price + fixed_dist

        return sl

    def on_signal_executed(self, signal: Signal, execution_price: float) -> None:
        """
        Callback when signal is executed.
        """
        self.daily_trade_count += 1
        pass

