import subprocess
import sys


def sh(cmd): return subprocess.check_output(cmd, shell=True, text=True).strip()

subprocess.check_call("mkdocs build -q", shell=True)
fences = int(sh("rg -N --no-line-number '```mermaid' docs --glob '*.md' | wc -l | tr -d ' '") or "0")
divs   = int(sh("rg -N --no-line-number '<div class=\"mermaid\">' -g 'site/**/*.html' | wc -l | tr -d ' '") or "0")

print(f"Mermaid parity: source={fences} rendered={divs}")
sys.exit(0 if fences == divs else 1)
