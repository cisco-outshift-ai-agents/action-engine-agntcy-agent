import os
import random
import shlex
import subprocess
import time
import logging
import asyncio
from typing import Dict, Any, Optional
from browser_use.agent.views import ActionResult
from browser_use.controller.service import Registry

from src.terminal.terminal_views import TerminalCommandAction

logger = logging.getLogger(__name__)

import os
import random
import shlex
import subprocess
import time
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TerminalManager:
    """Manages terminal sessions and command execution using tmux"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TerminalManager, cls).__new__(cls)
            cls._instance.terminals = {}
            cls._instance.current_terminal_id = None
            logger.info("TerminalManager instance created")
        return cls._instance
    
    async def create_terminal(self) -> str:
        """Creates a new terminal session using tmux and returns its ID"""
        # terminal_id = str(random.randint(1000, 9999))
        # logger.info(f"Generated terminal ID: {terminal_id}")

        if self.current_terminal_id and self.current_terminal_id in self.terminals:
            logger.info(f"Terminal {self.current_terminal_id} already exists, reusing it.")
            return self.current_terminal_id
        #generate a new ID that doesnt conflict with existing sessions
        terminal_id = str(random.randint(1000, 9999))
        while os.system(f"tmux has-session -t {terminal_id} 2>/dev/null") == 0:
            #session exists, try another ID
            terminal_id = str(random.randint(1000, 9999))
        logger.info(f"Generated terminal ID: {terminal_id}")

        #Generate a new tmux session

        try:
        
           process = subprocess.Popen(
 ["tmux", "new-session", "-d", "-s", terminal_id, "-c", os.path.expanduser("~")],
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE
 )
           stdout, stderr = process.communicate()
        
           if process.returncode != 0:
               error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
               logger.error(f"Error creating terminal: {error_msg}")
               raise Exception(f"Error creating terminal: {error_msg}")
        
           # Get the initial working directory
           working_dir = await self._get_working_directory(terminal_id)
        
           self.terminals[terminal_id] = {
               "session_name": terminal_id, 
               "output": "",
               "working_directory": working_dir
 }
           self.current_terminal_id = terminal_id
           logger.info(f"Created terminal with ID: {terminal_id}")
           return terminal_id
        except Exception as e:
            logger.error(f"Error creating terminal: {str(e)}")
            raise e
    
    async def _get_working_directory(self, terminal_id: str) -> str:
        """Get the current working directory of the terminal"""
        if terminal_id not in self.terminals:
            raise ValueError(f"Terminal {terminal_id} does not exist")
        
        session_name = self.terminals[terminal_id]["session_name"]
        
        # Run pwd in the terminal and capture output
        start_marker = f"PWD_{random.randint(1000, 9999)}"
        end_marker = f"END_{random.randint(1000, 9999)}"
        
        os.system(f"tmux send-keys -t {session_name} 'echo {start_marker} && pwd && echo {end_marker}' C-m")
        
        # Wait for output
        for _ in range(10):
            await asyncio.sleep(0.2)
            output = subprocess.getoutput(f"tmux capture-pane -p -t {session_name}")
            
            if start_marker in output and end_marker in output:
                # Extract the working directory
                output_lines = output.split(start_marker, 1)[1].split(end_marker, 1)[0].strip().split('\n')
                # The pwd output should be the second line
                if len(output_lines) >= 2:
                    return output_lines[1].strip()
                return os.path.expanduser("~")  # Default to home directory
        
        return os.path.expanduser("~")  # Default to home directory if unable to determine
    
    async def execute_command(self, terminal_id:Optional[str], command: str) -> tuple[str, bool]:
        """Execute a command in the specified terminal and return the output"""
        "Returns a tuple of (output, is_success)"
        try:
            # Handle None terminal_id 
            if terminal_id  is None or terminal_id not in self.terminals:
               logger.warning(f"Terminal {terminal_id} does not exist, creating a new one.")  
               terminal_id = await self.create_terminal() 

            session_name = self.terminals[terminal_id]["session_name"]
            escaped_command = shlex.quote(command)
        
            # Clear the terminal before executing the command
            os.system(f"tmux send-keys -t {session_name} 'clear' C-m")
        
           # Use markers to identify the start and end of our command output
            start_marker = f"START_{random.randint(1000, 9999)}"
            end_marker = f">>>END<<<"
        
            os.system(f"tmux send-keys -t {session_name} 'echo {start_marker}' C-m")
            os.system(f"tmux send-keys -t {session_name} {escaped_command} C-m")
            os.system(f"tmux send-keys -t {session_name} 'echo {end_marker}' C-m")
        
            # Poll for output until end marker is found - up to 10 seconds
            for _ in range(20):
               await asyncio.sleep(0.5)
               output = subprocess.getoutput(f"tmux capture-pane -p -t {session_name} -S -5000")
               if end_marker in output:
                   break
            else:
               logger.warning(f"Command execution timed out: {command}")
               return "Command execution timed out"
        
            # Extract the command output between markers using get_terminal_output
            final_output = self.get_terminal_output(output, start_marker)
            self.terminals[terminal_id]["output"] = final_output
        
            # Update the working directory
            self.terminals[terminal_id]["working_directory"] = await self._get_working_directory(terminal_id)
        
            return final_output, True
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            logger.error(error_msg)

            working_dir = "~"
            if terminal_id in self.terminals:
                working_dir = self.terminals[terminal_id].get("working_directory", "~")
            return f"Error executing command: {error_msg}\nCurrent directory: {working_dir}", False
    
    def get_terminal_output(self, output: str, start_marker: str) -> str:
        """Extract command output between markers"""
        if start_marker in output and ">>>END<<<" in output:
            output = output.split(start_marker, 1)[-1]
            output = output.split(">>>END<<<", 1)[0]
        else:
            return "Command execution failed or output parsing error"
        
        output_lines = output.splitlines()
        
        # Cleanup logic from your implementation
        cleaned_lines = []
        for i, line in enumerate(output_lines):
            stripped_line = line.strip()
            if stripped_line == start_marker:
                continue
            if stripped_line.endswith("echo"):
                stripped_line = stripped_line.replace("echo", "").strip()
                
            cleaned_lines.append(stripped_line)
            
        return "\n".join(cleaned_lines).strip()
    
    async def get_terminal_output_history(self, terminal_id: str) -> str:
        """Get the current output of the terminal session"""
        if terminal_id not in self.terminals:
            raise ValueError(f"Terminal {terminal_id} does not exist")
        
        return self.terminals[terminal_id].get("output", "")
    
    async def get_terminal_state(self, terminal_id: str) -> Dict[str, Any]:
        """Get the current state of the terminal"""
        if terminal_id not in self.terminals:
            raise ValueError(f"Terminal {terminal_id} does not exist")
        
        return {
            "terminal_id": terminal_id,
            "output": self.terminals[terminal_id].get("output", ""),
            "working_directory": self.terminals[terminal_id].get("working_directory", "")
 }
    
    async def execute_command_workflow(self, command: str) -> Dict[str, Any]:
        """Complete workflow for executing a terminal command"""
        try:
            # Get or create terminal
            if self.current_terminal_id is None or self.current_terminal_id not in self.terminals:
                terminal_id = await self.create_terminal()
            else:
                terminal_id = self.current_terminal_id
            
            # Execute the command
            output = await self.execute_command(terminal_id, command)
            
            # Get the terminal state
            terminal_state = await self.get_terminal_state(terminal_id)
            
            return {
                "success": True,
                "terminal_id": terminal_id,
                "output": output,
                "working_directory": terminal_state["working_directory"],
                "command": command
 }
        except Exception as e:
            error_msg = f"Terminal workflow error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "command": command
 }
    
    async def delete_terminal(self, terminal_id: Optional[str] = None) -> str:
        """Delete a terminal session or all terminal sessions"""
        if terminal_id:
            # Delete a particular terminal
            if terminal_id not in self.terminals:
                raise ValueError(f"Terminal {terminal_id} does not exist")
                
            session_name = self.terminals[terminal_id]["session_name"]
            # Kill the tmux session
            process = subprocess.run(
 ["tmux", "kill-session", "-t", session_name], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
 )
            
            if process.returncode != 0:
                error_msg = process.stderr.decode('utf-8') if process.stderr else "Unknown error"
                logger.error(f"Error deleting terminal {terminal_id}: {error_msg}")
                raise Exception(f"Error deleting terminal {terminal_id}: {error_msg}")
            
            del self.terminals[terminal_id]
            if self.current_terminal_id == terminal_id:
                self.current_terminal_id = None
            
            return f"Terminal {terminal_id} deleted"
        else:
            # Delete all terminals
            for tid, terminal in list(self.terminals.items()):
                session_name = terminal["session_name"]
                process = subprocess.run(
 ["tmux", "kill-session", "-t", session_name], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
 )
                # We don't check for errors here, just trying to clean up as much as possible
            
            self.terminals = {}
            self.current_terminal_id = None
            return "All terminals deleted"
    
    async def get_current_terminal_id(self) -> Optional[str]:
        """Get the current terminal ID"""
        return self.current_terminal_id
    
    async def list_terminals(self) -> Dict[str, Dict[str, Any]]:
        """List all active terminal sessions"""
        return self.terminals
