from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from .const import DOMAIN, CONF_IP_ADDRESS

class PTLevelBaseEntity(CoordinatorEntity):
    """Base class to link all entities to a single Device Registry entry."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._device_id = coordinator.data.get("id", entry.entry_id)

    @property
    def device_info(self):
        info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": "PTLevel Cistern Monitor",
            "manufacturer": "ParemTech",
            "model": "Wireless PTLevel",
            "sw_version": str(self.coordinator.data.get("fw_v", "Unknown")),
            "hw_version": str(self.coordinator.data.get("hw_v", "Unknown")),
            "configuration_url": f"http://{self.entry.data.get(CONF_IP_ADDRESS)}/"
        }
        
        # Format "28372FA8D66C" into "28:37:2F:A8:D6:6C" and add to network connections
        raw_mac = self.coordinator.data.get("mac")
        if raw_mac and len(raw_mac) == 12:
            formatted_mac = ":".join(raw_mac[i:i+2] for i in range(0, 12, 2))
            info["connections"] = {(CONNECTION_NETWORK_MAC, formatted_mac.lower())}
            
        return info
