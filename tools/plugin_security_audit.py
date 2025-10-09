import pathlib

import yaml

pol = yaml.safe_load(pathlib.Path("plugins/plugin_policy.yaml").read_text())
assert pol.get("default") in ("deny","allow")
print("Policy parsed. default:", pol["default"])

# Validate mandatory policy keys for allowed plugins
if "allow" in pol:
    for plugin in pol["allow"]:
        assert "name" in plugin, f"Plugin missing 'name' key: {plugin}"
        assert "fs_allowlist" in plugin, f"Plugin {plugin.get('name', 'unknown')} missing 'fs_allowlist' key"
        assert "network" in plugin, f"Plugin {plugin.get('name', 'unknown')} missing 'network' key"
        assert "cpu_seconds" in plugin, f"Plugin {plugin.get('name', 'unknown')} missing 'cpu_seconds' key"
        assert "memory_mb" in plugin, f"Plugin {plugin.get('name', 'unknown')} missing 'memory_mb' key"
        print(f"Plugin '{plugin['name']}' policy validated")

print("All mandatory policy keys present")
