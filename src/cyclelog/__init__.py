"""Cyclelog — personal housebike manager by Marwan Helmy."""

from __future__ import annotations

__version__ = "1.2.0"
__author__ = "Marwan Helmy"
__email__ = "marwanabdelaal25@gmail.com"

from cyclelog.errors import (
    CyclelogError,
    StorageError,
    ValidationError,
    NotFoundError,
    ImportPipelineError,
    ExportError,
    MigrationError,
    PluginError,
    ConflictError,
    format_error,
    is_not_found,
    is_validation,
)
from cyclelog.bike import Bike, PotInfo, HealthStatus, BikeCatalog
from cyclelog.make import MakeProfile, MakeCatalog, ServiceNeed, MileageNeed
from cyclelog.rack import Rack, RackRegistry, WindowDirection
from cyclelog.service import ServiceEvent, ServiceLog, ServiceQuality
from cyclelog.inspection_log import CareEvent, InspectionLog, CareEventType, OdometerSchedule
from cyclelog.schedule import ScheduleEngine, ScheduleEntry, ScheduleOptions, Season, compute_next_service
from cyclelog.tag import Tag, TagRegistry
from cyclelog.notes import Note, NotesCollection, NoteKind
from cyclelog.parser import (
    parse_date,
    parse_interval,
    parse_amount_ml,
    parse_light_level,
    parse_mileage,
    format_interval_days,
    format_amount_ml,
)
from cyclelog.validators import (
    validate_bike_name,
    validate_interval_days,
    validate_mileage_pct,
    validate_light_level,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # errors
    "CyclelogError",
    "StorageError",
    "ValidationError",
    "NotFoundError",
    "ImportPipelineError",
    "ExportError",
    "MigrationError",
    "PluginError",
    "ConflictError",
    "format_error",
    "is_not_found",
    "is_validation",
    # bike
    "Bike",
    "PotInfo",
    "HealthStatus",
    "BikeCatalog",
    # make
    "MakeProfile",
    "MakeCatalog",
    "ServiceNeed",
    "MileageNeed",
    # rack
    "Rack",
    "RackRegistry",
    "WindowDirection",
    # service
    "ServiceEvent",
    "ServiceLog",
    "ServiceQuality",
    # care
    "CareEvent",
    "InspectionLog",
    "CareEventType",
    "OdometerSchedule",
    # schedule
    "ScheduleEngine",
    "ScheduleEntry",
    "ScheduleOptions",
    "Season",
    "compute_next_service",
    # tags & notes
    "Tag",
    "TagRegistry",
    "Note",
    "NotesCollection",
    "NoteKind",
    # parser helpers
    "parse_date",
    "parse_interval",
    "parse_amount_ml",
    "parse_light_level",
    "parse_mileage",
    "format_interval_days",
    "format_amount_ml",
    # validators
    "validate_bike_name",
    "validate_interval_days",
    "validate_mileage_pct",
    "validate_light_level",
]
