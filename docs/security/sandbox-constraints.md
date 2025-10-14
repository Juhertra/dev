# SecFlow Plugin Sandbox Constraints

## Security Model Compliance

Based on `docs/architecture/16-security-model.md`, all plugin executions must enforce:

### Resource Limits
- **CPU**: Maximum 5 seconds per plugin execution (configurable per plugin)
- **Memory**: Maximum 256MB per plugin (configurable per plugin)  
- **Disk**: Read-only filesystem with explicit allowlist
- **Network**: Disabled by default, explicit allowlist required

### Isolation Mechanisms
- **Namespaces**: PID, NET, MNT isolation
- **Seccomp Filters**: Syscall restriction
- **cgroups v2**: CPU/memory enforcement
- **No-root UID**: Privilege dropping
- **AppArmor**: File access control
- **Read-only FS**: Prevents persistence

### Policy Enforcement
```yaml
# plugins/plugin_policy.yaml
default: deny
allow:
  - name: example_safe_plugin
    fs_allowlist: ["data/"]          # Filesystem access
    network: false                   # Network access
    cpu_seconds: 5                   # CPU time limit
    memory_mb: 256                   # Memory limit
```

### Container Execution Example
```bash
docker run --rm --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --read-only -m 256m --cpus=1 \
  --tmpfs /tmp:noexec,nosuid,size=100m \
  SecFlow-runner:latest plugin-executor
```

### Security Validation
- All plugins validated by `tools/plugin_security_audit.py`
- Mandatory policy keys: name, fs_allowlist, network, cpu_seconds, memory_mb
- Runtime enforcement via container orchestration
- Audit logging of all policy decisions

## Compliance Framework
- **NIST SP 800-53**: Access control, auditing, system protection
- **ISO/IEC 27001**: Information security management  
- **OWASP SAMM**: Secure software development lifecycle
- **MITRE ATT&CK**: Mapping detection behaviors
- **GDPR Art. 32**: Data confidentiality and integrity
