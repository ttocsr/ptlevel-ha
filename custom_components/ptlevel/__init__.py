import logging
import aiohttp
import json
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, CONF_IP_ADDRESS, CONF_CONNECTION_TYPE, CONF_API_TOKEN, 
    CONF_DEVICE_ID, CONNECTION_LOCAL, CONNECTION_TOKEN, CONNECTION_REST
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]

# (Keep your fetch_ptlevel_local_data and fetch_ptlevel_token_data functions here as they were)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    conn_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL)

    # Setup OAuth2 Session if REST API
    session = None
    if conn_type == CONNECTION_REST:
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)
        session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    async def async_update_data():
        if conn_type == CONNECTION_REST:
            await session.async_ensure_token_valid()
            access_token = session.token["access_token"]
            
            client = async_get_clientsession(hass)
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            
            async with client.get("https://ptdevices.com/v1/devices", headers=headers, timeout=10) as resp:
                if resp.status != 200: raise UpdateFailed(f"REST API returned {resp.status}")
                devices = (await resp.json()).get("data", [])
                
                parsed_devices = {}
                for d in devices:
                    dev_id = str(d.get("device_id"))
                    dd = d.get("device_data", {})
                    wifi_raw = str(d.get("wifi_signal", ""))
                    
                    parsed_devices[dev_id] = {
                        "id": dev_id,
                        "mac": dev_id,
                        "ip": d.get("local_ip"),
                        "title": d.get("title"),
                        "fw": d.get("version"),
                        "wifi_pct": float(wifi_raw.replace("%", "")) if "%" in wifi_raw else None,
                        "bat": dd.get("battery_voltage"),
                        "bat_status": dd.get("battery_status"),
                        "cloud_percent": dd.get("percent_level"),
                        "temp": dd.get("enclosure_temperature"),
                        "raw_cloud_payload": d 
                    }
                return {"rest_devices": parsed_devices}
                
        elif conn_type == CONNECTION_TOKEN:
            return await fetch_ptlevel_token_data(entry.data[CONF_DEVICE_ID], entry.data[CONF_API_TOKEN])
        else:
            api_token = entry.data.get(CONF_API_TOKEN)
            if not api_token: api_token = None
            return await fetch_ptlevel_local_data(entry.data[CONF_IP_ADDRESS], api_token)

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name="ptlevel_sensor",
        update_method=async_update_data, update_interval=timedelta(seconds=60),
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok: hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
