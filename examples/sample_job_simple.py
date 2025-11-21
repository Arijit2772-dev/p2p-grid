"""
Sample Job: Simple Computation
This is a basic example showing how jobs work in CampusGrid.
"""

import time

print("Starting computation...")
start = time.time()

# Heavy computation: sum of squares
result = sum(i**2 for i in range(5_000_000))

elapsed = time.time() - start
print(f"Computation completed in {elapsed:.2f} seconds")
print(f"Result: {result:,}")
