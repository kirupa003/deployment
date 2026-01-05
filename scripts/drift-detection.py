#!/usr/bin/env python3
"""
Configuration Drift Detection Script
Detects and reports configuration drift in VPN infrastructure
"""

import os
import sys
import yaml
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DriftDetector:
    """Detects configuration drift in VPN infrastructure"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.drift_reports_dir = self.base_path / "drift-reports"
        self.drift_reports_dir.mkdir(exist_ok=True)
        
    def detect_drift(self, inventory: str = "inventories/production", 
                    limit: str = "vpn_servers") -> Dict[str, Any]:
        """Detect configuration drift using Ansible check mode"""
        logger.info(f"Starting drift detection for {limit} in {inventory}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.drift_reports_dir / f"drift_report_{timestamp}.json"
        
        # Run Ansible playbook in check mode with diff
        cmd = [
            "ansible-playbook",
            "playbooks/multi-protocol-deployment.yml",
            "--inventory", inventory,
            "--limit", limit,
            "--check",
            "--diff",
            "--extra-vars", "drift_detection=true"
        ]
        
        try:
            logger.info("Running Ansible drift detection...")
            result = subprocess.run(
                cmd,
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            drift_data = {
                "timestamp": timestamp,
                "inventory": inventory,
                "limit": limit,
                "command": " ".join(cmd),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "drift_detected": result.returncode != 0,
                "changes": self._parse_ansible_diff(result.stdout)
            }
            
            # Save drift report
            with open(report_file, 'w') as f:
                json.dump(drift_data, f, indent=2)
            
            logger.info(f"Drift detection completed. Report saved: {report_file}")
            
            return drift_data
            
        except subprocess.TimeoutExpired:
            logger.error("Drift detection timed out")
            return {
                "timestamp": timestamp,
                "error": "Timeout during drift detection",
                "drift_detected": True
            }
        except Exception as e:
            logger.error(f"Error during drift detection: {e}")
            return {
                "timestamp": timestamp,
                "error": str(e),
                "drift_detected": True
            }
    
    def _parse_ansible_diff(self, output: str) -> List[Dict[str, Any]]:
        """Parse Ansible diff output to extract changes"""
        changes = []
        lines = output.split('\n')
        
        current_task = None
        current_host = None
        in_diff = False
        diff_content = []
        
        for line in lines:
            # Detect task start
            if line.startswith("TASK ["):
                current_task = line.strip()
                in_diff = False
                
            # Detect host
            elif line.startswith("changed: [") or line.startswith("ok: ["):
                current_host = line.split('[')[1].split(']')[0]
                
            # Detect diff start
            elif "--- before" in line or "--- " in line:
                in_diff = True
                diff_content = [line]
                
            # Collect diff content
            elif in_diff:
                diff_content.append(line)
                
                # Detect diff end (empty line or next task)
                if line.strip() == "" or line.startswith("TASK ["):
                    if len(diff_content) > 1:
                        changes.append({
                            "task": current_task,
                            "host": current_host,
                            "diff": '\n'.join(diff_content[:-1])
                        })
                    diff_content = []
                    in_diff = False
        
        return changes
    
    def generate_drift_summary(self, drift_data: Dict[str, Any]) -> str:
        """Generate human-readable drift summary"""
        summary = f"""
Configuration Drift Detection Report
===================================

Timestamp: {drift_data['timestamp']}
Target: {drift_data.get('limit', 'Unknown')}
Inventory: {drift_data.get('inventory', 'Unknown')}

Drift Status: {'DETECTED' if drift_data.get('drift_detected', False) else 'NO DRIFT'}

"""
        
        if drift_data.get('error'):
            summary += f"Error: {drift_data['error']}\n"
            return summary
        
        changes = drift_data.get('changes', [])
        
        if changes:
            summary += f"Changes Detected: {len(changes)}\n\n"
            
            # Group changes by host
            changes_by_host = {}
            for change in changes:
                host = change.get('host', 'Unknown')
                if host not in changes_by_host:
                    changes_by_host[host] = []
                changes_by_host[host].append(change)
            
            for host, host_changes in changes_by_host.items():
                summary += f"Host: {host}\n"
                summary += "-" * (len(host) + 6) + "\n"
                
                for change in host_changes:
                    task = change.get('task', 'Unknown task')
                    summary += f"  Task: {task}\n"
                    
                    # Show abbreviated diff
                    diff = change.get('diff', '')
                    if diff:
                        diff_lines = diff.split('\n')[:10]  # First 10 lines
                        summary += "  Changes:\n"
                        for diff_line in diff_lines:
                            if diff_line.strip():
                                summary += f"    {diff_line}\n"
                        if len(diff.split('\n')) > 10:
                            summary += "    ... (truncated)\n"
                    summary += "\n"
        else:
            summary += "No configuration changes detected.\n"
        
        return summary
    
    def remediate_drift(self, drift_data: Dict[str, Any], 
                       auto_remediate: bool = False) -> bool:
        """Remediate detected configuration drift"""
        if not drift_data.get('drift_detected', False):
            logger.info("No drift detected, no remediation needed")
            return True
        
        changes = drift_data.get('changes', [])
        if not changes:
            logger.info("No specific changes identified for remediation")
            return True
        
        logger.info(f"Remediating {len(changes)} configuration changes...")
        
        if not auto_remediate:
            # Interactive mode - ask for confirmation
            print(self.generate_drift_summary(drift_data))
            response = input("Apply remediation? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Remediation cancelled by user")
                return False
        
        # Apply configuration changes
        cmd = [
            "ansible-playbook",
            "playbooks/multi-protocol-deployment.yml",
            "--inventory", drift_data.get('inventory', 'inventories/production'),
            "--limit", drift_data.get('limit', 'vpn_servers'),
            "--extra-vars", "remediate_drift=true"
        ]
        
        try:
            logger.info("Applying configuration remediation...")
            result = subprocess.run(
                cmd,
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode == 0:
                logger.info("Configuration remediation completed successfully")
                
                # Run post-remediation validation
                self._validate_remediation(drift_data)
                return True
            else:
                logger.error(f"Remediation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error during remediation: {e}")
            return False
    
    def _validate_remediation(self, original_drift_data: Dict[str, Any]):
        """Validate that remediation was successful"""
        logger.info("Validating remediation...")
        
        # Run health check
        health_cmd = [
            "ansible-playbook",
            "playbooks/health-check.yml",
            "--inventory", original_drift_data.get('inventory', 'inventories/production'),
            "--limit", original_drift_data.get('limit', 'vpn_servers')
        ]
        
        try:
            result = subprocess.run(
                health_cmd,
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                logger.info("Post-remediation health check passed")
            else:
                logger.warning("Post-remediation health check failed")
                
        except Exception as e:
            logger.error(f"Error during post-remediation validation: {e}")
    
    def schedule_drift_detection(self, interval_hours: int = 24):
        """Schedule regular drift detection"""
        logger.info(f"Scheduling drift detection every {interval_hours} hours")
        
        # This would integrate with system cron or systemd timers
        # For now, just document the recommended schedule
        
        cron_schedule = f"0 */{interval_hours} * * *"
        script_path = Path(__file__).absolute()
        
        cron_command = f"{cron_schedule} {sys.executable} {script_path} --auto-detect"
        
        logger.info(f"Recommended cron entry: {cron_command}")
        
        return cron_command
    
    def list_drift_reports(self) -> List[Dict[str, Any]]:
        """List available drift reports"""
        reports = []
        
        for report_file in self.drift_reports_dir.glob("drift_report_*.json"):
            try:
                with open(report_file, 'r') as f:
                    report_data = json.load(f)
                
                reports.append({
                    "file": report_file.name,
                    "timestamp": report_data.get('timestamp'),
                    "drift_detected": report_data.get('drift_detected', False),
                    "changes_count": len(report_data.get('changes', [])),
                    "size": report_file.stat().st_size
                })
                
            except Exception as e:
                logger.warning(f"Error reading report {report_file}: {e}")
        
        return sorted(reports, key=lambda x: x['timestamp'], reverse=True)
    
    def cleanup_old_reports(self, keep_days: int = 30):
        """Clean up old drift reports"""
        logger.info(f"Cleaning up drift reports older than {keep_days} days")
        
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
        removed_count = 0
        
        for report_file in self.drift_reports_dir.glob("drift_report_*.json"):
            if report_file.stat().st_mtime < cutoff_time:
                report_file.unlink()
                removed_count += 1
        
        logger.info(f"Removed {removed_count} old drift reports")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="VPN Infrastructure Drift Detection")
    parser.add_argument("--inventory", "-i", default="inventories/production", 
                       help="Ansible inventory to use")
    parser.add_argument("--limit", "-l", default="vpn_servers", 
                       help="Limit to specific hosts or groups")
    parser.add_argument("--auto-detect", action="store_true", 
                       help="Run automatic drift detection")
    parser.add_argument("--auto-remediate", action="store_true", 
                       help="Automatically remediate detected drift")
    parser.add_argument("--remediate", action="store_true", 
                       help="Remediate drift from latest report")
    parser.add_argument("--list-reports", action="store_true", 
                       help="List available drift reports")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", 
                       help="Clean up reports older than DAYS")
    parser.add_argument("--schedule", type=int, metavar="HOURS", 
                       help="Show cron schedule for regular detection")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    detector = DriftDetector()
    
    if args.list_reports:
        reports = detector.list_drift_reports()
        print("\nDrift Detection Reports:")
        print("=" * 50)
        
        if reports:
            for report in reports:
                status = "DRIFT" if report['drift_detected'] else "OK"
                print(f"{report['timestamp']} - {status} - {report['changes_count']} changes - {report['file']}")
        else:
            print("No drift reports found")
        return
    
    if args.cleanup:
        detector.cleanup_old_reports(args.cleanup)
        return
    
    if args.schedule:
        cron_command = detector.schedule_drift_detection(args.schedule)
        print(f"Recommended cron entry:\n{cron_command}")
        return
    
    # Run drift detection
    drift_data = detector.detect_drift(args.inventory, args.limit)
    
    # Print summary
    summary = detector.generate_drift_summary(drift_data)
    print(summary)
    
    # Handle remediation
    if args.remediate or args.auto_remediate:
        if drift_data.get('drift_detected', False):
            success = detector.remediate_drift(drift_data, args.auto_remediate)
            if success:
                print("Drift remediation completed successfully")
            else:
                print("Drift remediation failed")
                sys.exit(1)
        else:
            print("No drift detected, no remediation needed")
    
    # Exit with appropriate code
    if drift_data.get('drift_detected', False) and not (args.remediate or args.auto_remediate):
        sys.exit(1)  # Indicate drift detected
    else:
        sys.exit(0)  # No drift or successfully remediated

if __name__ == "__main__":
    main()