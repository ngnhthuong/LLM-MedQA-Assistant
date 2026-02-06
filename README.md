# LLM-MedQA-Assistant
**OVERVIEW**
![](assets/imgs/LLM_medQA_assisstant_pipeline.png)

## Table of content
- [Table of content](#table-of-content)
- [Introduction](#introduction)
- [Target Audience](#target-audience)
- [Repo structure](#repo-structure)
- [Guide to setup](#guide-to-setup)
    - [Set up cluster with gke standard](#set-up-cluster-with-gke-standard)
    - [Get kubeconfig and verify cluster ownership](#get-kubeconfig-and-verify-cluster-ownership)
    - [Create Artifact Registry](#create-artifact-registry)
    - [Buid Redis image](#buid-redis-image)
    - [Buid Qdrant image](#buid-qdrant-image)
    - [Buid Streamlit image](#buid-streamlit-image)
    - [Buid rag-orchestrator image](#buid-rag-orchestrator-image)
    - [Buid ingestion image](#buid-ingestion-image)
    - [Create configmap](#create-configmap)
    - [Deploy ingress-nginx namespace](#deploy-ingress-nginx-namespace)
    - [Deploy External LLM Inference Service (GPU via Vast.ai)](#deploy-external-llm-inference-service-(gpu-via-vast.ai))
    - [Deploy model-serving namespace](#deploy-model-serving-namespace)
    - [Deploy monitoring namespace](#deploy-monitoring-namespace)
    - [Deploy logging namespace](#deploy-logging-namespace)
    - [Deploy tracing](#deploy-tracing)
- [Guide to run](#guide-to-run)
- [Conclusion](#conclusion)
- [Reference](#reference)
---
## Introduction
LLM-MedQA-Assisstant is a cloud-native Medical Question Answering platform bulit around a scalable Retrieval-Agumented Generation (RAG) architecture. The system in a Streamlit frontend, a FastAPI based RAG orchestrator, Qdrant vector search for medical knowledge retrieval, and an external fine-tuned medical LLM inference server, with Redis-backed chat history for multi-run conversations. The entire stack is developed on Kubernetes, automated by Terraform, Helm and Jenkins CI/CD, and fully observable through Prometheus, Grafana, and ELK logging pipeline.  
> This repository demonstrates an end-to-end workflow, from git commit and containerized builds to monitored, scalable inference, suitable for well clinical decision support and medical education.  
---
## Target-audience  

This repo is well suited to individuals who's learning MLOPs, and everyone on the journey of becomming ML/LLM engineers.  

---
## Repo structure
```code
LLM-MedQA-Assistant
├── assets                                    # Static assets (images, screenshots, diagrams)
│
├── charts                                    # Helm charts for Kubernetes deployment
│   ├── logging                               # ELK logging stack (Elasticsearch, Logstash, Kibana)
│   │   ├── templates                         # Kubernetes manifests rendered by Helm
│   │   │   ├── elasticsearch-svc.yaml        # Service definition for Elasticsearch
│   │   │   ├── elasticsearch.yaml            # Elasticsearch StatefulSet
│   │   │   ├── filebeat-config.yaml          # Filebeat configuration for log shipping
│   │   │   ├── filebeat-rbac.yaml            # Filebeat RBAC
│   │   │   ├── filebeat-serviceaccount.yaml  # ServiceAccount for Filebeat
│   │   │   ├── filebeat.yaml                 # Filebeat DaemonSet
│   │   │   ├── kibana-svc.yaml               # Service exposing Kibana
│   │   │   ├── kibana.yaml                   # Kibana Deployment
│   │   │   ├── logstash-config.yaml          # Logstash pipeline configuration
│   │   │   ├── logstash-svc.yaml             # Service exposing Logstash
│   │   │   └── logstash.yaml                 # Logstash Deployment
│   │   ├── Chart.yaml                        # Helm chart metadata for logging stack
│   │   └── values.yaml                       # Default values for ELK deployment
│   │
│   ├── model-serving                         # Main application Helm chart (core MedQA platform)
│   │   ├── charts                            # Packaged subcharts (dependencies)
│   │   │   ├── qdrant-0.1.0.tgz              # Qdrant vector database subchart
│   │   │   ├── rag-orchestrator-0.1.0.tgz    # RAG backend subchart
│   │   │   ├── redis-0.1.0.tgz               # Redis subchart (sessions)
│   │   │   └── streamlit-0.1.0.tgz           # Streamlit UI subchart
│   │   ├── templates                         # Helm templates for platform-level resources
│   │   │   ├── _helpers.tpl                  # Shared Helm helper templates
│   │   │   ├── ingress-streamlit.yaml        # Ingress rules for Streamlit UI
│   │   │   ├── ingress.yaml                  # General ingress configuration
│   │   │   ├── namespace.yaml                # Namespace definition for model-serving
│   │   │   ├── qdrant-ingestion-job.yaml     # Job for on-demand document ingestion
│   │   │   └── qdrant-init-job.yaml          # Initialization job for Qdrant collections
│   │   ├── Chart.lock                        # Locked dependency versions
│   │   ├── Chart.yaml                        # Helm chart metadata
│   │   ├── values-dev.yaml                   # Development environment configuration
│   │   ├── values-prod.yaml                  # Production environment configuration
│   │   └── values.yaml                       # Default shared values
│   │
│   ├── monitoring                            # Monitoring stack (Prometheus + Grafana)
│   │   ├── templates
│   │   │   ├── clusterrole.yaml              # RBAC permissions for Prometheus
│   │   │   ├── clusterrolebinding.yaml       # RBAC bindings
│   │   │   ├── grafana-deploy.yaml           # Grafana Deployment
│   │   │   ├── grafana-svc.yaml              # Grafana Service
│   │   │   ├── namespace.yaml                # Monitoring namespace
│   │   │   ├── prometheus-config.yaml        # Prometheus scrape configuration
│   │   │   ├── prometheus-deploy.yaml        # Prometheus Deployment
│   │   │   ├── prometheus-svc.yaml           # Prometheus Service
│   │   │   └── serviceaccount.yaml           # ServiceAccount for monitoring components
│   │   ├── Chart.yaml                        # Monitoring Helm chart metadata
│   │   └── values.yaml                       # Monitoring configuration values
│   │
│   ├── qdrant                                # Standalone Qdrant Helm chart
│   │   ├── templates
│   │   │   ├── service.yaml                  # Qdrant Service
│   │   │   ├── serviceaccount.yaml           # ServiceAccount for Qdrant
│   │   │   └── statefulset.yaml              # Qdrant StatefulSet
│   │   ├── Chart.yaml                        # Qdrant chart metadata
│   │   └── values.yaml                       # Qdrant configuration
│   │
│   ├── rag-orchestrator                      # Helm chart for RAG backend service
│   │   ├── templates
│   │   │   ├── deployment.yaml               # RAG orchestrator Deployment
│   │   │   ├── hpa.yaml                      # Horizontal Pod Autoscaler
│   │   │   ├── service.yaml                  # RAG service exposure
│   │   │   └── serviceaccount.yaml           # ServiceAccount for RAG service
│   │   ├── Chart.yaml                        # RAG orchestrator chart metadata
│   │   └── values.yaml                       # RAG service configuration
│   │
│   ├── redis                                 # Redis Helm chart (session store)
│   │   ├── templates
│   │   │   ├── service.yaml                  # Redis Service
│   │   │   ├── serviceaccount.yaml           # Redis ServiceAccount
│   │   │   └── statefulset.yaml              # Redis StatefulSet
│   │   ├── Chart.yaml                        # Redis chart metadata
│   │   └── values.yaml                       # Redis configuration
│   │
│   ├── streamlit                             # Streamlit UI Helm chart
│   │   ├── templates
│   │   │   ├── deployment.yaml               # Streamlit Deployment
│   │   │   ├── service.yaml                  # Streamlit Service
│   │   │   └── serviceaccount.yaml           # Streamlit ServiceAccount
│   │   ├── Chart.yaml                        # Streamlit chart metadata
│   │   └── values.yaml                       # UI configuration
│   │
│   ├── tracing                               # Distributed tracing stack (OpenTelemetry + Jaeger).
│   │   ├── templates
│   │   │   ├── namespace.yaml                # tracing namespace
│   │   │   ├── otel-collector-config.yaml    # Receivers/exporters
│   │   │   ├── otel-collector-deploy.yaml    # Collector Deployment
│   │   │   ├── otel-collector-svc.yaml       # Collector Service
│   │   │   ├── jaeger-deploy.yaml            # Jaeger backend
│   │   │   └── jaeger-svc.yaml               # Jaeger UI + OTLP
│   │   ├── Chart.yaml                        # tracing chart metadata
│   │   └── values.yaml                       # tracing configuration
│   │
│   └── README.md                             # Helm charts documentation
│
├── ci                                        # CI/CD-related configuration
│   ├── Dockerfile                            # Custom Jenkins Docker image
│   ├── env                                   # Environment variables/templates for CI
│   └── README.md                             # CI/CD documentation
│
├── services                                  # Application-level services
│   ├── qdrant-ingestor                       # Document ingestion service
│   │   ├── app
│   │   │   ├── __init__.py                   # Python package initializer
│   │   │   └── ingest.py                     # Ingestion logic (embedding + indexing)
│   │   ├── data
│   │   │   ├── intro.txt                     # Sample text data
│   │   │   ├── medical_notes.jsonl           # Medical corpus (JSONL format)
│   │   │   └── rad.md                        # Markdown medical content
│   │   ├── Dockerfile                        # Ingestor service image definition
│   │   └── requirements.txt                  # Python dependencies
│   │
│   ├── rag-orchestrator                      # Core RAG backend service
│   │   ├── app
│   │   │   ├── __pycache__                   # Compiled Python cache (runtime)
│   │   │   ├── health.py                     # Health/readiness endpoints
│   │   │   ├── llm_client.py                 # Client for external LLM inference
│   │   │   ├── logging.py                    # Structured logging configuration
│   │   │   ├── main.py                       # FastAPI application entrypoint
│   │   │   ├── metrics.py                    # Prometheus metrics (general)
│   │   │   ├── metrics_llm.py                # LLM-specific metrics
│   │   │   ├── prompt.py                     # Prompt construction logic
│   │   │   ├── retriever.py                  # Vector retrieval from Qdrant
│   │   │   ├── schemas.py                    # Request/response schemas
│   │   │   ├── session.py                    # Redis-backed session management
│   │   │   └── tracing.py                    # OpenTelemetry instrumentation
│   │   ├── tests                             # Unit tests for RAG components
│   │   ├── Dockerfile                        # RAG orchestrator image definition
│   │   ├── pytest.ini                        # Pytest configuration
│   │   └── requirements.txt                  # Python dependencies
│   │
│   └── streamlit-ui                          # Frontend UI service
│       ├── app.py                            # Streamlit application entrypoint
│       ├── Dockerfile                        # UI image definition
│       ├── requirements.txt                  # UI dependencies
│       └── tracing.py                        # OpenTelemetry instrumentation
│
├── terraform                                 # Infrastructure-as-Code (GCP)
│   ├── main.tf                               # Core Terraform resources (VPC, GKE)
│   ├── outputs.tf                            # Exported infrastructure outputs
│   ├── terraform.tfstate                     # Terraform state (local)
│   ├── terraform.tfstate.backup              # Backup Terraform state
│   └── variables.tf                          # Input variables
│
├── Dockerfile.qdrant                         # Custom Qdrant image definition
├── Dockerfile.redis                          # Custom Redis image (AOF enabled)
├── jenkins-gke.json                          # Jenkins GCP service account key
├── Jenkinsfile                               # CI/CD pipeline definition
└── README.md                                 # Project documentation and setup guide
```
---
## Guide to setup
> Quick note: you should create google account platform and start using on free-trial (they provdes roughly 300$ within 90 days), which is good approach to learn and explore.  

---
### Set up cluster with gke standard
This step provides the Google Cloud infrastructure requried to run the MedQA plaform, including networking and a Kubernetes (GKE) environment. 
1. **Authenticate with Google Cloud**  
```code
gcloud auth login
```
2. **Initialize Terraform Working Directory**  
```code
cd terraform
terraform init
```
3. **Review infrastructure Changes**  
```code
terraform plan
```
4. **Provision Infastructure**  
```code
terraform apply
```
5. **Optional: Clean up Subnetwork**  
```code
gcloud container clusters delete gke-medqa \
  --region us-central1 \
  --project aide1-486601

gcloud compute networks subnets delete gke-medqa-subnet \
  --region=us-central1 \
  --project=aide1-486601

gcloud compute networks delete gke-medqa-vpc \
  --project=aide1-486601
```

---
### Get kubeconfig and verify cluster ownership
After provisioning the infrastructure, this steps configures local environment to authenticate with GKE cluster and verifies that you have correct access to Kubernetes control plan  
1. **Get Kubernetes Credentials**  
Fetches the Kubernetes credentials for the specified GKE cluster and allows `kubectl` to authenticate and interact with the cluster 
```code
gcloud container clusters get-credentials gke-medqa \
  --region us-central1 \
  --project aide1-486601
```
2. **Verify**  
```code
kubectl get nodes
kubectl get namespaces
```

---
### Create Artifact Registry
This step sets up Docker Artifact Registry in Google Cloud to store and manage container images for all MedQA services (UI, RAG orchestrator, Ingestor). Using Artifact Registry ensures secure, regional, and scalable image storage integrated with GKE and CI/CD pipelines.
1. **Create Artifact Registry Repository**  
```code
gcloud artifacts repositories create llm-medqa \
  --repository-format=docker \
  --location=us-central1 \
  --description="Images for LLM MedQA Assistant"
```
2. **Verify Repository Creation**
```code
gcloud artifacts repositories list
```

---
### Buid Redis image
Redis is used as the session and chat-history store for multi-run conversations in MedQA system. This steps builds a custom Redis image with persistence enable and pushes it to project's artifact registry so it can be pulled during deployment.  
> Note: The Dockerfile.redis already exists in this repository. No additional file creation is required.  

Redis Dockerfile:
```code
# Dockerfile.redis
FROM redis:7.2-alpine
CMD ["redis-server", "--appendonly", "yes"]
```
Explain: we use the offical lightweight Redis Alpine image, anable Appended-Only file peristence to ensure chat history is not lost on pod restarts

1. **Build Custom Redis Image**  
```code
docker build -f Dockerfile.redis -t redis-custom:7.2 .
```
2. **Tag Image for Artifact Registry**  
```
docker tag redis-custom:7.2 \
  us-central1-docker.pkg.dev/aide1-486601/llm-medqa/redis:7.2
```

3. **Push Image to Artifact Registry**  
```code
docker push us-central1-docker.pkg.dev/aide1-486601/llm-medqa/redis:7.2
```

---
### Buid Qdrant image
Qdrant is used as the vector database for semantic retrieval in the MedQA RAG pipeline. This steps builds a custom Qdrant image and pushes it to the project's Artifact Registry so it can be pulled during deployment
> Note: The Dockerfile.qdrant already exists in this repository. No additional file creation is required.
Qdrant dockerfile:
```code
FROM qdrant/qdrant:v1.11.0
EXPOSE 6333
```
Explain: we use the official Qdrant image at a fixed version, and exposes port 6333, which is the default HTTP API port used by Qdrant

1. **Build Custom Qdrant Image**  
```code
docker build -f Dockerfile.qdrant -t qdrant-custom:1.11.0 .
```
2. **Tag Image for Artifact Registry**  
```code
docker tag qdrant-custom:1.11.0 \
  us-central1-docker.pkg.dev/aide1-486601/llm-medqa/qdrant:1.11.0
```
3. **Push Image to Artifact Registry**  
```code
docker push us-central1-docker.pkg.dev/aide1-486601/llm-medqa/qdrant:1.11.0
```

---
### Buid Streamlit image
The streamlit is used as a frontend for the MedQA system, providing an interactive chat interface for medical question answering.
1. **Build Streamlit UI Image**  
```code
cd services/streamlit-ui
docker build -t streamlit-ui:0.2.2 .
```
2. **Tag Image for Artifact Registry**  
```code
docker tag streamlit-ui:0.2.2 \
  us-central1-docker.pkg.dev/aide1-486601/llm-medqa/streamlit-ui:0.2.2
```
3. **Push Image to Artifact Registry**  
```code
docker push us-central1-docker.pkg.dev/aide1-486601/llm-medqa/streamlit-ui:0.2.2
```

---
### Buid rag-orchestrator image
The RAG Orchestrator is the core backend service of the MedQA platform. It coordinates request handling, vector retrieval from Qdrant, prompt construction, calls to the external medical LLM inference server, and session management via Redis.
1. **Build RAG Orchestrator Image**  
```code
cd services/rag-orchestrator
docker build -f Dockerfile \
  -t us-central1-docker.pkg.dev/aide1-486601/llm-medqa/rag-orchestrator:0.5.2 .
```
2. **Push Image to Artifact Registry**  
```
docker push us-central1-docker.pkg.dev/aide1-486601/llm-medqa/rag-orchestrator:0.5.2
```

---
### Buid ingestion image
The Qdrant Ingestor is responsible for embedding medical documents and indexing them into the Qdrant vector database. This service enables semantic retrieval by transforming raw medical data into searchable vector used by RAG pipeline.
1. **Build Qdrant Ingestor Image**  
```code
cd services/qdrant-ingestor
docker build -t qdrant-ingestor:0.1.6 .
```
2. **Tag Image for Artifact Registry**  
```code
docker tag qdrant-ingestor:0.1.6 \
  us-central1-docker.pkg.dev/aide1-486601/llm-medqa/qdrant-ingestor:0.1.6
```
3. **Push Image to Artifact Registry**  
```code
docker push us-central1-docker.pkg.dev/aide1-486601/llm-medqa/qdrant-ingestor:0.1.6
```

---
### Create configmap
Document ingestion is a computational expensive operation (embedding + vector indexing) and should not be triggered on every deployment.  
For this reason, ingestion is designed as an explicit, on demand process, decoupled from normal service upgrades.
This step explains how medical documents are injected into the pipeline only when needed.  
1. **Create model-serving namespace**  
```code
kubectl create namespace model-serving
```
2. **Create ConfigMap for Medical Documents**  
```code
kubectl create configmap medical-docs \
  --from-file=services/qdrant-ingestor/data/ \
  -n model-serving
```
Explain: we create a Kubernetes ConfigMap containing all medical documents located in `services/qdrant-ingestor/data/`  

3. **Delete ConfigMap (Optional Cleanup)**  
```code
kubectl delete configmap medical-docs -n model-serving
```
Explain: Removes the existing document ConfigMap when documents are updated, new data is added or stale data must be replaced  

4. **Verify Ingestion Job Execution**  
```code
kubectl logs job/qdrant-ingestion -n model-serving
kubectl get job qdrant-ingestion -n model-serving
```
5. **Correct Data Ingestion Workflow (IMPORTANT)**  
To ingest new or updated medical data, follow this sequence exactly:  
    5.1 **Copy new documents (current supports: .txt, .jsonl, .md)**  

    ```code
    services/qdrant-ingestor/data/
    ```  

    5.2 **Enable ingestion in Helm values**  
    Edit values-dev.yaml:

    ```code
    ingestion:
        enabled: true
    ```

    5.3 **Delete existing ConfigMap**  

    ```code
    kubectl delete configmap medical-docs -n model-serving
    ```

    5.4 **Create a new ConfigMap with updated data**  

    ```code
    kubectl create configmap medical-docs \
        --from-file=services/qdrant-ingestor/data/ \
        -n model-serving
    ```
    5.5 **Trigger ingestion via Helm**  
    
    ```code
    helm upgrade
    ```
    5.6 **Disable ingestion after completion**  
    Edit values-dev.yaml:

    ```code
    ingestion:
        enabled: false
    ```
    5.7 **Run helm upgrade again**  
    
    ```code
    helm upgrade
    ```
---

### Deploy ingress-nginx namespace
The NGINX Ingress Controller is reponsible for exposing internal Kubernetes services to external traffic and routing HTTP requests to the appropriate backend services
1. **Add NGINX Ingress Helm Repository**  
```code
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```
2. **Install / Upgrade NGINX Ingress Controller**  
```code
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.watchIngressWithoutClass=true \
  --set controller.service.externalTrafficPolicy=Cluster \
  --set controller.admissionWebhooks.enabled=true
```
Explain params:  
`--install`: Installs the release if it does not already exist.  
`--namespace ingress-nginx`: Isolates ingress resources from application namespaces.  
`--create-namespace`: Automatically creates the namespace if missing.  
`controller.watchIngressWithoutClass=true`: Allows the controller to process Ingress resources without an explicit `ingressClassName`.  
`controller.service.externalTrafficPolicy=Cluster`: Enables cluster-wide load balancing for incoming traffic.  
`controller.admissionWebhooks.enabled=true`: Enables validation webhooks to prevent invalid or conflicting Ingress definitions.  

3. **Verify Ingress Controller Deployment**  
```code
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller
kubectl get endpoints -n ingress-nginx ingress-nginx-controller-admission
```
---

### Deploy External LLM Inference Service (GPU via Vast.ai)
Large Language Model inference requires GPU acceleration, which is not available in this project’s GCP environment due to free-trial limitations. To decouple inference from the Kubernetes cluster and avoid cloud GPU constraints, an external GPU-based inference server is provisioned using Vast.ai.  
This design avoid:
- avoids vendor lock-in
- keeps Kubernetes lightweight
- allows independent scaling of inference workloads

**Prerequisites**  
- A Vast.ai account
- A debit/credit card added to Vast.ai
- Initial balance charged (~ $10 recommended)
- Basic familiarity with HTTP APIs  

**Create vLLM Inference Instance**  
1. Log in to Vast.ai  
2. Choose the vLLM template  
![](assets/imgs/Choose_template.png)
3. Edit the template configuration, set the environment variable:  
![](assets/imgs/Edit_template.png)
```code
VLLM_MODEL = mistralai/Mistral-7B-Instruct-v0.2
```
4. Click “Create and Use”.
5. Select and rent a GPU instance based on availability and budget.

**Verify Inference Server Token**  
Once the instance is running, open the terminal provided by Vast.ai and run:
```code
echo $OPEN_BUTTON_TOKEN
```
Explain: This token is required to authenticate requests to the vLLM inference API. (It acts as a bearer token)

**Verify LLM Inference Endpoint**  
Replace the placeholders below:  
- `INSTANCE_IP`: Public IP of the rented Vast.ai GPU  
- `EXTERNAL_PORT`: Port exposed by the vLLM service  
- `OPEN_BUTTON_TOKEN`: Token obtained from the terminal  
```
curl http://INSTANCE_IP:EXTERNAL_PORT/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer OPEN_BUTTON_TOKEN" \
  -d '{
    "model": "mistralai/Mistral-7B-Instruct-v0.2",
    "prompt": "what is a medical rag?",
    "max_tokens": 128,
    "temperature": 0.6
  }'
```
Then place it into terminal, the expected result is html or answer for the question
*Example:*
```code
curl http://37.41.28.10:42079/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 6757582557d52ccceca1532b67e69804608da4eeef64cc9bb4f2cf0676990025" \
  -d '{
    "model": "mistralai/Mistral-7B-Instruct-v0.2",
    "prompt": "what is a medical rag?",
    "max_tokens": 128,
    "temperature": 0.6
  }'
```
**Edit values-dev.yaml with INSTANCE_IP, EXTERNAL_PORT**  
```code
  llm:
    enabled: true
    baseUrl: "http://INSTANCE_IP:EXTERNAL_PORT"
```

**Create a Kubernetes sercret for OPEN_BUTTON_TOKEN**  
```code
kubectl create secret generic llm-secrets \
  --from-literal=apiKey=OPEN_BUTTON_TOKEN \
  -n model-serving
```
To verify:
```
kubectl get secret llm-secrets -n model-serving
```
>Note: if the OPEN_BUTTON_TOKEN changes, delete it with:
```code
kubectl delete secret llm-secrets -n model-serving
```
---

### Deploy model-serving namespace
This step deploys all core MedQA services into the Kubernetes cluster using Helm, including the Streamlit UI, RAG orchestrator, Redis, Qdrant, and ingestion jobs. The deployment is performed in a dedicated `model-serving` namespace to isolate application workloads from system components.
1. **Build Helm Chart Dependencies**  
```
helm dependency build charts/model-serving
```
2. **Install Model-Serving Release**  
```
helm install model-serving charts/model-serving \
  -n model-serving \
  -f charts/model-serving/values-dev.yaml
```
3. **Uninstall Deployment (Optional)**  
```code
helm uninstall model-serving -n model-serving
```
---

### Deploy monitoring namespace
This step installs the monitoring and observability stack for the MedQA platform. Prometheus is used to scrape metrics from services, while Grafana provides dashboards and visualization for system health, performance, and LLM-specific metrics.
1. **Build Helm Chart Dependencies**  
```code
helm dependency build charts/monitoring
```
2. **Install Monitoring Stack**  
```code
helm install monitoring charts/monitoring \
  --namespace monitoring \
  --create-namespace
```
3. **Verify Monitoring Deployment**  
```code
kubectl get pods -n monitoring
```
4. **Access Prometheus UI**  
```code
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```
5. **Access Grafana UI**  
```code
kubectl port-forward -n monitoring svc/grafana 3000:3000
```
6. **Default Credentials**  
```code
Username: admin
Password: admin
```
7. **Steps to setup monitoring**  
In the Gradana UI, we add new data source:  
Connections -> Data sources -> Add new data source -> Select prometheus -> Put `http://prometheus.monitoring.svc.cluster.local:9090` into section `Prometheus server URL` -> Click Save & Test -> Build a dashboard (if passed)
![](assets/imgs/Gradana_UI_choose_datd_source.png)  
Create a new dashboard:
![alt text](assets/imgs/Create_a_new_dashboard.png)  
Enter a PromQL query: `rate(process_cpu_seconds_total[1m])`, rename title as `CPU resource` -> Click Save  
![alt text](assets/imgs/Enter_monitoring_params.png)  
Do the same thing with the following PromQL queries:
```
LLM request rate:
sum(rate(llm_requests_total[1m])) by (model, status)

P95 LLM latency:
histogram_quantile(
  0.95,
  sum(rate(llm_inference_latency_seconds_bucket[5m])) by (le)
)

Token usage growth:
rate(llm_prompt_tokens_total[5m])
rate(llm_completion_tokens_total[5m])
```
---

### Deploy logging namespace
This step installs the centralized logging stack for the MedQA platform. The logging namespace collects, stores, and visualizes logs from Kubernetes workloads and system components, enabling effective debugging, auditing, and operational monitoring.
1. **Install Logging Stack**  
```code
helm install logging charts/logging \
  --namespace logging \
  --create-namespace
```
2. **Verify Logging Deployment**  
```code
kubectl get pods -n logging
kubectl get svc -n logging
```

3. **Access Kibana UI**  
```code
kubectl port-forward -n logging svc/kibana 5601:5601
```

4. **Cleanup Logging Stack (Optional)**  
```code
kubectl delete namespace logging --wait=true
```
=>This concludes the end-to-end setup process.

---
### Deploy tracing
This steps installs a tracing feature that tracks multiple services in the system. Tracing is implemented using OpenTelemetry and Jaeger  
1. **Build Helm Chart Dependencies**  
```code
helm dependency update charts/tracing
```
2. **Install tracing**  
```code
helm upgrade --install tracing charts/tracing --namespace tracing --create-namespace
```
3. **Verify and access Jaeger**  
```code
kubectl get pods -n tracing
kubectl port-forward -n tracing deploy/jaeger 16686:16686
```
---
## Guide to run
To open Streamlit, get IP exposed by ingress-nginx
``` code
kubectl get svc -n ingress-nginx
```
![](assets/imgs/Open_Streamlit.png)

---

## Conclusion  
This repository demonstrates an end-to-end, production-grade LLM-powered Medical Question Answering platform, designed with real-world constraints, scalability, and operational reliability in mind. Rather than focusing solely on model inference, the system emphasizes full lifecycle engineering—from infrastructure provisioning and CI/CD automation to observability, controlled data ingestion, and modular deployment.

---

## Reference
This repo idea is inspired by various projects from section `Hall of frame` of the community named "FSDS", check out their page: [LINK](https://fullstackdatascience.com/hall-of-fame)