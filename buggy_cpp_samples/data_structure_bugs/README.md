# Data Structure Invariant Violations

## Description
This program implements Binary Search Tree and Priority Queue data structures with subtle bugs that violate fundamental invariants. The program runs without crashing but produces incorrect results that require GDB inspection to identify.

## Data Structure Issues
### Binary Search Tree
1. **Subtree Size Corruption**: Subtree sizes are incorrectly calculated (adding 1 twice)
2. **Height Calculation Error**: Heights calculated as sum instead of max + 1
3. **Node Count Mismatch**: Total node count doesn't match actual tree size
4. **Missing Updates**: Subtree sizes not updated after node removal

### Priority Queue (Heap)
1. **Incomplete Heapification**: Sometimes skips heap_down after extraction
2. **Heap Property Violations**: Parent-child relationships become invalid
3. **Structural Inconsistencies**: Array doesn't maintain proper heap structure

## Data Structure Invariants to Verify
### BST Invariants
- **Ordering**: For each node, left subtree < node < right subtree
- **Subtree Size**: Each node's size = 1 + left_size + right_size
- **Height**: Each node's height = 1 + max(left_height, right_height)
- **Count**: Total node count should match actual tree traversal count

### Heap Invariants
- **Heap Property**: Each parent >= children (max-heap) or <= children (min-heap)
- **Complete Tree**: All levels filled except possibly the last, left-justified
- **Array Representation**: For index i: left_child = 2i+1, right_child = 2i+2

## Debugging Strategy
This scenario teaches debug agents to:
- Set breakpoints in data structure manipulation methods
- Inspect complex recursive data structures using GDB
- Verify mathematical invariants using GDB expressions
- Trace how invariant violations propagate through operations
- Examine both individual node states and overall structure integrity

## Suggested GDB Commands
```bash
# Set breakpoints at key data structure methods
gdb(command="break BinarySearchTree::insert_recursive")
gdb(command="break BinarySearchTree::check_bst_invariant") 
gdb(command="break PriorityQueue::extract_top")
gdb(command="break PriorityQueue::heap_down")

# Run with breakpoints to examine structure corruption
gdb(command="run_with_break data_structure_bugs.cpp:46")  # BST insertion
gdb(command="run_with_break data_structure_bugs.cpp:152") # Heap property check

# Inspect tree node states
gdb(command="print *node")                    # Examine BST node
gdb(command="print node->subtree_size")       # Check size field
gdb(command="print node->height")             # Check height field
gdb(command="call check_bst_invariant()")     # Verify BST invariants

# Inspect heap array state
gdb(command="print heap")                     # View heap array
gdb(command="print heap.size()")              # Array size
gdb(command="call check_heap_property()")     # Verify heap invariants

# Navigate tree structure
gdb(command="print node->left->data")         # Left child value
gdb(command="print node->right->data")        # Right child value
```

## Expected Debugging Flow
1. **Structure Creation**: Set breakpoints during insertion operations
2. **Invariant Checking**: Break at invariant verification methods
3. **State Inspection**: Examine node/element states with GDB
4. **Relationship Verification**: Check parent-child relationships
5. **Corruption Tracing**: Follow how bugs propagate through operations
6. **Fix Implementation**: Correct invariant maintenance in methods

## Key Learning Points
- How to inspect complex recursive data structures with GDB
- Verifying mathematical invariants in data structure implementations  
- Understanding how bugs in fundamental operations corrupt entire structures
- Using GDB to navigate pointer-based tree structures
- Debugging algorithmic correctness vs. just crash-related bugs