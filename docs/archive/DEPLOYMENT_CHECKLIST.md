# Production Deployment Checklist

## Pre-Deployment

### Infrastructure
- [ ] GPU drivers installed and verified (`nvidia-smi`)
- [ ] PyTorch CUDA version matches GPU driver (`torch.cuda.is_available()`)
- [ ] Sufficient disk space for models (20GB+ recommended)
- [ ] Network ports 8000, 9090 open (or configured alternative ports)
- [ ] SSL/TLS certificates ready (if using HTTPS)

### Configuration
- [ ] `.env` file created from `.env.example`
- [ ] Strong API keys generated (`secrets.token_urlsafe(32)`)
- [ ] CORS origins restricted to production domains
- [ ] LOG_LEVEL set to WARNING or ERROR
- [ ] Prometheus port configured if using external monitoring

### Security
- [ ] API keys rotated from default values
- [ ] File upload size limits reviewed
- [ ] Rate limiting configured (optional: slowapi)
- [ ] Reverse proxy configured (nginx/traefik)
- [ ] Firewall rules applied

## Model Preparation

### Required for Medical Accuracy
- [ ] Medical datasets downloaded and preprocessed
- [ ] Models fine-tuned on domain-specific data
- [ ] Validation accuracy meets clinical thresholds (>95%)
- [ ] Model weights saved to `models/weights/`
- [ ] Model performance benchmarked against radiologist baseline

### Testing
- [ ] Unit tests pass (`pytest tests/`)
- [ ] Load tests pass 1000+ concurrent users (`locust`)
- [ ] API integration tests verified
- [ ] GPU memory usage under load measured
- [ ] Latency p99 < 2 seconds confirmed

## Deployment

### Docker (Recommended)
```bash
cd docker
docker-compose up -d
docker ps  # Verify containers running
docker logs medical-inference-server  # Check logs
```

### Manual Deployment
```bash
# Activate environment
.venv\Scripts\activate

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Verification
- [ ] Health endpoint responds: `curl http://localhost:8000/api/v1/health`
- [ ] Metrics endpoint accessible: `curl http://localhost:8000/metrics`
- [ ] Dashboard loads: http://localhost:8000/dashboard
- [ ] API docs available: http://localhost:8000/docs
- [ ] Sample prediction works with test image

## Monitoring Setup

### Prometheus Integration
- [ ] Prometheus server configured with `prometheus.yml`
- [ ] Grafana dashboards created (optional)
- [ ] Alert rules defined for critical metrics
- [ ] Notification channels configured (Slack/email)

### Key Metrics to Monitor
- [ ] `inference_requests_total` - request volume
- [ ] `inference_successful_total` - success rate
- [ ] `inference_failed_total` - error rate
- [ ] `inference_latency_seconds` - response time
- [ ] `system_cpu_usage_percent` - CPU load
- [ ] `system_memory_usage_bytes` - RAM usage
- [ ] `inference_queue_length` - queue backlog

### Alerting Thresholds
- [ ] Error rate > 1% triggers warning
- [ ] Error rate > 5% triggers critical alert
- [ ] Latency p95 > 2s triggers warning
- [ ] Queue length > 500 triggers warning
- [ ] CPU > 90% for 5 minutes triggers alert

## Post-Deployment

### Day 1
- [ ] Monitor logs for errors continuously
- [ ] Watch metrics dashboard for anomalies
- [ ] Test with production traffic sample
- [ ] Verify GPU utilization is optimal
- [ ] Check memory leaks don't occur over time

### Week 1
- [ ] Review error patterns and fix issues
- [ ] Optimize process/worker counts based on load
- [ ] Fine-tune circuit breaker thresholds
- [ ] Document operational procedures
- [ ] Train support team on troubleshooting

### Month 1
- [ ] Analyze performance trends
- [ ] Plan capacity upgrades if needed
- [ ] Review and update model weights
- [ ] Conduct security audit
- [ ] Gather user feedback

## Rollback Plan

### If Issues Occur
1. Stop current deployment: `docker-compose down`
2. Revert to previous version: `git checkout <previous-tag>`
3. Rebuild: `docker-compose build`
4. Restart: `docker-compose up -d`
5. Verify: Check health endpoint

### Emergency Contacts
- [ ] DevOps team contact info documented
- [ ] Medical team escalation path defined
- [ ] Vendor support contracts active

## Compliance & Legal

### Medical Device Regulations
- [ ] FDA 510(k) clearance obtained (if USA)
- [ ] CE Mark certification (if EU)
- [ ] Clinical validation study completed
- [ ] Risk management documentation (ISO 14971)

### Data Privacy
- [ ] HIPAA compliance verified (if handling PHI)
- [ ] GDPR compliance reviewed (if EU users)
- [ ] Data retention policies implemented
- [ ] Audit logging enabled

### Documentation
- [ ] User manual completed
- [ ] API documentation published
- [ ] Training materials prepared
- [ ] Incident response plan documented

## Performance Benchmarks

### Expected Metrics (RTX 4070)
- **Throughput**: 500-800 req/s
- **Latency p50**: <0.5s
- **Latency p95**: <1.5s
- **Latency p99**: <2.0s
- **Success Rate**: >99.5%
- **GPU Utilization**: 60-90%
- **Memory Usage**: 4-6GB VRAM

### Load Test Results
- [ ] 1000 concurrent users handled successfully
- [ ] No memory leaks observed over 1 hour
- [ ] Queue never exceeded capacity
- [ ] Circuit breaker activated and recovered properly

## Known Limitations

### Current Implementation
- ⚠️ Models use ImageNet pretrained weights (not medical-trained)
- ⚠️ Predictions are architectural demos, not clinically validated
- ⚠️ Single GPU deployment (no multi-GPU support yet)
- ⚠️ In-memory result caching (lost on restart)

### Requires Development
- Medical dataset integration and training
- Multi-GPU inference support
- Persistent result storage (Redis/database)
- Advanced authentication (OAuth2/JWT)
- Real-time model updates without restart

---

**Sign-off**: 
- [ ] Technical Lead: _______________ Date: ___________
- [ ] Medical Director: _______________ Date: ___________
- [ ] Compliance Officer: _______________ Date: ___________
