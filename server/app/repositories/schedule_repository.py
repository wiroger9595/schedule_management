from typing import Generic, TypeVar, Type, List, Optional
from sqlmodel import Session, select
from ..models.schedule import Schedule

class ScheduleRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, id: int) -> Optional[Schedule]:
        return self.session.get(Schedule, id)

    def get_by_schedule_id(self, schedule_id: str) -> Optional[Schedule]:
        return self.session.exec(select(Schedule).where(Schedule.schedule_id == schedule_id)).first()

    def get_all(self) -> List[Schedule]:
        return self.session.exec(select(Schedule)).all()

    def get_by_user_id(self, user_id: str) -> List[Schedule]:
        return self.session.exec(select(Schedule).where(Schedule.user_id == user_id)).all()

    def create(self, schedule: Schedule) -> Schedule:
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def update(self, schedule: Schedule) -> Schedule:
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def delete(self, schedule: Schedule) -> None:
        self.session.delete(schedule)
        self.session.commit()
