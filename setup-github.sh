#!/bin/bash

# VPN Master Panel - GitHub Setup Script
# This script helps you quickly push your project to GitHub

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Functions
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

clear
echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║       🚀 VPN MASTER PANEL - GITHUB SETUP WIZARD 🚀           ║
║                                                              ║
║          Quick and Easy GitHub Repository Setup             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed!"
    echo ""
    print_info "Installing Git..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update && sudo apt install -y git
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install git
    else
        print_error "Please install Git manually: https://git-scm.com/downloads"
        exit 1
    fi
    
    print_success "Git installed!"
fi

echo ""
print_info "Current directory: $(pwd)"
echo ""

# Check if already a git repo
if [ -d .git ]; then
    print_warning "This is already a Git repository!"
    read -p "Do you want to continue? (y/n): " continue_choice
    if [[ "$continue_choice" != "y" ]]; then
        exit 0
    fi
else
    # Initialize git
    print_info "Initializing Git repository..."
    git init
    print_success "Git repository initialized!"
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}         GIT CONFIGURATION             ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

# Check if git is configured
git_name=$(git config --global user.name 2>/dev/null || echo "")
git_email=$(git config --global user.email 2>/dev/null || echo "")

if [ -z "$git_name" ] || [ -z "$git_email" ]; then
    print_info "Git is not configured yet. Let's set it up!"
    echo ""
    
    if [ -z "$git_name" ]; then
        read -p "Enter your name (e.g., John Doe): " user_name
        git config --global user.name "$user_name"
    else
        print_info "Name: $git_name"
        read -p "Change name? (y/n): " change_name
        if [[ "$change_name" == "y" ]]; then
            read -p "Enter your name: " user_name
            git config --global user.name "$user_name"
        fi
    fi
    
    if [ -z "$git_email" ]; then
        read -p "Enter your email: " user_email
        git config --global user.email "$user_email"
    else
        print_info "Email: $git_email"
        read -p "Change email? (y/n): " change_email
        if [[ "$change_email" == "y" ]]; then
            read -p "Enter your email: " user_email
            git config --global user.email "$user_email"
        fi
    fi
    
    print_success "Git configured!"
else
    print_info "Git is already configured:"
    echo "  Name: $git_name"
    echo "  Email: $git_email"
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}      GITHUB REPOSITORY SETUP          ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

print_info "Please create a repository on GitHub first:"
print_info "1. Go to: https://github.com/new"
print_info "2. Repository name: vpn-master-panel"
print_info "3. Keep it Public (recommended for open source)"
print_info "4. Do NOT initialize with README, .gitignore, or license"
print_info "5. Click 'Create repository'"
echo ""

read -p "Have you created the GitHub repository? (y/n): " repo_created
if [[ "$repo_created" != "y" ]]; then
    print_warning "Please create the repository first, then run this script again."
    exit 0
fi

echo ""
read -p "Enter your GitHub username: " github_username
read -p "Enter repository name [vpn-master-panel]: " repo_name
repo_name=${repo_name:-vpn-master-panel}

GITHUB_URL="https://github.com/${github_username}/${repo_name}.git"

echo ""
print_info "Repository URL: $GITHUB_URL"
echo ""

# Check for sensitive files
print_info "Checking for sensitive files..."

sensitive_found=0

if [ -f .env ] && ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    print_warning "Found .env file! This should not be committed."
    sensitive_found=1
fi

if grep -r "password\|api_key\|secret_key" . --exclude-dir={venv,node_modules,.git} -l 2>/dev/null | grep -v ".gitignore" | head -5; then
    print_warning "Found files that may contain passwords or keys!"
    sensitive_found=1
fi

if [ $sensitive_found -eq 1 ]; then
    echo ""
    print_warning "⚠️  SECURITY WARNING ⚠️"
    print_warning "Sensitive files detected! Please review before continuing."
    echo ""
    read -p "Continue anyway? (y/n): " continue_sensitive
    if [[ "$continue_sensitive" != "y" ]]; then
        print_info "Aborting. Please remove sensitive data first."
        exit 0
    fi
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}         COMMITTING FILES              ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

# Add all files
print_info "Adding all files to Git..."
git add .

# Show status
echo ""
print_info "Files to be committed:"
git status --short

echo ""
read -p "Commit message [Initial commit: VPN Master Panel v1.0.0]: " commit_message
commit_message=${commit_message:-"Initial commit: VPN Master Panel v1.0.0"}

print_info "Creating commit..."
git commit -m "$commit_message"
print_success "Commit created!"

echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}        PUSHING TO GITHUB               ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

# Add remote
if git remote get-url origin &> /dev/null; then
    print_info "Remote 'origin' already exists. Updating..."
    git remote set-url origin "$GITHUB_URL"
else
    print_info "Adding remote repository..."
    git remote add origin "$GITHUB_URL"
fi

# Rename branch to main if needed
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    print_info "Renaming branch to 'main'..."
    git branch -M main
fi

print_info "Pushing to GitHub..."
echo ""
print_warning "You may need to enter your GitHub credentials:"
print_info "- Username: Your GitHub username"
print_info "- Password: Personal Access Token (NOT your GitHub password!)"
echo ""
print_info "To create a token:"
print_info "1. Go to: https://github.com/settings/tokens"
print_info "2. Generate new token (classic)"
print_info "3. Select 'repo' scope"
print_info "4. Copy the token and use it as password"
echo ""

if git push -u origin main; then
    print_success "Successfully pushed to GitHub! 🎉"
else
    print_error "Push failed!"
    echo ""
    print_info "Common issues:"
    print_info "1. Authentication failed - Use Personal Access Token"
    print_info "2. Repository not empty - Force push with: git push -f origin main"
    print_info "3. Network issues - Check your internet connection"
    echo ""
    read -p "Do you want to force push? (y/n): " force_push
    if [[ "$force_push" == "y" ]]; then
        print_warning "Force pushing..."
        git push -f origin main
        print_success "Force push completed!"
    else
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     SUCCESS! 🎉                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Your repository is now live at:${NC}"
echo -e "${YELLOW}https://github.com/${github_username}/${repo_name}${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo "1. Visit your repository and add topics (vpn, docker, fastapi, react)"
echo "2. Add a description in the About section"
echo "3. Review and update README.md with correct URLs"
echo "4. Consider adding screenshots or demo video"
echo "5. Share your project on social media!"
echo ""
echo -e "${CYAN}To update your repository in the future:${NC}"
echo "  git add ."
echo "  git commit -m \"your message\""
echo "  git push"
echo ""
print_success "Happy coding! 🚀"
