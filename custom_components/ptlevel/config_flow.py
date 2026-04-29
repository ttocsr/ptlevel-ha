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
    CONNECTION_TOKEN,
    CONNECTION_REST
)

_LOGGER = logging.getLogger(__name__)

class PTLevelConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a config flow for PTLevel."""

    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    def __init__(self):
        self.discovered_ip = None

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> config_entries.ConfigFlowResult:
        self.discovered_ip = discovery_info.ip
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: self.discovered_ip})
        self.context["title_placeholders"] = {"name": f"PTLevel ({self.discovered_ip})"}
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            conn_type = user_input[CONF_CONNECTION_TYPE]
            if conn_type == "Local Network (with optional Cloud)":
                return await self.async_step_local()
            elif conn_type == "Cloud Only (Token API)":
                return await self.async_step_cloud()
            else:
                return await self.async_step_pick_implementation()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_TYPE, default="Local Network (with optional Cloud)"): vol.In([
                    "Local Network (with optional Cloud)", 
                    "Cloud Only (Token API)",
                    "OAuth2 Account Link (All Devices)"
                ])
            })
        )

    async def async_oauth_create_entry(self, data: dict) -> config_entries.ConfigFlowResult:
        """Create an entry after successful OAuth2 web flow."""
        data[CONF_CONNECTION_TYPE] = CONNECTION_REST
        data[CONF_TANK_SIZE] = 1000 # Default tank size for REST accounts
        
        # Lock the account so they don't link it twice
        await self.async_set_unique_id("ptlevel_oauth_account")
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(title="ParemTech Account", data=data)

    async def async_step_local(self, user_input=None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_LOCAL
            return self.async_create_entry(title=f"PTLevel ({user_input[CONF_IP_ADDRESS]})", data=user_input)

        default_ip = self.discovered_ip if self.discovered_ip else ""
        return self.async_show_form(
            step_id="local", 
            data_schema=vol.Schema({
                vol.Required(CONF_IP_ADDRESS, default=default_ip): str,
                vol.Optional(CONF_API_TOKEN, default=""): str,
                vol.Required(CONF_TANK_SIZE, default=1000): int,
            })
        )

    async def async_step_cloud(self, user_input=None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TOKEN
            mac = format_mac(user_input[CONF_DEVICE_ID])
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"PTLevel Remote ({user_input[CONF_DEVICE_ID]})", data=user_input)

        return self.async_show_form(
            step_id="cloud", 
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_API_TOKEN): str,
                vol.Required(CONF_TANK_SIZE, default=1000): int,
            })
        )
