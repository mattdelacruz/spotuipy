"""Tests for the device-selection preference order in find_active_device.

find_active_device imports a live Spotify client at module load, so rather than
import it we test the pure decision tree it implements. Return-value contract:

    None  -> no devices available
    -1    -> the chosen device is already active; play on current device
    "id"  -> transfer playback to this device id first

Preference order:
    1. the preferred (spotifyd) device, by name
    2. whatever device is currently active
    3. the first available device

This logic is where the old "Speaker-only" bug and the dual-playback bug lived,
so it's worth pinning down.
"""


def choose_device(devices, preferred_name="spotifyd"):
    """Mirror of find_active_device's selection logic."""
    if not devices:
        return None
    preferred = next((d for d in devices if d.get("name") == preferred_name), None)
    if preferred:
        return -1 if preferred.get("is_active") else preferred["id"]
    active = next((d for d in devices if d.get("is_active")), None)
    if active:
        return -1
    return devices[0]["id"]


def dev(name, id_, is_active=False, type_="Computer"):
    return {"name": name, "id": id_, "is_active": is_active, "type": type_}


class TestNoDevices:
    def test_empty_list_returns_none(self):
        assert choose_device([]) is None


class TestPreferredDevice:
    def test_prefers_spotifyd_when_inactive_returns_its_id(self):
        devices = [
            dev("TV", "tv1", is_active=True, type_="TV"),
            dev("spotifyd", "sd1", is_active=False),
        ]
        # Even though the TV is active, prefer spotifyd -> transfer to its id.
        assert choose_device(devices) == "sd1"

    def test_prefers_spotifyd_when_active_returns_minus_one(self):
        devices = [dev("spotifyd", "sd1", is_active=True)]
        assert choose_device(devices) == -1

    def test_custom_preferred_name_is_respected(self):
        devices = [
            dev("my-daemon", "d1", is_active=False),
            dev("TV", "tv1", is_active=True, type_="TV"),
        ]
        assert choose_device(devices, preferred_name="my-daemon") == "d1"


class TestActiveFallback:
    def test_active_device_when_no_preferred(self):
        devices = [
            dev("Phone", "p1", is_active=False, type_="Smartphone"),
            dev("TV", "tv1", is_active=True, type_="TV"),
        ]
        # No spotifyd present; a device is active -> play on current.
        assert choose_device(devices) == -1


class TestFirstAvailableFallback:
    def test_first_device_when_none_active_and_no_preferred(self):
        devices = [
            dev("Phone", "p1", is_active=False, type_="Smartphone"),
            dev("TV", "tv1", is_active=False, type_="TV"),
        ]
        assert choose_device(devices) == "p1"

    def test_does_not_filter_by_type(self):
        # Regression: the old bug only looked for type == "Speaker".
        # A non-Speaker device must still be selectable.
        devices = [dev("Laptop", "l1", is_active=False, type_="Computer")]
        assert choose_device(devices) == "l1"
