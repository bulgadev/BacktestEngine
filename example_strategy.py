"""
Example Strategy Module
=======================

This module contains example trading strategies that demonstrate how to
implement the BaseStrategy interface. These can be used as templates
for creating your own strategies.

Strategies included:
- SimpleMovingAverageStrategy: Basic MA crossover strategy
"""

import pandas as pd
import numpy as np
from typing import Optional

from strategy_interface import BaseStrategy, Signal, SignalType


class SimpleBuyHoldStrategy(BaseStrategy):
    """
    Simple Buy and Hold Strategy for testing.
    
    Buys on the first bar and holds until the end.
    This is useful for testing that the engine works correctly.
    """
    
    def __init__(self):
        super().__init__()
        self.bought = False
    
    def initialize(self, **kwargs) -> None:
        """Initialize strategy."""
        self.bought = False
    
    def on_bar(self, data: pd.DataFrame) -> Optional[Signal]:
        """Buy on first bar, then hold."""
        if not self.bought and len(data) >= 1:
            self.bought = True
            return Signal(
                signal_type=SignalType.BUY,
                timestamp=data.index[-1],
                price=data['Close'].iloc[-1]
            )
        return None
    
    def get_name(self) -> str:
        return "Buy and Hold Strategy"


class SimpleMovingAverageStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    
    This strategy generates signals based on the crossover of two moving averages:
    - When fast MA crosses above slow MA: BUY signal
    - When fast MA crosses below slow MA: SELL signal
    
    This is a classic trend-following strategy used for demonstration.
    """
    
    def __init__(self, fast_period: int = 10, slow_period: int = 30):
        """
        Initialize the strategy.
        
        Args:
            fast_period: Period for fast moving average (default: 10)
            slow_period: Period for slow moving average (default: 30)
        """
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def initialize(self, **kwargs) -> None:
        """
        Initialize strategy parameters.
        
        Can override fast_period and slow_period via kwargs.
        """
        if 'fast_period' in kwargs:
            self.fast_period = kwargs['fast_period']
        if 'slow_period' in kwargs:
            self.slow_period = kwargs['slow_period']
    
    def on_bar(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Process each bar and generate signals based on MA crossover.
        
        Args:
            data: DataFrame with OHLCV data up to current bar
            
        Returns:
            Signal if crossover detected, None otherwise
        """
        # Need enough data to calculate both MAs for current bar
        if len(data) < self.slow_period:
            return None
        
        close_prices = data['Close']
        
        # Calculate current bar's MAs (using all data up to current bar)
        current_fast_ma = close_prices.rolling(window=self.fast_period).mean().iloc[-1]
        current_slow_ma = close_prices.rolling(window=self.slow_period).mean().iloc[-1]
        
        # Need at least 2 bars with valid MAs to detect crossover
        # We need the previous bar's MA values to compare
        if len(data) < self.slow_period + 1:
            return None
        
        # Calculate previous bar's MAs (from data excluding the current/last bar)
        # This gives us the MA values from exactly one bar ago
        prev_close = close_prices.iloc[:-1]  # All bars except the last one
        prev_fast_ma = prev_close.rolling(window=self.fast_period).mean().iloc[-1]
        prev_slow_ma = prev_close.rolling(window=self.slow_period).mean().iloc[-1]
        
        current_price = close_prices.iloc[-1]
        current_time = data.index[-1]
        
        # Detect bullish crossover: fast MA crosses above slow MA
        # Previous bar: fast <= slow, Current bar: fast > slow
        if prev_fast_ma <= prev_slow_ma and current_fast_ma > current_slow_ma:
            return Signal(
                signal_type=SignalType.BUY,
                timestamp=current_time,
                price=current_price
            )
        
        # Detect bearish crossover: fast MA crosses below slow MA
        # Previous bar: fast >= slow, Current bar: fast < slow
        elif prev_fast_ma >= prev_slow_ma and current_fast_ma < current_slow_ma:
            return Signal(
                signal_type=SignalType.SELL,
                timestamp=current_time,
                price=current_price
            )
        
        # No crossover detected
        return None
    
    def get_name(self) -> str:
        """Return strategy name."""
        return f"Simple MA Strategy ({self.fast_period}/{self.slow_period})"


class RSIStrategy(BaseStrategy):
    """
    Relative Strength Index (RSI) Strategy.
    
    Generates signals based on RSI overbought/oversold conditions:
    - RSI < 30 (oversold): BUY signal
    - RSI > 70 (overbought): SELL signal
    
    This is a mean-reversion strategy.
    """
    
    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        """
        Initialize the strategy.
        
        Args:
            period: RSI calculation period (default: 14)
            oversold: RSI level for oversold condition (default: 30)
            overbought: RSI level for overbought condition (default: 70)
        """
        super().__init__()
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.previous_rsi = None
    
    def initialize(self, **kwargs) -> None:
        """Initialize strategy parameters."""
        if 'period' in kwargs:
            self.period = kwargs['period']
        if 'oversold' in kwargs:
            self.oversold = kwargs['oversold']
        if 'overbought' in kwargs:
            self.overbought = kwargs['overbought']
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """
        Calculate RSI indicator.
        
        Args:
            prices: Series of closing prices
            period: RSI period
            
        Returns:
            RSI value
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if len(rsi) > 0 else 50.0
    
    def on_bar(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Process each bar and generate signals based on RSI.
        
        Args:
            data: DataFrame with OHLCV data up to current bar
            
        Returns:
            Signal if RSI condition met, None otherwise
        """
        # Need enough data to calculate RSI
        if len(data) < self.period + 1:
            return None
        
        close_prices = data['Close']
        current_rsi = self._calculate_rsi(close_prices, self.period)
        current_price = close_prices.iloc[-1]
        current_time = data.index[-1]
        
        # Generate BUY signal when RSI crosses below oversold level
        if self.previous_rsi is not None:
            if self.previous_rsi >= self.oversold and current_rsi < self.oversold:
                self.previous_rsi = current_rsi
                return Signal(
                    signal_type=SignalType.BUY,
                    timestamp=current_time,
                    price=current_price
                )
            
            # Generate SELL signal when RSI crosses above overbought level
            elif self.previous_rsi <= self.overbought and current_rsi > self.overbought:
                self.previous_rsi = current_rsi
                return Signal(
                    signal_type=SignalType.SELL,
                    timestamp=current_time,
                    price=current_price
                )
        
        self.previous_rsi = current_rsi
        return None
    
    def get_name(self) -> str:
        """Return strategy name."""
        return f"RSI Strategy ({self.period}, {self.oversold}/{self.overbought})"

