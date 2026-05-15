import logging
import aiohttp
import json
import voluptuous as vol
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, CONF_IP_ADDRESS, CONF_CONNECTION_TYPE, CONF_API_TOKEN, 
    CONF_DEVICE_ID, CONNECTION_LOCAL, CONNECTION_TOKEN, CONNECTION_REST
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]

async def fetch_ptlevel_token_data(device_id, api_token):
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
    data_url = f"http://{ip_address}/get_data"
    combined_data = {}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(data_url, timeout=10) as response:
                text = await response.text()
                json_data = json.loads(text)
                combined_data.update(json_data)
                
                local_s = json_data.get("local_s", [])
                if isinstance(local_s, list):
                    for item in local_s:
                        combined_data.update(item)
            
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

    session = None
    if conn_type == CONNECTION_REST:
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)
        session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    async def handle_rest_calibrate(call):
        device_id = call.data.get("device_id")
        tank_height = float(call.data.get("tank_height"))
        water_height = float(call.data.get("water_height"))
        pct = int(round((water_height / tank_height) * 100))
        
        if session: 
            await session.async_ensure_token_valid()
            access_token = session.token["access_token"]
            client = async_get_clientsession(hass)
            headers = {
                "Authorization": f"Bearer {access_token}", 
                "Content-Type": "application/json",
                "Accept": "*/*"
            }
            payload = {"calibration_value": pct}
            url = f"https://ptdevices.com/v1/device/{device_id}/calibrate"
            try:
                async with client.post(url, headers=headers, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"PTLevel Calibration failed with status: {resp.status}")
                    else:
                        _LOGGER.info(f"Successfully calibrated PTLevel {device_id} to {pct}%")
                        await coordinator.async_request_refresh()
            except Exception as e:
                _LOGGER.error(f"Error sending calibration to PTLevel: {e}")

    if conn_type == CONNECTION_REST:
        hass.services.async_register(
            DOMAIN, 
            "calibrate_rest_level", 
            handle_rest_calibrate,
            schema=vol.Schema({
                vol.Required("device_id"): cv.string,
                vol.Required("tank_height"): vol.Coerce(float),
                vol.Required("water_height"): vol.Coerce(float),
            })
        )

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

    if conn_type == CONNECTION_LOCAL:
        poll_interval = timedelta(seconds=60)
    else:
        poll_interval = timedelta(minutes=10)

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name="ptlevel_sensor",
        update_method=async_update_data, update_interval=poll_interval,
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # THIS IS THE CRITICAL LINE THAT FORCES THE REFRESH ON OPTION CHANGE!
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Reload the integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok: hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
