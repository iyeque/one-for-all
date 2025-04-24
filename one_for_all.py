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
    "dns_servers": ["94.140.14.14", "94.140.15.15"],  # AdGuard DNS servers
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
    if hasattr(os, 'getuid'):
        try:
            return os.getuid() == 0
        except Exception as e:
            logger.error(f"Failed to check admin privileges (Unix method): {e}")
            return False
    
    # For Windows
    else:
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin:
                logger.warning("Script is not running with administrator privileges")
            return is_admin
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

def update_hosts_file(progress_callback=None):
    """Update hosts file to block ads with progress reporting."""
    config = load_config()
    logger.info("Updating hosts file to block ads...")
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if platform.system() == "Windows" else "/etc/hosts"
    redirect_ip = config["hosts_redirect_ip"]

    # Update progress
    if progress_callback:
        progress_callback(10, "Fetching ad-serving domains...")

    # Fetch ad-serving domains from EasyList
    filter_list_url = config["filter_list_url"]
    logger.info(f"Fetching ad-serving domains from {filter_list_url}...")
    try:
        response = requests.get(filter_list_url, timeout=config["request_timeout"])
        response.raise_for_status()
        logger.info(f"Fetched {len(response.text.splitlines())} lines from EasyList.")
        
        # Update progress
        if progress_callback:
            progress_callback(30, "Processing domain list...")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch EasyList: {e}")
        if progress_callback:
            progress_callback(100, f"Error: {e}")
        return False

    ad_domains = set()
    for line in response.text.splitlines():
        if line.startswith("||") and not line.endswith("^"):
            domain = line[2:].split("^")[0]
            if domain:  # Ensure domain is not empty
                ad_domains.add(domain)
    
    logger.info(f"Extracted {len(ad_domains)} ad domains from filter list")
    
    # Update progress
    if progress_callback:
        progress_callback(50, "Backing up hosts file...")

    # Backup the original hosts file
    original_content = ""
    if os.path.exists(hosts_path):
        try:
            with open(hosts_path, "r") as file:
                original_content = file.read()

            backup_path = hosts_path + ".bak"
            with open(backup_path, "w") as file:
                file.write(original_content)
            logger.info(f"Backed up hosts file to {backup_path}.")
        except PermissionError:
            logger.error("Permission denied: Unable to read or backup hosts file")
            if progress_callback:
                progress_callback(100, "Error: Permission denied for hosts file")
            return False
        except Exception as e:
            logger.error(f"Error backing up hosts file: {e}")
            if progress_callback:
                progress_callback(100, f"Error: {e}")
            return False
    
    # Update progress
    if progress_callback:
        progress_callback(70, "Updating hosts file...")

    # Append ad-blocking entries
    try:
        with open(hosts_path, "a") as file:
            added_count = 0
            for domain in ad_domains:
                if domain not in original_content:
                    file.write(f"{redirect_ip} {domain}\n")
                    added_count += 1
        
        logger.info(f"Hosts file updated successfully. Added {added_count} domains.")
        
        # Update progress
        if progress_callback:
            progress_callback(100, "Hosts file updated successfully")
        return True
    except PermissionError:
        logger.error("Permission denied: Unable to modify the hosts file")
        if progress_callback:
            progress_callback(100, "Error: Permission denied for hosts file")
        return False
    except Exception as e:
        logger.error(f"Error updating hosts file: {e}")
        if progress_callback:
            progress_callback(100, f"Error: {e}")
        return False

def flush_dns_cache(progress_callback=None):
    """Flush DNS cache with progress reporting."""
    logger.info("Flushing DNS cache...")
    if progress_callback:
        progress_callback(10, "Flushing DNS cache...")
    
    try:
        if platform.system() == "Windows":
            subprocess.run(["ipconfig", "/flushdns"], check=True, timeout=10)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["dscacheutil", "-flushcache"], check=True, timeout=10)
            subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], check=True, timeout=10)
        elif platform.system() == "Linux":
            subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=True, timeout=10)
        else:
            logger.warning("Unsupported OS for DNS cache flushing.")
            if progress_callback:
                progress_callback(15, "Unsupported OS for DNS cache flushing")
            return False
        
        logger.info("DNS cache flushed successfully.")
        if progress_callback:
            progress_callback(20, "DNS cache flushed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to flush DNS cache: {e}")
        if progress_callback:
            progress_callback(20, f"Error: {e}")
        return False

def change_dns_settings_windows(progress_callback=None):
    """Change DNS settings on Windows with progress reporting."""
    logger.info("Changing DNS settings on Windows...")
    if progress_callback:
        progress_callback(25, "Detecting network interfaces...")
    
    config = load_config()
    dns_servers = config.get("dns_servers", ["94.140.14.14", "94.140.15.15"])
    
    try:
        # Get the name of the active network interface
        result = subprocess.run(
            ["netsh", "interface", "show", "interface"],
            capture_output=True,
            text=True,
            timeout=10
        )
        lines = result.stdout.splitlines()
        active_interface = None
        for line in lines:
            if "Connected" in line:
                parts = line.split()
                if len(parts) >= 4:
                    active_interface = parts[-1]  # Extract interface name
                    break

        if not active_interface:
            logger.warning("No active interface found.")
            if progress_callback:
                progress_callback(30, "No active interface found")
            return False

        logger.info(f"Found active interface: {active_interface}")
        if progress_callback:
            progress_callback(30, f"Found active interface: {active_interface}")

        # Set primary DNS
        if progress_callback:
            progress_callback(32, "Setting primary DNS server...")
            
        subprocess.run(
            ["netsh", "interface", "ip", "set", "dns", f"name={active_interface}", "source=static", f"addr={dns_servers[0]}", "register=primary"],
            check=True,
            timeout=10
        )

        # Add secondary DNS
        if progress_callback:
            progress_callback(36, "Setting secondary DNS server...")
            
        subprocess.run(
            ["netsh", "interface", "ip", "add", "dns", f"name={active_interface}", f"addr={dns_servers[1]}", "index=2"],
            check=True,
            timeout=10
        )

        logger.info(f"DNS settings updated for interface: {active_interface}")
        if progress_callback:
            progress_callback(40, "DNS settings updated successfully")
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
            result = subprocess.run([executable_path, "--service", "status"], 
                                   capture_output=True, text=True, timeout=10)
            if "running" in result.stdout.lower():
                logger.info("AdGuard Home service is already running.")
                if progress_callback:
                    progress_callback(65, "AdGuard Home service is running")
            else:
                logger.info("Starting AdGuard Home service...")
                if progress_callback:
                    progress_callback(60, "Starting AdGuard Home service...")
                subprocess.run([executable_path, "--service", "start"], check=True, timeout=10)
                logger.info("AdGuard Home service started.")
                if progress_callback:
                    progress_callback(65, "AdGuard Home service started")
        except Exception as e:
            logger.error(f"Error checking/starting AdGuard Home service: {e}")
            if progress_callback:
                progress_callback(65, f"Error: {e}")
            return False
        
        return True

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
    """Set up the 'One for All' browser extension with progress reporting."""
    logger.info("Setting up 'One for All' browser extension...")
    if progress_callback:
        progress_callback(75, "Setting up browser extension...")

    extension_dir = os.path.join(os.getcwd(), "one-for-all-extension")  # Define the extension directory
    os.makedirs(extension_dir, exist_ok=True)

    # Create assets directory if it doesn't exist
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Helper function to write files only if they don't exist
    def write_file_if_not_exists(file_path, content):
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"File created: {file_path}")
            return True
        else:
            logger.info(f"File already exists, skipping: {file_path}")
            return False
    if progress_callback:
        progress_callback(78, "Creating manifest.json...")
    # Manifest.json content with minimum extensions
    manifest_content = """
{
  "manifest_version": 3,
  "name": "One for All",
  "version": "1.0",
  "description": "A comprehensive ad blocker that blocks ads everywhere.",
  "permissions": [
    "tabs",
    "activeTab",
    "storage",
    "declarativeNetRequest",
    "scripting",
    "alarms"
  ],
  "host_permissions": ["*://*/*"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "run_at": "document_start"
    }
  ],
  "icons": {
    "48": "icon.png"
  },
  "action": {
    "default_icon": {
      "48": "icon.png"
    }
  },
  "options_page": "settings.html"
},
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "run_at": "document_start"
    }
  ],
  "icons": {
    "48": "icon.png"
  },
  "action": {
    "default_icon": {
      "48": "icon.png"
    }
  },
  "options_page": "settings.html"
}
"""
    write_file_if_not_exists(os.path.join(extension_dir, "manifest.json"), manifest_content)

    if progress_callback:
        progress_callback(82, "Creating background.js with caching...")

    # Background.js content (updated to handle isEnabled state and alarms and caching
    background_content = """
const defaultBlocklists = [
  "https://easylist.to/easylist/easylist.txt",
  "https://easylist.to/easylist/easyprivacy.txt",
  "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/filters.txt"
];

// Cache control
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

async function fetchBlocklists() {
  try {
    const storedData = await chrome.storage.local.get(["blocklists", "lastFetchTime", "cachedRules"]);
    const blocklists = storedData.blocklists || defaultBlocklists;
    const lastFetchTime = storedData.lastFetchTime || 0;
    const now = Date.now();
    
    // Check if we have cached rules that are still valid
    if (storedData.cachedRules && (now - lastFetchTime) < CACHE_DURATION) {
      console.log("Using cached rules from previous fetch");
      await updateRules(storedData.cachedRules);
      return;
    }
    
    console.log("Cache expired or not found, fetching fresh rules");
    let blockedDomains = [];
    let ruleIdCounter = 1;


    for (const url of blocklists) {
      try {
        console.log(`Fetching blocklist: ${url}`);
        const response = await fetch(url, { cache: "no-store" });
        const rules = await response.text();
        
        // Process rules in chunks to avoid UI freezing
        const lines = rules.split("\\n");
        const chunkSize = 1000;
        
        for (let i = 0; i < lines.length; i += chunkSize) {
          const chunk = lines.slice(i, i + chunkSize);
          
          chunk.forEach((rule) => {
            if (rule.startsWith("||") && !rule.endsWith("^")) {
              const domain = rule.slice(2).split("^")[0];
              if (domain) {
                blockedDomains.push({
                  id: ruleIdCounter++,
                  priority: 1,
                  action: { type: "block" },
                  condition: { 
                    urlFilter: domain, 
                    resourceTypes: ["main_frame", "sub_frame", "script", "image", "stylesheet", "object"] 
                  }
                });
              }
            }
          });
          
          // Small delay to prevent UI freezing
          await new Promise(resolve => setTimeout(resolve, 0));
        }
      } catch (error) {
        console.error(`Failed to fetch blocklist: ${url}`, error);
      }
    }

    // Limit the number of rules to avoid exceeding Chrome's limit
    blockedDomains = blockedDomains.slice(0, 5000);

    // Clear all existing rules before adding new ones
    try {
      const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
      const existingRuleIds = existingRules.map(rule => rule.id);

      await chrome.declarativeNetRequest.updateDynamicRules({
        removeRuleIds: existingRuleIds, // Remove all existing rules
        addRules: blockedDomains // Add new rules
      });

      console.log(`Successfully updated ${blockedDomains.length} rules.`);
    } catch (error) {
      console.error("Error updating dynamic rules:", error);
    }
  } catch (error) {
    console.error("Error updating blocklists:", error);
  }
}

async function updateRules(rules) {
  try {
    // Get existing rules to remove them
    const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
    const existingRuleIds = existingRules.map(rule => rule.id);
    
    // Update rules in batches to avoid hitting limits
    const batchSize = 1000;
    for (let i = 0; i < rules.length; i += batchSize) {
      const batch = rules.slice(i, i + batchSize);
      
      await chrome.declarativeNetRequest.updateDynamicRules({
        removeRuleIds: existingRuleIds.slice(i, i + batchSize),
        addRules: batch
      });
      
      // Small delay to prevent UI freezing
      await new Promise(resolve => setTimeout(resolve, 0));
    }
    
    console.log(`Successfully updated ${rules.length} rules.`);
  } catch (error) {
    console.error("Error updating dynamic rules:", error);
  }
}

// Schedule periodic updates using alarms
chrome.alarms.create("updateBlocklists", { periodInMinutes: 1440 }); // Run once per day

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "updateBlocklists") {
    await fetchBlocklists();
  }
});

// Initial fetch
chrome.runtime.onInstalled.addListener(() => {
  fetchBlocklists();
});

// Handle isEnabled state
chrome.storage.sync.get("isEnabled", ({ isEnabled }) => {
  if (isEnabled === false) {
    disableAdBlocking();
  } else {
    // Default to enabled if not set
    chrome.storage.sync.set({ isEnabled: true });
  }
});

// Listen for changes in isEnabled
chrome.storage.onChanged.addListener((changes) => {
  if (changes.isEnabled) {
    const isEnabled = changes.isEnabled.newValue;
    if (isEnabled) {
      fetchBlocklists();
    } else {
      disableAdBlocking();
    }
  }
});

async function disableAdBlocking() {
  try {
    const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
    const existingRuleIds = existingRules.map(rule => rule.id);
    
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: existingRuleIds
    });
    console.log("Ad blocker disabled. Rules cleared.");
  } catch (error) {
    console.error("Error clearing rules:", error);
  }
}
"""
    write_file_if_not_exists(os.path.join(extension_dir, "background.js"), background_content)

    if progress_callback:
        progress_callback(86, "Creating optimized content.js...")

    # Content.js content with optimized ad hiding
    content_content = """
//Ad selectors to target common ad elements
const adSelectors = [
  "ytd-display-ad-renderer", // YouTube display ads
  "ytd-promoted-video-renderer", // Promoted videos in search results
  ".ytp-ad-module", // YouTube video ads module
  ".video-ads", // Video ads container
  ".ytp-ad-player-overlay", // Ad overlay on videos
  ".ytp-ad-skip-button", // Skip ad button
  ".ytp-ad-text", // Text indicating an ad
  ".ytp-ad-action-interstitial", // Full-screen interstitial ads

  // General ad selectors
  "[class*='ad-']",
  "[class*='Ad']",
  "[class*='advertisement']",
  "[id*='google_ads']",
  "[id*='ad-']",
  "[data-ad]",
  
  // Common ad containers
  ".ad-container",
  ".ad-wrapper",
  ".adsbygoogle",
  ".advertisement",
  
  // Cookie consent banners
  ".cc-banner",
  ".cookie-consent",
  ".cookie-notice",
  ".gdpr-banner",
  ".consent-banner"
];

// Compile a single selector string for better performance
const combinedSelector = adSelectors.join(", ");

// Function to hide ads
function hideAds() {
  const ads = document.querySelectorAll(combinedSelector);
  if (ads.length > 0) {
    ads.forEach(ad => {
      if (ad.style.display !== 'none') {
        ad.style.display = 'none';
      }
    });
  }
}

// Hide ads immediately when script loads
hideAds();

// Set up a more efficient MutationObserver
const observer = new MutationObserver((mutations) => {
  let shouldHideAds = false;
  
  for (const mutation of mutations) {
    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
      shouldHideAds = true;
      break;
    }
  }
  
  if (shouldHideAds) {
    hideAds();
  }
});

// Start observing with a throttled approach
let observing = false;

function startObserver() {
  if (!observing && document.body) {
    observer.observe(document.body, { 
      childList: true, 
      subtree: true,
      attributes: false,
      characterData: false
    });
    observing = true;
  }
}

// Try to start immediately if document is ready
if (document.readyState === 'interactive' || document.readyState === 'complete') {
  startObserver();
  hideAds();
} else {
  // Otherwise wait for DOM to be ready
  document.addEventListener('DOMContentLoaded', () => {
    startObserver();
    hideAds();
  });
}

// Periodically check for ads but with a reasonable interval
let adCheckInterval;

function setupAdCheckInterval() {
  // Clear any existing interval
  if (adCheckInterval) {
    clearInterval(adCheckInterval);
  }
  
  // Set up a new interval with a reasonable delay (5 seconds)
  adCheckInterval = setInterval(hideAds, 5000);
}

// Set up the interval when page is visible
setupAdCheckInterval();

// Optimize performance by pausing when page is not visible
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (adCheckInterval) {
      clearInterval(adCheckInterval);
      adCheckInterval = null;
    }
    
    if (observing) {
      observer.disconnect();
      observing = false;
    }
  } else {
    startObserver();
    setupAdCheckInterval();
    hideAds(); // Check immediately when page becomes visible again
  }
});
"""
    # Write content.js file
    content_js_path = os.path.join(extension_dir, "content.js")
    if not os.path.exists(content_js_path):
        with open(content_js_path, "w", encoding="utf-8") as f:
            f.write(content_content)
        logger.info(f"File created: {content_js_path}")
    else:
        logger.info(f"File already exists, skipping: {content_js_path}")

    if progress_callback:
        progress_callback(90, "Creating streamlined settings.html...")
   
    # Settings.html content with streamlined interface
    settings_html_content = """
<!DOCTYPE html>
<html>
<head>
  <title>One for All Settings</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="settings.css">
</head>
<body>
  <div class="container">
    <h1>One for All Settings</h1>
    
    <!-- Enable/Disable Toggle -->
    <div class="switch-container">
      <span class="switch-label">Enable Ad Blocking:</span>
      <label class="switch">
        <input type="checkbox" id="enableToggle" checked>
        <span class="slider"></span>
      </label>
    </div>
    
    <!-- Blocklist Settings -->
    <div class="form-group">
      <label for="blocklists">Custom Blocklists (comma-separated URLs):</label>
      <input type="text" id="blocklists" placeholder="https://example.com/blocklist.txt, https://another.com/blocklist.txt">
    </div>
    
    <button id="save">Save Settings</button>
    <div id="successMessage" class="alert success">Settings saved successfully!</div>
    
    <!-- Stats Section -->
    <div class="stats-container">
      <h2>Statistics</h2>
      <div class="stat-item">
        <span class="stat-label">Ads Blocked Today:</span>
        <span id="adsBlockedToday" class="stat-value">0</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Total Ads Blocked:</span>
        <span id="totalAdsBlocked" class="stat-value">0</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Last Rules Update:</span>
        <span id="lastUpdate" class="stat-value">Never</span>
      </div>
    </div>
  </div>

  <script src="settings.js"></script>
</body>
</html>
"""
    write_file_if_not_exists(os.path.join(extension_dir, "settings.html"), settings_html_content)

    # Create settings.js file for functionality
    settings_js_content = """
document.addEventListener('DOMContentLoaded', function() {
  const enableToggle = document.getElementById('enableToggle');
  const blocklistsInput = document.getElementById('blocklists');
  const saveButton = document.getElementById('save');
  const successMessage = document.getElementById('successMessage');
  const adsBlockedToday = document.getElementById('adsBlockedToday');
  const totalAdsBlocked = document.getElementById('totalAdsBlocked');
  const lastUpdate = document.getElementById('lastUpdate');

  // Hide success message initially
  successMessage.style.display = 'none';

  // Load saved settings
  chrome.storage.sync.get(['isEnabled', 'blocklists', 'adsBlockedToday', 'totalAdsBlocked', 'lastUpdateTime'], function(data) {
    if (data.isEnabled !== undefined) {
      enableToggle.checked = data.isEnabled;
    }
    
    if (data.blocklists) {
      blocklistsInput.value = data.blocklists.join(', ');
    }
    
    if (data.adsBlockedToday) {
      adsBlockedToday.textContent = data.adsBlockedToday;
    }
    
    if (data.totalAdsBlocked) {
      totalAdsBlocked.textContent = data.totalAdsBlocked;
    }
    
    if (data.lastUpdateTime) {
      lastUpdate.textContent = new Date(data.lastUpdateTime).toLocaleString();
    }
  });

  // Save settings
  saveButton.addEventListener('click', function() {
    const isEnabled = enableToggle.checked;
    let blocklists = [];
    
    if (blocklistsInput.value.trim()) {
      blocklists = blocklistsInput.value.split(',').map(url => url.trim()).filter(url => url);
    }
    
    chrome.storage.sync.set({ isEnabled, blocklists }, function() {
      successMessage.style.display = 'block';
      setTimeout(() => {
        successMessage.style.display = 'none';
      }, 3000);
    });
  });
});
"""
    write_file_if_not_exists(os.path.join(extension_dir, "settings.js"), settings_js_content)

    # Add separate CSS file for better maintainability
    settings_css_content = """
:root {
  --primary-color: #007bff;
  --primary-hover: #0056b3;
  --text-color: #333;
  --bg-color: #f8f9fa;
  --card-bg: #fff;
  --border-color: #dee2e6;
  --success-color: #28a745;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: var(--text-color);
  background-color: var(--bg-color);
  margin: 0;
  padding: 20px;
}

/* ... additional CSS styles ... */
"""
    write_file_if_not_exists(os.path.join(extension_dir, "settings.css"), settings_css_content)
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

def gui_wizard():
    def update_progress(value, message=""):
        progress_var.set(value)
        if message:
            status_var.set(message)
        root.update()

    def run_task(task_func, *args, **kwargs):
        try:
            return task_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {task_func.__name__}: {e}")
            messagebox.showerror("Error", str(e))
            return False

    def on_submit():
        try:
            # Check for elevated privileges
            if not is_admin():
                messagebox.showerror("Error", "Please run this script with elevated privileges (as Administrator).")
                return

            # Disable the start button during setup
            start_button.config(state=tk.DISABLED)
            
            # Update hosts file with progress reporting
            update_progress(0, "Starting setup...")
            if not run_task(update_hosts_file, progress_callback=update_progress):
                start_button.config(state=tk.NORMAL)
                return
            
            # Flush DNS cache
            update_progress(0, "Flushing DNS cache...")
            if not run_task(flush_dns_cache, progress_callback=update_progress):
                start_button.config(state=tk.NORMAL)
                return
            update_progress(20, "DNS cache flushed")
            
            # Change DNS settings
            update_progress(20, "Changing DNS settings...")
            if not run_task(change_dns_settings_windows, progress_callback=update_progress):
                start_button.config(state=tk.NORMAL)
                return
            update_progress(40, "DNS settings updated")
            
            # Install AdGuard Home
            update_progress(40, "Installing AdGuard Home...")
            if not run_task(install_adguard_home, progress_callback=update_progress):
                start_button.config(state=tk.NORMAL)
                return
            update_progress(70, "AdGuard Home installed")
            
            # Set up browser extension
            update_progress(70, "Setting up browser extension...")
            if not run_task(setup_browser_extension, progress_callback=update_progress):
                start_button.config(state=tk.NORMAL)
                return
            update_progress(100, "Setup completed successfully!")

            # Close the wizard automatically after a short delay
            root.after(2000, root.destroy)
            messagebox.showinfo("Success", "'One for All' setup completed successfully!")
        except Exception as e:
            logger.error(f"Setup error: {e}")
            messagebox.showerror("Error", str(e))
            start_button.config(state=tk.NORMAL)

    # Create the main window with improved styling
    root = tk.Tk()
    root.title("'One for All' Setup Wizard")
    root.geometry("550x450")
    root.configure(bg="#f0f0f0")  # Light gray background

    # Add a header frame
    header_frame = tk.Frame(root, bg="#007bff", padx=10, pady=10)
    header_frame.pack(fill="x")
    
    tk.Label(header_frame, text="One for All Setup Wizard", 
             font=("Arial", 16, "bold"), fg="white", bg="#007bff").pack(pady=5)
    
    # Main content frame
    content_frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=20)
    content_frame.pack(fill="both", expand=True)
    
    tk.Label(content_frame, text="This wizard will set up a comprehensive ad-blocking solution:", 
             font=("Arial", 11), bg="#f0f0f0").pack(anchor="w", pady=(0, 10))
    
    # Create a frame for the checklist
    checklist_frame = tk.Frame(content_frame, bg="#f0f0f0")
    checklist_frame.pack(fill="x", pady=5)
    
    features = [
        "✓ Host file ad blocking",
        "✓ DNS-level protection",
        "✓ AdGuard Home installation",
        "✓ Browser extension setup"
    ]
    
    for feature in features:
        tk.Label(checklist_frame, text=feature, font=("Arial", 10), 
                 bg="#f0f0f0", fg="#333333").pack(anchor="w", pady=2)

    # Add progress bar and status with improved styling
    progress_frame = tk.Frame(content_frame, bg="#f0f0f0")
    progress_frame.pack(fill="x", pady=20)
    
    progress_var = tk.IntVar(value=0)
    status_var = tk.StringVar(value="Ready to start")
    
    tk.Label(progress_frame, text="Status:", font=("Arial", 10, "bold"), 
             bg="#f0f0f0").pack(anchor="w")
    status_label = tk.Label(progress_frame, textvariable=status_var, 
                           font=("Arial", 10), bg="#f0f0f0", fg="#007bff")
    status_label.pack(anchor="w", pady=(0, 10))
    
    # Use ttk.Progressbar for better appearance
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, 
                                  length=500, mode="determinate")
    progress_bar.pack(fill="x")
    
    # Button frame
    button_frame = tk.Frame(content_frame, bg="#f0f0f0", pady=20)
    button_frame.pack(fill="x")
    
    start_button = tk.Button(button_frame, text="Start Setup", command=on_submit, 
                            font=("Arial", 12, "bold"), bg="#007bff", fg="white",
                            activebackground="#0056b3", activeforeground="white",
                            padx=20, pady=10, relief=tk.FLAT)
    start_button.pack()

    # Run the GUI
    root.mainloop()


def generate_default_icon(icon_path):
    """Generate a default icon if the custom icon is missing."""
    try:
        # Check if PIL is available before attempting to use it
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            logger.error("PIL library not found. Cannot generate default icon.")
            return False
            
        # Create a new 48x48 image with a blue background
        img = Image.new('RGB', (48, 48), color=(0, 123, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw a shield shape
        draw.polygon([(24, 5), (5, 15), (5, 30), (24, 43), (43, 30), (43, 15)], fill=(255, 255, 255))
        draw.polygon([(24, 10), (10, 18), (10, 28), (24, 38), (38, 28), (38, 18)], fill=(0, 123, 255))
        
        # Save the image
        img.save(icon_path)
        logger.info(f"Generated default icon at {icon_path}")
        return True
    except Exception as e:
        logger.error(f"Error generating default icon: {e}")
        return False


if __name__ == "__main__":
    import sys
    if check_requirements():
        gui_wizard()
    else:
        print("Failed to meet requirements. Exiting.")
        sys.exit(1)
