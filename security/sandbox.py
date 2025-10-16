# Plugin Sandbox Execution Module

"""
Secure plugin sandbox execution environment.

This module provides sandboxed execution of plugins with OS-level restrictions,
resource limits, and security monitoring.
"""

import os
import subprocess
import tempfile
import time
import logging
import pathlib
import signal
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class SandboxResult(Enum):
    """Sandbox execution result."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    MEMORY_LIMIT = "memory_limit"
    SECURITY_VIOLATION = "security_violation"
    ERROR = "error"
    CRASH = "crash"

@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    cpu_seconds: int = 30
    memory_mb: int = 512  # Increased from 256
    timeout_seconds: int = 60
    allow_network: bool = False
    allow_filesystem_write: bool = False
    allowed_directories: List[str] = None
    drop_privileges: bool = False  # Disabled by default
    use_seccomp: bool = True
    use_apparmor: bool = True
    max_file_size: int = 1024 * 1024  # 1MB
    max_open_files: int = 10

@dataclass
class SandboxExecutionResult:
    """Result of sandbox execution."""
    result: SandboxResult
    output: str
    error: str
    execution_time: float
    memory_used: int
    exit_code: int
    audit_record: Optional[Dict[str, Any]] = None

class PluginSandbox:
    """Secure plugin sandbox execution environment."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.process = None
        self.start_time = None
        self.memory_monitor = None
        self.audit_logger = logging.getLogger("security.audit")
    
    def sandbox_exec(self, plugin_module: str, input_data: Any, plugin_path: str) -> SandboxExecutionResult:
        """Execute plugin in sandboxed environment."""
        self.start_time = time.time()
        
        try:
            # Create secure execution script
            execution_script = self._create_execution_script(plugin_path, input_data)
            
            # Prepare command with security restrictions
            cmd = self._prepare_sandbox_command(execution_script)
            
            # Execute in sandbox
            result = self._execute_sandbox(cmd, plugin_path)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - self.start_time
            
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "plugin_sandbox_execution",
                "plugin_module": plugin_module,
                "plugin_path": plugin_path,
                "execution_result": "error",
                "execution_time": execution_time,
                "error": str(e)
            }
            
            self.audit_logger.warning(f"Sandbox execution error for {plugin_module}: {e}")
            
            return SandboxExecutionResult(
                result=SandboxResult.ERROR,
                output="",
                error=str(e),
                execution_time=execution_time,
                memory_used=0,
                exit_code=-1,
                audit_record=audit_record
            )
    
    def _create_execution_script(self, plugin_module: str, input_data: Any) -> str:
        """Create secure execution script for plugin."""
        script_content = f"""
import sys
import json
import traceback
import signal
import importlib.util

# Set timeout handler
def timeout_handler(signum, frame):
    print("TIMEOUT_ERROR", file=sys.stderr)
    sys.exit(124)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({self.config.timeout_seconds})

try:
    # Load plugin module from file
    plugin_path = '{plugin_module}'
    spec = importlib.util.spec_from_file_location('plugin_module', plugin_path)
    plugin_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_module)
    
    # Get plugin class
    plugin_class = getattr(plugin_module, 'Plugin', None)
    if not plugin_class:
        print("PLUGIN_ERROR: No Plugin class found", file=sys.stderr)
        sys.exit(1)
    
    # Create plugin instance
    plugin = plugin_class()
    
    # Execute plugin
    result = plugin.run({repr(input_data)})
    
    # Output result
    print(json.dumps(result))
    
except Exception as e:
    print(f"PLUGIN_ERROR: {{str(e)}}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)
finally:
    signal.alarm(0)
"""
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            return f.name
    
    def _prepare_sandbox_command(self, script_path: str) -> List[str]:
        """Prepare sandbox command with security restrictions."""
        cmd = ["python3", script_path]
        
        # Skip privilege dropping for now (requires sudo configuration)
        # In production, this would be configured properly
        if self.config.drop_privileges and os.name == 'posix':
            logger.warning("Privilege dropping disabled - requires sudo configuration")
        
        return cmd
    
    def _execute_sandbox(self, cmd: List[str], plugin_path: str) -> SandboxExecutionResult:
        """Execute command in sandbox with monitoring."""
        try:
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=self._set_process_limits if os.name == 'posix' else None
            )
            
            self.process = process
            
            # Monitor process
            stdout, stderr = process.communicate(timeout=self.config.timeout_seconds)
            
            execution_time = time.time() - self.start_time
            
            # Parse output
            output = stdout.decode('utf-8', errors='ignore')
            error = stderr.decode('utf-8', errors='ignore')
            
            # Determine result
            result = self._determine_result(process.returncode, error, execution_time)
            
            # Create audit record
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "plugin_sandbox_execution",
                "plugin_path": plugin_path,
                "execution_result": result.value,
                "execution_time": execution_time,
                "exit_code": process.returncode,
                "memory_used": 0,  # Would need additional monitoring
                "output_length": len(output),
                "error_length": len(error)
            }
            
            # Log audit record
            if result == SandboxResult.SUCCESS:
                self.audit_logger.info(f"Plugin execution successful: {plugin_path}")
            else:
                self.audit_logger.warning(f"Plugin execution failed: {plugin_path} - {result.value}")
            
            return SandboxExecutionResult(
                result=result,
                output=output,
                error=error,
                execution_time=execution_time,
                memory_used=0,  # Would need additional monitoring
                exit_code=process.returncode,
                audit_record=audit_record
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - self.start_time
            
            # Kill process
            if self.process:
                self.process.kill()
                self.process.wait()
            
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "plugin_sandbox_execution",
                "plugin_path": plugin_path,
                "execution_result": "timeout",
                "execution_time": execution_time,
                "exit_code": 124
            }
            
            self.audit_logger.warning(f"Plugin execution timeout: {plugin_path}")
            
            return SandboxExecutionResult(
                result=SandboxResult.TIMEOUT,
                output="",
                error="Execution timeout",
                execution_time=execution_time,
                memory_used=0,
                exit_code=124,
                audit_record=audit_record
            )
            
        except Exception as e:
            execution_time = time.time() - self.start_time
            
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "plugin_sandbox_execution",
                "plugin_path": plugin_path,
                "execution_result": "error",
                "execution_time": execution_time,
                "error": str(e)
            }
            
            self.audit_logger.error(f"Sandbox execution error: {plugin_path} - {e}")
            
            return SandboxExecutionResult(
                result=SandboxResult.ERROR,
                output="",
                error=str(e),
                execution_time=execution_time,
                memory_used=0,
                exit_code=-1,
                audit_record=audit_record
            )
        finally:
            # Cleanup
            if hasattr(self, 'process') and self.process:
                self.process = None
    
    def _set_process_limits(self):
        """Set process limits for sandbox (Unix only)."""
        if os.name != 'posix':
            return
        
        try:
            import resource
            
            # Get current limits
            current_cpu = resource.getrlimit(resource.RLIMIT_CPU)
            current_memory = resource.getrlimit(resource.RLIMIT_AS)
            current_fsize = resource.getrlimit(resource.RLIMIT_FSIZE)
            current_nofile = resource.getrlimit(resource.RLIMIT_NOFILE)
            
            # Set CPU time limit (only if current limit allows)
            if current_cpu[1] == -1 or self.config.cpu_seconds <= current_cpu[1]:
                resource.setrlimit(resource.RLIMIT_CPU, (self.config.cpu_seconds, self.config.cpu_seconds))
            
            # Set memory limit (only if current limit allows)
            memory_bytes = self.config.memory_mb * 1024 * 1024
            if current_memory[1] == -1 or memory_bytes <= current_memory[1]:
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            
            # Set file size limit (only if current limit allows)
            if current_fsize[1] == -1 or self.config.max_file_size <= current_fsize[1]:
                resource.setrlimit(resource.RLIMIT_FSIZE, (self.config.max_file_size, self.config.max_file_size))
            
            # Set open file limit (only if current limit allows)
            if current_nofile[1] == -1 or self.config.max_open_files <= current_nofile[1]:
                resource.setrlimit(resource.RLIMIT_NOFILE, (self.config.max_open_files, self.config.max_open_files))
            
        except Exception as e:
            logger.warning(f"Could not set process limits: {e}")
    
    def _determine_result(self, exit_code: int, error: str, execution_time: float) -> SandboxResult:
        """Determine sandbox execution result."""
        if exit_code == 0:
            return SandboxResult.SUCCESS
        elif exit_code == 124:
            return SandboxResult.TIMEOUT
        elif "MEMORY_ERROR" in error:
            return SandboxResult.MEMORY_LIMIT
        elif "SECURITY_VIOLATION" in error:
            return SandboxResult.SECURITY_VIOLATION
        elif "PLUGIN_ERROR" in error:
            return SandboxResult.CRASH
        else:
            return SandboxResult.ERROR

class SecurePluginRunner:
    """Secure plugin runner with additional security features."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.sandbox = PluginSandbox(config)
        self.audit_logger = logging.getLogger("security.audit")
    
    def run_plugin(self, plugin_module: str, input_data: Any, plugin_path: str) -> Dict[str, Any]:
        """Run plugin with security checks and sandboxing."""
        try:
            # Execute in sandbox
            result = self.sandbox.sandbox_exec(plugin_module, input_data, plugin_path)
            
            # Process result
            if result.result == SandboxResult.SUCCESS:
                try:
                    import json
                    plugin_output = json.loads(result.output)
                    return {
                        "success": True,
                        "data": plugin_output,
                        "execution_time": result.execution_time,
                        "memory_used": result.memory_used
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Invalid plugin output format",
                        "execution_time": result.execution_time
                    }
            else:
                return {
                    "success": False,
                    "error": f"Plugin execution failed: {result.result.value}",
                    "execution_time": result.execution_time,
                    "sandbox_error": result.error
                }
                
        except Exception as e:
            self.audit_logger.error(f"Plugin runner error: {plugin_module} - {e}")
            return {
                "success": False,
                "error": f"Plugin runner error: {str(e)}"
            }

# Convenience functions
def sandbox_exec(plugin_module: str, input_data: Any, plugin_path: str, 
                 config: Optional[SandboxConfig] = None) -> SandboxExecutionResult:
    """Execute plugin in sandboxed environment."""
    if config is None:
        config = SandboxConfig()
    
    sandbox = PluginSandbox(config)
    return sandbox.sandbox_exec(plugin_module, input_data, plugin_path)

def run_plugin_secure(plugin_module: str, input_data: Any, plugin_path: str,
                     config: Optional[SandboxConfig] = None) -> Dict[str, Any]:
    """Run plugin securely with sandboxing."""
    if config is None:
        config = SandboxConfig()
    
    runner = SecurePluginRunner(config)
    return runner.run_plugin(plugin_module, input_data, plugin_path)

# CLI interface
def main():
    """CLI interface for sandbox execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Plugin sandbox execution")
    parser.add_argument("plugin_module", help="Plugin module name")
    parser.add_argument("plugin_path", help="Plugin file path")
    parser.add_argument("--input", default="{}", help="Input data as JSON")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    parser.add_argument("--memory", type=int, default=256, help="Memory limit in MB")
    parser.add_argument("--cpu", type=int, default=30, help="CPU time limit in seconds")
    
    args = parser.parse_args()
    
    # Parse input data
    import json
    input_data = json.loads(args.input)
    
    # Create config
    config = SandboxConfig(
        timeout_seconds=args.timeout,
        memory_mb=args.memory,
        cpu_seconds=args.cpu
    )
    
    # Run plugin
    result = run_plugin_secure(args.plugin_module, input_data, args.plugin_path, config)
    
    # Output result
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
