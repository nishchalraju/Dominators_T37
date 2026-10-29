"""Importing this package registers every table with SQLAlchemy's metadata."""

from app.models.activity import ActivityLog
from app.models.case import CASE_STATUSES, Case
from app.models.dataset import DatasetInspection, DatasetRecord
from app.models.description import WitnessDescription
from app.models.evaluation import ModelEvaluation
from app.models.note import InvestigatorNote
from app.models.sketch import SketchVersion
from app.models.user import User

__all__ = [
    "ActivityLog",
    "CASE_STATUSES",
    "Case",
    "DatasetInspection",
    "DatasetRecord",
    "InvestigatorNote",
    "ModelEvaluation",
    "SketchVersion",
    "User",
    "WitnessDescription",
]
