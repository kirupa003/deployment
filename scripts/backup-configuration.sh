#!/bin/bash
# Configuration Backup and Versioning Script
# Backs up VPN infrastructure configuration with versioning support

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups/configurations"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="config_backup_${TIMESTAMP}"
MAX_BACKUPS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to create backup directory
create_backup_dir() {
    log "Creating backup directory: ${BACKUP_DIR}/${BACKUP_NAME}"
    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"
}

# Function to backup configuration files
backup_configurations() {
    log "Backing up configuration files..."
    
    local backup_path="${BACKUP_DIR}/${BACKUP_NAME}"
    
    # Backup inventory files
    if [[ -d "${PROJECT_ROOT}/inventories" ]]; then
        log "Backing up inventory files..."
        cp -r "${PROJECT_ROOT}/inventories" "${backup_path}/"
        success "Inventory files backed up"
    else
        warning "Inventories directory not found"
    fi
    
    # Backup playbooks
    if [[ -d "${PROJECT_ROOT}/playbooks" ]]; then
        log "Backing up playbooks..."
        cp -r "${PROJECT_ROOT}/playbooks" "${backup_path}/"
        success "Playbooks backed up"
    else
        warning "Playbooks directory not found"
    fi
    
    # Backup roles
    if [[ -d "${PROJECT_ROOT}/roles" ]]; then
        log "Backing up roles..."
        cp -r "${PROJECT_ROOT}/roles" "${backup_path}/"
        success "Roles backed up"
    else
        warning "Roles directory not found"
    fi
    
    # Backup configuration files
    local config_files=(
        "ansible.cfg"
        "requirements.yml"
        ".vault_pass"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${config_file}" ]]; then
            log "Backing up ${config_file}..."
            cp "${PROJECT_ROOT}/${config_file}" "${backup_path}/"
        else
            warning "Configuration file not found: ${config_file}"
        fi
    done
}

# Function to create backup metadata
create_backup_metadata() {
    log "Creating backup metadata..."
    
    local backup_path="${BACKUP_DIR}/${BACKUP_NAME}"
    local metadata_file="${backup_path}/backup_metadata.json"
    
    # Get git information if available
    local git_commit=""
    local git_branch=""
    local git_status=""
    
    if command -v git >/dev/null 2>&1 && [[ -d "${PROJECT_ROOT}/.git" ]]; then
        git_commit=$(git -C "${PROJECT_ROOT}" rev-parse HEAD 2>/dev/null || echo "unknown")
        git_branch=$(git -C "${PROJECT_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        git_status=$(git -C "${PROJECT_ROOT}" status --porcelain 2>/dev/null | wc -l || echo "unknown")
    fi
    
    # Create metadata JSON
    cat > "${metadata_file}" << EOF
{
    "backup_info": {
        "timestamp": "${TIMESTAMP}",
        "backup_name": "${BACKUP_NAME}",
        "created_by": "$(whoami)",
        "hostname": "$(hostname)",
        "backup_type": "configuration"
    },
    "git_info": {
        "commit": "${git_commit}",
        "branch": "${git_branch}",
        "uncommitted_changes": ${git_status}
    },
    "system_info": {
        "os": "$(uname -s)",
        "kernel": "$(uname -r)",
        "architecture": "$(uname -m)"
    },
    "backup_contents": {
        "inventories": $([ -d "${backup_path}/inventories" ] && echo "true" || echo "false"),
        "playbooks": $([ -d "${backup_path}/playbooks" ] && echo "true" || echo "false"),
        "roles": $([ -d "${backup_path}/roles" ] && echo "true" || echo "false"),
        "ansible_cfg": $([ -f "${backup_path}/ansible.cfg" ] && echo "true" || echo "false"),
        "requirements_yml": $([ -f "${backup_path}/requirements.yml" ] && echo "true" || echo "false")
    }
}
EOF
    
    success "Backup metadata created"
}

# Function to compress backup
compress_backup() {
    log "Compressing backup..."
    
    local backup_path="${BACKUP_DIR}/${BACKUP_NAME}"
    local compressed_file="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    
    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    
    # Remove uncompressed directory
    rm -rf "${BACKUP_NAME}"
    
    success "Backup compressed: ${compressed_file}"
    
    # Show backup size
    local backup_size=$(du -h "${compressed_file}" | cut -f1)
    log "Backup size: ${backup_size}"
}

# Function to cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups (keeping last ${MAX_BACKUPS})..."
    
    cd "${BACKUP_DIR}"
    
    # Count current backups
    local backup_count=$(ls -1 config_backup_*.tar.gz 2>/dev/null | wc -l)
    
    if [[ ${backup_count} -gt ${MAX_BACKUPS} ]]; then
        local to_remove=$((backup_count - MAX_BACKUPS))
        log "Found ${backup_count} backups, removing ${to_remove} oldest..."
        
        # Remove oldest backups
        ls -1t config_backup_*.tar.gz | tail -n ${to_remove} | xargs rm -f
        
        success "Cleaned up ${to_remove} old backups"
    else
        log "No cleanup needed (${backup_count}/${MAX_BACKUPS} backups)"
    fi
}

# Function to list existing backups
list_backups() {
    log "Available configuration backups:"
    
    if [[ -d "${BACKUP_DIR}" ]]; then
        cd "${BACKUP_DIR}"
        
        if ls config_backup_*.tar.gz >/dev/null 2>&1; then
            echo
            printf "%-25s %-15s %-20s\n" "BACKUP NAME" "SIZE" "DATE"
            printf "%-25s %-15s %-20s\n" "----------" "----" "----"
            
            for backup in $(ls -1t config_backup_*.tar.gz); do
                local size=$(du -h "${backup}" | cut -f1)
                local date=$(stat -c %y "${backup}" | cut -d' ' -f1,2 | cut -d'.' -f1)
                printf "%-25s %-15s %-20s\n" "${backup}" "${size}" "${date}"
            done
            echo
        else
            warning "No configuration backups found"
        fi
    else
        warning "Backup directory does not exist: ${BACKUP_DIR}"
    fi
}

# Function to restore backup
restore_backup() {
    local backup_name="$1"
    local backup_file="${BACKUP_DIR}/${backup_name}"
    
    if [[ ! -f "${backup_file}" ]]; then
        error "Backup file not found: ${backup_file}"
        return 1
    fi
    
    log "Restoring backup: ${backup_name}"
    
    # Create restore confirmation
    echo -e "${YELLOW}WARNING: This will overwrite current configuration files!${NC}"
    read -p "Are you sure you want to restore? (yes/no): " confirm
    
    if [[ "${confirm}" != "yes" ]]; then
        log "Restore cancelled"
        return 0
    fi
    
    # Create current backup before restore
    log "Creating backup of current configuration before restore..."
    BACKUP_NAME="pre_restore_$(date +"%Y%m%d_%H%M%S")"
    create_backup_dir
    backup_configurations
    create_backup_metadata
    compress_backup
    
    # Extract and restore
    log "Extracting backup..."
    local temp_dir=$(mktemp -d)
    cd "${temp_dir}"
    tar -xzf "${backup_file}"
    
    local extracted_dir=$(ls -1 | head -n1)
    
    # Restore files
    if [[ -d "${extracted_dir}/inventories" ]]; then
        log "Restoring inventories..."
        rm -rf "${PROJECT_ROOT}/inventories"
        cp -r "${extracted_dir}/inventories" "${PROJECT_ROOT}/"
    fi
    
    if [[ -d "${extracted_dir}/playbooks" ]]; then
        log "Restoring playbooks..."
        rm -rf "${PROJECT_ROOT}/playbooks"
        cp -r "${extracted_dir}/playbooks" "${PROJECT_ROOT}/"
    fi
    
    if [[ -d "${extracted_dir}/roles" ]]; then
        log "Restoring roles..."
        rm -rf "${PROJECT_ROOT}/roles"
        cp -r "${extracted_dir}/roles" "${PROJECT_ROOT}/"
    fi
    
    # Restore config files
    local config_files=("ansible.cfg" "requirements.yml" ".vault_pass")
    for config_file in "${config_files[@]}"; do
        if [[ -f "${extracted_dir}/${config_file}" ]]; then
            log "Restoring ${config_file}..."
            cp "${extracted_dir}/${config_file}" "${PROJECT_ROOT}/"
        fi
    done
    
    # Cleanup
    rm -rf "${temp_dir}"
    
    success "Configuration restored from: ${backup_name}"
}

# Function to show backup info
show_backup_info() {
    local backup_name="$1"
    local backup_file="${BACKUP_DIR}/${backup_name}"
    
    if [[ ! -f "${backup_file}" ]]; then
        error "Backup file not found: ${backup_file}"
        return 1
    fi
    
    log "Extracting backup metadata..."
    local temp_dir=$(mktemp -d)
    cd "${temp_dir}"
    tar -xzf "${backup_file}"
    
    local extracted_dir=$(ls -1 | head -n1)
    local metadata_file="${extracted_dir}/backup_metadata.json"
    
    if [[ -f "${metadata_file}" ]]; then
        echo
        echo "Backup Information:"
        echo "=================="
        
        if command -v jq >/dev/null 2>&1; then
            jq . "${metadata_file}"
        else
            cat "${metadata_file}"
        fi
        echo
    else
        warning "No metadata found in backup"
    fi
    
    rm -rf "${temp_dir}"
}

# Function to show usage
show_usage() {
    cat << EOF
Configuration Backup and Versioning Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    backup              Create a new configuration backup
    list               List all available backups
    restore BACKUP     Restore from specified backup file
    info BACKUP        Show information about a backup
    cleanup            Remove old backups (keeping last ${MAX_BACKUPS})
    help               Show this help message

Examples:
    $0 backup                                    # Create new backup
    $0 list                                      # List all backups
    $0 restore config_backup_20240105_143022.tar.gz  # Restore specific backup
    $0 info config_backup_20240105_143022.tar.gz     # Show backup info
    $0 cleanup                                   # Clean old backups

EOF
}

# Main function
main() {
    local command="${1:-backup}"
    
    case "${command}" in
        "backup")
            log "Starting configuration backup..."
            create_backup_dir
            backup_configurations
            create_backup_metadata
            compress_backup
            cleanup_old_backups
            success "Configuration backup completed: ${BACKUP_NAME}.tar.gz"
            ;;
        "list")
            list_backups
            ;;
        "restore")
            if [[ $# -lt 2 ]]; then
                error "Please specify backup file to restore"
                show_usage
                exit 1
            fi
            restore_backup "$2"
            ;;
        "info")
            if [[ $# -lt 2 ]]; then
                error "Please specify backup file to show info"
                show_usage
                exit 1
            fi
            show_backup_info "$2"
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            error "Unknown command: ${command}"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"