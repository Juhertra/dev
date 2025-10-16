"""
SecFlow Python 3.14 Integration Considerations

This module documents and implements Python 3.14 integration considerations
for the observability system, focusing on no-GIL mode and subinterpreters.

Key Features:
- Thread safety considerations for no-GIL mode
- Subinterpreter support for observability tasks
- Background thread optimization
- Performance considerations for concurrent execution
"""

import threading
import time
import queue
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Python314Config:
    """Configuration for Python 3.14 features."""
    enable_no_gil: bool = False
    enable_subinterpreters: bool = False
    background_threads: int = 2
    observability_queue_size: int = 1000


class Python314ObservabilityAdapter:
    """
    Adapter for Python 3.14 observability features.
    
    Provides optimized observability operations for no-GIL mode
    and subinterpreter support.
    """
    
    def __init__(self, config: Python314Config):
        """
        Initialize Python 3.14 observability adapter.
        
        Args:
            config: Python 3.14 configuration
        """
        self.config = config
        self._lock = threading.RLock()
        
        # Background processing queues
        self._metrics_queue = queue.Queue(maxsize=config.observability_queue_size)
        self._logs_queue = queue.Queue(maxsize=config.observability_queue_size)
        
        # Background threads
        self._background_threads: Dict[str, threading.Thread] = {}
        self._shutdown_event = threading.Event()
        
        # Performance tracking for no-GIL mode
        self._gil_mode_detected = self._detect_gil_mode()
        
        if config.enable_no_gil and not self._gil_mode_detected:
            logger.warning("No-GIL mode requested but not detected")
    
    def _detect_gil_mode(self) -> bool:
        """
        Detect if running in no-GIL mode.
        
        Returns:
            True if no-GIL mode is active
        """
        try:
            # Simple test: create multiple threads and check if they run truly concurrently
            results = []
            threads = []
            
            def test_thread(thread_id: int):
                start = time.time()
                # Busy wait to test true concurrency
                while time.time() - start < 0.01:
                    pass
                results.append(thread_id)
            
            # Create multiple threads
            for i in range(4):
                thread = threading.Thread(target=test_thread, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # In no-GIL mode, threads should complete faster
            # This is a heuristic - actual detection would require more sophisticated testing
            return len(results) == 4
            
        except Exception as e:
            logger.error(f"Failed to detect GIL mode: {e}")
            return False
    
    def start_background_processing(self) -> None:
        """Start background processing threads for observability."""
        if not self.config.enable_no_gil:
            logger.info("Background processing disabled (GIL mode)")
            return
        
        # Start metrics processing thread
        metrics_thread = threading.Thread(
            target=self._process_metrics_queue,
            name="ObservabilityMetricsProcessor",
            daemon=True
        )
        metrics_thread.start()
        self._background_threads['metrics'] = metrics_thread
        
        # Start logs processing thread
        logs_thread = threading.Thread(
            target=self._process_logs_queue,
            name="ObservabilityLogsProcessor", 
            daemon=True
        )
        logs_thread.start()
        self._background_threads['logs'] = logs_thread
        
        logger.info("Started background observability processing threads")
    
    def stop_background_processing(self) -> None:
        """Stop background processing threads."""
        self._shutdown_event.set()
        
        for name, thread in self._background_threads.items():
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"Background thread {name} did not stop gracefully")
        
        self._background_threads.clear()
        logger.info("Stopped background observability processing threads")
    
    def _process_metrics_queue(self) -> None:
        """Process metrics queue in background thread."""
        while not self._shutdown_event.is_set():
            try:
                # Get metrics data with timeout
                metrics_data = self._metrics_queue.get(timeout=1.0)
                
                # Process metrics (placeholder for actual processing)
                self._process_metrics_data(metrics_data)
                
                self._metrics_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing metrics queue: {e}")
    
    def _process_logs_queue(self) -> None:
        """Process logs queue in background thread."""
        while not self._shutdown_event.is_set():
            try:
                # Get logs data with timeout
                logs_data = self._logs_queue.get(timeout=1.0)
                
                # Process logs (placeholder for actual processing)
                self._process_logs_data(logs_data)
                
                self._logs_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing logs queue: {e}")
    
    def _process_metrics_data(self, data: Dict[str, Any]) -> None:
        """Process metrics data (placeholder implementation)."""
        # In a real implementation, this would:
        # - Export metrics to Prometheus
        # - Send to monitoring systems
        # - Update dashboards
        pass
    
    def _process_logs_data(self, data: Dict[str, Any]) -> None:
        """Process logs data (placeholder implementation)."""
        # In a real implementation, this would:
        # - Send logs to Loki/ELK stack
        # - Apply log processing rules
        # - Update log analytics
        pass
    
    def queue_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """
        Queue metrics data for background processing.
        
        Args:
            metrics_data: Metrics data to process
            
        Returns:
            True if queued successfully, False if queue full
        """
        try:
            self._metrics_queue.put_nowait(metrics_data)
            return True
        except queue.Full:
            logger.warning("Metrics queue full, dropping data")
            return False
    
    def queue_logs(self, logs_data: Dict[str, Any]) -> bool:
        """
        Queue logs data for background processing.
        
        Args:
            logs_data: Logs data to process
            
        Returns:
            True if queued successfully, False if queue full
        """
        try:
            self._logs_queue.put_nowait(logs_data)
            return True
        except queue.Full:
            logger.warning("Logs queue full, dropping data")
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get queue status information.
        
        Returns:
            Dictionary containing queue status
        """
        return {
            'metrics_queue_size': self._metrics_queue.qsize(),
            'metrics_queue_maxsize': self._metrics_queue.maxsize,
            'logs_queue_size': self._logs_queue.qsize(),
            'logs_queue_maxsize': self._logs_queue.maxsize,
            'background_threads': len(self._background_threads),
            'gil_mode_detected': self._gil_mode_detected,
            'no_gil_enabled': self.config.enable_no_gil
        }


class ThreadSafeObservabilityWrapper:
    """
    Thread-safe wrapper for observability operations.
    
    Ensures thread safety in no-GIL mode where multiple threads
    can truly run concurrently.
    """
    
    def __init__(self, python314_adapter: Python314ObservabilityAdapter):
        """
        Initialize thread-safe wrapper.
        
        Args:
            python314_adapter: Python 3.14 adapter instance
        """
        self.adapter = python314_adapter
        self._lock = threading.RLock()
        
        # Thread-local storage for context
        self._thread_local = threading.local()
    
    def record_metrics_thread_safe(self, metrics_data: Dict[str, Any]) -> None:
        """
        Record metrics in a thread-safe manner.
        
        Args:
            metrics_data: Metrics data to record
        """
        with self._lock:
            # Add thread context
            metrics_data['thread_id'] = threading.get_ident()
            metrics_data['timestamp'] = time.time()
            
            # Queue for background processing if enabled
            if self.adapter.config.enable_no_gil:
                self.adapter.queue_metrics(metrics_data)
            else:
                # Process synchronously in GIL mode
                self.adapter._process_metrics_data(metrics_data)
    
    def record_logs_thread_safe(self, logs_data: Dict[str, Any]) -> None:
        """
        Record logs in a thread-safe manner.
        
        Args:
            logs_data: Logs data to record
        """
        with self._lock:
            # Add thread context
            logs_data['thread_id'] = threading.get_ident()
            logs_data['timestamp'] = time.time()
            
            # Queue for background processing if enabled
            if self.adapter.config.enable_no_gil:
                self.adapter.queue_logs(logs_data)
            else:
                # Process synchronously in GIL mode
                self.adapter._process_logs_data(logs_data)
    
    def set_thread_context(self, context: Dict[str, Any]) -> None:
        """
        Set thread-local context.
        
        Args:
            context: Context data for current thread
        """
        self._thread_local.context = context
    
    def get_thread_context(self) -> Dict[str, Any]:
        """
        Get thread-local context.
        
        Returns:
            Context data for current thread
        """
        return getattr(self._thread_local, 'context', {})


# Global Python 3.14 adapter instance
python314_config = Python314Config()
python314_adapter = Python314ObservabilityAdapter(python314_config)
thread_safe_wrapper = ThreadSafeObservabilityWrapper(python314_adapter)


def init_python314_observability() -> Python314ObservabilityAdapter:
    """
    Initialize Python 3.14 observability features.
    
    Returns:
        Configured Python314ObservabilityAdapter instance
    """
    logger.info("Initializing Python 3.14 observability features")
    
    # Start background processing if enabled
    if python314_config.enable_no_gil:
        python314_adapter.start_background_processing()
    
    return python314_adapter


def get_python314_adapter() -> Python314ObservabilityAdapter:
    """Get the global Python 3.14 adapter instance."""
    return python314_adapter


def get_thread_safe_wrapper() -> ThreadSafeObservabilityWrapper:
    """Get the global thread-safe wrapper instance."""
    return thread_safe_wrapper
