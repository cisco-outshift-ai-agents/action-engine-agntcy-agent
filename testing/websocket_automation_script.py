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

                # Wait for execution_started message with run_id
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    if data.get("type") == "execution_started":
                        run_id = data.get("run_id")
                        self.logger.info(f"Received run_id: {run_id}")

                        # Start monitoring execution
                        await self.monitor_execution(websocket, run_id)
                        return run_id

        except websockets.exceptions.ConnectionError as e:
            self.logger.error(f"Failed to connect to WebSocket: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during WebSocket connection: {str(e)}")
            raise

    async def monitor_execution(self, websocket, run_id: str):
        """Monitor the execution and collect outputs"""
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)

                # Store outputs
                if "output" in data:
                    self.chat_output.append(data["output"])

                # Check completion
                if data.get("type") == "execution_completed":
                    self.logger.info("Execution completed")
                    break

                # Store any error messages
                if "error" in data:
                    self.logger.error(f"Execution error: {data['error']}")
                    raise Exception(data["error"])

        except websockets.exceptions.ConnectionClosed:
            self.logger.error("WebSocket connection closed unexpectedly")
            raise

    async def get_langsmith_trace(self, run_id: str):
        """Fetch the trace data from Langsmith"""
        try:
            run = self.langsmith_client.read_run(run_id)
            trace_data = {
                "run_info": {
                    "id": run.id,
                    "name": run.name,
                    "status": run.status,
                    "error": str(run.error) if run.error else None,
                    "start_time": (
                        run.start_time.isoformat() if run.start_time else None
                    ),
                    "end_time": run.end_time.isoformat() if run.end_time else None,
                },
                "execution_steps": [],
            }

            # Get all child runs to capture execution steps
            child_runs = self.langsmith_client.list_runs(
                project_name=self.project_name,
                parent_run_id=run_id,
                execution_order="asc",
            )

            for child_run in child_runs:
                step_data = {
                    "id": child_run.id,
                    "name": child_run.name,
                    "status": child_run.status,
                    "inputs": child_run.inputs,
                    "outputs": child_run.outputs,
                    "start_time": (
                        child_run.start_time.isoformat()
                        if child_run.start_time
                        else None
                    ),
                    "end_time": (
                        child_run.end_time.isoformat() if child_run.end_time else None
                    ),
                }
                trace_data["execution_steps"].append(step_data)

            return trace_data
        except Exception as e:
            self.logger.error(f"Failed to get trace data: {str(e)}")
            raise

    def save_results(self, run_id: str, trace_data: dict):
        """Save the task results and trace data to a file"""
        try:
            output_data = {
                "task": self.task,
                "run_id": run_id,
                "chat_output": self.chat_output,
                "status": "completed" if self.chat_output else "error",
                "timestamp": datetime.now().isoformat(),
                "trace": trace_data,
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

            # Wait for a short time to ensure execution is complete
            await asyncio.sleep(2)

            # Get trace data from Langsmith
            trace_data = await self.get_langsmith_trace(run_id)

            # Save results with trace
            output_file = self.save_results(run_id, trace_data)
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
