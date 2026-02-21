import os
import platform
import subprocess
import requests
import tarfile
import zipfile
import tkinter as tk
from tkinter import messagebox, ttk
import time
import threading
import shutil
import secrets
import logging
import json
import sys
import argparse

# Suppress __pycache__ creation
sys.dont_write_bytecode = True

def run_full_setup(progress_callback=None):
    """Execute the complete setup and update process."""
    try:
        # 1. Update Hosts
        if not update_hosts_file(progress_callback): return False
        
        # 2. Flush DNS
        flush_dns_cache(progress_callback)
        
        # 3. AdGuard Home
        if not install_adguard_home(progress_callback): return False
        
        # 4. Wait for AGH
        if progress_callback: progress_callback(65, "Verifying AdGuard Home...")
        wait_for_service("http://localhost:3000")
        
        # 5. System DNS
        if not change_dns_settings(progress_callback): return False
        
        # 6. Browser Extension
        if not setup_browser_extension(progress_callback): return False
        
        if progress_callback: progress_callback(100, "Setup complete.")
        return True
    except Exception as e:
        logger.error(f"Full setup error: {e}")
        return False

def schedule_task_windows():
    """Create a Windows Scheduled Task for weekly silent updates."""
    try:
        script_path = os.path.abspath(__file__)
        python_exe = sys.executable
        task_name = "OneForAll_WeeklyUpdate"
        
        # Build the command string carefully for Windows task scheduler
        # We use python.exe with the full path to the script and the --silent flag
        command = f'"{python_exe}" "{script_path}" --silent'
        
        # Run schtasks command
        result = subprocess.run([
            "schtasks", "/create", "/tn", task_name, "/tr", command,
            "/sc", "weekly", "/d", "SUN", "/st", "03:00", "/rl", "highest", "/f"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Weekly scheduled task '{task_name}' created successfully.")
            return True
        else:
            logger.error(f"Failed to create scheduled task: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Failed to create scheduled task: {e}")
        return False

# Import PIL for icon generation
try:
    from PIL import Image, ImageDraw
except ImportError:
    # Will be handled by check_requirements function
    pass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "one_for_all.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OneForAll")

# Default configuration
DEFAULT_CONFIG = {
    "dns_servers": ["127.0.0.1", "1.1.1.1"],  # Primary: AdGuard Home, Secondary: Cloudflare
    "dns_servers_ipv6": ["::1", "2606:4700:4700::1111"], # Primary: AGH, Secondary: Cloudflare
    "encrypted_dns": [
        "https://1.1.1.2/dns-query",       # Cloudflare Malware Blocking (DoH)
        "https://dns.adguard-dns.com/dns-query", # AdGuard Privacy (DoH)
        "tls://1.1.1.2"                     # Cloudflare Malware Blocking (DoT)
    ],
    "hosts_redirect_ip": "127.0.0.1",
    "filter_list_url": "https://easylist.to/easylist/easylist.txt",
    "request_timeout": 10,
    "adguard_home_urls": {
        "Windows": "https://static.adguard.com/adguardhome/release/AdGuardHome_windows_amd64.zip",
        "Darwin": "https://static.adguard.com/adguardhome/release/AdGuardHome_darwin_amd64.tar.gz",
        "Linux": "https://static.adguard.com/adguardhome/release/AdGuardHome_linux_amd64.tar.gz"
    },
    "extension_blocklists": [
        "https://easylist.to/easylist/easylist.txt",
        "https://easylist.to/easylist/easyprivacy.txt",
        "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/filters.txt"
    ]
}

def load_config():
    """Load configuration from config.json or use defaults."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = DEFAULT_CONFIG.copy()
  
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
            logger.info("Loaded configuration from config.json")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            logger.info("Using default configuration")
    else:
        logger.info("No config file found. Using default configuration")
    
    return config

def is_admin():
    """Check if the script is running with elevated privileges."""
    # For Linux/macOS
    try:
        # Use getattr to avoid Pyright error on Windows
        getuid = getattr(os, 'getuid', None)
        if getuid:
            return getuid() == 0
    except Exception as e:
        logger.debug(f"Unix admin check failed: {e}")

    # For Windows
    try:
        import ctypes
        admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not admin:
            logger.warning("Script is not running with administrator privileges")
        return admin
    except Exception as e:
        logger.error(f"Failed to check admin privileges (Windows method): {e}")
        return False

def check_requirements():
    """Check if all required modules are installed."""
    required_modules = {
        "requests": "requests",
        "PIL": "pillow"  # For icon generation
    }
    
    missing_modules = []
    
    for module, package in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(package)
    
    if missing_modules:
        print("Missing required packages. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_modules)
            print("Successfully installed missing packages.")
            return True
        except Exception as e:
            print(f"Failed to install required packages: {e}")
            print("Please install the following packages manually:")
            for package in missing_modules:
                print(f"  - {package}")
            return False
    
    return True

HOSTS_MARKER_START = "# BEGIN ONE-FOR-ALL AD BLOCKING"
HOSTS_MARKER_END = "# END ONE-FOR-ALL AD BLOCKING"

def update_hosts_file(progress_callback=None):
    """Update hosts file to block ads with progress reporting and markers."""
    config = load_config()
    logger.info("Updating hosts file to block ads...")
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if platform.system() == "Windows" else "/etc/hosts"
    redirect_ip = config["hosts_redirect_ip"]

    # Update progress
    if progress_callback:
        progress_callback(5, "Fetching ad-serving domains...")

    # Fetch ad-serving domains
    filter_list_url = config["filter_list_url"]
    try:
        response = requests.get(filter_list_url, timeout=config["request_timeout"])
        response.raise_for_status()
        
        if progress_callback:
            progress_callback(30, "Processing domain list...")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch EasyList: {e}")
        if progress_callback:
            progress_callback(100, f"Error: {e}")
        return False

    ad_domains = set()
    excluded_from_hosts = {'youtube.com', 'google.com', 'googlevideo.com', 'ytimg.com', 'ggpht.com', 'static.doubleclick.net'}
    
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("||"):
            # Extract domain: ||example.com^$options -> example.com
            domain = line[2:].split("^")[0]
            if domain and domain not in excluded_from_hosts:
                # Basic validation to ensure it's a domain-like string
                if "." in domain and not any(c in domain for c in ["/", "*", "@", "%"]):
                    ad_domains.add(domain)
    
    # Read existing hosts content
    try:
        with open(hosts_path, "r") as file:
            lines = file.readlines()
    except Exception as e:
        logger.error(f"Error reading hosts file: {e}")
        return False

    # Remove existing One-For-All block if present
    new_lines = []
    skip = False
    for line in lines:
        if HOSTS_MARKER_START in line:
            skip = True
            continue
        if HOSTS_MARKER_END in line:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    # Add new block
    if progress_callback:
        progress_callback(70, "Writing to hosts file...")

    try:
        # Ensure trailing newline if needed
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
            
        with open(hosts_path, "w") as file:
            file.writelines(new_lines)
            file.write(f"\n{HOSTS_MARKER_START}\n")
            for domain in ad_domains:
                file.write(f"{redirect_ip} {domain}\n")
            file.write(f"{HOSTS_MARKER_END}\n")
        
        logger.info(f"Hosts file updated with {len(ad_domains)} domains.")
        if progress_callback:
            progress_callback(100, "Hosts file updated successfully")
        return True
    except PermissionError:
        logger.error("Permission denied: Unable to modify the hosts file")
        return False

def revert_hosts_file(progress_callback=None):
    """Remove ad-blocking entries from hosts file."""
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if platform.system() == "Windows" else "/etc/hosts"
    if progress_callback:
        progress_callback(50, "Reverting hosts file...")
        
    try:
        with open(hosts_path, "r") as file:
            lines = file.readlines()
            
        new_lines = []
        skip = False
        found = False
        for line in lines:
            if HOSTS_MARKER_START in line:
                skip = True
                found = True
                continue
            if HOSTS_MARKER_END in line:
                skip = False
                continue
            if not skip:
                new_lines.append(line)
        
        if found:
            with open(hosts_path, "w") as file:
                file.writelines(new_lines)
            logger.info("Hosts file reverted successfully.")
        
        if progress_callback:
            progress_callback(100, "Hosts file reverted")
        return True
    except Exception as e:
        logger.error(f"Error reverting hosts file: {e}")
        return False

def flush_dns_cache(progress_callback=None):
    """Flush DNS cache with progress reporting and increased timeout."""
    logger.info("Flushing DNS cache...")
    if progress_callback:
        progress_callback(10, "Flushing DNS cache...")
    
    for attempt in range(2):
        try:
            if platform.system() == "Windows":
                # Increased timeout to 20 seconds for slow systems
                subprocess.run(["ipconfig", "/flushdns"], check=True, timeout=20)
            elif platform.system() == "Darwin":
                subprocess.run(["dscacheutil", "-flushcache"], check=True, timeout=10)
                subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], check=True, timeout=10)
            elif platform.system() == "Linux":
                subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=True, timeout=10)
            
            logger.info("DNS cache flushed successfully.")
            if progress_callback:
                progress_callback(20, "DNS cache flushed")
            return True
        except subprocess.TimeoutExpired:
            logger.warning(f"DNS flush attempt {attempt+1} timed out. Retrying...")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to flush DNS cache: {e}")
            break
            
    return False

def change_dns_settings_macos(progress_callback=None):
    """Change DNS settings on macOS using networksetup."""
    logger.info("Changing DNS settings on macOS...")
    config = load_config()
    dns_servers = config.get("dns_servers", ["94.140.14.14", "94.140.15.15"])
    
    try:
        # Get active network services
        result = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True, check=True)
        services = [s for s in result.stdout.splitlines() if "*" not in s and s]
        
        for service in services:
            # Check if service is active/has an IP
            info = subprocess.run(["networksetup", "-getinfo", service], capture_output=True, text=True)
            if "IP address:" in info.stdout and "none" not in info.stdout.lower():
                if progress_callback: progress_callback(30, f"Configuring {service}...")
                subprocess.run(["networksetup", "-setdnsservers", service] + dns_servers, check=True)
                logger.info(f"DNS set for macOS service: {service}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to set macOS DNS: {e}")
        return False

def change_dns_settings_linux(progress_callback=None):
    """Change DNS settings on Linux using nmcli (NetworkManager)."""
    logger.info("Changing DNS settings on Linux...")
    config = load_config()
    dns_str = " ".join(config.get("dns_servers", ["94.140.14.14", "94.140.15.15"]))
    
    try:
        # Try NetworkManager (nmcli)
        result = subprocess.run(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.splitlines():
                name = line.split(":")[0]
                if progress_callback: progress_callback(30, f"Configuring {name}...")
                subprocess.run(["nmcli", "connection", "modify", name, "ipv4.dns", dns_str, "ipv4.ignore-auto-dns", "yes"], check=True)
                subprocess.run(["nmcli", "connection", "up", name], check=True)
            return True
        
        # Fallback for systems without NetworkManager (e.g., direct resolv.conf - less ideal)
        logger.warning("NetworkManager not found or no active connections. DNS set may be incomplete.")
        return False
    except Exception as e:
        logger.error(f"Failed to set Linux DNS: {e}")
        return False

def change_dns_settings(progress_callback=None):
    """Unified DNS configuration entry point."""
    system = platform.system()
    if system == "Windows":
        return change_dns_settings_windows(progress_callback)
    elif system == "Darwin":
        return change_dns_settings_macos(progress_callback)
    elif system == "Linux":
        return change_dns_settings_linux(progress_callback)
    else:
        logger.error(f"DNS configuration not supported for {system}")
        return False

def revert_dns_settings_macos(progress_callback=None):
    """Restore macOS DNS to Empty/Automatic."""
    try:
        result = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True)
        services = [s for s in result.stdout.splitlines() if "*" not in s and s]
        for service in services:
            subprocess.run(["networksetup", "-setdnsservers", service, "Empty"], check=True)
        return True
    except Exception: return False

def revert_dns_settings_linux(progress_callback=None):
    """Restore Linux DNS to Automatic."""
    try:
        result = subprocess.run(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"], capture_output=True, text=True)
        for name in result.stdout.splitlines():
            subprocess.run(["nmcli", "connection", "modify", name, "ipv4.ignore-auto-dns", "no"], check=True)
            subprocess.run(["nmcli", "connection", "up", name], check=True)
        return True
    except Exception: return False

def revert_dns_settings(progress_callback=None):
    """Unified DNS reversion entry point."""
    system = platform.system()
    if system == "Windows":
        return revert_dns_settings_windows(progress_callback)
    elif system == "Darwin":
        return revert_dns_settings_macos(progress_callback)
    elif system == "Linux":
        return revert_dns_settings_linux(progress_callback)
    return False

def change_dns_settings_windows(progress_callback=None):
    """Change DNS settings on Windows with progress reporting and smarter interface selection."""
    logger.info("Changing DNS settings on Windows...")
    if progress_callback:
        progress_callback(25, "Detecting network interfaces...")
    
    config = load_config()
    dns_servers = config.get("dns_servers", ["1.1.1.1", "1.0.0.1"])
    
    try:
        # Get the list of interfaces
        result = subprocess.run(
            ["netsh", "interface", "show", "interface"],
            capture_output=True,
            text=True,
            timeout=10
        )
        lines = result.stdout.splitlines()
        active_interface = None
        
        # Look for the primary connected interface, skipping virtual ones
        for line in lines:
            if "Connected" in line:
                # Example: Enabled  Connected  Dedicated  Wi-Fi
                parts = line.split()
                if len(parts) >= 4:
                    interface_name = " ".join(parts[3:])
                    # Skip common virtual adapters
                    if any(v in interface_name for v in ["VMnet", "VirtualBox", "vEthernet", "Pseudo", "Loopback"]):
                        logger.info(f"Skipping virtual interface: {interface_name}")
                        continue
                    active_interface = interface_name
                    break

        if not active_interface:
            logger.warning("No suitable active interface found.")
            if progress_callback:
                progress_callback(30, "No active physical interface found")
            return False

        logger.info(f"Targeting interface: {active_interface}")
        if progress_callback:
            progress_callback(30, f"Configuring {active_interface}...")

        # Set primary IPv4 DNS - Using standard syntax: name="Interface Name"
        if progress_callback:
            progress_callback(32, "Setting primary IPv4 DNS...")
        # Note: We don't use check=True here because Windows sometimes warns that the DNS doesn't exist
        # even when it successfully sets it.
        subprocess.run(
            ["netsh", "interface", "ip", "set", "dns", f"name={active_interface}", "source=static", f"address={dns_servers[0]}", "register=primary"],
            timeout=15
        )

        # Add secondary IPv4 DNS
        if progress_callback:
            progress_callback(34, "Setting secondary IPv4 DNS...")
        subprocess.run(
            ["netsh", "interface", "ip", "add", "dns", f"name={active_interface}", f"address={dns_servers[1]}", "index=2"],
            timeout=15
        )

        # Set IPv6 DNS
        dns_ipv6 = config.get("dns_servers_ipv6", ["2606:4700:4700::1111", "2606:4700:4700::1001"])
        if progress_callback:
            progress_callback(36, "Setting IPv6 DNS...")
        try:
            subprocess.run(
                ["netsh", "interface", "ipv6", "set", "dns", f"name={active_interface}", "source=static", f"address={dns_ipv6[0]}", "register=primary"],
                timeout=15
            )
            subprocess.run(
                ["netsh", "interface", "ipv6", "add", "dns", f"name={active_interface}", f"address={dns_ipv6[1]}", "index=2"],
                timeout=15
            )
            logger.info("IPv6 DNS settings updated.")
        except Exception as e:
            logger.warning(f"IPv6 configuration skipped or failed: {e}")

        logger.info(f"DNS configuration complete for: {active_interface}")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to configure DNS settings (subprocess error): {e}")
        if progress_callback:
            progress_callback(40, f"Error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to configure DNS settings: {e}")
        if progress_callback:
            progress_callback(40, f"Error: {e}")
        return False

def configure_adguard_home(ag_home_dir):
    """Ensure AdGuard Home is configured with our hybrid upstreams."""
    logger.info("Auto-configuring AdGuard Home DNS settings...")
    config_path = os.path.join(ag_home_dir, "AdGuardHome", "AdGuardHome.yaml")
    
    # Ensure directory exists
    if not os.path.exists(os.path.dirname(config_path)):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    config = load_config()
    upstreams = config.get("encrypted_dns", [
        "https://1.1.1.2/dns-query",
        "https://dns.adguard-dns.com/dns-query",
        "tls://1.1.1.2"
    ])

    # If config doesn't exist, write bootstrap
    if not os.path.exists(config_path):
        lines = ["dns:", "  upstream_dns:"]
        for u in upstreams: lines.append(f"    - {u}")
        lines.extend([
            "  upstream_mode: parallel",
            "  bootstrap_dns:",
            "    - 1.1.1.1",
            "    - 1.0.0.1",
            "  cache_size: 4194304",
            "schema_version: 20"
        ])
        try:
            with open(config_path, "w") as f: f.write("\n".join(lines))
            logger.info("AdGuard Home bootstrap config written.")
        except Exception as e:
            logger.error(f"Failed to write AdGuard Home config: {e}")
    else:
        logger.info("Existing AdGuard Home config found. Upstreams are pre-configured for new installs.")

def install_adguard_home(progress_callback=None):
    """Install AdGuard Home with progress reporting and cleanup."""
    logger.info("Installing AdGuard Home...")
    if progress_callback:
        progress_callback(45, "Preparing AdGuard Home installation...")
    
    config = load_config()
    AG_HOME_URL = config.get("adguard_home_urls", {
        "Windows": "https://static.adguard.com/adguardhome/release/AdGuardHome_windows_amd64.zip",
        "Darwin": "https://static.adguard.com/adguardhome/release/AdGuardHome_darwin_amd64.tar.gz",
        "Linux": "https://static.adguard.com/adguardhome/release/AdGuardHome_linux_amd64.tar.gz"
    })

    system = platform.system()
    if system not in AG_HOME_URL:
        logger.error(f"Unsupported OS for AdGuard Home: {system}")
        if progress_callback:
            progress_callback(50, f"Unsupported OS: {system}")
        return False

    # Define installation directory
    if system == "Windows":
        ag_home_dir = "C:\\AdGuardHome"
    else:
        ag_home_dir = "/opt/AdGuardHome"

    # Check if AdGuard Home is already installed
    executable_path = os.path.join(ag_home_dir, "AdGuardHome", "AdGuardHome.exe" if system == "Windows" else "AdGuardHome")
    if os.path.exists(executable_path):
        logger.info(f"AdGuard Home is already installed at {ag_home_dir}.")
        if progress_callback:
            progress_callback(55, "AdGuard Home already installed")
        
        # Check if the service is running
        try:
            # We don't use check=True here so we can handle the exit codes manually
            result = subprocess.run([executable_path, "--service", "start"], 
                                   capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 or "already running" in result.stderr.lower() or "already running" in result.stdout.lower():
                logger.info("AdGuard Home service is active.")
                if progress_callback:
                    progress_callback(65, "AdGuard Home service is active")
                return True
            else:
                logger.error(f"Failed to start AdGuard Home service: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error checking/starting AdGuard Home service: {e}")
            if progress_callback:
                progress_callback(65, f"Error: {e}")
            return False

    # Create installation directory
    logger.info(f"Creating AdGuard Home directory at {ag_home_dir}...")
    if progress_callback:
        progress_callback(50, "Creating installation directory...")
    os.makedirs(ag_home_dir, exist_ok=True)

    # Download AdGuard Home
    ag_home_file = os.path.join(ag_home_dir, "adguardhome.zip" if system == "Windows" else "adguardhome.tar.gz")
    logger.info(f"Downloading AdGuard Home for {system}...")
    if progress_callback:
        progress_callback(52, "Downloading AdGuard Home...")
    try:
        response = requests.get(AG_HOME_URL[system], timeout=config.get("request_timeout", 10))
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(ag_home_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and progress_callback:
                        # Calculate download progress between 52-58%
                        download_progress = 52 + int((downloaded / total_size) * 6)
                        progress_callback(download_progress, f"Downloading: {downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB")
        
        logger.info("Download completed.")
        if progress_callback:
            progress_callback(58, "Download completed")
    except requests.RequestException as e:
        logger.error(f"Failed to download AdGuard Home: {e}")
        if progress_callback:
            progress_callback(58, f"Download error: {e}")
        return False

    # Extract the archive
    logger.info("Extracting AdGuard Home...")
    if progress_callback:
        progress_callback(60, "Extracting files...")
    try:
        if system == "Windows":
            with zipfile.ZipFile(ag_home_file, "r") as zip_ref:
                zip_ref.extractall(ag_home_dir)
        else:
            with tarfile.open(ag_home_file, "r:gz") as tar_ref:
                tar_ref.extractall(ag_home_dir)
        logger.info("Extraction completed.")
        if progress_callback:
            progress_callback(62, "Extraction completed")
            
        # Pre-configure with upstream DNS before starting
        configure_adguard_home(ag_home_dir)
    except Exception as e:
        logger.error(f"Failed to extract AdGuard Home: {e}")
        if progress_callback:
            progress_callback(62, f"Extraction error: {e}")
        return False

    # Install AdGuard Home as a service
    logger.info("Installing AdGuard Home as a service...")
    if progress_callback:
        progress_callback(64, "Installing as a service...")
    try:
        subprocess.run([executable_path, "--service", "install"], check=True, timeout=10)
    except Exception as e:
        logger.error(f"Failed to install AdGuard Home as a service: {e}")
        if progress_callback:
            progress_callback(64, f"Service installation error: {e}")
        return False

    # Check if the service is already running before starting it
    logger.info("Checking if AdGuard Home service is already running...")
    if progress_callback:
        progress_callback(66, "Checking service status...")
    try:
        result = subprocess.run([executable_path, "--service", "status"], capture_output=True, text=True, timeout=10)
        if "running" in result.stdout.lower():
            logger.info("AdGuard Home service is already running. Skipping start command.")
            if progress_callback:
                progress_callback(68, "Service already running")
        else:
            logger.info("Starting AdGuard Home service...")
            if progress_callback:
                progress_callback(68, "Starting service...")
            subprocess.run([executable_path, "--service", "start"], check=True, timeout=10)
            logger.info("AdGuard Home service started.")
            if progress_callback:
                progress_callback(69, "Service started")
    except Exception as e:
        logger.error(f"Failed to start AdGuard Home service: {e}")
        if progress_callback:
            progress_callback(69, f"Service start error: {e}")
        return False

    # Clean up downloaded archive
    try:
        logger.info(f"Cleaning up temporary files: {ag_home_file}")
        if progress_callback:
            progress_callback(69, "Cleaning up temporary files...")
        os.remove(ag_home_file)
        logger.info("Temporary files removed.")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary files: {e}")
        # Don't return False here, as this is not a critical error

    logger.info("AdGuard Home installed and running. Access it at http://localhost:3000.")
    if progress_callback:
        progress_callback(70, "AdGuard Home installed successfully")
    return True

def setup_browser_extension(progress_callback=None):
    """Ensure the browser extension is ready for loading, generating it if missing."""
    logger.info("Setting up 'One for All' browser extension...")
    if progress_callback:
        progress_callback(75, "Setting up browser extension...")

    extension_dir = os.path.join(os.getcwd(), "one-for-all-extension")
    os.makedirs(extension_dir, exist_ok=True)
    os.makedirs(os.path.join(extension_dir, "utils"), exist_ok=True)

    # Helper to write files
    def write_ext_file(name, content):
        path = os.path.join(extension_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        # Force the OS to see a change by updating the timestamp
        os.utime(path, None)
        logger.info(f"Extension file ensured: {name}")

    # 1. Manifest
    write_ext_file("manifest.json", """
{
  "manifest_version": 3,
  "name": "One for All",
  "version": "1.2",
  "description": "Professional-grade ad blocker and privacy suite.",
  "permissions": ["declarativeNetRequest", "tabs", "activeTab", "storage", "alarms", "scripting", "privacy"],
  "host_permissions": ["*://*/*"],
  "background": { "service_worker": "background.js" },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["privacy-shield.js"],
      "run_at": "document_start",
      "world": "MAIN"
    },
    {
      "matches": ["<all_urls>"],
      "js": ["utils/dom-utils.js", "content.js", "cookie-consent.js"],
      "run_at": "document_start"
    }
  ],
  "icons": { "16": "icon.png", "32": "icon.png", "48": "icon.png", "128": "icon.png" },
  "action": { 
    "default_popup": "popup.html",
    "default_icon": { "16": "icon.png", "32": "icon.png", "48": "icon.png", "128": "icon.png" }
  },
  "options_page": "settings.html"
}
""")

    # 2. Privacy Shield (Shimming & Fingerprinting)
    write_ext_file("privacy-shield.js", """
(function() {
  'use strict';
  // Shims for tracking scripts
  window.ga = window.ga || function() { (window.ga.q = window.ga.q || []).push(arguments); };
  window.gtag = window.gtag || function() { (window.dataLayer = window.dataLayer || []).push(arguments); };
  window.fbq = window.fbq || function() { (window.fbq.q = window.fbq.q || []).push(arguments); };
  
  // Fingerprint Jittering
  const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function() {
    const ctx = this.getContext('2d');
    if (ctx) {
      const imgData = ctx.getImageData(0, 0, this.width, this.height);
      imgData.data[3] = imgData.data[3] + (Math.random() > 0.5 ? 1 : -1);
      ctx.putImageData(imgData, 0, 0);
    }
    return originalToDataURL.apply(this, arguments);
  };
  Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
})();
""")

    # 3. Background (Rules, WebRTC, & Status Check)
    write_ext_file("background.js", """
const adBlockingRules = [
  { id: 1, priority: 1, action: { type: 'block' }, condition: { urlFilter: '*ads*', excludedDomains: ['youtube.com', 'google.com', 'googlevideo.com'], resourceTypes: ['script', 'image', 'xmlhttprequest', 'sub_frame'] } },
  { id: 6, priority: 2, action: { type: 'modifyHeaders', requestHeaders: [{ header: 'referer', operation: 'remove' }, { header: 'x-client-data', operation: 'remove' }] }, condition: { urlFilter: '*', domainType: 'thirdParty', excludedDomains: ['youtube.com', 'google.com', 'googlevideo.com', 'ytimg.com', 'ggpht.com'] } },
  { id: 7, priority: 2, action: { type: 'modifyHeaders', requestHeaders: [{ header: 'user-agent', operation: 'set', value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' }] }, condition: { urlFilter: '*' } }
];

async function init() {
  const existing = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: existing.map(r => r.id), addRules: adBlockingRules });
}
chrome.runtime.onInstalled.addListener(init);
init();

// Handle status checks from settings page (Bypasses CORS)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'checkStatus') {
    const ports = ['3000', '80'];
    const checkPort = (index) => {
      if (index >= ports.length) {
        sendResponse({ status: 'offline' });
        return;
      }
      fetch(`http://localhost:${ports[index]}/`, { mode: 'no-cors', cache: 'no-store' })
        .then(() => sendResponse({ status: 'online' }))
        .catch(() => checkPort(index + 1));
    };
    checkPort(0);
    return true; 
  }
});

function setWebRTC(isEnabled) {
  if (chrome.privacy && chrome.privacy.network) {
    chrome.privacy.network.webRTCIPHandlingPolicy.set({ value: isEnabled ? 'disable_non_proxied_udp' : 'default' });
  }
}
chrome.storage.sync.get("isEnabled", (r) => setWebRTC(r.isEnabled !== false));
""")

    # 4. DOM Utils
    write_ext_file("utils/dom-utils.js", """
export function hideElements(selectors) {
  selectors.forEach(s => {
    document.querySelectorAll(s).forEach(el => { el.style.display = 'none'; });
  });
}
""")

    # 5. Content Scripts
    write_ext_file("content.js", "console.log('One for All: Content Active');")
    write_ext_file("cookie-consent.js", "console.log('One for All: Cookie Shield Active');")

    # 6. UI (Popup & Settings)
    write_ext_file("popup.html", """
<html>
<head><title>One for All</title></head>
<body style='width:200px;padding:10px;font-family:sans-serif;'>
  <h3>One for All</h3>
  <p>Privacy Active</p>
  <hr>
  <a href='#' id='openSettings'>Settings</a>
  <script src="popup.js"></script>
</body>
</html>
""".strip())
    
    write_ext_file("popup.js", """
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('openSettings');
  if (btn) {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      chrome.runtime.openOptionsPage();
    });
  }
});
""".strip())
    
    write_ext_file("settings.html", """
<!DOCTYPE html>
<html>
<head><title>One for All Settings</title><style>body{font-family:sans-serif;padding:20px;}h1{color:#007bff;}</style></head>
<body>
  <h1>One for All Settings</h1>
  <p>Your privacy suite is active and managed by the system-wide controller.</p>
  <div id="stats">Checking AdGuard Home connection...</div>
  <script src="settings.js"></script>
</body>
</html>
""".strip())

    write_ext_file("settings.js", """
document.addEventListener('DOMContentLoaded', () => {
  const stats = document.getElementById('stats');
  chrome.runtime.sendMessage({ action: 'checkStatus' }, (response) => {
    if (response && response.status === 'online') {
      stats.textContent = 'AdGuard Home is Connected and Filtering.';
      stats.style.color = 'green';
    } else {
      stats.textContent = 'AdGuard Home is not responding. Check the Control Panel.';
      stats.style.color = 'red';
    }
  });
});
""")

    # 7. Icon
    icon_path = os.path.join(extension_dir, "icon.png")
    if not os.path.exists(icon_path):
        generate_default_icon(icon_path)

    if progress_callback:
        progress_callback(100, "Extension generated successfully")
    return True

    try:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        logger.info(f"Extension files copied successfully to {target_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy extension files: {e}")
        return False
    # Use your custom icon
    custom_icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")  # Path to your custom icon
    icon_path = os.path.join(extension_dir, "icon.png")

    if not os.path.exists(icon_path):
        if os.path.exists(custom_icon_path):
            try:
                # Copy the custom icon to the extension directory
                shutil.copy(custom_icon_path, icon_path)
                logger.info("Custom icon copied successfully.")
            except Exception as e:
                logger.error(f"Failed to copy custom icon: {e}")
                generate_default_icon(icon_path)
        else:
            logger.info("Custom icon not found, generating default icon.")
            generate_default_icon(icon_path)
    else:
        logger.info("Icon already exists, skipping copy.")

    logger.info(f"'One for All' browser extension created at {extension_dir}.")
    logger.info("Manually load the unpacked extension in your browser.")
    
    if progress_callback:
        progress_callback(95, "Browser extension created successfully")
    return True

def revert_dns_settings_windows(progress_callback=None):
    """Restore DNS settings to automatic (DHCP) on Windows."""
    logger.info("Reverting DNS settings on Windows...")
    if progress_callback:
        progress_callback(50, "Detecting network interfaces...")
    
    try:
        result = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True, timeout=10)
        active_interface = None
        for line in result.stdout.splitlines():
            if "Connected" in line:
                active_interface = line.split()[-1]
                break

        if active_interface:
            if progress_callback: progress_callback(70, f"Resetting {active_interface}...")
            # Revert IPv4 to DHCP
            subprocess.run(["netsh", "interface", "ip", "set", "dns", f"name={active_interface}", "source=dhcp"], check=True, timeout=10)
            
            # Revert IPv6 to DHCP
            try:
                subprocess.run(["netsh", "interface", "ipv6", "set", "dns", f"name={active_interface}", "source=dhcp"], check=True, timeout=10)
                logger.info("IPv6 DNS settings reverted.")
            except subprocess.CalledProcessError:
                logger.warning("Failed to reset IPv6 DNS.")
            
            logger.info(f"DNS settings reset for interface: {active_interface}")
        
        if progress_callback: progress_callback(100, "DNS settings reverted")
        return True
    except Exception as e:
        logger.error(f"Failed to revert DNS settings: {e}")
        return False

def is_port_in_use(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def wait_for_service(ports=[3000, 80], timeout=30):
    """Wait for AdGuard Home to respond on either port 3000 or 80."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        for port in ports:
            try:
                response = requests.get(f"http://localhost:{port}", timeout=2)
                if response.status_code == 200 or response.status_code == 401: # 401 means it needs login, but it's alive!
                    return True
            except requests.RequestException:
                pass
        time.sleep(2)
    return False

def gui_wizard():
    def update_progress(value, message=""):
        progress_var.set(value)
        if message:
            status_var.set(message)
        root.update()

    def run_revert():
        if not is_admin():
            messagebox.showerror("Error", "Admin privileges required.")
            return
            
        if not messagebox.askyesno("Confirm", "This will restore your hosts file and DNS settings. Continue?"):
            return

        revert_button.config(state=tk.DISABLED)
        start_button.config(state=tk.DISABLED)
        
        try:
            revert_hosts_file(update_progress)
            revert_dns_settings(update_progress)
            flush_dns_cache(update_progress)
            messagebox.showinfo("Success", "System settings reverted successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            revert_button.config(state=tk.NORMAL)
            start_button.config(state=tk.NORMAL)
            update_progress(0, "Ready")

    def on_submit():
        if not is_admin():
            messagebox.showerror("Error", "Please run as Administrator.")
            return

        # Pre-flight port checks (Windows only for now)
        if platform.system() == "Windows" and is_port_in_use(53):
            if not messagebox.askyesno("Warning", "Port 53 (DNS) is already in use. AdGuard Home might fail. Continue?"):
                return
        
        start_button.config(state=tk.DISABLED)
        revert_button.config(state=tk.DISABLED)
        
        try:
            if run_full_setup(update_progress):
                messagebox.showinfo("Success", "One for All setup completed! This window will close in 3 seconds.")
                root.after(3000, root.destroy)
        except Exception as e:
            logger.error(f"Setup error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            start_button.config(state=tk.NORMAL)
            revert_button.config(state=tk.NORMAL)

    def on_schedule():
        if not is_admin():
            messagebox.showerror("Error", "Please run as Administrator to schedule tasks.")
            return
            
        if schedule_task_windows():
            messagebox.showinfo("Success", "Weekly background updates scheduled for Sundays at 3:00 AM.")
        else:
            messagebox.showerror("Error", "Failed to schedule task. See logs for details.")

    root = tk.Tk()
    root.title("'One for All' Control Panel")
    root.geometry("550x550")
    root.configure(bg="#f0f0f0")

    header_frame = tk.Frame(root, bg="#007bff", padx=10, pady=10)
    header_frame.pack(fill="x")
    tk.Label(header_frame, text="One for All Control Panel", font=("Arial", 16, "bold"), fg="white", bg="#007bff").pack()
    
    content_frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=20)
    content_frame.pack(fill="both", expand=True)
    
    tk.Label(content_frame, text="Manage your system-wide ad blocking solution.", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w", pady=(0, 10))
    
    progress_frame = tk.Frame(content_frame, bg="#f0f0f0")
    progress_frame.pack(fill="x", pady=20)
    
    progress_var = tk.IntVar(value=0)
    status_var = tk.StringVar(value="Ready")
    
    tk.Label(progress_frame, text="Status:", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(anchor="w")
    status_label = tk.Label(progress_frame, textvariable=status_var, font=("Arial", 10), bg="#f0f0f0", fg="#007bff")
    status_label.pack(anchor="w", pady=(0, 5))
    
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, length=500, mode="determinate")
    progress_bar.pack(fill="x")
    
    button_frame = tk.Frame(content_frame, bg="#f0f0f0", pady=20)
    button_frame.pack(fill="x")
    
    start_button = tk.Button(button_frame, text="Install / Update", command=on_submit, 
                            font=("Arial", 11, "bold"), bg="#28a745", fg="white",
                            padx=15, pady=8, relief=tk.FLAT, width=15)
    start_button.pack(side="left", padx=5)

    revert_button = tk.Button(button_frame, text="Revert Changes", command=run_revert, 
                             font=("Arial", 11, "bold"), bg="#dc3545", fg="white",
                             padx=15, pady=8, relief=tk.FLAT, width=15)
    revert_button.pack(side="right", padx=5)

    schedule_button = tk.Button(content_frame, text="Schedule Weekly Updates", command=on_schedule,
                                font=("Arial", 11), bg="#6c757d", fg="white",
                                padx=20, pady=10, relief=tk.FLAT)
    schedule_button.pack(pady=20)

    root.mainloop()

def generate_default_icon(icon_path, size=128):
    """Generate a default high-res icon if the custom icon is missing."""
    try:
        from PIL import Image, ImageDraw
        # Create a new image with a blue background
        img = Image.new('RGB', (size, size), color=(0, 123, 255))
        draw = ImageDraw.Draw(img)
        
        # Scale the shield shape proportionally
        scale = size / 48
        points = [(24*scale, 5*scale), (5*scale, 15*scale), (5*scale, 30*scale), 
                  (24*scale, 43*scale), (43*scale, 30*scale), (43*scale, 15*scale)]
        draw.polygon(points, fill=(255, 255, 255))
        
        inner_scale = size / 48
        inner_points = [(24*inner_scale, 10*inner_scale), (10*inner_scale, 18*inner_scale), 
                        (10*inner_scale, 28*inner_scale), (24*inner_scale, 38*inner_scale), 
                        (38*inner_scale, 28*inner_scale), (38*inner_scale, 18*inner_scale)]
        draw.polygon(inner_points, fill=(0, 123, 255))
        
        img.save(icon_path)
        logger.info(f"Generated {size}x{size} default icon at {icon_path}")
        return True
    except Exception as e:
        logger.error(f"Error generating default icon: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="'One for All' Ad Blocking Suite")
    parser.add_argument('--silent', action='store_true', help='Run update in silent mode without GUI')
    args = parser.parse_args()

    if check_requirements():
        if args.silent:
            if is_admin():
                logger.info("Running silent update...")
                run_full_setup()
            else:
                print("Error: Admin privileges required for silent update.")
                sys.exit(1)
        else:
            gui_wizard()
    else:
        print("Failed to meet requirements. Exiting.")
        sys.exit(1)
