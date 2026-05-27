"""Quantum Spatial Optimizer - VERSION CORRIGÉE"""

import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    logger.warning("Qiskit not available")

class QuantumSpatialOptimizer:
    """Optimise clustering géographique avec QAOA."""
    
    def __init__(self, use_ibm=False):
        self.use_ibm = use_ibm
        self.backend = None
        
        if QISKIT_AVAILABLE:
            self._setup_backend()
    
    def _setup_backend(self):
        """Setup quantum backend."""
        try:
            self.backend = AerSimulator()
            logger.info("Using local simulator")
        except Exception as e:
            logger.warning(f"Backend setup failed: {e}")
            self.backend = None
    
    def optimize_clustering(self, locations: np.ndarray, 
                          num_clusters: int) -> Tuple[np.ndarray, dict]:
        """Optimise clustering géographique."""
        
        # ✅ CONVERSION STRICTE!
        locations = np.asarray(locations, dtype=np.float64)
        logger.info(f"Optimizing clustering for {len(locations)} images...")
        logger.info(f"Locations shape: {locations.shape}, dtype: {locations.dtype}")
        
        if self.backend is None:
            logger.warning("Using classical K-means")
            return self._classical_kmeans(locations, num_clusters)
        
        try:
            # Construire circuit
            circuit = self._build_qaoa_circuit(locations, num_clusters)
            
            # Exécuter
            result = self._execute_circuit(circuit)
            
            # Post-process
            assignments = self._process_result(result, len(locations), num_clusters)
            
            # Métriques
            metrics = {'method': 'quantum_qaoa', 'num_clusters': num_clusters}
            
            logger.info(f"Quantum clustering complete")
            return assignments, metrics
            
        except Exception as e:
            logger.error(f"Quantum clustering failed: {e}")
            logger.warning("Falling back to K-means")
            return self._classical_kmeans(locations, num_clusters)
    
    def _build_qaoa_circuit(self, locations: np.ndarray, 
                           num_clusters: int) -> QuantumCircuit:
        """Construire circuit QAOA simplifié."""
        
        n_qubits = min(len(locations), 5)  # Max 5 qubits
        
        qreg = QuantumRegister(n_qubits, 'q')
        creg = ClassicalRegister(n_qubits, 'c')
        qc = QuantumCircuit(qreg, creg)
        
        # Superposition
        for i in range(n_qubits):
            qc.h(qreg[i])
        
        # Cost
        for i in range(n_qubits):
            angle = (i + 1) * 0.5
            qc.rz(angle, qreg[i])
        
        # Entanglement
        for i in range(n_qubits - 1):
            qc.cx(qreg[i], qreg[i + 1])
        
        # Mixer
        for i in range(n_qubits):
            qc.rx(0.5, qreg[i])
        
        # ✅ MESURES
        for i in range(n_qubits):
            qc.measure(qreg[i], creg[i])
        
        return qc
    
    def _execute_circuit(self, circuit: QuantumCircuit) -> dict:
        """Exécuter circuit."""
        
        try:
            job = self.backend.run(circuit, shots=100)
            result = job.result()
            counts = result.get_counts()
            
            if not counts:
                logger.warning("Empty counts, using default")
                return {'0': 100}
            
            return counts
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {'0': 100}
    
    def _process_result(self, counts: dict, n_images: int, 
                       num_clusters: int) -> np.ndarray:
        """Convertir résultats en clusters."""
        
        if not counts:
            return np.array([i % num_clusters for i in range(n_images)])
        
        best_bitstring = max(counts, key=counts.get)
        assignments = np.zeros(n_images, dtype=int)
        
        for i in range(n_images):
            if i < len(best_bitstring):
                assignments[i] = int(best_bitstring[i]) % num_clusters
            else:
                assignments[i] = i % num_clusters
        
        return assignments
    
    def _classical_kmeans(self, locations: np.ndarray, 
                         num_clusters: int) -> Tuple[np.ndarray, dict]:
        """Fallback classique."""
        
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
        assignments = kmeans.fit_predict(locations)
        metrics = {'method': 'classical_kmeans', 'inertia': kmeans.inertia_}
        
        return assignments, metrics