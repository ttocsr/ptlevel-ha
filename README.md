# PTLevel Direct to Device for Home Assistant

This is a custom integration for Home Assistant to connect locally to a [PTLevel](https://support.paremtech.com/) device via its Direct-to-Device API.

## Features
* Config Flow (Setup via the UI)
* Live Sensors: Cistern Percentage, Gallons, Raw Values, Battery, WiFi, and Firmware.
* UI Calibration: Easily calibrate your "Full" level dynamically with a button press.

## Installation via HACS
1. Open HACS in Home Assistant.
2. Click the 3-dots menu in the top right corner and select **Custom repositories**.
3. Paste the URL to this GitHub repository in the URL field.
4. Select **Integration** as the Category and click **Add**.
5. Search for "PTLevel" in HACS, click it, and select **Download**.
6. Restart Home Assistant.
7. Go to **Settings > Devices & Services > Add Integration** and search for PTLevel.
