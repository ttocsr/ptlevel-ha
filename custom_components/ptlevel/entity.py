from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_CONNECTION_TYPE, CONNECTION_LOCAL

class PTLevelBaseEntity(CoordinatorEntity):
    """Base class to link all entities to a single Device Registry entry."""
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._device_id = coordinator.data.get("id", entry.entry_id)

    @property
    def device_info(self):
        info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": "PTLevel",
            "manufacturer": "ParemTech",
            "model": "Wireless PTLevel",
            "sw_version": str(self.coordinator.data.get("fw", "Unknown")),
            "serial_number": str(self._device_id),
        }
        
        if self.entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL) == CONNECTION_LOCAL:
            info["configuration_url"] = f"http://{self.entry.data.get(CONF_IP_ADDRESS)}/"
        
        raw_mac = self.coordinator.data.get("mac")
        if raw_mac and len(raw_mac) == 12:
            formatted_mac = ":".join(raw_mac[i:i+2] for i in range(0, 12, 2))
            info["connections"] = {(CONNECTION_NETWORK_MAC, formatted_mac.lower())}
            
        return info
