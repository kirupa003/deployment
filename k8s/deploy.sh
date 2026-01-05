#!/bin/bash
# Kubernetes Deployment Script for VPN Infrastructure Management
# This script deploys the K8s management layer for the VPN infrastructure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}=== VPN Infrastructure Kubernetes Deployment ===${NC}"
echo "Deploying management and monitoring layer for VPN infrastructure"
echo

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}✗${NC} kubectl not found. Please install kubectl."
        exit 1
    fi
    echo -e "${GREEN}✓${NC} kubectl found"
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}✗${NC} Cannot connect to Kubernetes cluster."
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Kubernetes cluster accessible"
    
    # Check if running as cluster admin
    if ! kubectl auth can-i create clusterroles &> /dev/null; then
        echo -e "${YELLOW}!${NC} Warning: May not have cluster admin permissions"
    else
        echo -e "${GREEN}✓${NC} Cluster admin permissions confirmed"
    fi
}

# Function to install required operators
install_operators() {
    echo -e "\n${YELLOW}Installing required operators...${NC}"
    
    # Install cert-manager
    echo "Installing cert-manager..."
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    
    # Wait for cert-manager to be ready
    echo "Waiting for cert-manager to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-cainjector -n cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager
    echo -e "${GREEN}✓${NC} cert-manager installed and ready"
    
    # Install NGINX Ingress Controller
    echo "Installing NGINX Ingress Controller..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.0/deploy/static/provider/cloud/deploy.yaml
    
    # Wait for ingress controller to be ready
    echo "Waiting for NGINX Ingress Controller to be ready..."
    kubectl wait --namespace ingress-nginx \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/component=controller \
        --timeout=300s
    echo -e "${GREEN}✓${NC} NGINX Ingress Controller installed and ready"
}

# Function to create namespaces
create_namespaces() {
    echo -e "\n${YELLOW}Creating namespaces...${NC}"
    kubectl apply -f "$SCRIPT_DIR/namespaces/"
    echo -e "${GREEN}✓${NC} Namespaces created"
}

# Function to deploy monitoring stack
deploy_monitoring() {
    echo -e "\n${YELLOW}Deploying monitoring stack...${NC}"
    
    # Deploy Prometheus
    echo "Deploying Prometheus..."
    kubectl apply -f "$SCRIPT_DIR/monitoring/prometheus/"
    
    # Deploy Grafana
    echo "Deploying Grafana..."
    kubectl apply -f "$SCRIPT_DIR/monitoring/grafana/"
    
    # Deploy Alertmanager
    echo "Deploying Alertmanager..."
    kubectl apply -f "$SCRIPT_DIR/alertmanager/"
    
    echo -e "${GREEN}✓${NC} Monitoring stack deployed"
}

# Function to deploy logging stack
deploy_logging() {
    echo -e "\n${YELLOW}Deploying logging stack...${NC}"
    kubectl apply -f "$SCRIPT_DIR/logging/"
    echo -e "${GREEN}✓${NC} Logging stack deployed"
}

# Function to deploy VPN management services
deploy_vpn_management() {
    echo -e "\n${YELLOW}Deploying VPN management services...${NC}"
    kubectl apply -f "$SCRIPT_DIR/vpn-management/"
    echo -e "${GREEN}✓${NC} VPN management services deployed"
}

# Function to deploy backup services
deploy_backup() {
    echo -e "\n${YELLOW}Deploying backup services...${NC}"
    kubectl apply -f "$SCRIPT_DIR/backup/"
    echo -e "${GREEN}✓${NC} Backup services deployed"
}

# Function to deploy ingress and certificates
deploy_ingress() {
    echo -e "\n${YELLOW}Deploying ingress and certificates...${NC}"
    
    # Deploy cluster issuers
    kubectl apply -f "$SCRIPT_DIR/cert-manager/"
    
    # Deploy ingress
    kubectl apply -f "$SCRIPT_DIR/ingress/"
    
    echo -e "${GREEN}✓${NC} Ingress and certificates deployed"
}

# Function to wait for deployments
wait_for_deployments() {
    echo -e "\n${YELLOW}Waiting for deployments to be ready...${NC}"
    
    # Wait for monitoring stack
    echo "Waiting for Prometheus..."
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring
    
    echo "Waiting for Grafana..."
    kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring
    
    echo "Waiting for Alertmanager..."
    kubectl wait --for=condition=available --timeout=300s deployment/alertmanager -n monitoring
    
    echo "Waiting for Loki..."
    kubectl wait --for=condition=available --timeout=300s deployment/loki -n logging
    
    echo "Waiting for VPN Config API..."
    kubectl wait --for=condition=available --timeout=300s deployment/vpn-config-api -n vpn-management
    
    echo "Waiting for WireGuard Dashboard..."
    kubectl wait --for=condition=available --timeout=300s deployment/wireguard-dashboard -n vpn-management
    
    echo -e "${GREEN}✓${NC} All deployments are ready"
}

# Function to display access information
display_access_info() {
    echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
    echo -e "\n${BLUE}Access Information:${NC}"
    
    # Get ingress IP
    INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    if [ "$INGRESS_IP" = "pending" ] || [ -z "$INGRESS_IP" ]; then
        INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.clusterIP}')
        echo -e "${YELLOW}Note: Using ClusterIP. For external access, set up port forwarding or configure LoadBalancer.${NC}"
    fi
    
    echo -e "\n${BLUE}Management Interfaces:${NC}"
    echo "• Grafana Dashboard: https://grafana.vpn-infrastructure.local"
    echo "  - Username: admin"
    echo "  - Password: admin123 (change in production!)"
    echo
    echo "• Prometheus: https://prometheus.vpn-infrastructure.local"
    echo "  - Basic Auth: admin/admin123 (change in production!)"
    echo
    echo "• WireGuard Dashboard: https://wg-dashboard.vpn-infrastructure.local"
    echo "  - Username: admin"
    echo "  - Password: admin123 (change in production!)"
    echo
    echo "• VPN Config API: https://vpn-api.vpn-infrastructure.local"
    echo "  - API Key required in X-API-Key header"
    echo
    
    if [ "$INGRESS_IP" != "pending" ]; then
        echo -e "${BLUE}DNS Configuration:${NC}"
        echo "Add these entries to your DNS or /etc/hosts:"
        echo "$INGRESS_IP grafana.vpn-infrastructure.local"
        echo "$INGRESS_IP prometheus.vpn-infrastructure.local"
        echo "$INGRESS_IP wg-dashboard.vpn-infrastructure.local"
        echo "$INGRESS_IP vpn-api.vpn-infrastructure.local"
    fi
    
    echo -e "\n${BLUE}Useful Commands:${NC}"
    echo "• Check pod status: kubectl get pods -A"
    echo "• View logs: kubectl logs -f deployment/grafana -n monitoring"
    echo "• Port forward Grafana: kubectl port-forward svc/grafana 3000:3000 -n monitoring"
    echo "• Port forward Prometheus: kubectl port-forward svc/prometheus 9090:9090 -n monitoring"
    
    echo -e "\n${GREEN}✓ VPN Infrastructure Kubernetes management layer deployed successfully!${NC}"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Deploy Kubernetes management layer for VPN infrastructure"
    echo
    echo "Options:"
    echo "  --skip-operators    Skip installation of cert-manager and ingress controller"
    echo "  --monitoring-only   Deploy only monitoring stack"
    echo "  --help             Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Full deployment"
    echo "  $0 --skip-operators   # Skip operator installation"
    echo "  $0 --monitoring-only  # Deploy only monitoring"
}

# Parse command line arguments
SKIP_OPERATORS=false
MONITORING_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-operators)
            SKIP_OPERATORS=true
            shift
            ;;
        --monitoring-only)
            MONITORING_ONLY=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main deployment flow
main() {
    check_prerequisites
    
    if [ "$SKIP_OPERATORS" = false ]; then
        install_operators
    fi
    
    create_namespaces
    deploy_monitoring
    
    if [ "$MONITORING_ONLY" = false ]; then
        deploy_logging
        deploy_vpn_management
        deploy_backup
        deploy_ingress
    fi
    
    wait_for_deployments
    display_access_info
}

# Run main function
main "$@"