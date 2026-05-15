from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False)
    name = Column(String(255))
    exchange = Column(String(50))
    currency = Column(String(10), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)

    prices = relationship("Price", back_populates="stock", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="stock", cascade="all, delete-orphan")


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    # Technical indicators
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    ema_12 = Column(Float)
    ema_26 = Column(Float)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    atr_14 = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)

    stock = relationship("Stock", back_populates="prices")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(Date, nullable=False)
    signal_type = Column(String(10), nullable=False)  # 'BUY' or 'SELL'
    indicator = Column(String(50), nullable=False)    # e.g. 'MACD', 'RSI', 'SMA_CROSS'
    price_at_signal = Column(Float)

    # Backtesting results
    outcome_date = Column(Date)
    outcome_price = Column(Float)
    outcome_pct = Column(Float)      # % gain/loss from signal to outcome
    is_success = Column(Boolean)     # True if signal was profitable

    stock = relationship("Stock", back_populates="signals")


class NewsArticle(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    source_symbol = Column(String(20))
    date = Column(DateTime)
    title = Column(String(500), nullable=False)
    source = Column(String(100))
    url = Column(String(1000), nullable=False)
    url_hash = Column(String(32), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("ticker", "url_hash", name="uq_news_ticker_url"),)
