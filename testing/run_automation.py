/*
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
# SPDX-License-Identifier: Apache-2.0"
*/
import asyncio
import argparse
import json
import os
import sys
from websocket_automation_script import WebAutomation
from read_trace import get_run_trace, process_trace_data
from evaluate import evaluate_actions
from datetime import datetime
from typing import Dict, List, Any, Optional


async def run_task_and_get_runid(
    url: str, task_data: Dict[str, Any], output_dir: str
) -> Optional[Dict[str, Any]]:
    """
    Run a single task through automation and get its run_id.
    """
    task = task_data["task"]
    print(f"\n=== Processing Task: {task[:50]}... ===")

    # Step 1: Run websocket automation
    print("\n1. Running Websocket Automation...")
    automation = WebAutomation(url, task)
    output_file = await automation.run()

    if not output_file:
        print("Error: Websocket automation failed to produce output file")
        return None

    # Load the output file to get run_id
    try:
        with open(output_file, "r") as f:
            output_data = json.load(f)
            run_id = output_data.get("run_id")
            status = output_data.get("status")

        # Delete the task output file after extracting the data
        try:
            os.remove(output_file)
            print(f"Cleaned up temporary file: {output_file}")
        except Exception as cleanup_error:
            print(
                f"Warning: Could not delete temporary file {output_file}: {cleanup_error}"
            )
    except Exception as e:
        print(f"Error reading output file: {str(e)}")
        return None

    if not run_id:
        print("Error: No run_id found in output file")
        return None

    print(f"Successfully obtained run_id: {run_id}")
    print(f"Automation status: {status}")

    # Update task data with run_id
    task_data["run_id"] = run_id
    task_data["status"] = status
    return task_data


async def process_task_trace(task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process the trace data and run evaluation for a completed task.
    """
    run_id = task_data.get("run_id")
    if not run_id:
        print("Error: No run_id found in task data")
        return None

    print(f"\n=== Processing Trace for run_id: {run_id} ===")

    # Read trace from langsmith
    print("\n1. Reading Trace from Langsmith...")
    trace_data = get_run_trace(run_id)

    if not trace_data or "child_runs" not in trace_data:
        print("Error: Failed to get valid trace data")
        task_data["action_repr_output"] = []
        task_data["score"] = 0.0
        task_data["decision"] = "Failed to get valid trace data"
        task_data["error"] = "No valid trace data"
        return task_data

    try:
        action_reprs = process_trace_data(trace_data)
        task_data["action_repr_output"] = action_reprs if action_reprs else []
    except Exception as e:
        print(f"Error processing trace: {str(e)}")
        # Store any partial action_reprs that might have been collected
        if "action_repr_output" not in task_data:
            task_data["action_repr_output"] = []
        task_data["error"] = f"Trace processing error: {str(e)}"
        task_data["score"] = 0.0
        task_data["decision"] = f"Failed to process trace: {str(e)}"
        return task_data

    # Run evaluation
    print("\n2. Running Evaluation...")
    try:
        if not task_data["action_repr_output"]:
            print("Warning: No action representations to evaluate")
            task_data["score"] = 0.0
            task_data["decision"] = "No actions were extracted from the trace"
            task_data["error"] = "No actions extracted"
        else:
            correctness_metric = evaluate_actions(
                task_data["task"],
                task_data["action_repr_output"],
                task_data["action_reprs"],
            )
            task_data["score"] = correctness_metric.score
            task_data["decision"] = correctness_metric.reason
            task_data["error"] = None  # Clear error if evaluation succeeds
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        task_data["score"] = 0.0
        task_data["decision"] = f"Evaluation error: {str(e)}"
        task_data["error"] = f"Evaluation error: {str(e)}"

    return task_data


async def save_output(tasks_data: List[Dict[str, Any]], output_dir: str):
    """
    Save tasks data to output.json file.
    """
    try:
        output_file = os.path.join(output_dir, "output.json")
        with open(output_file, "w") as f:
            json.dump(tasks_data, f, indent=2)
        print(f"\nOutput saved to: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error saving output: {str(e)}")
        return None


async def run_automated_flow(url: str, input_json_path: str, output_dir: str = "data"):
    """
    Run the complete automation flow for all tasks in the input JSON.
    """
    print("\n=== Starting Automated Flow ===")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load input tasks
    try:
        with open(input_json_path, "r") as f:
            tasks_data = json.load(f)
    except Exception as e:
        print(f"Error loading input JSON: {str(e)}")
        return False

    tasks_in_progress = []

    # Phase 1: Run all tasks and get run_ids
    print("\n=== Phase 1: Running Tasks and Collecting Run IDs ===")
    for task_data in tasks_data:
        try:
            enriched_task = await run_task_and_get_runid(url, task_data, output_dir)
            if enriched_task:
                tasks_in_progress.append(enriched_task)
                # Update output file after each task
                await save_output(tasks_in_progress, output_dir)
        except Exception as e:
            print(f"Error processing task: {str(e)}")
            continue

    # Phase 2: Process traces and run evaluations
    print("\n=== Phase 2: Processing Traces and Running Evaluations ===")
    for i, task_data in enumerate(tasks_in_progress):
        try:
            processed_task = await process_task_trace(task_data)
            if processed_task:
                # Update task in place
                tasks_in_progress[i] = processed_task
                # Update output file after each processed task
                await save_output(tasks_in_progress, output_dir)
        except Exception as e:
            print(f"Error processing trace: {str(e)}")
            continue

    if tasks_in_progress:
        print("\n=== Automation Flow Completed ===")
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Run complete automation flow")
    parser.add_argument("--url", required=True, help="URL of the backend server")
    parser.add_argument(
        "--input-json",
        required=True,
        help="Path to input JSON file with tasks and expected actions",
    )
    parser.add_argument(
        "--output-dir", default="data", help="Directory to store output files"
    )

    args = parser.parse_args()

    try:
        asyncio.run(run_automated_flow(args.url, args.input_json, args.output_dir))
    except Exception as e:
        print(f"Error during automation: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
