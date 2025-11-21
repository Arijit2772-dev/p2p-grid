"""
Sample Job: Generate Output Files
Demonstrates how to create downloadable files from your job.

The job provides:
- OUTPUT_DIR: Directory path where you should save files
- save_output(filename, content): Save text files (txt, csv, json, etc.)
- save_binary(filename, content): Save binary files (PDF, images, etc.)
"""

import json
import os

print("Generating output files demo...")

# Method 1: Use save_output for TEXT files
save_output("results.txt", """
Analysis Results
================
Total items processed: 1000
Success rate: 98.5%
Average processing time: 0.023s
""")

# Method 2: Write directly to OUTPUT_DIR
report_data = {
    "title": "Computation Report",
    "timestamp": "2024-01-15 10:30:00",
    "metrics": {
        "accuracy": 0.95,
        "precision": 0.93,
        "recall": 0.97
    },
    "summary": "All computations completed successfully"
}

# Save JSON report
json_path = os.path.join(OUTPUT_DIR, "report.json")
with open(json_path, 'w') as f:
    json.dump(report_data, f, indent=2)
print(f"[OUTPUT] Saved: report.json")

# Save CSV data
csv_content = """id,name,score,status
1,Item A,95.5,pass
2,Item B,87.3,pass
3,Item C,72.1,pass
4,Item D,45.6,fail
5,Item E,91.2,pass
"""
save_output("data.csv", csv_content)

print()
print("Job completed! Files are available for download:")
print("  - results.txt")
print("  - report.json")
print("  - data.csv")
