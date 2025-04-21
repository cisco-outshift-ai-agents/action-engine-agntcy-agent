import asyncio
import json
import logging
import os
from datetime import datetime
import websockets
from langsmith import Client
from urllib.parse import urljoin
import argparse


class WebAutomation:
    def __init__(self, url, task):
        self.url = url
        self.task = task
        self.chat_output = []
        self.setup_logging()
        self.langsmith_client = Client(
            api_url=os.getenv(
                "LANGSMITH_ENDPOINT", "https://langsmith.outshift.io/api/v1"
            ),
            api_key=os.getenv("LANGSMITH_API_KEY"),
        )
        self.project_name = os.getenv("LANGSMITH_PROJECT", "action-engine-testing")

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

                # Get initial response which should contain run ID
                run_id = await self.get_run_id(websocket)
                self.logger.info(f"Received run ID: {run_id}")

                return run_id

        except websockets.exceptions.ConnectionError as e:
            self.logger.error(f"Failed to connect to WebSocket: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during WebSocket connection: {str(e)}")
            raise

    async def get_run_id(self, websocket):
        """Extract run ID from WebSocket response"""
        try:
            while True:
                message = await websocket.recv()
                self.logger.debug(f"Received message: {message}")

                try:
                    data = json.loads(message)
                    # The run ID should be in the first message after sending the task
                    if isinstance(data, dict):
                        if "run_id" in data:
                            return data["run_id"]
                        elif "metadata" in data and "run_id" in data["metadata"]:
                            return data["metadata"]["run_id"]
                        # Log the message structure to help debug run ID extraction
                        self.logger.debug(
                            f"Message structure: {json.dumps(data, indent=2)}"
                        )
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse WebSocket message as JSON")
                    continue

        except websockets.exceptions.ConnectionClosed as e:
            self.logger.error(f"WebSocket connection closed prematurely: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error while waiting for run ID: {str(e)}")
            raise

    async def monitor_langsmith_execution(self, run_id):
        try:
            while True:
                # Get current run state
                run = self.langsmith_client.read_run(run_id)

                # Capture intermediate outputs regardless of status
                child_runs = self.langsmith_client.list_runs(
                    project_name=self.project_name,
                    parent_run_id=run_id,
                    execution_order="asc",
                )
                self.capture_outputs(child_runs)  # Save outputs seen so far

                if run.status == "completed":
                    break
                elif run.status == "failed":
                    error_msg = str(run.error)
                    # Even on error, we've already captured partial outputs
                    raise Exception(error_msg)

                await asyncio.sleep(1)
        except Exception as e:
            # Save what we have before exiting
            self.save_results(error=str(e))
            raise

    def save_results(self):
        """Save the task results to a file"""
        try:
            output_data = {
                "task": self.task,
                "chat_output": self.chat_output,
                "status": "completed" if self.chat_output else "error",
                "timestamp": datetime.now().isoformat(),
            }

            filename = f"task_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Results saved to {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
            raise

    async def run(self):
        """Main execution method"""
        try:
            # Connect to WebSocket and get run ID
            run_id = await self.connect_websocket()

            # Monitor execution through LangSmith
            await self.monitor_langsmith_execution(run_id)

            # Save results
            output_file = self.save_results()
            return output_file
        except Exception as e:
            self.logger.error(f"Automation failed: {str(e)}")
            raise


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
