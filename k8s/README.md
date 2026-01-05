# Kubernetes Integration for VPN Infrastructure

This directory contains Kubernetes manifests to deploy a management and monitoring layer for the VPN infrastructure. The K8s cluster complements the existing Ansible-managed VPN servers by providing centralized monitoring, logging, and management services.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CONTROL PLANE                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Monitoring    │  │   Dashboards    │  │   APIs &        │     │
│  │   Stack         │  │   & UIs         │  │   Automation    │     │
│  │   (Prometheus,  │  │   (Grafana,     │  │   (Config API,  │     │
│  │   Loki, etc.)   │  │   WG Dashboard) │  │   Cert Manager) │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VPN EDGE LAYER (30+ Servers)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   EUROPE (12)   │  │ NORTH AMERICA   │  │ ASIA PACIFIC    │     │
│  │                 │  │     (10)        │  │     (8)         │     │
│  │ • WireGuard     │  │ • WireGuard     │  │ • WireGuard     │     │
│  │ • OpenVPN       │  │ • OpenVPN       │  │ • OpenVPN       │     │
│  │ • AmneziaWG     │  │ • AmneziaWG     │  │ • AmneziaWG     │     │
│  │ • Node Exporter │  │ • Node Exporter │  │ • Node Exporter │     │
│  │ • Promtail      │  │ • Promtail      │  │ • Promtail      │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

## Components Deployed

### 🔍 Monitoring Stack
- **Prometheus**: Metrics collection from all 30 VPN servers
- **Grafana**: Visualization dashboards for VPN infrastructure
- **Alertmanager**: Alert routing and notification management
- **Node Exporter**: System metrics (deployed via Ansible on VPN servers)
- **WireGuard Exporter**: WireGuard-specific metrics
- **OpenVPN Exporter**: OpenVPN-specific metrics

### 📊 Logging Stack
- **Loki**: Centralized log aggregation
- **Promtail**: Log shipping agent (deployed via Ansible on VPN servers)

### 🛠️ Management Services
- **WireGuard Dashboard**: Centralized WireGuard management interface
- **VPN Config API**: RESTful API for VPN configuration management
- **Backup CronJob**: Automated configuration backups

### 🔐 Security & Access
- **NGINX Ingress**: SSL termination and routing
- **Cert-Manager**: Automated SSL certificate management
- **Basic Auth**: Authentication for management interfaces

## Quick Deployment

### Prerequisites
```bash
# Ensure you have a Kubernetes cluster running
kubectl cluster-info

# Install required operators
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.13.0/cert-manager.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.0/deploy/static/provider/cloud/deploy.yaml
```

### Deploy VPN Infrastructure Management
```bash
# Deploy all components
kubectl apply -k .

# Or deploy specific components
kubectl apply -f namespaces/
kubectl apply -f monitoring/
kubectl apply -f logging/
kubectl apply -f vpn-management/
kubectl apply -f ingress/
```

### Verify Deployment
```bash
# Check all pods are running
kubectl get pods -A

# Check services
kubectl get svc -A

# Check ingress
kubectl get ingress -A
```

## Access Management Interfaces

### Grafana Dashboard
- **URL**: `https://grafana.vpn-infrastructure.local`
- **Username**: `admin`
- **Password**: Check secret `grafana-secrets`

### Prometheus
- **URL**: `https://prometheus.vpn-infrastructure.local`
- **Authentication**: Basic auth (admin/admin123 - change in production)

### WireGuard Dashboard
- **URL**: `https://wg-dashboard.vpn-infrastructure.local`
- **Username**: `admin`
- **Password**: Check secret `wireguard-dashboard-secrets`

### VPN Config API
- **URL**: `https://vpn-api.vpn-infrastructure.local`
- **Authentication**: API key in header `X-API-Key`

## Configuration

### Update Server IPs
Edit the Prometheus configuration to match your actual server IPs:
```bash
kubectl edit configmap prometheus-config -n monitoring
```

### Configure Alerting
Update Alertmanager configuration for your notification channels:
```bash
kubectl edit configmap alertmanager-config -n monitoring
```

### SSL Certificates
Update the cluster issuer with your email:
```bash
kubectl edit clusterissuer letsencrypt-prod
```

## Monitoring Dashboards

### Available Dashboards
1. **VPN Infrastructure Overview**: High-level status of all 30 servers
2. **WireGuard Monitoring**: WireGuard-specific metrics and connections
3. **OpenVPN Monitoring**: OpenVPN-specific metrics and clients
4. **System Monitoring**: CPU, memory, disk, and network metrics

### Key Metrics Monitored
- **Server Health**: CPU, memory, disk usage across all regions
- **VPN Connections**: Active connections per protocol and region
- **Network Traffic**: Bandwidth usage and patterns
- **Security Events**: Failed logins, blocked IPs, security alerts
- **Service Availability**: Uptime and response times

## Alerting Rules

### Critical Alerts
- VPN server down (5+ minutes)
- High CPU usage (>80% for 10+ minutes)
- High memory usage (>85% for 10+ minutes)
- Low disk space (<15%)
- VPN service failures

### Warning Alerts
- High connection counts
- Network errors
- Certificate expiration warnings
- Regional load imbalances

## Backup and Recovery

### Automated Backups
- **Schedule**: Daily at 2 AM UTC
- **Retention**: 7 days local, 30 days in S3
- **Scope**: All VPN configurations from 30 servers
- **Storage**: Kubernetes PVC + S3 bucket

### Manual Backup
```bash
# Trigger manual backup
kubectl create job --from=cronjob/vpn-config-backup manual-backup-$(date +%Y%m%d)
```

### Restore Process
```bash
# List available backups
kubectl exec -it backup-pod -- ls /backup/

# Restore from backup
kubectl exec -it backup-pod -- tar -xzf /backup/vpn-backup-YYYY-MM-DD.tar.gz
```

## Scaling and Performance

### Resource Requirements
- **Minimum**: 4 CPU cores, 8GB RAM, 200GB storage
- **Recommended**: 8 CPU cores, 16GB RAM, 500GB storage
- **High Availability**: 3 master nodes, 6 worker nodes

### Performance Tuning
```bash
# Increase Prometheus retention
kubectl patch deployment prometheus -n monitoring -p '{"spec":{"template":{"spec":{"containers":[{"name":"prometheus","args":["--storage.tsdb.retention.time=90d"]}]}}}}'

# Scale Grafana for high availability
kubectl scale deployment grafana --replicas=2 -n monitoring
```

## Integration with Ansible

### Ansible Playbook Integration
The K8s services integrate with existing Ansible playbooks:

```yaml
# Update Prometheus targets when servers change
- name: Update Prometheus configuration
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: v1
      kind: ConfigMap
      metadata:
        name: prometheus-config
        namespace: monitoring
      data:
        prometheus.yml: "{{ prometheus_config | to_nice_yaml }}"
```

### Automated Configuration Sync
- VPN configurations are automatically synced to K8s ConfigMaps
- Server inventory changes trigger Prometheus target updates
- Certificate renewals are reflected in monitoring dashboards

## Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n <namespace>

# Check logs
kubectl logs <pod-name> -n <namespace>
```

#### Ingress Not Working
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check certificate status
kubectl get certificates -A
```

#### Monitoring Data Missing
```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# Visit http://localhost:9090/targets
```

### Log Collection
```bash
# Collect logs from all components
kubectl logs -l app=prometheus -n monitoring
kubectl logs -l app=grafana -n monitoring
kubectl logs -l app=loki -n logging
```

## Security Considerations

### Network Policies
```bash
# Apply network policies for isolation
kubectl apply -f security/network-policies.yaml
```

### RBAC
```bash
# Review service account permissions
kubectl get clusterrolebindings | grep prometheus
kubectl get rolebindings -A | grep grafana
```

### Secrets Management
```bash
# Rotate secrets regularly
kubectl create secret generic new-secret --from-literal=password=new-password
kubectl patch deployment app -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","env":[{"name":"PASSWORD","valueFrom":{"secretKeyRef":{"name":"new-secret","key":"password"}}}]}]}}}}'
```

## Maintenance

### Regular Tasks
- Monitor resource usage and scale as needed
- Update container images for security patches
- Review and rotate secrets
- Test backup and restore procedures
- Validate monitoring and alerting

### Updates
```bash
# Update all images to latest versions
kubectl set image deployment/prometheus prometheus=prom/prometheus:latest -n monitoring
kubectl set image deployment/grafana grafana=grafana/grafana:latest -n monitoring
```

This Kubernetes integration provides a robust, scalable management layer for your VPN infrastructure while maintaining the proven bare-metal approach for the core VPN services.