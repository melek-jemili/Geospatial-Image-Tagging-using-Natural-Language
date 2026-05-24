import os

import torch
import logging
from typing import Optional, Tuple
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from quantum_features_optimizer import QuantumFeatureOptimizer
from quantum_config import (
    DIFFUSION_MODEL, DEVICE, OUTPUT_PATH,
    NUM_INFERENCE_STEPS, GUIDANCE_SCALE, USE_QUANTUM
)

try:
    from diffusers import StableDiffusionPipeline
    from huggingface_hub import login, HfApi
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    logger.warning("Diffusers not installed")
    StableDiffusionPipeline = None

class QuantumImageGenerator:
    """Generate images with quantum feature optimization."""
    
    def __init__(self, use_quantum=USE_QUANTUM):
        self.use_quantum = use_quantum
        self.device = self._get_device()
        self.pipe = None
        self.optimizer = None
        
        if DIFFUSERS_AVAILABLE:
            self._authenticate_huggingface()
            self._load_model()
        
        if use_quantum:
            self.optimizer = QuantumFeatureOptimizer()
    

    def _authenticate_huggingface(self):
        """Authentifier avec HuggingFace."""
    
        hf_token = os.getenv("HF_TOKEN")
        
        if hf_token:
            try:
                login(token=hf_token)
                logger.info("✅ Authentifié avec HuggingFace")
            except Exception as e:
                logger.warning(f"HF Auth failed: {e}")
        else:
            logger.info("⚠️  HF_TOKEN non trouvé dans .env")
        
    def _get_device(self) -> str:
            """Determine device (cuda/mps/cpu)."""
            if DEVICE == "auto":
                if torch.cuda.is_available():
                    return "cuda"
                elif torch.backends.mps.is_available():
                    return "mps"
                return "cpu"
            return DEVICE
    
    def _load_model(self):
        """Load Stable Diffusion model."""
        logger.info(f"Loading {DIFFUSION_MODEL}...")
        
        try:
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
            self.pipe = StableDiffusionPipeline.from_pretrained(
                DIFFUSION_MODEL,
                torch_dtype=torch_dtype,
                use_auth_token=True
            )
            self.pipe = self.pipe.to(self.device)
            logger.info(f"✅ Model loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.pipe = None
    
    def generate(self, prompt: str, num_steps: Optional[int] = None) -> Optional[Path]:
        """Generate image from prompt."""
        
        if not self.pipe:
            logger.error("Model not loaded")
            return None
        
        num_steps = num_steps or NUM_INFERENCE_STEPS
        
        logger.info(f"Generating: {prompt[:50]}...")
        
        # Extract and optimize features
        features = self._extract_features(prompt)
        
        if self.use_quantum and self.optimizer:
            logger.info("Optimizing features with QAOA...")
            features = self.optimizer.optimize_features(features)
        
        # Generate image
        with torch.no_grad():
            image = self.pipe(
                prompt=prompt,
                num_inference_steps=num_steps,
                guidance_scale=GUIDANCE_SCALE
            ).images[0]
        
        # Save
        filename = self._save_image(image, prompt)
        logger.info(f"✅ Saved: {filename}")
        
        return filename
    
    def _extract_features(self, prompt: str) -> list:
        """Extract features from prompt text."""
        features = []
        
        # Complexity
        features.append(min(len(prompt) / 100, 1.0))
        
        # Colors
        colors = ["red", "blue", "green", "yellow", "purple"]
        color_count = sum(1 for c in colors if c in prompt.lower())
        features.append(min(color_count / 5, 1.0))
        
        # Timing
        timing_words = {
            "night": 0.0, "morning": 0.3, "day": 0.6,
            "sunset": 0.7, "sunrise": 0.5
        }
        timing = 0.5
        for word, val in timing_words.items():
            if word in prompt.lower():
                timing = val
                break
        features.append(timing)
        
        # Sentiment
        positive = ["beautiful", "stunning", "amazing"]
        negative = ["dark", "scary", "sad"]
        pos = sum(1 for w in positive if w in prompt.lower())
        neg = sum(1 for w in negative if w in prompt.lower())
        features.append(np.clip(0.5 + (pos - neg) * 0.1, 0, 1))
        
        # Pad to 10 features
        import numpy as np
        np.random.seed(hash(prompt) % 2**32)
        while len(features) < 10:
            features.append(np.random.random())
        
        return features[:10]
    
    def _save_image(self, image, prompt: str) -> Path:
        """Save generated image."""
        method = "quantum" if self.use_quantum else "classical"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{method}_{timestamp}.png"
        
        path = Path(OUTPUT_PATH) / filename
        image.save(path)
        
        return path