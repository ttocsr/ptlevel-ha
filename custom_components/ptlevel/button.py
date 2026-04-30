import logging
import aiohttp
from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.const import EntityCategory
from .const import DOMAIN, CONF_CONNECTION_TYPE, CONNECTION_LOCAL, CONF_IP_ADDRESS
from .entity import PTLevelBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    conn_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL)

    entities = []
    if conn_type == CONNECTION_LOCAL:
        entities.append(PTLevelRestartButton(coordinator, entry))
        entities.append(PTLevelCalibrateButton(coordinator, entry))
    async_add_entities(entities)

class PTLevelRestartButton(PTLevelBaseEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Restart Device"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_restart"

    async def async_press(self) -> None:
        """Handle the button press to reboot the device."""
        ip = self.entry.data.get(CONF_IP_ADDRESS)
        is_static = self.target_data.get("is_static", False)

        # The reboot hack: set the IP configuration to whatever it currently is
        enable_val = "1" if is_static else "0"
        url = f"http://{ip}/set_static_ip?enable={enable_val}"

        async with aiohttp.ClientSession() as session:
            try:
                # We use a very short timeout because the ESP chip drops the network connection immediately to reboot!
                async with session.get(url, timeout=3) as response:
                    if response.status == 200:
                        _LOGGER.info(f"Restart command sent to PTLevel ({ip})")
            except Exception:
                # A timeout exception is actually expected here, so we log it cleanly
                _LOGGER.info(f"PTLevel ({ip}) is restarting...")

class PTLevelCalibrateButton(PTLevelBaseEntity, ButtonEntity):
    _attr_name = "Set Full Point"
    _attr_icon = "mdi:car-coolant-level"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_calibrate_full"

    async def async_press(self) -> None:
        current_data = self.coordinator.data
        if current_data and '1' in current_data:
            full_ad = current_data['1']
            new_data = dict(self.entry.data)
            new_data[CONF_FULL_AD] = full_ad
            self.hass.config_entries.async_update_entry(self.entry, data=new_data)
            await self.coordinator.async_request_refresh()
