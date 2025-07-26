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
        """gdb(command="break example/src/main.cpp:42") to set a breakpoint at line 42 in example/src/main.cpp.""",
        """gdb(command="continue") to continue execution until the next breakpoint.""",
        """gdb(command="print x") to print the value of variable x.""",
        """gdb(command="list") to list the source code around the current line.""",
        """gdb(command="info breakpoints") to list all breakpoints.""",
        """gdb(command="delete 1") to delete the breakpoint with id 1.""",
        """gdb(command="clear example/src/main.cpp:26") to clear the breakpoint at line 26 in example/src/main.cpp.""",
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

    def interact_with_gdb(self, command: str, timeout: int):
        try:
            output = self._session.run(command, read_until="(gdb)", timeout=timeout)
        except TimeoutError as e:
            output = f"The command `{command}` has timed out. {e!r}"

        # Remove the (gdb) prompt and any echoed command
        output = output.replace("(gdb)", "").strip()
        # Optionally, remove the echoed command from the output
        if output.startswith(command):
            output = output[len(command):].lstrip("\n\r ")

        return output

    def close_gdb(self):
        self._session.close()
        self.current_frame_file = None

    def start_gdb(self, environment) -> str:
        self._session = environment.terminal.new_shell_session()
        # init gdb and wait for the prompt
        initial_output = self._session.start(
            environment.debug_entrypoint, read_until="(gdb)"
        )

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
        if not self.gdb_is_running:
            output += self.start_gdb(environment)

        if not self.gdb_is_running:
            # gdb failed to start
            return Observation(self.name, f"Failure calling gdb:\n{output}")

        if command in ["b", "break"]:
            # list all breakpoints
            success, output = (
                True,
                f"Breakpoints:\n{environment.current_breakpoints()}\n",
            )
        elif command in ["cl", "clear"]:
            # clear all breakpoints
            environment.current_breakpoints_state = {}
            self.restart_gdb(environment)
            success, output = True, "All breakpoints have been cleared."
        else:  # other gdb commands, send directly
            try:
                gdb_out = self.interact_with_gdb(command, environment.run_timeout)
                # remove the working dir from the output
                gdb_out = gdb_out.replace(f"{environment.working_dir}/", "")
                if gdb_out in (
                    "End of file",
                    "Blank or comment",
                    "*** Blank or comment",
                ):
                    # if out of bounds, gdb may return messages like 'No such file or directory.' or 'No line number'
                    success = False
                    output = f"Invalid line number: {gdb_out}."
                else:
                    output += f"Gdb command output:\n{gdb_out}"
                self.update_breakpoints(environment)
            except Exception:
                success = False

        if not success:
            if _warning:  # prevend additional \n
                obs = f"Invalid gdb command: {command}\n{_warning}\n{output.strip()}"
            else:
                obs = f"Invalid gdb command: {command}\n{output.strip()}"
            return Observation(self.name, obs)

        # sometimes it will run into the end of the program
        # we need to put the stdout before:
        # The program exited via sys.exit().
        # into self.last_eval_output, and remove them from the output
        if "The program exited via sys.exit()." in output:
            # end index is the last occurrence of the program exited (from the \n after)
            start_index = output.rfind("The program exited via sys.exit().")
            end_index = output.find("\n", start_index) + 1
            output = (
                output[:start_index]
                + "\nReached the end of the program. Restarting the debugging session.\n"
                + output[end_index:]
            )
        if _warning:
            obs = f"{_warning}\n{output.strip()}\n"
        else:
            obs = f"{output.strip()}\n"

        # Add the current frame information to the observation.
        if self.gdb_is_running:
            # read the current frame info to determine the current file
            current_frame = self.set_current_frame_file(environment)

            # free 'list' to provide context around the current frame
            list_output = ""
            if environment.auto_list and command.split()[0] not in ["l", "list"]:
                list_output = self.interact_with_gdb("l .", environment.run_timeout)

            if current_frame:
                obs += f"\nCurrent frame:\n{current_frame}\n"
            if list_output:
                obs += f"\nContext around the current frame:\n{list_output}\n"

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
        """Updates the environment's current_breakpoints_state by
        parsing the output of the PDB 'b' (breakpoints) command.

        The new_breakpoints dictionary keys are in the format "file_path|||line_number",
        and the values are the corresponding PDB breakpoint commands.

        environment.current_breakpoints_state = {
            "path/to/file.py|||line_number": "b path/to/file.py:line_number",
            ...
        }"""

        command = "b"  # list all breakpoints
        output = self.interact_with_gdb(command, environment.run_timeout)
        # parse the output to update the current_breakpoints_state
        # example output:
        # Num Type         Disp Enb   Where
        # 1   breakpoint   keep yes   at /tmp/RepoEnv-_ha8r7_2/constants.py:6
        # 2   breakpoint   keep yes   at /tmp/RepoEnv-_ha8r7_2/constants.py:10
        # 3   breakpoint   keep yes   at /tmp/RepoEnv-_ha8r7_2/constants.py:14
        # -> ACTION_TO_INDEX = {
        new_breakpoints = {}
        breakpoint_pattern = re.compile(
            r"^\s*\d+\s+breakpoint\s+keep\s+yes\s+at\s+(.+):(\d+)$"
        )
        for line in output.splitlines():
            match = breakpoint_pattern.match(line)
            if match:
                # extract the file path and line number from the regex match
                file_path, line_number = match.groups()
                key = "|||".join([file_path, line_number])
                new_breakpoints[key] = f"b {file_path}:{line_number}"
        environment.current_breakpoints_state = new_breakpoints

    def set_current_frame_file(self, environment) -> str | None:
        """A free 'where' to obtain the current frame (line number), hidden from the agent."""
        command = "where"
        output = self.interact_with_gdb(command, environment.run_timeout)
        # parse the output to get the current frame
        # example output:
        #    /home/eryua/venvs/pdb/lib/python3.12/bdb.py(606)run()
        # -> exec(cmd, globals, locals)
        #    <string>(1)<module>()
        # > /tmp/RepoEnv-_ha8r7_2/constants.py(6)<module>()
        # -> ACTION_TO_INDEX = {
        sep = "> "
        file_path = None
        for line in output.splitlines():
            # find the line that starts with "> "
            if line.startswith(sep):
                # extract the file path from the line,
                # remove the leading "> ", the trailing "(line_number)<module>()", and working_dir
                # constants.py(6)<module>()
                # -> ACTION_TO_INDEX = {
                file_path = line[len(sep) :].split("(")[0]
                break
        if self.current_frame_file != file_path:
            self.current_frame_file = file_path
        return file_path
