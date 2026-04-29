from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE, UnitOfVolume, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfElectricPotential
from .const import DOMAIN, CONF_TANK_SIZE, CONF_FULL_AD

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Add all of our new sensors to the setup
    async_add_entities([
        PTLevelPercentageSensor(coordinator, entry),
        PTLevelGallonsSensor(coordinator, entry),
        PTLevelRawSensor(coordinator, entry),
        PTLevelZeroSensor(coordinator, entry),
        PTLevelBatterySensor(coordinator, entry),
        PTLevelWiFiSensor(coordinator, entry),
        PTLevelFirmwareSensor(coordinator, entry)
    ])

# --- VOLUME & PERCENTAGE SENSORS ---

class PTLevelPercentageSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Cistern Level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
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

class PTLevelGallonsSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Cistern Volume"
    _attr_native_unit_of_measurement = UnitOfVolume.GALLONS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
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

class PTLevelRawSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Cistern Raw Value (1)"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:numeric-1-box-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_raw"

    @property
    def native_value(self):
        return self.coordinator.data.get('1')

class PTLevelZeroSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Cistern Zero Value (z)"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:numeric-0-box-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_zero"

    @property
    def native_value(self):
        return self.coordinator.data.get('z')

# --- DEVICE HEALTH SENSORS ---

class PTLevelBatterySensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Cistern Battery"
    # Change to UnitOfElectricPotential.VOLTS if your API reports raw voltage instead of %.
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLTS
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_battery"

    @property
    def native_value(self):
        # Checks for common battery keys. Change 'bat' if your API uses 'v' or 'battery'
        return self.coordinator.data.get('bat') or self.coordinator.data.get('battery') or self.coordinator.data.get('v')

class PTLevelWiFiSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Cistern WiFi Signal"
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_wifi"

    @property
    def native_value(self):
        # Checks for common wifi keys. Change 'wifi' if your API uses 'rssi' or 'sig'
        return self.coordinator.data.get('wifi') or self.coordinator.data.get('rssi') or self.coordinator.data.get('sig')

class PTLevelFirmwareSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Cistern Firmware Version"
    _attr_icon = "mdi:cellphone-arrow-down"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_firmware"

    @property
    def native_value(self):
        # Checks for common firmware keys. 
        return self.coordinator.data.get('fw') or self.coordinator.data.get('ver') or self.coordinator.data.get('firmware')
