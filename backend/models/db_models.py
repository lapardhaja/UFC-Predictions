from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    event_name: Mapped[str] = mapped_column(String(512), nullable=False)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_upcoming: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fights: Mapped[list["Fight"]] = relationship("Fight", back_populates="event")


class Fighter(Base):
    __tablename__ = "fighters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fighter_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    reach_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_lbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    stance: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    nc: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participations: Mapped[list["FightParticipation"]] = relationship(
        "FightParticipation", back_populates="fighter"
    )


class Fight(Base):
    __tablename__ = "fights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fight_id: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    winner_fighter_id: Mapped[int | None] = mapped_column(ForeignKey("fighters.id"), nullable=True)
    method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_str: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weight_class: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_title_fight: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped["Event"] = relationship("Event", back_populates="fights")
    winner: Mapped["Fighter | None"] = relationship("Fighter", foreign_keys=[winner_fighter_id])
    participations: Mapped[list["FightParticipation"]] = relationship(
        "FightParticipation", back_populates="fight", cascade="all, delete-orphan"
    )


class FightParticipation(Base):
    __tablename__ = "fight_participations"
    __table_args__ = (UniqueConstraint("fight_id", "fighter_id", name="uq_fight_fighter"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fight_id: Mapped[int] = mapped_column(ForeignKey("fights.id"), nullable=False)
    fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"), nullable=False)
    is_fighter_a: Mapped[bool] = mapped_column(Boolean, nullable=False)

    sig_strikes_landed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sig_strikes_attempted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_strikes_landed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_strikes_attempted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    takedowns_landed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    takedowns_attempted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submission_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    knockdowns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    control_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    fight: Mapped["Fight"] = relationship("Fight", back_populates="participations")
    fighter: Mapped["Fighter"] = relationship("Fighter", back_populates="participations")
