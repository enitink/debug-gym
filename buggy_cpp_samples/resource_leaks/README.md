# Resource Management Bugs Debugging Scenario

## Description
This program simulates a system with file handles and network connections that has multiple resource management bugs. The resources are not properly cleaned up, leading to resource leaks that accumulate over the program's lifetime.

## Resource Management Issues
### File Manager
1. **Missing Destructor**: Files not closed when FileManager is destroyed
2. **Incomplete Close Logic**: Only closes input files, not output files
3. **Counter Corruption**: File count decremented even for non-existent files
4. **Resource Tracking**: Inconsistency between actual open files and counters

### Connection Pool
1. **Missing Cleanup**: Connections not disconnected in destructor
2. **Counter Bugs**: Active connection counter not updated on release/cleanup
3. **Resource State Mismatch**: Actual pool size vs. tracked count inconsistencies
4. **Orphaned Resources**: Disconnected connections not properly removed

## Resource Invariants to Verify
### File Manager Invariants
- `current_file_count` should equal `open_files.size() + output_files.size()`
- All files in maps should have valid, open file streams
- File count should never exceed `max_open_files`
- All files should be properly closed on destruction

### Connection Pool Invariants
- `active_connections` should equal number of connected connections in pool
- All connections in pool should be properly initialized
- Pool size should never exceed `max_connections`
- Disconnected connections should be cleaned up promptly

## Debugging Strategy  
This scenario teaches debug agents to:
- Set breakpoints in resource management methods
- Inspect resource state consistency using GDB
- Examine object lifecycle and cleanup patterns
- Verify resource invariants during program execution
- Understand RAII (Resource Acquisition Is Initialization) violations

## Suggested GDB Commands
```bash
# Set breakpoints at resource management points
gdb(command="break FileManager::open_file_for_reading")
gdb(command="break FileManager::close_file") 
gdb(command="break ConnectionPool::get_connection")
gdb(command="break ConnectionPool::release_connection")

# Run with breakpoints to examine resource states
gdb(command="run_with_break resource_leaks.cpp:28")  # File opening
gdb(command="run_with_break resource_leaks.cpp:72")  # File closing
gdb(command="run_with_break resource_leaks.cpp:154") # Connection creation

# Inspect resource manager states
gdb(command="print current_file_count")         # File counter
gdb(command="print open_files.size()")          # Actual input files
gdb(command="print output_files.size()")        # Actual output files
gdb(command="print active_connections")         # Connection counter
gdb(command="print connections.size()")         # Actual connections

# Verify resource states
gdb(command="call list_open_files()")           # Show file status
gdb(command="call status_report()")             # Show connection status

# Examine individual resources
gdb(command="print *open_files.begin()->second") # File stream state
gdb(command="print connections[0]->get_connected_status()") # Connection state
```

## Expected Debugging Flow
1. **Resource Creation**: Set breakpoints during resource acquisition
2. **State Tracking**: Examine counters vs. actual resource counts
3. **Resource Usage**: Monitor how resources are used and modified
4. **Cleanup Analysis**: Check resource cleanup and counter updates
5. **Invariant Verification**: Verify resource state consistency
6. **Lifecycle Debugging**: Examine constructor/destructor behavior

## Key Learning Points
- How to inspect resource management patterns with GDB
- Understanding RAII and proper resource cleanup in C++
- Debugging resource leaks that don't cause immediate crashes
- Verifying consistency between resource counters and actual states
- Using GDB to examine complex resource ownership relationships
- Identifying subtle bugs in resource lifecycle management