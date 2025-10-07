#!/bin/bash

# ASVS Template Setup Script
# This script downloads and sets up OWASP ASVS templates for the Security Toolkit

set -e

echo "🔧 Setting up OWASP ASVS templates for Security Toolkit..."

# Configuration
ASVS_REPO="https://github.com/OWASP/owasp-asvs-security-evaluation-templates-with-nuclei.git"
INSTALL_DIR="/opt/owasp-asvs-nuclei"
TEMP_DIR="/tmp/asvs-setup"

# Check if running as root for /opt installation
if [[ $EUID -eq 0 ]]; then
    echo "⚠️  Running as root. This will install ASVS templates system-wide."
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
else
    echo "ℹ️  Running as regular user. Will install to user directory."
    INSTALL_DIR="$HOME/owasp-asvs-nuclei"
fi

# Create installation directory
echo "📁 Creating installation directory: $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"
sudo chown $(whoami):$(whoami) "$INSTALL_DIR"

# Clone the repository
echo "📥 Cloning ASVS repository..."
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

git clone "$ASVS_REPO" "$TEMP_DIR"

# Copy templates to installation directory
echo "📋 Copying templates..."
cp -r "$TEMP_DIR/templates"/* "$INSTALL_DIR/"

# Clean up temporary directory
rm -rf "$TEMP_DIR"

# Verify installation
TEMPLATE_COUNT=$(find "$INSTALL_DIR" -name "*.yaml" | wc -l)
echo "✅ Installation complete!"
echo "📊 Found $TEMPLATE_COUNT template files in $INSTALL_DIR"

# Test with the application
echo "🧪 Testing integration..."
cd "$(dirname "$0")"
python3 -c "
from nuclei_integration import nuclei_integration
nuclei_integration.nuclei.register_template_dir('$INSTALL_DIR', source='asvs')
templates = nuclei_integration.nuclei.list_templates(source='asvs')
print(f'✅ Successfully registered {len(templates)} ASVS templates')
"

echo ""
echo "🎉 ASVS setup complete!"
echo ""
echo "Next steps:"
echo "1. Go to the Security Toolkit web interface"
echo "2. Navigate to 'Template Manager' in the sidebar"
echo "3. Click 'Refresh Status' to see the new ASVS templates"
echo "4. Use 'Update All Templates' to refresh the template index"
echo ""
echo "ASVS templates are now available in Active Testing!"
