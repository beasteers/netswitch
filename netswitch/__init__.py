import ifcfg
from . import util
from .core import *
from .iw import *
from .wpasup import *


def get_ifaces(*ifaces):
    avail = ifcfg.interfaces()
    matches = util.matches(ifaces, avail)
    return {iface: avail[iface] for iface in matches}


def get_aps(*ifaces):
    '''List available APs for an interface.'''
    return {
        iface: WLan(iface).scan()
        for iface in get_ifaces(*(ifaces or ('wlan*',)))
    }


def get_ip(*ifaces, key='inet'):
    '''Get the ip of an interface.'''
    return get_ap_info(key, *ifaces)


def get_ap_info(key, *ifaces):
    info = {iface: d.get(key) for iface, d in get_ifaces(*ifaces).items()}
    return {k: v for k, v in info.items() if v is not Nonew}
