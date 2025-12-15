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
            ema_period: Period for EMA Trend Bias (default: 50)
            pivot_length: Lookback/Lookforward for swing detection (default: 5)
            risk_reward: Minimum Risk:Reward ratio (default: 2.0)
            bias_method: 'ORIGINAL', 'SIMPLE', 'SLOPE' (default: 'SIMPLE')
            sl_atr_multiplier: Multiplier for ATR based stop loss (default: 1.5)
        """
        # Combine defaults from __init__ with any arguments passed directly to initialize
        params = {**self.default_params, **kwargs}
        
        self.ema_period = params.get('ema_period', 50)
        self.pivot_length = params.get('pivot_length', 5)
        self.min_risk_reward = params.get('risk_reward', 2.0)
        self.bias_method = params.get('bias_method', 'SIMPLE') # 'ORIGINAL', 'SIMPLE', 'SLOPE'
        self.sl_atr_multiplier = params.get('sl_atr_multiplier', 1.5)
        
        # State
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.bullish_structure = MarketStructure()
        self.bearish_structure = MarketStructure()
        
        self.last_trade_index = -1
        
        print(f"LiquidityCatcher Initialized: EMA={self.ema_period}, Pivot={self.pivot_length}, Bias={self.bias_method}")

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
                if current_price > last_lower_high:
                    self.bullish_structure.bos_detected = True
                    self.bullish_structure.bos_level = last_lower_high
                    self.bullish_structure.confirmation_bars = 0
                    # Reset confirmed flag until we get a pullback/confirmation candle
                    self.bullish_structure.bos_confirmed = False
        else:
            self.bullish_structure.confirmation_bars += 1
            if self.bullish_structure.confirmation_bars > 20: # Timeout
                 self.bullish_structure.reset()

        # --- Bearish BOS Logic ---
        # Break below the last Higher Low
        if not self.bearish_structure.bos_detected:
            if len(self.swing_lows) >= 2:
                last_higher_low = self.swing_lows[0].price
                
                if current_price < last_higher_low:
                    self.bearish_structure.bos_detected = True
                    self.bearish_structure.bos_level = last_higher_low
                    self.bearish_structure.confirmation_bars = 0
                    self.bearish_structure.bos_confirmed = False
        else:
            self.bearish_structure.confirmation_bars += 1
            if self.bearish_structure.confirmation_bars > 20:
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
        # Assuming we just need to be above the BOS level to show strength? 
        # Actually MQL5 says: if(ask < entryZone + minEntryDistance) return;
        # So it WANTS price to be ABOVE the BOS level (breakout continuation) OR above HL.
        entry_zone = self.bullish_structure.last_higher_low
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
        
        # 1. Try Swing Level
        if ref_level > 0:
            if is_buy:
                sl = ref_level * 0.9995 # Little buffer
            else:
                sl = ref_level * 1.0005
                
        # 2. Check ATR validity (Safety check) or if ref level invalid
        # Simple ATR calc
        high_low = data['High'] - data['Low']
        high_close = (data['High'] - data['Close'].shift()).abs()
        low_close = (data['Low'] - data['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().iloc[-1]
        
        if atr > 0:
            atr_sl_dist = atr * self.sl_atr_multiplier
            
            if is_buy:
                atr_sl = price - atr_sl_dist
                # If swing SL is too far or invalid, use ATR
                if sl == 0 or (price - sl) > (atr_sl_dist * 2): 
                    sl = atr_sl
                # Ensure SL is below price
                sl = min(sl, price - atr_sl_dist * 0.5) 
            else:
                atr_sl = price + atr_sl_dist
                if sl == 0 or (sl - price) > (atr_sl_dist * 2):
                    sl = atr_sl
                sl = max(sl, price + atr_sl_dist * 0.5)
                
        return sl
