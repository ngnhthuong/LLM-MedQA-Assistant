# About Helm chart designs

This document describes the **Kubernetes pod architecture**, **workload types**, and **components communication** used in the LLM-MedQA-Assistant platform.

The system is designed following **namespace separation**, **stateless vs stateful workload patterns**, and **observability**.

---

## 1. Namespace Responsibilities

| Namespace        | Responsibility |
|------------------|----------------|
| `ingress-nginx`  | Traffic entry into the cluster |
| `model-serving`  | Core application logic, RAG pipeline, vector DB, sessions |
| `logging`        | Centralized log collection, parsing, storage, and visualization |
| `monitoring`     | Metrics scraping, storage, and dashboards |

---

## 2. Ingress Namespace

### Purpose
Handles **external HTTP/HTTPS traffic** and routes it to internal services using Kubernetes Ingress resources.

### Pods

| Pod | Pod Type | What it does | Why this type | Communicates with | How it communicates |
|----|---------|--------------|--------------|------------------|---------------------|
| ingress-nginx-controller | Deployment | Acts as Kubernetes Ingress Controller | Stateless controller pattern defined by ingress-nginx Helm chart | Streamlit service (`model-serving`) | HTTP/HTTPS via Ingress rules → ClusterIP Service |

**Why Deployment?**  
Ingress controllers do not store state and can be horizontally scaled for availability.

---

## 3. Logging Namespace (ELK Stack)

### Purpose
Provides **cluster-wide log aggregation** using a classic **ELK + Beats** pipeline.

### Pods

| Pod | Pod Type | What it does | Why this type | Communicates with | How it communicates |
|----|---------|--------------|--------------|------------------|---------------------|
| elasticsearch-0 | StatefulSet | Stores logs and indices | Requires stable identity & persistent storage (PVC) | Logstash, Kibana | TCP 9200 |
| logstash-* | Deployment | Parses and forwards logs | Stateless pipeline workers | Elasticsearch | TCP 9200 |
| kibana-* | Deployment | Visualizes logs | Stateless UI | Elasticsearch | HTTP 9200 |
| filebeat-* | DaemonSet | Collects node & pod logs | Must run on every node | Logstash | TCP 5044 |

**Why DaemonSet for Filebeat?**  
Log agents must run **1 pod per node** to access `/var/log` and container logs reliably.

---

## 4. Model-Serving Namespace

### Purpose
Hosts the **RAG pipeline**, **vector database**, **session storage**, and **UI**.

### Data & Storage Components

| Pod | Pod Type | What it does | Why this type | Communicates with | How it communicates |
|----|---------|--------------|--------------|------------------|---------------------|
| qdrant-0 | StatefulSet | Stores vector embeddings | Persistent DB with PVC | RAG Orchestrator | HTTP (6333) via ClusterIP |
| redis-0 | StatefulSet | Session storage | Stateful in-memory DB | RAG Orchestrator | TCP 6379 |

### Initialization Jobs

| Pod | Pod Type | What it does | Why this type | Communicates with | How it communicates |
|----|---------|--------------|--------------|------------------|---------------------|
| qdrant-init-* | Job | Initializes Qdrant collections | One-time bootstrap task | Qdrant | HTTP bootstrap calls |

### Application Layer

| Pod | Pod Type | What it does | Why this type | Communicates with | How it communicates |
|----|---------|--------------|--------------|------------------|---------------------|
| rag-orchestrator-* | Deployment | Handles RAG pipeline logic | Stateless API service | Redis, Qdrant, external LLM | HTTP + Redis TCP |
| streamlit-* | Deployment | User interface | Stateless frontend | RAG Orchestrator | HTTP via Service |

**Key Design Principle:**  
Only **datastores** are StatefulSets.  
All **business logic and UI** are Deployments.

---

## 5. Monitoring Namespace

### Purpose
Provides **metrics collection and visualization** for workloads and infrastructure.

### Pods

| Pod | Pod Type | What it does | Why this type | Communicates with | How it communicates |
|----|---------|--------------|--------------|------------------|---------------------|
| prometheus-* | Deployment | Scrapes & stores metrics | Config-driven, no PVC | All metrics endpoints | HTTP scrape |
| grafana-* | Deployment | Metrics visualization | Stateless UI | Prometheus | HTTP queries |

---

## 6. Service Topology

| Component | Namespace | Service Name | Service Type | Purpose |
|---------|----------|--------------|--------------|--------|
| Streamlit UI | model-serving | streamlit | ClusterIP | Internal UI exposed via Ingress |
| RAG Orchestrator | model-serving | rag-orchestrator | ClusterIP | Internal API |
| Qdrant | model-serving | qdrant | ClusterIP | Vector DB access |
| Redis | model-serving | redis | ClusterIP | Session store |
| Elasticsearch | logging | elasticsearch | ClusterIP | Log storage |
| Logstash | logging | logstash | ClusterIP | Log ingestion |
| Kibana | logging | kibana | ClusterIP | Log visualization |
| Prometheus | monitoring | prometheus | ClusterIP | Metrics backend |
| Grafana | monitoring | grafana | ClusterIP | Metrics UI |

**Design Choice:**  
All services are **ClusterIP**.  
External exposure is handled **only by Ingress**, not by LoadBalancers per service.

---

## 7. Workload Type Comparison

| Criteria | Deployment | StatefulSet | DaemonSet |
|--------|------------|------------|-----------|
| Has state | X | O | X |
| Stable pod name | X | O | X |
| Uses PVC | X | O | X |
| Scales replicas | X | O | X |
| One pod per node | X | X | O |
| Typical usage | API / UI | DB / Storage | Agents |

---

## 8. Architectural Summary

- **Clear separation of concerns by namespace**
- **Ingress-only external exposure**
- **Stateful components isolated and minimal**
- **Observability treated as first-class (logs + metrics)**
- **Ready for future NetworkPolicy hardening**

This layout reflects **Kubernetes design** and supports scalability, observability, and maintainability.

---
