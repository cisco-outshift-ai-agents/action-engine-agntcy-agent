import json
import os
import argparse
import pandas as pd


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
            data_dict[domain][subdomain][website].append(ex["confirmed_task"])
    print(f"Finished loading {len(paths)} files!")
    return data_dict


def get_data_df(paths: list[str]) -> pd.DataFrame:
    """Create DataFrame for examples in domain-subdomain-website hierarchy.
    Args:
        paths: list[str], list of data path strings
    Returns:
        data_df: pd.DataFrame with columns [domain, subdomain, website, confirmed_task]
    """
    print("Start loading data files...")
    rows = []
    for p in paths:
        print(p)
        data = json.load(open(p, "r"))
        for ex in data:
            rows.append(
                {
                    "domain": ex["domain"],
                    "subdomain": ex["subdomain"],
                    "website": ex["website"],
                    "confirmed_task": ex["confirmed_task"],
                }
            )
    df = pd.DataFrame(rows)
    print(f"Finished loading {len(paths)} files!")
    return df


def main():
    # load data into dict
    data_paths = [os.path.join(args.data_dir, f) for f in os.listdir(args.data_dir)]
    # data_dict = get_data_dict(paths=data_paths)
    df = get_data_df(paths=data_paths)

    print(df.head())
    print("\nDataFrame Shape:", df.shape)

    # Save DataFrame to CSV
    output_path = os.path.join(
        os.path.dirname(args.output_dir), "mind2web_utterances.csv"
    )
    df.to_csv(output_path, index=False)
    print(f"\nDataFrame saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_dir", type=str, default="../offline_induction/data/train"
    )
    parser.add_argument("--output_dir", type=str, default="./utterances")
    args = parser.parse_args()
    main()
