import logging
import aiohttp
from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.const import EntityCategory
from .const import DOMAIN, CONF_CONNECTION_TYPE, CONNECTION_LOCAL, CONF_IP_ADDRESS, CONF_FULL_AD, CONF_ZERO_AD
from .entity import PTLevelBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    conn_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL)
    entities = []
    
    if conn_type == CONNECTION_LOCAL:
        entities.append(PTLevelRestartButton(coordinator, entry))
        entities.append(PTLevelSetEmptyButton(coordinator, entry))
        entities.append(PTLevelSetFullButton(coordinator, entry))
        
    async_add_entities(entities)

class PTLevelSetEmptyButton(PTLevelBaseEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Set Empty Point"
    _attr_icon = "mdi:arrow-down-bold-box-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_set_empty"

    async def async_press(self) -> None:
        """Saves the current raw AD value as the Zero/Empty point."""
        current_ad = self.target_data.get('1')
        if current_ad is not None:
            new_options = dict(self.entry.options)
            new_options[CONF_ZERO_AD] = float(current_ad)
            self.hass.config_entries.async_update_entry(self.entry, options=new_options)
            _LOGGER.info(f"PTLevel Empty Point calibrated to {current_ad}")

class PTLevelSetFullButton(PTLevelBaseEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Set Full Point"
    _attr_icon = "mdi:arrow-up-bold-box-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_set_full"

    async def async_press(self) -> None:
        """Saves the current raw AD value as the Full point."""
        current_ad = self.target_data.get('1')
        if current_ad is not None:
            new_options = dict(self.entry.options)
            new_options[CONF_FULL_AD] = float(current_ad)
            self.hass.config_entries.async_update_entry(self.entry, options=new_options)
            _LOGGER.info(f"PTLevel Full Point calibrated to {current_ad}")

class PTLevelRestartButton(PTLevelBaseEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Restart Device"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_restart"

    async def async_press(self) -> None:
        ip = self.entry.data.get(CONF_IP_ADDRESS)
        is_static = self.target_data.get("is_static", False)
        enable_val = "1" if is_static else "0"
        url = f"http://{ip}/set_static_ip?enable={enable_val}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=3) as response:
                    if response.status == 200:
                        _LOGGER.info(f"Restart command sent to PTLevel ({ip})")
            except Exception:
                _LOGGER.info(f"PTLevel ({ip}) is restarting...")
