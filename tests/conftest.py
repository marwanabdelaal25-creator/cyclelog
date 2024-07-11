"""Shared pytest fixtures for cyclelog tests."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from cyclelog.inspection_log import CareEvent, CareEventType, InspectionLog, OdometerSchedule
from cyclelog.rack import Rack, RackRegistry, WindowDirection
from cyclelog.bike import HealthStatus, Bike, BikeCatalog, PotInfo
from cyclelog.make import MakeCatalog, MakeProfile
from cyclelog.storage import JsonStorage
from cyclelog.tag import Tag, TagRegistry
from cyclelog.service import ServiceEvent, ServiceLog
from cyclelog.notes import Note, NotesCollection, NoteKind


@pytest.fixture
def tmp_shed_path(tmp_path: Path) -> Path:
    """Fresh shed.json path under tmp_path."""
    return tmp_path / "shed.json"


@pytest.fixture
def empty_storage(tmp_shed_path: Path) -> JsonStorage:
    """Empty JsonStorage backed by tmp_path."""
    return JsonStorage(tmp_shed_path)


@pytest.fixture
def sample_make() -> MakeProfile:
    return MakeProfile(
        key="baghos-golden",
        common_name="Golden Pothos",
        scientific_name="Epipremnum aureum",
        light_level="medium",
        service_interval_min=7,
        service_interval_max=14,
        mileage_min=40,
        mileage_max=60,
    )


@pytest.fixture
def sample_rack() -> Rack:
    return Rack.create(
        "Living Room",
        id="loc001",
        zone="main",
        light_level="bright_indirect",
        window_direction=WindowDirection.SOUTH,
        mileage_pct=45.0,
    )


@pytest.fixture
def sample_bike(sample_rack: Rack, sample_make: MakeProfile) -> Bike:
    return Bike.create(
        "Monstera",
        id="bike001",
        nickname="Monty",
        make_key=sample_make.key,
        rack_id=sample_rack.id,
        health=HealthStatus.OKAY,
        health_score=70,
        service_interval_days=7,
        last_serviced_at=(date.today() - timedelta(days=3)).isoformat(),
        bag=PotInfo(diameter=6.0, unit="in", material="ceramic"),
    )


@pytest.fixture
def sample_bike2(sample_rack: Rack) -> Bike:
    return Bike.create(
        "Snake Bike",
        id="bike002",
        make_key="snake-bike",
        rack_id=sample_rack.id,
        health=HealthStatus.THRIVING,
        service_interval_days=14,
        last_serviced_at=(date.today() - timedelta(days=10)).isoformat(),
    )


@pytest.fixture
def sample_service_events(sample_bike: Bike, sample_bike2: Bike) -> list[ServiceEvent]:
    today = date.today()
    return [
        ServiceEvent.create(
            sample_bike.id,
            id="we001",
            serviced_at=(today - timedelta(days=3)).isoformat(),
            amount_ml=250.0,
        ),
        ServiceEvent.create(
            sample_bike.id,
            id="we002",
            serviced_at=(today - timedelta(days=10)).isoformat(),
            amount_ml=200.0,
        ),
        ServiceEvent.create(
            sample_bike2.id,
            id="we003",
            serviced_at=(today - timedelta(days=10)).isoformat(),
            amount_ml=150.0,
        ),
    ]


@pytest.fixture
def populated_storage(
    empty_storage: JsonStorage,
    sample_make: MakeProfile,
    sample_rack: Rack,
    sample_bike: Bike,
    sample_bike2: Bike,
    sample_service_events: list[ServiceEvent],
) -> JsonStorage:
    """Storage with sample bikes, make, racks, and service events."""
    empty_storage.create_make(sample_make)
    empty_storage.create_rack(sample_rack)
    empty_storage.create_bike(sample_bike)
    empty_storage.create_bike(sample_bike2)
    for ev in sample_service_events:
        empty_storage.create_service_event(ev.to_dict())
    tag = Tag.create("beginner", id="tag001", color="#4caf50")
    empty_storage.create_tag(tag.to_dict())
    note = Note.create(sample_bike.id, "New leaf unfurling", id="note001", kind=NoteKind.OBSERVATION)
    empty_storage.create_note(note.to_dict())
    return empty_storage


@pytest.fixture
def sample_csv_content() -> str:
    return (
        "name,make,rack,service_interval,notes\n"
        "Fern,baghos-golden,Living Room,7d,Test import\n"
        "Aloe,snake-bike,Kitchen,14d,Succulent\n"
    )


@pytest.fixture
def sample_service_csv() -> str:
    return (
        "bike_id,serviced_at,amount_ml,method\n"
        "bike001,2024-06-01,250,top_service\n"
        "bike002,2024-06-02,150,bottom_service\n"
    )


@pytest.fixture
def bike_catalog(sample_bike: Bike, sample_bike2: Bike) -> BikeCatalog:
    cat = BikeCatalog()
    cat.add(sample_bike)
    cat.add(sample_bike2)
    return cat


@pytest.fixture
def make_catalog(sample_make: MakeProfile) -> MakeCatalog:
    cat = MakeCatalog()
    cat.register(sample_make)
    cat.load_builtin()
    return cat


@pytest.fixture
def rack_registry(sample_rack: Rack) -> RackRegistry:
    reg = RackRegistry()
    reg.add(sample_rack)
    return reg


@pytest.fixture
def service_log(sample_service_events: list[ServiceEvent]) -> ServiceLog:
    log = ServiceLog()
    log.load_many(sample_service_events)
    return log


@pytest.fixture
def inspection_log(sample_bike: Bike) -> InspectionLog:
    log = InspectionLog()
    log.log(sample_bike.id, CareEventType.FERTILIZE, product="10-10-10")
    log.log(sample_bike.id, CareEventType.PRUNE, notes="Trimmed yellow leaves")
    log.set_odometer_schedule(OdometerSchedule(bike_id=sample_bike.id, interval_weeks=4))
    return log


@pytest.fixture
def tag_registry() -> TagRegistry:
    reg = TagRegistry()
    reg.add(Tag.create("beginner", id="tag001", color="#4caf50"))
    reg.add(Tag.create("pet-safe", id="tag002", color="#2196f3"))
    return reg


@pytest.fixture
def notes_collection(sample_bike: Bike) -> NotesCollection:
    coll = NotesCollection()
    coll.create(sample_bike.id, "General note", kind=NoteKind.GENERAL)
    coll.create(sample_bike.id, "Spider mites sbagted", kind=NoteKind.PEST)
    return coll
