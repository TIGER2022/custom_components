
import logging
import math

from homeassistant.const import ATTR_ASSUMED_STATE
from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from homeassistant.components.cover import (
    ATTR_POSITION, SUPPORT_CLOSE, SUPPORT_OPEN,
    SUPPORT_SET_POSITION, SUPPORT_STOP, CoverDevice)

from .const import DOMAIN, DEVICE_DEFINE, CURTAIN_TIME

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """"""
    _LOGGER.warning(discovery_info)

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
    if component=='cover' and subtype=='relay':
        for i in range(slot_number):
            device=mp_relay_cover_simple(bus, zone_id, device_id, bytes([i]), type_name)
            devices.append(device)
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

    return True

class mp_relay_cover_simple(CoverDevice):

    def __init__(self, bus, zone_id, device_id, channel_id, type_name, curtain_time=CURTAIN_TIME, reverse=False):
        """Initialize"""
        self._bus = bus
        self._zone_id = zone_id
        self._device_id = device_id
        self._channel_id = channel_id
        self._curtain_time = CURTAIN_TIME
        self._name = type_name + '_' + bus.name + '_' + (zone_id+device_id+channel_id).hex()
        self._supported_features = (SUPPORT_OPEN|SUPPORT_CLOSE|SUPPORT_STOP)
        self._device_class = 'curtain'

        self._closed = None
        self._is_opening = False
        self._is_closing = False
        self._position = None

    def _control(self, direction, time):
        """1:right 0:left 3:stop"""
        direction_id = bytes([direction])
        time_id = bytes([math.ceil(time/5)])

        command = b'\xaa\x55\x06\xb3'
        command += (self._zone_id + self._device_id + self._channel_id + direction_id + time_id)
        self._bus.write(command)

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name
    
    @property
    def unique_id(self):
       """Return the unique_id of the light"""
       return self._name
    
    @property
    def should_poll(self):
        """No polling needed for a demo cover."""
        return False

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._position

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._closed

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return True

    def close_cover(self, **kwargs):
        """Close the cover."""
        #关动作
        run_time = self._curtain_time
        self._control(1,run_time)

    def open_cover(self, **kwargs):
        """Open the cover."""
        #开动作
        run_time = self._curtain_time
        self._control(0,run_time)

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        #关动作
        self._control(3,0)


class mp_relay_cover(CoverDevice):

    def __init__(self, bus, zone_id, device_id, channel_id, type_name, curtain_time=CURTAIN_TIME, reverse=False):
        """Initialize"""
        self._bus = bus
        self._zone_id = zone_id
        self._device_id = device_id
        self._channel_id = channel_id
        self._reverse = reverse # 未使用
        self._curtain_time = CURTAIN_TIME
        self._name = type_name + '_' + bus.name + '_' + (zone_id+device_id+channel_id).hex()
        self._supported_features = (SUPPORT_OPEN|SUPPORT_CLOSE|SUPPORT_SET_POSITION|SUPPORT_STOP)
        self._device_class = 'curtain'

        self._position = 50
        self._closed = False
        self._is_opening = False
        self._is_closing = False
        self._set_position = None
        self._unsub_listener_cover = None

    def _control(self, direction, time):
        """1:right 0:left 3:stop"""
        direction_id = bytes([direction])
        time_id = bytes([math.ceil(time/5)])

        command = b'\xaa\x55\x06\xb3'
        command += (self._zone_id + self._device_id + self._channel_id + direction_id + time_id)
        self._bus.write(command)

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name
    
    @property
    def unique_id(self):
       """Return the unique_id of the light"""
       return self._name
       
    @property
    def should_poll(self):
        """No polling needed for a demo cover."""
        return False

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._position

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._closed

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return True

#    @property
#    def device_state_attributes(self):
#        """Return the device state attributes."""
#        data = {}
#        data[ATTR_ASSUMED_STATE] = True
#        return data

    def close_cover(self, **kwargs):
        """Close the cover."""
        #关动作
        run_time = self._position*self._curtain_time/100
        self._control(0,run_time)
        self._stop_listen()
        self._is_closing = True
        self._listen_cover()
        self._requested_closing = True
        self.schedule_update_ha_state()

    def open_cover(self, **kwargs):
        """Open the cover."""
        #开动作
        run_time = (100-self._position)*self._curtain_time/100
        self._control(1,run_time)
        self._stop_listen()
        self._is_opening = True
        self._listen_cover()
        self._requested_closing = False
        self.schedule_update_ha_state()

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        self._set_position = round(position, -1)
        if self._position == position:
            return

        self._listen_cover()
        self._requested_closing = position < self._position
        run_time = abs(position-self._position)*self._curtain_time/100
        if self._requested_closing:
            #关动作
            self._control(0,run_time)
            pass
        else:
            #开动作
            self._control(1,run_time)
            pass


    def stop_cover(self, **kwargs):
        """Stop the cover."""
        #关动作
        self._control(3,0)
        self._stop_listen()

    def _stop_listen(self):
        self._set_position = None
        self._is_closing = False
        self._is_opening = False
        if self._unsub_listener_cover is not None:
            self._unsub_listener_cover()
            self._unsub_listener_cover = None
        
    def _listen_cover(self):
        """Listen for changes in cover."""
        if self._unsub_listener_cover is None:
            self._unsub_listener_cover = track_time_interval(
                self.hass,
                self._time_changed_cover,
                timedelta(seconds=math.ceil(0.1*self._curtain_time))
                )

    def _time_changed_cover(self, now):
        """Track time changes."""
        if self._requested_closing:
            self._position -= 10
        else:
            self._position += 10

        if self._position in (100, 0):
            self._stop_listen()
        if (self._set_position != None):
            if (self._requested_closing and self._position<=self._set_position) or \
               ((not self._requested_closing) and self._position>=self._set_position):
                self._stop_listen()

        self._closed = self.current_cover_position <= 0

        self.schedule_update_ha_state()
