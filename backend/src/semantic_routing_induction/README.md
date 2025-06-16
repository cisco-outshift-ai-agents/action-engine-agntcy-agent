# Semantic Routing Module

This directory provides scripts and data for extracting, generating, and routing user utterances for semantic task classification, with a focus on web automation and agent-based systems.

## Directory Structure

```
semantic_routing/
├── data/                # (Optional) Place for raw or processed data files
├── extract_utterances.py
├── generate_utterances.py
├── mind2web_utterances.csv
├── router_files/        # Stores saved router JSON files
├── sample_router.py
└── offline_induction.py
```

## File Descriptions

### `extract_utterances.py`
- **Purpose:** Extracts confirmed user tasks from raw JSON data files and outputs a CSV (`mind2web_utterances.csv`) with columns: domain, subdomain, website, confirmed_task.
- **Usage Example:**
  ```bash
  python extract_utterances.py --data_dir ./data --output_dir .
  ```
- **Arguments:**
  - `--data_dir`: Directory containing input JSON files.
  - `--output_dir`: Directory to save the output CSV.

### `generate_utterances.py`
- **Purpose:** Uses Azure OpenAI to generate realistic user tasks for a given website and description.
- **Usage Example:**
  ```bash
  python generate_utterances.py
  ```
- **Setup:**  
  Set the following environment variables in your `.env` file:
  ```
  AZURE_OPENAI_API_KEY=your_key
  AZURE_OPENAI_ENDPOINT=your_endpoint
  AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
  ```

### `mind2web_utterances.csv`
- **Purpose:** Stores structured utterance data for use in router creation and testing.

### `sample_router.py`
- **Purpose:** Builds, saves, loads, and tests semantic routers for domains and subdomains using utterances from the CSV.
- **Modes:**
  - `save`: Build routers and save them as JSON files in `router_files/`.
  - `test`: Load routers from `router_files/` and run test queries.
- **Usage Examples:**
  - Save routers:
    ```bash
    python sample_router.py --mode save --data_path ./mind2web_utterances.csv --output_dir ./router_files
    ```
  - Test routers:
    ```bash
    python sample_router.py --mode test --router_dir ./router_files
    ```
- **Notes:**  
  - Uses `HuggingFaceEncoder` by default for embedding.
  - Routers are saved as JSON files for reuse and fast loading.

### `offline_induction.py`
- **Purpose:** Induces website-specific workflows from training examples using Azure OpenAI.
- **Modes:**
  - `input`: Interactive mode that prompts for domain, subdomain, and website.
  - `auto`: Process a single website with provided tags.
  - `all`: Process all websites in the dataset automatically.
- **Usage Examples:**
  ```bash
  # Interactive mode
  python offline_induction.py --mode input
  
  # Auto mode for a specific website
  python offline_induction.py --mode auto --domain shopping --subdomain retail --website amazon
  
  # Process all websites
  python offline_induction.py --mode all
  ```
- **Arguments:**
  - `--data_dir`: Directory containing training data (default: "./data/train").
  - `--output_dir`: Directory to save workflows (default: "./workflow").
  - `--output_suffix`: Optional suffix for output files.
  - `--model_name`: LLM model to use (default: "gpt-4o").
  - `--temperature`: Temperature for generation (default: 0.0).
  - `--instruction_path`, `--one_shot_path`: Paths to prompt templates.
  - `--verbose`: Flag to print prompt and response.
- **Notes:**
  - Organizes examples hierarchically by domain, subdomain, and website.
  - Saves workflows in a corresponding folder structure.
  - Requires Azure OpenAI API credentials.

### `data/` and `router_files/`
- `data/`: Place your raw JSON data files here for extraction.
- `router_files/`: Output directory for saved router JSON files.

## Workflow

1. **Extract utterances:**  
   Run `extract_utterances.py` to convert raw JSON data into `mind2web_utterances.csv`.
2. **(Optional) Generate new utterances:**  
   Run `generate_utterances.py` to augment your dataset.
3. **Build and save routers:**  
   Run `sample_router.py` in `save` mode.
4. **Test routers:**  
   Run `sample_router.py` in `test` mode.
5. **(Optional) Induce website workflows:**
   Run `offline_induction.py` to generate website-specific workflows from examples.

## Requirements

- Python 3.8+
- Packages: `pandas`, `openai`, `dotenv`, `semantic_router`
- For LLM generation: Azure OpenAI credentials

## Example Commands

```bash
# Extract utterances from data
python extract_utterances.py --data_dir ./data --output_dir .

# Generate new utterances (requires .env)
python generate_utterances.py

# Build and save routers
python sample_router.py --mode save --data_path ./mind2web_utterances.csv --output_dir ./router_files

# Test routers
python sample_router.py --mode test --router_dir ./router_files

# Induce workflows for all websites
python offline_induction.py --mode all --verbose
```

## License

See project root for license information.