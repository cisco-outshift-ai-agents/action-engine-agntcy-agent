# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import logging
from typing import Dict, Any
from fastapi import Body, Path, Response
from fastapi.responses import JSONResponse
from pydantic import Field, StrictStr
from typing_extensions import Annotated

from agent_workflow_server.services.runs import Runs
from agent_workflow_server.storage.storage import DB

logger = logging.getLogger(__name__)


async def safe_resume_stateless_run(
    run_id: Annotated[StrictStr, Field(description="The ID of the run.")] = Path(...),
    body: Dict[str, Any] = Body(None, description=""),
) -> Response:
    """Safe handler for resuming runs that avoids serialization errors"""
    try:
        logger.info(f"Safe resume handler called for run_id={run_id}")

        # Get the run to inspect the interrupt data
        run = DB.get_run(run_id)
        logger.info(f"Fetched run from DB: {run}")
        if not run:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"Run {run_id} not found"},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                },
            )

        # Pass the approval as a top-level state value as this is what LangGraph expects for proper state handling
        if "approved" in body:
            # Directly set the approved value in the state for LangGraph
            resume_data = {"approved": body["approved"]}

            # Also update the pending approval in the interrupt data if it exists
            if (
                run.get("interrupt")
                and run["interrupt"].get("ai_data")
                and run["interrupt"]["ai_data"].get("tool_call")
            ):
                tool_call = run["interrupt"]["ai_data"]["tool_call"]
                # Add to state for LangGraph's state_update
                resume_data["pending_approval"] = {
                    "tool_call": tool_call,
                    "approved": body["approved"],
                }
                logger.info(f"Adding tool_call approval to state: {resume_data}")
        else:
            resume_data = body

        await Runs.resume(run_id, resume_data)

        logger.info(f"Fetched run from DB after resume: {run}")
        logger.info(f"Resume data: {resume_data}")

        # Return a clean JSON response that won't trigger serialization errors
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Run {run_id} resumed successfully",
                "run_id": run_id,
                "approved": body.get("approved", False),
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )
    except ValueError as e:
        logger.error(f"Error resuming run {run_id}: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in safe_resume_handler: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )


def apply_route_override():
    """Apply route override at the FastAPI app level"""
    try:
        from agent_workflow_server.main import app as acp_app
        from fastapi import APIRouter

        # Create a new router with safe handler
        override_router = APIRouter()

        # Define the endpoint with the same path pattern but uses safe handler
        override_router.post("/runs/{run_id}")(safe_resume_stateless_run)

        # Add route at the beginning of the routes list to ensure it's prioritized
        # over the original route
        acp_app.routes.insert(0, override_router.routes[0])

        logger.info("✅ Successfully applied resume route override")
        return True
    except Exception as e:
        logger.error(f"Failed to apply route override: {e}")
        return False
