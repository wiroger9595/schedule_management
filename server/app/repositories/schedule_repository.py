from typing import Generic, TypeVar, Type, List, Optional
from datetime import datetime
from sqlmodel import Session, select, or_
from ..models.schedule import Schedule
from ..models.attend import attend
from ..models.contact import Contact

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

    def get_schedules_with_contact(self, user_id: str, contact_id: int) -> List[Schedule]:
        """
        Fetch schedules where the contact (or linked user) is involved.
        Only returns schedules created by the current user.
        """
        # 1. Get the contact to check for linked user_id
        contact = self.session.get(Contact, contact_id)
        if not contact:
            return []
            
        contact_user_id = contact.contact_user_id
        
        # 2. Build Query
        # Schedules created by current_user
        # AND (
        #   Schedule.contact_id == contact_id 
        #   OR contact is in attend_records VIA contact_id 
        #   OR via user_id
        # )
        
        # 2. Build Query
        conditions = [
            Schedule.contact_id == contact_id,
            attend.contact_id == contact_id
        ]
        
        if contact_user_id:
            conditions.append(attend.user_id == contact_user_id)
            
        statement = (
            select(Schedule)
            .outerjoin(attend, Schedule.schedule_id == attend.schedule_id)
            .where(Schedule.user_id == user_id)
            .where(or_(*conditions))
            .distinct()
        )
        
        return self.session.exec(statement).all()

    def find_overlapping(self, user_id: str, start_time: datetime, end_time: datetime, exclude_schedule_id: Optional[str] = None) -> List[Schedule]:
        """
        Find schedules that overlap with the given time range for the user.
        Overlapping logic: (StartA < EndB) and (EndA > StartB)
        
        NOTE: The database columns meeting_start_time and meeting_end_time seem to be VARCHAR
        in some environments, causing comparison errors. We cast them to TIMESTAMP here.
        """
        from sqlalchemy import func, TIMESTAMP
        
        # Ensure we are comparing 'like with like'. 
        # If DB is varchar, we cast DB col to timestamp.
        statement = (
            select(Schedule)
            .where(Schedule.user_id == user_id)
            .where(Schedule.status != "cancelled") # Ignore cancelled
            .where(func.cast(Schedule.meeting_start_time, TIMESTAMP) < end_time)
            .where(func.cast(Schedule.meeting_end_time, TIMESTAMP) > start_time)
        )
        
        if exclude_schedule_id:
            statement = statement.where(Schedule.schedule_id != exclude_schedule_id)
            
        return self.session.exec(statement).all()
