from datetime import date, datetime
from sqlalchemy import Integer, String, Float, Date, DateTime, func
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
