from datetime import date, datetime
from sqlalchemy import Integer, String, Float, Date, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account: Mapped[str] = mapped_column(String, index=True)       # "Bank1", "Bank2", "CreditCard"
    date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)                    # negative=debit, positive=credit
    category: Mapped[str] = mapped_column(String, default="Uncategorized")
    source_file: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserProfile(Base):
    """Single-row settings table (always id=1)."""
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    alert_threshold: Mapped[float] = mapped_column(Float, default=500.0)       # flag adhoc purchases above this
    emergency_fund_target: Mapped[float] = mapped_column(Float, default=0.0)   # keep this untouched
    monthly_buffer: Mapped[float] = mapped_column(Float, default=200.0)        # safety buffer on top of emergency fund
    outstanding_debts: Mapped[str] = mapped_column(Text, default="[]")         # JSON: [{name, balance, rate}]
