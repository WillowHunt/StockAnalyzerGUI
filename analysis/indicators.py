import pandas as pd
import ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"]

    df["sma_20"] = ta.trend.sma_indicator(close, window=20)
    df["sma_50"] = ta.trend.sma_indicator(close, window=50)
    df["sma_200"] = ta.trend.sma_indicator(close, window=200)
    df["ema_12"] = ta.trend.ema_indicator(close, window=12)
    df["ema_26"] = ta.trend.ema_indicator(close, window=26)
    df["rsi_14"] = ta.momentum.rsi(close, window=14)

    macd = ta.trend.MACD(close)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    bb = ta.volatility.BollingerBands(close)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()

    atr = ta.volatility.AverageTrueRange(df["High"], df["Low"], close, window=14)
    df["atr_14"] = atr.average_true_range()

    stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], close, window=14, smooth_window=3)
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()

    return df
