#!/usr/bin/env python3
"""
P6 - UI Metrics Tests

Test the metrics dashboard UI functionality.
"""

import unittest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


class TestUIMetrics(unittest.TestCase):
    """Test metrics dashboard UI."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        self.test_dir = tempfile.mkdtemp()
        self.pid = "test_project"
        
        # Ensure ui_projects directory exists
        os.makedirs("ui_projects", exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        if os.path.exists("ui_projects"):
            shutil.rmtree("ui_projects")
    
    @patch('analytics_core.analytics.get_metrics')
    def test_metrics_html_view(self, mock_get_metrics):
        """Test metrics HTML view."""
        mock_metrics = {
            'total_findings': 10,
            'active': 5,
            'resolved': 3,
            'false_positives': 1,
            'risk_accepted': 1,
            'suppressed': 0,
            'avg_fix_time_days': 2.5,
            'most_common_tags': ['auth', 'header'],
            'top_owners': ['alice@example.com', 'bob@example.com'],
            'trend_30d': [
                {'date': '2025-01-01', 'count': 2},
                {'date': '2025-01-02', 'count': 3}
            ],
            'severity_breakdown': {
                'critical': 1,
                'high': 3,
                'medium': 4,
                'low': 2,
                'info': 0
            }
        }
        mock_get_metrics.return_value = mock_metrics
        
        response = self.client.get(f'/p/{self.pid}/metrics')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Metrics & Analytics', response.data)
        self.assertIn(b'Total Findings', response.data)
        self.assertIn(b'Active', response.data)
        self.assertIn(b'Resolved', response.data)
    
    @patch('routes.metrics.get_metrics')
    def test_metrics_json_view(self, mock_get_metrics):
        """Test metrics JSON view."""
        mock_metrics = {
            'total_findings': 10,
            'active': 5,
            'resolved': 3,
            'false_positives': 1,
            'risk_accepted': 1,
            'suppressed': 0,
            'avg_fix_time_days': 2.5,
            'most_common_tags': ['auth', 'header'],
            'top_owners': ['alice@example.com', 'bob@example.com'],
            'trend_30d': [
                {'date': '2025-01-01', 'count': 2},
                {'date': '2025-01-02', 'count': 3}
            ],
            'severity_breakdown': {
                'critical': 1,
                'high': 3,
                'medium': 4,
                'low': 2,
                'info': 0
            }
        }
        mock_get_metrics.return_value = mock_metrics
        
        response = self.client.get(f'/p/{self.pid}/metrics?format=json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        
        data = json.loads(response.data)
        self.assertEqual(data['total_findings'], 10)
        self.assertEqual(data['active'], 5)
        self.assertEqual(data['resolved'], 3)
    
    @patch('routes.metrics.get_filtered_metrics')
    def test_metrics_with_filters(self, mock_get_filtered_metrics):
        """Test metrics with filters."""
        mock_metrics = {
            'total_findings': 5,
            'active': 3,
            'resolved': 2,
            'false_positives': 0,
            'risk_accepted': 0,
            'suppressed': 0,
            'avg_fix_time_days': 1.5,
            'most_common_tags': ['auth'],
            'top_owners': ['alice@example.com'],
            'trend_30d': [
                {'date': '2025-01-01', 'count': 1},
                {'date': '2025-01-02', 'count': 2}
            ],
            'severity_breakdown': {
                'critical': 0,
                'high': 2,
                'medium': 2,
                'low': 1,
                'info': 0
            },
            'last_updated': '2025-01-01T00:00:00Z'
        }
        mock_get_filtered_metrics.return_value = mock_metrics
        
        response = self.client.get(f'/p/{self.pid}/metrics?status=open&owner=alice@example.com')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Metrics & Analytics', response.data)
    
    @patch('routes.metrics.get_metrics')
    def test_metrics_empty_project(self, mock_get_metrics):
        """Test metrics for empty project."""
        mock_metrics = {
            'total_findings': 0,
            'active': 0,
            'resolved': 0,
            'false_positives': 0,
            'risk_accepted': 0,
            'suppressed': 0,
            'avg_fix_time_days': 0,
            'most_common_tags': [],
            'top_owners': [],
            'trend_30d': [],
            'severity_breakdown': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            },
            'last_updated': '2025-01-01T00:00:00Z'
        }
        mock_get_metrics.return_value = mock_metrics
    
        response = self.client.get(f'/p/{self.pid}/metrics')
    
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Metrics & Analytics', response.data)
    
    @patch('routes.metrics.get_metrics')
    def test_metrics_error_handling(self, mock_get_metrics):
        """Test metrics error handling."""
        mock_get_metrics.side_effect = Exception("Metrics error")
    
        response = self.client.get(f'/p/{self.pid}/metrics')
    
        self.assertEqual(response.status_code, 500)
        self.assertIn(b'Error loading metrics', response.data)
    
    def test_metrics_template_structure(self):
        """Test metrics template structure."""
        with patch('analytics_core.analytics.get_metrics') as mock_get_metrics:
            mock_metrics = {
                'total_findings': 10,
                'active': 5,
                'resolved': 3,
                'false_positives': 1,
                'risk_accepted': 1,
                'suppressed': 0,
                'avg_fix_time_days': 2.5,
                'most_common_tags': ['auth', 'header'],
                'top_owners': ['alice@example.com', 'bob@example.com'],
                'trend_30d': [
                    {'date': '2025-01-01', 'count': 2},
                    {'date': '2025-01-02', 'count': 3}
                ],
                'severity_breakdown': {
                    'critical': 1,
                    'high': 3,
                    'medium': 4,
                    'low': 2,
                    'info': 0
                },
                'last_updated': '2025-01-01T00:00:00Z'
            }
            mock_get_metrics.return_value = mock_metrics
            
            response = self.client.get(f'/p/{self.pid}/metrics')
            
            # Check for key template elements
            self.assertIn(b'Metrics & Analytics', response.data)
            self.assertIn(b'Total Findings', response.data)
            self.assertIn(b'30-Day Trend', response.data)
            self.assertIn(b'Severity Breakdown', response.data)
            
            # Check for Chart.js integration
            self.assertIn(b'Chart.js', response.data)
    
    def test_metrics_navigation_integration(self):
        """Test metrics navigation integration."""
        with patch('routes.metrics.get_metrics') as mock_get_metrics:
            mock_metrics = {
                'total_findings': 10,
                'active': 5,
                'resolved': 3,
                'false_positives': 1,
                'risk_accepted': 1,
                'suppressed': 0,
                'avg_fix_time_days': 2.5,
                'most_common_tags': ['auth', 'header'],
                'top_owners': ['alice@example.com', 'bob@example.com'],
                'trend_30d': [
                    {'date': '2025-01-01', 'count': 2},
                    {'date': '2025-01-02', 'count': 3}
                ],
                'severity_breakdown': {
                    'critical': 1,
                    'high': 3,
                    'medium': 4,
                    'low': 2,
                    'info': 0
                },
                'last_updated': '2025-01-01T00:00:00Z'
            }
            mock_get_metrics.return_value = mock_metrics
            
            response = self.client.get(f'/p/{self.pid}/metrics')
            
            # Check for navigation elements
            self.assertIn(b'Metrics', response.data)
            self.assertIn(b'Vulnerabilities', response.data)
            self.assertIn(b'Active Testing', response.data)


if __name__ == '__main__':
    unittest.main()
