# Buggy C++ Samples for Debug Gym

This directory contains various C++ programs with intentional bugs for testing and demonstrating the Debug Gym C++ debugging capabilities.

## Available Samples

### 1. Buffer Overflow (`buffer_overflow/`)
- **File**: `buffer_bug.cpp`
- **Bug**: Array access beyond bounds
- **Symptoms**: Undefined behavior, random memory values
- **Fix**: Correct loop bounds

### 2. Memory Leak (`memory_leak/`)
- **File**: `memory_leak.cpp`
- **Bug**: Missing `delete[]` for dynamically allocated memory
- **Symptoms**: Memory not freed, detectable with valgrind
- **Fix**: Add proper memory deallocation

### 3. Null Pointer Dereference (`null_pointer/`)
- **File**: `null_deref.cpp`
- **Bug**: Dereferencing a null pointer
- **Symptoms**: Segmentation fault
- **Fix**: Check pointer validity before dereferencing

## Usage with Debug Gym

Each sample directory can be used as a source path in Debug Gym configurations:

```yaml
env_kwargs:
  source_path: "buggy_cpp_samples/buffer_overflow"
  entrypoint: "./buffer_bug"
  debug_entrypoint: "gdb ./buffer_bug"
```

## Testing Individually

Each sample includes its own Makefile for standalone testing:

```bash
cd buggy_cpp_samples/buffer_overflow
make
./buffer_bug
```