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
import json
import logging
import os
from datetime import datetime
import websockets
from urllib.parse import urljoin
import argparse


class WebAutomation:
    def __init__(self, url, task):
        self.url = url
        self.task = task
        self.setup_logging()
        self.status = ""

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    async def connect_websocket(self):
        """Connect to the WebSocket endpoint and send task"""
        ws_url = urljoin(self.url, "ws/chat").replace("http", "ws")
        self.logger.info(f"Connecting to WebSocket at {ws_url}")

        try:
            async with websockets.connect(ws_url) as websocket:
                # Send task
                message = {"task": self.task, "add_infos": ""}
                await websocket.send(json.dumps(message))
                self.logger.info("Task sent to WebSocket")

                # Wait for execution_started message with run_id
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    if data.get("type") == "execution_started":
                        run_id = data.get("run_id")
                        self.logger.info(f"Received run_id: {run_id}")

                        # Start monitoring execution
                        await self.monitor_execution(websocket)
                        return run_id

        except websockets.exceptions.WebSocketException as e:
            self.logger.error(f"Failed to connect to WebSocket: {str(e)}")
            self.status = "websocket connection error"
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during WebSocket connection: {str(e)}")
            self.status = "unknown websocket error"
            return None

    async def monitor_execution(self, websocket):
        """Monitor the execution and collect outputs"""
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)

                # Check for termination/completion
                if any(
                    [
                        # Normal completion via type
                        data.get("type") == "execution_completed",
                        # Termination via executor state
                        isinstance(data.get("executor"), dict)
                        and data["executor"].get("exiting") is True,
                        # Tool-based termination
                        any(
                            msg.get("tool_calls", [])
                            and any(
                                call.get("name") == "terminate"
                                for call in msg.get("tool_calls", [])
                            )
                            for msg in data.get("executor", {}).get("messages", [])
                        ),
                    ]
                ):
                    self.logger.info("Execution completed")
                    if isinstance(data.get("executor"), dict):
                        self.status = "success"
                    break

                # Handle errors
                if "error" in data:
                    error_msg = data["error"]
                    self.logger.error(f"Execution error: {error_msg}")

                    # Check for graph recursion error
                    if (
                        "Recursion limit" in error_msg
                        and "GRAPH_RECURSION_LIMIT" in error_msg
                    ):
                        self.logger.info(
                            "Graph recursion limit reached - treating as completion"
                        )
                        self.status = "graph recursion error"
                        break
                    else:
                        return  # Exit monitoring but don't raise exception

        except websockets.exceptions.WebSocketException as e:
            self.logger.error(f"WebSocket error during monitoring: {str(e)}")
            self.status = "websocket monitoring error"

    def save_results(self, run_id: str, filename: str = None):
        """Save the task results and trace data to a file"""
        try:
            output_data = {
                "task": self.task,
                "run_id": run_id,
                "status": self.status,
                "timestamp": datetime.now().isoformat(),
                "langsmith_project": os.getenv("LANGSMITH_PROJECT"),
            }

            # Use existing filename if provided, otherwise create new one
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                run_id_part = f"_{run_id}" if run_id else ""
                filename = f"task_output{run_id_part}_{timestamp}.json"

            # Update the file with current status
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Results saved/updated in {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
            raise

    async def run(self):
        """Main execution method"""
        run_id = None
        output_file = None
        try:
            # Connect to WebSocket and get run ID
            run_id = await self.connect_websocket()
            if not run_id:
                self.logger.warning("No run_id received, execution may have failed")

            # Create initial output file
            output_file = self.save_results(run_id)

            # Keep updating status until completion
            while self.status not in ["success", "graph recursion error"]:
                await asyncio.sleep(1)
                output_file = self.save_results(run_id, filename=output_file)

            return output_file
        except Exception as e:
            self.logger.error(f"Automation failed: {str(e)}")
            self.status = "automation error"

            # Try to save final status even if something went wrong
            if output_file:
                try:
                    self.save_results(run_id, filename=output_file)
                except Exception as save_error:
                    self.logger.error(f"Failed to save final status: {str(save_error)}")

            return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Web automation script for chat interaction"
    )
    parser.add_argument("--url", required=True, help="URL of the backend server")
    parser.add_argument("--task", required=True, help="Task to execute")
    args = parser.parse_args()

    try:
        automation = WebAutomation(args.url, args.task)
        output_file = asyncio.run(automation.run())
        print(f"Task completed. Results saved to: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
