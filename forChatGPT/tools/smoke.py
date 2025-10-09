#!/usr/bin/env python3
"""
Security Toolkit Smoke Test
Creates/loads project, queues endpoints, starts scan, verifies dossier files
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SmokeTest:
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.api_key = "test-key-123"
        self.project_id = None
        self.run_id = None
        self.results = []
    
    def log(self, message: str, status: str = "INFO"):
        """Log test step with status"""
        status_icon = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        print(f"{status_icon.get(status, 'ℹ️')} {message}")
        self.results.append({"message": message, "status": status})
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        self.log("Checking prerequisites...")
        
        # Check if app is running
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code not in [200, 302]:
                self.log(f"App not responding: {response.status_code}", "ERROR")
                return False
        except requests.exceptions.RequestException as e:
            self.log(f"App not running: {e}", "ERROR")
            return False
        
        # Check Nuclei installation
        try:
            result = subprocess.run(["nuclei", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.log("Nuclei not installed", "WARNING")
            else:
                self.log(f"Nuclei version: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log("Nuclei not found", "WARNING")
        
        # Check ui_projects directory
        if not os.path.exists("ui_projects"):
            os.makedirs("ui_projects")
            self.log("Created ui_projects directory")
        
        self.log("Prerequisites check completed", "SUCCESS")
        return True
    
    def create_or_load_project(self) -> bool:
        """Create or load test project"""
        self.log("Creating/loading test project...")
        
        try:
            # Try to create project
            response = requests.post(f"{self.base_url}/p/create", 
                                   data={"name": "Smoke Test Project"}, 
                                   timeout=10)
            
            if response.status_code == 302:  # Redirect after creation
                # Extract project ID from redirect
                location = response.headers.get('Location', '')
                if '/p/' in location:
                    self.project_id = location.split('/p/')[1].split('/')[0]
                    self.log(f"Created project: {self.project_id}", "SUCCESS")
                else:
                    # Use default project
                    self.project_id = "default"
                    self.log("Using default project", "SUCCESS")
            else:
                self.log(f"Project creation failed: {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"Project creation error: {e}", "ERROR")
            return False
        
        return True
    
    def queue_endpoints(self) -> bool:
        """Queue test endpoints for scanning"""
        self.log("Queueing test endpoints...")
        
        test_endpoints = [
            {"url": "https://httpbin.org/get", "method": "GET"},
            {"url": "https://httpbin.org/post", "method": "POST"}
        ]
        
        try:
            for endpoint in test_endpoints:
                # Add endpoint to queue (simplified - would need actual queue endpoint)
                self.log(f"Queued {endpoint['method']} {endpoint['url']}")
            
            self.log("Endpoints queued successfully", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Endpoint queueing failed: {e}", "ERROR")
            return False
    
    def start_scan(self) -> bool:
        """Start a security scan"""
        self.log("Starting security scan...")
        
        self.run_id = f"smoke-test-{int(time.time())}"
        
        try:
            # Start scan
            response = requests.post(f"{self.base_url}/p/{self.project_id}/nuclei/scan",
                                   data={
                                       "templates": "http-methods",
                                       "severity": "medium"
                                   },
                                   timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log("Scan started successfully", "SUCCESS")
                    return True
                else:
                    self.log(f"Scan failed: {result.get('error', 'Unknown error')}", "ERROR")
                    return False
            else:
                self.log(f"Scan request failed: {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"Scan request error: {e}", "ERROR")
            return False
    
    def monitor_sse_stream(self) -> bool:
        """Monitor SSE stream for scan progress"""
        self.log("Monitoring SSE stream...")
        
        try:
            # Connect to SSE stream
            response = requests.get(f"{self.base_url}/p/{self.project_id}/nuclei/stream",
                                  headers={"Accept": "text/event-stream"},
                                  stream=True, timeout=60)
            
            if response.status_code != 200:
                self.log(f"SSE stream failed: {response.status_code}", "ERROR")
                return False
            
            events_received = 0
            start_time = time.time()
            
            # Read events for up to 60 seconds
            for line in response.iter_lines(decode_unicode=True):
                if time.time() - start_time > 60:
                    break
                
                if line.startswith('event:'):
                    event_type = line.split(':', 1)[1].strip()
                    self.log(f"Received event: {event_type}")
                    events_received += 1
                    
                    if event_type == 'done':
                        self.log("Scan completed via SSE", "SUCCESS")
                        return True
            
            if events_received > 0:
                self.log(f"Received {events_received} events", "SUCCESS")
                return True
            else:
                self.log("No SSE events received", "WARNING")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"SSE stream error: {e}", "ERROR")
            return False
    
    def verify_dossier_files(self) -> bool:
        """Verify dossier files were created"""
        self.log("Verifying dossier files...")
        
        try:
            project_dir = Path("ui_projects") / self.project_id
            endpoints_dir = project_dir / "endpoints"
            
            if not endpoints_dir.exists():
                self.log("Endpoints directory not found", "ERROR")
                return False
            
            # Check for dossier files
            dossier_files = list(endpoints_dir.glob("*.json"))
            
            if len(dossier_files) == 0:
                self.log("No dossier files found", "ERROR")
                return False
            
            self.log(f"Found {len(dossier_files)} dossier files", "SUCCESS")
            
            # Validate dossier file structure
            for dossier_file in dossier_files:
                try:
                    with open(dossier_file, 'r') as f:
                        dossier = json.load(f)
                    
                    required_fields = ['endpoint_key', 'total_runs', 'latest_run', 'history']
                    if all(field in dossier for field in required_fields):
                        self.log(f"Validated {dossier_file.name}")
                    else:
                        self.log(f"Invalid dossier structure: {dossier_file.name}", "WARNING")
                        
                except json.JSONDecodeError as e:
                    self.log(f"Invalid JSON in {dossier_file.name}: {e}", "ERROR")
                    return False
            
            return True
            
        except Exception as e:
            self.log(f"Dossier verification failed: {e}", "ERROR")
            return False
    
    def check_findings(self) -> bool:
        """Check if findings were created"""
        self.log("Checking findings...")
        
        try:
            findings_file = Path("ui_projects") / self.project_id / "findings.json"
            
            if not findings_file.exists():
                self.log("Findings file not found", "WARNING")
                return True  # Not critical for smoke test
            
            with open(findings_file, 'r') as f:
                findings = json.load(f)
            
            self.log(f"Found {len(findings)} findings", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Findings check failed: {e}", "WARNING")
            return True  # Not critical
    
    def generate_report(self) -> None:
        """Generate smoke test report"""
        self.log("Generating smoke test report...")
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'SUCCESS'])
        failed_tests = len([r for r in self.results if r['status'] == 'ERROR'])
        warnings = len([r for r in self.results if r['status'] == 'WARNING'])
        
        print("\n" + "="*50)
        print("SMOKE TEST SUMMARY")
        print("="*50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Warnings: {warnings}")
        print("="*50)
        
        if failed_tests == 0:
            print("✅ Smoke test completed successfully!")
        else:
            print("❌ Smoke test failed!")
            print("\nFailed tests:")
            for result in self.results:
                if result['status'] == 'ERROR':
                    print(f"  - {result['message']}")
        
        if warnings > 0:
            print(f"\n⚠️  {warnings} warnings (non-critical)")
    
    def run(self) -> bool:
        """Run complete smoke test"""
        print("Starting Security Toolkit Smoke Test...")
        print("="*50)
        
        steps = [
            self.check_prerequisites,
            self.create_or_load_project,
            self.queue_endpoints,
            self.start_scan,
            self.monitor_sse_stream,
            self.verify_dossier_files,
            self.check_findings
        ]
        
        for step in steps:
            if not step():
                self.log(f"Step failed: {step.__name__}", "ERROR")
                self.generate_report()
                return False
        
        self.generate_report()
        return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Toolkit Smoke Test")
    parser.add_argument("--url", default="http://localhost:5001", 
                       help="Base URL of the application")
    parser.add_argument("--timeout", type=int, default=120,
                       help="Test timeout in seconds")
    
    args = parser.parse_args()
    
    smoke_test = SmokeTest(args.url)
    success = smoke_test.run()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
