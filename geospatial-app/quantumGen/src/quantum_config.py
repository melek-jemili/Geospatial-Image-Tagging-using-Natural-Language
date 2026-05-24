import os
from dotenv import load_dotenv

load_dotenv()

# IBM Quantum
IBM_QUANTUM_TOKEN = os.getenv("IBM_QUANTUM_TOKEN")
IBM_QUANTUM_CHANNEL = os.getenv("IBM_QUANTUM_CHANNEL", "ibm_quantum_platform")
IBM_QUANTUM_INSTANCE = os.getenv("IBM_QUANTUM_INSTANCE", "ibm-q/open/main")
USE_IBM_CLOUD = os.getenv("USE_QUANTUM", "true").lower() == "true"

# Model
DIFFUSION_MODEL = os.getenv("DIFFUSION_MODEL", "runwayml/stable-diffusion-v1-5")
DEVICE = os.getenv("DEVICE", "auto")

# Paths
DATA_PATH = os.getenv("DATA_PATH", "./data")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "./output")
LOG_PATH = os.getenv("LOG_PATH", "./logs")

# Create directories
for path in [DATA_PATH, OUTPUT_PATH, LOG_PATH]:
    os.makedirs(path, exist_ok=True)

# Generation
NUM_INFERENCE_STEPS = int(os.getenv("NUM_INFERENCE_STEPS", "50"))
GUIDANCE_SCALE = float(os.getenv("GUIDANCE_SCALE", "7.5"))
NUM_IMAGES = int(os.getenv("NUM_IMAGES", "1"))

# Quantum
USE_QUANTUM = os.getenv("USE_QUANTUM", "true").lower() == "true"
BACKEND_NAME = os.getenv("BACKEND_NAME", "ibmq_qasm_simulator")
MAX_QUBITS = int(os.getenv("MAX_QUBITS", "5"))
SHOTS = int(os.getenv("SHOTS", "1000"))