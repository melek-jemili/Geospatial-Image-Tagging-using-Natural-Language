import sys
sys.path.insert(0, 'src')

from src.quantum_features_optimizer import QuantumFeatureOptimizer

opt = QuantumFeatureOptimizer(use_ibm=False)
features = [0.5, 0.3, 0.8, 0.2, 0.9]
optimized = opt.optimize_features(features)

print(f"Original: {features}")
print(f"Optimized: {optimized}")