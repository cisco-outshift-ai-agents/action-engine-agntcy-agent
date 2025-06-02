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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import argparse
from datetime import datetime
import time
import logging


class WebAutomation:
    def __init__(self, url, task):
        self.url = url
        self.task = task
        self.driver = None
        self.chat_output = []
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Initialize and configure the Chrome WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def navigate_to_url(self):
        """Navigate to the specified URL"""
        try:
            self.driver.get(self.url)
            self.logger.info(f"Navigated to {self.url}")
        except Exception as e:
            self.logger.error(f"Failed to navigate to URL: {str(e)}")
            raise

    def find_and_interact_with_chat(self):
        """Find chat input and enter task"""
        try:
            # Wait for chat input to be present and interactable
            chat_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='text'], textarea")
                )
            )
            chat_input.clear()
            chat_input.send_keys(self.task)
            chat_input.send_keys(Keys.RETURN)
            self.logger.info("Task entered in chat window")
        except Exception as e:
            self.logger.error(f"Failed to interact with chat: {str(e)}")
            raise

    def monitor_chat_output(self):
        """Monitor and record chat output"""
        try:
            # Wait for initial response
            time.sleep(2)
            last_message_count = 0

            # Monitor for 5 minutes maximum
            start_time = time.time()
            while time.time() - start_time < 120:  # 2 minute timeout
                # Find all chat messages
                messages = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[class*='text-l text-[#f7f7f7]']"
                )

                if len(messages) > last_message_count:
                    # New messages found
                    for msg in messages[last_message_count:]:
                        message_text = msg.text.strip()
                        if message_text:
                            self.chat_output.append(message_text)
                            self.logger.info(
                                f"New message recorded: {message_text[:50]}..."
                            )

                    last_message_count = len(messages)

                # Check if task is complete (implement based on your specific completion indicators)
                if self.is_task_complete():
                    break

                time.sleep(1)

            self.logger.info(f"Recorded {len(self.chat_output)} messages")
        except Exception as e:
            self.logger.error(f"Error monitoring chat output: {str(e)}")
            raise

    def is_task_complete(self):
        """Check if the task has been completed"""
        try:
            # Implement your task completion detection logic here
            # For example, look for specific completion messages or states
            completion_indicators = [
                "Task completed",
                "Done",
                "Finished",
                "GraphRecursionError",
            ]

            last_messages = self.chat_output[-3:] if self.chat_output else []
            return any(
                indicator in msg
                for msg in last_messages
                for indicator in completion_indicators
            )
        except Exception:
            return False

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

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing browser: {str(e)}")

    def run(self):
        """Main execution method"""
        try:
            self.setup_driver()
            self.navigate_to_url()
            self.find_and_interact_with_chat()
            self.monitor_chat_output()
            output_file = self.save_results()
            return output_file
        except Exception as e:
            self.logger.error(f"Automation failed: {str(e)}")
            raise
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Web automation script for chat interaction"
    )
    parser.add_argument("--url", required=True, help="URL to navigate to")
    parser.add_argument("--task", required=True, help="Task to enter in chat")
    args = parser.parse_args()

    try:
        automation = WebAutomation(args.url, args.task)
        output_file = automation.run()
        print(f"Task completed. Results saved to: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
