from langchain_core.messages import HumanMessage, SystemMessage

agent_workflow_memory_abstract_prompt = """
Given a list of web nagivation tasks, your task is to extract the common workflows to solve these tasks. 
Each given task contains a natural language instruction, and a series of actions to solve the task. You need to find the repetitive subset of actions across multiple tasks, and extract each of them out as a workflow. 
Each workflow should be a commonly-reused sub-routine of the tasks. Do not generate similar or overlapping workflows. Each workflow should have at least two steps. Represent the non-fixed elements (input text, button strings) with descriptive variable names as shown in the example.
Another AI assistant will be using these workflows to solve similar tasks in the future, so please make sure that the workflow appropriately conveys the steps required to accomplish the user's task.
"""

# https://github.com/zorazrw/agent-workflow-memory/blob/main/mind2web/prompt/one_shot_abstract.txt
agent_workflow_memory_oneshot_prompt = """
Below is an example of how to respond.  Please follow the same format for your response.  
Do not respond with any other information other than the extracted workflows.
Website: Travel, Airlines, delta
## Query 1: Find flights from Seattle to New York on June 5th and only show those that can be purchased with miles.
Actions:
[link]  From Departure Airport or City Your Origin -> CLICK
[textbox]  Origin City or Airport -> TYPE: Seattle
[link]  SEA Seattle, WA -> CLICK
[link]  To Destination Airport or City Your Destination -> CLICK
[textbox]  Destination City or Airport -> TYPE: New York
[link]  NYC New York City Area Airports, NY -> CLICK
[combobox]  Trip Type:, changes will reload the page -> CLICK
[option]  One Way -> CLICK
[button]   Depart and Return Calendar Use enter to open, es... -> CLICK
[link]  Next -> CLICK
[link]  5 June 2023, Monday -> CLICK
[button]  done -> CLICK
[label]  Shop with Miles -> CLICK
[button]   SUBMIT -> CLICK
## Query 2: Find my trip with confirmation number SFTBAO including first and last name Joe Lukeman
Actions 
[tab]  MY TRIPS -> CLICK
[combobox]  Find Your Trip By -> CLICK
[option]  Confirmation Number -> CLICK
[input]   -> TYPE: SFTBAO
[input]   -> TYPE: Joe
[input]   -> TYPE: Lukeman
[button]   SUBMIT -> CLICK
## Query 3: Find the status of March 25 flights from New York airports to Columbus in Ohio 
Actions 
[tab]  FLIGHT STATUS -> CLICK
[button]   Search by date required selected as 19 March 202... -> CLICK
[link]  25 March 2023, Saturday -> CLICK
[button]  done -> CLICK
[link]  Depart City required From -> CLICK
[textbox]  Origin City or Airport -> TYPE: New York
[link]  NYC New York City Area Airports, NY -> CLICK
[link]  Arrival City required To -> CLICK
[textbox]  Destination City or Airport -> TYPE: Columbus
[li]  CMH -> CLICK
[button]   SUBMIT -> CLICK
## Query 4: Check all available one way flights for a single passenger from Manhattan to Philadelphia on May 23rd in first class 
Actions 
[link]  From Departure Airport or City Your Origin -> CLICK
[textbox]  Origin City or Airport -> TYPE: Manhattan
[link]  MHK Manhattan Regl, USA -> CLICK
[link]  To Destination Airport or City Your Destination -> CLICK
[textbox]  Destination City or Airport -> TYPE: Philadelphia
[link]  PHL Philadelphia, PA -> CLICK
[combobox]  Trip Type:, changes will reload the page -> CLICK
[option]  One Way -> CLICK
[button]   Depart and Return Calendar Use enter to open, es... -> CLICK
[link]  23 March 2023, Thursday -> CLICK
[button]  done -> CLICK
[link]   Advanced Search -> CLICK
[combobox]  Best Fares For -> CLICK
[option]  First Class -> CLICK
[button]   SUBMIT -> CLICK
Extracted Workflows 
# enter_flight_locations
Given that you are on the Delta flight booking page, this workflow enters the departure and destination city/airport for your flight 
[link]  {link to enter departure city} -> CLICK
[textbox]  {textbox to input departure city} -> TYPE: {your-origin-city}
[link]  {best-popup-option} -> CLICK
[link]  {link to enter destination city} -> CLICK
[textbox]  {textbox to enter destination city} -> TYPE: {your-destination-city }
[link]  {best-popup-option} -> CLICK
# select_oneway_trip
Given that you are on the Delta flight booking page, this workflow changes the flight to be one-way 
[combobox]  {option to select trip type} -> CLICK
[option]  One Way -> CLICK
# select_date_for_travel
Given that you are on the Delta flight booking page, this workflow selects the travel date 
[button] {calendar to select flight dates} -> CLICK
[link]  {travel-date} -> CLICK
[button]  done -> CLICK
# find_trip
Given that you are on the Delta flight searching page, this workflow finds a trip with the confirmation number and passenger name 
[tab]  MY TRIPS -> CLICK
[combobox]  {button to instantiate search} -> CLICK
[option]  Confirmation Number -> CLICK
[input]   -> TYPE: {confirmation-number}
[input]   -> TYPE: {passenger-name}
[button]   SUBMIT -> CLICK
"""

plan_generating_abstract = """
Given a list of user actions, your task is to extract a structured plan that captures these interactions. Generate the plan in a structured format that matches this schema:

{
    "plan_id": string | null,  // Optional identifier for the plan
    "steps": [
        {
            "content": string,  // Main step description
            "notes": string | null,  // Optional notes about the step, include details like html or implementation details here.  They will be hidden from the user, but shown to the agent.
            "status": "not_started" | "in_progress" | "completed" | "blocked",
            "substeps": [
                {
                    "content": string,  // Substep description
                    "notes": string | null,  // Optional notes
                    "status": "not_started" | "in_progress" | "completed" | "blocked"
                }
            ]
        }
    ]
}

Requirements:
1. Break down the workflow into logical main steps
2. For each main step, create substeps that provide more detailed actions
3. Each step and substep should have clear, actionable content
4. Use "notes" field to provide additional context or requirements when needed
5. All steps and substeps should start with "not_started" status
6. Keep descriptions clear and concise
7. Preserve the sequence and dependencies between steps
8. DON'T reference hard-coded HTML identifiers in the content of the steps, use the "notes" field for that
9. The notes are user-facing, so they should be clear, concise, and easy to understand with the tone of a user manual

Example:
If a user performs a login workflow:

Input Actions:
1. Navigate to login page
2. Click username field
3. Type "user@example.com"
4. Click password field
5. Type "password123"
6. Click "Remember me"
7. Click "Log in"
8. Wait for dashboard

The plan might look like:

{
    "plan_id": null,
    "steps": [
        {
            "content": "Access Login Interface",
            "notes": "Ensure the login page is fully loaded",
            "status": "not_started",
            "substeps": [
                {
                    "content": "Navigate to the login page",
                    "notes": null,
                    "status": "not_started"
                }
            ]
        },
        {
            "content": "Enter Credentials",
            "notes": "Complete all required login fields",
            "status": "not_started",
            "substeps": [
                {
                    "content": "Enter username or email into form",
                    "notes": "Input: user@example.com, HTML ID: #un-form-field",
                    "status": "not_started"
                },
                {
                    "content": "Enter password",
                    "notes": "Input: password123, HTML ID: #pw-form-field",
                    "status": "not_started"
                }
            ]
        },
        {
            "content": "Submit Login",
            "notes": "Complete login process",
            "status": "not_started",
            "substeps": [
                {
                    "content": "Select 'Remember me' option",
                    "notes": "Ensure the checkbox is checked, HTML ID: #remember-me, may be optional",
                    "status": "not_started"
                },
                {
                    "content": "Click login button",
                    "notes": "HTML ID: #login-button",
                    "status": "not_started"
                }
            ]
        }
    ]
}

Generate a similar structured plan based on the provided actions, ensuring each step and substep is clear, actionable, and properly organized.
"""
