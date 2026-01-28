# CI/CD (Jenkins)

This repository uses **Jenkins** to implement Continuous Integration and Continuous Deployment (CI/CD)
for the **application layer only**.

Infrastructure components are provisioned separately and are **explicitly out of scope** for CI/CD.

---

## Scope

### What Jenkins manages

Jenkins is responsible for:

- Running unit tests with coverage enforcement
- Building application Docker images
- Pushing images to **Google Artifact Registry**
- Deploying application workloads via Helm to Kubernetes

Specifically, Jenkins deploys:

- `rag-orchestrator`
- `streamlit-ui`
- `qdrant-ingestor` (image build only; ingestion is triggered explicitly)

All deployments target the `model-serving` namespace.

---

## Pipeline Overview

The CI/CD pipeline is defined in the root-level `Jenkinsfile`.

High-level stages:

1. Source checkout
2. Unit tests (FastAPI)
3. Coverage quality gate (>= 80%)
4. Docker image build
5. Image push to Artifact Registry
6. Helm upgrade to `model-serving` namespace