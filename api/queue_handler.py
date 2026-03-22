"""
Async queue handler for managing inference requests
"""
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Optional
import logging
import time
import uuid

import config
from models import run_inference_worker
from monitoring import metrics

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


import multiprocessing

class QueueHandler:
    """
    Manages async queue and process pool for inference
    """
    
    def __init__(self):
        self.request_queue = asyncio.Queue(maxsize=config.MAX_QUEUE_SIZE)
        self.result_cache: Dict[str, Dict] = {}
        self.process_pool: Optional[ProcessPoolExecutor] = None
        self.workers_running = False
        self.circuit_breaker: Dict[str, Dict] = {}  # Track model failures
        
    async def initialize(self):
        """Initialize process pool and start workers"""
        logger.info("Initializing queue handler...")
        
        # Create process pool for CPU-intensive inference
        # Use 'spawn' to avoid deadlock with PyTorch/Gunicorn
        self.process_pool = ProcessPoolExecutor(
            max_workers=config.PROCESS_POOL_WORKERS,
            mp_context=multiprocessing.get_context('spawn')
        )
        
        # Start background workers
        for i in range(config.NUM_ASYNC_WORKERS):
            asyncio.create_task(self._queue_worker(worker_id=i))
            logger.info(f"Started worker {i}")
        
        self.workers_running = True
        logger.info(f"Queue handler initialized with {config.NUM_ASYNC_WORKERS} workers")
    
    async def shutdown(self):
        """Shutdown workers and process pool"""
        logger.info("Shutting down queue handler...")
        self.workers_running = False
        
        if self.process_pool:
            self.process_pool.shutdown(wait=True)
        
        logger.info("Queue handler shutdown complete")
    
    async def add_request(self, image_bytes: bytes, disease_type: str) -> str:
        """
        Add inference request to queue
        
        Args:
            image_bytes: Raw image data
            disease_type: Type of disease to detect
            
        Returns:
            request_id: Unique identifier for tracking
        """
        # Check if queue is full
        if self.request_queue.full():
            raise RuntimeError("Queue is full. Server at capacity.")
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Get model name from disease type
        model_name = config.MODEL_ROUTES.get(disease_type)
        if not model_name:
            raise ValueError(f"Unknown disease type: {disease_type}")
        
        # Check circuit breaker
        if self._is_circuit_open(model_name):
            raise RuntimeError(f"Model {model_name} temporarily unavailable (circuit breaker open)")
        
        # Create request data
        request_data = {
            'request_id': request_id,
            'image': image_bytes,
            'model': model_name,
            'disease_type': disease_type,
            'timestamp': time.time()
        }
        
        # Add to queue
        await self.request_queue.put(request_data)
        
        # Initialize result cache entry
        self.result_cache[request_id] = {
            'status': 'queued',
            'model': model_name
        }
        
        # Update metrics
        metrics.requests_total.inc()
        
        logger.info(f"Request {request_id} added to queue (type: {disease_type})")
        return request_id
    
    def get_result(self, request_id: str) -> Dict:
        """
        Get result for a request ID
        
        Args:
            request_id: Request identifier
            
        Returns:
            Result dictionary
        """
        if request_id not in self.result_cache:
            return {
                'status': 'not_found',
                'error': 'Request ID not found'
            }
        
        return self.result_cache[request_id]
    
    def get_queue_length(self) -> int:
        """Get current queue length"""
        return self.request_queue.qsize()
    
    async def _queue_worker(self, worker_id: int):
        """
        Background worker that processes queued requests
        
        Args:
            worker_id: Worker identifier
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.workers_running:
            try:
                # Get request from queue with timeout
                try:
                    request_data = await asyncio.wait_for(
                        self.request_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                request_id = request_data['request_id']
                model_name = request_data['model']
                
                # Update status
                self.result_cache[request_id]['status'] = 'processing'
                
                logger.info(f"Worker {worker_id} processing {request_id}")
                
                # Run inference in process pool
                loop = asyncio.get_running_loop()
                try:
                    # Update queue size metric
                    metrics.queue_length_gauge.set(self.request_queue.qsize())
                    metrics.update_system_metrics()
                    
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            self.process_pool,
                            run_inference_worker,
                            request_data
                        ),
                        timeout=config.MODEL_TIMEOUT
                    )
                    
                    if result['success']:
                        # Update cache with successful result
                        self.result_cache[request_id] = {
                            'status': 'completed',
                            **result['result']
                        }
                        self._reset_circuit_breaker(model_name)
                        metrics.successful_requests.inc()
                        metrics.inference_latency.observe(result.get('latency', 0))
                        logger.info(f"Worker {worker_id} completed {request_id}")
                    else:
                        # Handle inference error
                        self.result_cache[request_id] = {
                            'status': 'failed',
                            'error': result['error']
                        }
                        self._record_failure(model_name)
                        metrics.failed_requests.inc()
                        logger.error(f"Worker {worker_id} failed {request_id}: {result['error']}")
                
                except asyncio.TimeoutError:
                    self.result_cache[request_id] = {
                        'status': 'failed',
                        'error': 'Inference timeout'
                    }
                    self._record_failure(model_name)
                    metrics.failed_requests.inc()
                    logger.error(f"Worker {worker_id} timeout on {request_id}")
                
                except Exception as e:
                    self.result_cache[request_id] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    self._record_failure(model_name)
                    metrics.failed_requests.inc()
                    logger.error(f"Worker {worker_id} error on {request_id}: {e}")
                
                # Mark task as done
                self.request_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(0.1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _is_circuit_open(self, model_name: str) -> bool:
        """Check if circuit breaker is open for model"""
        if model_name not in self.circuit_breaker:
            return False
        
        breaker = self.circuit_breaker[model_name]
        
        # Check if circuit is open
        if breaker['failures'] >= config.CIRCUIT_BREAKER_THRESHOLD:
            # Check if timeout has passed
            if time.time() - breaker['last_failure'] < config.CIRCUIT_BREAKER_TIMEOUT:
                return True
            else:
                # Reset circuit breaker after timeout
                self._reset_circuit_breaker(model_name)
                return False
        
        return False
    
    def _record_failure(self, model_name: str):
        """Record a failure for circuit breaker"""
        if model_name not in self.circuit_breaker:
            self.circuit_breaker[model_name] = {
                'failures': 0,
                'last_failure': 0
            }
        
        self.circuit_breaker[model_name]['failures'] += 1
        self.circuit_breaker[model_name]['last_failure'] = time.time()
        
        if self.circuit_breaker[model_name]['failures'] >= config.CIRCUIT_BREAKER_THRESHOLD:
            logger.warning(f"Circuit breaker opened for model {model_name}")
    
    def _reset_circuit_breaker(self, model_name: str):
        """Reset circuit breaker for model"""
        if model_name in self.circuit_breaker:
            self.circuit_breaker[model_name] = {
                'failures': 0,
                'last_failure': 0
            }


# Global queue handler instance
queue_handler = QueueHandler()
