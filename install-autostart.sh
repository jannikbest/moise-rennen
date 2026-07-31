#!/bin/bash

# Installations-Script für Moise Autostart Service

echo "Installing Moise Autostart Service..."

# Service-Datei kopieren
sudo cp moise-autostart.service /etc/systemd/system/

# Service aktivieren
sudo systemctl daemon-reload
sudo systemctl enable moise-autostart.service

echo "Service installed and enabled."
echo "To start manually: sudo systemctl start moise-autostart.service"
echo "To check status: sudo systemctl status moise-autostart.service"
echo "To view logs: sudo journalctl -u moise-autostart.service -f"
