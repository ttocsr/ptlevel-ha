from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfVolume, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfElectricPotential, EntityCategory
from .const import DOMAIN, CONF_TANK_SIZE, CONF_FULL_AD
from .entity import PTLevelBaseEntity

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        PTLevelPercentageSensor(coordinator, entry),
        PTLevelGallonsSensor(coordinator, entry),
        PTLevelRawSensor(coordinator, entry),
        PTLevelZeroSensor(coordinator, entry),
        PTLevelBatterySensor(coordinator, entry),
        PTLevelWiFiSensor(coordinator, entry),
        PTLevelFirmwareSensor(coordinator, entry),
        PTLevelIPSensor(coordinator, entry),
        PTLevelMacSensor(coordinator, entry),
        PTLevelDeviceIDSensor(coordinator, entry)
    ])

# --- VOLUME & PERCENTAGE SENSORS ---

class PTLevelPercentageSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "PTlevel Level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_percentage"

    @property
    def native_value(self):
        current_ad = self.coordinator.data.get('1')
        zero_ad = self.coordinator.data.get('z')
        full_ad = self.entry.data.get(CONF_FULL_AD)
        
        if current_ad is None or zero_ad is None or not full_ad: return None
        if full_ad == zero_ad: return 0
            
        pct = ((float(current_ad) - float(zero_ad)) / (float(full_ad) - float(zero_ad))) * 100
        return round(max(0, min(100, pct)), 1)

class PTLevelGallonsSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "PTlevel Volume"
    _attr_native_unit_of_measurement = UnitOfVolume.GALLONS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_gallons"

    @property
    def native_value(self):
        current_ad = self.coordinator.data.get('1')
        zero_ad = self.coordinator.data.get('z')
        full_ad = self.entry.data.get(CONF_FULL_AD)
        tank_size = self.entry.data.get(CONF_TANK_SIZE, 0)
        
        if current_ad is None or zero_ad is None or not full_ad: return None
        if full_ad == zero_ad: return 0
            
        pct = ((float(current_ad) - float(zero_ad)) / (float(full_ad) - float(zero_ad))) * 100
        gallons = (max(0, min(100, pct)) / 100) * float(tank_size)
        return round(gallons, 1)

# --- RAW DATA SENSORS ---

class PTLevelRawSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "PTlevel Raw Value (1)"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:numeric-1-box-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_raw"

    @property
    def native_value(self):
        return self.coordinator.data.get('1')

    @property
    def extra_state_attributes(self):
        """Dumps the ENTIRE /config and /get_sensors payload into the attributes"""
        return self.coordinator.data

class PTLevelZeroSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "PTlevel Zero Value (z)"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:numeric-0-box-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_zero"

    @property
    def native_value(self):
        return self.coordinator.data.get('z')

# --- DEVICE HEALTH SENSORS ---

class PTLevelBatterySensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "PTlevel Battery"
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_battery"

    @property
    def native_value(self):
        return self.coordinator.data.get('bat') or self.coordinator.data.get('battery') or self.coordinator.data.get('v')

class PTLevelWiFiSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "PTlevel WiFi Signal"
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_wifi"

    @property
    def native_value(self):
        return self.coordinator.data.get('wifi') or self.coordinator.data.get('rssi') or self.coordinator.data.get('sig')

class PTLevelFirmwareSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "PTlevel Firmware Version"
    _attr_icon = "mdi:cellphone-arrow-down"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_firmware"

    @property
    def native_value(self):
        return self.coordinator.data.get('fw') or self.coordinator.data.get('ver') or self.coordinator.data.get('firmware')
# --- DIAGNOSTIC SENSORS ---

class PTLevelIPSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "IP Address"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_ip"

    @property
    def native_value(self):
        return self.entry.data.get(CONF_IP_ADDRESS)

class PTLevelMacSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "MAC Address"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:network"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_mac"

    @property
    def native_value(self):
        raw_mac = self.coordinator.data.get('mac', '')
        if len(raw_mac) == 12:
            return ":".join(raw_mac[i:i+2] for i in range(0, 12, 2)).upper()
        return raw_mac

class PTLevelDeviceIDSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Device ID"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:identifier"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_device_id"

    @property
    def native_value(self):
        return self.coordinator.data.get('id')
