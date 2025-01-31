import os
import platform
import subprocess
import requests
import tarfile
import zipfile
import tkinter as tk
from tkinter import messagebox

def is_admin():
    """Check if the script is running with elevated privileges."""
    try:
        return os.getuid() == 0  # For Linux/macOS
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # For Windows

def update_hosts_file():
    print("Updating hosts file to block ads...")
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if platform.system() == "Windows" else "/etc/hosts"
    redirect_ip = "127.0.0.1"

    # Fetch ad-serving domains from EasyList
    print("Fetching ad-serving domains from EasyList...")
    filter_list_url = "https://easylist.to/easylist/easylist.txt"
    response = requests.get(filter_list_url)
    ad_domains = set()
    for line in response.text.splitlines():
        if line.startswith("||") and not line.endswith("^"):
            domain = line[2:].split("^")[0]
            ad_domains.add(domain)

    # Backup the original hosts file
    if os.path.exists(hosts_path):
        with open(hosts_path, "r") as file:
            original_content = file.read()

        backup_path = hosts_path + ".bak"
        with open(backup_path, "w") as file:
            file.write(original_content)

    # Append ad-blocking entries
    with open(hosts_path, "a") as file:
        for domain in ad_domains:
            if domain not in original_content:
                file.write(f"{redirect_ip} {domain}\n")

    print("Hosts file updated successfully.")

def flush_dns_cache():
    print("Flushing DNS cache...")
    if platform.system() == "Windows":
        subprocess.run(["ipconfig", "/flushdns"], check=True)
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(["dscacheutil", "-flushcache"], check=True)
        subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], check=True)
    elif platform.system() == "Linux":
        subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=True)
    else:
        print("Unsupported OS for DNS cache flushing.")
    print("DNS cache flushed.")

def change_dns_settings():
    print("Changing DNS settings to use AdGuard DNS...")
    dns_servers = ["94.140.14.14", "94.140.15.15"]

    if platform.system() == "Windows":
        # Get the name of the active network interface
        try:
            interface_name = (
                subprocess.check_output(
                    ["netsh", "interface", "show", "interface"],
                    text=True,
                )
                .splitlines()[3]
                .split()[-1]
            )

            # Set DNS servers using netsh
            subprocess.run(["netsh", "interface", "ip", "set", "dns", f"name={interface_name}", "source=static", f"addr={dns_servers[0]}", "register=primary"], check=True)
            subprocess.run(["netsh", "interface", "ip", "add", "dns", f"name={interface_name}", f"addr={dns_servers[1]}", "index=2"], check=True)
        except Exception as e:
            print(f"Failed to configure DNS settings: {e}")
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(["networksetup", "-setdnsservers", "Wi-Fi", *dns_servers], check=True)
    elif platform.system() == "Linux":
        subprocess.run(["nmcli", "con", "mod", "Wi-Fi", "ipv4.dns", ",".join(dns_servers)], check=True)
        subprocess.run(["nmcli", "con", "down", "Wi-Fi"], check=True)
        subprocess.run(["nmcli", "con", "up", "Wi-Fi"], check=True)
    else:
        print("Unsupported OS for DNS configuration.")
    print("DNS settings updated.")

def check_port_conflicts():
    """Check if port 53 is already in use and warn the user."""
    print("Checking for port conflicts on port 53...")
    system = platform.system()

    if system == "Windows":
        # Check if DNS Client service is running
        result = subprocess.run(["sc", "query", "Dnscache"], capture_output=True, text=True)
        if "RUNNING" in result.stdout:
            print("Port 53 may be in use by the DNS Client service.")
            messagebox.showwarning(
                "Port Conflict",
                "Port 53 is in use by the DNS Client service. "
                "You may need to stop this service manually to proceed.\n\n"
                "To stop the service, open Command Prompt as Administrator and run:\n"
                "sc stop Dnscache"
            )
    elif system == "Linux":
        # Check if systemd-resolved is running
        result = subprocess.run(["systemctl", "is-active", "systemd-resolved"], capture_output=True, text=True)
        if "active" in result.stdout:
            print("Port 53 may be in use by systemd-resolved.")
            messagebox.showwarning(
                "Port Conflict",
                "Port 53 is in use by systemd-resolved. "
                "You may need to stop this service manually to proceed.\n\n"
                "To stop the service, run:\n"
                "sudo systemctl stop systemd-resolved"
            )
    elif system == "Darwin":  # macOS
        # macOS uses mDNSResponder, which cannot be stopped easily
        print("Port 53 may be in use by mDNSResponder. Consider disabling it manually if needed.")
        messagebox.showwarning(
            "Port Conflict",
            "Port 53 is likely in use by mDNSResponder. "
            "Disabling mDNSResponder may disrupt network functionality.\n\n"
            "If you wish to proceed, consult macOS documentation for guidance."
        )
    else:
        print("Unsupported OS for port conflict resolution.")

def install_adguard_home():
    print("Installing AdGuard Home...")
    AG_HOME_URL = {
        "Windows": "https://static.adguard.com/adguardhome/release/AdGuardHome_windows_amd64.zip",
        "Darwin": "https://static.adguard.com/adguardhome/release/AdGuardHome_darwin_amd64.tar.gz",
        "Linux": "https://static.adguard.com/adguardhome/release/AdGuardHome_linux_amd64.tar.gz"
    }

    system = platform.system()
    if system not in AG_HOME_URL:
        print(f"Unsupported OS for AdGuard Home: {system}")
        return

    # Define installation directory
    if system == "Windows":
        ag_home_dir = "C:\\AdGuardHome"
    else:
        ag_home_dir = "/opt/AdGuardHome"

    # Check if AdGuard Home is already installed
    executable_path = os.path.join(ag_home_dir, "AdGuardHome", "AdGuardHome.exe" if system == "Windows" else "AdGuardHome")
    if os.path.exists(executable_path):
        print(f"AdGuard Home is already installed at {ag_home_dir}. Skipping installation steps.")
        return

    # Create installation directory
    print(f"Creating AdGuard Home directory at {ag_home_dir}...")
    os.makedirs(ag_home_dir, exist_ok=True)

    # Download AdGuard Home
    ag_home_file = os.path.join(ag_home_dir, "adguardhome.zip" if system == "Windows" else "adguardhome.tar.gz")
    print(f"Downloading AdGuard Home for {system}...")
    response = requests.get(AG_HOME_URL[system])
    with open(ag_home_file, "wb") as f:
        f.write(response.content)

    # Extract the archive
    print("Extracting AdGuard Home...")
    if system == "Windows":
        with zipfile.ZipFile(ag_home_file, "r") as zip_ref:
            zip_ref.extractall(ag_home_dir)
    else:
        with tarfile.open(ag_home_file, "r:gz") as tar_ref:
            tar_ref.extractall(ag_home_dir)

    # Locate the executable
    ag_executable = executable_path

    # Install AdGuard Home as a service
    print("Installing AdGuard Home as a service...")
    subprocess.run([ag_executable, "--service", "install"], check=True)

    # Check if the service is already running before starting it
    print("Checking if AdGuard Home service is already running...")
    result = subprocess.run([ag_executable, "--service", "status"], capture_output=True, text=True)
    if "running" in result.stdout.lower():
        print("AdGuard Home service is already running. Skipping start command.")
    else:
        print("Starting AdGuard Home service...")
        subprocess.run([ag_executable, "--service", "start"], check=True)

    print("AdGuard Home installed and running. Access it at http://localhost:3000.")

def install_network_wide_ad_blocker():
    print("Detecting OS and installing appropriate network-wide ad blocker...")
    system = platform.system()

    if system == "Linux":
        print("Linux detected. Installing Pi-hole...")
        install_pihole()
    elif system == "Darwin":  # macOS
        print("macOS detected. Installing AdGuard Home...")
        install_adguard_home()
    elif system == "Windows":
        print("Windows detected. Installing AdGuard Home...")
        install_adguard_home()
    else:
        print(f"Unsupported OS for network-wide ad blocking: {system}")

def setup_browser_extension():
    print("Setting up 'One for All' browser extension...")
    extension_dir = os.path.join(os.getcwd(), "one-for-all-extension")
    os.makedirs(extension_dir, exist_ok=True)

    manifest_content = """
{
  "manifest_version": 3,
  "name": "One for All",
  "version": "1.0",
  "description": "A comprehensive ad blocker that blocks ads everywhere.",
  "permissions": ["webRequest", "webRequestBlocking", "tabs", "activeTab"],
  "host_permissions": ["*://*/*"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"]
    }
  ],
  "icons": {
    "48": "icon.png"
  }
}
"""
    background_content = """
const blockedDomains = [
  "ads.example.com",
  "tracking.example.com",
  "analytics.example.com"
];

chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    const url = new URL(details.url);
    if (blockedDomains.includes(url.hostname)) {
      console.log(`Blocked request to: ${url.hostname}`);
      return { cancel: true };
    }
  },
  { urls: ["<all_urls>"] },
  ["blocking"]
);
"""
    content_content = """
const adSelectors = [
  "div[id*='ad-']",
  "iframe[src*='ads']",
  "img[src*='ads']",
  ".ad",
  "#ad",
  ".advertisement"
];

function hideAds() {
  adSelectors.forEach(selector => {
    const ads = document.querySelectorAll(selector);
    ads.forEach(ad => {
      ad.style.display = "none";
      console.log(`Hidden ad element: ${selector}`);
    });
  });
}

document.addEventListener("DOMContentLoaded", hideAds);
setInterval(hideAds, 2000);
"""

    with open(os.path.join(extension_dir, "manifest.json"), "w") as f:
        f.write(manifest_content)
    with open(os.path.join(extension_dir, "background.js"), "w") as f:
        f.write(background_content)
    with open(os.path.join(extension_dir, "content.js"), "w") as f:
        f.write(content_content)

    icon_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/No_advertising_logo.svg/48px-No_advertising_logo.svg.png"
    icon_path = os.path.join(extension_dir, "icon.png")
    with open(icon_path, "wb") as f:
        f.write(requests.get(icon_url).content)

    print(f"'One for All' browser extension created at {extension_dir}.")
    print("Manually load the unpacked extension in your browser.")

def gui_wizard():
    def on_submit():
        try:
            # Check for elevated privileges
            if not is_admin():
                messagebox.showerror("Error", "Please run this script with elevated privileges (as Administrator).")
                return

            # Check for port conflicts
            check_port_conflicts()

            # Proceed with setup
            update_hosts_file()
            flush_dns_cache()
            change_dns_settings()
            install_network_wide_ad_blocker()
            setup_browser_extension()
            messagebox.showinfo("Success", "'One for All' setup completed successfully!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Create the main window
    root = tk.Tk()
    root.title("'One for All' Setup Wizard")
    root.geometry("400x300")

    # Add labels and buttons
    tk.Label(root, text="Welcome to the 'One for All' Setup Wizard", font=("Arial", 14)).pack(pady=20)
    tk.Label(root, text="This wizard will guide you through setting up a comprehensive ad-blocking solution.", font=("Arial", 10)).pack()

    tk.Button(root, text="Start Setup", command=on_submit, font=("Arial", 12)).pack(pady=50)

    # Run the GUI
    root.mainloop()

if __name__ == "__main__":
    gui_wizard()