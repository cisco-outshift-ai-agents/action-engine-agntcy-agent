# Web Automation Testing

## Selenium Automation Script

### Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Chrome browser is installed on your system
3. ChromeDriver will be automatically managed by webdriver_manager

### Usage
Run the automation script with URL and task parameters:
```bash
python automation_script.py <url> "<task>"
```

Example:
```bash
python automation_script.py http://example.com "Create a hello world webpage"
```

### Output
The script will:
1. Open the specified URL in Chrome
2. Enter the task in the chat window
3. Monitor and record chat output
4. Save results to a JSON file with timestamp

### Output Format
```json
{
  "task": "input task text",
  "chat_output": ["step 1", "step 2", "..."],
  "status": "completed/error",
  "timestamp": "ISO datetime"
}
```

### Error Handling
- The script includes comprehensive error handling and logging
- Errors are logged to console with timestamps
- Failed runs will create output files with error status
- Browser resources are properly cleaned up even on failure

### Timeouts and Limits
- Maximum chat monitoring time: 5 minutes
- Element wait timeout: 10 seconds
- Script will exit if completion indicators are detected

### Completion Detection
The script considers a task complete when it detects any of these indicators in recent messages:
- "Task completed"
- "Done"
- "Finished"

You can modify these indicators in the `is_task_complete()` method to match your specific needs.
