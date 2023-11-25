"""Support for RS485 lights."""
import logging
import math

from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS)
from .const import DOMAIN, DEVICE_DEFINE
from . import listen

ATTR_CURRENCY = 'currency'

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
    if component=='light' and subtype=='relay':
        for i in range(slot_number):
            light=mp_relay_light(bus, zone_id, device_id, bytes([i]), type_name)
            devices.append(light)
    elif component=='light' and subtype=='relay_cu':
        for i in range(slot_number):
            light=mp_relay_light_with_currency(bus, zone_id, device_id, bytes([i]), type_name)
            devices.append(light)
    elif component=='light' and subtype=='dimmer':
        for i in range(slot_number):
            light=mp_dimmer_light(bus, zone_id, device_id, bytes([i]), type_name)
            devices.append(light)
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

    listen.query_light_status(bus, zone_id, device_id)

    return True


class mp_relay_light(Light):
    """Representation of a simple one-color Relay Light."""

    def __init__(self, bus, zone_id, device_id, channel_id, type_name):
        """Initialize"""
        self._bus = bus
        self._zone_id = zone_id
        self._device_id = device_id
        self._channel_id = channel_id
        self._name = type_name + '_' + bus.name + '_' + (zone_id+device_id+channel_id).hex()
        self._is_on = False

    def _control(self, turn_on, transition=0):
        if turn_on:
            turn_on_id = b'\x01'
        else:
            turn_on_id = b'\x00'
        transition_id = bytes([transition])

        command = b'\xaa\x55\x06\xb3'
        command += (self._zone_id + self._device_id + self._channel_id + turn_on_id + transition_id)
        self._bus.write(command)

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._is_on
        
    @property    
    def unique_id(self):
        """Return the unique_id of the light"""
        return self._name
        
    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def supported_features(self):
        """Flag supported features."""
        return 0

    def turn_on(self, **kwargs):
        """Turn on a light."""
        self._control(True)
        self._is_on = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off a light."""
        self._control(False)
        self._is_on = False
        self.schedule_update_ha_state()

class mp_relay_light_with_currency(Light):
    """Representation of a simple one-color Relay Light with attribute currency."""

    def __init__(self, bus, zone_id, device_id, channel_id, type_name):
        """Initialize"""
        self._bus = bus
        self._zone_id = zone_id
        self._device_id = device_id
        self._channel_id = channel_id
        self._name = type_name + '_' + bus.name + '_' + (zone_id+device_id+channel_id).hex()
        self._is_on = False
        self._currency = 0

    def _control(self, turn_on, transition=0):
        if turn_on:
            turn_on_id = b'\x01'
        else:
            turn_on_id = b'\x00'
        transition_id = bytes([transition])

        command = b'\xaa\x55\x06\xb3'
        command += (self._zone_id + self._device_id + self._channel_id + turn_on_id + transition_id)
        self._bus.write(command)

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._is_on

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name
        
    @property    
    def unique_id(self):
        """Return the unique_id of the light"""
        return self._name

    @property
    def supported_features(self):
        """Flag supported features."""
        return 0

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {ATTR_CURRENCY: self._currency,
                }

    def turn_on(self, **kwargs):
        """Turn on a light."""
        self._control(True)
        self._is_on = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off a light."""
        self._control(False)
        self._is_on = False
        self.schedule_update_ha_state()


class mp_dimmer_light(Light):
    """Representation of a one-color dimming controlled light."""

    def __init__(self, bus, zone_id, device_id, channel_id, type_name):
        """Initialize"""
        self._bus = bus
        self._zone_id = zone_id
        self._device_id = device_id
        self._channel_id = channel_id
        self._name = type_name + '_' + bus.name + '_' + (zone_id+device_id+channel_id).hex()
        self._brightness = 255
        self._is_on = False

    def _control(self, brightness, transition=0):
        brightness_id = bytes([brightness])
        transition_id = bytes([transition])

        command = b'\xaa\x55\x06\xb3'
        command += (self._zone_id + self._device_id + self._channel_id + brightness_id + transition_id)
        self._bus.write(command)

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._is_on

    @property
    def brightness(self):
        """Return the brightness property."""
        return self._brightness

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name
        
    @property    
    def unique_id(self):
        """Return the unique_id of the light"""
        return self._name

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def should_poll(self):
        """No polling needed for a demo switch."""
        return False

    def turn_on(self, **kwargs):
        """Turn on a light."""
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            if self._brightness == 0:
                self._brightness = 255
        self._control(math.ceil(self._brightness/255*100))
        self._is_on = (self._brightness != 0)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off a light."""
        self._control(0)
        self._is_on = False
        self.schedule_update_ha_state()
