import ifcfg
import netswitch



import fire
fire.Fire({
    'ip': netswitch.get_ip,
    'aps': netswitch.get_aps,
    'iface': netswitch.get_ifaces,
    'connected': netswitch.internet_connected,
    'restart': netswitch.restart_iface,
    'wpa': netswitch.Wpa,
})
