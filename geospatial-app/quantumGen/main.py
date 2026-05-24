import sys
import logging
from pathlib import Path
# -*- coding: utf-8 -*-
import sys
import io

# Force UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.image_generator import QuantumImageGenerator
from src.utils import setup_logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run Quantum Image Generator."""
    
    logger.info("="*60)
    logger.info("QUANTUM IMAGE GENERATOR")
    logger.info("="*60)
    
    # Initialize
    gen = QuantumImageGenerator(use_quantum=True)
    
    # Example prompts
    prompts = [
        "Eiffel Tower at sunset, impressionist painting",
        "Quantum computer core, digital art",
        "Deep ocean with bioluminescent creatures"
    ]
    
    # Generate images
    for prompt in prompts:
        logger.info(f"\nPrompt: {prompt}")
        output_path = gen.generate(prompt)
        if output_path:
            logger.info(f"Generated: {output_path}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Generation complete!")
    logger.info("="*60)

if __name__ == "__main__":
    setup_logging()
    main()