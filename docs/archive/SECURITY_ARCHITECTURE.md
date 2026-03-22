# 🔒 Security Architecture for Federated Medical Imaging System

## Overview
This document outlines the comprehensive security implementation for a **federated learning platform** enabling multiple hospitals to collaboratively train chest X-ray diagnostic models while maintaining HIPAA compliance and protecting patient privacy.

---

## 🎯 System Purpose

### Real ML Application: Federated Multi-Disease Chest X-Ray Diagnosis

**Problem Statement:**
Hospitals need to collaboratively improve diagnostic AI models but cannot share patient data due to privacy regulations (HIPAA, GDPR). Traditional centralized training is legally impossible.

**Solution:**
Federated learning system where:
1. Each hospital trains models locally on private data
2. Only encrypted model gradients are transmitted
3. Central server aggregates updates using FedAvg algorithm
4. Differential privacy protects against model inversion attacks
5. Zero raw patient data ever leaves hospital premises

**Literature-Backed Approach:**
- **Federated Learning**: McMahan et al. "Communication-Efficient Learning of Deep Networks from Decentralized Data" (2017)
- **Differential Privacy**: Abadi et al. "Deep Learning with Differential Privacy" (2016)
- **Medical Federated Learning**: Rieke et al. "The Future of Digital Health with Federated Learning" (Nature 2020)
- **CheXNet Architecture**: Rajpurkar et al. "CheXNet: Radiologist-Level Pneumonia Detection" (2017)

---

## 🏗️ Security Layers

### Layer 1: Authentication & Authorization

#### JWT (JSON Web Token) Authentication
```
Implementation: PyJWT with RS256 (RSA-SHA256)

Token Structure:
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "hospital_id_12345",
    "role": "hospital_client",
    "permissions": ["upload_gradients", "download_global_model"],
    "exp": 1700000000,
    "iat": 1699996400,
    "hospital_name": "Medora Medical",
    "region": "US-East"
  },
  "signature": "..."
}

Token Lifecycle:
- Access tokens: 15 minute expiration
- Refresh tokens: 7 day expiration
- Rotation: Required every 24 hours
- Revocation: Redis blacklist for compromised tokens

Security Features:
✓ RSA 4096-bit key pairs (not HMAC - prevents key confusion attacks)
✓ Token blacklisting via Redis
✓ IP whitelist validation per hospital
✓ Rate limiting per token (100 requests/minute)
✓ Automatic rotation on suspicious activity
```

**Implementation Files:**
- `security/jwt_handler.py` - Token generation/validation
- `security/token_manager.py` - Refresh/revocation logic
- `api/auth_routes.py` - Login/refresh endpoints
- `.env.example` - JWT secret configuration

#### Role-Based Access Control (RBAC)

**Roles:**
1. **Hospital Client** (most common)
   - Upload local model gradients
   - Download aggregated global model
   - View training metrics for own hospital
   - Cannot access other hospitals' data

2. **Admin** (central server operator)
   - View all training metrics
   - Manage hospital registrations
   - Configure federated learning parameters
   - Emergency model rollback

3. **Auditor** (compliance officer)
   - Read-only access to audit logs
   - View differential privacy parameters
   - Generate compliance reports
   - Cannot modify any data

**Permissions Matrix:**
```
Action                          | Hospital | Admin | Auditor
--------------------------------|----------|-------|--------
Upload local gradients          |    ✓     |   ✗   |   ✗
Download global model           |    ✓     |   ✓   |   ✗
View own training metrics       |    ✓     |   ✓   |   ✓
View all hospital metrics       |    ✗     |   ✓   |   ✓
Modify FL hyperparameters       |    ✗     |   ✓   |   ✗
Access audit logs               |    ✗     |   ✓   |   ✓
Revoke hospital access          |    ✗     |   ✓   |   ✗
Emergency stop training         |    ✗     |   ✓   |   ✗
```

---

### Layer 2: Transport Security

#### TLS 1.3 Encryption

```
Configuration: Mandatory TLS 1.3 with Perfect Forward Secrecy

Cipher Suites (in order of preference):
1. TLS_AES_256_GCM_SHA384
2. TLS_CHACHA20_POLY1305_SHA256
3. TLS_AES_128_GCM_SHA256

Certificate Strategy:
- Let's Encrypt for production (auto-renewal)
- Self-signed for development
- Certificate pinning for hospital clients
- HSTS enforced: max-age=31536000; includeSubDomains

Implementation:
- Uvicorn with SSL context
- Certificate rotation: 90 days
- OCSP stapling for revocation checks
- TLS 1.2 and below: REJECTED
```

**Files:**
- `security/tls_config.py` - SSL context configuration
- `certs/` - Certificate storage (gitignored)
- `scripts/generate_certs.py` - Dev certificate generation
- `docker/nginx.conf` - Reverse proxy with TLS termination

#### mTLS (Mutual TLS) for Hospital Clients

```
Additional layer for hospital → server communication

Requirements:
✓ Server verifies client certificate (hospital identity)
✓ Client verifies server certificate
✓ Certificate-based authentication before JWT
✓ Prevents man-in-the-middle attacks

Hospital Certificate Issuance:
1. Hospital generates CSR (Certificate Signing Request)
2. Admin validates hospital credentials
3. CA signs certificate (2-year validity)
4. Hospital installs client cert in their system
5. Server maintains whitelist of valid cert fingerprints
```

---

### Layer 3: Data Encryption

#### AES-256-GCM for Model Files

```
Encryption Strategy: Encrypt-then-MAC with AES-256-GCM

What Gets Encrypted:
1. Global model weights (.pth files)
2. Local gradients uploaded by hospitals
3. Aggregated gradient checkpoints
4. Training state dictionaries

Encryption Process:
┌─────────────────────────────────────────────────────┐
│ Model Weights (PyTorch state_dict)                 │
│   ↓                                                 │
│ Serialize to bytes (torch.save)                    │
│   ↓                                                 │
│ Generate random 96-bit nonce (per file)            │
│   ↓                                                 │
│ AES-256-GCM encryption                              │
│   Key: Derived from master key + hospital ID       │
│   ↓                                                 │
│ Prepend nonce + authentication tag                 │
│   ↓                                                 │
│ Store encrypted blob + metadata                    │
└─────────────────────────────────────────────────────┘

Key Management:
- Master key: Stored in AWS KMS / Azure Key Vault
- Hospital-specific keys: HKDF derivation from master
- Key rotation: Every 90 days
- Old keys retained for decryption of historical data

File Structure:
[12 bytes: nonce][16 bytes: auth_tag][variable: ciphertext]
```

**Implementation:**
- `security/crypto_handler.py` - AES-256-GCM implementation
- `security/key_manager.py` - Key derivation and rotation
- `models/encrypted_storage.py` - Encrypted model persistence
- `api/upload_routes.py` - Decrypt gradients on upload

#### Differential Privacy for Gradients

```
Algorithm: DP-SGD (Abadi et al., 2016)

Privacy Parameters:
- ε (epsilon): 1.0 - 8.0 (privacy budget)
- δ (delta): 10^-5 (failure probability)
- C (clipping): Gradient clipping norm = 1.0
- σ (noise): Gaussian noise scaled to C/ε

Process per Training Round:
1. Hospital computes local gradients on private data
2. Clip gradients: g_clipped = g / max(1, ||g||₂ / C)
3. Add Gaussian noise: g_private = g_clipped + N(0, σ²C²I)
4. Upload noisy gradients to server
5. Server aggregates: Θ_global = (1/K) Σ g_private_k

Privacy Guarantee:
After T rounds: ε_total ≤ T·ε (composition theorem)
With ε=1.0, T=1000 rounds → ε_total ≈ 31.6 (via moments accountant)

Implementation:
- opacus library for PyTorch differential privacy
- Privacy budget tracking per hospital
- Automatic training termination at ε_max
```

**Files:**
- `federated/differential_privacy.py` - DP-SGD implementation
- `federated/privacy_accountant.py` - ε tracking
- `config/privacy_config.py` - Privacy parameters

---

### Layer 4: Attack Prevention

#### Rate Limiting (Token Bucket Algorithm)

```
Multi-Tier Rate Limiting:

1. Global Rate Limit (All Traffic):
   - 10,000 requests/minute across all clients
   - Prevents DDoS attacks
   - 503 response when exceeded

2. Per-Hospital Rate Limit:
   - 100 requests/minute per hospital
   - Prevents single hospital monopolizing resources
   - 429 response with Retry-After header

3. Endpoint-Specific Limits:
   - /api/v1/upload_gradients: 10/minute (heavy operation)
   - /api/v1/download_model: 20/minute
   - /api/v1/metrics: 100/minute
   - /api/v1/login: 5/minute (brute-force prevention)

Implementation:
- Redis for distributed rate limit counters
- Sliding window algorithm (more accurate than fixed window)
- Exponential backoff for repeated violations
- Automatic temporary ban after 10 violations (1 hour)

Token Bucket Formula:
  tokens_available = min(capacity, tokens + (now - last_update) * refill_rate)
  if tokens_available >= 1:
      tokens_available -= 1
      allow_request()
  else:
      reject_with_429()
```

**Files:**
- `security/rate_limiter.py` - Token bucket implementation
- `middleware/rate_limit_middleware.py` - FastAPI middleware
- `config/rate_limits.py` - Limit configuration

#### Input Validation & Sanitization

```
Validation Layers:

1. File Upload Validation:
   - Max size: 500 MB (large model gradients)
   - Allowed formats: .pth (PyTorch), .npz (NumPy)
   - Magic byte validation (not just extension)
   - Virus scanning with ClamAV
   - Pickle exploit detection

2. Gradient Shape Validation:
   - Verify tensor shapes match model architecture
   - Reject gradients with NaN/Inf values
   - Check gradient norms (detect poisoning attacks)
   - Byzantine-robust aggregation (Krum algorithm)

3. API Parameter Validation:
   - Pydantic schemas for all endpoints
   - SQL injection prevention (parameterized queries)
   - XSS prevention (sanitize all string inputs)
   - CSRF tokens for state-changing operations

4. Model Integrity Checks:
   - Cryptographic hash (SHA-256) for each model version
   - Digital signatures from trusted hospitals
   - Backdoor detection via activation clustering
```

**Files:**
- `api/validators.py` - Pydantic validation schemas
- `security/file_validator.py` - Gradient file validation
- `federated/byzantine_defense.py` - Attack detection

#### SQL Injection & NoSQL Injection Prevention

```
Database Security:

PostgreSQL Configuration:
- Prepared statements only (no string concatenation)
- Minimum privilege principle (read-only for most users)
- Encrypted connections (SSL required)
- Audit logging for all write operations

Example (SECURE):
cursor.execute(
    "SELECT * FROM hospitals WHERE id = %s AND active = %s",
    (hospital_id, True)
)

Example (INSECURE - NEVER DO THIS):
query = f"SELECT * FROM hospitals WHERE id = {hospital_id}"

Redis Security:
- No EVAL commands (Lua script injection risk)
- Only use predefined commands
- AUTH password required
- Bind to localhost only

MongoDB (if used):
- Disable JavaScript execution
- Use $where operator carefully
- Validate all query operators
```

---

### Layer 5: Monitoring & Incident Response

#### Real-Time Security Monitoring

```
Monitoring Dashboard Components:

1. Authentication Metrics:
   - Failed login attempts (spike = brute force attack)
   - Invalid JWT tokens (spike = token theft)
   - IP geolocation changes (account compromise)
   - After-hours access patterns (suspicious)

2. Traffic Analysis:
   - Request rate per hospital (detect DDoS)
   - Upload/download volume (data exfiltration)
   - Unusual endpoint access patterns
   - Geographic anomalies (VPN/proxy detection)

3. Model Integrity Monitoring:
   - Gradient norm distribution (poisoning attacks)
   - Model performance degradation (backdoor insertion)
   - Validation accuracy drops (data quality issues)
   - Training loss anomalies (byzantine clients)

4. System Health:
   - CPU/GPU utilization
   - Memory usage
   - Disk space (encrypted model storage)
   - Network bandwidth

Alerting Rules:
- 🚨 CRITICAL: 10+ failed logins from same IP → auto-ban
- 🚨 CRITICAL: Model accuracy drops >10% → rollback
- ⚠️  WARNING: Gradient norm > 3σ → flag for review
- ⚠️  WARNING: Unusual access time → notify admin
- ℹ️  INFO: New hospital registration → manual approval
```

**Implementation:**
- **Prometheus** - Time-series metrics
- **Grafana** - Visualization dashboards
- **ELK Stack** (Elasticsearch, Logstash, Kibana) - Log aggregation
- **PagerDuty** - Alert notification
- **Sentry** - Error tracking

**Files:**
- `monitoring/security_metrics.py` - Custom metrics
- `monitoring/dashboards/security_dashboard.json` - Grafana config
- `monitoring/alerts.yml` - Alertmanager rules
- `docker/docker-compose.monitoring.yml` - Monitoring stack

#### Audit Logging

```
Compliance Logging (HIPAA/GDPR Requirements):

What Gets Logged:
1. All authentication attempts (success/failure)
2. All model downloads (who, when, which version)
3. All gradient uploads (hospital ID, timestamp, size)
4. All configuration changes (admin actions)
5. All access to audit logs (who viewed what)

Log Format (JSON):
{
  "timestamp": "2025-11-22T14:35:22.123Z",
  "event_type": "model_download",
  "actor": {
    "hospital_id": "hosp_12345",
    "ip_address": "192.168.1.100",
    "user_agent": "FederatedClient/1.0"
  },
  "action": "download_global_model",
  "resource": {
    "model_version": "v1.2.3",
    "model_hash": "sha256:abcdef...",
    "file_size_bytes": 512000000
  },
  "result": "success",
  "metadata": {
    "jwt_id": "uuid-xyz",
    "session_id": "sess-abc"
  }
}

Log Retention:
- Hot storage: 90 days (fast queries)
- Cold storage: 7 years (compliance requirement)
- Immutable storage: AWS S3 Glacier with Object Lock
- Tamper detection: Merkle tree with periodic snapshots

SIEM Integration:
- Forward logs to Splunk/ELK
- Real-time correlation rules
- Automated incident response
- Compliance report generation
```

**Files:**
- `monitoring/audit_logger.py` - Structured logging
- `monitoring/log_aggregator.py` - Log collection
- `scripts/generate_compliance_report.py` - Audit reports

---

## 🔐 Cryptographic Components

### Key Hierarchy

```
Master Key (KMS)
   ↓
Hospital Root Keys (HKDF-SHA256)
   ├─→ Model Encryption Keys (AES-256)
   ├─→ Gradient Encryption Keys (AES-256)
   └─→ Signature Keys (RSA-4096)

Derivation Example:
hospital_key = HKDF(
    master_key,
    info=f"hospital:{hospital_id}",
    salt=hospital_creation_timestamp
)

model_key = HKDF(
    hospital_key,
    info=f"model:{model_version}",
    salt=model_creation_timestamp
)
```

### Digital Signatures

```
Purpose: Verify gradient authenticity (non-repudiation)

Process:
1. Hospital computes gradients: G
2. Serialize: G_bytes = serialize(G)
3. Hash: H = SHA-256(G_bytes)
4. Sign: S = RSA_sign(H, hospital_private_key)
5. Upload: (G_bytes, S, hospital_cert)
6. Server verifies:
   - Verify certificate chain
   - Extract hospital_public_key from cert
   - Verify signature: RSA_verify(H, S, hospital_public_key)
   - Accept only if signature valid

Benefits:
✓ Proves gradient came from legitimate hospital
✓ Prevents gradient injection attacks
✓ Enables audit trail (who contributed what)
✓ Legal non-repudiation for compliance
```

---

## 🏥 Federated Learning Security

### Secure Aggregation Protocol

```
Problem: Even encrypted gradients can leak information
Solution: Secure multi-party computation (Bonawitz et al., 2017)

Protocol (Simplified):
1. Each hospital adds a secret mask to gradients:
   g_masked_i = g_i + mask_i

2. Hospitals pairwise exchange mask shares:
   mask_i = Σ_{j≠i} (h(secret_ij) - h(secret_ji))
   where h() is a hash function

3. Server aggregates masked gradients:
   G_agg = (1/K) Σ g_masked_i

4. Masks cancel out in aggregation:
   G_agg = (1/K) Σ g_i  (true average)

Security:
- Server never sees individual gradients
- Hospitals can't see each other's gradients
- Collusion resistance (up to K-2 corrupted hospitals)
- Dropout tolerance (survives hospital failures)

Implementation:
- Use SEAL library for homomorphic encryption
- Shamir secret sharing for mask distribution
- Paillier cryptosystem for secure summation
```

### Byzantine-Robust Aggregation

```
Attack: Malicious hospital sends poisoned gradients to backdoor model

Defense: Krum Algorithm (Blanchard et al., 2017)

Intuition: Honest gradients cluster together, outliers are malicious

Algorithm:
1. Receive K gradients: {g₁, g₂, ..., g_K}
2. For each gradient g_i:
   - Compute distances to all others: d(g_i, g_j)
   - Sum K-f-2 smallest distances (f = max byzantine)
   - Score_i = Σ_{j ∈ closest} d(g_i, g_j)
3. Select gradient with lowest score (most central)
4. Use that gradient for update (or average top-k)

Alternative: Trimmed Mean
- Sort gradients coordinate-wise
- Remove top/bottom 10% (outliers)
- Average remaining gradients

Comparison:
- Krum: Better for targeted attacks, more computation
- Trimmed Mean: Better for random noise, faster
- Use both: Krum for selection, Trimmed Mean for aggregation
```

### Model Poisoning Detection

```
Detection Methods:

1. Gradient Norm Filtering:
   if ||g_i||₂ > median(||g||₂) + 3·σ:
       flag_as_suspicious()

2. Validation Accuracy Monitoring:
   if accuracy_with_g_i < baseline - threshold:
       reject_gradient()

3. Activation Clustering (Backdoor Detection):
   - Run validation data through model
   - Cluster activation patterns
   - Backdoored models show distinct clusters
   - Chen et al. "Detecting Backdoor Attacks" (2018)

4. Neural Cleanse (Trigger Detection):
   - Reverse-engineer potential triggers
   - Small triggers indicate backdoor
   - Wang et al. "Neural Cleanse" (2019)

Mitigation:
- Reject suspicious gradients
- Weight gradients by reputation score
- Periodically retrain from scratch
- Use consensus mechanisms (majority vote)
```

---

## 📊 Security Metrics & KPIs

```
Metric                              | Target      | Critical Threshold
------------------------------------|-------------|-------------------
Failed authentication rate          | < 0.1%      | > 1% (attack)
Average JWT validation time         | < 10ms      | > 100ms
TLS handshake time                  | < 50ms      | > 500ms
Encryption overhead (gradients)     | < 5%        | > 20%
Rate limit hit rate                 | < 1%        | > 5%
Gradient validation failures        | < 0.01%     | > 0.1%
Audit log write latency             | < 20ms      | > 200ms
Model integrity check time          | < 2s        | > 10s
Key rotation success rate           | 100%        | < 99.9%
Incident response time              | < 15min     | > 1hr
```

---

## 🚀 Implementation Roadmap

### Phase 1: Core Security (Weeks 1-2)
- [ ] JWT authentication with RS256
- [ ] TLS 1.3 configuration
- [ ] AES-256-GCM model encryption
- [ ] Basic rate limiting (Redis)
- [ ] Input validation (Pydantic schemas)

### Phase 2: Monitoring & Logging (Week 3)
- [ ] Prometheus metrics setup
- [ ] Grafana dashboards
- [ ] Audit logging system
- [ ] ELK stack deployment
- [ ] Alert rules configuration

### Phase 3: Advanced Security (Week 4)
- [ ] Differential privacy implementation
- [ ] mTLS for hospital clients
- [ ] Byzantine-robust aggregation
- [ ] Secure multi-party computation
- [ ] Model poisoning detection

### Phase 4: Compliance & Testing (Week 5)
- [ ] HIPAA compliance audit
- [ ] Penetration testing
- [ ] Security documentation
- [ ] Incident response playbook
- [ ] Key rotation procedures

---

## 📚 Literature References

### Federated Learning
1. McMahan et al. "Communication-Efficient Learning of Deep Networks from Decentralized Data" (AISTATS 2017)
2. Li et al. "Federated Optimization in Heterogeneous Networks" (MLSys 2020)
3. Kairouz et al. "Advances and Open Problems in Federated Learning" (2021)

### Privacy & Security
4. Abadi et al. "Deep Learning with Differential Privacy" (CCS 2016)
5. Bonawitz et al. "Practical Secure Aggregation" (CCS 2017)
6. Blanchard et al. "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent" (NIPS 2017)
7. Nasr et al. "Comprehensive Privacy Analysis of Deep Learning" (IEEE S&P 2019)

### Medical AI
8. Rieke et al. "The Future of Digital Health with Federated Learning" (Nature 2020)
9. Rajpurkar et al. "CheXNet: Radiologist-Level Pneumonia Detection" (2017)
10. Sheller et al. "Federated Learning in Medicine" (Nature 2020)
11. Brisimi et al. "Federated Learning of Predictive Models from Federated EHRs" (IJERPH 2018)

### Attack & Defense
12. Bagdasaryan et al. "How To Backdoor Federated Learning" (AISTATS 2020)
13. Wang et al. "Neural Cleanse: Identifying Backdoors" (IEEE S&P 2019)
14. Sun et al. "Can You Really Backdoor Federated Learning?" (NeurIPS 2019)
15. Chen et al. "Detecting Backdoor Attacks" (CCS 2018)

---

## 🎓 Why This System Justifies Security Infrastructure

**Unlike basic inference servers:**

1. **High-Value Target**: Aggregated medical AI model worth millions
2. **Privacy-Critical**: Patient data indirectly encoded in gradients
3. **Compliance**: HIPAA/GDPR mandatory security requirements
4. **Multi-Tenant**: Multiple hospitals = complex access control
5. **Adversarial**: Byzantine hospitals can poison the global model
6. **Long-Term**: Model trained over months = sustained attack surface

**Security is not optional—it's the core requirement.**

