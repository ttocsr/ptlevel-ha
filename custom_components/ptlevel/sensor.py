from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfVolume, UnitOfElectricPotential, UnitOfTemperature, EntityCategory
from .const import (
    DOMAIN, CONF_TANK_SIZE, CONF_VOLUME_UNIT, CONF_FULL_AD, 
    CONF_CONNECTION_TYPE, CONNECTION_LOCAL, 
    UNIT_LITERS, UNIT_IMP_GAL, UNIT_US_GAL
)
from .entity import PTLevelBaseEntity

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    conn_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL)
    
    entities = []
    
    # If REST, create a full set of sensors for every device in the account
    if "rest_devices" in coordinator.data:
        for device_id in coordinator.data["rest_devices"]:
            entities.extend(create_sensors(coordinator, entry, conn_type, device_id))
    else:
        # Standard Single Device Setup
        entities.extend(create_sensors(coordinator, entry, conn_type, None))
        
    async_add_entities(entities)

def create_sensors(coordinator, entry, conn_type, device_id):
    """Helper to generate a set of sensors for a specific device."""
    sensors = [
        PTLevelPercentageSensor(coordinator, entry, device_id),
        PTLevelVolumeSensor(coordinator, entry, device_id),
        PTLevelTemperatureSensor(coordinator, entry, device_id),
        PTLevelBatterySensor(coordinator, entry, device_id),
        PTLevelBatteryStatusSensor(coordinator, entry, device_id),
        PTLevelWiFiSensor(coordinator, entry, device_id),
        PTLevelFirmwareSensor(coordinator, entry, device_id),
        PTLevelIPSensor(coordinator, entry, device_id),          
        PTLevelMacSensor(coordinator, entry, device_id)         
    ]
    
    # Only load RAW AD sensors if connected locally
    if conn_type == CONNECTION_LOCAL:
        sensors.append(PTLevelRawSensor(coordinator, entry, device_id))
        sensors.append(PTLevelZeroSensor(coordinator, entry, device_id))
        
    return sensors

# --- VOLUME & PERCENTAGE SENSORS ---

class PTLevelPercentageSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_percentage"

    @property
    def native_value(self):
        data = self.target_data
        if 'cloud_percent' in data:
            return data['cloud_percent']
            
        current_ad = data.get('1')
        zero_ad = data.get('z')
        full_ad = self.entry.data.get(CONF_FULL_AD)
        
        if current_ad is None or zero_ad is None or not full_ad: return None
        if full_ad == zero_ad: return 0
            
        pct = ((float(current_ad) - float(zero_ad)) / (float(full_ad) - float(zero_ad))) * 100
        return round(max(0, min(100, pct)), 1)

class PTLevelVolumeSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Volume"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_volume"

    @property
    def native_unit_of_measurement(self):
        unit = self.entry.data.get(CONF_VOLUME_UNIT)
        if unit == UNIT_LITERS:
            return UnitOfVolume.LITERS
        return UnitOfVolume.GALLONS

    @property
    def native_value(self):
        tank_size = self.entry.data.get(CONF_TANK_SIZE)
        if not tank_size: return None # Fails gracefully if user left it blank
        
        data = self.target_data
        pct = None
        
        if 'cloud_percent' in data:
            pct = data['cloud_percent']
        else:
            current_ad = data.get('1')
            zero_ad = data.get('z')
            full_ad = self.entry.data.get(CONF_FULL_AD)
            if current_ad is not None and zero_ad is not None and full_ad:
                if full_ad != zero_ad:
                    pct = ((float(current_ad) - float(zero_ad)) / (float(full_ad) - float(zero_ad))) * 100
                    pct = max(0, min(100, pct))
        
        if pct is not None:
            return round((float(pct) / 100) * float(tank_size), 1)
        return None

class PTLevelTemperatureSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_temperature"

    @property
    def native_value(self):
        return self.target_data.get('temp')

# --- RAW DATA SENSORS (Only loaded on Local API) ---

class PTLevelRawSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Raw Value (1)"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:numeric-1-box-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_raw"

    @property
    def native_value(self):
        return self.target_data.get('1')

    @property
    def extra_state_attributes(self):
        return self.target_data

class PTLevelZeroSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Zero Value (z)"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:numeric-0-box-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_zero"

    @property
    def native_value(self):
        return self.target_data.get('z')

# --- DEVICE HEALTH SENSORS ---

class PTLevelBatterySensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Battery Voltage"
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_battery"

    @property
    def native_value(self):
        return self.target_data.get('bat')

class PTLevelBatteryStatusSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Battery Status"
    _attr_icon = "mdi:battery-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_battery_status"

    @property
    def native_value(self):
        return self.target_data.get('bat_status')

class PTLevelWiFiSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "WiFi Signal"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:wifi"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_wifi"

    @property
    def native_value(self):
        return self.target_data.get('wifi_pct')

class PTLevelFirmwareSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "Firmware Version"
    _attr_icon = "mdi:cellphone-arrow-down"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_firmware"

    @property
    def native_value(self):
        return self.target_data.get('fw')

class PTLevelIPSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "IP Address"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_ip"

    @property
    def native_value(self):
        return self.target_data.get('ip')

class PTLevelMacSensor(PTLevelBaseEntity, SensorEntity):
    _attr_name = "MAC Address"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:network"

    def __init__(self, coordinator, entry, device_id=None):
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{self.hardware_id}_mac"

    @property
    def native_value(self):
        raw_mac = self.target_data.get('mac', '')
        if len(raw_mac) == 12:
            return ":".join(raw_mac[i:i+2] for i in range(0, 12, 2)).upper()
        return raw_mac
