"""Support for Lumioo sensor."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfSpeed
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DEFAULT_NAME,
    DEVICE_TYPES,
    DOMAIN,
    DATA,
    COORDINATOR_PLANT,
    COORDINATOR_SOLAR,
    COORDINATOR_TRACKERS,
    COORDINATOR_METER,
)


@dataclass
class LumiooSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    state_fn: Callable[[Any], StateType]


@dataclass
class LumiooSensorEntityDescription(
    SensorEntityDescription, LumiooSensorEntityDescriptionMixin
):
    """Describes Lumioo sensor entity."""

    attributes_fn: Callable[[Any], dict[Any, StateType]] | None = None


_LOGGER = logging.getLogger(__name__)

PLANT_SENSORS = [
    LumiooSensorEntityDescription(
        key="synchronised_data",
        name="Synchronised data",
        state_fn=lambda data: data["main"]["is_synchronised"],
        attributes_fn=lambda data: {
            "time": data["main"]["latest_synchronisation"],
        },
    ),
    LumiooSensorEntityDescription(
        key="status_reference",
        name="Status reference",
        state_fn=lambda data: data["main"]["status_type"]["reference"],
    ),
    LumiooSensorEntityDescription(
        key="today_production",
        name="Today production ",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        state_fn=lambda data: data["energy_day"]["production"],
        attributes_fn=lambda data: {
            "time": data["energy_day"]["date"],
        },
    ),
    LumiooSensorEntityDescription(
        key="today_consumption",
        name="Today consumption ",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        state_fn=lambda data: data["energy_day"]["consumption"],
        attributes_fn=lambda data: {
            "time": data["energy_day"]["date"],
        },
    ),
    LumiooSensorEntityDescription(
        key="today_auto_consumption",
        name="Today auto consumption ",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        state_fn=lambda data: data["energy_day"]["auto_consumption"],
        attributes_fn=lambda data: {
            "time": data["energy_day"]["date"],
        },
    ),
    LumiooSensorEntityDescription(
        key="today_grid_consumption",
        name="Today grid consumption ",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        state_fn=lambda data: data["energy_day"]["grid_consumption"],
        attributes_fn=lambda data: {
            "time": data["energy_day"]["date"],
        },
    ),
    LumiooSensorEntityDescription(
        key="today_grid_restitution",
        name="Today grid restitution ",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        state_fn=lambda data: data["energy_day"]["grid_restitution"],
        attributes_fn=lambda data: {
            "time": data["energy_day"]["date"],
        },
    ),
]

SOLAR_SENSORS = [
    LumiooSensorEntityDescription(
        key="sunrise",
        name="Sunrise",
        device_class=SensorDeviceClass.TIMESTAMP,
        state_fn=lambda data: data["times"]["sunrise"],
    ),
    LumiooSensorEntityDescription(
        key="sunset",
        name="Sunset",
        device_class=SensorDeviceClass.TIMESTAMP,
        state_fn=lambda data: data["times"]["sunset"],
    ),
    LumiooSensorEntityDescription(
        key="forecast today morning",
        name="Today morning solar forecast",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        state_fn=lambda data: data["production_estimates"]["today_morning"][
            "production"
        ],
        attributes_fn=lambda data: {
            "index": data["production_estimates"]["today_morning"]["production_index"],
        },
    ),
    LumiooSensorEntityDescription(
        key="forecast today afternoon",
        name="Today afternoon solar forecast",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        state_fn=lambda data: data["production_estimates"]["today_afternoon"][
            "production"
        ],
        attributes_fn=lambda data: {
            "index": data["production_estimates"]["today_afternoon"][
                "production_index"
            ],
        },
    ),
    LumiooSensorEntityDescription(
        key="forecast tomorrow morning",
        name="Tomorrow morning solar forecast",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        state_fn=lambda data: data["production_estimates"]["tomorrow_morning"][
            "production"
        ],
        attributes_fn=lambda data: {
            "index": data["production_estimates"]["tomorrow_morning"][
                "production_index"
            ],
        },
    ),
    LumiooSensorEntityDescription(
        key="forecast tomorrow afternoon",
        name="Tomorrow afternoon solar forecast",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        state_fn=lambda data: data["production_estimates"]["tomorrow_afternoon"][
            "production"
        ],
        attributes_fn=lambda data: {
            "index": data["production_estimates"]["tomorrow_afternoon"][
                "production_index"
            ],
        },
    ),
]

TRACKER_SENSORS = [
    LumiooSensorEntityDescription(
        key="synchronised_data",
        name="Synchronised data",
        state_fn=lambda data: data["is_synchronised"],
        attributes_fn=lambda data: {
            "time": data["latest_synchronisation"],
        },
    ),
    LumiooSensorEntityDescription(
        key="production",
        name="Production",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        state_fn=lambda data: data["data"]["production"],
        attributes_fn=lambda data: {
            "time": data["data"]["date"],
        },
    ),
    LumiooSensorEntityDescription(
        key="wind_speed_max",
        name="Wind speed max",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        state_fn=lambda data: data["control"]["max_wind_speed"],
        attributes_fn=lambda data: {
            "time": data["control"]["date"],
        },
    ),
    LumiooSensorEntityDescription(
        key="wind_speed_average",
        name="Wind speed average",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        state_fn=lambda data: data["control"]["average_wind_speed"],
        attributes_fn=lambda data: {
            "time": data["control"]["date"],
        },
    ),
    LumiooSensorEntityDescription(
        key="status_reference",
        name="Status reference",
        state_fn=lambda data: data["status_type"]["reference"],
    ),
]

METER_SENSORS = [
    LumiooSensorEntityDescription(
        key="synchronised_data",
        name="Synchronised data",
        state_fn=lambda data: data["is_synchronised"],
        attributes_fn=lambda data: {
            "time": data["latest_synchronisation"],
        },
    ),
    LumiooSensorEntityDescription(
        key="consumption",
        name="Consumption",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        state_fn=lambda data: data["consumption"],
        attributes_fn=lambda data: {
            "time": data["date"],
        },
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    lumioo = data[DATA]

    coordinator_plant: DataUpdateCoordinator = data[COORDINATOR_PLANT]
    coordinator_solar: DataUpdateCoordinator = data[COORDINATOR_SOLAR]
    coordinator_trackers: DataUpdateCoordinator = data[COORDINATOR_TRACKERS]
    coordinator_meter: DataUpdateCoordinator = data[COORDINATOR_METER]

    entities: list[SensorEntity] = []

    # Create plant sensors
    entities.extend(
        [
            LumiooSensor(lumioo, "plant", "", entity_description, coordinator_plant)
            for entity_description in PLANT_SENSORS
        ]
    )

    # Create solar sensors
    entities.extend(
        [
            LumiooSensor(lumioo, "solar", "", entity_description, coordinator_solar)
            for entity_description in SOLAR_SENSORS
        ]
    )

    # Create trackers sensors
    for tracker in lumioo.trackers:
        entities.extend(
            [
                LumiooSensor(
                    lumioo,
                    "trackers",
                    str(tracker.id),
                    entity_description,
                    coordinator_trackers,
                )
                for entity_description in TRACKER_SENSORS
            ]
        )

    # Create meter sensors
    entities.extend(
        [
            LumiooSensor(lumioo, "meter", "", entity_description, coordinator_meter)
            for entity_description in METER_SENSORS
        ]
    )

    async_add_entities(entities, True)


class LumiooSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Representation of a Lumioo Meter sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        lumioo,
        data_type: str,
        tracker_id: str,
        entity_description: SensorEntityDescription,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self.entity_description = entity_description
        self.lumioo = lumioo
        self.data_type = data_type
        self.tracker_id = tracker_id
        self._state = None
        self._available = False

        self.device_id = None
        if self.data_type == "plant":
            self.device_id = self.lumioo.data[self.data_type]["main"]["id"]
        if self.data_type == "trackers":
            self.device_id = self.lumioo.data[self.data_type][self.tracker_id]["id"]
        if self.data_type == "meter":
            self.device_id = self.lumioo.data[self.data_type]["id"]

        self._attr_device_class = entity_description.device_class
        self._attr_state_class = entity_description.state_class
        self._attr_native_unit_of_measurement = (
            entity_description.native_unit_of_measurement
        )

    @property
    def unique_id(self) -> str:
        """Device Uniqueid."""
        unique_id = f"lumioo {self.data_type} {self.entity_description.key}"
        if self.device_id is not None:
            unique_id = f"lumioo {str(self.device_id)} {self.data_type} {self.entity_description.key}"
        return unique_id

    @property
    def name(self) -> str | None:
        """Entity Name."""
        return self.entity_description.name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def native_value(self) -> StateType | str | None:
        """Get the latest reading."""
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        device_info = DeviceInfo(
            name=DEVICE_TYPES[self.data_type],
            manufacturer=DEFAULT_NAME,
            model=DEVICE_TYPES[self.data_type],
            identifiers={(DOMAIN, self.device_id)},
        )
        if self.data_type == "plant":
            device_info[
                "configuration_url"
            ] = "https://mylumioo.com/plant/plant-settings"
        if self.data_type == "solar":
            device_info["entry_type"] = DeviceEntryType.SERVICE
            device_info["identifiers"] = {(DOMAIN, self.data_type)}
            device_info["via_device"] = (DOMAIN, 2180)
        if self.data_type == "trackers":
            device_info["name"] = f"{DEVICE_TYPES[self.data_type]} {self.device_id}"
            device_info[
                "configuration_url"
            ] = f"https://mylumioo.com/plant/tracker-settings/{self.tracker_id}"
            device_info["via_device"] = (DOMAIN, 2180)
        if self.data_type == "meter":
            device_info["via_device"] = (DOMAIN, 2180)
        return device_info

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        self._available = self.coordinator.last_update_success
        if self._available:
            try:
                lumioo_data = self.lumioo.data[self.data_type]
                if len(self.tracker_id) > 0:
                    lumioo_data = lumioo_data[self.tracker_id]
            except KeyError as exc:
                _LOGGER.debug(exc)
                return

            try:
                self._state = self.entity_description.state_fn(lumioo_data)
                if self.entity_description.attributes_fn is not None:
                    self._attr_extra_state_attributes = (
                        self.entity_description.attributes_fn(lumioo_data)
                    )
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                _LOGGER.debug(exc)
                return
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))

        # If the background update finished before
        # we added the entity, there is no need to restore
        # state.
        if self.coordinator.last_update_success:
            return

        if last_state := await self.async_get_last_state():
            self._state = last_state.state
            self._available = True
