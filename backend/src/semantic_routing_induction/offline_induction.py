"""Induce Website-Specific Workflows Offline from Training Examples."""

import os
import json
import pickle
import argparse
from utils.data import add_scores, format_examples, filter_workflows


from openai import AzureOpenAI

OPENAI_API_KEY = "API_KEY"
OPENAI_BASE_URL = "BASE_URL"

client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    api_version="2024-02-01",
    azure_endpoint=OPENAI_BASE_URL,
)


# %% Data loading and processing
def get_data_dict(paths: list[str]) -> dict:
    """Create dict for examples in domain-subdomain-website hierarchy.
    Args:
        paths: list[str], list of data path strings
    Rets:
        data_dict: dict[str, dict], (domain, subdomain, website) dict
    """
    print("Start loading data files...")
    data_dict = {}
    for p in paths:
        print(p)
        data = json.load(open(p, "r"))
        for ex in data:
            domain, subdomain, website = ex["domain"], ex["subdomain"], ex["website"]
            if domain not in data_dict:
                data_dict[domain] = {}
            if subdomain not in data_dict[domain]:
                data_dict[domain][subdomain] = {}
            if website not in data_dict[domain][subdomain]:
                data_dict[domain][subdomain][website] = []
            data_dict[domain][subdomain][website].append(ex)
    print(f"Finished loading {len(paths)} files!")
    return data_dict


def get_split(data_dict: dict) -> dict:
    """Return the split from the data dict from inputted option."""
    options = list(data_dict.keys())
    split = input(f"Select from {options} >> ")
    while split not in options:
        split = input(f"Select from {options} >> ")
    return split, data_dict[split]


def get_examples(data_dict: dict, tags: tuple[str, str, str]) -> list[dict]:
    """Return the examples satisfying the tags."""
    domain, subdomain, website = tags
    return data_dict[domain][subdomain][website]


# %% Prompt and generate
def llm_generate(
    tags: tuple[str, str, str], examples: list[dict], args, verbose: bool = False
):
    """Call gpt model to generate workflows."""
    prompt = f"Website: " + ",".join(tags) + "\n"
    prompt += format_examples(examples, args.prefix, args.suffix)
    prompt = "\n\n".join([args.INSTRUCTION, args.ONE_SHOT, prompt])
    if verbose:
        print("Prompt:\n", prompt, "\n\n")
    response = client.chat.completions.create(
        model=args.model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=args.temperature,
        max_tokens=1024,
    )
    response = response.choices[0].message.content
    if verbose:
        print(response)
    return response


# %% Save outputs
def save_to_txt(text: str, args, domain=None, subdomain=None, website=None):
    """Save text to a .txt file in hierarchical folder structure."""
    # Use provided domain/subdomain/website or fall back to args
    domain = domain or args.domain
    subdomain = subdomain or args.subdomain
    website = website or args.website

    # Create hierarchical directory structure
    domain_dir = os.path.join(args.output_dir, domain)
    subdomain_dir = os.path.join(domain_dir, subdomain)

    # Ensure directories exist
    os.makedirs(subdomain_dir, exist_ok=True)

    output_name = (
        f"{website.lower()}_{args.output_suffix}.txt"
        if args.output_suffix is not None
        else f"{website.lower()}.txt"
    )
    output_path = os.path.join(subdomain_dir, output_name)
    with open(output_path, "w") as fw:
        fw.write(text)
    print(f"Saved workflow to {output_path}")


# %% Main pipeline
def main():
    # load data into dict
    data_paths = [os.path.join(args.data_dir, f) for f in os.listdir(args.data_dir)]
    data_dict = get_data_dict(paths=data_paths)

    # load candidate scores and ranks
    with open(os.path.join("data", "scores_all_data.pkl"), "rb") as f:
        candidate_results = pickle.load(f)

    # load prompt contexts
    args.INSTRUCTION = open(args.instruction_path, "r").read()
    args.ONE_SHOT = open(args.one_shot_path, "r").read()

    def single_website_loop(
        tags: tuple[str, str, str], domain=None, subdomain=None, website=None
    ):
        """Pipeline to induce, filter, and save workflows on a single website."""
        examples = get_examples(data_dict, tags=tags)
        print(f"Processing {tags} with #{len(examples)} examples")
        # examples = add_scores(examples, candidate_results)
        response = llm_generate(tags, examples, args, verbose=args.verbose)
        workflows = filter_workflows(response, website=tags[-1])
        save_to_txt(
            workflows, args, domain=domain, subdomain=subdomain, website=website
        )

    def process_all_websites():
        """Process all domains, subdomains, and websites in the data."""
        print(f"Starting batch processing of all websites...")
        total_websites = 0

        for domain in data_dict:
            for subdomain in data_dict[domain]:
                for website in data_dict[domain][subdomain]:
                    tags = (domain, subdomain, website)
                    print(f"\nProcessing {domain}/{subdomain}/{website}")
                    single_website_loop(
                        tags, domain=domain, subdomain=subdomain, website=website
                    )
                    total_websites += 1

        print(f"Completed processing {total_websites} websites")

    if args.mode == "auto":
        single_website_loop(args.tags)
    elif args.mode == "input":
        stop = False
        while not stop:
            # select split
            args.domain, domain_dict = get_split(data_dict)
            args.subdomain, subdomain_dict = get_split(domain_dict)
            args.website, examples = get_split(subdomain_dict)

            # generate workflows
            tags = [args.domain, args.subdomain, args.website]
            single_website_loop(tags)

            if input("Stop? [y/n] ").strip() == "y":
                stop = True
    elif args.mode == "all":
        # Process all websites automatically
        process_all_websites()
    else:
        raise ValueError("Please enter a valid `mode` ('input', 'auto', or 'all')")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="./data/train")
    parser.add_argument("--output_dir", type=str, default="./workflow")
    parser.add_argument("--output_suffix", type=str, default=None)
    parser.add_argument(
        "--verbose", action="store_true", help="Whether to print prompt and response."
    )

    # mode
    parser.add_argument(
        "--mode", type=str, default="input", choices=["input", "auto", "all"]
    )
    parser.add_argument(
        "--domain", type=str, default=None, help="Specify in 'auto' mode."
    )
    parser.add_argument(
        "--subdomain", type=str, default=None, help="Specify in 'auto' mode."
    )
    parser.add_argument(
        "--website", type=str, default=None, help="Specify in 'auto' mode."
    )
    # model
    parser.add_argument("--model_name", type=str, default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=0.0)

    # prompt
    parser.add_argument(
        "--instruction_path", type=str, default="prompt/instruction_action.txt"
    )
    parser.add_argument(
        "--one_shot_path", type=str, default="prompt/one_shot_action.txt"
    )
    parser.add_argument("--prefix", type=str, default=None)
    parser.add_argument("--suffix", type=str, default="# Summary Workflows")

    args = parser.parse_args()

    # sanity check
    if args.mode == "auto":
        args.tags = [args.domain, args.subdomain, args.website]
        assert not any([tag is None for tag in args.tags])

    main()
