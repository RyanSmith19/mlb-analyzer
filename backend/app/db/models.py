"""Initial persisted source data and ingestion bookkeeping."""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MlbPayload(Base):
    __tablename__ = "mlb_payloads"
    __table_args__ = (UniqueConstraint("kind", "resource_key", name="uq_mlb_payload_resource"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_key: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlayerRecord(Base):
    __tablename__ = "players"

    mlb_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(160))
    bats: Mapped[str | None] = mapped_column(String(1))
    throws: Mapped[str | None] = mapped_column(String(1))


class TeamRecord(Base):
    __tablename__ = "teams"

    mlb_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(160))


class GameRecord(Base):
    __tablename__ = "games"

    mlb_id: Mapped[int] = mapped_column(primary_key=True)
    game_date: Mapped[date | None] = mapped_column(Date)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.mlb_id"))
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.mlb_id"))
    status: Mapped[str | None] = mapped_column(String(80))


class AppearanceRecord(Base):
    __tablename__ = "appearances"
    __table_args__ = (UniqueConstraint("game_id", "player_id", "role", name="uq_appearance_player_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.mlb_id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.mlb_id"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.mlb_id"))
    role: Mapped[str] = mapped_column(String(16), nullable=False)


class StatcastPitchRecord(Base):
    __tablename__ = "statcast_pitches"
    __table_args__ = (
        UniqueConstraint("game_id", "at_bat_number", "pitch_number", name="uq_statcast_pitch_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(Integer, nullable=False)
    at_bat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pitch_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pitcher_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hitter_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    pitcher_hand: Mapped[str] = mapped_column(String(1), nullable=False)
    batter_side: Mapped[str] = mapped_column(String(1), nullable=False)
    pitch_type: Mapped[str] = mapped_column(String(8), nullable=False)
    velocity_mph: Mapped[float | None] = mapped_column(Float)
    horizontal_movement_ft: Mapped[float | None] = mapped_column(Float)
    vertical_movement_ft: Mapped[float | None] = mapped_column(Float)
    zone: Mapped[int | None] = mapped_column(Integer)
    plate_x_ft: Mapped[float | None] = mapped_column(Float)
    plate_z_ft: Mapped[float | None] = mapped_column(Float)
    balls: Mapped[int | None] = mapped_column(Integer)
    strikes: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(80), nullable=False)
    event: Mapped[str | None] = mapped_column(String(80))
    exit_velocity_mph: Mapped[float | None] = mapped_column(Float)
    launch_angle_deg: Mapped[float | None] = mapped_column(Float)
    estimated_woba: Mapped[float | None] = mapped_column(Float)
    woba_value: Mapped[float | None] = mapped_column(Float)
    woba_denominator: Mapped[float | None] = mapped_column(Float)
    launch_speed_angle: Mapped[int | None] = mapped_column(Integer)
    source_fields: Mapped[dict | None] = mapped_column(JSON)


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"
    __table_args__ = (
        UniqueConstraint("profile_kind", "player_id", "split_key", "model_version", "through_date", name="uq_profile_snapshot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    split_key: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    through_date: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
