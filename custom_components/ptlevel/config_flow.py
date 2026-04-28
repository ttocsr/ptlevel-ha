import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_TANK_SIZE

class PTLevelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Save the inputs and create the integration instance
            return self.async_create_entry(title=f"Cistern ({user_input[CONF_IP_ADDRESS]})", data=user_input)

        # Build the form
        data_schema = vol.Schema({
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required(CONF_TANK_SIZE, default=1000): int,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)
