import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import dhcp
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_TANK_SIZE

class PTLevelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.discovered_ip = None

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> config_entries.ConfigFlowResult:
        """Handle discovery via DHCP."""
        self.discovered_ip = discovery_info.ip
        mac_address = discovery_info.macaddress

        # Prevent setting it up twice if it's already configured
        await self.async_set_unique_id(mac_address)
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: self.discovered_ip})

        # Set the name that appears in the discovery notification
        self.context["title_placeholders"] = {
            "name": f"PTLevel ({self.discovered_ip})"
        }

        # Move to the user step to finish configuration
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle the manual input or the step after discovery."""
        if user_input is not None:
            return self.async_create_entry(title=f"Cistern ({user_input[CONF_IP_ADDRESS]})", data=user_input)

        # If we arrived here from DHCP, pre-fill the IP address
        default_ip = self.discovered_ip if self.discovered_ip else ""

        data_schema = vol.Schema({
            vol.Required(CONF_IP_ADDRESS, default=default_ip): str,
            vol.Required(CONF_TANK_SIZE, default=1000): int,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)
