import copy
import re

from debug_gym.gym.entities import Observation
from debug_gym.gym.terminal import ShellSession
from debug_gym.gym.tools.tool import EnvironmentTool
from debug_gym.gym.tools.toolbox import Toolbox


@Toolbox.register()
class GDBTool(EnvironmentTool):
    name: str = "gdb"
    examples = [
        """gdb(command="run") to start the program from the beginning.""",
        """gdb(command="break main.cpp:42") to set a breakpoint at line 42 in main.cpp.""",
        """gdb(command="break function_name") to set a breakpoint at a function.""",
        """gdb(command="break if x==42") to set a conditional breakpoint when x==42.""",
        """gdb(command="tbreak main.cpp:50") to set a temporary breakpoint at line 50.""",
        """gdb(command="watch x") to break when variable x changes.""",
        """gdb(command="rwatch x") to break when variable x is read.""",
        """gdb(command="awatch x") to break when variable x is accessed (read or write).""",
        """gdb(command="commands 1") to specify commands to run when breakpoint 1 is hit.""",
        """gdb(command="delete") to delete all breakpoints.""",
        """gdb(command="delete 1") to delete breakpoint number 1.""",
        """gdb(command="disable breakpoint 1") to disable breakpoint number 1.""",
        """gdb(command="enable breakpoint 1") to enable breakpoint number 1.""",
        """gdb(command="info breakpoints") to list all breakpoints.""",
        """gdb(command="clear main.cpp:26") to clear the breakpoint at line 26 in main.cpp.""",
        """gdb(command="continue") to continue execution until the next breakpoint.""",
        """gdb(command="next") to execute the next line of code (step over).""",
        """gdb(command="step") to step into the next function call.""",
        """gdb(command="finish") to run until the current function returns.""",
        """gdb(command="until 50") to continue until line 50 is reached.""",
        """gdb(command="jump 100") to jump to line 100 in the current file.""",
        """gdb(command="signal SIGTERM") to send a signal to the program.""",
        """gdb(command="catch throw") to break when a C++ exception is thrown.""",
        """gdb(command="catch catch") to break when a C++ exception is caught.""",
        """gdb(command="backtrace") to display the call stack.""",
        """gdb(command="bt full") to display the full call stack with local variables.""",
        """gdb(command="info frame") to list the current frame.""",
        """gdb(command="frame 2") to switch to frame 2.""",
        """gdb(command="up") to move up one frame in the call stack.""",
        """gdb(command="down") to move down one frame in the call stack.""",
        """gdb(command="info threads") to list all threads.""",
        """gdb(command="thread 1") to switch to thread 1.""",
        """gdb(command="thread apply all bt") to show backtrace for all threads.""",
        """gdb(command="info registers") to show CPU register values.""",
        """gdb(command="info sharedlibrary") to list loaded shared libraries.""",
        """gdb(command="info signals") to list all signals and their handlers.""",
        """gdb(command="info proc mappings") to show memory mappings of the process.""",
        """gdb(command="print x") to print the value of variable x.""",
        """gdb(command="display x") to automatically print the value of x after each stop.""",
        """gdb(command="undisplay") to remove all automatic display expressions.""",
        """gdb(command="info locals") to list all local variables.""",
        """gdb(command="info args") to list all function arguments.""",
        """gdb(command="set var x=42") to set the value of variable x to 42.""",
        """gdb(command="ptype x") to print the type of variable x.""",
        """gdb(command="whatis x") to show the type of x.""",
        """gdb(command="x/16x &x") to examine 16 hexadecimal values at the address of x.""",
        """gdb(command="x/s str") to examine a string at the address of str.""",
        """gdb(command="x/4i $pc") to examine 4 instructions at the program counter.""",
        """gdb(command="info variables") to list all global and static variables.""",
        """gdb(command="list") to list the source code around the current line.""",
        """gdb(command="list main") to list the source code around the function main.""",
        """gdb(command="list 100,120") to list lines 100 to 120.""",
        """gdb(command="info line 42") to show information about line 42.""",
        """gdb(command="directory ../src") to add ../src to the source search path.""",
        """gdb(command="quit") to exit the GDB debugger.""",
        """gdb(command="help") to list all available GDB commands.""",
        """gdb(command="help break") to get help for the break command.""",
        """gdb(command="set logging on") to log output to a file.""",
        """gdb(command="set environment VAR=value") to set an environment variable.""",
        """gdb(command="shell ls -l") to run a shell command from GDB.""",
        """gdb(command="source script.gdb") to execute commands from a script file.""",
        """gdb(command="set print pretty on") to pretty-print structures.""",
        """gdb(command="set print elements 0") to print all elements of arrays.""",
        """gdb(command="set print array on") to print arrays.""",
    ]
    description = (
        "An interface to the gdb debugger. Send a command to the gdb terminal. The command should be a valid gdb command."
        + "\nWhen using the breakpoint command (e.g., 'b', 'break', 'cl', 'clear'), make sure you specify the file path and line number in the format `file_path:line_number`."
        + "\nExamples (for demonstration purposes only, you need to adjust the tool calling format according to your specific syntax):"
        + "\n".join(examples)
    )
    arguments = {
        "command": {
            "type": ["string"],
            "description": "The command to be sent to the gdb terminal. The command should be a valid gdb command. See https://www.gnu.org/software/gdb/documentation/ for more information.",
        },
    }

    def __init__(self):
        super().__init__()
        self.current_frame_file = None
        self._session: ShellSession = None

    def __deepcopy__(self, memo):
        """Create a deep copy of the GDBTool instance with _session set to None."""
        result = type(self).__new__(self.__class__)
        memo[id(self)] = result
        # Copy all attributes except _session
        for k, v in self.__dict__.items():
            # drop the session which is not serializable
            if k == "_session":
                setattr(result, k, None)
            # drop the current_frame_file which is None at the beginning
            # and will be set when the PDB session starts
            elif k == "current_frame_file":
                setattr(result, k, None)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result

    @property
    def gdb_is_running(self):
        return self._session is not None and self._session.is_running

    
    def get_all_thread_ids(self, timeout):
        """Get all thread IDs from GDB."""
        output = self._session.run("info threads", read_until="(gdb)", timeout=timeout)
        # Example line: '* 1    Thread 0x7ffff7e9c740 (LWP 56932) "test" ...'
        thread_id_pattern = re.compile(r'^\s*[\*\s]?(\d+)\s+Thread')
        thread_ids = []
        for line in output.splitlines():
            match = thread_id_pattern.match(line)
            if match:
                thread_ids.append(match.group(1))
        return thread_ids

    def get_all_frame_ids(self, thread_id, timeout):
        """Get all frame numbers for a given thread from GDB."""
        self._session.run(f"thread {thread_id}", read_until="(gdb)", timeout=timeout)
        output = self._session.run("backtrace", read_until="(gdb)", timeout=timeout)
        # Example line: '#0  main () at main.cpp:5'
        frame_id_pattern = re.compile(r'^#(\d+)\s')
        frame_ids = []
        for line in output.splitlines():
            match = frame_id_pattern.match(line)
            if match:
                frame_ids.append(match.group(1))
        return frame_ids

    def get_all_locals_all_threads(self, timeout):
        """Collect all local variables from all frames of all threads."""
        thread_ids = self.get_all_thread_ids(timeout)
        all_locals = {}
        for thread_id in thread_ids:
            all_locals[thread_id] = {}
            frame_ids = self.get_all_frame_ids(thread_id, timeout)
            for frame_id in frame_ids:
                self._session.run(f"thread {thread_id}", read_until="(gdb)", timeout=timeout)
                self._session.run(f"frame {frame_id}", read_until="(gdb)", timeout=timeout)
                locals_output = self._session.run("info locals", read_until="(gdb)", timeout=timeout)
                all_locals[thread_id][frame_id] = locals_output
        return all_locals

    def interact_with_gdb(self, command: str, timeout: int, self_call: bool = False):
        try:
            output = self._session.run(command, read_until="(gdb)", timeout=timeout)
        except TimeoutError as e:
            # More intelligent timeout handling - don't close session unnecessarily
            if command == "run":
                # For 'run' command timeout, try to get backtrace instead of closing
                if not self_call:
                    try:
                        # Send Ctrl+C to interrupt the running program
                        self._session.send_signal(2)  # SIGINT
                        # Wait a moment for the program to stop
                        self._session.run("", read_until="(gdb)", timeout=5)
                        # Get backtrace to show where we stopped
                        command = "thread apply all bt"
                        output = self.interact_with_gdb(command, timeout, True)
                    except:
                        output = f"Program execution timed out after {timeout}s. Use 'continue' to resume or set breakpoints to control execution."
                else:
                    output = f"The command `{command}` had timed out. {e!r}."
            elif command in ["continue", "cont", "c"]:
                # For continue timeout, the program is still running - this is often expected
                output = f"Program is still running (timeout after {timeout}s). Use Ctrl+C to interrupt or wait longer."
            elif command in ["step", "next", "s", "n"]:
                # For stepping commands that timeout, try to get current status
                try:
                    self._session.send_signal(2)  # SIGINT to stop
                    self._session.run("", read_until="(gdb)", timeout=5)
                    output = f"Stepping timed out. Program interrupted."
                except:
                    output = f"Stepping command timed out after {timeout}s."
            else:
                # For other commands, timeout is likely an error but don't close session
                output = f"The command `{command}` timed out after {timeout}s. Session remains active."

        if output.startswith(command):
            output = output[len(command):].lstrip("\n\r ")

        return output

    def close_gdb(self):
        if self._session and self._session.is_running:
            self._session.close()
        self._session = None
        self.current_frame_file = None

    def interrupt_program(self):
        """Send SIGINT to interrupt a running program in GDB."""
        if self._session and self._session.is_running:
            try:
                self._session.send_signal(2)  # SIGINT
                return True
            except:
                return False
        return False

    def start_gdb(self, environment) -> str:
        self._session = environment.terminal.new_shell_session()
        # init gdb and wait for the prompt
        initial_output = self._session.start(
            environment.debug_entrypoint, read_until="(gdb)"
        )

        # Don't explicitly load executable since it's already in the command line
        # Just ensure the session is properly started

        # Disable paging in GDB
        self._session.run("set pagination off", read_until="(gdb)", timeout=environment.run_timeout)
        # Enable debuginfod in GDB
        self._session.run("set debuginfod enabled off", read_until="(gdb)", timeout=environment.run_timeout)
        # Automatically confirm symbol loading questions
        self._session.run("set confirm off", read_until="(gdb)", timeout=environment.run_timeout)

        if "The program finished and will be restarted" in initial_output:
            self.close_gdb()
        else:
            if environment.persistent_breakpoints:
                # restore persistent breakpoints
                for _, _command in environment.current_breakpoints_state.items():
                    self.interact_with_gdb(_command, environment.run_timeout)
                if len(environment.current_breakpoints_state) > 0:
                    initial_output = "\n".join(
                        [initial_output, "Breakpoints have been restored."]
                    )
            self.set_current_frame_file(environment)
        return initial_output

    def on_env_reset(self, environment, **kwargs) -> Observation:
        super().on_env_reset(environment, **kwargs)
        obs = self.start_gdb(environment)
        return Observation(self.name, obs)

    def on_rewrite_success(
        self, environment, file, head, tail, length, **kwargs
    ) -> Observation:
        self.breakpoint_modify(environment, file, head, tail, length)
        obs = self.restart_gdb(environment)
        obs = "\nDebugging terminal started:\n" f"{obs}\n"
        return Observation(self.name, obs)

    def restart_gdb(self, environment) -> str:
        """Restart the gdb session and restore the breakpoints."""
        self.close_gdb()
        return self.start_gdb(environment)

    def use(self, environment, command: str) -> Observation:
        if command == "":
            return Observation(
                self.name, "Failure calling gdb:\nEmpty commands are not allowed."
            )

        _warning = ""
        # if print, it's OK to have ";" or "\n" in the command
        # otherwise, only the first command will be executed
        if not (command.split()[0] in ["p", "pp"] or command.startswith("print(")):
            splits = re.split("\n|;", command)
            if len(splits) > 1:
                command = splits[0].strip()
                _warning += "Multiple commands are not supported. Only the first command will be executed."

        success, output = True, ""
        
        # Start GDB session if not running
        if not self.gdb_is_running:
            output += self.start_gdb(environment)

        if not self.gdb_is_running:
            # gdb failed to start
            return Observation(self.name, f"Failure calling gdb:\n{output}")

        # Handle special commands that don't need to interact with GDB directly
        if command in ["info breakpoints"]:
            # list all breakpoints
            success, output = (
                True,
                f"Breakpoints:\n{environment.current_breakpoints()}\n",
            )
        elif command in ["delete"]:
            # clear all breakpoints
            environment.current_breakpoints_state = {}
            self.restart_gdb(environment)
            success, output = True, "All breakpoints have been cleared."
        else:  # other gdb commands, send directly
            try:
                gdb_out = self.interact_with_gdb(command, environment.run_timeout)
                # remove the working dir from the output
                gdb_out = gdb_out.replace(f"{environment.working_dir}/", "")
                
                # Handle common GDB responses that indicate issues
                if gdb_out in (
                    "End of file",
                    "Blank or comment", 
                    "*** Blank or comment",
                ):
                    success = False
                    output = f"Invalid line number: {gdb_out}."
                elif "No such file or directory" in gdb_out:
                    success = False
                    output = f"File not found: {gdb_out}"
                elif "The program is not being run" in gdb_out and command in ["continue", "cont", "c", "step", "next", "s", "n"]:
                    # This is expected when trying to continue/step without a running program
                    output += f"Gdb command output:\n{gdb_out}"
                elif "Breakpoint" in gdb_out or "Hardware assisted breakpoint" in gdb_out:
                    # Breakpoint was hit - this is good
                    output += f"Gdb command output:\n{gdb_out}"
                else:
                    output += f"Gdb command output:\n{gdb_out}"
                    
                # Update breakpoints state after successful command
                if success and command.split()[0] in ["break", "b", "tbreak", "rbreak", "delete", "clear", "disable", "enable"]:
                    self.update_breakpoints(environment)
                    
            except Exception as e:
                success = False
                output = f"Error executing GDB command: {str(e)}"

        if not success:
            if _warning:
                obs = f"Invalid gdb command: {command}\n{_warning}\n{output.strip()}"
            else:
                obs = f"Invalid gdb command: {command}\n{output.strip()}"
            return Observation(self.name, obs)

        # Handle program exit messages more gracefully
        if "exited normally" in output or "exited with code" in output:
            output += "\nProgram has exited. Use 'run' to start again or set breakpoints before running."
        elif "The program finished and will be restarted" in output:
            output += "\nProgram finished. GDB is ready for the next run command."

        if _warning:
            obs = f"{_warning}\n{output.strip()}\n"
        else:
            obs = f"{output.strip()}\n"

        # Add the current frame information to the observation only if program is stopped at a breakpoint
        if self.gdb_is_running:
            # Try to get current frame info
            try:
                current_frame = self.set_current_frame_file(environment)
                
                # Only show context if we're actually stopped in the program (not just at gdb prompt)
                if current_frame and not any(x in output.lower() for x in ["exited", "not being run", "no stack"]):
                    # Get context around current line
                    list_output = ""
                    if environment.auto_list and command.split()[0] not in ["l", "list"]:
                        try:
                            list_output = self.interact_with_gdb("l .", environment.run_timeout)
                        except:
                            pass  # Skip if list fails
                    
                    if current_frame:
                        obs += f"\nCurrent frame:\n{current_frame}\n"
                    if list_output and "No such file or directory" not in list_output:
                        obs += f"\nContext around the current frame:\n{list_output}\n"
            except:
                pass  # Skip frame info if there's any error

        return Observation(self.name, obs)

    def breakpoint_modify(
        self, environment, rewrite_file, rewrite_head, rewrite_tail, new_code_length
    ):
        # handle breakpoints line number changes caused by rewriting
        # this is a wrapper that manages the self.breakpoints_state, which does not reset at each pseudo terminal start
        # self.breakpoints_state is a dict, the keys are "|||".join([file_path, str(line_number)]) and values are breakpoint_command
        if len(environment.current_breakpoints_state) == 0:
            return
        current_breakpoints_state_copy = copy.deepcopy(
            environment.current_breakpoints_state
        )
        rewrite_file = environment.resolve_path(rewrite_file)
        for _key in environment.current_breakpoints_state.keys():
            _file_path, _line_number = _key.split("|||")
            _file_path = environment.resolve_path(_file_path)
            if _file_path != rewrite_file:
                # the breakpoints are not in the current file, no need to modify
                continue
            _line_number = int(_line_number)
            if rewrite_head is None:
                # no line number is provided, rewrite the whole code
                # we remove all breakpoints in the current file
                del current_breakpoints_state_copy[_key]
            else:
                # if a breakpoint was set in between the rewritten code, we need to remove it
                if rewrite_head <= _line_number <= rewrite_tail:
                    del current_breakpoints_state_copy[_key]
                # if a breakpoint was set after the rewritten code, we need to move it
                elif _line_number > rewrite_tail:
                    new_line_number = (
                        _line_number
                        + new_code_length
                        - (rewrite_tail - rewrite_head + 1)
                    )
                    new_key = "|||".join([str(_file_path), str(new_line_number)])
                    _new_value = environment.current_breakpoints_state[_key].split(":")
                    _new_value[1] = " ".join(
                        [str(new_line_number), " ".join(_new_value[1].split()[1:])]
                    )
                    current_breakpoints_state_copy[new_key] = ":".join(
                        _new_value
                    ).strip()
                    del current_breakpoints_state_copy[_key]
                # if a breakpoint was set before the rewritten code, we don't need to do anything
                else:
                    pass
        environment.current_breakpoints_state = current_breakpoints_state_copy

    def update_breakpoints(self, environment):
        """
        Updates the environment's current_breakpoints_state by parsing the output of GDB's 'info breakpoints' command.
        The new_breakpoints dictionary keys are in the format "file_path|||line_number",
        and the values are the corresponding GDB breakpoint commands.
        """
        command = "info breakpoints"
        output = self.interact_with_gdb(command, environment.run_timeout)
        # GDB 'info breakpoints' output example:
        # Num Type           Disp Enb Address            What
        # 1   breakpoint     keep y   0x00005555555551d6 in main at main.cpp:5
        # 2   breakpoint     keep y   0x00005555555551f0 in foo at foo.cpp:10
        new_breakpoints = {}
        breakpoint_pattern = re.compile(r"^\s*\d+\s+breakpoint\s+keep\s+y\s+\S+\s+in\s+.+\s+at\s+(.+):(\d+)")
        for line in output.splitlines():
            match = breakpoint_pattern.match(line)
            if match:
                file_path, line_number = match.groups()
                key = "|||".join([file_path, line_number])
                new_breakpoints[key] = f"break {file_path}:{line_number}"
        environment.current_breakpoints_state = new_breakpoints

    def set_current_frame_file(self, environment) -> str | None:
        """
        Use 'frame' or 'where' to obtain the current frame (file and line number) in GDB.
        """
        try:
            command = "frame"
            output = self.interact_with_gdb(command, environment.run_timeout)
            # GDB 'frame' output example:
            # #0  in main () at main.cpp:5
            # #0  main () at main.cpp:5  
            file_path = None
            line_number = None
            frame_pattern = re.compile(r"at\s+(.+):(\d+)")
            for line in output.splitlines():
                match = frame_pattern.search(line)
                if match:
                    file_path, line_number = match.groups()
                    break
            
            if file_path and self.current_frame_file != file_path:
                self.current_frame_file = file_path
            
            return file_path
        except:
            # If frame command fails, don't crash - just return None
            return None
