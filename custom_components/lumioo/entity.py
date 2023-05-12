"""Base class for Lumioo entity."""
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DEFAULT_NAME, DOMAIN, LUMIOO_PLANT, LUMIOO_METER


class LumiooDeviceEntity(Entity):
    """Base implementation for Lumioo device."""

    _attr_should_poll = False

    def __init__(self, device_info) -> None:
        """Initialize a Lumioo device."""
        super().__init__()
        self._device_info = device_info
        self.device_name = device_info["serialNo"]
        self.device_id = device_info["shortSerialNo"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.device_name,
            manufacturer=DEFAULT_NAME,
            model=self._device_info["deviceType"],
            via_device=(DOMAIN, self._device_info["serialNo"]),
        )


class LumiooPlantEntity(Entity):
    """Base implementation for Lumioo plant."""

    _attr_should_poll = False

    def __init__(self, lumioo) -> None:
        """Initialize a Lumioo plant."""
        super().__init__()
        self.plant_name = lumioo.plant_name
        self.plant_id = lumioo.plant_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.plant_id)},
            manufacturer=DEFAULT_NAME,
            model=LUMIOO_PLANT,
            name=self.plant_name,
        )


class LumiooMeterEntity(Entity):
    """Base implementation for Lumioo meter."""

    _attr_should_poll = False

    def __init__(self, meter_name, plant_id, meter_id) -> None:
        """Initialize a Lumioo meter."""
        super().__init__()
        self._device_zone_id = f"{plant_id}_{meter_id}"
        self.meter_name = meter_name
        self.meter_id = meter_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_zone_id)},
            name=self.meter_name,
            manufacturer=DEFAULT_NAME,
            model=LUMIOO_METER,
        )
