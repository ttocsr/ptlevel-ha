import logging
import voluptuous as vol
import json

from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, 
    CONF_IP_ADDRESS, 
    CONF_TANK_SIZE, 
    CONF_CONNECTION_TYPE, 
    CONF_API_TOKEN, 
    CONF_DEVICE_ID, 
    CONNECTION_LOCAL, 
    CONNECTION_TOKEN,
    CONNECTION_REST
)

_LOGGER = logging.getLogger(__name__)

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

class PTLevelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PTLevel."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow variables."""
        self.discovered_ip = None
        self.rest_token = None
        self.rest_devices = {}
        self.rest_tank_size = 1000

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> config_entries.ConfigFlowResult:
        """Handle discovery via DHCP."""
        self.discovered_ip = discovery_info.ip
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: self.discovered_ip})
        self.context["title_placeholders"] = {"name": f"PTLevel ({self.discovered_ip})"}
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """First step: Choose connection type."""
        if user_input is not None:
            conn_type = user_input[CONF_CONNECTION_TYPE]
            if conn_type == "Local Network (with optional Cloud)":
                return await self.async_step_local()
            elif conn_type == "Cloud Only (Token API)":
                return await self.async_step_cloud()
            else:
                return await self.async_step_rest()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_TYPE, default="Local Network (with optional Cloud)"): vol.In([
                    "Local Network (with optional Cloud)", 
                    "Cloud Only (Token API)",
                    "Cloud REST API (Advanced Data)"
                ])
            })
        )

    async def async_step_local(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle local setup."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_LOCAL
            return self.async_create_entry(title=f"PTLevel ({user_input[CONF_IP_ADDRESS]})", data=user_input)

        default_ip = self.discovered_ip if self.discovered_ip else ""
        data_schema = vol.Schema({
            vol.Required(CONF_IP_ADDRESS, default=default_ip): str,
            vol.Optional(CONF_API_TOKEN, default=""): str,
            vol.Required(CONF_TANK_SIZE, default=1000): int,
        })
        return self.async_show_form(step_id="local", data_schema=data_schema)

    async def async_step_cloud(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle Cloud Only (Token API) setup."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TOKEN
            mac = format_mac(user_input[CONF_DEVICE_ID])
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(title=f"PTLevel Remote ({user_input[CONF_DEVICE_ID]})", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID): str,
            vol.Required(CONF_API_TOKEN): str,
            vol.Required(CONF_TANK_SIZE, default=1000): int,
        })
        return self.async_show_form(step_id="cloud", data_schema=data_schema)

    async def async_step_rest(self, user_input=None) -> config_entries.ConfigFlowResult:
        """REST Step 1: Authenticate and fetch available devices."""
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            token_url = "https://ptdevices.com/api/authorize"
            payload = {
                "grant_type": "client_credentials",
                "client_id": user_input[CONF_CLIENT_ID],
                "client_secret": user_input[CONF_CLIENT_SECRET]
            }
            self.rest_tank_size = user_input[CONF_TANK_SIZE]

            try:
                # 1. Fetch Token
                async with session.post(token_url, data=payload, timeout=10) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.rest_token = token_data.get("access_token")
                    else:
                        errors["base"] = "auth_failed"
                        
                # 2. Fetch Devices List if token succeeded
                if self.rest_token:
                    devices_url = "https://ptdevices.com/v1/devices"
                    headers = {"Authorization": f"Bearer {self.rest_token}", "Accept": "application/json"}
                    
                    async with session.get(devices_url, headers=headers, timeout=10) as resp:
                        if resp.status == 200:
                            devices_json = await resp.json()
                            devices = devices_json.get("data", [])
                            
                            if not devices:
                                errors["base"] = "no_devices"
                            else:
                                # Create a dictionary mapping the Device ID to its friendly Title
                                self.rest_devices = {
                                    str(d.get("device_id")): f"{d.get('title', 'Unknown')} ({d.get('device_id')})"
                                    for d in devices if d.get("device_id")
                                }
                                # Move to the selection step
                                return await self.async_step_rest_select()
                        else:
                            errors["base"] = "auth_failed"
                            
            except Exception as e:
                _LOGGER.error(f"Error connecting to ParemTech REST API: {e}")
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_CLIENT_ID): str,
            vol.Required(CONF_CLIENT_SECRET): str,
            vol.Required(CONF_TANK_SIZE, default=1000): int,
        })
        
        return self.async_show_form(step_id="rest", data_schema=data_schema, errors=errors)

    async def async_step_rest_select(self, user_input=None) -> config_entries.ConfigFlowResult:
        """REST Step 2: User selects which device to add."""
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            
            # Register MAC to prevent duplicates
            mac = format_mac(device_id)
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            # Package the data and create the entry!
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_REST,
                CONF_API_TOKEN: self.rest_token,
                CONF_DEVICE_ID: device_id,
                CONF_TANK_SIZE: self.rest_tank_size
            }
            title = self.rest_devices[device_id]
            
            return self.async_create_entry(title=f"PTLevel ({title})", data=data)

        # Show dropdown menu of available devices
        data_schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID): vol.In(self.rest_devices)
        })
        return self.async_show_form(step_id="rest_select", data_schema=data_schema)
