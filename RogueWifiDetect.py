#!/usr/bin/python

# This script shows how to connect to a WPA protected WiFi network
# by communicating through D-Bus to NetworkManager 0.9.
#
# Reference URLs:
# http://projects.gnome.org/NetworkManager/developers/
# http://projects.gnome.org/NetworkManager/developers/settings-spec-08.html
# 
# DBUS API: http://dbus.freedesktop.org/doc/dbus-python/api/

import dbus
import time
from random import *

NM_BUS_NAME                    = 'org.freedesktop.NetworkManager'
NM_PATH                        = '/org/freedesktop/NetworkManager'
NM_DBUS_INTERFACE              = 'org.freedesktop.NetworkManager'
NM_DBUS_PROPS                  = 'org.freedesktop.DBus.Properties'

pseudo_random_ssids = []
random_ssids        = []
SSID_POOL           = ["Public Wifi", "attwifi", "hotspot", "linksys", "<no ssid>", "NETGEAR", "dlink", "hpsetup", "default", "FreeWifi", 						   "Wireless", "Router", "Private WiFi", "WiFi", "Airport"]
ALPHABET 		    = ["0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$&*()_-=+"]

#SEEKED_SSID = "skynet"
#SEEKED_PASSPHRASE = "qwertyuiop"


def generate_pseudo_random():
	#Generate Pseudo Random SSIDS using the constant Lists above.
    for ssid in SSID_POOL:
		rand_alpha_index = randrange(0, 35)
		rand_pool_index = randrange(0, len(SSID_POOL))
		pseduo_random_ssids += SSID_POOL[random_pool_index] + ALPHABET[0][rand_alpha_index]
	
def generate_random():
	#Generate Random SSIDs
	for index in range(0, 14):
		rand_index = randrange(0, 35)
		random_ssids.append(ALPHABET[0][rand_index:-rand_index])

if __name__ == "__main__":
    bus = dbus.SystemBus()
    # Obtain handles to manager objects.
    manager_bus_object = bus.get_object(NM_BUS_NAME,
                                        NM_PATH)
    manager = dbus.Interface(manager_bus_object,
                             NM_DBUS_INTERFACE)
    manager_props = dbus.Interface(manager_bus_object,
                                   NM_DBUS_PROPS)

    # Enable Wireless. If Wireless is already enabled, this does nothing.
    was_wifi_enabled = manager_props.Get("org.freedesktop.NetworkManager",
                                         "WirelessEnabled")
    if not was_wifi_enabled:
        print "Enabling WiFi and sleeping for 10 seconds ..."
        manager_props.Set("org.freedesktop.NetworkManager", "WirelessEnabled",
                          True)
        # Give the WiFi adapter some time to scan for APs. This is absolutely
        # the wrong way to do it, and the program should listen for
        # AccessPointAdded() signals, but it will do.
        time.sleep(10)

    # Get path to the 'wlan0' device. If you're uncertain whether your WiFi
    # device is wlan0 or something else, you may utilize manager.GetDevices()
    # method to obtain a list of all devices, and then iterate over these
    # devices to check if DeviceType property equals NM_DEVICE_TYPE_WIFI (2).
    device_path = manager.GetDeviceByIpIface("wlan0")
    print "wlan0 path: ", device_path

    # Connect to the device's Wireless interface and obtain list of access
    # points.
    device = dbus.Interface(bus.get_object("org.freedesktop.NetworkManager",
                                           device_path),
                            "org.freedesktop.NetworkManager.Device.Wireless")
    accesspoints_paths_list = device.GetAccessPoints()

    # Identify our access point. We do this by comparing our desired SSID
    # to the SSID reported by the AP.
    our_ap_path = None
    for ap_path in accesspoints_paths_list:
        ap_props = dbus.Interface(
            bus.get_object("org.freedesktop.NetworkManager", ap_path),
            "org.freedesktop.DBus.Properties")
        ap_ssid = ap_props.Get("org.freedesktop.NetworkManager.AccessPoint",
                               "Ssid")
        # Returned SSID is a list of ASCII values. Let's convert it to a proper
        # string.
        str_ap_ssid = "".join(chr(i) for i in ap_ssid)
        print ap_path, ": SSID =", str_ap_ssid
        if str_ap_ssid == SEEKED_SSID:
            our_ap_path = ap_path
            break

    if not our_ap_path:
        print "AP not found :("
        exit(2)
    print "Our AP: ", our_ap_path

    # At this point we have all the data we need. Let's prepare our connection
    # parameters so that we can tell the NetworkManager what is the passphrase.
    connection_params = {
        "802-11-wireless": {
            "security": "802-11-wireless-security",
        },
        "802-11-wireless-security": {
            "key-mgmt": "wpa-psk",
            "psk": SEEKED_PASSPHRASE
        },
    }

    # Establish the connection.
    settings_path, connection_path = manager.AddAndActivateConnection(
        connection_params, device_path, our_ap_path)
    print "settings_path =", settings_path
    print "connection_path =", connection_path

    # Wait until connection is established. This may take a few seconds.
    NM_ACTIVE_CONNECTION_STATE_ACTIVATED = 2
    print """Waiting for connection to reach """ \
          """NM_ACTIVE_CONNECTION_STATE_ACTIVATED state ..."""
    connection_props = dbus.Interface(
        bus.get_object("org.freedesktop.NetworkManager", connection_path),
        "org.freedesktop.DBus.Properties")
    state = 0
    while True:
        # Loop forever until desired state is detected.
        #
        # A timeout should be implemented here, otherwise the program will
        # get stuck if connection fails.
        #
        # IF PASSWORD IS BAD, NETWORK MANAGER WILL DISPLAY A QUERY DIALOG!
        # This is something that should be avoided, but I don't know how, yet.
        #
        # Also, if connection is disconnected at this point, the Get()
        # method will raise an org.freedesktop.DBus.Error.UnknownMethod
        # exception. This should also be anticipated.
        state = connection_props.Get(
            "org.freedesktop.NetworkManager.Connection.Active", "State")
        if state == NM_ACTIVE_CONNECTION_STATE_ACTIVATED:
            break
        time.sleep(0.001)
    print "Connection established!"

    #
    # Connection is established. Do whatever is necessary.
    # ...
    #
    print "Sleeping for 5 seconds ..."
    time.sleep(5)
    print "Disconnecting ..."

    # Clean up: disconnect and delete connection settings. If program crashes
    # before this point is reached then connection settings will be stored
    # forever.
    # Some pre-init cleanup feature should be devised to deal with this problem,
    # but this is an issue for another topic.
    manager.DeactivateConnection(connection_path)
    settings = dbus.Interface(
        bus.get_object("org.freedesktop.NetworkManager", settings_path),
        "org.freedesktop.NetworkManager.Settings.Connection")
    settings.Delete()

    # Disable Wireless (optional step)
    if not was_wifi_enabled:
        manager_props.Set("org.freedesktop.NetworkManager", "WirelessEnabled",
                          False)
    print "DONE!"
    exit(0)
