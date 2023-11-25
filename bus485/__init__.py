"""Support for BUS 485"""

import logging
import threading
import time
from datetime import timedelta

import socket
import serial

import voluptuous as vol

from homeassistant.const import (
    ATTR_STATE, CONF_HOST, CONF_METHOD, CONF_NAME, CONF_PORT, CONF_TIMEOUT,
    CONF_TYPE, EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import track_time_interval, track_point_in_time
from . import discovery, listen
from .const import DOMAIN, WRITE_INTERVAL, LIGHT_QUERY_STATES_INTERVAL, BINARY_SENSOR_QUERY_STATES_INTERVAL, DISCOVERY_INTERVAL

_LOGGER = logging.getLogger(__name__)

ATTR_BUS = 'bus'
CONF_BUS = 'bus'
ATTR_COMMAND = 'command'

DEFAULT_TIMEOUT = 3

CONF_BAUDRATE = 'baudrate'
CONF_BYTESIZE = 'bytesize'
CONF_PARITY = 'parity'
CONF_STOPBITS = 'stopbits'
DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = 'N'
DEFAULT_STOPBITS = 1
DEFAULT_PORT = '/dev/ttyUSB0'

SERVICE_SEND = 'send'

BASE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    })

SERIAL_SCHEMA = BASE_SCHEMA.extend({
    vol.Required(CONF_TYPE): 'serial',
    vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
    vol.Optional(CONF_BYTESIZE, default=DEFAULT_BYTESIZE): vol.Any(5, 6, 7, 8),
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
    vol.Optional(CONF_PARITY, default=DEFAULT_PARITY): vol.Any('E', 'O', 'N'),
    vol.Optional(CONF_STOPBITS, default=DEFAULT_STOPBITS): vol.Any(1, 2),
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.socket_timeout,
    })

ETHERNET_SCHEMA = BASE_SCHEMA.extend({
    vol.Required(CONF_TYPE): 'tcp',
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.port,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.socket_timeout,
    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Any(SERIAL_SCHEMA, ETHERNET_SCHEMA)])
    }, extra=vol.ALLOW_EXTRA,)

SERVICE_SEND_SCHEMA = vol.Schema({
    vol.Required(ATTR_BUS): cv.string,
    vol.Required(ATTR_COMMAND): cv.string,
    })


def setup(hass, config):
    """Set up bus485 component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]['buses'] = hub_collect = {}
    hass.data[DOMAIN]['devices'] = {}

    for client_config in config[DOMAIN]:
        name = client_config[CONF_NAME]
        if client_config[CONF_TYPE] == 'serial':
            hub_collect[name] = Bus485_Serial(name=name,
                                              port=client_config[CONF_PORT],
                                              baudrate=client_config[CONF_BAUDRATE],
                                              stopbits=client_config[CONF_STOPBITS],
                                              bytesize=client_config[CONF_BYTESIZE],
                                              parity=client_config[CONF_PARITY],
                                              timeout=client_config[CONF_TIMEOUT])
        elif client_config[CONF_TYPE] == 'tcp':
            hub_collect[name] = Bus485_TCP(name=name,
                                           host=client_config[CONF_HOST],
                                           port=client_config[CONF_PORT],
                                           timeout=client_config[CONF_TIMEOUT])
        _LOGGER.debug("Setting up hub: %s", client_config)

    def stop_bus485(event):
        """Stop Bus485 service."""
        for client in hub_collect.values():
            client.terminate()

    def start_bus485(event):
        """Start Bus485 service."""
        for client in hub_collect.values():
            client.connect()
            client.start_reading_thread()

        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_bus485)

        # Register services for bus485
        hass.services.register(
            DOMAIN, SERVICE_SEND, send,
            schema=SERVICE_SEND_SCHEMA)

        listen.start(hass, config)

        def init_query(event_time=0):
            for bus in hass.data[DOMAIN]['buses'].values():
                discovery.query_zone(bus)

        def light_state_query(event_time=0):
            """Send query status command"""
            for (device_key, device_value) in hass.data[DOMAIN]['devices'].items():
                if device_value['component']=="light" and device_value['polling']:
                    bus_name = device_key[0]
                    zone_id = bytes([device_key[1]])
                    device_id = bytes([device_key[2]])
                    bus = hass.data[DOMAIN]['buses'].get(bus_name)
                    listen.query_light_status(bus, zone_id, device_id)
                    if device_value['subtype']=='relay_cu':
                        listen.query_light_currency(bus, zone_id, device_id)

        def binary_sensor_state_query(event_time=0):
            """Send query status command"""
            for (device_key, device_value) in hass.data[DOMAIN]['devices'].items():
                if device_value['component']=="binary_sensor" and device_value['polling']:
                    bus_name = device_key[0]
                    zone_id = bytes([device_key[1]])
                    device_id = bytes([device_key[2]])
                    bus = hass.data[DOMAIN]['buses'].get(bus_name)
                    listen.query_binary_sensor_status(bus, zone_id, device_id)

        track_time_interval(hass, init_query, timedelta(minutes=DISCOVERY_INTERVAL))
        track_time_interval(hass, light_state_query, timedelta(minutes=LIGHT_QUERY_STATES_INTERVAL))
        track_time_interval(hass, binary_sensor_state_query, timedelta(minutes=BINARY_SENSOR_QUERY_STATES_INTERVAL))

        init_query()
        track_point_in_time(hass, init_query, dt_util.utcnow()+timedelta(seconds=17))
        track_point_in_time(hass, init_query, dt_util.utcnow()+timedelta(seconds=17*2))
        track_point_in_time(hass, init_query, dt_util.utcnow()+timedelta(seconds=17*3))


    def send(service):
        """Send Command to Bus485."""
        command = service.data.get(ATTR_COMMAND)
        client_name = service.data.get(ATTR_BUS)
        hub_collect[client_name].write(bytes.fromhex(command))

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_bus485)

    return True


class Bus485Base:
    """Base class for Bus485."""

    def __init__(self, name):
        """Initialize the Modbus hub."""
        self._lock = threading.Lock()
        self._name = name
        self._thread = None
        self._terminated = False
        self._queues = []

    @property
    def name(self):
        """Return the name of this hub."""
        return self._name

    def start_reading_thread(self):
        self._thread = threading.Thread(target=self.always_read, name='ReadingThread')
        self._thread.start()

    def close(self):
        """Disconnect client."""
        raise NotImplementedError

    def terminate(self):
        """terminate thread and close the socket"""
        self._terminated = True
        self.close()

    def connect(self):
        """Connect client."""
        raise NotImplementedError

    def write(self, command):
        """Send the command."""
        raise NotImplementedError

    def always_read(self):
        """Read the bus and put into queues"""
        raise NotImplementedError

    def add_listen_queue(self, queue):
        self._queues.append(queue)


class Bus485_Serial(Bus485Base):
    """Thread safe wrapper class for serial to bus485"""

    def __init__(self, name, port, baudrate, stopbits, bytesize, parity, timeout):
        self._port = port
        self._baudrate = baudrate
        self._stopbits = stopbits
        self._bytesize = bytesize
        self._parity = parity
        self._timeout = timeout
        self._socket = None
        super().__init__(name=name)

    def always_read(self):
        while True:
            if self._terminated:
                return
            if self._socket:
                buffer = self._socket.read(1024)
                if len(buffer)>0:
                    for queue in self._queues:
                        queue.put(buffer)
            else:
                _LOGGER.warning("Reading thread break because socket is None")
                break

    def connect(self):
        if self._socket:
            return True
        try:
            self._socket = serial.Serial(port=self._port,
                                         timeout=self._timeout,
                                         bytesize=self._bytesize,
                                         stopbits=self._stopbits,
                                         baudrate=self._baudrate,
                                         parity=self._parity)
        except serial.SerialException as msg:
            _LOGGER.error("serial connect error: %s", msg)
            self.close()

        return self._socket is not None


    def close(self):
        if self._socket:
            self._socket.close()
        self._socket = None


    def write(self, command):
        with self._lock:
            if self._socket:
                try:
                    self._socket.write(bytes(command))
                    time.sleep(WRITE_INTERVAL)
                except serial.SerialTimeoutException as msg:
                    _LOGGER.error("serial write error: %s", msg)
            else:
                _LOGGER.error("writing to a closed serial port")



class Bus485_TCP(Bus485Base):
    """Thread safe wrapper class for tcp to bus485"""

    def __init__(self, name, host, port, timeout):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._socket = None
        super().__init__(name=name)

    def always_read(self):
        while True:
            if self._terminated:
                return
            if not self.connect():
                time.sleep(10)
            else:
                try:
                    buffer = self._socket.recv(1024)
                    if len(buffer)==0:
                        self.close()
                except socket.timeout as msg:
                    continue
                except socket.error as msg:
                    self.close()
                    continue
                else:
                    if len(buffer)>0:
                        for queue in self._queues:
                            queue.put(buffer)

    def connect(self):
        if self._socket:
            return True
        try:
            self._socket = socket.create_connection(
                (self._host, self._port),
                timeout=self._timeout
                )
        except socket.error as msg:
            _LOGGER.error('Connection to (%s, %s) failed: %s',
                          self._host, self._port, msg
                          )
            self.close()
        return self._socket is not None


    def close(self):
        if self._socket:
            self._socket.close()
        self._socket = None


    def write(self, command):
        with self._lock:
            if not self.connect():
                return None
            try:
                self._socket.send(bytes(command))
                time.sleep(WRITE_INTERVAL)
            except (socket.error, socket.timeout) as msg:
                _LOGGER.error("TCP write error: %s", msg)
                self.close()
