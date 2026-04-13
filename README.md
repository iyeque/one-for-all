# One for All: Vertical Integration Ad-Blocking & Privacy Suite

"One for All" is a professional-grade, multi-layered privacy solution that synchronizes protection across your System, Network, and Browser. 

## 🛡️ The "Vertical" Advantage

Unlike standard blockers that only operate in the browser, "One for All" provides a three-tiered defense:

### 1. Network & System Engine (Python)
*   **Hybrid DNS Mode:** Blends **Cloudflare Security** (speed + malware protection) with **AdGuard Privacy** (surgical filtering).
*   **Parallel Queries:** Resolves DNS requests using multiple encrypted providers simultaneously, choosing the fastest response.
*   **Hardened Hosts:** A system-level "kill switch" for ad-serving domains with safe `# BEGIN/END` markers for clean management.
*   **Universal Support:** Native DNS configuration for **Windows, macOS, and Linux**.
*   **Automated Updates:** A "Set and Forget" scheduler that keeps your ad-blocking lists fresh in the background.
*   **Self-Healing Setup:** Automatically repairs or regenerates extension components if they are missing.
*   **Smart Connectivity:** Auto-detection of AdGuard Home on multiple ports (80/3000) for zero-config monitoring.

### 2. The "Smart" Browser Extension (MV3)
*   **Active Content Shielding**: 
    *   **Ad-Hiding Engine**: Real-time DOM scanning via `MutationObserver` to strip ad containers and sponsored posts from the page.
    *   **Cookie Notice Neutralization**: Automatically identifies and hides intrusive cookie consent banners and overlays.
*   **Script Shimming**: Injects dummy objects for Google Analytics and Facebook Pixel. Sites stay stable and functional while tracking is neutralized.
*   **Digital Trail Camouflage**: 
    *   **User-Agent Spoofing**: Reports a generic Windows/Chrome profile to blend in.
    *   **Referer Stripping**: Removes the "where did you come from" header on third-party requests.
    *   **X-Client-Data Removal**: Blocks Google's unique Chrome tracking header.
*   **Fingerprint Randomization**: 
    *   **Canvas/Audio Jitter**: Adds invisible noise to renderings to make your hardware fingerprint "unstable" and untrackable.
    *   **Hardware Spoofing**: Reports a standardized 8-core CPU and 8GB RAM profile.
*   **WebRTC Leak Protection**: Stops your real IP from leaking through VPNs.

### 3. User Control
*   **Self-Healing Architecture**: The Python controller features a dictionary-driven engine that can automatically reconstruct or repair the browser extension files if they are missing or corrupted.
*   **Intelligent Whitelisting**: A "Compatibility Mode" toggle that dynamically syncs network rules to allow specific sites while maintaining background protection.
*   **High-DPI Visuals**: Sharp, high-resolution icons for 4K and Retina displays.

---

## 🔒 Security & Identity

### Managing the Private Key (`.pem`)
To maintain your extension's identity across updates, the project uses a private key:
*   **Identity Persistence**: Your extension ID is tied to the `one-for-all-extension.pem` file. **Never share or commit this file.**
*   **Backup**: Move the `.pem` file to a secure, private location (like a password manager) outside of your project folder.
*   **Git Protection**: The project is pre-configured with a `.gitignore` that prevents `.pem` and `.crx` files from being accidentally tracked.

---

## 🚀 Setup & Launch

### 1. System Setup
Run the master installer with Administrator/Root privileges:
```bash
python one_for_all.py
```
*   Click **"Install / Update"**. This will configure your DNS, update hosts, and bootstrap AdGuard Home.

### 2. Browser Extension
*   Go to `chrome://extensions/` in any Chromium browser.
*   Enable **"Developer mode"**.
*   Click **"Load unpacked"** and select the `one-for-all-extension` folder.

### 3. Automated Updates
To keep your filters fresh without manual effort:
*   Open the "One for All Control Panel".
*   Click **"Schedule Weekly Updates"**.
*   This creates a Windows Task that runs every Sunday at 3:00 AM in `--silent` mode, updating your hosts file and AdGuard Home automatically.

### 4. Maintenance
*   **Dashboard:** View your DNS stats at `http://localhost:3000`.
*   **Revert:** Run the Python script and click **"Revert Changes"** to restore your system to its original state.

---

## 🔒 Security Philosophy
"One for All" is built on the principle of **"Noise over Silence."** Instead of just blocking (which makes you unique), it adds jitter and standardizes your profile so you blend into the most common crowd of web users.
