#!/usr/bin/env python3
"""
IP Monitor Service for EbayStock
Automatically monitors IP address changes and sends notifications
"""

import requests
import sqlite3
import time
import json
import logging
from datetime import datetime
import threading
import os

class IPMonitorService:
    def __init__(self):
        self.current_ip = None
        self.database_path = 'ip_history.db'
        self.config_file = 'ip_config.json'
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ip_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize database
        self.init_database()
        
    def load_config(self):
        """Load configuration settings"""
        default_config = {
            "check_interval": 300,  # 5 minutes
            "ip_services": [
                "https://api.ipify.org?format=json",
                "https://httpbin.org/ip",
                "https://api.myip.com"
            ],
            "webhook_url": "http://localhost:5000/api/ip-update",
            "notification_file": "current_ip.txt"
        }
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
        except FileNotFoundError:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    def init_database(self):
        """Initialize IP history database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ip_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                location TEXT,
                isp TEXT
            )
        """)
        conn.commit()
        conn.close()
        
    def get_current_ip(self):
        """Get current public IP address"""
        for service_url in self.config['ip_services']:
            try:
                response = requests.get(service_url, timeout=10)
                response.raise_for_status()
                
                if 'ipify.org' in service_url:
                    return response.json()['ip']
                elif 'httpbin.org' in service_url:
                    return response.json()['origin'].split(',')[0].strip()
                elif 'myip.com' in service_url:
                    return response.json()['ip']
                    
            except Exception as e:
                self.logger.warning(f"Failed to get IP from {service_url}: {e}")
                continue
                
        return None
    
    def get_ip_details(self, ip_address):
        """Get location details for IP"""
        try:
            response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'location': f"{data.get('city', '')}, {data.get('country_name', '')}",
                    'isp': data.get('org', 'Unknown')
                }
        except Exception as e:
            self.logger.warning(f"Failed to get IP details: {e}")
            
        return {'location': 'Unknown', 'isp': 'Unknown'}
    
    def save_ip_change(self, new_ip, old_ip=None):
        """Save IP change to database"""
        ip_details = self.get_ip_details(new_ip)
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ip_history (ip_address, location, isp)
            VALUES (?, ?, ?)
        """, (new_ip, ip_details['location'], ip_details['isp']))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"IP saved: {new_ip} ({ip_details['location']})")
    
    def notify_ip_change(self, new_ip, old_ip=None):
        """Send notifications about IP change"""
        # Save to database
        self.save_ip_change(new_ip, old_ip)
        
        # Save to file
        try:
            with open(self.config['notification_file'], 'w') as f:
                f.write(f"{new_ip}\n{datetime.now().isoformat()}")
        except Exception as e:
            self.logger.error(f"Failed to save IP to file: {e}")
        
        # Send webhook notification
        try:
            payload = {
                'event': 'ip_changed',
                'new_ip': new_ip,
                'old_ip': old_ip,
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Webhook notification sent successfully")
            else:
                self.logger.warning(f"Webhook failed with status: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Webhook notification failed: {e}")
    
    def check_ip_change(self):
        """Check for IP changes"""
        new_ip = self.get_current_ip()
        
        if new_ip is None:
            self.logger.error("Could not retrieve IP address")
            return
            
        if self.current_ip is None:
            # First run
            self.current_ip = new_ip
            self.notify_ip_change(new_ip)
            self.logger.info(f"Initial IP: {new_ip}")
        elif new_ip != self.current_ip:
            # IP changed
            old_ip = self.current_ip
            self.current_ip = new_ip
            self.notify_ip_change(new_ip, old_ip)
            self.logger.info(f"IP changed: {old_ip} -> {new_ip}")
        else:
            self.logger.debug(f"IP unchanged: {self.current_ip}")
    
    def start_monitoring(self):
        """Start IP monitoring"""
        self.running = True
        self.logger.info("IP Monitor started")
        
        while self.running:
            try:
                self.check_ip_change()
                time.sleep(self.config['check_interval'])
            except KeyboardInterrupt:
                self.logger.info("Monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                time.sleep(60)
    
    def start_background(self):
        """Start monitoring in background"""
        if not self.running:
            self.monitor_thread = threading.Thread(target=self.start_monitoring, daemon=True)
            self.monitor_thread.start()
            self.logger.info("Background monitor started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        self.logger.info("Monitor stopped")
    
    def get_current_status(self):
        """Get current IP status"""
        return {
            'current_ip': self.current_ip,
            'running': self.running,
            'last_check': datetime.now().isoformat()
        }

if __name__ == "__main__":
    monitor = IPMonitorService()
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nMonitor stopped") 