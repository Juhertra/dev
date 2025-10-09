import pathlib

import yaml

pol = yaml.safe_load(pathlib.Path("plugins/plugin_policy.yaml").read_text())
assert pol.get("default") in ("deny","allow")
print("Policy parsed. default:", pol["default"])
