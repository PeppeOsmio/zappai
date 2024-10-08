from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from zappai.database.base import Base
from geoalchemy2 import Geography


class Location(Base):
    __tablename__ = "location"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(index=True)
    longitude: Mapped[float]
    latitude: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(index=True)
    is_visible: Mapped[bool] = mapped_column(server_default="false")
    is_downloading_past_climate_data: Mapped[bool] = mapped_column(server_default="false")

    #__table_args__ = (
    #    UniqueConstraint("longitude", "latitude", name="_longitude_latitude_uc"),
    #)


class ClimateGenerativeModel(Base):
    __tablename__ = "climate_generative_model"

    id: Mapped[UUID] = mapped_column(primary_key=True)

    model: Mapped[bytes]
    x_scaler: Mapped[bytes]
    y_scaler: Mapped[bytes]
    rmse: Mapped[float]

    train_start_year: Mapped[int]
    train_start_month: Mapped[int]
    train_end_year: Mapped[int]
    train_end_month: Mapped[int]

    validation_start_year: Mapped[int]
    validation_start_month: Mapped[int]
    validation_end_year: Mapped[int]
    validation_end_month: Mapped[int]

    test_start_year: Mapped[int]
    test_start_month: Mapped[int]
    test_end_year: Mapped[int]
    test_end_month: Mapped[int]

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey(column="location.id", ondelete="CASCADE")
    )

    location: Mapped[Location] = relationship()

    __table_args__ = (UniqueConstraint("location_id", name="_location_id_nc"),)


class Crop(Base):
    __tablename__ = "crop"

    name: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(index=True)
    min_farming_months: Mapped[int]
    max_farming_months: Mapped[int]
    crop_yield_model: Mapped[bytes | None]
    mse: Mapped[float | None]
    r2: Mapped[float | None]


class CropYieldData(Base):
    __tablename__ = "crop_yield_data"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    location_id: Mapped[UUID] = mapped_column(ForeignKey(column="location.id", ondelete="CASCADE"))
    crop_name: Mapped[str] = mapped_column(ForeignKey(column="crop.name"))
    sowing_year: Mapped[int]
    sowing_month: Mapped[int]
    harvest_year: Mapped[int]
    harvest_month: Mapped[int]
    duration_months: Mapped[int]
    yield_per_hectar: Mapped[float]

    location: Mapped[Location] = relationship()


class PastClimateData(Base):
    __tablename__ = "past_climate_data"

    id: Mapped[UUID] = mapped_column(primary_key=True)

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey(column="location.id", ondelete="CASCADE")
    )
    year: Mapped[int]
    month: Mapped[int]

    u_component_of_wind_10m: Mapped[float]
    v_component_of_wind_10m: Mapped[float]
    temperature_2m: Mapped[float]
    evaporation: Mapped[float]
    total_precipitation: Mapped[float]
    surface_pressure: Mapped[float]
    surface_solar_radiation_downwards: Mapped[float]
    surface_thermal_radiation_downwards: Mapped[float]

    surface_net_solar_radiation: Mapped[float]
    surface_net_thermal_radiation: Mapped[float]
    snowfall: Mapped[float]
    total_cloud_cover: Mapped[float]
    dewpoint_temperature_2m: Mapped[float]
    soil_temperature_level_3: Mapped[float]
    volumetric_soil_water_layer_3: Mapped[float]

    location: Mapped[Location] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "location_id", "year", "month", name="_location_id_year_month_uc"
        ),
    )


class FutureClimateData(Base):
    __tablename__ = "future_climate_data"

    id: Mapped[UUID] = mapped_column(primary_key=True)

    longitude: Mapped[float]
    latitude: Mapped[float]
    year: Mapped[int]
    month: Mapped[int]

    coordinates: Mapped[Geography] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )

    u_component_of_wind_10m: Mapped[float]
    v_component_of_wind_10m: Mapped[float]
    temperature_2m: Mapped[float]
    evaporation: Mapped[float]
    total_precipitation: Mapped[float]
    surface_pressure: Mapped[float]
    surface_solar_radiation_downwards: Mapped[float]
    surface_thermal_radiation_downwards: Mapped[float]

    __table_args__ = (
        UniqueConstraint(
            "longitude",
            "latitude",
            "year",
            "month",
            name="_longitude_latitude_year_month_uc",
        ),
    )
