import os
from openai import AzureOpenAI
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TaskGenerator:
    def __init__(self, api_key: str, endpoint: str, deployment_name: str):
        self.client = AzureOpenAI(
            api_key=api_key, api_version="2024-02-15-preview", azure_endpoint=endpoint
        )
        self.deployment_name = deployment_name

    def generate_tasks(
        self, website_url: str, website_description: str, num_tasks: int = 5
    ) -> List[str]:
        prompt = f"""
        We are testing the website
        {website_url}
        
        {website_description}
        
        We want to test practical daily tasks that a user would do on the website.
        Come up with a list of {num_tasks} example tasks and try to cover different cases.
        
        Requirements:
        - Each example should be a single sentence and not just click one of the elements.
        - Don't give step-by-step instructions or directly mention the element to interact.
        - Describe the goal of the task and provide concrete information or constraints.
        Use mock-up information (identifier, number, personal information, name, date,
        attributes, constraints, etc.) to make the task more specific and realistic.
        
        Format your response as a numbered list with one task per line.
        """

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates realistic user tasks for website testing.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        # Extract tasks from the response
        tasks_text = response.choices[0].message.content
        tasks = [
            line.strip().split(". ", 1)[1]
            for line in tasks_text.strip().split("\n")
            if line.strip()
        ]
        return tasks


def main():
    # Load configuration from environment variables
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not all([api_key, endpoint, deployment_name]):
        raise ValueError(
            "Missing required environment variables for Azure OpenAI configuration"
        )

    # Example website information
    # website_url = "https://aa.com"
    # website_description = """American Airlines - Airline tickets and low fares at aa.com
    # Book low fares to destinations around the world and find the latest deals on
    # airline tickets, hotels, car rentals and vacations at aa.com. As an AAdantage
    # member you earn miles on every trip and everyday spend."""
    website_url = "https://aws.amazon.com/rotate-aws-root-credentials/"
    website_description = """Secure Credential Management
    Manage and rotate your AWS credentials securely with 
    services like AWS Identity and Access Management (IAM) 
    and AWS Secrets Manager. Follow security best practices 
    by regularly rotating IAM user access keys and automating 
    the rotation of secrets such as database credentials, 
    API keys, and other sensitive "secret zero"s using 
    scheduled functions. Enhance your security posture by 
    automating credential lifecycle management to minimize 
    risk and ensure seamless application access."""

    # Initialize task generator
    generator = TaskGenerator(api_key, endpoint, deployment_name)

    # Generate tasks
    tasks = generator.generate_tasks(website_url, website_description)

    # Print generated tasks
    print("\nGenerated Tasks:")
    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task}")


if __name__ == "__main__":
    main()
