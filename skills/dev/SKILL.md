---
name: dev
description: Start local development environment with Skaffold
disable-model-invocation: true
allowed-tools: Bash, Read
---

# Start Local Development

Start the PlotPals local development environment using Skaffold and Kubernetes.

## Prerequisites

- Docker running
- kubectl configured
- Helm installed

## Quick Start

```bash
# Using Makefile
make dev

# Or directly
./bin/skaffold
```

## Manual Setup

```bash
# 1. Start minikube (if using minikube)
minikube start --memory 8192 --cpus 4

# 2. Enable ingress
minikube addons enable ingress

# 3. Install infrastructure
helm upgrade --install plotpals-infra ./helm/plotpals-infra \
  -f helm/plotpals-infra/values.yaml \
  -n plotpals-infra --create-namespace

# 4. Start Skaffold dev mode
skaffold dev -f skaffold.yaml
```

## Services Started

| Service | Local Port | Description |
|---------|-----------|-------------|
| http | 8080 | REST API |
| wss | 8081 | WebSocket |
| admin | (via ingress) | Admin dashboard |
| postgres | 5432 | Database |
| redis | 6379 | Cache |
| nats | 4222 | Message broker |

## Port Forwarding

```bash
# API
kubectl port-forward svc/plotpals-http 8080:8080 -n plotpals

# Database
kubectl port-forward svc/plotpals-infra-postgres 5432:5432 -n plotpals-infra
```

## Cleanup

```bash
make clean
# Or
skaffold delete && helm uninstall plotpals-server -n plotpals
```
