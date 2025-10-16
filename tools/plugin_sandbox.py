"""
Plugin Sandboxing Implementation

This module implements lightweight plugin sandboxing for M1, providing basic 
resource limits and process isolation. Full container-based sandboxing will 
be implemented in M4.
"""

import subprocess
import tempfile
import os
import signal
import time
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class SandboxConfig:
    """Configuration for plugin sandboxing."""
    max_memory_mb: int = 100
    max_cpu_time_seconds: int = 30
    max_file_size_mb: int = 10
    allowed_network_hosts: List[str] = None
    temp_dir: Optional[str] = None
    
    def __post_init__(self):
        if self.allowed_network_hosts is None:
            self.allowed_network_hosts = []

@dataclass
class SandboxResult:
    """Result of plugin execution in sandbox."""
    success: bool
    output: str
    error: str
    exit_code: int
    memory_used_mb: float
    cpu_time_seconds: float
    execution_time_seconds: float

class PluginSandbox:
    """Lightweight plugin sandbox for M1."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.temp_dir = config.temp_dir or tempfile.mkdtemp()
        
    def execute_plugin(self, plugin_path: str, args: List[str] = None) -> SandboxResult:
        """Execute plugin in sandboxed environment."""
        if args is None:
            args = []
            
        start_time = time.time()
        
        try:
            # Create subprocess with resource limits
            process = subprocess.Popen(
                [plugin_path] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.temp_dir,
                preexec_fn=self._set_resource_limits
            )
            
            # Monitor resource usage
            memory_used = 0
            cpu_time = 0
            
            try:
                stdout, stderr = process.communicate(timeout=self.config.max_cpu_time_seconds)
                memory_used = self._get_memory_usage(process.pid)
                cpu_time = self._get_cpu_time(process.pid)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return SandboxResult(
                    success=False,
                    output=stdout.decode('utf-8', errors='ignore'),
                    error=f"Timeout after {self.config.max_cpu_time_seconds}s",
                    exit_code=-1,
                    memory_used_mb=memory_used,
                    cpu_time_seconds=cpu_time,
                    execution_time_seconds=time.time() - start_time
                )
            
            execution_time = time.time() - start_time
            
            return SandboxResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8', errors='ignore'),
                error=stderr.decode('utf-8', errors='ignore'),
                exit_code=process.returncode,
                memory_used_mb=memory_used,
                cpu_time_seconds=cpu_time,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            return SandboxResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                memory_used_mb=0,
                cpu_time_seconds=0,
                execution_time_seconds=time.time() - start_time
            )
    
    def _set_resource_limits(self):
        """Set resource limits for the subprocess."""
        try:
            import resource
            # Set memory limit
            memory_limit = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit
            cpu_limit = self.config.max_cpu_time_seconds
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")
    
    def _get_memory_usage(self, pid: int) -> float:
        """Get memory usage in MB for a process."""
        try:
            process = psutil.Process(pid)
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _get_cpu_time(self, pid: int) -> float:
        """Get CPU time in seconds for a process."""
        try:
            process = psutil.Process(pid)
            return process.cpu_times().user + process.cpu_times().system
        except:
            return 0.0
    
    def cleanup(self):
        """Clean up sandbox resources."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox: {e}")

# Example usage and testing
if __name__ == "__main__":
    # Test the sandbox with a simple command
    config = SandboxConfig(
        max_memory_mb=50,
        max_cpu_time_seconds=10
    )
    
    sandbox = PluginSandbox(config)
    
    # Test with a simple echo command
    result = sandbox.execute_plugin("echo", ["Hello, Sandbox!"])
    
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    print(f"Error: {result.error}")
    print(f"Memory used: {result.memory_used_mb:.2f} MB")
    print(f"CPU time: {result.cpu_time_seconds:.2f} seconds")
    
    sandbox.cleanup()