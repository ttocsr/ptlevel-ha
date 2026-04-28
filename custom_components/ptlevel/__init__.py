import logging
import aiohttp
import re
import json
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]

async def fetch_ptlevel_data(ip_address):
    url = f"http://{ip_address}/"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                text = await response.text()
                
                # Try to parse the entire response as JSON
                try:
                    data = json.loads(text)
                    return data
                except json.JSONDecodeError:
                    pass
                
                # Fallback: If it's a raw string, find all key-value pairs
                # This regex looks for pattern like  key: value  or  "key":"value"
                matches = re.findall(r'["\']?([a-zA-Z0-9_]+)["\']?\s*:\s*["\']?([^,"\']+)', text)
                if matches:
                    parsed_data = {}
                    for key, val in matches:
                        # Try to convert numbers to floats, leave strings as strings
                        try:
                            parsed_data[key] = float(val)
                        except ValueError:
                            parsed_data[key] = val.strip()
                    return parsed_data
                    
                raise ValueError(f"Could not parse data from device. Raw response: {text}")
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
