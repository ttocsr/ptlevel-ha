import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.components import dhcp
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.device_registry import format_mac

from .const import (
    DOMAIN, CONF_IP_ADDRESS, CONF_TANK_SIZE, CONF_VOLUME_UNIT, 
    CONF_CONNECTION_TYPE, CONF_API_TOKEN, CONF_DEVICE_ID, 
    CONNECTION_LOCAL, CONNECTION_TOKEN, CONNECTION_REST,
    UNIT_LITERS, UNIT_IMP_GAL, UNIT_US_GAL, CONF_FULL_AD, CONF_ZERO_AD
)

_LOGGER = logging.getLogger(__name__)

class PTLevelConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    def __init__(self):
        self.discovered_ip = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PTLevelOptionsFlowHandler(config_entry)

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
        data[CONF_CONNECTION_TYPE] = CONNECTION_REST
        await self.async_set_unique_id("ptlevel_oauth_account")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="ParemTech Account", data=data)

    def _get_base_schema(self, default_ip="", opts=None, data=None):
        if opts is None: opts = {}
        if data is None: data = {}
        
        schema = {}
        if default_ip is not None:
            schema[vol.Required(CONF_IP_ADDRESS, default=default_ip)] = str
        
        try:
            tank_size = int(opts.get(CONF_TANK_SIZE, data.get(CONF_TANK_SIZE, 3300)))
        except (ValueError, TypeError):
            tank_size = 3300
            
        vol_unit = opts.get(CONF_VOLUME_UNIT, data.get(CONF_VOLUME_UNIT, UNIT_IMP_GAL))
        
        schema[vol.Optional(CONF_TANK_SIZE, default=tank_size)] = vol.Coerce(int)
        schema[vol.Required(CONF_VOLUME_UNIT, default=vol_unit)] = vol.In([UNIT_LITERS, UNIT_IMP_GAL, UNIT_US_GAL])
        
        # Switched to safely coerce into standard integers!
        zero_ad = opts.get(CONF_ZERO_AD, data.get(CONF_ZERO_AD))
        try:
            schema[vol.Optional(CONF_ZERO_AD, default=int(zero_ad))] = vol.Coerce(int)
        except (ValueError, TypeError):
            schema[vol.Optional(CONF_ZERO_AD)] = vol.Coerce(int)
            
        full_ad = opts.get(CONF_FULL_AD, data.get(CONF_FULL_AD))
        try:
            schema[vol.Optional(CONF_FULL_AD, default=int(full_ad))] = vol.Coerce(int)
        except (ValueError, TypeError):
            schema[vol.Optional(CONF_FULL_AD)] = vol.Coerce(int)
            
        return schema

    async def async_step_local(self, user_input=None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_LOCAL
            return self.async_create_entry(title=f"PTLevel ({user_input[CONF_IP_ADDRESS]})", data=user_input)

        schema = self._get_base_schema(self.discovered_ip if self.discovered_ip else "")
        schema[vol.Optional(CONF_API_TOKEN, default="")] = str
        return self.async_show_form(step_id="local", data_schema=vol.Schema(schema))

    async def async_step_cloud(self, user_input=None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TOKEN
            mac = format_mac(user_input[CONF_DEVICE_ID])
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"PTLevel Remote ({user_input[CONF_DEVICE_ID]})", data=user_input)

        schema = self._get_base_schema(None)
        schema[vol.Required(CONF_DEVICE_ID)] = str
        schema[vol.Required(CONF_API_TOKEN)] = str
        return self.async_show_form(step_id="cloud", data_schema=vol.Schema(schema))

class PTLevelOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        data = self.config_entry.data
        schema_dict = {}
        
        try:
            tank_size = int(opts.get(CONF_TANK_SIZE, data.get(CONF_TANK_SIZE, 3300)))
        except (ValueError, TypeError):
            tank_size = 3300
            
        vol_unit = opts.get(CONF_VOLUME_UNIT, data.get(CONF_VOLUME_UNIT, UNIT_IMP_GAL))
        
        schema_dict[vol.Optional(CONF_TANK_SIZE, default=tank_size)] = vol.Coerce(int)
        schema_dict[vol.Required(CONF_VOLUME_UNIT, default=vol_unit)] = vol.In([UNIT_LITERS, UNIT_IMP_GAL, UNIT_US_GAL])
        
        # Integer logic applied to the Configure gear menu too
        zero_ad = opts.get(CONF_ZERO_AD, data.get(CONF_ZERO_AD))
        try:
            schema_dict[vol.Optional(CONF_ZERO_AD, default=int(zero_ad))] = vol.Coerce(int)
        except (ValueError, TypeError):
            schema_dict[vol.Optional(CONF_ZERO_AD)] = vol.Coerce(int)
            
        full_ad = opts.get(CONF_FULL_AD, data.get(CONF_FULL_AD))
        try:
            schema_dict[vol.Optional(CONF_FULL_AD, default=int(full_ad))] = vol.Coerce(int)
        except (ValueError, TypeError):
            schema_dict[vol.Optional(CONF_FULL_AD)] = vol.Coerce(int)

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
