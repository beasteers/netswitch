# Netswitch

Network switching. Make sure you're connecting with the priority that you want.

Works on Linux (relies on wpa_supplicant)


## Install

```bash
pip install netswitch
```

### Docker
Or you can use Docker instead:
```bash
# copy your wpa supplicant configs
cp -r ./aps /etc/wpa_supplicant/aps

docker run -d --privileged --network="host" \
    -v /etc/wpa_supplicant:/etc/wpa_supplicant \
    -e LIFELINE_SSID=mylifeline-2G \
    --name netswitch beasteers/netswitch
```
where `./aps` is filled with a single wpa_supplicant network configuration and where the filename matches the SSID that's inside the file:
```
# all of the networks you want to be able to connect to
./aps/
    networkA.conf
    myspectrum-2G.conf
    myspectrum-5G.conf
    ...
```

You can also use `-v ./aps:/etc/wpa_supplicant/aps` instead of copying if you want the aps to be editable from their current location.

**IMPORTANT**: if you don't give it any aps to manage, it won't do anything.

## Usage

### Network Switching

```python
import time
import netswitch

# tell netswitch where to get its AP list. see explanation below
netswitch.set_ap_path('path/to/aps')


# create a new wpa supplicant file
netswitch.generate_wpa_config('my-network-2G', 'wifipassword')

# create your network switching rules
witch = netswitch.NetSwitch([
    {'interface': 'wlan*', 'ssids': 'lifeline'},
    'eth*',  # equivalent to {'interface': 'eth*'}
    'ppp*',
    {'interface': 'wlan*'},  # implied - 'ssids': '*'
])

# periodically check network
while True:
    time.sleep(10)
    connected = witch.check()
# or equivalently
witch.run(interval=10)
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

#### Modifications to WPA Supplicant

For the collection of available APs and credentials that you can connect to, typically they are stored in a single `/etc/wpa_supplicant/wpa_supplicant.conf` file and the wpa service will select the best one based on the priority specified. But this has issues and doesn't switch when one network is stronger than the other.

So, what's different:
 - instead of one big file, we break it up into one file per AP (where the filename is the same as the AP ssid)
 - periodically, the above check will be run and we will check to see what networks are in range, which ones are trusted, and which have the highest quality. If a different AP consistently higher quality (3/5 pings atm), then we will switch to the new AP.

So calling `netswitch.sync_aps('path/to/aps')` tells `netswitch` that each of your AP credentials are stored in individual files under `'path/to/aps'`.

You can also call `netswitch.sync_aps('path/to/aps')` which will sync that directory with `/etc/wpa_supplicant/aps/` and will operate out of there so that nothing will be touched in the original directory.

### CLI

```bash
# run the wifi switcher with a lifeline ssid to look out for
python -m netswitch run --lifeline mylifelinenetwork-2G

# get ip addresses for available interfaces
python -m netswitch ip
python -m netswitch ip 'wlan*' 'eth*'  # certain interfaces

# get available aps
python -m netswitch aps
python -m netswitch aps en0  # for mac

# get available interfaces
python -m netswitch iface
python -m netswitch iface '*tun*' 'eth*'

# restart interface
python -m netswitch restart wlan0

# list current wpa supplicant info
python -m netswitch wpa info
```

### WPA Supplicant
```python
import netswitch

# get current wpa supplicant file
wpa = netswitch.Wpa()

# get

```

### Cellular
```python
import netswitch.cell

assert isinstance(netswitch.cell.signal_strength(), float)

with netswitch.cell.Cell('/dev/ttyUSB2') as cell:
    # read from stdind
    cell.chat()
```


## TODO
 - tests - .travis.yml
 - eth0 connection, ppp0 connection
 - /etc/network/interfaces setup? / instructions?
 - restart interface if it's missing / not connected? maybe only 0, or if it showed up once?
 - time since connected - restart after a certain amount of time.
 - `/etc/network/interfaces` ????
