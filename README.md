# DevOps Lab API

A Flask REST API used to practise an end-to-end DevOps workflow, from application development and automated testing to containerization, Kubernetes deployment, and GitOps-based delivery.

The goal is to build, deploy, troubleshoot, automate, and document the same application while progressively introducing production-oriented DevOps practices.

## Project status

| Component | Status |
|---|---|
| Python Flask API | Implemented |
| Automated application tests | Implemented |
| Single-stage Docker build | Implemented |
| Multi-stage Docker build experiment | Available |
| Docker Hub image publishing | Implemented |
| GitHub Actions CI pipeline | Implemented |
| Kubernetes Deployment and Service | Implemented |
| ConfigMaps and Secrets | Implemented |
| Readiness and liveness probes | Implemented |
| Resource requests and limits | Implemented |
| Helm chart | Implemented |
| Argo CD GitOps deployment | Implemented |
| Automated image-tag promotion | Implemented |
| Gunicorn worker configuration experiment | In progress |
| Terraform and AWS ECR/EKS | Planned |
| Observability and security scanning | Planned |

## Architecture

### Current deployment workflow

```text
Developer changes application code
              |
              v
         GitHub main
              |
              v
       GitHub Actions
              |
       +------+------+
       |             |
   Run tests     Build image
                     |
                     v
              Docker Hub
                     |
                     v
         Update Helm image tag
              in Git repository
                     |
                     v
                  Argo CD
                     |
                     v
            Helm chart rendering
                     |
                     v
            Kind Kubernetes cluster
                     |
                     v
          Deployment: 3 replicas
                     |
                     v
              ClusterIP Service
                     |
                     v
                Flask API
```

GitHub Actions validates application changes, builds and publishes a versioned container image, and updates the image tag in the Helm values file. Argo CD watches the Git repository and reconciles the Kubernetes resources with the declared configuration.

The application is currently deployed to a local Kind cluster. AWS EKS and ECR are future extensions.

## Repository structure

```text
devops-lab/
├── app/
│   ├── src/
│   │   └── app.py
│   ├── tests/
│   │   └── test_app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── Dockerfile.multistage
├── helm/
│   └── devops-lab-api/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-dev.yaml
│       └── templates/
│           ├── deployment.yaml
│           └── service.yaml
├── argocd/
│   └── applications/
│       └── devops-lab-api-dev.yaml
├── .github/
│   └── workflows/
│       └── ci.yaml
├── docs/
│   └── lessons-learned-troubleshooting.md
└── README.md
```

This is the logical structure of the main project components; additional manifests and files may exist in the repository.

## Application endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Application welcome message and version |
| `/health` | Health-check endpoint |
| `/info` | Application, environment, and version information |
| `/version` | Application version and build metadata |

Example health response:

```json
{
  "status": "healthy"
}
```

Example version response:

```json
{
  "application": "devops-lab-api",
  "build": "unknown",
  "environment": "dev",
  "version": "1.0.0"
}
```

The `build` value is `unknown` when `BUILD_SHA` is not configured for the running application.

## 1. Run locally

Run the following commands from the repository root in Git Bash.

Create and activate a virtual environment:

```bash
cd app
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Run the application:

```bash
python src/app.py
```

The application is available at:

```text
http://localhost:5000
```

Test the endpoints:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/info
curl http://localhost:5000/version
```

Run the automated tests from the `app` directory:

```bash
python -m pytest -v
```

## 2. Build and run with Docker

The main Dockerfile is:

```text
app/Dockerfile
```

Build the image from the repository root:

```bash
docker build -t devops-lab-api:1.0.0 ./app
```

Run the container:

```bash
docker run -d \
  --name devops-lab-api \
  -p 5000:5000 \
  devops-lab-api:1.0.0
```

Test the application:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/info
curl http://localhost:5000/version
```

Inspect logs:

```bash
docker logs devops-lab-api
```

Remove the container:

```bash
docker rm -f devops-lab-api
```

### Multi-stage build

The experimental multi-stage Dockerfile is:

```text
app/Dockerfile.multistage
```

It demonstrates separating build-time dependencies from the final runtime image. Dependencies required at runtime must be explicitly available in the final stage. Multi-stage builds do not automatically guarantee a smaller image.

## 3. CI pipeline

The GitHub Actions workflow is:

```text
.github/workflows/ci.yaml
```

The implemented workflow covers:

1. Detecting application changes.
2. Installing dependencies and running tests.
3. Building the Docker image.
4. Publishing a commit-SHA-tagged image to Docker Hub.
5. Updating the image tag in `helm/devops-lab-api/values-dev.yaml`.
6. Committing and pushing the GitOps configuration update.
7. Allowing Argo CD to reconcile the deployment.

The workflow uses GitHub repository secrets for Docker Hub authentication:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

The workflow also needs appropriate repository write permissions to update the Helm values file.

Image repository:

```text
vinodhk92/devops-lab-api
```

The commit SHA is used as the image tag so the deployed image can be associated with a particular source revision.

## 4. Kubernetes deployment

The application is deployed to a local Kind cluster in the `argocd-lab` namespace.

The current deployment configuration includes:

- Three replicas.
- A ClusterIP Service.
- ConfigMap and Secret references.
- Readiness and liveness HTTP probes.
- CPU and memory requests and limits.
- An application container listening on port `5000`.
- A Service exposing port `8080`.

Inspect the resources:

```bash
kubectl get deployment,service,replicaset,pods -n argocd-lab
```

Inspect the deployment:

```bash
kubectl describe deployment argocd-lab-api-app -n argocd-lab
```

Inspect application logs:

```bash
kubectl logs deployment/argocd-lab-api-app -n argocd-lab
```

### Access the API locally

Run the port-forward command in a dedicated Git Bash terminal:

```bash
kubectl port-forward svc/argocd-lab-api-service 8080:8080 -n argocd-lab
```

Keep this terminal running while accessing the application.

Test from another terminal or your browser:

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/info
curl http://localhost:8080/version
```

Browser URLs:

```text
http://localhost:8080/
http://localhost:8080/health
http://localhost:8080/info
http://localhost:8080/version
```

Port-forwarding is for local development and testing, not a production ingress solution.

## 5. Helm and Argo CD

The Helm chart is located at:

```text
helm/devops-lab-api/
```

The development values file is:

```text
helm/devops-lab-api/values-dev.yaml
```

The Argo CD Application manifest is:

```text
argocd/applications/devops-lab-api-dev.yaml
```

Argo CD tracks the Git repository and deploys the Helm chart using the development values file. Helm renders the Kubernetes manifests; Argo CD manages their synchronization with the cluster.

Useful commands:

```bash
kubectl get applications -n argocd
kubectl get pods -n argocd-lab
kubectl get events -n argocd-lab --sort-by='.lastTimestamp'
```

The exact namespace of the Argo CD Application resource depends on the installed Argo CD configuration.

### GitOps principle

Avoid manually editing live Kubernetes resources to make permanent configuration changes.

Instead:

1. Change the application or Helm configuration in Git.
2. Commit and push the change.
3. Let GitHub Actions run the relevant pipeline.
4. Let Argo CD reconcile the desired state.
5. Verify the rollout.

This keeps Git as the source of truth for the deployment configuration.

## 6. Environment configuration

The application supports:

```text
APP_VERSION
ENVIRONMENT
BUILD_SHA
```

For local Docker testing:

```bash
docker run --rm \
  -p 5000:5000 \
  -e APP_VERSION=2.0.0 \
  -e ENVIRONMENT=dev \
  -e BUILD_SHA=local-test \
  devops-lab-api:1.0.0
```

Check:

```bash
curl http://localhost:5000/version
```

In Kubernetes, environment values can be supplied through ConfigMaps, Secrets, and explicit container environment settings.

Do not store real credentials in Git. Use appropriate secret-management mechanisms.

## 7. Troubleshooting

Detailed troubleshooting notes are maintained in:

```text
docs/lessons-learned-troubleshooting.md
```

Topics include:

- Docker build context and `WORKDIR`.
- Multi-stage image dependencies.
- Kubernetes Service and pod health checks.
- Readiness and liveness probe failures.
- Container restarts and resource limits.
- Port-forward behaviour.
- Git non-fast-forward push rejections.
- GitHub Actions image promotion and Argo CD reconciliation.
- Gunicorn worker configuration experiments.

## 8. Roadmap

### Application and containers

- [x] Build a Flask API.
- [x] Add automated tests.
- [x] Build Docker images.
- [x] Publish images to Docker Hub.
- [ ] Add PostgreSQL and database integration.
- [ ] Add Docker Compose for local development.

### Kubernetes and delivery

- [x] Deploy the application to Kind.
- [x] Configure Deployment and Service resources.
- [x] Configure ConfigMaps and Secrets.
- [x] Configure readiness and liveness probes.
- [x] Configure resource requests and limits.
- [x] Create a Helm chart.
- [x] Configure Argo CD GitOps.
- [x] Automate image-tag promotion through Git.
- [ ] Add and validate an ingress solution.
- [ ] Practise persistent volumes, StatefulSets, and NetworkPolicies.

### Cloud, security, and observability

- [ ] Provision AWS infrastructure using Terraform.
- [ ] Push images to Amazon ECR.
- [ ] Deploy to Amazon EKS.
- [ ] Add security scanning.
- [ ] Add Prometheus and Grafana.
- [ ] Add centralized logging with Loki.
- [ ] Explore OpenTelemetry and Tempo.
- [ ] Explore SRE and platform engineering practices.

## 9. Learning approach

The project follows an iterative engineering workflow:

```text
BUILD
  ↓
TEST
  ↓
DEPLOY
  ↓
OBSERVE
  ↓
TROUBLESHOOT
  ↓
AUTOMATE
  ↓
DOCUMENT
  ↓
COMMIT
```

The objective is not to build a complex business application. It is to demonstrate the engineering practices required to build, deploy, operate, and troubleshoot software reliably.

