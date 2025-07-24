#!/bin/bash

# JupyterLab Setup Script
# Sets up JupyterLab with useful extensions and configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -e, --extensions-only    Only install extensions (skip JupyterLab installation)"
    echo "  -c, --config-only        Only configure JupyterLab (skip installation and extensions)"
    echo "  -v, --virtual-env NAME   Use specific virtual environment"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "This script will:"
    echo "  1. Install JupyterLab"
    echo "  2. Install useful extensions"
    echo "  3. Configure JupyterLab settings"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Determine the target directory and basename for virtual environment
get_venv_paths() {
    local venv_name="$1"
    local target_dir=""
    local venv_basename=""
    
    if [[ "$venv_name" = /* ]] || [[ "$venv_name" = ./* ]] || [[ "$venv_name" = ../* ]]; then
        # venv_name is a path (absolute or relative)
        target_dir="$(dirname "$venv_name")"
        venv_basename="$(basename "$venv_name")"
        print_status "Using custom directory: $target_dir"
    else
        # venv_name is just a name, use default .virtualenvs directory
        target_dir="$HOME/.virtualenvs"
        venv_basename="$venv_name"
    fi
    
    echo "$target_dir" "$venv_basename"
}

# Create virtual environment using uv
create_venv_uv() {
    local target_dir="$1"
    local venv_basename="$2"
    local venv_name="$3"
    
    cd "$target_dir"
    uv venv --python 3.13 "$venv_basename"
    
    # Determine the full path for activation
    if [[ "$venv_name" = /* ]] || [[ "$venv_name" = ./* ]] || [[ "$venv_name" = ../* ]]; then
        echo "$venv_name"
        source "$venv_name/bin/activate"
    else
        echo "$target_dir/$venv_basename"
        source "$target_dir/$venv_basename/bin/activate"
    fi
}

# Create virtual environment using python3
create_venv_python3() {
    local target_dir="$1"
    local venv_basename="$2"
    local venv_name="$3"
    
    # Determine the full path for creation and activation
    if [[ "$venv_name" = /* ]] || [[ "$venv_name" = ./* ]] || [[ "$venv_name" = ../* ]]; then
        python3 -m venv "$venv_name"
        echo "$venv_name"
        source "$venv_name/bin/activate"
    else
        python3 -m venv "$target_dir/$venv_basename"
        echo "$target_dir/$venv_basename"
        source "$target_dir/$venv_basename/bin/activate"
    fi
    
    # Upgrade pip in the new environment
    pip install --upgrade pip
}

# Install JupyterLab
install_jupyterlab() {
    print_status "Installing JupyterLab..."
    
    if command_exists uv; then
        uv pip install --upgrade jupyterlab
        uv pip install --upgrade notebook
    elif command_exists pip; then
        pip install --upgrade jupyterlab
        pip install --upgrade notebook
    else
        print_error "Neither uv nor pip found. Please install Python and pip first."
        exit 1
    fi
    
    print_success "JupyterLab installed successfully"
}

# Install useful JupyterLab extensions
install_extensions() {
    print_status "Installing JupyterLab extensions..."
    
    # Core extensions
    local extensions=(
        "jupyterlab-git"
        "jupyterlab-lsp"
        "python-lsp-server[all]"
        "jupyterlab_code_formatter"
        "black"
        "isort"
        "lckr-jupyterlab-variableinspector"
        "jupyterlab_widgets"
        "ipywidgets"
        "plotly"
        "jupyter-dash"
        "jupyterlab-spreadsheet"
        "jupyterlab_execute_time"
    )
    
    for extension in "${extensions[@]}"; do
        print_status "Installing $extension..."
        if command_exists uv; then
            uv pip install "$extension" || print_warning "Failed to install $extension"
        else
            pip install "$extension" || print_warning "Failed to install $extension"
        fi
    done
    
    # Enable server extensions
    jupyter server extension enable --py jupyterlab_git
    jupyter server extension enable --py jupyterlab_code_formatter
    
    print_success "Extensions installed successfully"
}

# Configure JupyterLab
configure_jupyterlab() {
    print_status "Configuring JupyterLab..."
    
    # Create config directory if it doesn't exist
    local config_dir="$HOME/.jupyter"
    mkdir -p "$config_dir"
    
    # Create JupyterLab config
    cat > "$config_dir/jupyter_lab_config.py" << 'EOF'
# JupyterLab Configuration

c = get_config()

# Server configuration
c.ServerApp.ip = '127.0.0.1'
c.ServerApp.port = 8888
c.ServerApp.open_browser = True
c.ServerApp.allow_remote_access = False

# File browser configuration
c.ServerApp.root_dir = '.'

# Security
c.ServerApp.disable_check_xsrf = False

# Logging
c.Application.log_level = 'INFO'

# Extensions
c.LabApp.check_for_updates_class = 'jupyterlab.handlers.LabConfig'
EOF

    # Create user settings directory
    local settings_dir="$HOME/.jupyter/lab/user-settings"
    mkdir -p "$settings_dir/@jupyterlab/notebook-extension"
    mkdir -p "$settings_dir/@jupyterlab/fileeditor-extension"
    mkdir -p "$settings_dir/@jupyterlab/codemirror-extension"
    mkdir -p "$settings_dir/@ryantam626/jupyterlab_code_formatter"

    # Configure notebook settings
    cat > "$settings_dir/@jupyterlab/notebook-extension/tracker.jupyterlab-settings" << 'EOF'
{
    "codeCellConfig": {
        "lineNumbers": true,
        "fontFamily": "Monaco, Menlo, 'Ubuntu Mono', monospace",
        "fontSize": 13
    },
    "markdownCellConfig": {
        "lineNumbers": true,
        "fontFamily": "Monaco, Menlo, 'Ubuntu Mono', monospace",
        "fontSize": 13
    }
}
EOF

    # Configure code formatter
    cat > "$settings_dir/@ryantam626/jupyterlab_code_formatter/settings.jupyterlab-settings" << 'EOF'
{
    "preferences": {
        "default_formatter": {
            "python": "black"
        }
    },
    "black": {
        "line_length": 88,
        "string_normalization": true
    },
    "isort": {
        "multi_line_output": 3,
        "include_trailing_comma": true,
        "force_grid_wrap": 0,
        "use_parentheses": true,
        "line_length": 88
    }
}
EOF

    # Configure file editor
    cat > "$settings_dir/@jupyterlab/fileeditor-extension/plugin.jupyterlab-settings" << 'EOF'
{
    "editorConfig": {
        "lineNumbers": true,
        "fontFamily": "Monaco, Menlo, 'Ubuntu Mono', monospace",
        "fontSize": 13,
        "tabSize": 4,
        "insertSpaces": true
    }
}
EOF

    print_success "JupyterLab configured successfully"
}

# Main setup function
main() {
    local extensions_only=false
    local config_only=false
    local venv_name=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--extensions-only)
                extensions_only=true
                shift
                ;;
            -c|--config-only)
                config_only=true
                shift
                ;;
            -v|--venv)
                venv_name="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Check homebrew installation (macOS only)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command_exists brew; then
            print_warning "Homebrew not found. Some extensions may not work properly."
            print_status "You can install Homebrew from: https://brew.sh"
        else
            print_status "Homebrew found"
            
            # Install uv if not already installed
            if ! command_exists uv; then
                print_status "Installing uv via Homebrew..."
                brew install uv
                print_success "uv installed successfully"
            else
                print_status "uv already installed"
            fi
            
            # Install Python 3.13 using uv if not already available
            if ! uv python list | grep -q "3.13"; then
                print_status "Installing Python 3.13 via uv..."
                uv python install 3.13
                print_success "Python 3.13 installed successfully"
            else
                print_status "Python 3.13 already available"
            fi
        fi
    else
        print_error "This script is currently designed for macOS only."
        print_error "The script relies on Homebrew for installing uv and Python 3.13."
        print_error "Please install uv and Python 3.13 manually on your system:"
        print_status "1. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        print_status "2. Install Python 3.13: uv python install 3.13"
        print_status "3. Then re-run this script"
        exit 1
    fi
    
    # Activate virtual environment if specified
    local actual_venv_path=""
    if [[ -n "$venv_name" ]]; then
        if [[ -d "$HOME/.virtualenvs/$venv_name" ]]; then
            # Standard virtualenvs directory
            source "$HOME/.virtualenvs/$venv_name/bin/activate"
            actual_venv_path="$HOME/.virtualenvs/$venv_name"
            print_status "Activated virtual environment: $venv_name"
        elif [[ -d "$venv_name" ]]; then
            # Direct path to existing venv
            source "$venv_name/bin/activate"
            actual_venv_path="$venv_name"
            print_status "Activated virtual environment: $venv_name"
        else
            # Create new virtual environment
            print_status "Virtual environment not found, creating: $venv_name"
            
            # Get target directory and basename
            read -r target_dir venv_basename <<< "$(get_venv_paths "$venv_name")"
            mkdir -p "$target_dir"
            
            # Create the virtual environment
            if command_exists uv; then
                actual_venv_path="$(create_venv_uv "$target_dir" "$venv_basename" "$venv_name")"
                print_success "Created and activated virtual environment: $venv_name (Python 3.13)"
            elif command_exists python3; then
                print_warning "uv not found, falling back to python3 venv"
                actual_venv_path="$(create_venv_python3 "$target_dir" "$venv_basename" "$venv_name")"
                print_success "Created and activated virtual environment: $venv_name"
            else
                print_error "Neither uv nor python3 found. Please install Python 3 or uv first."
                exit 1
            fi
        fi
    fi
    
    print_status "Starting JupyterLab setup..."
    
    # Install JupyterLab unless extensions-only or config-only
    if [[ "$extensions_only" == false && "$config_only" == false ]]; then
        install_jupyterlab
    fi
    
    # Install extensions unless config-only
    if [[ "$config_only" == false ]]; then
        install_extensions
    fi
    
    # Configure JupyterLab unless extensions-only
    if [[ "$extensions_only" == false ]]; then
        configure_jupyterlab
    fi
    
    print_success "JupyterLab setup completed!"
    print_status "You can now start JupyterLab with: jupyter lab"
    
    if [[ -n "$actual_venv_path" ]]; then
        print_status "Remember to activate your virtual environment: source $actual_venv_path/bin/activate"
    fi
}

# Run main function with all arguments
main "$@"