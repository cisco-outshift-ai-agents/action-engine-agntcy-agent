"""
Utility to generate OASF schema for ActionEngine

Run like this:
$ PYTHONPATH=. python src/utils/oasf_generator.py

You MUST ensure that the LLM running this script passes RAI assessment prior to running this script.
"""

import hashlib
import json
import os
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from src.utils.utils import get_llm_model
from langsmith import tracing_context

load_dotenv()


class ToolInfo(BaseModel):
    """Information about a tool extracted from source code"""

    name: str = Field(description="Tool name from the @tool decorator")
    description: str = Field(description="First paragraph of the tool's docstring")
    file_path: str = Field(description="Path to the source file")


class OASFSkill(BaseModel):
    """OASF skill mapping for a tool"""

    class_name: str = Field(description="Name of the skill class")
    category_name: str = Field(description="Name of the skill category")
    class_uid: int = Field(description="Unique ID of the skill class")
    category_uid: int = Field(description="Unique ID of the skill category")


class SkillList(BaseModel):
    """Wrapper for list of OASF skills"""

    skills: List[OASFSkill] = Field(description="List of OASF skills")


async def analyze_tool_file(file_path: str, llm) -> Optional[ToolInfo]:
    """Have LLM analyze Python file to extract tool information"""
    with open(file_path, "r") as f:
        content = f.read()

        if "@tool" not in content:
            print(f"No @tool decorator found in {file_path}")
            return None

    system_prompt = """You are an expert at analyzing Python code.
Examine the provided source file and identify all functions decorated with @tool.
Extract the tool name from the decorator and the first paragraph of the docstring."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Python source file {file_path}:\n\n{content}"),
    ]

    structured_llm = llm.with_structured_output(ToolInfo)

    try:
        with tracing_context(enabled=False):
            # Anything in this code block will **not** be traced to LangSmith
            response = await structured_llm.ainvoke(messages)
            return response
    except Exception as e:
        print(f"Error analyzing file {file_path}: {e}")
        return None


def parse_requirements() -> List[Dict]:
    """Parse requirements.txt to get package information"""
    packages = []
    try:
        with open("requirements.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Handle package==version format
                    if "==" in line:
                        name, version = line.split("==")
                        packages.append(
                            {"name": name.strip(), "version": version.strip()}
                        )
    except FileNotFoundError:
        pass
    return packages


def get_python_version() -> str:
    """Get the Python version constraints from Dockerfile"""
    try:
        with open("Dockerfile", "r") as f:
            content = f.read().lower()
            if "python:3.11" in content:
                return "<=3.11,>=3.10"
            elif "python:3.10" in content:
                return "<=3.10,>=3.9"
    except FileNotFoundError:
        pass
    return ">=3.8,<3.12"  # Default constraint


async def get_tool_skills(
    tool_info: ToolInfo, llm, skill_categories: str
) -> List[OASFSkill]:
    """Use LLM to map a tool to appropriate OASF skills"""
    system_prompt = f"""You are a skilled AI system classifier. Your task is to analyze a software tool and map it to the most appropriate skill categories from the OASF standard.

Available OASF skill categories:
{skill_categories}

Rules:
1. Consider the tool's name, description, and functionality
2. Map to 1-3 most relevant skills
3. Use exact category and class names from OASF
4. Provide class_uid and category_uid as specified in OASF
5. Focus on practical capabilities, not theoretical ones

Respond in valid JSON format like:
[{{"class_name": "Search", "category_name": "Retrieval Augmented Generation", "class_uid": 60102, "category_uid": 6}}]"""

    human_prompt = f"""Tool Information:
Name: {tool_info.name}
Description: {tool_info.description}
Source File: {tool_info.file_path}

Identify the most appropriate OASF skills for this tool."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    structured_llm = llm.with_structured_output(SkillList)

    try:
        with tracing_context(enabled=False):
            # Anything in this code block will **not** be traced to LangSmith
            response = await structured_llm.ainvoke(messages)
            return response.skills
    except Exception as e:
        print(f"Error mapping skills for {tool_info.name}: {e}")
        return []


def check_rai_assessment():
    """Check if cloud-hosted LLM requires RAI assessment confirmation"""

    response = input(
        "If the LLM provided in the .env file is a cloud-hosted LLM, does it pass the RAI assessment? Y/n: "
    )
    if response.lower() != "y":
        print("RAI assessment confirmation required. Exiting.")
        sys.exit(1)


async def generate_oasf_schema() -> Dict:
    """Generate OASF schema for ActionEngine"""
    tools_dir = "tools"
    all_tools = []

    # Initialize LLM for all operations
    llm = get_llm_model(
        provider=os.getenv("LLM_PROVIDER"),
        model_name=os.getenv("LLM_MODEL_NAME"),
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.0)),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_api_key=os.getenv("LLM_API_KEY"),
    )

    # Scan tools directory with LLM
    for filename in os.listdir(tools_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            file_path = os.path.join(tools_dir, filename)
            print(f"Analyzing {file_path}...")
            tool = await analyze_tool_file(file_path, llm)
            if tool:
                print(f"Found tool {tool.name} in {file_path}")
                all_tools.append(tool)
            else:
                print(f"No tools found in {file_path}")

    # Generate SHA-256 fingerprint
    hasher = hashlib.sha256()
    for tool in sorted(all_tools, key=lambda x: x.name):
        hasher.update(tool.name.encode())
    fingerprint = hasher.hexdigest().lower()

    # Read skill categories
    with open("agntcy/tools/oasf_skills.txt", "r") as f:
        skill_categories = f.read()

    # Map tools to skills using LLM
    all_skills = []
    for tool in all_tools:
        tool_skills = await get_tool_skills(tool, llm, skill_categories)
        all_skills.extend(tool_skills)

    # Deduplicate skills while preserving order
    seen_skills = set()
    unique_skills = []
    for skill in all_skills:
        skill_key = (skill.class_name, skill.category_name)
        if skill_key not in seen_skills:
            seen_skills.add(skill_key)
            unique_skills.append(skill)

    # Standard extensions
    extensions = [
        {
            "name": "oasf.agntcy.org/features/runtime",
            "version": "v0.0.0",
            "specs": {
                "language": "python",
                "version": get_python_version(),
                "config": {},
                "interrupts": [],
                "deployments": [
                    {
                        "type": "source_code",
                        "name": "src",
                        "url": "file://.",
                        "framework_config": {
                            "framework_type": "langgraph",
                            "name": "./src/graph",
                            "path": "graph:run",
                        },
                    }
                ],
                "sbom": {"packages": parse_requirements()},
            },
        },
        {
            "name": "oasf.agntcy.org/features/framework",
            "version": "v0.0.0",
            "specs": {
                "type": "langgraph",
                "version": "0.2.34",
                "tasks": {},
                "config": {},
            },
        },
        {
            "name": "oasf.agntcy.org/features/observability/logging",
            "version": "v0.0.0",
            "specs": {"config": {}},
        },
    ]

    # Convert skills to dictionaries for JSON serialization
    skills_json = [
        {
            "class_name": skill.class_name,
            "category_name": skill.category_name,
            "class_uid": skill.class_uid,
            "category_uid": skill.category_uid,
        }
        for skill in unique_skills
    ]

    schema = {
        "name": "directory.agntcy.org/actionengine/backend",
        "version": "v1.0.0",
        "extensions": extensions,
        "digest": {"value": fingerprint, "algorithm": "SHA-256", "algorithm_id": 3},
        "skills": skills_json,
        "authors": ["ActionEngine Team"],
        "created_at": int(time.time()),
        "locators": [{"type": "source-code", "source": {"url": "file://."}}],
    }

    return schema


if __name__ == "__main__":
    import asyncio
    import sys

    check_rai_assessment()
    schema = asyncio.run(generate_oasf_schema())

    save_path = os.path.join(os.getcwd(), "oasf_schema.json")
    with open(save_path, "w") as f:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Navigate to the /agntcy directory (parent of the lib directory)
        agntcy_dir = os.path.dirname(script_dir)
        save_path = os.path.join(agntcy_dir, "oasf_schema.json")
        with open(save_path, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"\nSaved OASF schema to {save_path}")
