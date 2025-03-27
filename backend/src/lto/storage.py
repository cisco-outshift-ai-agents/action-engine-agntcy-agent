import os
import json
from datetime import datetime
import logging
from typing import Dict, Optional, List
from pathlib import Path
from .models import LTOEvent, Operation

logger = logging.getLogger(__name__)


class EventStorage:
    def __init__(self, base_dir: str = "event_logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.current_session: Optional[str] = None

    def create_session(self) -> str:
        """Create a new session ID based on timestamp"""
        self.current_session = datetime.now().strftime("%Y%m%d%H%M%S")
        session_dir = self.base_dir / self.current_session
        session_dir.mkdir(exist_ok=True)
        return self.current_session

    def store_event(self, event_data: Dict) -> str:
        """Store a single event as a JSON file"""
        if not self.current_session:
            self.create_session()

        session_dir = self.base_dir / self.current_session
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f")
        event_file = session_dir / f"event_{timestamp}.json"

        with open(event_file, "w") as f:
            json.dump(event_data, f)

        return str(event_file)

    def get_session_events(self, session_id: Optional[str]) -> List[LTOEvent]:
        """Get all events for a session, converting them to LTOEvent objects"""
        events = []

        if not session_id:
            logger.warning("Attempted to get events with no session ID")
            return events

        session_dir = self.base_dir / session_id
        if not session_dir.exists():
            logger.info(f"No events found for session {session_id}")
            return events

        for event_file in sorted(session_dir.glob("event_*.json")):
            with open(event_file, "r") as f:
                event_dict = json.load(f)
                # Convert operation dict to Operation object
                if "operation" in event_dict:
                    event_dict["operation"] = Operation(**event_dict["operation"])
                # Convert dict to LTOEvent
                event = LTOEvent(**event_dict)
                events.append(event)

        return events

    def get_current_session(self) -> Optional[str]:
        return self.current_session
