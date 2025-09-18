import os
import subprocess
import tempfile
import time

from debug_gym.gym.entities import Observation
from debug_gym.gym.tools.tool import EnvironmentTool
from debug_gym.gym.tools.toolbox import Toolbox


@Toolbox.register("gdb")
class GDBTool(EnvironmentTool):
    """Interactive GDB debugging tool for C++ programs that supports human-like debugging workflows"""
    
    name = "gdb"
    examples = [
        """gdb(command="start") - Start the program under GDB (doesn't run to completion)""",
        """gdb(command="break main") - Set a breakpoint at the main function""",
        """gdb(command="break filename.cpp:42") - Set a breakpoint at line 42 in filename.cpp""",
        """gdb(command="run") - Run the program (will stop at breakpoints)""",
        """gdb(command="continue") - Continue execution from current breakpoint""",
        """gdb(command="step") - Execute one line of source code""",
        """gdb(command="next") - Execute next line (step over function calls)""",
        """gdb(command="finish") - Execute until current function returns""",
        """gdb(command="bt") - Show backtrace/call stack""",
        """gdb(command="info locals") - Show local variable values""",
        """gdb(command="info args") - Show function arguments""",
        """gdb(command="print variable_name") - Print value of a specific variable (searches all frames if needed)""",
        """gdb(command="print *pointer") - Dereference and print pointer value""",
        """gdb(command="frame 2") - Switch to stack frame number 2""",
        """gdb(command="up") - Move up one frame in the call stack""",
        """gdb(command="down") - Move down one frame in the call stack""",
        """gdb(command="info frame") - Show detailed information about current frame""",
        """gdb(command="list") - Show source code around current location""",
        """gdb(command="info breakpoints") - Show all breakpoints""",
        """gdb(command="delete 1") - Delete breakpoint number 1""",
        """gdb(command="watch variable_name") - Set a watchpoint on variable""",
        """gdb(command="x/10x $rsp") - Examine memory (10 hex words from stack pointer)""",
        """gdb(command="info registers") - Show CPU register values""",
        """gdb(command="disas") - Show disassembly of current function""",
    ]
    
    description = (
        "Execute GDB debugger commands to interactively debug C++ programs. "
        "This tool supports human-like debugging workflows including setting breakpoints, "
        "stepping through code, examining variables and memory, and inspecting program state. "
        "Unlike batch debugging, this allows you to pause execution and examine state at any point."
        + "\n\nInteractive GDB commands for debugging:\n"
        + "\n".join(examples)
    )
    
    arguments = {
        "command": {
            "type": ["string"],
            "description": "GDB command to execute. Interactive commands: 'start' (start program), 'break <location>' (set breakpoint), 'run' (execute), 'continue' (resume), 'step' (step into), 'next' (step over), 'print <var>' (examine variable), 'info locals' (show variables), 'bt' (backtrace), 'list' (show source), etc.",
        },
    }

    def __init__(self):
        super().__init__()
        self.gdb_session_file = None
        self.executable_path = None
        self.session_active = False
        # Make these attributes not serializable to avoid pickle issues
        self._gdb_process = None
        self.program_running = False
        self.breakpoints_set = []
    
    @property 
    def gdb_process(self):
        """Property to access the GDB process"""
        return self._gdb_process
        
    @gdb_process.setter
    def gdb_process(self, value):
        """Property setter for GDB process"""
        self._gdb_process = value
    
    def __getstate__(self):
        """Custom serialization to exclude unpicklable attributes"""
        state = self.__dict__.copy()
        # Remove the unpicklable GDB process
        state['_gdb_process'] = None
        return state
    
    def __setstate__(self, state):
        """Custom deserialization to restore state"""
        self.__dict__.update(state)
        # Restore the process as None - will be recreated when needed
        self._gdb_process = None

    def use(self, environment, command: str) -> Observation:
        """Execute GDB command in interactive debugging session"""
        try:
            # Prepare for debugging session
            if not self._prepare_session(environment):
                return Observation(self.name, "❌ GDB Error: Failed to prepare debugging session")
            
            # Handle session initialization
            if command in ["start", "begin"]:
                return self._start_debugging_session()
            
            # Execute the command in interactive mode
            return self._execute_interactive_command(command)
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")

    def _prepare_session(self, environment) -> bool:
        """Prepare the GDB debugging session"""
        try:
            # Get the executable path from environment
            full_entrypoint = environment.entrypoint
            
            # Extract executable path
            if "PYTHONPATH=" in full_entrypoint and " ./" in full_entrypoint:
                executable_path = full_entrypoint.split(" ./")[-1]
                self.executable_path = f"./{executable_path}"
            elif full_entrypoint.startswith("./"):
                self.executable_path = full_entrypoint
            else:
                self.executable_path = f"./{full_entrypoint}"
            
            # Change to workspace directory
            self.working_dir = environment.workspace.working_dir
            old_cwd = os.getcwd()
            os.chdir(self.working_dir)
            
            try:
                # Ensure executable exists
                if not os.path.exists(self.executable_path.lstrip("./")):
                    self._ensure_executable_built(environment)
                    
                    if not os.path.exists(self.executable_path.lstrip("./")):
                        return False
                
                return True
            finally:
                os.chdir(old_cwd)
                
        except Exception:
            return False

    def _start_debugging_session(self) -> Observation:
        """Start a new GDB debugging session"""
        try:
            old_cwd = os.getcwd()
            os.chdir(self.working_dir)
            
            try:
                # Create GDB command script for starting session
                gdb_commands = [
                    "set confirm off",
                    "set print pretty on", 
                    "set print array on",
                    "set print array-indexes on",
                    f"file {self.executable_path}",
                    "info sources",  # Show loaded source files
                    "info functions",  # Show available functions
                ]
                
                result = self._run_gdb_commands(gdb_commands)
                
                self.session_active = True
                return Observation(
                    self.name, 
                    f"🔍 GDB Session Started for {self.executable_path}\n"
                    f"Ready for interactive debugging. Use 'break <location>' to set breakpoints, then 'run' to start execution.\n\n"
                    f"{result}"
                )
                
            finally:
                os.chdir(old_cwd)
                
        except Exception as e:
            return Observation(self.name, f"❌ Failed to start GDB session: {str(e)}")

    def _execute_interactive_command(self, command: str) -> Observation:
        """Execute GDB command in persistent interactive session"""
        try:
            if not self.gdb_process or self.gdb_process.poll() is not None:
                # Start new persistent session if needed
                return self._start_persistent_session()
            
            # Handle specific commands that require special processing
            if command.startswith("break "):
                return self._set_breakpoint(command)
            elif command == "run":
                return self._run_program()
            elif command in ["step", "next", "continue", "finish"]:
                return self._execute_step_command(command)
            elif command.startswith("print ") or command == "info locals" or command == "info args":
                return self._examine_variables(command)
            elif command == "bt" or command == "backtrace":
                return self._show_backtrace()
            elif command == "list":
                return self._show_source_code()
            elif command.startswith("frame ") or command in ["up", "down"] or command == "info frame":
                return self._handle_frame_navigation(command)
            else:
                # Generic command execution
                return self._execute_generic_command(command)
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _start_persistent_session(self) -> Observation:
        """Start a persistent GDB session"""
        try:
            old_cwd = os.getcwd()
            os.chdir(self.working_dir)
            
            try:
                import subprocess
                import time
                
                # Start persistent GDB process in CLI mode for better interaction
                self.gdb_process = subprocess.Popen(
                    ["gdb", "-q", self.executable_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                # Send initial setup commands
                setup_commands = [
                    "set confirm off\n",
                    "set print pretty on\n",
                    "set pagination off\n"
                ]
                
                for cmd in setup_commands:
                    self.gdb_process.stdin.write(cmd)
                    self.gdb_process.stdin.flush()
                
                # Wait a moment for GDB to initialize
                time.sleep(0.2)
                
                # Read initial output
                initial_output = self._read_gdb_response()
                
                self.session_active = True
                self.program_running = False
                
                # Get program information for model analysis
                program_info = self._get_program_analysis()
                
                return Observation(self.name, 
                    f"🔍 INTERACTIVE GDB SESSION INITIALIZED\n\n"
                    f"TARGET PROGRAM: {self.executable_path}\n"
                    f"SESSION STATUS: Ready for debugging\n\n"
                    f"PROGRAM ANALYSIS:\n{program_info}\n\n"
                    f"DEBUGGING WORKFLOW:\n"
                    f"1. Set breakpoints: 'break main', 'break file.cpp:line'\n"
                    f"2. Start execution: 'run'\n"
                    f"3. Examine state: 'info locals', 'bt', 'list'\n"
                    f"4. Control flow: 'step', 'next', 'continue'\n"
                    f"5. Inspect data: 'print variable', 'x/format address'\n\n"
                    f"GDB INITIALIZATION: {initial_output}")
                    
            finally:
                os.chdir(old_cwd)
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: Failed to start persistent session: {str(e)}")
    
    def _set_breakpoint(self, command: str) -> Observation:
        """Set a breakpoint and provide detailed context"""
        try:
            location = command.split(" ", 1)[1] if " " in command else "main"
            
            # Send breakpoint command to persistent session
            gdb_command = f"break {location}\n"
            self.gdb_process.stdin.write(gdb_command)
            self.gdb_process.stdin.flush()
            
            # Read response
            response = self._read_gdb_response()
            
            if "Breakpoint" in response:
                self.breakpoints_set.append(location)
                
                # Get additional context about the breakpoint location
                context_info = self._get_breakpoint_context(location)
                
                return Observation(self.name, 
                    f"🔍 BREAKPOINT SET: {location}\n\n"
                    f"GDB Response: {response}\n\n"
                    f"BREAKPOINT CONTEXT:\n{context_info}\n\n"
                    f"DEBUGGING STATUS:\n"
                    f"- Total breakpoints: {len(self.breakpoints_set)}\n"
                    f"- Active breakpoints: {', '.join(self.breakpoints_set)}\n"
                    f"- Program state: {'Running' if self.program_running else 'Not started'}")
            else:
                return Observation(self.name, f"❌ Failed to set breakpoint: {response}")
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _run_program(self) -> Observation:
        """Run the program and provide comprehensive execution analysis"""
        try:
            # Send run command
            gdb_command = "run\n"
            self.gdb_process.stdin.write(gdb_command)
            self.gdb_process.stdin.flush()
            
            # Read response with longer timeout for program startup
            response = self._read_gdb_response(timeout=5.0)
            
            # Analyze the execution state
            execution_analysis = self._analyze_execution_state(response)
            
            # Check if we hit a breakpoint or stopped
            if "Breakpoint" in response and "hit" in response:
                self.program_running = True
                
                # Get detailed context at breakpoint
                breakpoint_context = self._get_current_execution_context()
                
                return Observation(self.name, 
                    f"🔍 PROGRAM EXECUTION - BREAKPOINT HIT\n\n"
                    f"GDB Response: {response}\n\n"
                    f"EXECUTION ANALYSIS:\n{execution_analysis}\n\n"
                    f"CURRENT CONTEXT:\n{breakpoint_context}\n\n"
                    f"NEXT STEPS:\n"
                    f"- Use 'info locals' to examine local variables\n"
                    f"- Use 'bt' to see the call stack\n"
                    f"- Use 'list' to see source code around current location\n"
                    f"- Use 'step' or 'next' to continue step-by-step\n"
                    f"- Use 'continue' to resume execution")
                    
            elif "exited" in response or "Program terminated" in response:
                self.program_running = False
                
                # Extract exit information
                exit_analysis = self._analyze_program_exit(response)
                
                return Observation(self.name, 
                    f"🔍 PROGRAM EXECUTION - COMPLETED\n\n"
                    f"GDB Response: {response}\n\n"
                    f"EXIT ANALYSIS:\n{exit_analysis}\n\n"
                    f"EXECUTION SUMMARY:\n{execution_analysis}")
                    
            elif "Starting program" in response:
                self.program_running = True
                return Observation(self.name, 
                    f"🔍 PROGRAM EXECUTION - STARTED\n\n"
                    f"GDB Response: {response}\n\n"
                    f"EXECUTION ANALYSIS:\n{execution_analysis}\n\n"
                    f"STATUS: Program is running continuously. Use Ctrl+C to interrupt if needed.")
            else:
                self.program_running = True
                return Observation(self.name, 
                    f"🔍 PROGRAM EXECUTION - STATUS UPDATE\n\n"
                    f"GDB Response: {response}\n\n"
                    f"EXECUTION ANALYSIS:\n{execution_analysis}")
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _execute_step_command(self, command: str) -> Observation:
        """Execute step/next/continue commands with detailed analysis"""
        try:
            if not self.program_running:
                return Observation(self.name, "❌ Program is not running. Use 'run' first.")
            
            # Send the command directly
            self.gdb_process.stdin.write(f"{command}\n")
            self.gdb_process.stdin.flush()
            
            response = self._read_gdb_response()
            
            # Check if program has exited during this step
            if any(phrase in response for phrase in ["exited normally", "exited with code", "Inferior", "No stack"]):
                self.program_running = False
            
            # Analyze the step execution
            step_analysis = self._analyze_step_execution(command, response)
            
            # Get current context after stepping (only if program still running)
            if self.program_running:
                current_context = self._get_current_execution_context()
            else:
                current_context = "Program has terminated - no active execution context"
            
            return Observation(self.name, 
                f"🔍 STEP EXECUTION - {command.upper()}\n\n"
                f"GDB Response: {response}\n\n"
                f"STEP ANALYSIS:\n{step_analysis}\n\n"
                f"CURRENT EXECUTION STATE:\n{current_context}\n\n"
                f"DEBUGGING SUGGESTIONS:\n"
                f"- Examine variables: 'info locals', 'info args'\n"
                f"- Check call stack: 'bt'\n"
                f"- View source: 'list'\n"
                f"- Continue stepping: 'step', 'next', 'finish'\n"
                f"- Resume execution: 'continue'")
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _examine_variables(self, command: str) -> Observation:
        """Examine variables and provide detailed analysis with frame-aware search"""
        try:
            # Check program state first
            if not self.session_active:
                return Observation(self.name, "❌ GDB session is not active. Start debugging first.")
            
            if not self.program_running:
                # Try to detect if program has finished vs never started
                self.gdb_process.stdin.write("info program\n")
                self.gdb_process.stdin.flush()
                program_info = self._read_gdb_response()
                
                if "No executable" in program_info or "not being run" in program_info:
                    return Observation(self.name, "❌ Program is not running. Use 'run' first to examine variables.")
                else:
                    return Observation(self.name, 
                        "❌ Program has finished execution. Variables are no longer in scope.\n"
                        "💡 To examine variables during execution:\n"
                        "   1. Set breakpoints before running: 'break function_name'\n"
                        "   2. Run the program: 'run'\n"
                        "   3. When stopped at breakpoint, examine variables\n"
                        "   4. Use 'step'/'next' to advance and continue examining")
            
            # Send the command directly first
            self.gdb_process.stdin.write(f"{command}\n")
            self.gdb_process.stdin.flush()
            
            response = self._read_gdb_response()
            frame_info = ""
            
            # If it's a print command and variable not found in current frame, search other frames
            if command.startswith("print ") and "No symbol" in response:
                var_name = command.split(" ", 1)[1].strip()
                frame_number, frame_result = self._find_variable_in_frames(var_name)
                
                if frame_number >= 0:
                    current_frame = self._get_current_frame_number()
                    frame_info = (
                        f"🎯 FRAME-AWARE SEARCH RESULT:\n"
                        f"Variable '{var_name}' found in frame {frame_number}\n"
                        f"(Current frame: {current_frame})\n\n"
                        f"Frame {frame_number} Value: {frame_result}\n\n"
                        f"💡 To access this variable directly:\n"
                        f"   - Use 'frame {frame_number}' to switch to that frame\n"
                        f"   - Or examine all frames with 'bt full'\n\n"
                    )
                    response = frame_result  # Update response with the found value
                else:
                    frame_info = f"🔍 CROSS-FRAME SEARCH: {frame_result}\n\n"
            
            # Analyze variable information
            variable_analysis = self._analyze_variable_data(command, response)
            
            # Get additional context if examining specific variable and it was found
            additional_context = ""
            if command.startswith("print ") and "No symbol" not in response:
                var_name = command.split(" ", 1)[1].strip()
                additional_context = self._get_variable_context(var_name)
            
            return Observation(self.name, 
                f"🔍 VARIABLE EXAMINATION - {command.upper()}\n\n"
                f"GDB Response:\n{response}\n\n"
                f"{frame_info}"
                f"VARIABLE ANALYSIS:\n{variable_analysis}\n\n"
                f"{additional_context}"
                f"MEMORY & TYPE INSIGHTS:\n"
                f"- Use 'print &variable' to see memory address\n"
                f"- Use 'print *pointer' to dereference pointers\n"
                f"- Use 'print sizeof(variable)' to see memory size\n"
                f"- Use 'ptype variable' to see detailed type information\n"
                f"- Use 'frame N' to switch to specific stack frame N")
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _show_backtrace(self) -> Observation:
        """Show backtrace with detailed analysis"""
        try:
            # Check both session and program state
            if not self.session_active:
                return Observation(self.name, "❌ GDB session is not active. Start debugging first.")
            
            # Check if program is running by attempting backtrace
            self.gdb_process.stdin.write("bt\n")
            self.gdb_process.stdin.flush()
            
            response = self._read_gdb_response()
            
            # Handle case where program has finished
            if "No stack" in response or "No frame" in response:
                return Observation(self.name, 
                    f"🔍 CALL STACK ANALYSIS\n\n"
                    f"BASIC BACKTRACE:\n{response}\n\n"
                    f"STACK ANALYSIS:\n"
                    f"📊 STACK DEPTH: Program has finished execution - no active stack\n\n"
                    f"💡 DEBUGGING GUIDANCE:\n"
                    f"- Program has completed execution\n"
                    f"- To examine call stack during execution, set breakpoints first\n"
                    f"- Use 'break main' or 'break function_name'\n"
                    f"- Then 'run' to start program and stop at breakpoints")
            
            # Get detailed backtrace information if program is running
            self.gdb_process.stdin.write("bt full\n") 
            self.gdb_process.stdin.flush()
            
            full_response = self._read_gdb_response()
            
            # Analyze the call stack
            stack_analysis = self._analyze_call_stack(response, full_response)
            
            return Observation(self.name, 
                f"🔍 CALL STACK ANALYSIS\n\n"
                f"BASIC BACKTRACE:\n{response}\n\n"
                f"DETAILED BACKTRACE:\n{full_response}\n\n"
                f"STACK ANALYSIS:\n{stack_analysis}\n\n"
                f"CALL STACK INSIGHTS:\n"
                f"- Frame 0 is the current function execution point\n"
                f"- Higher frame numbers show the calling sequence\n"
                f"- Use 'frame N' to switch to specific stack frame\n"
                f"- Use 'up' and 'down' to navigate stack frames\n"
                f"- Use 'info frame' for detailed frame information")
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _handle_frame_navigation(self, command: str) -> Observation:
        """Handle frame navigation commands with detailed frame information"""
        try:
            # Check program state first
            if not self.session_active:
                return Observation(self.name, "❌ GDB session is not active. Start debugging first.")
            
            if not self.program_running:
                return Observation(self.name, 
                    "❌ Program is not running. Frame navigation requires an active call stack.\n"
                    "💡 Set breakpoints and run the program to examine frames")
            
            # Store current frame before command
            original_frame = self._get_current_frame_number()
            
            # Execute the frame command
            self.gdb_process.stdin.write(f"{command}\n")
            self.gdb_process.stdin.flush()
            
            response = self._read_gdb_response()
            
            # Get detailed frame information after the command
            new_frame = self._get_current_frame_number()
            frame_count = self._get_frame_count()
            
            # Get detailed information about the current frame
            self.gdb_process.stdin.write("info frame\n")
            self.gdb_process.stdin.flush()
            frame_details = self._read_gdb_response()
            
            # Get local variables in this frame
            self.gdb_process.stdin.write("info locals\n")
            self.gdb_process.stdin.flush()
            locals_info = self._read_gdb_response()
            
            # Analyze frame navigation
            frame_analysis = self._analyze_frame_navigation(command, original_frame, new_frame, frame_count)
            
            return Observation(self.name, 
                f"🎯 FRAME NAVIGATION - {command.upper()}\n\n"
                f"Navigation Result:\n{response}\n\n"
                f"FRAME ANALYSIS:\n{frame_analysis}\n\n"
                f"CURRENT FRAME DETAILS:\n{frame_details}\n\n"
                f"LOCAL VARIABLES IN FRAME {new_frame}:\n{locals_info}\n\n"
                f"FRAME NAVIGATION COMMANDS:\n"
                f"- 'frame N' to switch to specific frame N\n"
                f"- 'up' to move to calling function (higher frame number)\n"
                f"- 'down' to move to called function (lower frame number)\n"
                f"- 'bt' to see all frames in the call stack\n"
                f"- Variables are frame-specific - switch frames to access different variables")
                
        except Exception as e:
            return Observation(self.name, f"❌ Frame navigation error: {str(e)}")

    def _analyze_frame_navigation(self, command: str, old_frame: int, new_frame: int, total_frames: int) -> str:
        """Analyze frame navigation results"""
        analysis = []
        
        analysis.append(f"📊 FRAME CONTEXT: {total_frames} total frames in call stack")
        analysis.append(f"🎯 FRAME CHANGE: From frame {old_frame} to frame {new_frame}")
        
        if old_frame == new_frame:
            analysis.append("✓ Already at the requested frame")
        elif command.startswith("frame "):
            target_frame = int(command.split()[1])
            if target_frame == new_frame:
                analysis.append(f"✓ Successfully switched to frame {target_frame}")
            else:
                analysis.append(f"⚠️ Requested frame {target_frame} but ended up at frame {new_frame}")
        elif command == "up":
            if new_frame > old_frame:
                analysis.append("✓ Moved up the call stack (to calling function)")
            else:
                analysis.append("⚠️ Could not move up - possibly at top of stack")
        elif command == "down":
            if new_frame < old_frame:
                analysis.append("✓ Moved down the call stack (to called function)")
            else:
                analysis.append("⚠️ Could not move down - possibly at bottom of stack")
        
        # Frame context information
        if new_frame == 0:
            analysis.append("📍 CURRENT POSITION: Bottom of call stack (innermost function)")
        elif new_frame == total_frames - 1:
            analysis.append("📍 CURRENT POSITION: Top of call stack (outermost function, usually main)")
        else:
            analysis.append(f"📍 CURRENT POSITION: Middle of call stack (frame {new_frame} of {total_frames})")
        
        return "\n".join(analysis)

    def _show_source_code(self) -> Observation:
        """Show current source code location"""
        try:
            self.gdb_process.stdin.write("list\n")
            self.gdb_process.stdin.flush()
            
            response = self._read_gdb_response()
            
            return Observation(self.name, 
                f"🔍 Current source location:\n{response}")
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _execute_generic_command(self, command: str) -> Observation:
        """Execute any other GDB command with intelligent analysis"""
        try:
            self.gdb_process.stdin.write(f"{command}\n")
            self.gdb_process.stdin.flush()
            
            response = self._read_gdb_response()
            
            # Provide intelligent analysis based on command type
            analysis = self._analyze_generic_command(command, response)
            
            return Observation(self.name, 
                f"🔍 GDB COMMAND EXECUTION: {command}\n\n"
                f"GDB Response:\n{response}\n\n"
                f"COMMAND ANALYSIS:\n{analysis}\n\n"
                f"DEBUGGING CONTEXT:\n"
                f"- Program state: {'Running' if self.program_running else 'Not started'}\n"
                f"- Active breakpoints: {len(self.breakpoints_set)}\n"
                f"- Available commands: info, print, list, step, next, continue, bt")
                
        except Exception as e:
            return Observation(self.name, f"❌ GDB Error: {str(e)}")
    
    def _analyze_generic_command(self, command: str, response: str) -> str:
        """Provide intelligent analysis for various GDB commands"""
        analysis = []
        
        # Command category analysis
        if command.startswith("info"):
            analysis.append("📋 INFORMATION COMMAND: Retrieving program state information")
            if "info registers" in command:
                analysis.append("🔍 CPU register state retrieved - useful for low-level debugging")
            elif "info breakpoints" in command:
                analysis.append(f"🎯 Breakpoint management - currently {len(self.breakpoints_set)} active")
            elif "info functions" in command:
                analysis.append("📚 Function listing retrieved - shows all available functions")
            elif "info variables" in command:
                analysis.append("📊 Global variable information retrieved")
                
        elif command.startswith("list"):
            analysis.append("📄 SOURCE CODE VIEW: Displaying source code context")
            if response and not "No source file" in response:
                line_count = len([line for line in response.split('\n') if line.strip() and not line.strip().startswith('(')])
                analysis.append(f"📝 Showing {line_count} lines of source code")
                
        elif command.startswith("x/"):
            analysis.append("🧠 MEMORY EXAMINATION: Direct memory inspection")
            analysis.append("💡 Memory content retrieved - check for corruption or unexpected values")
            
        elif command.startswith("disas"):
            analysis.append("⚙️ ASSEMBLY CODE: Disassembly view of machine instructions")
            analysis.append("🔍 Low-level analysis - useful for optimization and crash analysis")
            
        elif command.startswith("watch") or command.startswith("awatch") or command.startswith("rwatch"):
            analysis.append("👁️ WATCHPOINT SET: Monitoring memory location for changes")
            analysis.append("🎯 Program will break when watched memory is accessed/modified")
            
        elif command.startswith("delete") or command.startswith("clear"):
            analysis.append("🗑️ BREAKPOINT MANAGEMENT: Removing debug points")
            
        elif command.startswith("frame") or command == "up" or command == "down":
            analysis.append("🎬 STACK NAVIGATION: Moving through call stack frames")
            analysis.append("🔍 Context switched - local variables and scope may have changed")
            
        # Response analysis
        if "No symbol" in response:
            analysis.append("⚠️ Symbol not found - check spelling or compile with debug symbols (-g)")
        elif "No source file" in response:
            analysis.append("⚠️ Source file not available - ensure source files are accessible")
        elif response and len(response.strip()) < 10:
            analysis.append("ℹ️ Minimal output - command executed but limited information returned")
            
        return "\n".join(analysis) if analysis else "Command executed successfully"
    
    def _get_program_analysis(self) -> str:
        """Get comprehensive analysis of the target program for model intelligence"""
        try:
            analysis_info = []
            
            # Get program file information
            try:
                self.gdb_process.stdin.write("info files\n")
                self.gdb_process.stdin.flush()
                files_info = self._read_gdb_response(timeout=2.0)
                if files_info and "No executable file" not in files_info:
                    analysis_info.append(f"📁 EXECUTABLE INFO: {files_info[:300]}..." if len(files_info) > 300 else f"📁 EXECUTABLE INFO: {files_info}")
            except:
                pass
            
            # Get available functions
            try:
                self.gdb_process.stdin.write("info functions\n")
                self.gdb_process.stdin.flush()
                functions_info = self._read_gdb_response(timeout=2.0)
                if functions_info:
                    # Count functions
                    func_lines = [line for line in functions_info.split('\n') if line.strip() and not line.startswith('All defined functions')]
                    func_count = len(func_lines)
                    analysis_info.append(f"🔧 FUNCTIONS: Found {func_count} functions in program")
                    
                    # Show key functions if available
                    key_functions = [line for line in func_lines if any(keyword in line.lower() for keyword in ['main', 'init', 'setup', 'process', 'run'])]
                    if key_functions:
                        analysis_info.append(f"🎯 KEY FUNCTIONS: {'; '.join(key_functions[:5])}")
            except:
                pass
            
            # Get source files
            try:
                self.gdb_process.stdin.write("info sources\n")
                self.gdb_process.stdin.flush()
                sources_info = self._read_gdb_response(timeout=2.0)
                if sources_info:
                    cpp_files = [line for line in sources_info.split() if line.endswith(('.cpp', '.c', '.cc', '.cxx'))]
                    if cpp_files:
                        analysis_info.append(f"📄 SOURCE FILES: {', '.join(cpp_files[:5])}")
                        if len(cpp_files) > 5:
                            analysis_info.append(f"   ... and {len(cpp_files) - 5} more files")
            except:
                pass
            
            # Check if program has debug symbols
            try:
                self.gdb_process.stdin.write("info line main\n")
                self.gdb_process.stdin.flush()
                main_info = self._read_gdb_response(timeout=1.0)
                if "No line number information" in main_info:
                    analysis_info.append("⚠️ DEBUG SYMBOLS: Limited debug information - consider compiling with -g flag")
                else:
                    analysis_info.append("✓ DEBUG SYMBOLS: Full debug information available")
            except:
                pass
            
            return "\n".join(analysis_info) if analysis_info else "Basic program analysis complete"
            
        except Exception as e:
            return f"Program analysis error: {str(e)}"
    
    def _read_gdb_response(self, timeout: float = 3.0) -> str:
        """Read response from GDB process"""
        import select
        import time
        
        response = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.gdb_process.stdout.readable():
                # Check if data is available
                try:
                    ready, _, _ = select.select([self.gdb_process.stdout], [], [], 0.1)
                    if ready:
                        line = self.gdb_process.stdout.readline()
                        if line:
                            response += line
                            # Look for GDB prompt or completion indicators
                            if "(gdb)" in line and len(response) > 10:  # Make sure we have substantial output
                                break
                        else:
                            break
                    else:
                        time.sleep(0.05)
                except:
                    break
            else:
                break
        
        return response.strip() if response else "No response from GDB"
    
    # Enhanced Analysis Methods for Model Intelligence
    
    def _get_breakpoint_context(self, location: str) -> str:
        """Get detailed context about a breakpoint location"""
        try:
            context_commands = [
                f"info line {location}",  # Get file and line info
                f"list {location}",       # Show source around location
                f"info symbol {location}" # Get symbol information
            ]
            
            context_info = []
            for cmd in context_commands:
                try:
                    self.gdb_process.stdin.write(f"{cmd}\n")
                    self.gdb_process.stdin.flush()
                    response = self._read_gdb_response(timeout=1.0)
                    if response and "No response" not in response:
                        context_info.append(f"{cmd}: {response}")
                except:
                    continue
            
            return "\n".join(context_info) if context_info else "Context information not available"
            
        except Exception as e:
            return f"Error getting breakpoint context: {str(e)}"
    
    def _get_current_execution_context(self) -> str:
        """Get comprehensive context about current execution state"""
        try:
            context_info = []
            
            # First check if program is actually running by checking stack
            try:
                self.gdb_process.stdin.write("info frame\n")
                self.gdb_process.stdin.flush()
                frame_response = self._read_gdb_response(timeout=1.0)
                
                if "No frame selected" in frame_response or "No stack" in frame_response:
                    self.program_running = False
                    return ("Program has terminated - no active execution context\n"
                           "💡 To examine state during execution, set breakpoints before running")
            except:
                pass
            
            if not self.program_running:
                return "Program not running"
            
            # Current location
            try:
                self.gdb_process.stdin.write("where\n")
                self.gdb_process.stdin.flush()
                location = self._read_gdb_response(timeout=1.0)
                if location and "No stack" not in location:
                    context_info.append(f"CURRENT LOCATION: {location}")
                else:
                    # Program terminated during execution
                    self.program_running = False
                    return ("Program has terminated during execution\n"
                           "💡 Use breakpoints to examine state before termination")
            except:
                pass
            
            # Current function info
            try:
                self.gdb_process.stdin.write("info frame\n")
                self.gdb_process.stdin.flush()
                frame_info = self._read_gdb_response(timeout=1.0)
                if frame_info and "No frame selected" not in frame_info:
                    context_info.append(f"FRAME INFO: {frame_info}")
                else:
                    self.program_running = False
                    return ("Program has terminated during execution\n"
                           "💡 Use breakpoints to examine state before termination")
            except:
                pass
            
            # Local variables preview
            try:
                self.gdb_process.stdin.write("info locals\n")
                self.gdb_process.stdin.flush()
                locals_info = self._read_gdb_response(timeout=1.0)
                if locals_info and "No locals" not in locals_info and "No frame selected" not in locals_info:
                    # Truncate if too long
                    locals_preview = locals_info[:500] + "..." if len(locals_info) > 500 else locals_info
                    context_info.append(f"LOCAL VARIABLES: {locals_preview}")
                elif "No frame selected" in locals_info:
                    self.program_running = False
                    return ("Program has terminated during execution\n"
                           "💡 Use breakpoints to examine state before termination")
                else:
                    context_info.append("LOCAL VARIABLES: No local variables in current scope")
            except:
                pass
            
            return "\n".join(context_info) if context_info else "Execution context not available"
            
        except Exception as e:
            return f"Error getting execution context: {str(e)}"
    
    def _analyze_execution_state(self, response: str) -> str:
        """Analyze program execution state and provide insights"""
        analysis = []
        
        # Program state analysis
        if "Breakpoint" in response:
            analysis.append("✓ Program stopped at breakpoint (controlled execution)")
            if "hit" in response:
                analysis.append("✓ Successfully hit a user-defined breakpoint")
        elif "Starting program" in response:
            analysis.append("✓ Program started successfully")
        elif "exited" in response:
            analysis.append("✓ Program completed execution")
            if "code" in response:
                analysis.append(f"✓ Exit code detected in response")
        elif "SIGSEGV" in response or "Segmentation fault" in response:
            analysis.append("⚠️ CRITICAL: Segmentation fault detected")
            analysis.append("⚠️ Memory access violation - possible null pointer, buffer overflow, or invalid memory access")
        elif "SIGABRT" in response:
            analysis.append("⚠️ CRITICAL: Program aborted")
            analysis.append("⚠️ Possible assertion failure or explicit abort() call")
        
        # Execution flow analysis
        if "main" in response:
            analysis.append("✓ Execution context involves main function")
        
        return "\n".join(analysis) if analysis else "Normal execution state"
    
    def _analyze_program_exit(self, response: str) -> str:
        """Analyze program exit information"""
        analysis = []
        
        # Extract exit code if present
        if "exited normally" in response:
            analysis.append("✓ Program exited normally (exit code 0)")
        elif "exited with code" in response:
            # Try to extract exit code
            import re
            code_match = re.search(r'exited with code (\d+)', response)
            if code_match:
                exit_code = code_match.group(1)
                analysis.append(f"⚠️ Program exited with non-zero code: {exit_code}")
                if exit_code != "0":
                    analysis.append("⚠️ Non-zero exit indicates potential error or abnormal termination")
        
        # Memory leak hints
        if any(word in response.lower() for word in ["heap", "memory", "leak"]):
            analysis.append("💡 Consider using valgrind to check for memory leaks")
        
        return "\n".join(analysis) if analysis else "Program terminated - no specific exit analysis available"
    
    def _analyze_step_execution(self, command: str, response: str) -> str:
        """Analyze step execution and provide insights"""
        analysis = []
        
        # Command-specific analysis
        if command == "step":
            analysis.append("✓ STEP: Executed one line of source code (steps into function calls)")
        elif command == "next":
            analysis.append("✓ NEXT: Executed next line (steps over function calls)")
        elif command == "continue":
            analysis.append("✓ CONTINUE: Resumed execution until next breakpoint or program end")
        elif command == "finish":
            analysis.append("✓ FINISH: Executed until current function returns")
        
        # Response analysis
        if "Breakpoint" in response:
            analysis.append("→ Stopped at another breakpoint during execution")
        elif response and any(line.strip().startswith(('0x', '→', 'at ')) for line in response.split('\n')):
            analysis.append("→ Advanced to new location in code")
        elif "exited" in response:
            analysis.append("→ Program completed during step execution")
        
        return "\n".join(analysis) if analysis else "Step executed successfully"
    
    def _analyze_variable_data(self, command: str, response: str) -> str:
        """Analyze variable examination results"""
        analysis = []
        
        # Check for program termination or scope issues first
        if "No frame selected" in response or "No stack" in response:
            analysis.append("⚠️ No execution frame available")
            analysis.append("💡 Program has finished execution - variables are no longer in scope")
            analysis.append("🔧 To examine variables during execution:")
            analysis.append("   1. Set breakpoints: 'break main' or 'break function_name'")
            analysis.append("   2. Run program: 'run'")
            analysis.append("   3. When stopped at breakpoint, examine variables")
            return "\n".join(analysis)
        
        # Command-specific analysis
        if command == "info locals":
            if "No locals" in response or "No frame selected" in response:
                if "No frame selected" in response:
                    analysis.append("📝 No execution context available (program may have finished)")
                else:
                    analysis.append("📝 No local variables in current scope (possibly global scope or optimized code)")
            else:
                var_count = len([line for line in response.split('\n') if '=' in line])
                analysis.append(f"📝 Found {var_count} local variables in current scope")
                
        elif command == "info args":
            if "No arguments" in response or "No frame selected" in response:
                if "No frame selected" in response:
                    analysis.append("📝 No execution context available (program may have finished)")
                else:
                    analysis.append("📝 Current function takes no parameters")
            else:
                arg_count = len([line for line in response.split('\n') if '=' in line])
                analysis.append(f"📝 Current function has {arg_count} parameters")
                
        elif command.startswith("print "):
            var_name = command.split(" ", 1)[1] if " " in command else ""
            if "No symbol" in response:
                analysis.append(f"⚠️ Variable '{var_name}' not found in current scope")
                analysis.append("💡 Possible reasons:")
                analysis.append("   • Variable is out of scope (program finished or wrong function)")
                analysis.append("   • Variable name misspelled")
                analysis.append("   • Variable optimized out by compiler")
                analysis.append("   • Need to be at a breakpoint within variable's scope")
            elif "$" in response and "=" in response:
                analysis.append(f"✓ Successfully retrieved value for '{var_name}'")
                # Try to detect potential issues
                if "0x0" in response or "(nil)" in response:
                    analysis.append("⚠️ WARNING: Null pointer detected - potential null pointer dereference risk")
                elif "0x" in response and len(response.split("0x")) > 2:
                    analysis.append("💡 Pointer variable detected - consider dereferencing to see actual value")
        
        # General data analysis
        if "optimized out" in response:
            analysis.append("⚠️ Some variables optimized out by compiler - compile with -O0 for full debug info")
        
        return "\n".join(analysis) if analysis else "Variable data retrieved successfully"
    
    def _get_current_frame_number(self) -> int:
        """Get the current frame number from GDB"""
        try:
            self.gdb_process.stdin.write("info frame\n")
            self.gdb_process.stdin.flush()
            response = self._read_gdb_response(timeout=1.0)
            
            if "Stack frame" in response:
                # Extract frame number from "Stack frame at 0x... in ..."
                for line in response.split('\n'):
                    if "Stack frame" in line and "in" in line:
                        # Try to extract frame number if present
                        import re
                        frame_match = re.search(r'frame (\d+)', line)
                        if frame_match:
                            return int(frame_match.group(1))
                        # If no explicit frame number, we're likely at frame 0
                        return 0
            
            return 0  # Default to frame 0
        except Exception:
            return 0

    def _get_frame_count(self) -> int:
        """Get the total number of frames in the call stack"""
        try:
            self.gdb_process.stdin.write("bt\n")
            self.gdb_process.stdin.flush()
            response = self._read_gdb_response(timeout=1.0)
            
            # Count frames by counting lines that start with #
            frame_count = len([line for line in response.split('\n') 
                             if line.strip().startswith('#')])
            return max(frame_count, 1)  # At least 1 frame
        except Exception:
            return 1

    def _switch_to_frame(self, frame_number: int) -> bool:
        """Switch to a specific frame and return True if successful"""
        try:
            self.gdb_process.stdin.write(f"frame {frame_number}\n")
            self.gdb_process.stdin.flush()
            response = self._read_gdb_response(timeout=1.0)
            
            # Check if frame switch was successful
            return "No stack" not in response and "Invalid frame" not in response
        except Exception:
            return False

    def _find_variable_in_frames(self, var_name: str) -> tuple[int, str]:
        """
        Search for a variable across all frames.
        Returns (frame_number, value) if found, (-1, error_message) if not found.
        """
        try:
            original_frame = self._get_current_frame_number()
            frame_count = self._get_frame_count()
            
            # Search through all frames
            for frame_num in range(frame_count):
                if self._switch_to_frame(frame_num):
                    # Try to print the variable in this frame
                    self.gdb_process.stdin.write(f"print {var_name}\n")
                    self.gdb_process.stdin.flush()
                    response = self._read_gdb_response(timeout=1.0)
                    
                    if "No symbol" not in response and "$" in response and "=" in response:
                        # Found the variable! Return to original frame and return result
                        self._switch_to_frame(original_frame)
                        return frame_num, response.strip()
            
            # Restore original frame
            self._switch_to_frame(original_frame)
            return -1, f"Variable '{var_name}' not found in any frame"
            
        except Exception as e:
            return -1, f"Error searching for variable: {str(e)}"

    def _get_variable_context(self, var_name: str) -> str:
        """Get additional context about a specific variable"""
        try:
            context_info = []
            
            # Get type information
            self.gdb_process.stdin.write(f"ptype {var_name}\n")
            self.gdb_process.stdin.flush()
            type_info = self._read_gdb_response(timeout=1.0)
            if type_info and "No symbol" not in type_info:
                context_info.append(f"TYPE INFORMATION: {type_info}")
            
            # Get memory address
            self.gdb_process.stdin.write(f"print &{var_name}\n")
            self.gdb_process.stdin.flush()
            addr_info = self._read_gdb_response(timeout=1.0)
            if addr_info and "No symbol" not in addr_info:
                context_info.append(f"MEMORY ADDRESS: {addr_info}")
            
            return "\n".join(context_info) + "\n" if context_info else ""
            
        except Exception as e:
            return f"Variable context error: {str(e)}\n"
    
    def _analyze_call_stack(self, basic_bt: str, full_bt: str) -> str:
        """Analyze call stack information"""
        analysis = []
        
        # Count stack frames
        frame_count = len([line for line in basic_bt.split('\n') if line.strip().startswith('#')])
        analysis.append(f"📊 STACK DEPTH: {frame_count} frames")
        
        # Look for common patterns
        if "main" in basic_bt:
            main_frame = None
            for line in basic_bt.split('\n'):
                if "main" in line and line.strip().startswith('#'):
                    main_frame = line.split()[0]
                    break
            if main_frame:
                analysis.append(f"🎯 Main function at frame {main_frame}")
        
        # Look for potential issues
        if frame_count > 20:
            analysis.append("⚠️ Deep call stack detected - possible infinite recursion")
        
        if any(word in basic_bt.lower() for word in ["sigsegv", "segfault", "abort"]):
            analysis.append("🚨 CRASH DETECTED: Stack trace shows program crash")
        
        # Function pattern analysis
        functions = []
        for line in basic_bt.split('\n'):
            if 'in ' in line and '(' in line:
                # Extract function name
                try:
                    func_part = line.split(' in ')[1].split('(')[0]
                    functions.append(func_part)
                except:
                    pass
        
        if len(functions) > 1:
            analysis.append(f"📋 CALL SEQUENCE: {' → '.join(functions[:5])}")
            if len(functions) > 5:
                analysis.append(f"   ... and {len(functions) - 5} more functions")
        
        # Memory and variable information from full backtrace
        if "No locals" not in full_bt and len(full_bt) > len(basic_bt):
            analysis.append("💡 Local variables available in stack frames (see detailed backtrace above)")
        
        return "\n".join(analysis) if analysis else "Call stack analysis complete"

    def _run_gdb_commands(self, commands) -> str:
        """Run a list of GDB commands and return the output"""
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gdb', delete=False) as f:
            for cmd in commands:
                f.write(f"{cmd}\n")
            script_file = f.name
        
        try:
            # Clear problematic environment variables
            env = dict(os.environ)
            env.pop('PYTHONPATH', None)
            
            # Run GDB with the command script
            cmd_args = ["gdb", "-batch", "-x", script_file, self.executable_path]
            
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            output = result.stdout + result.stderr
            return output.strip()
            
        finally:
            # Clean up temporary script file
            try:
                os.unlink(script_file)
            except:
                pass

    def _ensure_executable_built(self, environment):
        """Ensure the executable is built before running GDB"""
        try:
            # Get build command from environment (default to make)
            build_cmd = getattr(environment, 'build_command', 'make')
            
            # First, try to build
            result = subprocess.run(
                build_cmd.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Build failed, try basic g++ compilation
                executable_name = environment.entrypoint.lstrip("./")
                cpp_file = f"{executable_name}.cpp"
                
                if os.path.exists(cpp_file):
                    build_result = subprocess.run([
                        "g++", "-g", "-O0", "-std=c++11", "-o", executable_name, cpp_file
                    ], capture_output=True, text=True, timeout=30)
                    
                    if build_result.returncode != 0:
                        raise Exception(f"Compilation failed: {build_result.stderr}")
                else:
                    raise Exception(f"Could not find source file {cpp_file}")
                    
        except Exception as e:
            raise Exception(f"Failed to build executable: {str(e)}")