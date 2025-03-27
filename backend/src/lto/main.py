from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.utils.default_config_settings import default_config
from pydantic import BaseModel, Field
from typing import List, Optional
from .models import (
    LTOEvent,
    AnalyzedLTOResult,
    Operation,
    Plan,
    Step,
    SubStep,
    StepStatus,
)
from .prompts import (
    plan_generating_abstract,
    agent_workflow_memory_abstract_prompt,
    agent_workflow_memory_oneshot_prompt,
)
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class LTOResponse(BaseModel):
    """The expected response of the learning observation chain"""

    browser_behavior_summary: str
    workflow_summary: str
    plan: Optional[Plan] = Field(
        None,
        description="The structured plan with steps and substeps",
    )


async def generate_structured_plan(analyzed_result: AnalyzedLTOResult) -> Plan:
    """Generate a structured plan using the LLM with enforced output structure"""
    config = default_config()
    llm = ChatOpenAI(
        model=config["llm_model_name"],
        temperature=config["llm_temperature"],
        base_url=config["llm_base_url"],
        api_key=config["llm_api_key"],
    )

    # Use structured output to enforce the Plan schema
    structured_llm = llm.with_structured_output(Plan)

    messages = [
        SystemMessage(content=plan_generating_abstract),
        HumanMessage(content=analyzed_result.workflow),
        HumanMessage(content="\n".join(analyzed_result.actions)),
        HumanMessage(
            content="Based on these actions, generate a structured plan following the format specified above."
        ),
    ]

    try:
        plan = await structured_llm.ainvoke(messages)
        return plan
    except Exception as e:
        logger.error(f"Failed to generate structured plan: {e}")
        # Return a basic plan structure if generation fails
        return Plan(
            plan_id=None,
            steps=[
                Step(
                    content="Error generating structured plan",
                    notes=str(e),
                    status=StepStatus.not_started,
                    substeps=[],
                )
            ],
        )


async def summarize_with_ai(analyzed_result: AnalyzedLTOResult) -> LTOResponse:
    """Generate a summary and structured plan from the analyzed result"""
    config = default_config()
    llm = ChatOpenAI(
        model=config["llm_model_name"],
        temperature=config["llm_temperature"],
        base_url=config["llm_base_url"],
        api_key=config["llm_api_key"],
    )

    # Generate behavior summary
    messages = [
        SystemMessage(content=agent_workflow_memory_abstract_prompt),
        SystemMessage(content=agent_workflow_memory_oneshot_prompt),
        HumanMessage(content=analyzed_result.workflow),
        HumanMessage(content="\n".join(analyzed_result.actions)),
        HumanMessage(
            content="Please describe the user's actions given the aforementioned workflow and actions"
        ),
    ]

    summary = await llm.ainvoke(messages)

    # Generate structured plan
    plan = await generate_structured_plan(analyzed_result)

    return LTOResponse(
        browser_behavior_summary=summary.content,
        workflow_summary=analyzed_result.workflow,
        plan=plan,
    )


async def analyze_event_log(events: List[LTOEvent]) -> AnalyzedLTOResult:
    """
    Take the event log and generate a summary of the user behavior and workflow.
    """
    logger.info("Starting to analyze the provided event log")

    if not events:
        logger.warning("No events to analyze")
        return AnalyzedLTOResult(
            session_id="", workflow="No events to analyze", actions=[]
        )

    # Ensure all events are LTOEvent objects
    processed_events = []
    for event in events:
        if isinstance(event, dict):
            # Convert operation dict to Operation object if needed
            if "operation" in event and isinstance(event["operation"], dict):
                event["operation"] = Operation(**event["operation"])
            # Convert dict to LTOEvent
            event = LTOEvent(**event)
        processed_events.append(event)

    events = processed_events  # Replace with converted events

    # Get initial website safely
    try:
        initial_website = getattr(events[0], "website", None) or "unknown website"
    except Exception as e:
        logger.warning(f"Could not get initial website: {e}")
        initial_website = "unknown website"

    # Step 1: Group related events and track URL changes
    grouped_events = []
    current_input_group = None
    current_url = initial_website

    for event in events:
        # Safely get website from event
        event_website = getattr(event, "website", None) or current_url

        # Track URL changes and create a synthetic URL change event
        if event_website != current_url:
            # First, add any pending input group
            if current_input_group:
                grouped_events.append(current_input_group)
                current_input_group = None

            # Create a synthetic URL change event
            url_change_event = LTOEvent(
                website=event_website,
                session_id=getattr(event, "session_id", ""),
                operation=type(event.operation)(
                    original_op="url_updated",
                    target=f"from {current_url} to {event_website}",
                    value=event_website,
                    op="url_updated",
                ),
                timestamp=getattr(event, "timestamp", None),
            )
            grouped_events.append(url_change_event)
            current_url = event_website

        op = event.operation.original_op

        # Handle input events grouping
        if op == "input":
            if current_input_group is None:
                # Start a new input group
                current_input_group = event
            else:
                # Update existing group with latest value
                current_input_group.operation.value = event.operation.value
        else:
            # Add any pending input group before adding non-input event
            if current_input_group:
                grouped_events.append(current_input_group)
                current_input_group = None
            grouped_events.append(event)

    # Add any remaining input group
    if current_input_group:
        grouped_events.append(current_input_group)

    logger.info(f"Grouped events: {grouped_events}")

    # Step 2: Convert events to semantic actions
    actions = []
    last_input_value = None
    last_input_target = None

    for event in grouped_events:
        op = event.operation.original_op
        target = event.operation.target
        value = event.operation.value

        if op == "input":
            # Only store the target and value, don't create action yet
            last_input_value = value
            last_input_target = target
            continue
        elif op == "url_updated":
            # If there was a pending input action, add it first
            if last_input_value:
                actions.append(f"Type '{last_input_value}' into {last_input_target}")
                last_input_value = None
                last_input_target = None
            action = f"Navigate to {value}"
        elif op == "click":
            # If there was a pending input action, add it first
            if last_input_value:
                actions.append(f"Type '{last_input_value}' into {last_input_target}")
                last_input_value = None
                last_input_target = None
            action = f"Click on {target}"
        elif op == "scroll":
            # If there was a pending input action, add it first
            if last_input_value:
                actions.append(f"Type '{last_input_value}' into {last_input_target}")
                last_input_value = None
                last_input_target = None
            action = "Scroll down the page"
        elif op == "keydown":
            if value in ["Enter", "Tab", "Escape"]:
                # If there was a pending input action, add it first
                if last_input_value:
                    actions.append(
                        f"Type '{last_input_value}' into {last_input_target}"
                    )
                    last_input_value = None
                    last_input_target = None
                action = f"Press {value} key"
            else:
                continue
        else:
            # If there was a pending input action, add it first
            if last_input_value:
                actions.append(f"Type '{last_input_value}' into {last_input_target}")
                last_input_value = None
                last_input_target = None
            action = f"Perform {op} on {target}"

        actions.append(action)

    # Add any remaining input action
    if last_input_value:
        actions.append(f"Type '{last_input_value}' into {last_input_target}")

    logger.info(f"Converted actions: {actions}")

    # Step 3: Generate workflow summary
    session_id = events[0].session_id if events else ""

    workflow_summary = (
        f"User interaction sequence starting at {initial_website}:\n"
        f"1. Started a new browsing session\n"
    )

    for i, action in enumerate(actions, 2):
        workflow_summary += f"{i}. {action}\n"

    logger.info(f"Generated workflow summary: {workflow_summary}")

    return AnalyzedLTOResult(
        session_id=session_id, workflow=workflow_summary, actions=actions
    )
