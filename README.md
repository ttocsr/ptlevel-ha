# PTLevel Integration for Home Assistant

A fully-featured custom component to integrate your [ParemTech PTLevel](https://ptlevel.com/) liquid level monitors into Home Assistant. 

This integration supports three different connection methods—Local Network, Cloud REST API, and Cloud Token API—allowing you to choose the perfect balance of speed, privacy, and remote management for your setup.

## ✨ Features
* **Three API Modes:** Connect locally for instant updates, or via the Cloud for remote tanks.
* **Dynamic Volume Calculation:** Automatically estimates tank volume in Liters, US Gallons, or Imperial Gallons based on your custom tank size.
* **Multi-Device Support:** The REST API pulls in all devices attached to your ParemTech account seamlessly.
* **Comprehensive Device Health:** Monitors Battery Voltage, Battery Status, WiFi Signal, Firmware, and IP/MAC addresses.
* **Advanced Local Diagnostics:** Access Raw AD values, Zero points, Reset Reasons, and natively reboot the device directly from Home Assistant.
* **Native Calibration:** Set the Full Point locally or use the custom Action to calibrate remote tanks dynamically.

---

## 📥 Installation

### Option 1: HACS (Recommended)
1. Open HACS in Home Assistant.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add the URL to this repository and select **Integration** as the category.
4. Click **Add**, then search for "PTLevel" in HACS and click Download.
5. Restart Home Assistant.

### Option 2: Manual Installation
1. Download the latest release from this repository.
2. Copy the `ptlevel` folder into your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

---

## ⚙️ Setup & Configuration

Once installed, go to **Settings** -> **Devices & Services** -> **Add Integration** and search for **PTLevel**. You will be prompted to choose one of three connection methods:

### Option A: Local Network (Recommended)
Fastest and most reliable. Communicates directly with the PTLevel device on your local WiFi network. Bypasses the cloud entirely.
* **IP Address:** The IP address of your PTLevel device (can often be auto-discovered).
* **Tank Size (Optional):** The total capacity of your tank (used to estimate volume).
* **Units:** Choose between Liters, Imperial Gallons, or US Gallons.

### Option B: Cloud REST API (Multi-Device Support)
Best if you want to manage multiple PTLevel devices on a single account, or want to access advanced cloud actions (like the dynamic calibration service).

Because this relies on a secure Application Link, setup is a two-part process.

**Part 1: Generate your Client ID and Secret**
1. Open the PTDevices App or log into the web portal.
2. Navigate to **Home** -> **Account**.
3. Scroll down to the bottom and click the **Gear/Settings** tab.
4. *(Note: You will see "Token API" at the top of this page. Ignore this section).*
5. Scroll down to the **REST API** section. Look for the **"Create New Client"** heading. 
6. In the text box directly to the right of the "Create New Client" button, paste this exact URL: `https://my.home-assistant.io/redirect/oauth`
7. Click the **Create New Client** button.
8. The system will generate a **Client ID** and a **Client Secret**. Copy both of these down.

**Part 2: Add Credentials to Home Assistant**
1. Open Home Assistant and navigate to **Settings** > **Devices & Services**.
2. Click the **Three Dots Menu (`...`)** in the top right corner.
3. Select **Application Credentials** from the dropdown menu.
4. Click **Add Application Credentials** in the bottom right corner.
5. Fill out the form:
   * **Integration:** Select **PTLevel**
   * **Name:** `ParemTech REST API`
   * **Client ID:** Paste the Client ID you generated in Part 1.
   * **Client Secret:** Paste the Client Secret you generated in Part 1.
6. Click **Create**.

**Part 3: Add the Integration**
1. Navigate back to the main **Devices & Services** page.
2. Click **Add Integration** and search for **PTLevel**.
3. Select **OAuth2 Account Link (All Devices)** from the dropdown menu. 
4. Home Assistant will securely redirect you to the ParemTech login page. Log in with your standard email and password to authorize the link.
5. Home Assistant will automatically discover and set up every PTLevel device attached to your account!

### Option C: Cloud Only (Token API)
Best for a single, remote tank where you only want standard monitoring data.
1. Log into your PTDevices account and go to **Account** -> **Settings**.
2. Under the **Token API** section, copy your generated token.
3. Back in Home Assistant, select the **Cloud Only** connection type.
4. Enter your Device ID (MAC Address) and your API Token.

---

## 🛠️ Provided Entities

Depending on your connection type, the following entities will be created for each tank:

| Sensor / Entity | Type | Available In | Description |
| :--- | :--- | :--- | :--- |
| Level | Sensor | All | The water level percentage (0-100%). |
| Volume | Sensor | All | Estimated volume in your selected unit based on the tank size. |
| Temperature | Sensor | All | Enclosure temperature. |
| Battery Voltage | Sensor | All | Device battery voltage. |
| Battery Status | Sensor | All | Good, Ok, or Low. |
| WiFi Signal | Sensor | All | Device WiFi signal strength (%). |
| Firmware Version | Sensor | All | Current firmware version running on the device. |
| IP Address | Sensor | All | The local IP of the device. |
| MAC Address | Sensor | All | The hardware MAC address. |
| Raw Value (1) | Sensor | Local Only | The raw AD sensor reading. |
| Zero Value (z) | Sensor | Local Only | The established zero-point AD reading. |
| Reset Reason | Sensor | Local Only | The reason for the last device reboot. |
| Set Full Point | Button | Local Only | Captures the current Raw AD value as the new 100% full mark. |
| Restart Device | Button | Local Only | Sends a command to reboot the ESP chip. |

---

## ⚡ Services / Actions

When set up via the REST API, this integration exposes a custom Home Assistant Action that allows you to easily calibrate your tank levels from dashboards or automations.

**`ptlevel.calibrate_rest_level`**
* **`device_id`**: The MAC address of your device (e.g., `28372FA8D66C`).
* **`tank_height`**: The total depth/height of your tank (e.g., 100).
* **`water_height`**: The current exact height of the water (e.g., 85).

*The integration will automatically calculate the new percentage and fire the proper calibration payload to the cloud.*

---

## 🐛 Troubleshooting & Notes
* **Polling Limits:** The Local API polls your device every 60 seconds. To prevent your account from being rate-limited by ParemTech, the Cloud Token and REST APIs poll every 10 minutes.
* **Volume Estimation:** Volume is a mathematical estimation based on the percentage level and your stated tank size. It assumes a uniform tank shape (like a vertical cylinder or square). 
* **Duplicate Sensors:** If you switch connection types (e.g., moving from Local to REST), Home Assistant will seamlessly merge the devices based on their MAC Address so you don't end up with duplicate dashboards.
