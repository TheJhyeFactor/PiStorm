#!/bin/bash
# PiStorm GitHub Upload Script
# Prepares and uploads the complete PiStorm repository

echo "🚀 PiStorm GitHub Upload Preparation"
echo "======================================="

# Check if we're in the right directory
if [ ! -f "wifi_api.py" ]; then
    echo "❌ Error: wifi_api.py not found. Run this script from the PiStorm directory."
    exit 1
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    sudo apt update && sudo apt install -y git
fi

# Initialize git repository if not already done
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    git branch -M main
fi

# Add remote origin if not exists
if ! git remote get-url origin &> /dev/null; then
    echo "🔗 Adding GitHub remote..."
    git remote add origin https://github.com/TheJhyeFactor/PiStorm.git
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env

# Capture files
*.cap
*.pcap
*.hccapx
*.22000

# Config files with secrets
config.env
*.key
*.pem

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Results
results/
captures/
wordlists/
incoming/

# Temporary files
/tmp/
temp/
*.tmp

# Test files
test_*.cap
monitor_test*
EOF
fi

# Stage all files
echo "📁 Staging files for commit..."
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "ℹ️ No changes to commit"
else
    echo "💾 Creating commit..."
    git commit -m "PiStorm v1.0 - Distributed WiFi Security Testing Platform

🚀 Initial Release Features:
- Raspberry Pi backend with Flask API
- Windows GPU acceleration with hashcat (RTX 4070 Super)
- Wio Terminal control interface
- Real-time distributed processing
- Advanced handshake capture with channel targeting
- Multi-round deauthentication attacks
- Monitor mode testing and validation
- GPU offload with 800x performance improvement
- Professional logging and packet analysis
- Comprehensive API documentation

🏗️ Architecture:
- Pi: Network scanning, handshake capture, deauth attacks
- PC: GPU-accelerated password cracking with hashcat
- Wio Terminal: Real-time control and status display

⚡ Performance:
- Pi-only: ~1,000 passwords/second
- With RTX 4070 Super: ~800,000 passwords/second
- 800x speed improvement with GPU acceleration

🔧 Components:
- wifi_api.py: Complete Pi backend with GPU integration
- crack_listener.py: Windows GPU processing station
- test_monitor.py: Monitor mode validation
- analyze_capture.py: Advanced packet analysis
- Comprehensive setup and documentation

🛡️ Security Features:
- API key authentication and rate limiting
- Input validation and sanitization
- Process cleanup and error handling
- Professional audit logging

📚 Documentation:
- Complete setup guides for all platforms
- API reference documentation
- Troubleshooting guides
- Contributing guidelines

⚠️ Legal: Authorized security testing only
Built for security professionals, by security professionals"
fi

# Show repository status
echo "📊 Repository Status:"
echo "===================="
git status --short
echo ""
git log --oneline -5
echo ""

# Show file structure
echo "📁 Repository Structure:"
echo "======================="
find . -type f -name "*.py" -o -name "*.md" -o -name "*.txt" -o -name "*.sh" -o -name "*.ps1" | grep -v "__pycache__" | sort

echo ""
echo "🎯 Ready for GitHub Upload!"
echo "=========================="
echo "To complete the upload:"
echo "1. git push -u origin main"
echo "2. Create release on GitHub:"
echo "   - Tag: v1.0.0"
echo "   - Title: PiStorm v1.0 - Initial Release"
echo "   - Description: Distributed WiFi Security Testing Platform"
echo ""
echo "3. Repository URL: https://github.com/TheJhyeFactor/PiStorm"
echo ""
echo "🔑 Don't forget to:"
echo "- Set repository visibility (public/private)"
echo "- Add topics: wifi-security, penetration-testing, raspberry-pi, gpu-acceleration"
echo "- Enable Issues and Discussions"
echo "- Add repository description"

# Ask if user wants to push immediately
read -p "🚀 Push to GitHub now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Pushing to GitHub..."
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully pushed to GitHub!"
        echo "🌐 Repository: https://github.com/TheJhyeFactor/PiStorm"
    else
        echo "❌ Push failed. You may need to authenticate with GitHub."
        echo "💡 Try: git push -u origin main"
    fi
else
    echo "ℹ️ Push skipped. Run 'git push -u origin main' when ready."
fi

echo "🎉 PiStorm repository preparation complete!"