import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

def setup_logging(log_file="logs/execution.log"):
    """Setup logging configuration."""
    Path("logs").mkdir(exist_ok=True)
    
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logging.getLogger().addHandler(handler)

def save_results(results: dict, filename: str):
    """Save results to JSON."""
    path = Path("output") / filename
    with open(path, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved: {path}")

def load_prompts(filename: str) -> list:
    """Load prompts from file."""
    path = Path("data") / filename
    if not path.exists():
        return []
    
    with open(path, 'r') as f:
        return [line.strip() for line in f if line.strip()]