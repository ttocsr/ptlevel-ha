import logging
import aiohttp
import json
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_CONNECTION_TYPE, CONF_API_TOKEN, CONF_DEVICE_ID, CONNECTION_LOCAL, CONNECTION_TOKEN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]

async def fetch_ptlevel_local_data(ip_address):
    sensors_url = f"http://{ip_address}/get_sensors"
    config_url = f"http://{ip_address}/config"
    combined_data = {}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(sensors_url, timeout=10) as response:
                text = await response.text()
                sensors_json = json.loads(text)
                if isinstance(sensors_json, list):
                    for item in sensors_json: combined_data.update(item)
                elif isinstance(sensors_json, dict):
                    combined_data.update(sensors_json)
            async with session.get(config_url, timeout=10) as response:
                text = await response.text()
                config_json = json.loads(text)
                if isinstance(config_json, dict): combined_data.update(config_json)
            
            combined_data["bat"] = combined_data.get("2", combined_data.get("bat"))
            combined_data["rssi"] = combined_data.get("rx_rssi", combined_data.get("wifi"))
            combined_data["fw"] = combined_data.get("fw_v")
            return combined_data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with local PTLevel device: {err}")

async def fetch_ptlevel_token_data(device_id, api_token):
    url = f"https://api.ptdevices.com/token/v1/device/{device_id}?api_token={api_token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                text = await response.text()
                json_response = json.loads(text)
                data = json_response.get("data", {})
                
                # Normalize cloud keys to match our local architecture
                return {
                    "id": data.get("device_id"),
                    "mac": data.get("device_id"),
                    "ip": data.get("local_ip"),
                    "fw": data.get("version"),
                    "rssi": data.get("wifi_signal"),
                    "bat": data.get("device_data", {}).get("battery_voltage"),
                    "cloud_percent": data.get("device_data", {}).get("percent_level"),
                    "cloud_temp": data.get("device_data", {}).get("enclosure_temperature"),
                    "raw_cloud_payload": data # Dump everything into attributes
                }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with PTLevel Cloud API: {err}")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    conn_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL)

    async def async_update_data():
        if conn_type == CONNECTION_TOKEN:
            return await fetch_ptlevel_token_data(entry.data[CONF_DEVICE_ID], entry.data[CONF_API_TOKEN])
        else:
            return await fetch_ptlevel_local_data(entry.data[CONF_IP_ADDRESS])

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
