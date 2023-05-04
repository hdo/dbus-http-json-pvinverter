#!/usr/bin/env python

####################################
# Title: dbus-http-json-pvinverter
# Author: Huy Do (huydo1@gmail.com)
####################################


import platform
import logging
import sys
import os
import sys
if sys.version_info.major == 2:
    import gobject
else:
    from gi.repository import GLib as gobject
import sys
import time
import requests # for http GET
import configparser  # for config/ini file
import json

# our own packages from victron
sys.path.insert(
    1,
    os.path.join(
        os.path.dirname(__file__),
        "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python",
    ),
)
from vedbus import VeDbusService

class DbusJSONInverterService:

    def __init__(
        self,
        config,
        servicename,
        paths,
        productname="HTTP JSON Inverter",
        connection="HTTP JSON Inverter service",
    ):
        self.config = config
        deviceinstance = int(config['DEFAULT']['DeviceInstance'])
        customname = config['DEFAULT']['CustomName']
        self.inverter_url = "http://%s:%s" % (config['HTTP']['Host'], config['HTTP']['Port'])
        
        self._dbusservice = VeDbusService(
            "{}.http_{:02d}".format(servicename, deviceinstance)
        )
        self._paths = paths

        logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path("/Mgmt/ProcessName", __file__)
        self._dbusservice.add_path(
            "/Mgmt/ProcessVersion",
            "Unkown version, and running on Python " + platform.python_version(),
        )
        self._dbusservice.add_path("/Mgmt/Connection", connection)

        # Create the mandatory objects
        self._dbusservice.add_path("/DeviceInstance", deviceinstance)
        # self._dbusservice.add_path('/ProductId', 16) # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self._dbusservice.add_path(
            "/ProductId", 0xFFFF
        )  # id assigned by Victron Support from SDM630v2.py
        self._dbusservice.add_path("/ProductName", productname)
        self._dbusservice.add_path("/CustomName", customname)
        self._dbusservice.add_path("/Connected", 1)

        self._dbusservice.add_path("/Latency", None)
        self._dbusservice.add_path("/FirmwareVersion", 1.0)
        self._dbusservice.add_path("/HardwareVersion", 1)
        self._dbusservice.add_path("/Position", 0)  # normaly only needed for pvinverter
        self._dbusservice.add_path("/Serial", config['DEFAULT']['DeviceSerial'])
        self._dbusservice.add_path("/UpdateIndex", 0)
        self._dbusservice.add_path(
            "/StatusCode", 0
        )  # Dummy path so VRM detects us as a PV-inverter.

        # add path values to dbus
        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path,
                settings["initial"],
                gettextcallback=settings["textformat"],
                writeable=True,
                onchangecallback=self._handlechangedvalue,
            )

        # last update
        self._lastUpdate = 0

        # add _update function 'timer'
        gobject.timeout_add(2000, self._update)  # pause 250ms before the next request

        # add _signOfLife 'timer' to get feedback in log every 5minutes
        gobject.timeout_add(self._getSignOfLifeInterval() * 60 * 1000, self._signOfLife)


    def _getSignOfLifeInterval(self):
        value = self.config["DEFAULT"]["SignOfLifeLog"]
        if not value:
            value = 0
        return int(value)

    def _signOfLife(self):
        logging.info("--- Start: sign of life ---")
        logging.info("Last _update() call: %s" % (self._lastUpdate))
        logging.info("Last '/Ac/Power': %s" % (self._dbusservice["/Ac/Power"]))
        logging.info("--- End: sign of life ---")
        return True
        
    def _getHTTPJsonData(self):
        URL = self.inverter_url
        meter_r = requests.get(url = URL, timeout=15)
    
        # check for response
        if not meter_r:
            raise ConnectionError("No response from HTTP - %s" % (URL))
        
        meter_data = meter_r.json()     
        
        # check for Json
        if not meter_data:
            raise ValueError("Converting response to JSON failed")        
        return meter_data        
        
        
    def _update(self):
        try:
            # get data from HTTP JSON inverter 
            meter_data = self._getHTTPJsonData()

            #config = self._getConfig()
            #str(config["DEFAULT"]["Phase"])

            #pvinverter_phase = str(config["DEFAULT"]["Phase"])

            if meter_data:           
                # send data to DBus
            
                self._dbusservice["/Ac/L1/Voltage"] = meter_data['spotacvoltage1']
                self._dbusservice["/Ac/L1/Current"] = meter_data['spotacamperage1']
                self._dbusservice["/Ac/L1/Power"] = meter_data['spotacpower1']
                #self._dbusservice["/Ac/L1/Energy/Forward"] = 

                self._dbusservice["/Ac/L2/Voltage"] = meter_data['spotacvoltage2']
                self._dbusservice["/Ac/L2/Current"] = meter_data['spotacamperage2']
                self._dbusservice["/Ac/L2/Power"] = meter_data['spotacpower2']
                #self._dbusservice["/Ac/L2/Energy/Forward"] = 

                self._dbusservice["/Ac/L3/Voltage"] = meter_data['spotacvoltage3']
                self._dbusservice["/Ac/L3/Current"] = meter_data['spotacamperage3']
                self._dbusservice["/Ac/L3/Power"] = meter_data['spotacpower3']
                #self._dbusservice["/Ac/L3/Energy/Forward"] = 

                self._dbusservice["/Ac/Energy/Forward"] = meter_data['total'] / 1000
                self._dbusservice["/Ac/Power"] = meter_data['spotacpower']
                            
                # increment UpdateIndex - to show that new data is available
                index = self._dbusservice["/UpdateIndex"] + 1  # increment index
                if index > 255:  # maximum value of the index
                    index = 0  # overflow from 255 to 0
                self._dbusservice["/UpdateIndex"] = index

                # update lastupdate vars
                self._lastUpdate = time.time()
        except Exception as e:
            logging.critical("Error at %s", "_update", exc_info=e)

        # return true, otherwise add_timeout will be removed from GObject - see docs http://library.isr.ist.utl.pt/docs/pygtk2reference/gobject-functions.html#function-gobject--timeout-add
        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change



# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    logging.debug(msg.topic+" "+str(msg.payload))
    try:
        if msg.topic.endswith("inverter") and len(msg.payload) > 0:
            data = json.loads(msg.payload)
            #logging.debug(data)
            data_queue.put(data)       
            #logging.debug("Queue size: %d" % data_queue.qsize())
            # prevent large queues
            if data_queue.qsize() > 4:
                data_queue.get_nowait()            
        else:
            logging.warning("empty data")
    except Exception as ex:
        logging.error("JSON parse error! %s" % ex)



def main():
    # configure logging
    logging.basicConfig(
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[
            logging.FileHandler(
                "%s/current.log" % (os.path.dirname(os.path.realpath(__file__)))
            ),
            logging.StreamHandler(),
        ],
    )

    try:
        logging.info("Start")

        config_file = "%s/config.ini" % (os.path.dirname(os.path.realpath(__file__)))
        logging.info("reading config file %s ... " % config_file)
        config = configparser.ConfigParser()
        config.read(config_file)
       
        from dbus.mainloop.glib import DBusGMainLoop

        # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
        DBusGMainLoop(set_as_default=True)

        # formatting
        _kwh = lambda p, v: (str(round(v, 2)) + "KWh")
        _a = lambda p, v: (str(round(v, 1)) + "A")
        _w = lambda p, v: (str(round(v, 1)) + "W")
        _v = lambda p, v: (str(round(v, 1)) + "V")

        # start our main-service
        pvac_output = DbusJSONInverterService(
            config,
            servicename="com.victronenergy.pvinverter",
            paths={
                "/Ac/Energy/Forward": {
                    "initial": None,
                    "textformat": _kwh,
                },  # energy produced by pv inverter
                "/Ac/Power": {"initial": 0, "textformat": _w},
                "/Ac/Current": {"initial": 0, "textformat": _a},
                "/Ac/Voltage": {"initial": 0, "textformat": _v},
                "/Ac/L1/Voltage": {"initial": 0, "textformat": _v},
                "/Ac/L2/Voltage": {"initial": 0, "textformat": _v},
                "/Ac/L3/Voltage": {"initial": 0, "textformat": _v},
                "/Ac/L1/Current": {"initial": 0, "textformat": _a},
                "/Ac/L2/Current": {"initial": 0, "textformat": _a},
                "/Ac/L3/Current": {"initial": 0, "textformat": _a},
                "/Ac/L1/Power": {"initial": 0, "textformat": _w},
                "/Ac/L2/Power": {"initial": 0, "textformat": _w},
                "/Ac/L3/Power": {"initial": 0, "textformat": _w},
            },
        )

        logging.info(
            "Connected to dbus, and switching over to gobject.MainLoop() (= event based)"
        )
        mainloop = gobject.MainLoop()
        mainloop.run()
    except Exception as e:
        logging.critical("Error at %s", "main", exc_info=e)


if __name__ == "__main__":
    main()
