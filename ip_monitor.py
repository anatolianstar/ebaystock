#!/usr/bin/env python3
"""
IP Monitor Service
Automatically monitors IP address changes and sends notifications
"""

import requests
import sqlite3
import time
import json
import logging
from datetime import datetime
import threading
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import os
from typing import Optional, Dict, Any

class IPMonitor:
    def __init__(self, config_file='ip_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.current_ip = None
        self.database_path = 'ip_history.db'
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
        
        # Initialize database
        self.init_database()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        default_config = {
            "check_interval": 300,  # 5 minutes
            "ip_services": [
                "https://api.ipify.org?format=json",
                "https://httpbin.org/ip",
                "https://api.myip.com"
            ],
            "notification": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "to_email": ""
                },
                "webhook": {
                    "enabled": True,
                    "url": "http://localhost:5000/api/ip-update",
                    "headers": {"Content-Type": "application/json"}
                },
                "file": {
                    "enabled": True,
                    "path": "current_ip.txt"
                }
            }
        }
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except FileNotFoundError:
            self.logger.info(f"Config file not found. Creating default: {self.config_file}")
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
                isp TEXT,
                change_reason TEXT
            )
        """)
        conn.commit()
        conn.close()
        
    def get_current_ip(self) -> Optional[str]:
        """Get current public IP address from multiple services"""
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
                else:
                    # Try to parse as JSON
                    try:
                        data = response.json()
                        if 'ip' in data:
                            return data['ip']
                    except:
                        # If not JSON, try as plain text
                        return response.text.strip()
                        
            except requests.RequestException as e:
                self.logger.warning(f"Failed to get IP from {service_url}: {e}")
                continue
                
        self.logger.error("Failed to get IP from all services")
        return None
    
    def get_ip_details(self, ip_address: str) -> Dict[str, str]:
        """Get location and ISP details for IP address"""
        try:
            # Using ipapi.co for IP geolocation (free tier)
            response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'location': f"{data.get('city', '')}, {data.get('region', '')}, {data.get('country_name', '')}",
                    'isp': data.get('org', 'Unknown')
                }
        except Exception as e:
            self.logger.warning(f"Failed to get IP details: {e}")
            
        return {'location': 'Unknown', 'isp': 'Unknown'}
    
    def save_ip_change(self, new_ip: str, old_ip: str = None):
        """Save IP change to database"""
        ip_details = self.get_ip_details(new_ip)
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        change_reason = "Initial" if old_ip is None else f"Changed from {old_ip}"
        
        cursor.execute("""
            INSERT INTO ip_history (ip_address, location, isp, change_reason)
            VALUES (?, ?, ?, ?)
        """, (new_ip, ip_details['location'], ip_details['isp'], change_reason))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"IP change saved: {new_ip} ({ip_details['location']})")
    
    def send_email_notification(self, new_ip: str, old_ip: str = None):
        """Send email notification about IP change"""
        email_config = self.config['notification']['email']
        if not email_config['enabled']:
            return
            
        try:
            msg = MimeMultipart()
            msg['From'] = email_config['username']
            msg['To'] = email_config['to_email']
            msg['Subject'] = "IP Address Changed - EbayStock System"
            
            body = f"""
            Your EbayStock system IP address has changed:
            
            New IP: {new_ip}
            Old IP: {old_ip or 'N/A'}
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Please update your connection settings accordingly.
            
            - EbayStock IP Monitor
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            text = msg.as_string()
            server.sendmail(email_config['username'], email_config['to_email'], text)
            server.quit()
            
            self.logger.info(f"Email notification sent to {email_config['to_email']}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def send_webhook_notification(self, new_ip: str, old_ip: str = None):
        """Send webhook notification about IP change"""
        webhook_config = self.config['notification']['webhook']
        if not webhook_config['enabled']:
            return
            
        try:
            payload = {
                'event': 'ip_changed',
                'new_ip': new_ip,
                'old_ip': old_ip,
                'timestamp': datetime.now().isoformat(),
                'system': 'ebaystock'
            }
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=webhook_config['headers'],
                timeout=10
            )
            response.raise_for_status()
            
            self.logger.info(f"Webhook notification sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
    
    def save_to_file(self, new_ip: str):
        """Save current IP to file"""
        file_config = self.config['notification']['file']
        if not file_config['enabled']:
            return
            
        try:
            with open(file_config['path'], 'w') as f:
                f.write(f"{new_ip}\n{datetime.now().isoformat()}")
            self.logger.info(f"IP saved to file: {file_config['path']}")
        except Exception as e:
            self.logger.error(f"Failed to save IP to file: {e}")
    
    def notify_ip_change(self, new_ip: str, old_ip: str = None):
        """Send all configured notifications about IP change"""
        self.logger.info(f"IP changed: {old_ip} -> {new_ip}")
        
        # Save to database
        self.save_ip_change(new_ip, old_ip)
        
        # Send notifications
        self.send_email_notification(new_ip, old_ip)
        self.send_webhook_notification(new_ip, old_ip)
        self.save_to_file(new_ip)
    
    def check_ip_change(self):
        """Check for IP address changes"""
        new_ip = self.get_current_ip()
        
        if new_ip is None:
            self.logger.error("Could not retrieve current IP address")
            return
            
        if self.current_ip is None:
            # First run
            self.current_ip = new_ip
            self.notify_ip_change(new_ip)
        elif new_ip != self.current_ip:
            # IP changed
            old_ip = self.current_ip
            self.current_ip = new_ip
            self.notify_ip_change(new_ip, old_ip)
        else:
            self.logger.debug(f"IP unchanged: {self.current_ip}")
    
    def run_monitor(self):
        """Main monitoring loop"""
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
                time.sleep(60)  # Wait 1 minute before retrying
    
    def start_background_monitor(self):
        """Start monitoring in background thread"""
        if self.running:
            self.logger.warning("Monitor is already running")
            return
            
        self.monitor_thread = threading.Thread(target=self.run_monitor, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Background IP monitor started")
    
    def stop_monitor(self):
        """Stop the monitoring service"""
        self.running = False
        self.logger.info("Monitor stop requested")
    
    def get_ip_history(self, limit: int = 10) -> list:
        """Get IP address history from database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ip_address, timestamp, location, isp, change_reason
            FROM ip_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'ip': row[0],
                'timestamp': row[1],
                'location': row[2],
                'isp': row[3],
                'reason': row[4]
            }
            for row in results
        ]

def main():
    """Main function for standalone execution"""
    monitor = IPMonitor()
    
    try:
        monitor.run_monitor()
    except KeyboardInterrupt:
        print("\nMonitor stopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 