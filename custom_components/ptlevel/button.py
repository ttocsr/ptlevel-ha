from homeassistant.components.button import ButtonEntity
from .const import DOMAIN, CONF_FULL_AD
from .entity import PTLevelBaseEntity

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PTLevelCalibrateButton(coordinator, entry)])

class PTLevelCalibrateButton(PTLevelBaseEntity, ButtonEntity):
    _attr_name = "Calibrate Full Level"
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
