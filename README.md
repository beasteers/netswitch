# Netswitch

Network switching. Make sure you're connecting with the priority that you want.

Works on Linux (relies on wpa_supplicant)


## Install

```bash
pip install netswitch
```

## Usage

### Network Switching

```python
import time
import netswitch

netswitch.sync_aps('path/to/aps')

switch = netswitch.NetSwitch([
    {'interface': 'wlan*', 'ssids': 'lifeline'},
    'eth*',  # equivalent to {'interface': 'eth*'}
    'ppp*',
    {'interface': 'wlan*'},  # implied - 'ssids': '*'
])

while True:
    time.sleep(10)
    connected = switch.check()
# or equivalently
switch.run(interval=10)
```

For example, assume your setup is:
 - ifaces: wlan0 (built-in Pi 4 wifi), wlan1 (usb wifi dongle), ppp0 (cellular)
 - trusted ssids: nyu, nyu-legacy

Procedure - at any point in these steps, if we connect, we're finished:
 - check wlan1 for s0nycL1f3l1ne, if yes, connect
 - check wlan0 for s0nycL1f3l1ne, if yes, connect
 - check for eth0 and internet connected thru interface
 - check for ppp0 and internet connected thru interface
    - should we control wvdial or whatevs in this ???
 - check wlan1 for [nyu, nyu-legacy], if yes, connect
 - check wlan0 for [nyu, nyu-legacy], if yes, connect
 - check if internet is already connected thru any interface



## TODO
 - tests - .travis.yml
 - eth0 connection, ppp0 connection
 - /etc/network/interfaces setup? / instructions?
 - restart interface if it's missing / not connected? maybe only 0, or if it showed up once?
 - time since connected - restart after a certain amount of time.
