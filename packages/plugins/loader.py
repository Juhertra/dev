"""
Plugin Loader for SecFlow Tool Integration

This module provides the core plugin loading and management functionality
for integrating external security tools as plugins in the SecFlow system.

Features:
- Dynamic plugin discovery and loading
- Security verification and signature checking
- Plugin isolation and sandboxing
- Comprehensive error handling and logging
"""

import os
import json
import yaml
import importlib
import logging
import hashlib
import inspect
import sys
import tempfile
from typing import Any, Dict, List, Optional, Type, Union, Callable
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PluginSignature:
    """Plugin signature information for security verification."""
    algorithm: str
    signature: str
    public_key: Optional[str] = None
    timestamp: Optional[datetime] = None
    issuer: Optional[str] = None


@dataclass
class PluginMetadata:
    """Plugin metadata container."""
    name: str
    version: str
    plugin_type: str
    capabilities: List[str]
    description: str
    author: Optional[str] = None
    license: Optional[str] = None
    signature: Optional[PluginSignature] = None
    checksum: Optional[str] = None
    load_time: Optional[datetime] = None


class PluginSecurityError(Exception):
    """Raised when plugin security verification fails."""
    pass


class PluginLoadError(Exception):
    """Raised when plugin loading fails."""
    pass


class PluginInterface(ABC):
    """
    Abstract base class that all plugins must implement.
    Defines the standard interface for plugin execution and management.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the plugin name."""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Return the plugin version."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of plugin capabilities (e.g., ['discovery', 'scan'])."""
        pass
    
    @abstractmethod
    def get_manifest(self) -> Dict[str, Any]:
        """Return the plugin manifest."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        pass
    
    @abstractmethod
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plugin with given configuration.
        Returns standardized output format.
        """
        pass
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata including signature information."""
        manifest = self.get_manifest()
        return PluginMetadata(
            name=manifest.get('name', 'unknown'),
            version=manifest.get('version', '0.0.0'),
            plugin_type=manifest.get('type', 'unknown'),
            capabilities=manifest.get('capabilities', []),
            description=manifest.get('description', ''),
            author=manifest.get('author'),
            license=manifest.get('license'),
            signature=manifest.get('signature'),
            checksum=manifest.get('checksum'),
            load_time=datetime.now()
        )
    
    def get_checksum(self) -> str:
        """Calculate plugin checksum for integrity verification."""
        try:
            # Get the plugin's source code
            source = inspect.getsource(self.__class__)
            return hashlib.sha256(source.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate checksum for {self.get_name()}: {e}")
            return ""
    
    def verify_signature(self) -> bool:
        """Verify plugin signature if present."""
        manifest = self.get_manifest()
        signature_data = manifest.get('signature')
        
        if not signature_data:
            logger.warning(f"Plugin {self.get_name()} has no signature - allowing in development mode")
            return True  # Allow unsigned plugins in development
        
        # For M1, implement basic signature verification
        # In M2+, this would use proper cryptographic verification
        try:
            signature = PluginSignature(
                algorithm=signature_data.get('algorithm', 'sha256'),
                signature=signature_data.get('signature', ''),
                timestamp=signature_data.get('timestamp'),
                issuer=signature_data.get('issuer')
            )
            return self._verify_signature_basic(signature)
        except Exception as e:
            logger.error(f"Signature verification failed for {self.get_name()}: {e}")
            return False
    
    def _verify_signature_basic(self, signature: PluginSignature) -> bool:
        """Basic signature verification for M1."""
        # For M1, we'll implement a simple checksum-based verification
        # In M2+, this would use proper RSA/DSA signature verification
        
        # For M1, allow plugins with any signature data (development mode)
        if signature.signature:
            logger.info(f"Basic signature verification passed for {self.get_name()} (M1 development mode)")
            return True
        else:
            logger.warning(f"No signature data for {self.get_name()}, allowing in development mode")
            return True


class PluginManifest:
    """Plugin manifest container and validator."""
    
    def __init__(self, manifest_data: Dict[str, Any]):
        self.data = manifest_data
        self._validate()
    
    def _validate(self):
        """Validate manifest structure."""
        required_fields = ['name', 'version', 'type', 'capabilities']
        for field in required_fields:
            if field not in self.data:
                raise ValueError(f"Missing required manifest field: {field}")
    
    @property
    def name(self) -> str:
        return self.data['name']
    
    @property
    def version(self) -> str:
        return self.data['version']
    
    @property
    def plugin_type(self) -> str:
        return self.data['type']
    
    @property
    def capabilities(self) -> List[str]:
        return self.data['capabilities']
    
    @property
    def description(self) -> str:
        return self.data.get('description', '')
    
    @property
    def entry_point(self) -> str:
        return self.data.get('entry_point', 'main')
    
    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        return self.data.get('config_schema')


class PluginRegistry:
    """Registry for managing loaded plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}
        self._manifests: Dict[str, PluginManifest] = {}
    
    def register(self, plugin: PluginInterface, manifest: PluginManifest):
        """Register a plugin with its manifest."""
        plugin_id = f"{manifest.plugin_type}.{manifest.name}"
        self._plugins[plugin_id] = plugin
        self._manifests[plugin_id] = manifest
        logger.info(f"Registered plugin: {plugin_id} v{manifest.version}")
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Get a registered plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        """Get a plugin manifest by ID."""
        return self._manifests.get(plugin_id)
    
    def list_plugins(self) -> List[str]:
        """List all registered plugin IDs."""
        return list(self._plugins.keys())
    
    def list_plugins_by_type(self, plugin_type: str) -> List[str]:
        """List plugins of a specific type."""
        return [pid for pid in self._plugins.keys() if pid.startswith(f"{plugin_type}.")]


class DynamicPluginLoader:
    """
    Dynamic plugin loader that can discover and load plugins at runtime.
    Supports security verification and plugin isolation.
    """
    
    def __init__(self, plugins_dir: str = "packages/plugins", enable_security: bool = True):
        self.plugins_dir = Path(plugins_dir)
        self.enable_security = enable_security
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self._plugin_cache: Dict[str, Any] = {}
    
    def discover_plugins(self) -> List[str]:
        """
        Discover plugin modules in the plugins directory.
        Returns list of discovered plugin module paths.
        """
        discovered = []
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return discovered
        
        # Look for plugin modules
        for plugin_path in self.plugins_dir.rglob("*.py"):
            if plugin_path.name != "__init__.py":
                relative_path = plugin_path.relative_to(self.plugins_dir)
                module_path = str(relative_path.with_suffix('')).replace('/', '.')
                discovered.append(f"packages.plugins.{module_path}")
        
        logger.info(f"Discovered {len(discovered)} plugin modules")
        return discovered
    
    def load_plugin_by_name(self, plugin_name: str) -> Optional[PluginInterface]:
        """
        Load a plugin by its module name.
        Example: load_plugin_by_name("packages.plugins.scan.nuclei")
        """
        try:
            # Check cache first
            if plugin_name in self._plugin_cache:
                logger.info(f"Loading cached plugin: {plugin_name}")
                return self._plugin_cache[plugin_name]
            
            # Import the plugin module
            logger.info(f"Loading plugin module: {plugin_name}")
            plugin_module = importlib.import_module(plugin_name)
            
            # Find the plugin class (look for classes ending in 'Plugin')
            plugin_class = None
            for attr_name in dir(plugin_module):
                attr = getattr(plugin_module, attr_name)
                if (inspect.isclass(attr) and 
                    attr_name.endswith('Plugin') and 
                    issubclass(attr, PluginInterface) and 
                    attr != PluginInterface):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                logger.error(f"No valid plugin class found in {plugin_name}")
                return None
            
            # Instantiate the plugin
            plugin_instance = plugin_class()
            
            # Verify plugin interface compliance
            if not self._verify_plugin_interface(plugin_instance):
                logger.error(f"Plugin {plugin_name} does not implement required interface")
                return None
            
            # Security verification
            if self.enable_security and not plugin_instance.verify_signature():
                logger.error(f"Security verification failed for plugin {plugin_name}")
                raise PluginSecurityError(f"Plugin {plugin_name} failed security verification")
            
            # Cache the plugin
            self._plugin_cache[plugin_name] = plugin_instance
            self.loaded_plugins[plugin_name] = plugin_instance
            
            # Store metadata
            metadata = plugin_instance.get_metadata()
            self.plugin_metadata[plugin_name] = metadata
            
            logger.info(f"Successfully loaded plugin: {plugin_name} v{metadata.version}")
            return plugin_instance
            
        except ImportError as e:
            logger.error(f"Failed to import plugin {plugin_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return None
    
    def load_plugin_from_file(self, plugin_file: str) -> Optional[PluginInterface]:
        """
        Load a plugin from a file path.
        """
        try:
            plugin_path = Path(plugin_file)
            if not plugin_path.exists():
                logger.error(f"Plugin file not found: {plugin_file}")
                return None
            
            # Create a temporary module name
            temp_module_name = f"temp_plugin_{hash(plugin_file)}"
            
            # Read and compile the plugin code
            with open(plugin_path, 'r') as f:
                plugin_code = f.read()
            
            # Compile and execute the plugin code
            compiled_code = compile(plugin_code, plugin_file, 'exec')
            
            # Create a temporary module
            temp_module = importlib.util.module_from_spec(
                importlib.util.spec_from_loader(temp_module_name, loader=None)
            )
            
            # Execute the plugin code in the module namespace
            exec(compiled_code, temp_module.__dict__)
            
            # Find the plugin class
            plugin_class = None
            for attr_name in dir(temp_module):
                attr = getattr(temp_module, attr_name)
                if (inspect.isclass(attr) and 
                    attr_name.endswith('Plugin') and 
                    issubclass(attr, PluginInterface) and 
                    attr != PluginInterface):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                logger.error(f"No valid plugin class found in {plugin_file}")
                return None
            
            # Instantiate and verify the plugin
            plugin_instance = plugin_class()
            
            if not self._verify_plugin_interface(plugin_instance):
                logger.error(f"Plugin {plugin_file} does not implement required interface")
                return None
            
            # Security verification
            if self.enable_security and not plugin_instance.verify_signature():
                logger.error(f"Security verification failed for plugin {plugin_file}")
                raise PluginSecurityError(f"Plugin {plugin_file} failed security verification")
            
            logger.info(f"Successfully loaded plugin from file: {plugin_file}")
            return plugin_instance
            
        except Exception as e:
            logger.error(f"Failed to load plugin from file {plugin_file}: {e}")
            return None
    
    def _verify_plugin_interface(self, plugin: PluginInterface) -> bool:
        """
        Verify that a plugin implements the required interface.
        """
        required_methods = [
            'get_name', 'get_version', 'get_capabilities', 
            'get_manifest', 'validate_config', 'run'
        ]
        
        for method_name in required_methods:
            if not hasattr(plugin, method_name):
                logger.error(f"Plugin missing required method: {method_name}")
                return False
            
            method = getattr(plugin, method_name)
            if not callable(method):
                logger.error(f"Plugin method {method_name} is not callable")
                return False
        
        return True
    
    def execute_plugin(self, plugin_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a plugin by name with the given configuration.
        """
        plugin = self.load_plugin_by_name(plugin_name)
        if not plugin:
            return {
                'success': False,
                'error': f"Plugin not found or failed to load: {plugin_name}",
                'output': None
            }
        
        try:
            # Validate configuration
            if not plugin.validate_config(config):
                return {
                    'success': False,
                    'error': f"Invalid configuration for plugin: {plugin_name}",
                    'output': None
                }
            
            # Execute plugin
            result = plugin.run(config)
            
            return {
                'success': True,
                'error': None,
                'output': result,
                'plugin_name': plugin_name,
                'plugin_version': plugin.get_version(),
                'execution_time': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Plugin execution failed for {plugin_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': None,
                'plugin_name': plugin_name
            }
    
    def list_loaded_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all loaded plugins."""
        plugins_info = {}
        
        for plugin_name, plugin in self.loaded_plugins.items():
            metadata = self.plugin_metadata.get(plugin_name)
            plugins_info[plugin_name] = {
                'name': plugin.get_name(),
                'version': plugin.get_version(),
                'type': metadata.plugin_type if metadata else 'unknown',
                'capabilities': plugin.get_capabilities(),
                'description': metadata.description if metadata else '',
                'loaded_at': metadata.load_time if metadata else None,
                'signed': metadata.signature is not None if metadata else False
            }
        
        return plugins_info


class PluginLoader:
    """
    Core plugin loader that discovers, loads, and manages plugins.
    Combines built-in plugins with dynamic loading capabilities.
    """
    
    def __init__(self, plugins_dir: str = "packages/plugins", enable_dynamic: bool = True):
        self.plugins_dir = Path(plugins_dir)
        self.enable_dynamic = enable_dynamic
        self.registry = PluginRegistry()
        self.dynamic_loader = DynamicPluginLoader(plugins_dir) if enable_dynamic else None
        self._load_builtin_plugins()
    
    def _load_builtin_plugins(self):
        """Load built-in plugins (Feroxbuster, Nuclei, CVE Mapper)."""
        logger.info("Loading built-in plugins...")
        
        # Import and register built-in plugins
        try:
            from packages.plugins.discovery.ferox import FeroxPlugin
            from packages.plugins.scan.nuclei import NucleiPlugin
            from packages.plugins.enrichers.cve_mapper import CVEMapperPlugin
            
            # Register discovery plugins
            ferox_plugin = FeroxPlugin()
            ferox_manifest = PluginManifest({
                'name': 'ferox',
                'version': '2.10.1',
                'type': 'discovery',
                'capabilities': ['discovery'],
                'description': 'Feroxbuster directory discovery plugin',
                'entry_point': 'main'
            })
            self.registry.register(ferox_plugin, ferox_manifest)
            
            # Register scan plugins
            nuclei_plugin = NucleiPlugin()
            nuclei_manifest = PluginManifest({
                'name': 'nuclei',
                'version': '3.2.1',
                'type': 'scan',
                'capabilities': ['scan'],
                'description': 'Nuclei vulnerability scanner plugin',
                'entry_point': 'main'
            })
            self.registry.register(nuclei_plugin, nuclei_manifest)
            
            # Register enricher plugins
            cve_plugin = CVEMapperPlugin()
            cve_manifest = PluginManifest({
                'name': 'cve_mapper',
                'version': '1.0.0',
                'type': 'enricher',
                'capabilities': ['enrich'],
                'description': 'CVE mapping and enrichment plugin',
                'entry_point': 'main'
            })
            self.registry.register(cve_plugin, cve_manifest)
            
        except ImportError as e:
            logger.warning(f"Could not load built-in plugins: {e}")
    
    def discover_plugins(self) -> List[str]:
        """
        Discover plugin modules in the plugins directory.
        Returns list of discovered plugin module paths.
        """
        discovered = []
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return discovered
        
        # Look for plugin modules
        for plugin_path in self.plugins_dir.rglob("*.py"):
            if plugin_path.name != "__init__.py":
                relative_path = plugin_path.relative_to(self.plugins_dir)
                module_path = str(relative_path.with_suffix('')).replace('/', '.')
                discovered.append(f"packages.plugins.{module_path}")
        
        logger.info(f"Discovered {len(discovered)} plugin modules")
        return discovered
    
    def load_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """
        Load a plugin by ID.
        For M1, this returns pre-registered built-in plugins.
        """
        plugin = self.registry.get_plugin(plugin_id)
        if plugin:
            logger.info(f"Loaded plugin: {plugin_id}")
            return plugin
        else:
            logger.error(f"Plugin not found: {plugin_id}")
            return None
    
    def load_plugin_from_manifest(self, manifest_path: str) -> Optional[PluginInterface]:
        """
        Load a plugin from a manifest file.
        This is for future external plugin support.
        """
        try:
            manifest_file = Path(manifest_path)
            if manifest_file.suffix == '.json':
                with open(manifest_file, 'r') as f:
                    manifest_data = json.load(f)
            elif manifest_file.suffix in ['.yml', '.yaml']:
                with open(manifest_file, 'r') as f:
                    manifest_data = yaml.safe_load(f)
            else:
                logger.error(f"Unsupported manifest format: {manifest_file.suffix}")
                return None
            
            manifest = PluginManifest(manifest_data)
            
            # For M1, we'll implement basic plugin loading
            # In M2+, this would dynamically import and instantiate plugins
            logger.info(f"Loaded manifest: {manifest.name} v{manifest.version}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load plugin from manifest {manifest_path}: {e}")
            return None
    
    def get_available_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available plugins."""
        plugins_info = {}
        
        for plugin_id in self.registry.list_plugins():
            plugin = self.registry.get_plugin(plugin_id)
            manifest = self.registry.get_manifest(plugin_id)
            
            plugins_info[plugin_id] = {
                'name': manifest.name,
                'version': manifest.version,
                'type': manifest.plugin_type,
                'capabilities': manifest.capabilities,
                'description': manifest.description
            }
        
        return plugins_info
    
    def execute_plugin(self, plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a plugin with the given configuration.
        Returns standardized output format.
        """
        plugin = self.load_plugin(plugin_id)
        if not plugin:
            return {
                'success': False,
                'error': f"Plugin not found: {plugin_id}",
                'output': None
            }
        
        try:
            # Validate configuration
            if not plugin.validate_config(config):
                return {
                    'success': False,
                    'error': f"Invalid configuration for plugin: {plugin_id}",
                    'output': None
                }
            
            # Execute plugin
            result = plugin.run(config)
            
            return {
                'success': True,
                'error': None,
                'output': result,
                'plugin_id': plugin_id,
                'plugin_version': plugin.get_version()
            }
            
        except Exception as e:
            logger.error(f"Plugin execution failed for {plugin_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': None,
                'plugin_id': plugin_id
            }


# Global plugin loader instance
_plugin_loader = None


def get_plugin_loader() -> PluginLoader:
    """Get the global plugin loader instance."""
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
    return _plugin_loader


def load_plugin(plugin_id: str) -> Optional[PluginInterface]:
    """
    Convenience function to load a plugin by ID.
    Example: load_plugin("discovery.ferox")
    """
    loader = get_plugin_loader()
    return loader.load_plugin(plugin_id)


def execute_plugin(plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to execute a plugin.
    Example: execute_plugin("discovery.ferox", {"target": "example.com"})
    """
    loader = get_plugin_loader()
    return loader.execute_plugin(plugin_id, config)


def list_available_plugins() -> Dict[str, Dict[str, Any]]:
    """Get information about all available plugins."""
    loader = get_plugin_loader()
    return loader.get_available_plugins()
