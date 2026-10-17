# Lessons Learned and Troubleshooting

This document records practical issues encountered while building and operating the DevOps Lab API.

The objective is to preserve the diagnostic process, explain why commands are useful, and avoid treating an unverified hypothesis as a confirmed root cause.

## 1. Docker build context and file paths

### Problem

A Docker build failed because the source file or directory referenced by `COPY` could not be found.

### Lesson

Docker resolves `COPY` source paths relative to the build context, not relative to the Dockerfile's directory automatically.

For example, from the repository root:

```bash
docker build -t devops-lab-api:1.0.0 ./app
```

The build context is `./app`.

With:

```dockerfile
WORKDIR /app
COPY src/ ./src/
```

the source directory `src/` is taken from the build context, and the destination becomes `/app/src/`.

### Troubleshooting

Check:

- The current working directory.
- The final argument passed to `docker build`.
- The path of the source file relative to the build context.
- Whether `.dockerignore` excludes the required files.

## 2. Multi-stage Docker builds

### Problem

Files or dependencies installed in the build stage were missing from the runtime image.

### Explanation

Each `FROM` instruction starts a new build stage. A later stage does not automatically inherit files installed in an earlier stage unless it uses that stage as its base or explicitly copies the required artifacts.

Example:

```dockerfile
FROM python:3.13-slim AS build

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim

WORKDIR /app
```

The final stage starts from a fresh image. Packages installed into the first stage are not automatically present in the second stage.

### Lesson

Explicitly copy or install every artifact and runtime dependency needed by the final image.

Multi-stage builds are particularly useful when build-time tools are not required at runtime. They do not guarantee a smaller image in every case.

## 3. Kubernetes readiness and liveness probes

### Observed problem

The API intermittently returned connection failures through port-forwarding. Kubernetes also recorded:

- `Readiness probe failed`.
- `Liveness probe failed`.
- `connection refused`.
- `context deadline exceeded`.
- `Container ... failed liveness probe, will be restarted`.

The application subsequently responded successfully to direct health checks.

### Probe configuration during the investigation

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3
```

### What these observations mean

- **Connection refused:** the connection could not be established at the target address and port at that time.
- **Probe timeout:** Kubernetes did not receive a successful response within the configured timeout.
- **Readiness failure:** Kubernetes marks the container as not ready, affecting whether it receives normal Service traffic.
- **Liveness failure:** after enough consecutive failures, Kubernetes can restart the container.

A successful health check at one moment does not prove that the endpoint is always responsive.

### Diagnostic commands

Inspect pods:

```bash
kubectl get pods -n argocd-lab -o wide
```

Inspect probe configuration and events:

```bash
kubectl describe pod <pod-name> -n argocd-lab
```

Inspect the latest events:

```bash
kubectl get events -n argocd-lab --sort-by='.lastTimestamp'
```

Inspect the previous container's logs after a restart:

```bash
kubectl logs <pod-name> -n argocd-lab --previous --tail=100
```

Test the health endpoint from within the cluster:

```bash
kubectl run api-check \
  -n argocd-lab \
  --image=curlimages/curl:8.12.1 \
  --restart=Never \
  --command -- \
  curl -sS -w '\nHTTP %{http_code} | time %{time_total}s\n' \
  --max-time 5 \
  http://argocd-lab-api-service:8080/health
```

Retrieve the result:

```bash
kubectl logs api-check -n argocd-lab
```

Remove the temporary diagnostic pod:

```bash
kubectl delete pod api-check -n argocd-lab
```

### Confirmed findings versus hypotheses

Confirmed during the investigation:

- All three replicas successfully returned HTTP 200 from direct `/health` requests at the time of testing.
- The Service successfully returned HTTP 200 from `/health`.
- Kubernetes recorded intermittent probe timeouts and connection refusals.
- Liveness-probe failures led to container restarts.
- The deployment uses resource requests of 100m CPU and 64Mi memory, with limits of 200m CPU and 128Mi memory.
- The original Dockerfile did not explicitly configure a Gunicorn worker count.
[O
Not conclusively established:

- Whether the failures were caused by CPU throttling.
- Whether memory pressure contributed.
- Whether a Gunicorn worker was blocked.
- Whether browser cache or local browser behaviour contributed to the access symptoms.
- Whether the two-worker configuration resolved the underlying problem.

### Lesson

Do not immediately change probes, CPU limits, and memory limits together. Collect evidence, make one controlled change, and observe the result.

## 4. Gunicorn worker configuration

### Original configuration

The Dockerfile originally launched Gunicorn without an explicit worker count:

```dockerfile
ENTRYPOINT ["gunicorn"]
CMD ["--bind", "0.0.0.0:5000", "src.app:app"]
```

### Experimental configuration

The Dockerfile was changed to:

```dockerfile
ENTRYPOINT ["gunicorn"]
CMD ["--workers", "2", "--bind", "0.0.0.0:5000", "src.app:app"]
```

The updated image was deployed through the existing CI/CD and GitOps workflow.

### Verification

The container's process command line was inspected without installing extra packages:

```bash
kubectl exec -n argocd-lab \
  deployment/argocd-lab-api-app -- \
  python -c "from pathlib import Path; print(Path('/proc/1/cmdline').read_bytes().replace(bytes([0]), b' ').decode())"
```

The output confirmed:

```text
/usr/local/bin/python3.13 /usr/local/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 src.app:app
```

### Why two workers might help

With synchronous workers, one worker handles a request at a time. If one worker blocks, another worker may still be able to serve requests.

However, additional workers consume additional memory. The container has a 128Mi memory limit, so this change must be evaluated against actual resource usage.

### Result

The API subsequently responded successfully through curl and browser access, and all three replicas were observed with zero restarts shortly after deployment.

This is encouraging, but it does not establish that the worker change was the root-cause fix. The browser issue also stopped reproducing, and the investigation did not isolate all possible causes.

### Lesson

Record the configuration change, verify that it reached the running container, and monitor the outcome before declaring a root cause.

## 5. Port-forwarding and browser access

### Port-forward command

```bash
kubectl port-forward svc/argocd-lab-api-service 8080:8080 -n argocd-lab
```

The local port is `8080`. The Service receives traffic on port `8080` and forwards it to the application container on port `5000`.

The command must remain running while the local endpoint is accessed.

### Observed behaviour

During the earlier investigation, the port-forward process reported connection failures to the target container and lost its connection. Later, a new port-forward worked, and browser access recovered.

The normal browser initially failed while incognito worked; subsequently, both worked.

### Lesson

A port-forward failure does not automatically mean that the Service configuration is wrong. A connection to a pod can fail if the selected container restarts or is temporarily unavailable.

Similarly, a browser-specific failure and a Kubernetes probe failure should be investigated separately. Browser cache was a possible explanation for the browser symptom, but it was not proven to explain the Kubernetes restarts.

### Useful checks

Test the API directly through the local port-forward:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/version
```

Test the Service from inside the cluster:

```bash
kubectl run api-check \
  -n argocd-lab \
  --image=curlimages/curl:8.12.1 \
  --restart=Never \
  --command -- \
  curl -sS --max-time 5 \
  http://argocd-lab-api-service:8080/health
```

If browser access fails while curl succeeds, inspect the browser request and local connection before changing the Kubernetes configuration.

## 6. Minimal container images and missing utilities

### Problem

This command failed:

```bash
kubectl exec -n argocd-lab \
  deployment/argocd-lab-api-app -- \
  sh -c 'ps -ef | grep "[g]unicorn"'
```

Error:

```text
sh: 1: ps: not found
```

### Explanation

The application uses `python:3.13-slim`, which does not necessarily include the `ps` utility.

The failure was caused by a missing diagnostic utility; it did not demonstrate that Gunicorn was absent or failing.

### Alternative

Inspect PID 1's command line through `/proc` using Python:

```bash
kubectl exec -n argocd-lab \
  deployment/argocd-lab-api-app -- \
  python -c "from pathlib import Path; print(Path('/proc/1/cmdline').read_bytes().replace(bytes([0]), b' ').decode())"
```

This verifies the master process command line. It does not independently prove that all expected worker processes are alive.

### Lesson

Minimal images reduce unnecessary packages, but troubleshooting may require alternative tools or temporary diagnostic containers.

## 7. Git push rejected because the remote has new commits

### Error

```text
! [rejected] main -> main (fetch first)
error: failed to push some refs
```

### Explanation

The remote `main` branch contains commits not present in the local branch. In this project, GitHub Actions can update the Helm values file automatically after publishing an image, so local and remote branches can diverge.

### Safe recovery

First inspect the branch state:

```bash
git fetch origin
git status
git log --oneline --graph --decorate -8 --all
```

If the local commit is ready and the working tree is clean:

```bash
git pull --rebase origin main
```

If there are conflicts, resolve them deliberately and continue the rebase only after checking the affected files.

Then:

```bash
git push origin main
```

### Lesson

Do not force-push simply to bypass a non-fast-forward rejection. Preserve the remote GitOps changes and integrate them safely.

## 8. GitHub Actions and Argo CD image promotion

### Implemented workflow

The pipeline performs the following operations:

1. Detect application changes.
2. Run automated tests.
3. Build and publish the container image.
4. Use the Git commit SHA as an image tag.
5. Update the Helm values file with the new tag.
6. Commit and push the updated GitOps configuration.
7. Allow Argo CD to synchronize the desired deployment state.

### Verification commands

Check the running image:

```bash
kubectl get deployment argocd-lab-api-app \
  -n argocd-lab \
  -o jsonpath='{.spec.template.spec.containers[*].image}{"\n"}'
```

Check rollout status:

```bash
kubectl rollout status deployment/argocd-lab-api-app -n argocd-lab
```

Check replica status:

```bash
kubectl get deployment,replicaset,pods -n argocd-lab
```

### Important distinction

Argo CD uses Helm to render Kubernetes resources. An empty output from `helm list -n argocd-lab` does not necessarily mean that the Argo CD-managed application is not deployed as expected.

Verify the Argo CD Application and live Kubernetes resources when investigating a GitOps deployment.

## 9. General troubleshooting principles

1. Reproduce the failure before changing configuration.
2. Separate symptoms occurring in the browser, port-forward, Service, pod, and container.
3. Inspect the actual configuration deployed to Kubernetes.
4. Use direct pod checks and Service checks to isolate networking from application behaviour.
5. Inspect previous container logs after restarts.
6. Do not assume exit code 137 alone proves an out-of-memory kill.
7. Do not assume a successful request proves that an intermittent problem is resolved.
8. Make one controlled change at a time.
9. Prefer Git-based changes for GitOps-managed resources.
10. Record what was observed, what changed, and whether the result was conclusive.

## 10. Investigation status

The intermittent liveness-probe failures have not been conclusively explained. The deployment later ran successfully with two Gunicorn workers, and browser access recovered.

Continue observing restart counts and probe events before treating the issue as resolved. If it returns, use new evidence to choose the next diagnostic step rather than repeating checks that have already been completed.


