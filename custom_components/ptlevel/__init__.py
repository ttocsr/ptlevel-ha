import logging
import aiohttp
import json
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]

async def fetch_ptlevel_data(ip_address):
    sensors_url = f"http://{ip_address}/get_sensors"
    config_url = f"http://{ip_address}/config"
    
    combined_data = {}
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Fetch the water level, zero, battery, and temperature data
            async with session.get(sensors_url, timeout=10) as response:
                text = await response.text()
                sensors_json = json.loads(text)
                
                # The API returns a list of dicts: [{"1":9994,"z":10040},{"5":18.8},{"2":6.6}]
                if isinstance(sensors_json, list):
                    for item in sensors_json:
                        combined_data.update(item)
                elif isinstance(sensors_json, dict):
                    combined_data.update(sensors_json)
                    
            # 2. Fetch the WiFi and Firmware data
            async with session.get(config_url, timeout=10) as response:
                text = await response.text()
                config_json = json.loads(text)
                if isinstance(config_json, dict):
                    combined_data.update(config_json)
                    
            # 3. Map ParemTech's cryptic keys to our standard sensor keys
            if "2" in combined_data:
                combined_data["bat"] = combined_data["2"] # Battery Voltage
            if "rx_rssi" in combined_data:
                combined_data["rssi"] = combined_data["rx_rssi"] # WiFi Signal
            if "fw_v" in combined_data:
                combined_data["fw"] = combined_data["fw_v"] # Firmware Version
                
            return combined_data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with PTLevel device: {err}")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    ip_address = entry.data[CONF_IP_ADDRESS]

    async def async_update_data():
        return await fetch_ptlevel_data(ip_address)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="ptlevel_sensor",
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
