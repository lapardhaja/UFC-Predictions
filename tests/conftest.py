import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import Base  # noqa: E402
from backend.models.db_models import Event, Fight, FightParticipation, Fighter  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


@pytest.fixture()
def sample_card(db_session):
    e = Event(event_id="evt-1", event_name="Test Event", date=None, location="LV", is_upcoming=True)
    db_session.add(e)
    db_session.flush()
    fa = Fighter(fighter_id="fa", name="Fighter A", wins=10, losses=2, reach_cm=180, height_cm=175)
    fb = Fighter(fighter_id="fb", name="Fighter B", wins=8, losses=3, reach_cm=178, height_cm=178)
    db_session.add_all([fa, fb])
    db_session.flush()
    f = Fight(
        fight_id="fight-1",
        event_id=e.id,
        winner_fighter_id=None,
        method=None,
        weight_class="Lightweight",
        is_title_fight=False,
    )
    db_session.add(f)
    db_session.flush()
    db_session.add_all(
        [
            FightParticipation(
                fight_id=f.id,
                fighter_id=fa.id,
                is_fighter_a=True,
                sig_strikes_landed=50,
                sig_strikes_attempted=100,
                takedowns_landed=1,
                takedowns_attempted=4,
                submission_attempts=0,
                knockdowns=0,
                control_time_seconds=60,
            ),
            FightParticipation(
                fight_id=f.id,
                fighter_id=fb.id,
                is_fighter_a=False,
                sig_strikes_landed=40,
                sig_strikes_attempted=90,
                takedowns_landed=0,
                takedowns_attempted=2,
                submission_attempts=1,
                knockdowns=0,
                control_time_seconds=30,
            ),
        ]
    )
    db_session.commit()
    return db_session
