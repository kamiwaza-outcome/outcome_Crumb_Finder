#!/bin/bash
# Run full Friday discovery without any timeouts
echo "Starting full Friday discovery - this will take 15-25 minutes..."
echo "DO NOT INTERRUPT - Let it complete!"
echo "=================================================="

# Run the Python script directly
python3 run_friday.py

echo "=================================================="
echo "Full discovery complete!"