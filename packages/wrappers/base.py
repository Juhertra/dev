"""
Base wrapper protocol and common functionality for tool integration.

This module defines the standardized interface that all tool wrappers must implement
to ensure consistent orchestration and parsing across different security tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Protocol, Optional
from dataclasses import dataclass
import subprocess
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolOutput:
    """Standardized tool output container."""
    raw_output: str
    exit_code: int
    stderr: str
    execution_time_ms: int
    tool_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Finding:
    """Standardized finding model for all tools."""
    title: str
    severity: str
    path: str
    detector_id: str
    evidence: Dict[str, Any]
    confidence: int = 80
    status: str = "open"


class ToolWrapperError(Exception):
    """Base exception for tool wrapper errors."""
    pass


class ToolBinaryError(ToolWrapperError):
    """Tool binary not found or not executable."""
    pass


class ToolExecutionError(ToolWrapperError):
    """Tool execution failed."""
    pass


class ToolParseError(ToolWrapperError):
    """Tool output parsing failed."""
    pass


class ToolWrapper(Protocol):
    """
    Standardized interface for all tool wrappers.
    
    All tool wrappers must implement this protocol to ensure consistent
    orchestration and integration with the workflow engine.
    """
    
    def prepare(self, config: Dict[str, Any]) -> None:
        """
        Prepare tool with configuration.
        
        Args:
            config: Tool-specific configuration dictionary
        """
        pass
    
    def run(self, target: str, **kwargs) -> ToolOutput:
        """
        Execute tool and return standardized output.
        
        Args:
            target: Target URL, IP, or file path
            **kwargs: Additional tool-specific parameters
            
        Returns:
            ToolOutput: Standardized output container
            
        Raises:
            ToolBinaryError: If tool binary is not found
            ToolExecutionError: If tool execution fails
        """
        pass
    
    def parse_output(self, output: ToolOutput) -> List[Finding]:
        """
        Parse raw tool output into standardized findings.
        
        Args:
            output: ToolOutput container with raw output
            
        Returns:
            List[Finding]: Parsed findings
            
        Raises:
            ToolParseError: If parsing fails
        """
        pass
    
    def check_version(self) -> str:
        """
        Check tool version and return version string.
        
        Returns:
            str: Tool version string
            
        Raises:
            ToolBinaryError: If tool binary is not found
        """
        pass


class BaseWrapper(ABC):
    """
    Abstract base class providing common wrapper functionality.
    
    Concrete wrappers should inherit from this class and implement
    the abstract methods for tool-specific behavior.
    """
    
    def __init__(self, manifest: Dict[str, Any]):
        """
        Initialize wrapper with tool manifest.
        
        Args:
            manifest: Tool manifest containing configuration
        """
        self.manifest = manifest
        self.binary = manifest.get("binary", "")
        self.min_version = manifest.get("min_version", "0.0.0")
        
    def _check_binary(self) -> None:
        """Check if tool binary is available."""
        try:
            result = subprocess.run(
                [self.binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ToolBinaryError(f"Tool {self.binary} not executable")
        except FileNotFoundError:
            raise ToolBinaryError(f"Tool binary {self.binary} not found")
        except subprocess.TimeoutExpired:
            raise ToolBinaryError(f"Tool {self.binary} version check timeout")
    
    def _execute_command(self, cmd: List[str], timeout: int = 300) -> ToolOutput:
        """
        Execute command and return standardized output.
        
        Args:
            cmd: Command to execute
            timeout: Execution timeout in seconds
            
        Returns:
            ToolOutput: Standardized output container
        """
        import time
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return ToolOutput(
                raw_output=result.stdout,
                exit_code=result.returncode,
                stderr=result.stderr,
                execution_time_ms=execution_time_ms
            )
            
        except subprocess.TimeoutExpired:
            raise ToolExecutionError(f"Tool execution timeout after {timeout}s")
        except Exception as e:
            raise ToolExecutionError(f"Tool execution failed: {str(e)}")
    
    @abstractmethod
    def prepare(self, config: Dict[str, Any]) -> None:
        """Prepare tool with configuration."""
        pass
    
    @abstractmethod
    def run(self, target: str, **kwargs) -> ToolOutput:
        """Execute tool and return standardized output."""
        pass
    
    @abstractmethod
    def parse_output(self, output: ToolOutput) -> List[Finding]:
        """Parse raw tool output into standardized findings."""
        pass
    
    def check_version(self) -> str:
        """Check tool version and return version string."""
        self._check_binary()
        
        try:
            result = subprocess.run(
                [self.binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                # Some tools output version to stderr
                return result.stderr.strip()
                
        except Exception as e:
            raise ToolBinaryError(f"Version check failed: {str(e)}")


# Example implementation skeleton for reference
class ExampleWrapper(BaseWrapper):
    """
    Example wrapper implementation showing the pattern.
    
    This is a skeleton for reference - actual wrappers will be implemented
    in M2 for Nuclei, Feroxbuster, Katana, and ZAP.
    """
    
    def prepare(self, config: Dict[str, Any]) -> None:
        """Prepare example tool with configuration."""
        self.config = config
        logger.info(f"Prepared {self.binary} with config: {config}")
    
    def run(self, target: str, **kwargs) -> ToolOutput:
        """Execute example tool."""
        self._check_binary()
        
        cmd = [self.binary, target]
        return self._execute_command(cmd)
    
    def parse_output(self, output: ToolOutput) -> List[Finding]:
        """Parse example tool output."""
        findings = []
        
        try:
            # Example parsing logic
            data = json.loads(output.raw_output)
            
            finding = Finding(
                title="Example Finding",
                severity="medium",
                path=target,
                detector_id="example",
                evidence=data
            )
            findings.append(finding)
            
        except json.JSONDecodeError as e:
            raise ToolParseError(f"Failed to parse JSON output: {str(e)}")
        
        return findings
