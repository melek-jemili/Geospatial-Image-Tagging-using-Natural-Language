import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("IBM_QUANTUM_TOKEN")

if not token:
    print("❌ IBM_QUANTUM_TOKEN not found in .env")
    print("\nTo set up:")
    print("1. Go to https://quantum.cloud.ibm.com/")
    print("2. Get your API token from Account → IBM Quantum credentials")
    print("3. Add to .env:")
    print("   IBM_QUANTUM_TOKEN=your_token_here")
    exit(1)

try:
    from qiskit_ibm_runtime import QiskitRuntimeService
    
    QiskitRuntimeService.save_account(
        channel="ibm_quantum",
        instance="ibm-q/open/main",
        token=token,
        overwrite=True
    )
    
    print("✅ IBM Quantum authentication successful!")
    
    # List backends
    service = QiskitRuntimeService(channel="ibm_quantum")
    backends = service.backends()
    print(f"\nAvailable backends: {len(backends)}")
    for backend in backends[:5]:
        print(f"  - {backend.name}")
    
except Exception as e:
    print(f"❌ Authentication failed: {e}")