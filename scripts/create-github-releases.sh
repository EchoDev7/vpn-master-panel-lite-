#!/bin/bash

###############################################################################
#  GitHub Version Release Script
#  Automates the process of creating version tags and releases
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}VPN Master Panel - GitHub Version Release${NC}\n"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: Not a git repository${NC}"
    echo "Run: git init"
    exit 1
fi

# Check if remote is set
if ! git remote get-url origin &> /dev/null; then
    echo -e "${YELLOW}No remote 'origin' found${NC}"
    read -p "Enter your GitHub repository URL: " REPO_URL
    git remote add origin "$REPO_URL"
    echo -e "${GREEN}✅ Remote added${NC}"
fi

# Function to create and push version
create_version() {
    local VERSION=$1
    local BRANCH=$2
    local MESSAGE=$3
    
    echo -e "\n${BLUE}Creating version $VERSION...${NC}"
    
    # Create branch
    git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
    
    # Add all files
    git add .
    
    # Commit
    git commit -m "$MESSAGE" || echo "No changes to commit"
    
    # Create tag
    git tag -a "$VERSION" -m "Version $VERSION"
    
    # Push branch and tag
    git push origin "$BRANCH"
    git push origin "$VERSION"
    
    echo -e "${GREEN}✅ Version $VERSION created and pushed${NC}"
}

# Main menu
echo "Select version to create:"
echo "1) v1.0.0 - Initial Release"
echo "2) v2.0.0 - Professional Dashboard"
echo "3) v3.0.0 - Enterprise Features"
echo "4) All versions (recommended for first time)"
echo "5) Exit"

read -p "Enter choice [1-5]: " CHOICE

case $CHOICE in
    1)
        create_version "v1.0.0" "v1.0" "Release v1.0.0 - Initial Release

Features:
- Basic dashboard
- User management
- OpenVPN support
- WireGuard support
- Basic monitoring"
        ;;
    2)
        create_version "v2.0.0" "v2.0" "Release v2.0.0 - Professional Dashboard

New Features:
- 16 new frontend components
- Real-time notifications (database-backed)
- Activity timeline (database-backed)
- Advanced analytics
- QR code generation
- Data export (CSV/JSON)
- Audit logs
- Backup & restore
- Systemd auto-start services

Bug Fixes:
- Fixed notifications static count
- Fixed activity timeline mock data
- Fixed SQLAlchemy reserved keyword
- Fixed dashboard 500 error
- Fixed missing npm dependencies"
        ;;
    3)
        create_version "v3.0.0" "v3.0" "Release v3.0.0 - Enterprise Features

New Enterprise Features:
- WebSocket real-time communication
- Multi-language support (English, Persian with RTL)
- Email notifications (SMTP + 4 templates)
- Telegram bot integration (6 commands)
- Automatic SSL setup (Let's Encrypt)
- Subscription management system

Technical Details:
- 32 new files created
- 8 new API endpoints
- 3 new database models
- Full async/await support
- Production-ready error handling

Dependencies:
- Added react-i18next, i18next
- Added aiosmtplib, jinja2
- Added python-telegram-bot
- See requirements-enterprise.txt for full list"
        ;;
    4)
        echo -e "${YELLOW}Creating all versions...${NC}"
        
        # v1.0.0
        create_version "v1.0.0" "v1.0" "Release v1.0.0 - Initial Release"
        
        # Back to main
        git checkout main
        
        # v2.0.0
        create_version "v2.0.0" "v2.0" "Release v2.0.0 - Professional Dashboard"
        
        # Back to main
        git checkout main
        
        # v3.0.0
        create_version "v3.0.0" "v3.0" "Release v3.0.0 - Enterprise Features"
        
        # Merge v3.0 to main
        git checkout main
        git merge v3.0 --no-ff -m "Merge v3.0 to main"
        git push origin main
        
        echo -e "\n${GREEN}✅ All versions created successfully!${NC}"
        ;;
    5)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Version Release Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Go to: https://github.com/YOUR_USERNAME/vpn-master-panel-lite/releases"
echo "2. Click 'Draft a new release'"
echo "3. Select the tag you just created"
echo "4. Add release notes from release_notes_vX.md files"
echo "5. Publish release"

echo -e "\n${YELLOW}Or use GitHub CLI:${NC}"
echo "gh release create v1.0.0 --notes-file release_notes_v1.md"
echo "gh release create v2.0.0 --notes-file release_notes_v2.md"
echo "gh release create v3.0.0 --notes-file release_notes_v3.md"
