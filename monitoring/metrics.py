"""
Prometheus metrics for monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging
import config

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Request metrics
requests_total = Counter(
    'inference_requests_total',
    'Total number of inference requests'
)

successful_requests = Counter(
    'inference_successful_total',
    'Total number of successful inferences'
)

failed_requests = Counter(
    'inference_failed_total',
    'Total number of failed inferences'
)

# Queue metrics
queue_length_gauge = Gauge(
    'inference_queue_length',
    'Current number of requests in queue'
)

# Latency metrics
inference_latency = Histogram(
    'inference_latency_seconds',
    'Time spent on inference',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Model-specific errors
model_errors = Counter(
    'model_errors_total',
    'Total errors per model',
    ['model_name']
)

# System metrics
cpu_usage_gauge = Gauge(
    'system_cpu_usage_percent',
    'CPU usage percentage'
)

memory_usage_gauge = Gauge(
    'system_memory_usage_bytes',
    'Memory usage in bytes'
)


def start_metrics_server(port: int = None):
    """
    Start Prometheus metrics HTTP server
    
    Args:
        port: Port to run metrics server on (default from config)
    """
    if port is None:
        port = config.PROMETHEUS_PORT
    
    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


def update_system_metrics():
    """Update system resource metrics"""
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_usage_gauge.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage_gauge.set(memory.used)
        
    except Exception as e:
        logger.error(f"Failed to update system metrics: {e}")
