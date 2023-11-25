import logging
import threading
from queue import Queue

from . import discovery
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def query_light_status(bus, zone_id, device_id):
    command = b'\xaa\x55\x03\xc3'
    command += (zone_id + device_id)
    bus.write(command)

def query_binary_sensor_status(bus, zone_id, device_id):
    command = b'\xaa\x55\x03\xcd'
    command += (zone_id + device_id)
    bus.write(command)

def query_light_currency(bus, zone_id, device_id):
    command = b'\xaa\x55\x03\xb1'
    command += (zone_id + device_id)
    bus.write(command)

def found_light_status(info, length, bus, hass, hass_config):
    zone_id = info[0:1]
    device_id = info[1:2]
    device_key = (bus.name, zone_id[0], device_id[0])
    device_info = hass.data[DOMAIN]['devices'].get(device_key)
    if device_info==None:
        return
    if device_info['component'] in ('light') and device_info['subtype'] in ('relay', 'relay_cu'):
        if device_info['number']+2!=length:
            _LOGGER.warning("message length is not match with the device:{}:{}:{}:{}".format(bus.name, zone_id, device_id, info))
            return
        for i in range(device_info['number']):
            device_info['entities'][i]._is_on = (info[2+i:2+i+1]==b'\x01')
            device_info['entities'][i].schedule_update_ha_state()
    elif device_info['component'] in ('light') and device_info['subtype'] in ('dimmer'):
        if device_info['number']+2!=length:
            _LOGGER.warning("message length is not match with the device:{}:{}:{}:{}".format(bus.name, zone_id, device_id, info))
            return
        for i in range(device_info['number']):
            device_info['entities'][i]._brightness = min(255,info[2+i]/100*255)
            device_info['entities'][i]._is_on = (info[2+i]!=0)
            device_info['entities'][i].schedule_update_ha_state()

def found_binary_sensor_status(info, length, bus, hass, hass_config):
    zone_id = info[0:1]
    device_id = info[1:2]
    device_key = (bus.name, zone_id[0], device_id[0])
    device_info = hass.data[DOMAIN]['devices'].get(device_key)
    if device_info==None:
        return
    if device_info['component'] in ('binary_sensor') and device_info['subtype'] in ('board'):
        if length!=3:
            _LOGGER.warning("message length is not match with the device:{}:{}:{}:{}".format(bus.name, zone_id, device_id, info))
            return
        status = info[2]
        for i in range(device_info['number']):
            device_info['entities'][i]._is_on = (status&0x01==0x01)
            device_info['entities'][i].schedule_update_ha_state()
            status = status>>1

def found_light_currency(info, length, bus, hass, hass_config):
    zone_id = info[0:1]
    device_id = info[1:2]
    device_key = (bus.name, zone_id[0], device_id[0])
    device_info = hass.data[DOMAIN]['devices'].get(device_key)
    if device_info==None:
        return
    if device_info['component'] in ('light') and device_info['subtype'] in ('relay_cu'):
        if (device_info['number']*2)+2!=length:
            _LOGGER.warning("message length is not match with the device:{}:{}:{}:{}".format(bus.name, zone_id, device_id, info))
            return
        for i in range(device_info['number']):
            cur = (info[2+i]*256 + info[2+i+1])*0.05
            device_info['entities'][i]._currency = cur
            device_info['entities'][i].schedule_update_ha_state()

def found_update_command(info, length, bus, hass, hass_config):
    zone_id = info[0:1]
    device_id = info[1:2]
    bus_name = bus.name

    device_info = hass.data[DOMAIN]['devices'].get((bus_name, zone_id[0], device_id[0]))
    if device_info and device_info['polling']:
        query_light_status(bus, zone_id, device_id)


message_func = {b'\x1c':discovery.found_device_id,
                b'\x2c':discovery.found_device_type,
                b'\x3c':found_light_status,
                b'\x1b':found_light_currency,
                b'\xdc':found_binary_sensor_status,
                b'\xb3':found_update_command,
                b'\xa7':found_update_command,
                b'\xd3':found_update_command,
                }

def listen(bus, hass, hass_config):
    _queue = Queue()
    bus.add_listen_queue(_queue)
    while True:
        info = _queue.get()
        _LOGGER.warning("get message:{}".format(info.hex()))

        if info[:2]!= b'\xaa\x55' or len(info)<4:
            next = info.find(b'\xaa\x55')
            if next==-1:
                _LOGGER.warning("get unknown message:{}".format(info.hex()))
            else:
                _LOGGER.warning("get malformed message:{}".format(info.hex()))
                _queue.put(info[next:])
            continue

        message_len = info[2]
        if message_len+3 > len(info):
            _LOGGER.warning("get error length message:{}".format(info.hex()))
            continue
        elif message_len+3 < len(info):
            _queue.put(info[message_len+3:])
            info = info[:message_len+3]

        func = message_func.get(info[3:4])
        if func:
            func(info[4:], message_len-1, bus, hass, hass_config)

def start(hass, hass_config) -> bool:

    for bus in hass.data[DOMAIN]['buses'].values():
        _thread = threading.Thread(target=listen,
                                   kwargs={'bus':bus, 'hass':hass, 'hass_config':hass_config},
                                   name=bus.name+"_listen")
        _thread.start()

    return True
