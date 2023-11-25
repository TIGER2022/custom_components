import logging

from homeassistant.helpers.discovery import load_platform

from .const import DOMAIN, DEVICE_DEFINE

_LOGGER = logging.getLogger(__name__)


def query_zone(bus):
    command = b'\xaa\x55\x01\xc1'
    bus.write(command)

def query_device(bus, zone_id, device_id):
    command = b'\xaa\x55\x03\xc2'+ zone_id + device_id
    bus.write(command)

"""
def query_binary_sensor_type(bus, zone_id, device_id):
    command = b'\xaa\x55\x03\xce'+ zone_id + device_id
    bus.write(command)
"""

def found_device_id(info, length, bus, hass, hass_config):
    device_id = info[0:1]
    zone_id = info[1:2]
    active = info[2:3]

    #if(active!=b'\x01'):
    #    _LOGGER.warning("Found unactive device:{}:{}:{}".format(bus.name, zone_id, device_id))
    #    return

    device_key = ( bus.name, zone_id[0], device_id[0] )
    if device_key not in hass.data[DOMAIN]['devices'].keys():
        query_device(bus, zone_id, device_id)

def found_device_type(info, length, bus, hass, hass_config):
    device_id = info[0:1]
    device_type = info[1:2]
    zone_id = info[2:3]
    active = info[3:4]

    #if(active!=b'\x01'):
    #    _LOGGER.warning("Found unactive device:{}:{}:{}:{}".format(bus.name, zone_id, device_id, device_type))
    #    return

    type_para = DEVICE_DEFINE.get(device_type)
    if not type_para:
        _LOGGER.warning("Found unknown device type:{}:{}:{}:{}".format(bus.name, zone_id, device_id, device_type))
        return

    device_key = ( bus.name, zone_id[0], device_id[0])
    device_info = {'bus_name': bus.name,
                   'zone_id': zone_id[0],
                   'device_id': device_id[0],
                   'device_type': device_type[0]
                   }
    if device_key not in hass.data[DOMAIN]['devices'].keys():
        component = type_para["component"]
        load_platform( hass, component, DOMAIN, device_info, hass_config)
        return
    elif hass.data[DOMAIN]['devices'][device_key]["type"] != device_type[0]:
        _LOGGER.warning("Device type changed:{}:{}:{}:{}".format(bus.name, zone_id, device_id, device_type))
        return
