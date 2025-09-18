# Buffer Overflow Bug

## Problem Description
This program contains a buffer overflow vulnerability where it accesses array elements beyond the allocated bounds, causing undefined behavior.

## Bug Details
- Array `arr[5]` has valid indices from 0 to 4
- Loop condition `i <= 7` allows accessing `arr[5]`, `arr[6]`, and `arr[7]`
- These accesses read from unallocated memory locations

## Expected Fix
Change the loop condition from `i <= 7` to `i < 5` to ensure only valid array indices are accessed.

## How to Test
1. Compile: `make`
2. Run: `./buffer_bug`
3. Observe out-of-bounds memory values in the output
4. Use GDB to analyze: `gdb ./buffer_bug` then `run`