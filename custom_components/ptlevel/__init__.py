import logging
import aiohttp
import json
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DOMAIN, 
    CONF_IP_ADDRESS, 
    CONF_CONNECTION_TYPE, 
    CONF_API_TOKEN, 
    CONF_DEVICE_ID, 
    CONNECTION_LOCAL, 
    CONNECTION_TOKEN,
    CONNECTION_REST
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]

async def fetch_ptlevel_rest_data(api_token, target_device_id=None):
    """Fetches data from the advanced REST API."""
    url = "https://ptdevices.com/v1/devices"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    raise UpdateFailed(f"REST API returned status {response.status}")
                    
                json_response = await response.json()
                devices = json_response.get("data", [])
                
                if not devices:
                    raise UpdateFailed("No devices found on this ParemTech account.")
                    
                # Find specific device if provided, otherwise default to the first one in the array
                target_data = next((d for d in devices if d.get("device_id") == target_device_id), devices[0])
                device_data = target_data.get("device_data", {})
                
                wifi_raw = str(target_data.get("wifi_signal", ""))
                wifi_pct = float(wifi_raw.replace("%", "")) if "%" in wifi_raw else None
                
                return {
                    "id": target_data.get("device_id"),
                    "mac": target_data.get("device_id"),
                    "ip": target_data.get("local_ip"),
                    "fw": target_data.get("version"),
                    "wifi_pct": wifi_pct,
                    "bat": device_data.get("battery_voltage"),
                    "bat_status": device_data.get("battery_status"),
                    "cloud_percent": device_data.get("percent_level"),
                    "temp": device_data.get("enclosure_temperature"),
                    "raw_cloud_payload": target_data 
                }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with PTLevel REST API: {err}")

async def fetch_ptlevel_token_data(device_id, api_token):
    """Fetches data from the standard Token API."""
    url = f"https://api.ptdevices.com/token/v1/device/{device_id}?api_token={api_token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                text = await response.text()
                json_response = json.loads(text)
                data = json_response.get("data", {})
                device_data = data.get("device_data", {})
                
                wifi_raw = str(data.get("wifi_signal", ""))
                wifi_pct = float(wifi_raw.replace("%", "")) if "%" in wifi_raw else None
                
                return {
                    "id": data.get("device_id"),
                    "mac": data.get("device_id"),
                    "ip": data.get("local_ip"),
                    "fw": data.get("version"),
                    "wifi_pct": wifi_pct,
                    "bat": device_data.get("battery_voltage"),
                    "bat_status": device_data.get("battery_status"),
                    "cloud_percent": device_data.get("percent_level"),
                    "temp": device_data.get("enclosure_temperature"),
                    "raw_cloud_payload": data 
                }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with PTLevel Cloud API: {err}")

async def fetch_ptlevel_local_data(ip_address, api_token=None):
    """Fetches local data, and optionally merges cloud Token API data if provided."""
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
            
            bat_voltage = combined_data.get("2", combined_data.get("bat"))
            combined_data["bat"] = bat_voltage
            combined_data["fw"] = combined_data.get("fw_v")
            combined_data["temp"] = combined_data.get("5")
            
            if bat_voltage is not None:
                v = float(bat_voltage)
                if v >= 6.0: combined_data["bat_status"] = "Good"
                elif v >= 5.5: combined_data["bat_status"] = "Ok"
                else: combined_data["bat_status"] = "Low"
                
            rssi = combined_data.get("rx_rssi", combined_data.get("wifi"))
            if rssi is not None:
                rssi_val = float(rssi)
                pct = max(0, min(100, int((rssi_val + 100) * 2)))
                combined_data["wifi_pct"] = pct

            if api_token and combined_data.get("mac"):
                try:
                    cloud_data = await fetch_ptlevel_token_data(combined_data["mac"], api_token)
                    combined_data["cloud_percent"] = cloud_data.get("cloud_percent")
                    if cloud_data.get("bat_status"):
                        combined_data["bat_status"] = cloud_data.get("bat_status")
                except Exception as e:
                    _LOGGER.warning(f"Could not reach PTLevel Cloud API to merge data: {e}")

            return combined_data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with local PTLevel device: {err}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    conn_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL)

    async def async_update_data():
        if conn_type == CONNECTION_REST:
            return await fetch_ptlevel_rest_data(entry.data[CONF_API_TOKEN], entry.data.get(CONF_DEVICE_ID))
        elif conn_type == CONNECTION_TOKEN:
            return await fetch_ptlevel_token_data(entry.data[CONF_DEVICE_ID], entry.data[CONF_API_TOKEN])
        else:
            api_token = entry.data.get(CONF_API_TOKEN)
            if not api_token: api_token = None
            return await fetch_ptlevel_local_data(entry.data[CONF_IP_ADDRESS], api_token)

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
