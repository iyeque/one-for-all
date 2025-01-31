# One for All

A comprehensive ad-blocking solution that combines network-wide blocking with a custom browser extension to block ads everywhere.

![AdGuard Home](https://adguard.com/images/logo.png)

## Overview

"One for All" is an all-in-one ad-blocking tool designed to provide maximum protection against ads, trackers, and malicious domains. It integrates seamlessly with [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) to block ads at the DNS level while adding additional layers of protection through system-level and browser-level blocking.

## Features

- **Network-Wide Blocking**: Installs and configures AdGuard Home as a service to block ads at the DNS level.
- **Hosts File Updates**: Automatically updates the system's `hosts` file with ad-serving domains for additional blocking.
- **DNS Configuration**: Configures DNS settings to use AdGuard DNS for enhanced privacy and ad blocking.
- **Custom Browser Extension**: Includes a lightweight browser extension to block ads directly in the browser.
- **User-Friendly Setup**: Provides a GUI wizard to simplify the installation and configuration process.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Third-Party Software](#third-party-software)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- Python 3.x installed on your system.
- Elevated privileges (run as Administrator on Windows or with `sudo` on Linux/macOS).
- Git installed (optional, for cloning the repository).

### Steps

1. Clone this repository:
   ```bash
   git clone https://github.com/<your-username>/one-for-all.git
   cd one-for-all 
2. Install required dependencies:
   ```bash
   pip install requests
3. Run the script:
   On Windows, Linux/macOS:
      ```bash
      python one_for_all.py

      sudo python3 one_for_all.py
      
4. Follow the on-screen instructions provided by the GUI wizard.

## Usage
Once installed:

Access AdGuard Home's web interface at http://localhost:3000 to configure additional settings.
Use the custom browser extension by loading it as an unpacked extension in your browser.

## Third-Party Software
This project uses the following third-party software:

AdGuard Home : A network-wide ad blocker and DNS server.
Repository: https://github.com/AdguardTeam/AdGuardHome
License: GNU General Public License v3.0 (GPLv3)
EasyList : A popular ad-blocking filter list.
Source: https://easylist.to/easylist/easylist.txt

## Contributing
Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

## Fork the repository.
Create a new branch (git checkout -b feature/YourFeatureName).
Commit your changes (git commit -m "Add YourFeatureName").
Push to the branch (git push origin feature/YourFeatureName).
Open a pull request.
Please ensure your code adheres to the existing style and includes appropriate documentation.
