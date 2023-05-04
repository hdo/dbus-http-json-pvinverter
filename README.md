# dbus-http-json-pvinverter
Integrate HTTP JSON inverter data into Victron Energies Venus OS

## Purpose
With the scripts in this repo it should be easy possible to install, uninstall, restart a service that connects HTTP JSON inverter data to the VenusOS and GX devices from Victron.

## My Setup

I'mm running a HTTP server for home automation purposes. There is a script polling data from my SMA PV inverter via HTTP JSON.

## Inspiration

Base on the following works - many thanks for sharing the knowledge:

- https://github.com/vikt0rm/dbus-shelly-1pm-pvinverter
- https://github.com/victronenergy/venus/wiki/dbus#pv-inverters

## How it works

Polls data from HTTP JSON server to update inverter data.

## JSON Format / Example

This is an example JSON payload:

```
{
   "total":54446224,
   "today":2728,
   "spotacpower":2087,
   "spotacpower1":699,
   "spotacpower2":694,
   "spotacpower3":694,
   "spotacvoltage1":235.13,
   "spotacvoltage2":235.29,
   "spotacvoltage3":235.95,
   "spotacamperage1":2.973,
   "spotacamperage2":2.952,
   "spotacamperage3":2.944,
   "spotdcpower1":1739,
   "spotdcpower2":341,
   "spotdcvoltage1":347.45,
   "spotdcvoltage2":424.75,
   "spotdcamperage1":5.009,
   "spotdcamperage2":0.806,
   "msg_count":12028
}
```




