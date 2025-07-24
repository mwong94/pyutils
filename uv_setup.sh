#!/bin/bash

# UV Setup Script
# Checks for and installs Homebrew and uv on macOS

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
    echo "  -f, --force             Force reinstall even if already installed"
    echo "  -u, --uv-only           Only install uv (skip Homebrew installation)"
    echo "  -b, --brew-only         Only install Homebrew (skip uv installation)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "This script will:"
    echo "  1. Check for and install Homebrew (macOS and Linux)"
    echo "  2. Install uv via Homebrew"
    echo "  3. Install Python 3.13 via uv"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Homebrew
install_homebrew() {
    print_status "Installing Homebrew..."
    
    # Download and run the Homebrew installer
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    print_success "Homebrew installed successfully"
    print_warning "You may need to add Homebrew to your PATH manually:"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [[ $(uname -m) == "arm64" ]]; then
            print_status "  eval \"\$(/opt/homebrew/bin/brew shellenv)\""
        else
            print_status "  eval \"\$(/usr/local/bin/brew shellenv)\""
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_status "  eval \"\$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)\""
    fi
}

# Install uv
install_uv() {
    print_status "Installing uv..."
    
    if command_exists brew; then
        brew install uv
        print_success "uv installed successfully via Homebrew"
    else
        print_warning "Homebrew not found. Installing uv via curl..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        print_success "uv installed successfully via curl"
        print_warning "You may need to add uv to your PATH manually:"
        print_status "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

# Install Python 3.13
install_python() {
    print_status "Installing Python 3.13 via uv..."
    
    if command_exists uv; then
        # Check if Python 3.13 is already installed
        if ! uv python list | grep -q "3.13"; then
            uv python install 3.13
            print_success "Python 3.13 installed successfully"
        else
            print_status "Python 3.13 already available"
        fi
    else
        print_error "uv not found. Cannot install Python 3.13"
        return 1
    fi
}

# Main setup function
main() {
    local force_install=false
    local uv_only=false
    local brew_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                force_install=true
                shift
                ;;
            -u|--uv-only)
                uv_only=true
                shift
                ;;
            -b|--brew-only)
                brew_only=true
                shift
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
    
    # Check operating system
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_status "Starting uv setup for macOS..."
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_status "Starting uv setup for Linux..."
    else
        print_error "This script supports macOS and Linux only."
        exit 1
    fi
    
    # Install Homebrew unless uv-only is specified
    if [[ "$brew_only" == true || "$uv_only" == false ]]; then
        if ! command_exists brew || [[ "$force_install" == true ]]; then
            if [[ "$force_install" == true ]] && command_exists brew; then
                print_warning "Homebrew already installed, but --force specified"
            fi
            install_homebrew
        else
            print_status "Homebrew already installed"
        fi
    fi
    
    # Install uv unless brew-only is specified
    if [[ "$uv_only" == true || "$brew_only" == false ]]; then
        if ! command_exists uv || [[ "$force_install" == true ]]; then
            if [[ "$force_install" == true ]] && command_exists uv; then
                print_warning "uv already installed, but --force specified"
            fi
            install_uv
        else
            print_status "uv already installed"
        fi
        
        # Install Python 3.13 unless brew-only is specified
        if [[ "$brew_only" == false ]]; then
            install_python
        fi
    fi
    
    print_success "Setup completed!"
    
    # Display installation info
    if command_exists brew; then
        print_status "Homebrew version: $(brew --version | head -n1)"
    fi
    
    if command_exists uv; then
        print_status "uv version: $(uv --version)"
        print_status "Available Python versions:"
        uv python list
    fi
    
    print_warning "If commands are not found, you may need to restart your terminal or update your PATH."
}

# Run main function with all arguments
main "$@"
