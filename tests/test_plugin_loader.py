"""
Comprehensive test suite for the SecFlow Plugin Loader system.

This module tests:
- Dynamic plugin loading
- Security verification
- Plugin interface compliance
- Error handling
- End-to-end plugin execution
"""

import pytest
import tempfile
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Add packages to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.plugins.loader import (
    PluginInterface, PluginLoader, DynamicPluginLoader,
    PluginSecurityError, PluginLoadError, PluginSignature, PluginMetadata
)


class MockPlugin(PluginInterface):
    """Test plugin implementation for unit tests."""
    
    def __init__(self, name: str = "test", version: str = "1.0.0", signed: bool = True):
        self.name = name
        self.version = version
        self.signed = signed
        self.capabilities = ["test"]
    
    def get_name(self) -> str:
        return self.name
    
    def get_version(self) -> str:
        return self.version
    
    def get_capabilities(self) -> list:
        return self.capabilities
    
    def get_manifest(self) -> Dict[str, Any]:
        manifest = {
            "name": self.name,
            "version": self.version,
            "type": "test",
            "capabilities": self.capabilities,
            "description": "Test plugin",
            "author": "Test Author",
            "license": "MIT"
        }
        
        if self.signed:
            manifest["signature"] = {
                "algorithm": "sha256",
                "signature": "test_signature_hash",
                "timestamp": "2025-10-14T00:00:00Z",
                "issuer": "Test"
            }
        
        return manifest
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return "target" in config
    
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "plugin": self.name,
            "type": "test",
            "results": {"test": "success"},
            "metadata": {"version": self.version}
        }
    
    def verify_signature(self) -> bool:
        return self.signed


class InvalidPlugin:
    """Invalid plugin that doesn't implement PluginInterface."""
    
    def run(self, config):
        return {"test": "invalid"}


class TestDynamicPluginLoader:
    """Test cases for DynamicPluginLoader."""
    
    def test_discover_plugins(self):
        """Test plugin discovery functionality."""
        loader = DynamicPluginLoader()
        discovered = loader.discover_plugins()
        
        # Should discover existing plugins
        assert isinstance(discovered, list)
        assert len(discovered) > 0
        
        # Should include our test plugins
        expected_plugins = [
            "packages.plugins.discovery.ferox",
            "packages.plugins.scan.nuclei",
            "packages.plugins.enrichers.cve_mapper"
        ]
        
        for expected in expected_plugins:
            assert expected in discovered
    
    def test_load_valid_plugin(self):
        """Test loading a valid plugin."""
        loader = DynamicPluginLoader(enable_security=False)  # Disable security for test
        
        # Create a temporary plugin file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            plugin_code = '''
from packages.plugins.loader import PluginInterface

class MockPlugin(PluginInterface):
    def get_name(self): return "test"
    def get_version(self): return "1.0.0"
    def get_capabilities(self): return ["test"]
    def get_manifest(self): return {"name": "test", "version": "1.0.0", "type": "test", "capabilities": ["test"], "description": "Test"}
    def validate_config(self, config): return True
    def run(self, config): return {"test": "success"}
'''
            f.write(plugin_code)
            f.flush()
            
            try:
                plugin = loader.load_plugin_from_file(f.name)
                assert plugin is not None
                assert plugin.get_name() == "test"
                assert plugin.get_version() == "1.0.0"
            finally:
                os.unlink(f.name)
    
    def test_load_invalid_plugin(self):
        """Test loading an invalid plugin."""
        loader = DynamicPluginLoader(enable_security=False)
        
        # Create a plugin file without required interface
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            plugin_code = '''
class BadPlugin:
    def run(self, config):
        return {"test": "bad"}
'''
            f.write(plugin_code)
            f.flush()
            
            try:
                plugin = loader.load_plugin_from_file(f.name)
                assert plugin is None  # Should fail to load
            finally:
                os.unlink(f.name)
    
    def test_security_verification_enabled(self):
        """Test security verification when enabled."""
        loader = DynamicPluginLoader(enable_security=True)
        
        # Test with signed plugin
        signed_plugin = MockPlugin(signed=True)
        assert signed_plugin.verify_signature() is True
        
        # Test with unsigned plugin
        unsigned_plugin = MockPlugin(signed=False)
        assert unsigned_plugin.verify_signature() is True  # Should allow in dev mode
    
    def test_security_verification_disabled(self):
        """Test security verification when disabled."""
        loader = DynamicPluginLoader(enable_security=False)
        
        # Should allow any plugin when security is disabled
        unsigned_plugin = MockPlugin(signed=False)
        assert unsigned_plugin.verify_signature() is True
    
    def test_plugin_interface_verification(self):
        """Test plugin interface verification."""
        loader = DynamicPluginLoader()
        
        # Valid plugin should pass
        valid_plugin = MockPlugin()
        assert loader._verify_plugin_interface(valid_plugin) is True
        
        # Invalid plugin should fail
        invalid_plugin = InvalidPlugin()
        assert loader._verify_plugin_interface(invalid_plugin) is False
    
    def test_execute_plugin_success(self):
        """Test successful plugin execution."""
        loader = DynamicPluginLoader(enable_security=False)
        
        # Mock a plugin
        plugin = MockPlugin()
        loader.loaded_plugins["test.plugin"] = plugin
        
        config = {"target": "test.com"}
        result = loader.execute_plugin("test.plugin", config)
        
        assert result['success'] is True
        assert result['error'] is None
        assert result['output']['plugin'] == "test"
    
    def test_execute_plugin_invalid_config(self):
        """Test plugin execution with invalid configuration."""
        loader = DynamicPluginLoader(enable_security=False)
        
        plugin = MockPlugin()
        loader.loaded_plugins["test.plugin"] = plugin
        
        config = {}  # Missing required 'target' field
        result = loader.execute_plugin("test.plugin", config)
        
        assert result['success'] is False
        assert "Invalid configuration" in result['error']
    
    def test_execute_plugin_not_found(self):
        """Test executing a non-existent plugin."""
        loader = DynamicPluginLoader()
        
        result = loader.execute_plugin("nonexistent.plugin", {"target": "test"})
        
        assert result['success'] is False
        assert "Plugin not found" in result['error']


class MockPluginLoader:
    """Test cases for the main PluginLoader."""
    
    def test_load_builtin_plugins(self):
        """Test loading built-in plugins."""
        loader = PluginLoader()
        
        # Should have built-in plugins registered
        plugins = loader.registry.list_plugins()
        assert len(plugins) > 0
        
        expected_plugins = ["discovery.ferox", "scan.nuclei", "enricher.cve_mapper"]
        for expected in expected_plugins:
            assert expected in plugins
    
    def test_get_available_plugins(self):
        """Test getting available plugin information."""
        loader = PluginLoader()
        
        plugins_info = loader.get_available_plugins()
        assert isinstance(plugins_info, dict)
        assert len(plugins_info) > 0
        
        # Check structure of plugin info
        for plugin_id, info in plugins_info.items():
            assert 'name' in info
            assert 'version' in info
            assert 'type' in info
            assert 'capabilities' in info
            assert 'description' in info
    
    def test_execute_builtin_plugin(self):
        """Test executing a built-in plugin."""
        loader = PluginLoader()
        
        config = {"target": "https://example.com"}
        result = loader.execute_plugin("discovery.ferox", config)
        
        assert result['success'] is True
        assert result['output']['plugin'] == "feroxbuster"
        assert 'urls' in result['output']['results']
    
    def test_dynamic_loading_integration(self):
        """Test integration with dynamic loading."""
        loader = PluginLoader(enable_dynamic=True)
        
        # Should have both built-in and dynamic capabilities
        assert loader.dynamic_loader is not None
        
        # Test discovering plugins
        discovered = loader.dynamic_loader.discover_plugins()
        assert len(discovered) > 0


class MockPluginSecurity:
    """Test cases for plugin security features."""
    
    def test_plugin_signature_creation(self):
        """Test PluginSignature creation."""
        signature = PluginSignature(
            algorithm="sha256",
            signature="test_hash",
            public_key="test_key",
            timestamp=None,
            issuer="Test"
        )
        
        assert signature.algorithm == "sha256"
        assert signature.signature == "test_hash"
        assert signature.public_key == "test_key"
        assert signature.issuer == "Test"
    
    def test_plugin_metadata_creation(self):
        """Test PluginMetadata creation."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            plugin_type="test",
            capabilities=["test"],
            description="Test plugin",
            author="Test Author",
            license="MIT",
            signature=None,
            checksum="test_checksum",
            load_time=None
        )
        
        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.plugin_type == "test"
        assert metadata.capabilities == ["test"]
        assert metadata.checksum == "test_checksum"
    
    def test_plugin_checksum_calculation(self):
        """Test plugin checksum calculation."""
        plugin = MockPlugin()
        checksum = plugin.get_checksum()
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex length
    
    def test_security_error_handling(self):
        """Test security error handling."""
        with pytest.raises(PluginSecurityError):
            raise PluginSecurityError("Test security error")
        
        with pytest.raises(PluginLoadError):
            raise PluginLoadError("Test load error")


class MockPluginIntegration:
    """Integration tests for the complete plugin system."""
    
    def test_end_to_end_plugin_execution(self):
        """Test complete end-to-end plugin execution."""
        loader = PluginLoader()
        
        # Test discovery phase
        discovery_result = loader.execute_plugin("discovery.ferox", {
            "target": "https://example.com"
        })
        assert discovery_result['success'] is True
        
        # Test scanning phase
        scan_result = loader.execute_plugin("scan.nuclei", {
            "targets": ["https://example.com"]
        })
        assert scan_result['success'] is True
        
        # Test enrichment phase
        findings = scan_result['output']['results']['findings']
        enrichment_result = loader.execute_plugin("enricher.cve_mapper", {
            "findings": findings
        })
        assert enrichment_result['success'] is True
    
    def test_plugin_error_recovery(self):
        """Test plugin error recovery and handling."""
        loader = PluginLoader()
        
        # Test with invalid plugin name
        result = loader.execute_plugin("invalid.plugin", {"target": "test"})
        assert result['success'] is False
        assert result['error'] is not None
        
        # Test with invalid configuration
        result = loader.execute_plugin("discovery.ferox", {})
        assert result['success'] is False
        assert "Invalid configuration" in result['error']
    
    def test_plugin_caching(self):
        """Test plugin caching functionality."""
        loader = DynamicPluginLoader()
        
        # Load plugin twice - should use cache second time
        plugin1 = loader.load_plugin_by_name("packages.plugins.discovery.ferox")
        plugin2 = loader.load_plugin_by_name("packages.plugins.discovery.ferox")
        
        assert plugin1 is not None
        assert plugin2 is not None
        assert plugin1 is plugin2  # Should be same instance from cache


# Performance and stress tests
class MockPluginPerformance:
    """Performance tests for the plugin system."""
    
    def test_plugin_loading_performance(self):
        """Test plugin loading performance."""
        import time
        
        loader = DynamicPluginLoader()
        
        start_time = time.time()
        plugin = loader.load_plugin_by_name("packages.plugins.discovery.ferox")
        load_time = time.time() - start_time
        
        assert plugin is not None
        assert load_time < 1.0  # Should load in under 1 second
    
    def test_plugin_execution_performance(self):
        """Test plugin execution performance."""
        import time
        
        loader = PluginLoader()
        
        start_time = time.time()
        result = loader.execute_plugin("discovery.ferox", {
            "target": "https://example.com"
        })
        execution_time = time.time() - start_time
        
        assert result['success'] is True
        assert execution_time < 5.0  # Should execute in under 5 seconds


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
