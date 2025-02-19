import os
import platform
import subprocess
import requests
import tarfile
import zipfile
import tkinter as tk
from tkinter import messagebox
import time
import threading
import shutil
import secrets

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
    filter_list_url = "https://easylist.to/easylist/easylist.txt"
    print("Fetching ad-serving domains from EasyList...")
    try:
        response = requests.get(filter_list_url, timeout=10)  # Add a timeout to prevent hanging
        response.raise_for_status()  # Raise an exception for HTTP errors
        print(f"Fetched {len(response.text.splitlines())} lines from EasyList.")
    except requests.RequestException as e:
        print(f"Failed to fetch EasyList: {e}")
        return

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
        print(f"Backed up hosts file to {backup_path}.")

    # Append ad-blocking entries
    try:
        with open(hosts_path, "a") as file:
            for domain in ad_domains:
                if domain not in original_content:
                    file.write(f"{redirect_ip} {domain}\n")
        print("Hosts file updated successfully.")
    except PermissionError:
        print("Permission denied: Unable to modify the hosts file. Please run the script as Administrator.")
        return

def flush_dns_cache():
    print("Flushing DNS cache...")
    try:
        if platform.system() == "Windows":
            subprocess.run(["ipconfig", "/flushdns"], check=True, timeout=10)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["dscacheutil", "-flushcache"], check=True, timeout=10)
            subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], check=True, timeout=10)
        elif platform.system() == "Linux":
            subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=True, timeout=10)
        else:
            print("Unsupported OS for DNS cache flushing.")
        print("DNS cache flushed.")
    except Exception as e:
        print(f"Failed to flush DNS cache: {e}")

def change_dns_settings_windows():
    print("Changing DNS settings on Windows...")
    dns_servers = ["94.140.14.14", "94.140.15.15"]  # AdGuard DNS servers

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
            if "Connected" in line and "Wi-Fi" in line:
                active_interface = line.split()[-1]  # Extract interface name
                break

        if not active_interface:
            print("No active Wi-Fi interface found.")
            return

        # Set primary DNS
        subprocess.run(
            ["netsh", "interface", "ip", "set", "dns", f"name={active_interface}", "source=static", f"addr={dns_servers[0]}", "register=primary"],
            check=True,
            timeout=10
        )

        # Add secondary DNS
        subprocess.run(
            ["netsh", "interface", "ip", "add", "dns", f"name={active_interface}", f"addr={dns_servers[1]}", "index=2"],
            check=True,
            timeout=10
        )

        print(f"DNS settings updated for interface: {active_interface}")
    except Exception as e:
        print(f"Failed to configure DNS settings: {e}")

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
    try:
        response = requests.get(AG_HOME_URL[system], timeout=10)
        response.raise_for_status()
        with open(ag_home_file, "wb") as f:
            f.write(response.content)
        print("Download completed.")
    except requests.RequestException as e:
        print(f"Failed to download AdGuard Home: {e}")
        return

    # Extract the archive
    print("Extracting AdGuard Home...")
    try:
        if system == "Windows":
            with zipfile.ZipFile(ag_home_file, "r") as zip_ref:
                zip_ref.extractall(ag_home_dir)
        else:
            with tarfile.open(ag_home_file, "r:gz") as tar_ref:
                tar_ref.extractall(ag_home_dir)
        print("Extraction completed.")
    except Exception as e:
        print(f"Failed to extract AdGuard Home: {e}")
        return

    # Locate the executable
    ag_executable = executable_path

    # Install AdGuard Home as a service
    print("Installing AdGuard Home as a service...")
    try:
        subprocess.run([ag_executable, "--service", "install"], check=True, timeout=10)
    except Exception as e:
        print(f"Failed to install AdGuard Home as a service: {e}")
        return

    # Check if the service is already running before starting it
    print("Checking if AdGuard Home service is already running...")
    try:
        result = subprocess.run([ag_executable, "--service", "status"], capture_output=True, text=True, timeout=10)
        if "running" in result.stdout.lower():
            print("AdGuard Home service is already running. Skipping start command.")
        else:
            print("Starting AdGuard Home service...")
            subprocess.run([ag_executable, "--service", "start"], check=True, timeout=10)
    except Exception as e:
        print(f"Failed to start AdGuard Home service: {e}")
        return

    print("AdGuard Home installed and running. Access it at http://localhost:3000.")

def setup_browser_extension():
    print("Setting up 'One for All' browser extension...")
    extension_dir = os.path.join(os.getcwd(), "one-for-all-extension")  # Define the extension directory
    os.makedirs(extension_dir, exist_ok=True)

    # Helper function to write files only if they don't exist
    def write_file_if_not_exists(file_path, content):
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"File created: {file_path}")
        else:
            print(f"File already exists, skipping: {file_path}")

    # Manifest.json content (updated to remove popup)
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
      "js": ["content.js"]
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

    # Background.js content (updated to handle isEnabled state and alarms)
    background_content = """
const defaultBlocklists = [
  "https://easylist.to/easylist/easylist.txt",
  "https://easylist.to/easylist/easyprivacy.txt",
  "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/filters.txt"
];

async function fetchBlocklists() {
  try {
    const storedBlocklists = await chrome.storage.sync.get("blocklists");
    const blocklists = storedBlocklists.blocklists || defaultBlocklists;
    let blockedDomains = [];

    // Generate a unique ID for each rule using a counter
    let ruleIdCounter = 1;

    for (const url of blocklists) {
      try {
        const response = await fetch(url);
        const rules = await response.text();
        rules.split("\n").forEach((rule) => {
          if (rule.startsWith("||") && !rule.endsWith("^")) {
            const domain = rule.slice(2).split("^")[0];
            blockedDomains.push({
              id: ruleIdCounter++, // Use a counter to ensure unique IDs
              priority: 1,
              action: { type: "block" },
              condition: { urlFilter: domain, resourceTypes: ["main_frame", "sub_frame", "script", "image"] }
            });
          }
        });
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

// Schedule periodic updates using alarms
chrome.alarms.create("updateBlocklists", { periodInMinutes: 1440 }); // Run once per day

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "updateBlocklists") {
    await fetchBlocklists();
  }
});

// Initial fetch
fetchBlocklists();

// Cookie consent blocking
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && !tab.url.startsWith("chrome://")) {
    chrome.scripting.executeScript({
      target: { tabId },
      files: ["cookie-consent.js"]
    }).catch(error => {
      console.error("Failed to inject cookie-consent.js:", error);
    });
  }
});

// Handle isEnabled state
chrome.runtime.onStartup.addListener(async () => {
  const isEnabled = (await chrome.storage.sync.get("isEnabled")).isEnabled || true;

  if (!isEnabled) {
    // Clear all declarativeNetRequest rules if ad blocker is disabled
    try {
      const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
      const existingRuleIds = existingRules.map(rule => rule.id);

      await chrome.declarativeNetRequest.updateDynamicRules({
        removeRuleIds: existingRuleIds // Remove all rules
      });
      console.log("Ad blocker is disabled. Rules cleared.");
    } catch (error) {
      console.error("Error clearing rules:", error);
    }
  } else {
    fetchBlocklists(); // Re-enable ad blocker rules
    console.log("Ad blocker is enabled. Fetching blocklists.");
  }
});

// Listen for changes in isEnabled
chrome.storage.onChanged.addListener((changes) => {
  if (changes.isEnabled) {
    const isEnabled = changes.isEnabled.newValue;
    if (!isEnabled) {
      // Clear all declarativeNetRequest rules if ad blocker is disabled
      chrome.declarativeNetRequest.getDynamicRules().then(existingRules => {
        const existingRuleIds = existingRules.map(rule => rule.id);

        chrome.declarativeNetRequest.updateDynamicRules({
          removeRuleIds: existingRuleIds // Remove all rules
        }).then(() => {
          console.log("Ad blocker is disabled. Rules cleared.");
        }).catch(error => {
          console.error("Error clearing rules:", error);
        });
      });
    } else {
      fetchBlocklists(); // Re-enable ad blocker rules
      console.log("Ad blocker is enabled. Fetching blocklists.");
    }
  }
});
"""
    write_file_if_not_exists(os.path.join(extension_dir, "background.js"), background_content)

    # Content.js content
    content_content = """
const adSelectors = [
  "ytd-display-ad-renderer", // YouTube display ads
  "ytd-promoted-video-renderer", // Promoted videos in search results
  ".ytp-ad-module", // YouTube video ads module
  ".video-ads", // Video ads container
  ".ytp-ad-player-overlay", // Ad overlay on videos
  ".ytp-ad-skip-button", // Skip ad button
  ".ytp-ad-text", // Text indicating an ad
  ".ytp-ad-action-interstitial" // Full-screen interstitial ads
];

function hideAds() {
  const ads = document.querySelectorAll(adSelectors.join(", "));
  ads.forEach(ad => {
    ad.style.display = "none";
    console.log(`Hidden ad element: ${ad}`);
  });
}

document.addEventListener("DOMContentLoaded", hideAds);
setInterval(hideAds, 2000);

// MutationObserver for dynamically injected ads
const observer = new MutationObserver(mutations => {
  mutations.forEach(mutation => {
    mutation.addedNodes.forEach(node => {
      if (node.nodeType === 1 && adSelectors.some(selector => node.matches(selector))) {
        node.style.display = "none";
      }
    });
  });
});

observer.observe(document.body, { childList: true, subtree: true });
"""
    write_file_if_not_exists(os.path.join(extension_dir, "content.js"), content_content)

    # Cookie-consent.js content
    cookie_consent_content = """
const cookieConsentSelectors = [
  ".cc-banner",
  ".cookie-consent",
  ".cookie-notice",
  ".gdpr-banner"
];

cookieConsentSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  elements.forEach(el => {
    el.style.display = "none";
    console.log(`Hidden cookie consent banner: ${selector}`);
  });
});
"""
    write_file_if_not_exists(os.path.join(extension_dir, "cookie-consent.js"), cookie_consent_content)

    # Settings.html content with Feedback Form and Visual Feedback Tools
    settings_html_content = """
<!DOCTYPE html>
<html>
<head>
  <title>One for All Settings</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 20px;
    }
    h1 {
      font-size: 24px;
    }
    label {
      display: block;
      margin-top: 10px;
    }
    input[type="text"], textarea {
      width: 100%;
      padding: 5px;
      margin-top: 5px;
    }
    button {
      margin-top: 20px;
      padding: 10px 20px;
      background-color: #007bff;
      color: white;
      border: none;
      cursor: pointer;
    }
    button:hover {
      background-color: #0056b3;
    }
    #successMessage {
      color: green;
      margin-top: 10px;
      display: none;
    }
    @media (max-width: 600px) {
      input[type="text"], textarea {
        width: 100%;
      }
      button {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <h1>One for All Settings</h1>
  
  <!-- Blocklist Settings -->
  <label for="blocklists">Custom Blocklists (comma-separated URLs):</label>
  <input type="text" id="blocklists" placeholder="https://example.com/blocklist.txt, https://another.com/blocklist.txt">
  <button id="save">Save Settings</button>
  <div id="successMessage">Settings saved successfully!</div>

  <!-- Feedback Section -->
  <h2>Report Issues or Suggest Improvements</h2>
  <p>If you notice any issues or have suggestions for improvement, please let us know!</p>
  <label for="feedback">Your Feedback:</label>
  <textarea id="feedback" rows="5" placeholder="Describe the issue or suggestion..."></textarea>
  <button id="sendFeedback">Send Feedback</button>

  <script>
    document.addEventListener("DOMContentLoaded", async () => {
      const blocklistsInput = document.getElementById("blocklists");
      const saveButton = document.getElementById("save");
      const feedbackInput = document.getElementById("feedback");
      const sendFeedbackButton = document.getElementById("sendFeedback");
      const successMessage = document.getElementById("successMessage");

      // Load saved blocklists
      const storedBlocklists = await chrome.storage.sync.get("blocklists");
      blocklistsInput.value = storedBlocklists.blocklists ? storedBlocklists.blocklists.join(", ") : "";

      // Save blocklists
      saveButton.addEventListener("click", async () => {
        const blocklists = blocklistsInput.value.split(",").map(url => url.trim());

        // Validate URLs
        function isValidUrl(url) {
          try {
            new URL(url);
            return true;
          } catch (e) {
            return false;
          }
        }

        const validBlocklists = blocklists.filter(isValidUrl);

        if (validBlocklists.length !== blocklists.length) {
          alert("Some URLs are invalid. Please check your input.");
          return;
        }

        await chrome.storage.sync.set({ blocklists: validBlocklists });

        // Show success message
        successMessage.style.display = "block";
        setTimeout(() => {
          successMessage.style.display = "none";
        }, 3000);
      });

      // Send Feedback
      sendFeedbackButton.addEventListener("click", async () => {
        const feedback = feedbackInput.value.trim();
        if (!feedback) {
          alert("Please provide some feedback before submitting.");
          return;
        }

        try {
          // Example: Send feedback to Formspree
          const response = await fetch("https://formspree.io/f/your-form-id", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({ feedback })
          });

          if (response.ok) {
            alert("Thank you for your feedback! We'll review it soon.");
            feedbackInput.value = ""; // Clear the feedback box
          } else {
            alert("Failed to submit feedback. Please try again later.");
          }
        } catch (error) {
          console.error("Error submitting feedback:", error);
          alert("An error occurred while submitting feedback. Please try again later.");
        }
      });
    });
  </script>
</body>
</html>
"""
    write_file_if_not_exists(os.path.join(extension_dir, "settings.html"), settings_html_content)

    # Use your custom icon
    custom_icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")  # Path to your custom icon
    icon_path = os.path.join(extension_dir, "icon.png")

    if not os.path.exists(icon_path):
        try:
            # Copy the custom icon to the extension directory
            shutil.copy(custom_icon_path, icon_path)
            print("Custom icon copied successfully.")
        except Exception as e:
            print(f"Failed to copy custom icon: {e}")
    else:
        print("Icon already exists, skipping copy.")

    print(f"'One for All' browser extension created at {extension_dir}.")
    print("Manually load the unpacked extension in your browser.")

def gui_wizard():
    def on_submit():
        try:
            # Check for elevated privileges
            if not is_admin():
                messagebox.showerror("Error", "Please run this script with elevated privileges (as Administrator).")
                return

            # Proceed with setup
            update_hosts_file()
            flush_dns_cache()
            change_dns_settings_windows()
            install_adguard_home()

            # Set up the browser extension
            setup_browser_extension()

            # Close the wizard automatically
            root.destroy()

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
