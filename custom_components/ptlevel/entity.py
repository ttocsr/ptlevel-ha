from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_IP_ADDRESS

class PTLevelBaseEntity(CoordinatorEntity):
    """Base class to link all entities to a single Device Registry entry."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        # Grab the hardware ID from the /config payload. Fallback to HA's entry ID if missing.
        self._device_id = coordinator.data.get("id", entry.entry_id)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": "PTLevel Monitor",
            "manufacturer": "ParemTech",
            "model": "Wireless PTLevel",
            "sw_version": str(self.coordinator.data.get("fw_v", "Unknown")),
            "hw_version": str(self.coordinator.data.get("hw_v", "Unknown")),
            "configuration_url": f"http://{self.entry.data.get(CONF_IP_ADDRESS)}/"
        }
