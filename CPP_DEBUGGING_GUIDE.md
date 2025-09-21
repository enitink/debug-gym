# C++ Debugging Support for Debug Gym

This guide explains the C++ debugging functionality added to Debug Gym, including interactive GDB integration, dynamic file discovery, and comprehensive memory leak detection for debugging C++ programs.

## Overview

Debug Gym now supports C++ program debugging with the following key components:

### Core Components

1. **GDB Tool** (`debug_gym/gym/tools/gdb.py`)
   - Interactive GDB debugger integration
   - Supports common GDB commands: `run`, `bt`, `info registers`, `list`, `disas`, etc.
   - Automatic binary detection and execution

2. **C++ Environment** (`debug_gym/gym/envs/cpp_env.py`)
   - Specialized environment for C++ program debugging
   - Automatic compilation support with debug symbols
   - **Dynamic file discovery** - automatically detects available C++ source files
   - **Comprehensive memory leak detection** using Valgrind and static analysis
   - **Generic task setup** - discovers issues through debugging rather than hardcoded assumptions
   - C++-specific rewrite tool with proper language context

3. **C++ Debug Agent** (`debug_gym/agents/debug_agent_cpp.py`)
   - Specialized agent for C++ debugging workflows
   - Focuses on memory management, threading, and resource leaks
   - Proper C++ debugging methodology

### Key Features

- **Interactive GDB Integration**: Full GDB debugger support for crash analysis, backtrace examination, and memory inspection
- **Automatic Compilation**: Seamless C++ program compilation with debug symbols
- **Dynamic File Discovery**: Automatically detects and lists available C++ source files in the workspace
- **Memory Leak Detection**: Comprehensive memory analysis using:
  - **Valgrind Integration**: Runtime memory leak detection with `--leak-check=full`
  - **Static Analysis**: Fallback detection for new[]/delete[] mismatches when Valgrind is unavailable
- **Enhanced Evaluation Logic**: Success criteria now requires no crashes AND no memory issues
- **Generic Task Setup**: Discovers issues through interactive debugging rather than assuming specific bug types
- **C++ Language Context**: Proper understanding of C++ syntax, memory management, and threading
- **Automatic Makefile Generation**: Creates appropriate build configuration when needed

## Usage

### Configuration

Use the provided configuration file for C++ debugging:

```yaml
# scripts/config_cpp_gdb_live_test.yaml
environment:
  name: "cpp_env"
  entrypoint: "./your_program"
  debug_entrypoint: "./your_program"

agent:
  name: "cpp_debug_agent"
  max_steps: 10
  temperature: 0.1

llm:
  model_name: "gpt-4o-mini-fast"
  # ... other LLM settings
```

### Running C++ Debugging Sessions

```bash
# Basic C++ debugging session
python scripts/run.py scripts/config_cpp_gdb_live_test.yaml -p 'entrypoint=./your_cpp_program'

# Memory leak debugging example
python scripts/run.py scripts/config_cpp_memory_leak_demo.yaml --agent cpp_debug_agent -vv
```

### Available Tools

1. **gdb** - Interactive GDB debugging
   - `gdb(command="run")` - Execute program under GDB
   - `gdb(command="bt")` - Show backtrace
   - `gdb(command="info registers")` - Show CPU registers
   - `gdb(command="x/10x $rsp")` - Examine memory
   - `gdb(command="list")` - Show source code
   - `gdb(command="info locals")` - Show local variables

2. **view** - Examine C++ source files
3. **rewrite** - Fix bugs in C++ source files with C++-specific language awareness
4. **eval** - Build and run C++ programs with comprehensive analysis:
   - Automatic compilation with debug symbols
   - Memory leak detection via Valgrind
   - Static analysis for obvious memory issues
   - Enhanced success criteria (no crashes AND no memory leaks)

## Implementation Details

### GDB Tool Implementation

The GDB tool provides interactive debugging capabilities:

- Automatic GDB session management
- Command execution with proper error handling
- Binary file detection and loading
- Memory and register examination support

### C++ Environment Features

- Extends base RepoEnv for C++ programs
- **Dynamic File Discovery**: Automatically detects available C++ source files (.cpp) and headers (.h, .hpp)
- **Memory Leak Detection**: 
  - Valgrind integration with `--leak-check=full --error-exitcode=1 --quiet`
  - Static analysis fallback for new[]/delete[] mismatch detection
- **Enhanced Evaluation Logic**: Success requires compilation success, no crashes, AND no memory issues
- Custom rewrite tool with C++ language awareness
- Automatic compilation with debug symbols (`-g -O0` flags)
- **Generic Task Setup**: Uses interactive debugging to discover issues rather than hardcoded assumptions
- Automatic Makefile generation when needed
- Proper C++ error handling and reporting

### Agent Specialization

The C++ debug agent is specialized for:
- Memory management bugs (leaks, overflows, use-after-free)
- Threading and synchronization issues
- Resource management problems
- C++-specific debugging workflows

## Example Debugging Workflow

1. **Environment Setup**: Environment automatically discovers available C++ files and sets up generic debugging task
2. **Initial Analysis**: Agent examines discovered source files using `view` tool
3. **Build and Test**: Use `eval` to compile and run program, detecting crashes or memory issues
4. **Interactive Debugging**: If issues found, use GDB (`gdb command="run"`) to analyze crashes and program state
5. **Memory Analysis**: Automatic Valgrind analysis detects memory leaks with detailed output
6. **Fix Issues**: Use `rewrite` to apply fixes to source code with proper C++ syntax
7. **Verify Fix**: Re-run `eval` to ensure both crashes and memory leaks are resolved
8. **Success Criteria**: Task completion requires no compilation errors, no crashes, AND no memory leaks

### Example Memory Leak Detection Output

```
BUILD: ✅ Success
g++ -std=c++11 -g -O0 -Wall -Wextra -pthread -o memory_leak memory_leak.cpp

PROGRAM EXECUTION:
Memory allocated successfully!

🔍 MEMORY ANALYSIS (valgrind):
==1234== 400 bytes in 1 blocks are definitely lost in loss record 1 of 1
==1234==    at 0x123456: operator new[](unsigned long) (vg_replace_malloc.c:640)
==1234==    at 0x789ABC: main (memory_leak.cpp:8)
```

## Supported Bug Types

- **Memory Management Issues**:
  - Memory leaks (detected via Valgrind and static analysis)
  - Buffer overflows and underflows
  - Use-after-free and double-free errors
  - new[]/delete[] mismatches
- **Runtime Crashes**:
  - Null pointer dereferences
  - Segmentation faults
  - Stack overflow and infinite recursion
- **Concurrency Issues**:
  - Race conditions and threading issues
  - Resource management problems
- **General C++ Issues**:
  - Compilation errors
  - Logic errors discovered through interactive debugging

## Key Improvements

### Dynamic Discovery vs. Hardcoded Assumptions
- **Old Approach**: Environment assumed specific bug types and looked for hardcoded filenames
- **New Approach**: Environment discovers available files and lets interactive debugging reveal actual issues

### Comprehensive Memory Analysis
- **Runtime Detection**: Valgrind integration provides detailed memory leak analysis
- **Static Fallback**: When Valgrind unavailable, static analysis detects obvious memory issues  
- **Enhanced Success Criteria**: Tasks only succeed when both crashes AND memory leaks are resolved

### Generic Task Setup
- **Flexible**: Works with any C++ program regardless of specific bug types
- **Discovery-Based**: Uses debugging tools to find issues rather than making assumptions
- **Comprehensive**: Handles compilation, runtime, and memory issues in a unified workflow

This implementation provides a comprehensive C++ debugging environment within the Debug Gym framework, enabling dynamic discovery of issues, interactive debugging of C++ programs, and thorough memory analysis with proper tool integration and language-specific support. The environment now handles any type of C++ debugging scenario without requiring hardcoded assumptions about specific bug types.