import os
import pandas as pd
from semantic_router import Route
from semantic_router.encoders import FastEmbedEncoder, HuggingFaceEncoder
from semantic_router.routers import SemanticRouter

encoder = HuggingFaceEncoder(name="cointegrated/rubert-tiny", score_threshold=0.5)


def load_routers_from_files(router_dir):
    """
    Load the main router and all subdomain routers from JSON files.
    Returns (main_router, domain_routers)
    """
    main_router_path = os.path.join(router_dir, "main_router.json")
    mr = SemanticRouter.from_json(main_router_path)
    main_router = SemanticRouter(
        encoder=mr.encoder, routes=mr.routes, auto_sync="local"
    )

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

    return main_router, domain_routers


def infer_domain_router(query: str, main_router: SemanticRouter):
    """Infer domain from query using loaded router."""
    result = main_router(query)
    return result.name if result else None


def infer_subdomain_router(query: str, domain_router: SemanticRouter):
    """Infer subdomain from query using loaded router."""
    result = domain_router(query)
    return result.name if result else None


def get_workflow_file_path(
    base_dir: str, domain: str, subdomain: str, website: str, ext: str = ".txt"
):
    if not all([domain, subdomain, website]):
        return None
    return os.path.join(base_dir, domain, subdomain, f"{website.lower()}{ext}")


def get_hints_for_query_with_loaded_routers(
    query: str,
    main_router: SemanticRouter,
    domain_routers: dict,
    workflow_base_dir: str,
    ext: str = ".txt",
):
    """
    Given a query, use loaded routers to infer domain, subdomain, and website, and return the hints file content if matched.
    Returns (domain, subdomain, website, hints_content or None)
    """
    domain = infer_domain_router(query, main_router)
    if not domain or domain not in domain_routers:
        return None, None, None, None

    subdomain_router = domain_routers[domain]
    subdomain = infer_subdomain_router(query, subdomain_router)
    if not subdomain:
        return domain, None, None, None

    # Website router loading logic would go here if you have website-level routers saved.
    # For now, assume website is not inferred by router, but by string/semantic match or not used.

    # If you have a list of websites for the subdomain, you can implement matching here.
    # For now, just skip website inference and hints.
    # To extend: implement website router loading and inference as needed.

    # Example: try to find a workflow file for each website under this subdomain and match by name in query
    subdomain_dir = os.path.join(workflow_base_dir, domain, subdomain)
    if not os.path.exists(subdomain_dir):
        return domain, subdomain, None, None

    for file in os.listdir(subdomain_dir):
        if file.endswith(ext):
            website = file.replace(ext, "")
            if website.lower() in query.lower():
                workflow_path = os.path.join(subdomain_dir, file)
                with open(workflow_path, "r") as f:
                    hints_content = f.read()
                return domain, subdomain, website, hints_content

    return domain, subdomain, None, None
