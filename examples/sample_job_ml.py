"""
Sample Job: Machine Learning Training
Demonstrates ML model training on the P2P network.

Requirements:
numpy
scikit-learn
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.datasets import make_classification
import time

print("ML Model Training Benchmark")
print("=" * 50)

# Generate synthetic dataset
print("\nGenerating dataset...")
X, y = make_classification(
    n_samples=5000,
    n_features=20,
    n_informative=15,
    n_classes=2,
    random_state=42
)
print(f"Dataset: {X.shape[0]} samples, {X.shape[1]} features")

# Models to train
models = {
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=50, random_state=42),
}

print("\nTraining models...")
results = {}

for name, model in models.items():
    print(f"\n{name}:")
    start = time.time()

    # 5-fold cross-validation
    scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')

    elapsed = time.time() - start
    results[name] = {
        'accuracy': scores.mean(),
        'std': scores.std(),
        'time': elapsed
    }

    print(f"  Accuracy: {scores.mean():.4f} (+/- {scores.std():.4f})")
    print(f"  Training time: {elapsed:.2f}s")

print("\n" + "=" * 50)
print("Best model:", max(results, key=lambda x: results[x]['accuracy']))
print("Training complete!")
