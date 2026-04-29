from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from .const import DOMAIN, CONF_IP_ADDRESS, CONF_CONNECTION_TYPE, CONNECTION_LOCAL

class PTLevelBaseEntity(CoordinatorEntity):
    """Base class to link all entities to a single Device Registry entry."""
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, entry, specific_device_id=None):
        super().__init__(coordinator)
        self.entry = entry
        self._specific_device_id = specific_device_id

    @property
    def target_data(self):
        """Grabs the exact device data whether it's an array (REST) or single (Local/Token)."""
        if self._specific_device_id and "rest_devices" in self.coordinator.data:
            return self.coordinator.data["rest_devices"].get(self._specific_device_id, {})
        return self.coordinator.data

    @property
    def hardware_id(self):
        """Generates a universal ID based strictly on the MAC address."""
        mac = self.target_data.get("mac")
        if mac:
            # Strip any colons and ensure uppercase for a perfect match across APIs
            return str(mac).replace(":", "").upper()
        # Fallback to entry ID only if MAC is somehow missing
        return self.entry.entry_id

    @property
    def device_info(self):
        data = self.target_data
        _device_id = data.get("id", self.entry.entry_id)
        
        info = {
            "identifiers": {(DOMAIN, _device_id)},
            "name": data.get("title", "PTLevel"),
            "manufacturer": "ParemTech",
            "model": "Wireless PTLevel",
            "sw_version": str(data.get("fw", "Unknown")),
        }
        
        if self.entry.data.get(CONF_CONNECTION_TYPE) == CONNECTION_LOCAL:
            info["configuration_url"] = f"http://{self.entry.data.get(CONF_IP_ADDRESS)}/"
        
        raw_mac = data.get("mac")
        if raw_mac and len(raw_mac) == 12:
            formatted_mac = ":".join(raw_mac[i:i+2] for i in range(0, 12, 2))
            info["connections"] = {(CONNECTION_NETWORK_MAC, formatted_mac.lower())}
            
        return info
