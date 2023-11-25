"""Support for RS485 binary_sensor."""
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice
from .const import DOMAIN, DEVICE_DEFINE
from . import listen

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """"""
    bus_name = discovery_info.get('bus_name')
    zone_id = bytes([discovery_info.get('zone_id')])
    device_id = bytes([discovery_info.get('device_id')])
    device_type = bytes([discovery_info.get('device_type')])
    
    slot_number = DEVICE_DEFINE[device_type].get('number')
    component = DEVICE_DEFINE[device_type].get('component')
    subtype = DEVICE_DEFINE[device_type].get('subtype')
    polling = DEVICE_DEFINE[device_type].get('polling')
    type_name = DEVICE_DEFINE[device_type].get('name')
    bus = hass.data[DOMAIN]['buses'].get(bus_name)

    devices = []
    if component=='binary_sensor' and subtype=='board':
        for i in range(slot_number):
            binary_sensor=mp_binary_sensor(bus, zone_id, device_id, bytes([i]), type_name)
            devices.append(binary_sensor)
    else:
        _LOGGER.warning("Add device with unknown component and subtype")
        return False

    add_entities(devices)
    device_key = (bus_name, zone_id[0], device_id[0])
    hass.data[DOMAIN]['devices'][device_key] = {}
    hass.data[DOMAIN]['devices'][device_key]['type'] = device_type[0]
    hass.data[DOMAIN]['devices'][device_key]['number'] = slot_number
    hass.data[DOMAIN]['devices'][device_key]['polling'] = polling
    hass.data[DOMAIN]['devices'][device_key]['component'] = component
    hass.data[DOMAIN]['devices'][device_key]['subtype'] = subtype
    hass.data[DOMAIN]['devices'][device_key]['entities'] = devices

    listen.query_binary_sensor_status(bus, zone_id, device_id)

    return True


class mp_binary_sensor(BinarySensorDevice):
    """Representation of a simple binary sensor."""

    def __init__(self, bus, zone_id, device_id, channel_id, type_name):
        """Initialize"""
        self._bus = bus
        self._zone_id = zone_id
        self._device_id = device_id
        self._channel_id = channel_id
        self._name = type_name + '_' + bus.name + '_' + (zone_id+device_id+channel_id).hex()
        self._is_on = False
        self._sensor_type = None

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._is_on
        
    @property    
    def unique_id(self):
        """Return the unique_id of the binary_sensor"""
        return self._name
        
    @property
    def name(self):
        """Return the name of the binary_sensor."""
        return self._name

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._sensor_type
