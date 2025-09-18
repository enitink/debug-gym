"""
C++ Debug Environment for debug-gym
Extends the base RepoEnv to handle C++ programs instead of Python
"""
import os
import subprocess
from pathlib import Path
from debug_gym.gym.envs.env import RepoEnv
from debug_gym.gym.entities import EvalOutput, Observation
from debug_gym.gym.tools.toolbox import Toolbox
from debug_gym.gym.tools.rewrite import RewriteTool


class CppRewriteTool(RewriteTool):
    """C++-specific rewrite tool with proper language context"""
    name = "rewrite"
    examples = [
        """rewrite(path="memory_leak.cpp", start=None, end=None, new_code="#include <iostream>\\nint main() { return 0; }") will rewrite the entire C++ file.""",
        """rewrite(path="buffer_overflow.cpp", start=10, end=None, new_code="    delete[] buffer;") will rewrite line 10 with proper C++ memory deallocation.""",
        """rewrite(path="race_condition.cpp", start=15, end=20, new_code="    std::lock_guard<std::mutex> lock(mtx);\\n    shared_data++;") will replace lines 15-20 with thread-safe C++ code.""",
        """rewrite(path='main.cpp', start=4, end=6, new_code="        std::cout << \\"Hello World\\" << std::endl;") will replace lines 4-6 with proper C++ output statement.""",
    ]
    description = (
        "Rewrite the content of the specified C++ file path, between lines [start, end], with the new code. Line numbers are 1-based. When start is provided and end is None, it's assumed to rewrite a single line (start). When both start and end are None, it's assumed to rewrite the whole file, this is not recommended because most of the time the expected edit is local. The new code should be valid C++ code with proper indentation and syntax."
        + "\nExamples for C++ debugging (for demonstration purposes only, you need to adjust the tool calling format according to your specific syntax):"
        + "\n".join(examples)
    )
    arguments = {
        "path": {
            "type": ["string"],
            "description": "A C++ file path to be rewritten (*.cpp, *.h, *.hpp).",
        },
        "start": {
            "type": ["number", "null"],
            "description": "The starting line number to be rewritten. If None, the whole file will be rewritten.",
        },
        "end": {
            "type": ["number", "null"],
            "description": "The ending line number to be rewritten. If None, end is the same as start.",
        },
        "new_code": {
            "type": ["string"],
            "description": "The new C++ code to be inserted. The code should be valid C++ with proper indentation, syntax, and memory management.",
        },
    }


class CppDebugEnv(RepoEnv):
    """C++ debugging environment that handles C++ compilation and execution"""
    def _prepare_entrypoint(self, entrypoint):
        """Override base class to avoid Python wrapping of C++ executables"""
        # For C++ debugging, return entrypoint as-is without Python wrapping
        return entrypoint
    
    def __init__(
        self,
        build_command: str = "make",
        source_path: str = None,
        **kwargs
    ):
        # Store C++ specific settings
        self.build_command = build_command
        
        # Handle source_path parameter - pass it as path to parent
        if source_path is not None:
            kwargs['path'] = source_path
        
        # Initialize parent class
        super().__init__(**kwargs)
        

        """Override to NOT wrap with Python - return C++ command as-is"""
    def eval(self, **kwargs) -> EvalOutput:
        """
        C++ evaluation that builds, runs, and detects various issues including memory leaks:
        1. Build the program
        2. Run it to detect crashes or success
        3. If crash detected, automatically run GDB for analysis
        4. Check for memory leaks using valgrind (if available)
        5. Report the results
        """
        # Step 1: Try to build the program
        build_success, build_output = self.terminal.run(self.build_command, timeout=30)
        
        if not build_success:
            return EvalOutput(
                success=False, 
                output=f"BUILD FAILED:\n{build_output}"
            )
        
        # Step 2: Run the compiled program normally
        run_command = self.entrypoint
        if not run_command.startswith("timeout"):
            run_command = f"timeout 15 {run_command}"
            
        success, output = self.terminal.run(run_command, timeout=self.run_timeout)
        
        # Step 3: If crash detected, automatically run GDB analysis
        gdb_output = ""
        if self._is_crash_detected(output):
            self.logger.info("💥 Crash detected! Running GDB analysis...")
            gdb_success, gdb_output = self.terminal.run(self.debug_entrypoint, timeout=30)
            if gdb_success:
                output = f"{output}\n\n🔍 GDB ANALYSIS:\n{gdb_output}"
            
        # Step 4: Check for memory leaks using valgrind
        valgrind_output = ""
        memory_issues_detected = False
        
        # Try to run with valgrind for memory leak detection
        # Extract the executable path from debug_entrypoint (same approach as GDB)
        # debug_entrypoint format: "PYTHONPATH=$PYTHONPATH:$PWD ./executable"
        executable_path = self.debug_entrypoint.split()[-1]  # Get the last part (the actual executable)
        valgrind_command = f"valgrind --leak-check=full --error-exitcode=1 --quiet {executable_path}"
        valgrind_success, valgrind_result = self.terminal.run(valgrind_command, timeout=30)
        
        if valgrind_result:
            valgrind_output = f"\n\n🔍 MEMORY ANALYSIS (valgrind):\n{valgrind_result}"
            # valgrind exits with error code if memory issues are found
            if not valgrind_success or "definitely lost" in valgrind_result or "possibly lost" in valgrind_result:
                memory_issues_detected = True
            output += valgrind_output
        else:
            # Fallback: Static analysis for obvious memory issues
            memory_issues_detected = self._static_memory_analysis()
            if memory_issues_detected:
                output += f"\n\n🔍 STATIC MEMORY ANALYSIS:\nPotential memory leak detected - missing delete[] or delete statements"
            
        # Evaluate the execution
        cpp_success = self._evaluate_cpp_execution(success, output, build_output)
        
        # Enhanced output with build + run results
        combined_output = f"BUILD: ✅ Success\n{build_output}\n\nPROGRAM EXECUTION:\n{output}"
        
        # Success requires: build success, no crashes, AND no memory issues
        overall_success = cpp_success and not self._is_crash_detected(output) and not memory_issues_detected
        
        self.last_eval = EvalOutput(overall_success, combined_output)
        return self.last_eval

    def _is_crash_detected(self, output: str) -> bool:
        """Detect if the program crashed based on output patterns"""
        crash_indicators = [
            "segmentation fault",
            "segfault", 
            "signal sigkill",
            "signal sigterm", 
            "signal sigabrt",
            "signal sigsegv",
            "core dumped",
            "aborted",
            "killed",
            "invalid memory reference",
            "stack overflow",
            "double free",
            "heap corruption"
        ]
        
        output_lower = output.lower()
        return any(indicator in output_lower for indicator in crash_indicators)

    def _static_memory_analysis(self) -> bool:
        """
        Static analysis to detect potential memory leaks by looking for 
        new/new[] without corresponding delete/delete[]
        """
        try:
            # Find any C++ source files
            source_files = list(self.workspace.working_dir.glob("*.cpp"))
            if not source_files:
                return False
            
            for source_file in source_files:
                with open(source_file, 'r') as f:
                    content = f.read()
                
                # Count new/new[] vs delete/delete[]
                new_count = content.count('new ') + content.count('new[')
                delete_count = content.count('delete ') + content.count('delete[]')
                
                # If we have new but no delete, likely a memory leak
                if new_count > 0 and delete_count == 0:
                    return True
                    
                # More sophisticated check - look for missing delete[] specifically
                if 'new[' in content and 'delete[]' not in content:
                    return True
                    
        except Exception as e:
            self.logger.warning(f"Static memory analysis failed: {e}")
            
        return False

    def _evaluate_cpp_execution(self, run_success, run_output, build_output):
        """
        Evaluate C++ program execution success.
        For debugging purposes, even crashes are useful.
        """
        # Build must succeed
        if "error:" in build_output.lower():
            return False
            
        # For runtime, crashes are actually useful for debugging
        # We only fail if we can't run the program at all
        if "command not found" in run_output.lower():
            return False
        if "permission denied" in run_output.lower():
            return False
            
        # Otherwise, we successfully ran the program (even if it crashed)
        return True
        
    def add_tool(self, tool):
        """Override to replace rewrite tool with C++ version"""
        # Debug logging
        self.logger.info(f"CppDebugEnv.add_tool called with tool: {tool.name} (type: {type(tool).__name__})")
        
        # If this is a rewrite tool, replace it with our C++ version
        if tool.name == "rewrite" and not isinstance(tool, CppRewriteTool):
            self.logger.info("Replacing Python rewrite tool with C++ version")
            cpp_tool = CppRewriteTool()
            super().add_tool(cpp_tool)
        else:
            super().add_tool(tool)

    def _discover_available_files(self) -> str:
        """Discover what C++ source files are available in the workspace"""
        source_files = list(self.workspace.working_dir.glob("*.cpp"))
        header_files = list(self.workspace.working_dir.glob("*.h")) + list(self.workspace.working_dir.glob("*.hpp"))
        
        if not source_files and not header_files:
            return "No C++ files found in the workspace."
        
        file_list = []
        if source_files:
            file_list.append(f"Source files: {', '.join([f.name for f in source_files])}")
        if header_files:
            file_list.append(f"Header files: {', '.join([f.name for f in header_files])}")
            
        return "\n".join(file_list)

    def setup_workspace(self) -> None:
        """Setup the workspace with C++ specific configurations"""
        # Call parent class to copy source files from source_path
        super().setup_workspace()
        
        # Create or ensure Makefile exists for building
        makefile_path = self.workspace.working_dir / "Makefile"
        if not makefile_path.exists():
            self.logger.info(f"Creating default Makefile: {makefile_path}")
            # Try to infer target name from entrypoint
            target_name = self.entrypoint.lstrip('./')
            source_files = list(self.workspace.working_dir.glob("*.cpp"))
            if source_files:
                main_source = source_files[0].name
                with open(makefile_path, 'w') as f:
                    f.write(f"""# Auto-generated Makefile for C++ debugging
CXX=g++
CXXFLAGS=-std=c++11 -g -O0 -Wall -Wextra -pthread
TARGET={target_name}
SOURCE={main_source}

$(TARGET): $(SOURCE)
\t$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCE)

clean:
\trm -f $(TARGET)

.PHONY: clean
""")
                self.logger.info(f"Created Makefile with target={target_name}, source={main_source}")
        else:
            self.logger.info(f"Using existing Makefile: {makefile_path}")

    def _discover_available_files(self) -> str:
        """Discover what C++ source files are available in the workspace"""
        source_files = list(self.workspace.working_dir.glob("*.cpp"))
        header_files = list(self.workspace.working_dir.glob("*.h")) + list(self.workspace.working_dir.glob("*.hpp"))
        
        if not source_files and not header_files:
            return "No C++ files found in the workspace."
        
        file_list = []
        if source_files:
            file_list.append(f"Source files: {', '.join([f.name for f in source_files])}")
        if header_files:
            file_list.append(f"Header files: {', '.join([f.name for f in header_files])}")
            
        return "\n".join(file_list)



    def reset(self, *, options: dict = None):
        """
        Override reset to prevent Python evaluation of C++ executables
        """
        options = options or {}
        self.logger.info("Resetting C++ environment")
        self.setup_task(task_name=options.get("task_name"), options=options)
        self.setup_workspace()
        self.setup_terminal()
        self._reset_env_state()
        
        # Add GDB tool for C++ debugging (if not already added via configuration)
        if not any(tool.name == 'gdb' for tool in self.tools if hasattr(tool, 'name')):
            try:
                from debug_gym.gym.tools.gdb_tool import GDBTool
                gdb_tool = GDBTool()
                self.add_tool(gdb_tool)
                self.logger.info("GDB tool added to C++ environment")
            except ImportError as e:
                self.logger.warning(f"GDB tool not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to add GDB tool: {e}")
        else:
            self.logger.info("GDB tool already added via configuration")

        # Notify all tools that the environment is reset - but prevent auto-eval
        from debug_gym.gym.entities import Event
        self.queue_event(Event.ENV_RESET, source="env")
        
        # IMPORTANT: Filter out eval observations to prevent Python interpretation
        self.all_observations = []
        for obs in self.process_events():
            # Skip any eval observations that would trigger Python interpreter
            if obs.source != 'eval':
                self.all_observations.append(obs)

        # Create initial evaluation that indicates debugging work is needed
        from debug_gym.gym.entities import EvalOutput
        
        # Discover available files dynamically
        available_files = self._discover_available_files()
        
        # Set up a generic debugging task description that doesn't assume specific bugs
        task_description = f"""C++ Debugging Task: Analyze and Fix Issues
        
AVAILABLE FILES:
{available_files}

TASK: Use debugging tools to analyze the program, identify any issues, and fix them.

STEPS:
1. Use 'view' to examine the source code and understand the program
2. Use 'eval' to build and run the program to see if there are any issues
3. If issues are found, use 'gdb' to debug and analyze the problem
4. Use 'rewrite' to fix any identified issues
5. Use 'eval' again to verify the fix

The debugger will help you discover what type of issues exist rather than assuming specific problems."""
        
        # Initial evaluation should be False to indicate work needs to be done
        self.last_eval = EvalOutput(False, task_description)
        self.step_observation = Observation("env", task_description)
        
        # Add our safe observation to the front
        self.all_observations.insert(0, self.step_observation)

        self.max_score = self.calculate_max_score(self.last_eval)
        self.score = self.calculate_score(self.last_eval)
        self.done = self.calculate_done(self.last_eval)

        from debug_gym.gym.envs.env import EnvInfo
        self.infos = EnvInfo(
            step_observation=self.step_observation,
            all_observations=self.all_observations,
            eval_observation=Observation("env", self.last_eval.output),
            dir_tree=self.workspace.display_files(self.dir_tree_depth),
            current_breakpoints=self.current_breakpoints(),
            action_reasoning=None,
            action_content=None,
            action_tool_call=None,
            done=self.done,
            score=self.score,
            max_score=self.max_score,
            instructions=self.instructions,
            rewrite_counter=self.rewrite_counter,
            tools=self.tools,
        )
        return self.infos

    @property
    def instructions(self) -> str:
        """Instructions specific to C++ debugging"""
        available_files = self._discover_available_files()
        return f"""
C++ Debugging Environment:
- Build command: {self.build_command}
- Available files: {available_files}
- Debug symbols enabled (-g -O0)

Available debugging workflow:
1. View source: view <filename>.cpp
2. Build & run: eval (automatically builds then runs)
3. Debug with GDB: gdb command="run"
4. Fix code: rewrite <filename>.cpp start_line end_line new_code

Use the interactive debugger to discover what issues exist rather than assuming specific problems.
Focus on analyzing program behavior, crashes, and runtime issues.
"""