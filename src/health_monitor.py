"""
Health Monitoring and System Diagnostics
Provides health checks, metrics tracking, and system monitoring
"""

import os
import time
import json
import logging
import psutil
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque
from config import Config

logger = logging.getLogger(__name__)

class HealthMonitor:
    """System health monitoring and metrics collection"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            'api_calls': {
                'sam': {'success': 0, 'failure': 0, 'rate_limited': 0},
                'openai': {'success': 0, 'failure': 0, 'rate_limited': 0},
                'sheets': {'success': 0, 'failure': 0, 'quota_exceeded': 0},
                'drive': {'success': 0, 'failure': 0}
            },
            'rfp_processing': {
                'total_searched': 0,
                'mini_screened': 0,
                'deep_analyzed': 0,
                'qualified': 0,
                'maybe': 0,
                'rejected': 0,
                'errors': 0
            },
            'performance': {
                'avg_mini_time': deque(maxlen=100),
                'avg_deep_time': deque(maxlen=100),
                'avg_sam_time': deque(maxlen=100)
            },
            'system': {
                'memory_usage': [],
                'cpu_usage': [],
                'disk_usage': 0
            },
            'errors': deque(maxlen=100),  # Keep last 100 errors
            'warnings': deque(maxlen=100)  # Keep last 100 warnings
        }
        self.lock = threading.RLock()
        self.circuit_breakers = {}
        
    def record_api_call(self, api: str, success: bool, duration: float = None, error: str = None):
        """Record API call metrics"""
        with self.lock:
            if api in self.metrics['api_calls']:
                if success:
                    self.metrics['api_calls'][api]['success'] += 1
                else:
                    self.metrics['api_calls'][api]['failure'] += 1
                    if 'rate' in error.lower() if error else False:
                        self.metrics['api_calls'][api]['rate_limited'] += 1
                
                # Record timing
                if duration and api == 'sam':
                    self.metrics['performance']['avg_sam_time'].append(duration)
    
    def record_rfp_processing(self, stage: str, count: int = 1):
        """Record RFP processing metrics"""
        with self.lock:
            if stage in self.metrics['rfp_processing']:
                self.metrics['rfp_processing'][stage] += count
    
    def record_ai_processing_time(self, model: str, duration: float):
        """Record AI model processing times"""
        with self.lock:
            if 'mini' in model.lower():
                self.metrics['performance']['avg_mini_time'].append(duration)
            else:
                self.metrics['performance']['avg_deep_time'].append(duration)
    
    def record_error(self, error: str, context: str = None):
        """Record errors for analysis"""
        with self.lock:
            self.metrics['errors'].append({
                'time': datetime.now().isoformat(),
                'error': str(error)[:500],
                'context': context
            })
    
    def record_warning(self, warning: str):
        """Record warnings"""
        with self.lock:
            self.metrics['warnings'].append({
                'time': datetime.now().isoformat(),
                'warning': str(warning)[:500]
            })
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics['system']['memory_usage'] = {
                'percent': memory.percent,
                'used_gb': memory.used / (1024**3),
                'available_gb': memory.available / (1024**3)
            }
            
            # CPU usage
            self.metrics['system']['cpu_usage'] = {
                'percent': psutil.cpu_percent(interval=1),
                'cores': psutil.cpu_count()
            }
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.metrics['system']['disk_usage'] = {
                'percent': disk.percent,
                'free_gb': disk.free / (1024**3)
            }
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        with self.lock:
            self.update_system_metrics()
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime_hours': (time.time() - self.start_time) / 3600,
                'checks': {}
            }
            
            # Check API health
            for api, stats in self.metrics['api_calls'].items():
                total = stats['success'] + stats['failure']
                if total > 0:
                    success_rate = stats['success'] / total
                    health_status['checks'][f'{api}_api'] = {
                        'status': 'healthy' if success_rate > 0.9 else 'degraded' if success_rate > 0.5 else 'unhealthy',
                        'success_rate': round(success_rate, 3),
                        'total_calls': total,
                        'rate_limited': stats.get('rate_limited', 0)
                    }
            
            # Check processing health
            rfp_stats = self.metrics['rfp_processing']
            if rfp_stats['total_searched'] > 0:
                error_rate = rfp_stats['errors'] / rfp_stats['total_searched']
                health_status['checks']['processing'] = {
                    'status': 'healthy' if error_rate < 0.05 else 'degraded' if error_rate < 0.2 else 'unhealthy',
                    'error_rate': round(error_rate, 3),
                    'total_processed': rfp_stats['total_searched'],
                    'qualified_rate': round(rfp_stats['qualified'] / max(rfp_stats['deep_analyzed'], 1), 3)
                }
            
            # Check system resources
            mem = self.metrics['system'].get('memory_usage', {})
            cpu = self.metrics['system'].get('cpu_usage', {})
            disk = self.metrics['system'].get('disk_usage', {})
            
            health_status['checks']['system'] = {
                'status': 'healthy',
                'memory_percent': mem.get('percent', 0),
                'cpu_percent': cpu.get('percent', 0),
                'disk_free_gb': disk.get('free_gb', 0)
            }
            
            # Determine overall status
            if any(check.get('status') == 'unhealthy' for check in health_status['checks'].values()):
                health_status['status'] = 'unhealthy'
            elif any(check.get('status') == 'degraded' for check in health_status['checks'].values()):
                health_status['status'] = 'degraded'
            
            # Add recent errors if unhealthy
            if health_status['status'] != 'healthy' and self.metrics['errors']:
                health_status['recent_errors'] = list(self.metrics['errors'])[-5:]
            
            return health_status
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        with self.lock:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'uptime_hours': round((time.time() - self.start_time) / 3600, 2),
                'api_metrics': self.metrics['api_calls'],
                'processing_metrics': self.metrics['rfp_processing'],
                'performance': {
                    'avg_mini_time_sec': round(sum(self.metrics['performance']['avg_mini_time']) / 
                                              max(len(self.metrics['performance']['avg_mini_time']), 1), 2),
                    'avg_deep_time_sec': round(sum(self.metrics['performance']['avg_deep_time']) / 
                                              max(len(self.metrics['performance']['avg_deep_time']), 1), 2),
                    'avg_sam_time_sec': round(sum(self.metrics['performance']['avg_sam_time']) / 
                                            max(len(self.metrics['performance']['avg_sam_time']), 1), 2)
                },
                'system_resources': self.metrics['system'],
                'error_count': len(self.metrics['errors']),
                'warning_count': len(self.metrics['warnings'])
            }
            
            # Calculate cost estimates
            mini_calls = self.metrics['rfp_processing']['mini_screened']
            deep_calls = self.metrics['rfp_processing']['deep_analyzed']
            
            # Rough cost estimates (adjust based on actual pricing)
            summary['estimated_costs'] = {
                'gpt5_mini': round(mini_calls * 0.002, 2),  # Estimated cost per call
                'gpt5': round(deep_calls * 0.02, 2),  # Estimated cost per call
                'total_usd': round(mini_calls * 0.002 + deep_calls * 0.02, 2),
                'savings_from_screening': round((self.metrics['rfp_processing']['rejected'] * 0.02), 2)
            }
            
            return summary
    
    def save_metrics(self, filepath: str = 'metrics.json'):
        """Save metrics to file"""
        try:
            summary = self.get_metrics_summary()
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"Metrics saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def reset_metrics(self):
        """Reset all metrics (useful for daily resets)"""
        with self.lock:
            for api in self.metrics['api_calls']:
                self.metrics['api_calls'][api] = {'success': 0, 'failure': 0, 'rate_limited': 0}
            
            self.metrics['rfp_processing'] = {
                'total_searched': 0,
                'mini_screened': 0,
                'deep_analyzed': 0,
                'qualified': 0,
                'maybe': 0,
                'rejected': 0,
                'errors': 0
            }
            
            self.metrics['errors'].clear()
            self.metrics['warnings'].clear()
            logger.info("Metrics reset")

# Global instance
health_monitor = HealthMonitor()

def get_health_status() -> Dict[str, Any]:
    """Get current health status"""
    return health_monitor.check_health()

def get_metrics() -> Dict[str, Any]:
    """Get current metrics"""
    return health_monitor.get_metrics_summary()