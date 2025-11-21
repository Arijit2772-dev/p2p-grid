"""
Sample Job: NumPy Matrix Operations
Demonstrates a job that requires external dependencies.

Requirements: numpy
"""

import numpy as np
import time

print("NumPy Matrix Multiplication Benchmark")
print("=" * 40)

# Test different matrix sizes
sizes = [100, 500, 1000]

for n in sizes:
    print(f"\nMatrix size: {n}x{n}")

    # Create random matrices
    A = np.random.rand(n, n)
    B = np.random.rand(n, n)

    # Time the multiplication
    start = time.time()
    C = np.dot(A, B)
    elapsed = time.time() - start

    print(f"  Time: {elapsed:.4f} seconds")
    print(f"  Result sum: {C.sum():.2f}")
    print(f"  GFLOPS: {(2 * n**3) / elapsed / 1e9:.2f}")

print("\n" + "=" * 40)
print("Benchmark complete!")
