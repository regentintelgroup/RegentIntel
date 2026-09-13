#!/bin/bash
# ============================================================
# Regent Intelligence Group -- Server Setup Script
# Run this on your VPS (DigitalOcean, etc.) after first login
# ============================================================

echo "=== Regent Intel Pipeline Setup ==="

# 1. System updates
echo "[1/7] Updating system..."
sudo apt update && sudo apt upgrade -y

# 2. Install Python and Git
echo "[2/7] Installing Python and Git..."
sudo apt install -y python3 python3-pip git

# 3. Install Anthropic SDK
echo "[3/7] Installing Anthropic SDK..."
pip3 install anthropic --break-system-packages

# 4. Clone the repo
echo "[4/7] Cloning RegentIntel repo..."
cd ~
git clone https://github.com/regentintelgroup/RegentIntel.git
cd RegentIntel
mkdir -p reports

# 5. Configure Git identity (for automated commits)
echo "[5/7] Configuring Git..."
git config user.email "regentintelgroup@gmail.com"
git config user.name "Regent Intelligence Group"

# 6. Prompt for API key
echo ""
echo "[6/7] Enter your Anthropic API key (it will not display as you type):"
read -s API_KEY
echo ""

# Write environment file
cat > ~/.regent-env << EOF
export ANTHROPIC_API_KEY='${API_KEY}'
export REPO_DIR='/root/RegentIntel'
EOF

# Add to bash profile
echo 'source ~/.regent-env' >> ~/.bashrc
source ~/.regent-env

# 7. Set up cron schedule (0600 UTC daily)
echo "[7/7] Setting up daily cron schedule..."
CRON_CMD="0 6 * * * source /root/.regent-env && cd /root/RegentIntel && python3 generate_reports.py >> /root/regent-pipeline.log 2>&1"
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo ""
echo "=== SETUP COMPLETE ==="
echo ""
echo "Your pipeline will run daily at 0600 UTC (0200 EST)."
echo "Reports will auto-publish to regentintel.org/advisory."
echo ""
echo "To test now: python3 generate_reports.py --dry-run"
echo "To check logs: tail -f /root/regent-pipeline.log"
echo ""
