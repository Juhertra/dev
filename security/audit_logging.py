# Security Audit Logging Module

"""
Comprehensive security audit logging for plugin execution and security events.

This module provides structured audit logging for all security-related events,
enabling security monitoring, compliance, and incident response.
"""

import json
import logging
import logging.handlers
import pathlib
import time
import threading
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of security audit events."""
    PLUGIN_LOAD = "plugin_load"
    PLUGIN_EXECUTION = "plugin_execution"
    SIGNATURE_VERIFICATION = "signature_verification"
    POLICY_CHECK = "policy_check"
    SANDBOX_EXECUTION = "sandbox_execution"
    SECURITY_VIOLATION = "security_violation"
    ACCESS_ATTEMPT = "access_attempt"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_EVENT = "system_event"

class AuditSeverity(Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Security audit event."""
    timestamp: str
    event_type: AuditEventType
    severity: AuditSeverity
    plugin_name: Optional[str] = None
    plugin_path: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    memory_used: Optional[int] = None
    audit_id: Optional[str] = None

class SecurityAuditLogger:
    """Security audit logger with structured logging and compliance features."""
    
    def __init__(self, log_dir: str = "logs/security", 
                 max_file_size: int = 100 * 1024 * 1024,  # 100MB
                 backup_count: int = 10,
                 enable_console: bool = False):
        self.log_dir = pathlib.Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        
        self._setup_loggers()
        self._audit_lock = threading.Lock()
        
        # Audit event counter
        self._event_counter = 0
    
    def _setup_loggers(self):
        """Setup audit loggers."""
        # Main audit logger
        self.audit_logger = logging.getLogger("security.audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.audit_logger.handlers[:]:
            self.audit_logger.removeHandler(handler)
        
        # File handler for audit logs
        audit_file = self.log_dir / "audit.log"
        file_handler = logging.handlers.RotatingFileHandler(
            audit_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        json_formatter = AuditJSONFormatter()
        file_handler.setFormatter(json_formatter)
        
        self.audit_logger.addHandler(file_handler)
        
        # Console handler (optional)
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.audit_logger.addHandler(console_handler)
        
        # Security violations logger
        self.violation_logger = logging.getLogger("security.violations")
        self.violation_logger.setLevel(logging.WARNING)
        
        violation_file = self.log_dir / "violations.log"
        violation_handler = logging.handlers.RotatingFileHandler(
            violation_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        violation_handler.setLevel(logging.WARNING)
        violation_handler.setFormatter(json_formatter)
        
        self.violation_logger.addHandler(violation_handler)
        
        # System events logger
        self.system_logger = logging.getLogger("security.system")
        self.system_logger.setLevel(logging.INFO)
        
        system_file = self.log_dir / "system.log"
        system_handler = logging.handlers.RotatingFileHandler(
            system_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        system_handler.setLevel(logging.INFO)
        system_handler.setFormatter(json_formatter)
        
        self.system_logger.addHandler(system_handler)
    
    def log_audit_event(self, event: AuditEvent):
        """Log a security audit event."""
        with self._audit_lock:
            self._event_counter += 1
            event.audit_id = f"AUDIT-{self._event_counter:06d}"
            
            # Log to appropriate logger based on severity
            if event.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                self.violation_logger.warning(self._format_audit_event(event))
            else:
                self.audit_logger.info(self._format_audit_event(event))
    
    def _format_audit_event(self, event: AuditEvent) -> str:
        """Format audit event for logging."""
        event_dict = asdict(event)
        event_dict['event_type'] = event.event_type.value
        event_dict['severity'] = event.severity.value
        return json.dumps(event_dict, default=str)
    
    def log_plugin_load(self, plugin_name: str, plugin_path: str, 
                       success: bool, error: Optional[str] = None,
                       user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log plugin load event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.PLUGIN_LOAD,
            severity=AuditSeverity.MEDIUM if success else AuditSeverity.HIGH,
            plugin_name=plugin_name,
            plugin_path=plugin_path,
            user_id=user_id,
            session_id=session_id,
            result="success" if success else "failure",
            error_message=error
        )
        self.log_audit_event(event)
    
    def log_plugin_execution(self, plugin_name: str, plugin_path: str,
                           success: bool, execution_time: float,
                           memory_used: int, error: Optional[str] = None,
                           user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log plugin execution event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.PLUGIN_EXECUTION,
            severity=AuditSeverity.LOW if success else AuditSeverity.MEDIUM,
            plugin_name=plugin_name,
            plugin_path=plugin_path,
            user_id=user_id,
            session_id=session_id,
            result="success" if success else "failure",
            error_message=error,
            execution_time=execution_time,
            memory_used=memory_used
        )
        self.log_audit_event(event)
    
    def log_signature_verification(self, plugin_name: str, plugin_path: str,
                                 success: bool, signature_type: str,
                                 verification_time: float, error: Optional[str] = None):
        """Log signature verification event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.SIGNATURE_VERIFICATION,
            severity=AuditSeverity.LOW if success else AuditSeverity.HIGH,
            plugin_name=plugin_name,
            plugin_path=plugin_path,
            result="success" if success else "failure",
            error_message=error,
            execution_time=verification_time,
            event_data={"signature_type": signature_type}
        )
        self.log_audit_event(event)
    
    def log_policy_check(self, plugin_name: str, plugin_path: str,
                        compliant: bool, violations: List[str],
                        user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log policy check event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.POLICY_CHECK,
            severity=AuditSeverity.LOW if compliant else AuditSeverity.MEDIUM,
            plugin_name=plugin_name,
            plugin_path=plugin_path,
            user_id=user_id,
            session_id=session_id,
            result="compliant" if compliant else "violation",
            event_data={"violations": violations}
        )
        self.log_audit_event(event)
    
    def log_sandbox_execution(self, plugin_name: str, plugin_path: str,
                            success: bool, execution_time: float,
                            memory_used: int, sandbox_result: str,
                            error: Optional[str] = None):
        """Log sandbox execution event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.SANDBOX_EXECUTION,
            severity=AuditSeverity.LOW if success else AuditSeverity.MEDIUM,
            plugin_name=plugin_name,
            plugin_path=plugin_path,
            result=sandbox_result,
            error_message=error,
            execution_time=execution_time,
            memory_used=memory_used
        )
        self.log_audit_event(event)
    
    def log_security_violation(self, violation_type: str, description: str,
                             plugin_name: Optional[str] = None,
                             plugin_path: Optional[str] = None,
                             user_id: Optional[str] = None,
                             session_id: Optional[str] = None,
                             severity: AuditSeverity = AuditSeverity.HIGH):
        """Log security violation event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=severity,
            plugin_name=plugin_name,
            plugin_path=plugin_path,
            user_id=user_id,
            session_id=session_id,
            result="violation",
            event_data={
                "violation_type": violation_type,
                "description": description
            }
        )
        self.log_audit_event(event)
    
    def log_access_attempt(self, resource: str, access_type: str,
                          success: bool, user_id: Optional[str] = None,
                          session_id: Optional[str] = None,
                          source_ip: Optional[str] = None,
                          user_agent: Optional[str] = None):
        """Log access attempt event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.ACCESS_ATTEMPT,
            severity=AuditSeverity.LOW if success else AuditSeverity.MEDIUM,
            user_id=user_id,
            session_id=session_id,
            source_ip=source_ip,
            user_agent=user_agent,
            result="success" if success else "failure",
            event_data={
                "resource": resource,
                "access_type": access_type
            }
        )
        self.log_audit_event(event)
    
    def log_configuration_change(self, config_key: str, old_value: Any,
                                new_value: Any, user_id: Optional[str] = None,
                                session_id: Optional[str] = None):
        """Log configuration change event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            session_id=session_id,
            result="change",
            event_data={
                "config_key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value)
            }
        )
        self.log_audit_event(event)
    
    def log_system_event(self, event_description: str, event_data: Optional[Dict[str, Any]] = None,
                        severity: AuditSeverity = AuditSeverity.LOW):
        """Log system event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=AuditEventType.SYSTEM_EVENT,
            severity=severity,
            result="event",
            event_data={
                "description": event_description,
                "data": event_data or {}
            }
        )
        self.log_audit_event(event)

class AuditJSONFormatter(logging.Formatter):
    """JSON formatter for audit logs."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, default=str)

class SecurityAuditMonitor:
    """Monitor security audit events for anomalies and violations."""
    
    def __init__(self, audit_logger: SecurityAuditLogger):
        self.audit_logger = audit_logger
        self.violation_thresholds = {
            "failed_signatures_per_hour": 5,
            "policy_violations_per_hour": 3,
            "sandbox_failures_per_hour": 10,
            "security_violations_per_hour": 2
        }
        self.monitoring_active = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start security monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.audit_logger.log_system_event(
            "Security monitoring started",
            {"monitoring_active": True}
        )
    
    def stop_monitoring(self):
        """Stop security monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.audit_logger.log_system_event(
            "Security monitoring stopped",
            {"monitoring_active": False}
        )
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._check_violation_thresholds()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Security monitoring error: {e}")
                time.sleep(60)
    
    def _check_violation_thresholds(self):
        """Check violation thresholds."""
        # This would typically read from log files or database
        # For now, we'll implement a simple check
        
        # Check for high-severity events in the last hour
        recent_violations = self._count_recent_violations()
        
        for violation_type, count in recent_violations.items():
            threshold = self.violation_thresholds.get(f"{violation_type}_per_hour", 0)
            if count > threshold:
                self.audit_logger.log_security_violation(
                    "threshold_exceeded",
                    f"{violation_type} threshold exceeded: {count} > {threshold}",
                    severity=AuditSeverity.HIGH
                )
    
    def _count_recent_violations(self) -> Dict[str, int]:
        """Count recent violations (placeholder implementation)."""
        # In a real implementation, this would read from log files or database
        return {
            "failed_signatures": 0,
            "policy_violations": 0,
            "sandbox_failures": 0,
            "security_violations": 0
        }

@contextmanager
def audit_plugin_execution(audit_logger: SecurityAuditLogger, plugin_name: str,
                          plugin_path: str, user_id: Optional[str] = None,
                          session_id: Optional[str] = None):
    """Context manager for auditing plugin execution."""
    start_time = time.time()
    success = False
    error = None
    memory_used = 0
    
    try:
        yield
        success = True
    except Exception as e:
        error = str(e)
        raise
    finally:
        execution_time = time.time() - start_time
        audit_logger.log_plugin_execution(
            plugin_name, plugin_path, success, execution_time,
            memory_used, error, user_id, session_id
        )

# Global audit logger instance
_audit_logger = None

def get_audit_logger() -> SecurityAuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SecurityAuditLogger()
    return _audit_logger

def setup_security_audit_logging(log_dir: str = "logs/security",
                                enable_console: bool = False) -> SecurityAuditLogger:
    """Setup security audit logging."""
    global _audit_logger
    _audit_logger = SecurityAuditLogger(log_dir, enable_console=enable_console)
    return _audit_logger

# Convenience functions
def log_plugin_load(plugin_name: str, plugin_path: str, success: bool,
                   error: Optional[str] = None, user_id: Optional[str] = None,
                   session_id: Optional[str] = None):
    """Log plugin load event."""
    audit_logger = get_audit_logger()
    audit_logger.log_plugin_load(plugin_name, plugin_path, success, error, user_id, session_id)

def log_plugin_execution(plugin_name: str, plugin_path: str, success: bool,
                        execution_time: float, memory_used: int,
                        error: Optional[str] = None, user_id: Optional[str] = None,
                        session_id: Optional[str] = None):
    """Log plugin execution event."""
    audit_logger = get_audit_logger()
    audit_logger.log_plugin_execution(plugin_name, plugin_path, success, execution_time,
                                    memory_used, error, user_id, session_id)

def log_signature_verification(plugin_name: str, plugin_path: str, success: bool,
                              signature_type: str, verification_time: float,
                              error: Optional[str] = None):
    """Log signature verification event."""
    audit_logger = get_audit_logger()
    audit_logger.log_signature_verification(plugin_name, plugin_path, success,
                                          signature_type, verification_time, error)

def log_policy_check(plugin_name: str, plugin_path: str, compliant: bool,
                    violations: List[str], user_id: Optional[str] = None,
                    session_id: Optional[str] = None):
    """Log policy check event."""
    audit_logger = get_audit_logger()
    audit_logger.log_policy_check(plugin_name, plugin_path, compliant, violations, user_id, session_id)

def log_security_violation(violation_type: str, description: str,
                          plugin_name: Optional[str] = None,
                          plugin_path: Optional[str] = None,
                          user_id: Optional[str] = None,
                          session_id: Optional[str] = None,
                          severity: AuditSeverity = AuditSeverity.HIGH):
    """Log security violation event."""
    audit_logger = get_audit_logger()
    audit_logger.log_security_violation(violation_type, description, plugin_name,
                                       plugin_path, user_id, session_id, severity)

# CLI interface
def main():
    """CLI interface for security audit logging."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Audit Logging")
    parser.add_argument("--setup", action="store_true", help="Setup audit logging")
    parser.add_argument("--log-dir", default="logs/security", help="Log directory")
    parser.add_argument("--enable-console", action="store_true", help="Enable console logging")
    parser.add_argument("--test", action="store_true", help="Test audit logging")
    
    args = parser.parse_args()
    
    if args.setup:
        audit_logger = setup_security_audit_logging(args.log_dir, args.enable_console)
        print(f"Security audit logging setup complete. Logs in: {args.log_dir}")
    
    if args.test:
        audit_logger = get_audit_logger()
        
        # Test various audit events
        audit_logger.log_plugin_load("test_plugin", "/path/to/plugin.py", True)
        audit_logger.log_signature_verification("test_plugin", "/path/to/plugin.py", True, "rsa", 0.1)
        audit_logger.log_policy_check("test_plugin", "/path/to/plugin.py", True, [])
        audit_logger.log_plugin_execution("test_plugin", "/path/to/plugin.py", True, 0.5, 1024)
        audit_logger.log_security_violation("test_violation", "Test security violation")
        
        print("Test audit events logged successfully")

if __name__ == "__main__":
    main()
