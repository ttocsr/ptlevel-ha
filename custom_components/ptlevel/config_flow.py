import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import dhcp
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_TANK_SIZE, CONF_CONNECTION_TYPE, CONF_API_TOKEN, CONF_DEVICE_ID, CONNECTION_LOCAL, CONNECTION_TOKEN

class PTLevelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.discovered_ip = None

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> config_entries.ConfigFlowResult:
        """Handle discovery via DHCP."""
        self.discovered_ip = discovery_info.ip
        await self.async_set_unique_id(discovery_info.macaddress)
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: self.discovered_ip})
        self.context["title_placeholders"] = {"name": f"PTLevel ({self.discovered_ip})"}
        return await self.async_step_local()

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """First step: Choose connection type."""
        if user_input is not None:
            if user_input[CONF_CONNECTION_TYPE] == "Local API (IP Address)":
                return await self.async_step_local()
            else:
                return await self.async_step_token()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_TYPE, default="Local API (IP Address)"): vol.In(["Local API (IP Address)", "Cloud Token API"])
            })
        )

    async def async_step_local(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle local setup."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_LOCAL
            return self.async_create_entry(title=f"PTlevel ({user_input[CONF_IP_ADDRESS]})", data=user_input)

        default_ip = self.discovered_ip if self.discovered_ip else ""
        data_schema = vol.Schema({
            vol.Required(CONF_IP_ADDRESS, default=default_ip): str,
            vol.Required(CONF_TANK_SIZE, default=1000): int,
        })
        return self.async_show_form(step_id="local", data_schema=data_schema)

    async def async_step_token(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle cloud token setup."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TOKEN
            return self.async_create_entry(title=f"PTlevel Cloud ({user_input[CONF_DEVICE_ID]})", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID): str,
            vol.Required(CONF_API_TOKEN): str,
            vol.Required(CONF_TANK_SIZE, default=1000): int,
        })
        return self.async_show_form(step_id="token", data_schema=data_schema)
