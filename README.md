# DevOps Lab API

A simple Python Flask REST API used as the application for the DevOps Lab project.

The application will later be deployed through:

- Docker
- Kubernetes
- Helm
- Terraform
- AWS ECR / EKS
- GitHub Actions
- Jenkins
- ArgoCD
- Prometheus / Grafana
- Loki / OpenTelemetry / Tempo

---

## Application Endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Application information |
| `/health` | Health check |
| `/info` | Environment and version information |

Example response:

```json
{
  "message": "DevOps Lab API is running",
  "version": "1.0.0"
}
```

---

# 1. Run Locally

From the `app` directory:

```bash
cd app
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate it in Git Bash:

```bash
source .venv/Scripts/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
cd src
python app.py
```

The application will be available at:

```text
http://localhost:5000
```

Test:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/info
```

---

# 2. Single-Stage Docker Build

The single-stage Dockerfile is:

```text
app/Dockerfile
```

It uses a single image stage for installing dependencies and running the application.

## Build

From the `app` directory:

```bash
docker build -t devops-lab-api:1.0.0 .
```

Verify the image:

```bash
docker images
```

## Run

```bash
docker run -d \
  --name devops-lab-api \
  -p 5000:5000 \
  devops-lab-api:1.0.0
```

Test:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/info
```

Check logs:

```bash
docker logs devops-lab-api
```

Stop and remove the container:

```bash
docker rm -f devops-lab-api
```

---

# 3. Multi-Stage Docker Build

The multi-stage Dockerfile is:

```text
app/Dockerfile.multistage
```

The purpose of a multi-stage build is to separate:

```text
Build Stage
    ↓
Install dependencies
    ↓
Prepare application
    ↓
Runtime Stage
    ↓
Copy only required runtime artifacts
```

The final image does not need to contain everything that existed in the build stage.

## Build

```bash
docker build \
  -f Dockerfile.multistage \
  -t devops-lab-api:1.0.0-multistage .
```

Verify:

```bash
docker images
```

## Run

```bash
docker run -d \
  --name devops-lab-api-multistage \
  -p 5000:5000 \
  devops-lab-api:1.0.0-multistage
```

Test:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/info
```

Check logs:

```bash
docker logs devops-lab-api-multistage
```

---

# 4. Single-Stage vs Multi-Stage

| Area | Single-Stage | Multi-Stage |
|---|---|---|
| Dockerfile | `Dockerfile` | `Dockerfile.multistage` |
| Complexity | Simple | More complex |
| Build stages | 1 | 2 |
| Build/runtime separation | No | Yes |
| Easy to understand | Yes | Moderate |
| Production suitability | Depends | Generally better |
| Excludes build-time artifacts | No | Yes |
| Smaller image | Not necessarily | Often, depending on workload |

### Important

Multi-stage builds do **not automatically guarantee** a smaller image.

The benefit becomes much larger when the build stage contains things such as:

- Compilers
- Development libraries
- Build tools
- Test dependencies
- Node.js/npm
- Source/build artifacts

For this simple Flask application, the difference may be relatively small because the application already uses the lightweight `python:3.13-slim` image.

---

# 5. Multi-Stage Build Architecture

The current multi-stage Dockerfile uses:

```text
Stage 1: build
-------------------------
python:3.13-slim

WORKDIR /app

requirements.txt
       ↓
pip install
       ↓
/install

src/
       ↓
/app/src


Stage 2: runtime
-------------------------
python:3.13-slim

Copy:
/install → Python site-packages
/app/src → application source

Run:
Gunicorn
```

The important concept is that the second stage starts from a **fresh image**.

Therefore, packages installed in the first stage are not automatically available in the second stage.

They must be explicitly copied.

---

# 6. Docker Troubleshooting Lessons

## Lesson 1 — Understanding `WORKDIR`

When the Dockerfile contains:

```dockerfile
WORKDIR /app
```

and then:

```dockerfile
COPY src/ ./src/
```

the files are copied to:

```text
/app/src
```

Therefore, when copying from another stage:

```dockerfile
COPY --from=build /app/src ./src
```

is different from:

```dockerfile
COPY --from=build src/ ./src/
```

The latter looks for:

```text
/src
```

instead of:

```text
/app/src
```

---

## Lesson 2 — Runtime Stage Is a Fresh Image

A multi-stage Dockerfile such as:

```dockerfile
FROM python:3.13-slim AS build

...

FROM python:3.13-slim
```

creates a new runtime stage.

Packages installed in:

```text
build
```

are not automatically available in:

```text
runtime
```

For example, installing:

```bash
pip install gunicorn
```

in the build stage does not make `gunicorn` available in the runtime stage.

The required runtime dependencies must be copied into the final image.

---

# 7. Environment Variables

The application supports:

```text
APP_VERSION
ENVIRONMENT
```

Example:

```bash
docker run -d \
  --name devops-lab-api \
  -p 5000:5000 \
  -e APP_VERSION=2.0.0 \
  -e ENVIRONMENT=dev \
  devops-lab-api:1.0.0
```

Check:

```bash
curl http://localhost:5000/info
```

Expected response:

```json
{
  "application": "devops-lab-api",
  "environment": "dev",
  "version": "2.0.0"
}
```

This will later be replaced/overridden using Kubernetes environment variables and ConfigMaps.

---

# 8. Health Check

The application provides:

```text
GET /health
```

Example:

```bash
curl http://localhost:5000/health
```

Response:

```json
{
  "status": "healthy"
}
```

This endpoint will later be used for Kubernetes:

- Readiness probes
- Liveness probes
- Application monitoring
- Load balancer health checks

---

# 9. Docker Image Tagging

The image currently uses:

```text
devops-lab-api:1.0.0
```

The multi-stage image uses:

```text
devops-lab-api:1.0.0-multistage
```

Later, the image will be pushed to Amazon ECR using a tag such as:

```text
<account-id>.dkr.ecr.<region>.amazonaws.com/devops-lab-api:1.0.0
```

The CI pipeline will eventually automate:

```text
Git Push
   ↓
GitHub Actions
   ↓
Docker Build
   ↓
Security Scan
   ↓
Push Image to ECR
   ↓
Update GitOps configuration
   ↓
ArgoCD
   ↓
EKS
```

---

# 10. Future Improvements

The application will gradually be extended to demonstrate production DevOps practices.

Planned improvements:

- [ ] Add PostgreSQL
- [ ] Add database connection
- [ ] Add Docker Compose for local development
- [ ] Add Kubernetes Deployment
- [ ] Add Kubernetes Service
- [ ] Add Kubernetes ConfigMap
- [ ] Add Kubernetes Secret
- [ ] Add readiness probe
- [ ] Add liveness probe
- [ ] Add resource requests/limits
- [ ] Add Horizontal Pod Autoscaler
- [ ] Create Helm chart
- [ ] Push image to Amazon ECR
- [ ] Deploy to Amazon EKS
- [ ] Add GitHub Actions CI
- [ ] Add Jenkins CI pipeline
- [ ] Add ArgoCD GitOps
- [ ] Add Prometheus metrics
- [ ] Add Grafana dashboards
- [ ] Add Loki logging
- [ ] Add OpenTelemetry
- [ ] Add Tempo distributed tracing
- [ ] Add security scanning
- [ ] Add automated tests

---

# 11. DevOps Learning Approach

This application is intentionally simple.

The goal is not to build a complex business application.

The goal is to use the same application to learn the complete DevOps lifecycle:

```text
Application
     ↓
Git
     ↓
Docker
     ↓
Container Registry
     ↓
Kubernetes
     ↓
Helm
     ↓
Terraform
     ↓
AWS / EKS
     ↓
CI
     ↓
GitOps / ArgoCD
     ↓
Observability
     ↓
Security
```

The project follows:

```text
BUILD
  ↓
BREAK
  ↓
TROUBLESHOOT
  ↓
AUTOMATE
  ↓
DOCUMENT
  ↓
COMMIT
```
