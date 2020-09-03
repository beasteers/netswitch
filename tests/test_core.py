import os
import netswitch


# def test_utils():
#


def test_top_level_utils():
    ifaces = netswitch.get_ifaces()
    assert isinstance(ifaces, dict)
    assert all(isinstance(d, dict) for d in ifaces.values())

    ips = netswitch.get_ip()
    assert isinstance(ips, dict)
    assert all(isinstance(d, str) for d in ips.values())
    assert ips['lo0'] == '127.0.0.1'


def test_core():
    switch = netswitch.NetSwitch([
        {'interface': 'wlan*'},
        'ppp0', 'eth0', 'wlan*'
    ])

    for _ in range(5):
        switch.check()


def test_cell():
    pass


# def test_iw():
#     wlan = netswitch.WLan()
#     aps = wlan.scan()
#     assert wlan.ap_available(aps[0].ssid)
#     assert not wlan.ap_available('!!!!!!!!!!!!!!~~~~~~~~~~~~~~~~~~~~~'*87)  # pretty safe
#
#     best_ap, all_aps = wlan.select_best_ssid()
#     print(best_ap, all_aps)


def test_wpasup(tmp_path):
    netswitch.Wpa.ap_path = str(tmp_path / 'wpa/aps')
    netswitch.Wpa.WPA_PATH = str(tmp_path / 'wpa/wpa_supplicant.conf')

    creds = [
        ('asdf', 'asdf'),
        ('1111', '1111'),
        ('2222', '2222'),
        ('qqqq', 'qqqq'),
    ]

    # test generating

    OTHER_PATH = str(tmp_path / 'wpa/repo_aps')
    for ssid, password in creds:
        assert not os.path.isfile(
            os.path.join(netswitch.Wpa.ap_path, ssid + ".conf"))
        assert not os.path.isfile(
            os.path.join(OTHER_PATH, ssid + ".conf"))

        netswitch.generate_wpa_config(ssid, password, ap_path=OTHER_PATH)
        assert os.path.isfile(
            os.path.join(OTHER_PATH, ssid + ".conf"))

    # test syncing

    netswitch.sync_aps(OTHER_PATH)
    for ssid, _ in creds:
        assert os.path.isfile(
            os.path.join(netswitch.Wpa.ap_path, ssid + ".conf"))

    # test connect

    wpsup = netswitch.Wpa(creds[0][0])
    assert not os.path.isfile(netswitch.Wpa.WPA_PATH)
    wpsup.connect(restart=False)
    assert os.path.isfile(netswitch.Wpa.WPA_PATH)

    # test select current, connect other, backup

    current = netswitch.Wpa()
    assert current.path == netswitch.Wpa.WPA_PATH
    assert (current.ssid, current.password) == creds[0]
    os.remove(wpsup.path)
    assert not os.path.isfile(wpsup.path)

    wpsup2 = netswitch.Wpa(creds[1][0])
    assert wpsup.path != wpsup2.path
    assert wpsup.ssid != wpsup2.ssid
    wpsup2.connect(restart=False)
    assert os.path.isfile(wpsup.path)
    assert netswitch.Wpa().ssid == wpsup2.ssid
