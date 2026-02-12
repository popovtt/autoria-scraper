import datetime

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import mapped_column, Mapped

from src.models.base import Base


class CarOrm(Base):
    __tablename__ = "car"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, unique=True)

    title: Mapped[str] = mapped_column(String)
    price_usd: Mapped[int]
    odometer: Mapped[int]

    username: Mapped[str]
    phone_number: Mapped[str]

    image_url: Mapped[str]
    images_count: Mapped[int]

    car_number: Mapped[str]
    car_vin: Mapped[str]

    datetime_found: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.UTC
    )
