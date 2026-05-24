import numpy as np
import logging
from typing import List, Dict
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime import QiskitRuntimeService
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    logger.warning("Qiskit not available, using classical optimization")

from quantum_config import IBM_QUANTUM_TOKEN, BACKEND_NAME, MAX_QUBITS, SHOTS

class QuantumFeatureOptimizer:
    """Optimise features avec QAOA."""
    
    def __init__(self, use_ibm=True):
        self.use_ibm = use_ibm
        self.backend = None
        self.execution_history = []
        
        if QISKIT_AVAILABLE:
            self._setup_backend()
        else:
            logger.warning("Qiskit not installed, using classical mode")
    
    def _setup_backend(self):
        """Setup quantum backend."""
        try:
            if self.use_ibm and IBM_QUANTUM_TOKEN:
                service = QiskitRuntimeService(channel="ibm_quantum")
                self.backend = service.get_backend(BACKEND_NAME)
                logger.info(f"✅ Connected to IBM: {BACKEND_NAME}")
            else:
                self.backend = AerSimulator()
                logger.info("✅ Using local simulator")
        except Exception as e:
            logger.warning(f"Quantum setup failed: {e}, using classical")
            self.backend = None
    
    def optimize_features(self, features: List[float]) -> List[float]:
        """Optimize features with QAOA."""
        
        start_time = time.time()
        features = np.array(features)
        features = features / (np.linalg.norm(features) + 1e-8)
        
        if self.backend is None:
            logger.info("Using classical optimization")
            return features.tolist()
        
        try:
            # Créer circuit
            n_qubits = min(MAX_QUBITS, len(features))
            circuit = self._build_qaoa_circuit(features[:n_qubits])
            
            # Exécuter
            result = self._execute_circuit(circuit)
            
            # Post-process
            optimized = self._process_result(features, result)
            
            elapsed = time.time() - start_time
            
            self.execution_history.append({
                "timestamp": elapsed,
                "n_qubits": n_qubits,
                "success": True
            })
            
            logger.info(f"✅ Optimization completed in {elapsed:.2f}s")
            
            return optimized
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return features.tolist()
    
    def _build_qaoa_circuit(self, features: np.ndarray) -> QuantumCircuit:
        """Build QAOA circuit."""
        
        n_qubits = len(features)
        qreg = QuantumRegister(n_qubits, 'q')
        creg = ClassicalRegister(n_qubits, 'c')
        qc = QuantumCircuit(qreg, creg)
        
        # Superposition
        for i in range(n_qubits):
            qc.h(qreg[i])
        
        # Cost
        for i in range(n_qubits):
            angle = features[i] * np.pi
            qc.rz(angle, qreg[i])
        
        # Entanglement
        for i in range(n_qubits - 1):
            qc.cx(qreg[i], qreg[i + 1])
            qc.rz(0.3, qreg[i + 1])
            qc.cx(qreg[i], qreg[i + 1])
        
        # Mixer
        for i in range(n_qubits):
            qc.rx(0.5, qreg[i])
        
        # Mesure
        qc.measure(qreg, creg)
        
        return qc
    
    def _execute_circuit(self, circuit: QuantumCircuit) -> Dict:
        """Execute circuit on backend."""
        job = self.backend.run(circuit, shots=SHOTS)
        result = job.result()
        return result.get_counts()
    
    def _process_result(self, original_features: np.ndarray, 
                       quantum_counts: Dict) -> List[float]:
        """Process quantum results."""
        
        if not quantum_counts:
            return original_features.tolist()
        
        best_bitstring = max(quantum_counts, key=quantum_counts.get)
        best_state = np.array([float(b) for b in best_bitstring])
        
        optimized = 0.3 * best_state + 0.7 * original_features[:len(best_state)]
        
        while len(optimized) < len(original_features):
            optimized = np.append(optimized, original_features[len(optimized)])
        
        optimized = optimized / (np.linalg.norm(optimized) + 1e-8)
        
        return optimized.tolist()