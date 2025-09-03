# from semantic_router import Route
# from semantic_router.layer import RouteLayer
import pandas as pd
import argparse
import os
import json
from semantic_router import Route
from semantic_router.encoders import FastEmbedEncoder, HuggingFaceEncoder
from semantic_router.routers import SemanticRouter


# encoder = FastEmbedEncoder(score_threshold=0.5)
encoder = HuggingFaceEncoder(name="Qwen/Qwen3-Embedding-0.6B", score_threshold=0.5)


def create_subdomain_routes(df: pd.DataFrame, domain: str) -> SemanticRouter:
    """Create a SemanticRouter for subdomains within a domain."""
    domain_data = df[df["domain"] == domain]
    subdomain_routes = []

    for subdomain in extract_subdomains(df, domain):
        subdomain_data = domain_data[domain_data["subdomain"] == subdomain]
        subdomain_utterances = subdomain_data["confirmed_task"].tolist()
        subdomain_route = Route(name=subdomain, utterances=subdomain_utterances)
        subdomain_routes.append(subdomain_route)

    return SemanticRouter(encoder=encoder, routes=subdomain_routes, auto_sync="local")


def extract_domains(df: pd.DataFrame) -> list[str]:
    """Extract domains from DataFrame."""
    return df["domain"].unique().tolist()


def extract_subdomains(df: pd.DataFrame, domain: str) -> list[str]:
    """Extract subdomains from DataFrame."""
    return df[df["domain"] == domain]["subdomain"].unique().tolist()


def create_routes(df: pd.DataFrame, domain: str) -> Route:
    """Create a single Route object for a domain with all its confirmed tasks as utterances."""
    domain_data = df[df["domain"] == domain]
    utterances = domain_data["confirmed_task"].tolist()

    return Route(name=domain, utterances=utterances)


def save_routers(main_router, domain_routers, output_dir):
    """Save the main router and all subdomain routers to JSON files."""
    os.makedirs(output_dir, exist_ok=True)

    # Save main domain router
    main_router_path = os.path.join(output_dir, "main_router.json")
    main_router.to_json(main_router_path)
    print(f"Main router saved to {main_router_path}")

    # Save each subdomain router
    domain_dir = os.path.join(output_dir, "domains")
    os.makedirs(domain_dir, exist_ok=True)

    for domain, router in domain_routers.items():
        domain_path = os.path.join(domain_dir, f"{domain}_router.json")
        router.to_json(domain_path)
        print(f"Subdomain router for {domain} saved to {domain_path}")


def load_routers(router_dir):
    """Load the main router and all subdomain routers from JSON files."""
    # Load main router
    main_router_path = os.path.join(router_dir, "main_router.json")
    mr = SemanticRouter.from_json(main_router_path)
    main_router = SemanticRouter(
        encoder=mr.encoder, routes=mr.routes, auto_sync="local"
    )
    print(f"Main router loaded from {main_router_path}")

    # Load subdomain routers
    domain_dir = os.path.join(router_dir, "domains")
    domain_routers = {}

    for file in os.listdir(domain_dir):
        if file.endswith("_router.json"):
            domain = file.replace("_router.json", "")
            router_path = os.path.join(domain_dir, file)
            sdr = SemanticRouter.from_json(router_path)
            domain_routers[domain] = SemanticRouter(
                encoder=sdr.encoder, routes=sdr.routes, auto_sync="local"
            )
            print(f"Subdomain router for {domain} loaded from {router_path}")

    return main_router, domain_routers


def main():
    if args.mode == "save":
        # Load data into DataFrame
        df = pd.read_csv(args.data_path)
        domain_list = extract_domains(df)

        # Dictionary to store domain routers and their subdomain routers
        domain_routers = {}

        # Create main domain routes
        all_routes = []
        for domain in domain_list:
            # Create routes for each domain
            domain_route = create_routes(df, domain)
            all_routes.append(domain_route)

            # Create subdomain router for this domain
            subdomain_router = create_subdomain_routes(df, domain)
            domain_routers[domain] = subdomain_router

            # Print domain and subdomain info
            print(f"Domain: {domain}")
            print(f"Subdomains: {extract_subdomains(df, domain)}")

        # Main router for domains
        main_router = SemanticRouter(
            encoder=encoder, routes=all_routes, auto_sync="local"
        )

        # Save routers to JSON files
        save_routers(main_router, domain_routers, args.output_dir)

    elif args.mode == "test":
        # Load routers from JSON files
        main_router, domain_routers = load_routers(args.router_dir)

    else:
        raise ValueError(f"Invalid mode: {args.mode}. Must be 'save' or 'test'")

    # Run test queries in both save and test modes
    test_queries = [
        "rent a car in Brooklyn - Central, NY",
        "Show computer game reviews sorted by score",
        "Buy a copy of the Gorillaz first studio album",
        "Find flight tickets to London",
    ]

    print("\nRunning test queries:")
    for query in test_queries:
        # First, route to domain
        domain_result = main_router(query)
        domain_name = domain_result.name

        # Then, route to subdomain using the corresponding subdomain router
        subdomain_result = domain_routers[domain_name](query)

        print(f"Query: {query}")
        print(
            f"Extract agent_hints from /apps/resources/{domain_name}/{subdomain_result.name}"
        )
        print("---")


# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        choices=["save", "test"],
        required=True,
        help="Mode: 'save' to create and save routers, 'test' to load and test routers",
    )
    parser.add_argument(
        "--data_path",
        type=str,
        default="./mind2web_utterances.csv",
        help="Path to the processed CSV file (required for save mode)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./router_files",
        help="Directory to save the router files (for save mode)",
    )
    parser.add_argument(
        "--router_dir",
        type=str,
        default="./router_files",
        help="Directory containing saved router files (for test mode)",
    )
    args = parser.parse_args()

    if args.mode == "save" and not os.path.exists(args.data_path):
        raise FileNotFoundError(f"Data file not found at: {args.data_path}")

    if args.mode == "test" and not os.path.exists(args.router_dir):
        raise FileNotFoundError(f"Router directory not found at: {args.router_dir}")

    main()
