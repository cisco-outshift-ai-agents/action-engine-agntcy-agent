import os
from semantic_router_utils import (
    load_routers_from_files,
    get_hints_for_query_with_loaded_routers,
)


def main():
    # Set these paths as appropriate for your environment
    ROUTER_DIR = "./router_files"  # e.g., "./router_files"
    WORKFLOW_BASE_DIR = "./workflow_files"  # e.g., "./workflow_files"
    SAMPLE_QUERIES = [
        "Book a flight on Expedia",
        "Find a hotel on Booking.com",
        "Show computer game reviews sorted by score",
        "Buy a copy of the Gorillaz first studio album",
        "Unknown website example",
    ]

    # Load routers
    main_router, domain_routers = load_routers_from_files(ROUTER_DIR)

    for query in SAMPLE_QUERIES:
        domain, subdomain, website, hints = get_hints_for_query_with_loaded_routers(
            query, main_router, domain_routers, WORKFLOW_BASE_DIR, ext=".txt"
        )
        print(f"Query: {query}")
        print(f"  Domain: {domain}")
        print(f"  Subdomain: {subdomain}")
        print(f"  Website: {website}")
        if hints:
            print(f"  Hints file content (first 200 chars):\n{hints[:200]}...\n")
        else:
            print("  No hints file found or matched.\n")


if __name__ == "__main__":
    main()
