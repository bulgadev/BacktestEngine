"""
Data Fetcher Module
===================

This module handles fetching historical market data for backtesting.
Supports BTC (Bitcoin) and EURUSD (Euro/US Dollar) pairs.

Uses:
- ccxt library for crypto data (BTC) - free, cross-platform, unlimited historical data
- yfinance as fallback for forex data (EURUSD) - free, cross-platform
"""

import pandas as pd
from typing import Literal, Optional
from datetime import datetime, timedelta

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("Warning: ccxt not installed. Install with: pip install ccxt")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not installed. Install with: pip install yfinance")


class DataFetcher:
    """
    Fetches historical market data for backtesting.
    
    Supports:
    - BTC: Bitcoin/USD via ccxt (Binance, Coinbase, etc.)
    - EURUSD: Euro/US Dollar via yfinance
    
    Uses free APIs that work cross-platform (Windows, Mac, Linux).
    """
    
    # Mapping of interval strings to exchange timeframes
    TIMEFRAME_MAP = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d',
    }
    
    # Exchange to use for crypto (Binance is free and reliable)
    CRYPTO_EXCHANGE = 'binance'  # Can be changed to 'coinbase', 'kraken', etc.
    
    @staticmethod
    def fetch_data(
        symbol: Literal['BTC', 'EURUSD'],
        period: str = '1y',
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a given symbol.
        
        Args:
            symbol: Trading pair symbol ('BTC' or 'EURUSD')
            period: Time period ('1y', '6mo', '3mo', etc.) or '1y' for 1 year
            interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1d', etc.)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            Index is datetime
            
        Raises:
            ValueError: If symbol is not supported
            ImportError: If MetaTrader5 is not installed
        """
        # Convert period to date range
        end_date = datetime.now()
        if period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == '6mo':
            start_date = end_date - timedelta(days=180)
        elif period == '3mo':
            start_date = end_date - timedelta(days=90)
        elif period == '1mo':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=365)  # Default to 1 year
        
        return DataFetcher.fetch_data_by_dates(
            symbol=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval=interval
        )
    
    @staticmethod
    def fetch_data_by_dates(
        symbol: Literal['BTC', 'EURUSD'],
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Fetch historical data between specific dates.
        
        Uses ccxt for crypto (BTC) and yfinance for forex (EURUSD).
        Both are free and work cross-platform.
        
        Args:
            symbol: Trading pair symbol ('BTC' or 'EURUSD')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1d', etc.)
            
        Returns:
            DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
            Index is datetime
            
        Raises:
            ValueError: If symbol or interval is not supported
            ImportError: If required libraries are not installed
        """
        if interval not in DataFetcher.TIMEFRAME_MAP:
            raise ValueError(f"Unsupported interval: {interval}. Supported: {list(DataFetcher.TIMEFRAME_MAP.keys())}")
        
        # Convert dates
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Route to appropriate fetcher based on symbol
        if symbol == 'BTC':
            return DataFetcher._fetch_crypto_data('BTC', start_dt, end_dt, interval)
        elif symbol == 'EURUSD':
            return DataFetcher._fetch_forex_data('EURUSD', start_dt, end_dt, interval)
        else:
            raise ValueError(f"Unsupported symbol: {symbol}. Supported: ['BTC', 'EURUSD']")
    
    @staticmethod
    def _fetch_crypto_data(symbol: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp, interval: str) -> pd.DataFrame:
        """Fetch crypto data using ccxt (Binance, Coinbase, etc.)."""
        if not CCXT_AVAILABLE:
            raise ImportError(
                "ccxt library not installed. "
                "Install with: pip install ccxt"
            )
        
        # Initialize exchange (Binance is free and reliable)
        exchange = getattr(ccxt, DataFetcher.CRYPTO_EXCHANGE)({
            'enableRateLimit': True,  # Respect rate limits
        })
        
        # Map symbol to exchange symbol
        exchange_symbol = 'BTC/USDT'  # Binance uses BTC/USDT
        
        # Map interval to exchange timeframe
        timeframe = DataFetcher.TIMEFRAME_MAP[interval]
        
        print(f"Fetching {symbol} data from {start_dt.date()} to {end_dt.date()} ({interval}) via {DataFetcher.CRYPTO_EXCHANGE}...")
        
        # Convert to milliseconds (ccxt uses milliseconds)
        since = int(start_dt.timestamp() * 1000)
        until = int(end_dt.timestamp() * 1000)
        
        all_ohlcv = []
        current_since = since
        
        # Fetch data in chunks (some exchanges have limits per request)
        # Binance allows up to 1000 candles per request
        max_candles_per_request = 1000
        
        while current_since < until:
            try:
                # Fetch OHLCV data
                ohlcv = exchange.fetch_ohlcv(
                    exchange_symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=max_candles_per_request
                )
                
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Move to next chunk (use last candle's timestamp + 1)
                current_since = ohlcv[-1][0] + 1
                
                # If we got fewer candles than requested, we've reached the end
                if len(ohlcv) < max_candles_per_request:
                    break
                    
            except Exception as e:
                print(f"Error fetching data: {e}")
                break
        
        if not all_ohlcv:
            raise ValueError(f"No data retrieved for {symbol}")
        
        # Convert to DataFrame
        # OHLCV format: [timestamp, open, high, low, close, volume]
        data = pd.DataFrame(
            all_ohlcv,
            columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
        )
        
        # Convert timestamp to datetime index
        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
        data.set_index('timestamp', inplace=True)
        
        # Remove duplicates and sort
        data = data[~data.index.duplicated(keep='first')].sort_index()
        
        # Filter to exact date range
        data = data[(data.index >= start_dt) & (data.index <= end_dt)]
        
        # Remove any rows with NaN values
        data = data.dropna()
        
        print(f"Fetched {len(data)} bars from {data.index[0]} to {data.index[-1]}")
        
        return data
    
    @staticmethod
    def _fetch_forex_data(symbol: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp, interval: str) -> pd.DataFrame:
        """Fetch forex data using yfinance."""
        if not YFINANCE_AVAILABLE:
            raise ImportError(
                "yfinance library not installed. "
                "Install with: pip install yfinance"
            )
        
        # Map symbol to yfinance ticker
        ticker_map = {
            'EURUSD': 'EURUSD=X'
        }
        
        if symbol not in ticker_map:
            raise ValueError(f"Unsupported forex symbol: {symbol}")
        
        yf_symbol = ticker_map[symbol]
        
        # Map interval to yfinance interval
        # yfinance uses different interval format
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '1d': '1d',
        }
        
        if interval not in interval_map:
            raise ValueError(f"Unsupported interval for forex: {interval}")
        
        yf_interval = interval_map[interval]
        
        print(f"Fetching {symbol} data from {start_dt.date()} to {end_dt.date()} ({interval}) via yfinance...")
        
        # yfinance has limitations for intraday data, so we need to chunk
        total_days = (end_dt - start_dt).days
        
        # Determine chunk size based on interval
        if interval in ['1m', '5m']:
            chunk_days = 7  # yfinance limit
        elif interval in ['15m', '30m', '1h']:
            chunk_days = 60  # yfinance limit
        else:
            chunk_days = total_days + 1  # No limit for daily
        
        # If we can fetch in one request, do it
        if total_days <= chunk_days:
            data = yf.download(
                yf_symbol,
                start=start_dt.strftime('%Y-%m-%d'),
                end=end_dt.strftime('%Y-%m-%d'),
                interval=yf_interval,
                progress=False
            )
        else:
            # Fetch in chunks
            print(f"Note: Fetching in {chunk_days}-day chunks due to yfinance limitations...")
            all_data = []
            current_start = start_dt
            
            while current_start < end_dt:
                current_end = min(current_start + timedelta(days=chunk_days), end_dt)
                
                chunk_data = yf.download(
                    yf_symbol,
                    start=current_start.strftime('%Y-%m-%d'),
                    end=current_end.strftime('%Y-%m-%d'),
                    interval=yf_interval,
                    progress=False
                )
                
                if not chunk_data.empty:
                    all_data.append(chunk_data)
                    print(f"  Fetched chunk: {len(chunk_data)} bars")
                
                current_start = current_end - timedelta(days=1)
            
            if not all_data:
                raise ValueError(f"No data retrieved for {symbol}")
            
            data = pd.concat(all_data)
            data = data[~data.index.duplicated(keep='first')].sort_index()
        
        if data.empty:
            raise ValueError(f"No data retrieved for {symbol}")
        
        # Clean column names
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        
        # Select required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            # If Volume is missing, add it as 0
            if 'Volume' in missing_cols:
                data['Volume'] = 0
            else:
                raise ValueError(f"Missing required columns: {missing_cols}")
        
        data = data[required_cols].dropna()
        
        # Filter to exact date range
        data = data[(data.index >= start_dt) & (data.index <= end_dt)]
        
        print(f"Fetched {len(data)} bars from {data.index[0]} to {data.index[-1]}")
        
        return data

