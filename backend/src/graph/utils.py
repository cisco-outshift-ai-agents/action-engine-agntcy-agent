"""Utility functions for graph execution and response handling."""

import json
import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def serialize_graph_response(data: Any) -> Any:
    """Convert Pydantic models and other types to serializable format."""
    if isinstance(data, BaseModel):
        return data.model_dump()
    elif isinstance(data, dict):
        return {
            key: serialize_graph_response(value)
            for key, value in data.items()
            if key != "__interrupt__"
        }
    elif isinstance(data, (list, tuple, set)):
        return [serialize_graph_response(item) for item in data]

    try:
        json.dumps(data)
        return data
    except (TypeError, OverflowError):
        return str(data)


def handle_interrupt(
    step_output: Dict[str, Any], thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process an interrupt and format for consumption."""
    logger.info("Processing interrupt")

    interrupt_data = None
    interrupt_obj = step_output["__interrupt__"]

    if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
        interrupt_obj = interrupt_obj[0]

    if hasattr(interrupt_obj, "message"):
        interrupt_data = interrupt_obj.message
    elif hasattr(interrupt_obj, "value"):
        interrupt_data = interrupt_obj.value
    else:
        interrupt_data = interrupt_obj if isinstance(interrupt_obj, dict) else {}

    approval_request = {
        "type": "approval_request",
        "data": interrupt_data,
        "thread_id": thread_id,
    }

    return serialize_graph_response(approval_request)
