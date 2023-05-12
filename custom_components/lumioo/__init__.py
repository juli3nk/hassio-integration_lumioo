"""The Lumioo integration."""
from __future__ import annotations

from datetime import date, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

# from homeassistant.util import Throttle
# from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DATA,
    COORDINATOR_PLANT,
    COORDINATOR_SOLAR,
    COORDINATOR_TRACKERS,
    COORDINATOR_METER,
    UPDATE_LISTENER,
    # DEBOUNCE_COOLDOWN,
)

import aiohttp
from lumioo.auth import Auth
from lumioo.core import LumiooHubAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=4)
SCAN_INTERVAL_PLANT = timedelta(minutes=1)
SCAN_INTERVAL_SOLAR = timedelta(minutes=1)
SCAN_INTERVAL_TRACKERS = timedelta(minutes=1)
SCAN_INTERVAL_METER = timedelta(minutes=1)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lumioo from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    lumiooconnector = LumiooConnector(hass, entry.data["access_token"], 2180)

    try:
        await lumiooconnector.setup()
    except KeyError:
        _LOGGER.error("Failed to login to lumioo")
        return False
    except RuntimeError as exc:
        _LOGGER.error("Failed to setup lumioo: %s", exc)
        return False
    except Exception as err:
        raise ConfigEntryNotReady from err

    async def async_update_data_plant():
        _LOGGER.debug("Fetching latest data for plant")
        await lumiooconnector.update_data_plant()
        return lumiooconnector

    async def async_update_data_solar():
        _LOGGER.debug("Fetching latest data for solar")
        await lumiooconnector.update_data_solar()
        return lumiooconnector

    async def async_update_data_trackers():
        _LOGGER.debug("Fetching latest data for trackers")
        await lumiooconnector.update_data_trackers()
        return lumiooconnector

    async def async_update_data_meter():
        _LOGGER.debug("Fetching latest data for meter")
        await lumiooconnector.update_data_meter()
        return lumiooconnector

    coordinator_plant = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Lumioo Plant",
        update_method=async_update_data_plant,
        update_interval=SCAN_INTERVAL_PLANT,
        # request_refresh_debouncer=Debouncer(
        #    hass, _LOGGER, cooldown=DEBOUNCE_COOLDOWN, immediate=True
        # ),
    )

    coordinator_solar = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Lumioo Solar",
        update_method=async_update_data_solar,
        update_interval=SCAN_INTERVAL_SOLAR,
    )

    coordinator_trackers = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Lumioo Trackers",
        update_method=async_update_data_trackers,
        update_interval=SCAN_INTERVAL_TRACKERS,
    )

    coordinator_meter = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Lumioo Meter",
        update_method=async_update_data_meter,
        update_interval=SCAN_INTERVAL_METER,
    )

    # Fetch initial data so we have data when entities subscribe
    # await coordinator_plant.async_refresh()
    # await coordinator_meter.async_refresh()

    update_listener = entry.add_update_listener(_async_update_listener)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA: lumiooconnector,
        COORDINATOR_PLANT: coordinator_plant,
        COORDINATOR_SOLAR: coordinator_solar,
        COORDINATOR_TRACKERS: coordinator_trackers,
        COORDINATOR_METER: coordinator_meter,
        UPDATE_LISTENER: update_listener,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class LumiooConnector:
    """An object to store the Lumioo data."""

    def __init__(self, hass: HomeAssistant, access_token, plant_id) -> None:
        """Initialize Lumioo Connector."""
        self.hass = hass
        self._access_token = access_token

        self.auth = None
        self.api = None

        self.plant_id = plant_id
        self.main_meter_id = None

        self.plant = None
        self.trackers = None
        self.meter = None

        self.data = {
            "plant": {},
            "solar": {},
            "trackers": {},
            "meter": {},
        }

    async def setup(self):
        """Connect to Lumioo and fetch all datas."""
        websession = aiohttp_client.async_get_clientsession(self.hass)
        self.auth = Auth(websession, self._access_token)
        self.api = LumiooHubAPI(self.auth)

        await self.update_plant()

        await self.update_data_plant()
        await self.update_data_solar()
        await self.update_data_trackers()
        await self.update_data_meter()

    async def update_plant(self):
        """Update the internal data from Lumioo."""
        _LOGGER.debug("Updating plant %s", self.plant_id)
        try:
            data_plant = await self.api.async_get_plant(self.plant_id)
            data_trackers = await self.api.async_get_trackers(self.plant_id)
            data_meter = await self.api.async_get_meter(data_plant.main_meter)
        except RuntimeError:
            _LOGGER.error(
                "Unable to connect to Lumioo while updating trackers %d", self.plant_id
            )
            return

        self.main_meter_id = data_plant.main_meter

        self.plant = data_plant
        self.trackers = data_trackers
        self.meter = data_meter

    async def update_data_plant(self):
        """Update the internal data from Lumioo."""
        _LOGGER.debug("Updating data plant %s", self.main_meter_id)
        try:
            today = date.today()
            next_day_dt = today + timedelta(days=1)
            next_day = date(next_day_dt.year, next_day_dt.month, next_day_dt.day)

            date_after = today.isoformat()
            date_strictly_before = next_day.isoformat()

            data_plant = await self.api.async_get_plant_status(self.plant_id)
            data_plant_energy_day = await self.api.async_get_plant_energy_days(
                self.plant_id, date_after, date_strictly_before
            )
        except RuntimeError:
            _LOGGER.error(
                "Unable to connect to Lumioo while updating meter %s",
                self.main_meter_id,
            )
            return

        self.data["plant"]["main"] = data_plant
        if len(data_plant_energy_day) > 0:
            self.data["plant"]["energy_day"] = data_plant_energy_day[0]
        else:
            self.data["plant"]["energy_day"] = None

    async def update_data_solar(self):
        """Update the internal data from Lumioo."""
        _LOGGER.debug("Updating solar data %s", self.plant_id)
        try:
            today = date.today().isoformat()

            data_solar_times = await self.api.async_get_solar_times(
                self.plant_id, today
            )
            data_production_estimates = await self.api.async_get_production_estimates(
                self.plant_id
            )
        except RuntimeError:
            _LOGGER.error(
                "Unable to connect to Lumioo while updating solar %d", self.plant_id
            )
            return

        self.data["solar"]["times"] = data_solar_times
        self.data["solar"]["production_estimates"] = {}

        for pe in data_production_estimates:
            data = {}
            data["production_index"] = pe["production_index"]
            data["production"] = pe["production"]

            ref = pe["reference"]

            self.data["solar"]["production_estimates"][ref] = data

    async def update_data_trackers(self):
        """Update the internal data from Lumioo."""
        _LOGGER.debug("Updating trackers data %s", self.main_meter_id)
        try:
            for tracker in self.trackers:
                self.data["trackers"][
                    str(tracker.id)
                ] = await self.api.async_get_tracker_status(tracker.id)
        except RuntimeError:
            _LOGGER.error(
                "Unable to connect to Lumioo while updating meter %s",
                self.main_meter_id,
            )
            return

    async def update_data_meter(self):
        """Update the internal data from Lumioo."""
        _LOGGER.debug("Updating meter data %s", self.main_meter_id)
        try:
            data = await self.api.async_get_meter_status(self.main_meter_id)
        except RuntimeError:
            _LOGGER.error(
                "Unable to connect to Lumioo while updating meter %s",
                self.main_meter_id,
            )
            return

        self.data["meter"] = data
