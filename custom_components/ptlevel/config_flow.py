import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.device_registry import format_mac

from .const import (
    DOMAIN, 
    CONF_IP_ADDRESS, 
    CONF_TANK_SIZE, 
    CONF_CONNECTION_TYPE, 
    CONF_API_TOKEN, 
    CONF_DEVICE_ID, 
    CONNECTION_LOCAL, 
    CONNECTION_TOKEN
)

_LOGGER = logging.getLogger(__name__)

# Used internally for the OAuth2 flow
CONNECTION_OAUTH2 = "oauth2"

class PTLevelConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a config flow for PTLevel."""

    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    def __init__(self):
        """Initialize the config flow."""
        self.discovered_ip = None

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> config_entries.ConfigFlowResult:
        """Handle discovery via DHCP."""
        self.discovered_ip = discovery_info.ip
        
        # Standardize the MAC so HA knows if it was already setup via Cloud
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: self.discovered_ip})
        
        self.context["title_placeholders"] = {"name": f"PTLevel ({self.discovered_ip})"}
        
        # Route them to the main menu instead of forcing Local
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """First step: Choose connection type."""
        if user_input is not None:
            if user_input[CONF_CONNECTION_TYPE] == "Local Network (with optional Cloud)":
                return await self.async_step_local()
            elif user_input[CONF_CONNECTION_TYPE] == "Cloud Only (Token API)":
                return await self.async_step_cloud()
            else:
                # Kicks off Home Assistant's built-in OAuth2 Web Redirect logic
                return await super().async_step_user()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_TYPE, default="Local Network (with optional Cloud)"): vol.In([
                    "Local Network (with optional Cloud)", 
                    "Cloud Only (Token API)",
                    "OAuth2 REST API (Advanced)"
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
        """Handle Cloud Only setup."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TOKEN
            
            # Format the PT Device ID as a standard MAC and register it
            # This is what stops DHCP from re-discovering the cloud device!
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
