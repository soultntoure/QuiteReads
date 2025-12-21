"""Database models.

SQLAlchemy ORM definitions mapping domain entities to database tables.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base
from app.utils.types import AggregationStrategy, ExperimentStatus


class ExperimentModel(Base):
    """SQLAlchemy model for experiments.

    Stores both centralized and federated experiments with
    a discriminator column for type differentiation.
    """

    __tablename__ = "experiments"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Common fields
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    experiment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus), default=ExperimentStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Configuration (stored as JSON)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Final metrics (nullable until experiment completes)
    final_rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_mae: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    training_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Federated-specific fields (nullable for centralized)
    n_clients: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    n_rounds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aggregation_strategy: Mapped[Optional[AggregationStrategy]] = mapped_column(
        Enum(AggregationStrategy), nullable=True
    )

    # Relationships
    metrics: Mapped[list["MetricModel"]] = relationship(
        "MetricModel",
        back_populates="experiment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ExperimentModel(id={self.id}, name={self.name}, type={self.experiment_type})>"


class MetricModel(Base):
    """SQLAlchemy model for performance metrics.

    Stores per-epoch (centralized) or per-round/per-client (federated) metrics.
    """

    __tablename__ = "metrics"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to experiment
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )

    # Metric data
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 'rmse', 'mae', 'loss'
    value: Mapped[float] = mapped_column(Float, nullable=False)

    # Context fields
    context: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'global', 'client_1'
    round_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamp for ordering
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    # Relationship back to experiment
    experiment: Mapped["ExperimentModel"] = relationship(
        "ExperimentModel", back_populates="metrics"
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<MetricModel(name={self.name}, value={self.value}, round={self.round_number})>"
