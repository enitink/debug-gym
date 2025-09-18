# Object Memory Leak Debugging Scenario

## Description
This program simulates a data processing system that has multiple subtle memory leaks requiring GDB inspection to identify.

## Memory Leak Issues
1. **Missing Destructors**: `DataProcessor` class doesn't properly clean up allocated memory
2. **Incomplete Cleanup**: Only 1 in 10 temporary buffers are cleaned up  
3. **Object Management**: `ProcessorManager` doesn't delete processor objects
4. **Resource Accumulation**: Memory usage grows over time during simulation

## Debugging Strategy
This scenario is designed to help debug agents learn to:
- Set breakpoints in class methods to inspect object states
- Examine memory allocation patterns over time
- Use GDB to inspect private member variables
- Understand object lifecycle and resource management

## Suggested GDB Commands
```bash
# Set breakpoints to inspect object states
gdb(command="break DataProcessor::process_batch")
gdb(command="break ProcessorManager::create_processor") 
gdb(command="break main")

# Run with breakpoint to examine states
gdb(command="run_with_break object_leak.cpp:35")  # Inside process_batch
gdb(command="run_with_break object_leak.cpp:74")  # Inside create_processor

# Inspect object states when stopped at breakpoints
gdb(command="info locals")           # Show local variables
gdb(command="print *processor")      # Examine processor object
gdb(command="print temp_buffers.size()") # Check buffer count
gdb(command="print manager.processors.size()") # Check processor count
```

## Expected Debugging Flow
1. **Initial Run**: Execute program and observe memory growth patterns
2. **Set Breakpoints**: Break in key methods to examine object states
3. **Inspect Objects**: Use GDB to examine private members and invariants
4. **Identify Leaks**: Correlate object states with memory allocation issues
5. **Verify Fixes**: Ensure proper cleanup and destructor implementation

## Key Learning Points
- How to use GDB to inspect C++ object internal state
- Understanding object lifecycle in C++ programs
- Identifying subtle resource leaks that don't cause crashes
- Using breakpoints to verify invariants during execution