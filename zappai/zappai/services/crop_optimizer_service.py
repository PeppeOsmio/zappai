from __future__ import annotations
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import multiprocessing
from threading import Thread
from typing import Callable, cast
from uuid import UUID

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from zappai.schemas import CustomBaseModel
from zappai.zappai.exceptions import (
    ClimateGenerativeModelNotFoundError,
    CropNotFoundError,
    CropYieldModelNotFoundError,
    LocationNotFoundError,
)
from zappai.zappai.repositories.climate_generative_model_repository import (
    ClimateGenerativeModelRepository,
)
from zappai.zappai.repositories.crop_repository import CropRepository
from zappai.zappai.dtos import ClimateDataDTO, CropDTO, FutureClimateDataDTO
from zappai.zappai.repositories.future_climate_data_repository import (
    FutureClimateDataRepository,
)
from zappai.zappai.repositories.location_repository import LocationRepository
from zappai.zappai.repositories.past_climate_data_repository import (
    PastClimateDataRepository,
)
from zappai.zappai.utils.common import (
    calc_months_delta,
    create_stats_dataframe,
    get_next_n_months,
)
from sklearn.ensemble import RandomForestRegressor
from zappai.zappai.services.crop_yield_model_service import (
    FEATURES as CROP_YIELD_MODEL_FEATURES,
    TARGET as CROP_YIELD_MODEL_TARGET,
)
import random

Individual = list[bool]
Population = list[Individual]
FitnessCallback = Callable[[Individual], float]


def run_genetic_algorithm(forecast_df: pd.DataFrame, crop: CropDTO, model: RandomForestRegressor):
    def on_population_created(i: int, population: Population):
        print(f"\rPopulation {i}/20 processed", end="")
        if i == 20:
            print()

    ga = CropGeneticAlgorithm(
        chromosome_length=10,
        population_size=20,
        mutation_rate=0.01,
        crossover_rate=0.7,
        generations=20,
        forecast_df=forecast_df,
        crop=crop,
        model=model,
        on_population_created=on_population_created,
        parallel_workers=1,
    )
    return ga.run()


class CropGeneticAlgorithm:
    def __init__(
        self,
        chromosome_length: int,
        population_size: int,
        mutation_rate: float,
        crossover_rate: float,
        generations: int,
        forecast_df: pd.DataFrame,
        crop: CropDTO,
        model: RandomForestRegressor,
        on_population_created: Callable[[int, Population], None] | None = None,
        parallel_workers: int | None = None,
    ) -> None:
        self.chromosome_length = chromosome_length
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.generations = generations
        self.forecast_df = forecast_df
        self.crop = crop
        self.model = model
        self.on_population_processed = on_population_created
        self.parallel_workers = (
            parallel_workers
            if parallel_workers is not None
            else multiprocessing.cpu_count()
        )

    def fitness_func(self, individual: Individual) -> float:
        if len(individual) != 10:
            raise Exception(f"Bro individual must be of size 10...")
        sowing = individual_to_int(individual[:5])
        harvesting = individual_to_int(individual[5:])

        if (sowing >= len(self.forecast_df)) | (harvesting >= len(self.forecast_df)):
            return 0.0

        sowing_year, sowing_month = self.forecast_df.index[sowing]
        harvest_year, harvest_month = self.forecast_df.index[harvesting]

        duration = calc_months_delta(
            start_year=sowing_year,
            start_month=sowing_month,
            end_year=harvest_year,
            end_month=harvest_month,
        )

        if duration <= 0:
            return 0.0
        if (duration < cast(int, self.crop.min_farming_months)) | (
            duration > cast(int, self.crop.max_farming_months)
        ):
            return 0.0

        forecast_for_individual = self.forecast_df[
            (
                (self.forecast_df.index.get_level_values("year") < harvest_year)
                | (
                    (self.forecast_df.index.get_level_values("year") == harvest_year)
                    & (self.forecast_df.index.get_level_values("year") <= harvest_month)
                )
            )
            | (
                (self.forecast_df.index.get_level_values("year") > sowing_year)
                | (
                    (self.forecast_df.index.get_level_values("year") == sowing_year)
                    & (self.forecast_df.index.get_level_values("year") >= sowing_month)
                )
            )
        ]

        stats_forecast = create_stats_dataframe(df=forecast_for_individual, ignore=[])

        x_df = pd.DataFrame(
            {
                "sowing_year": [sowing_year],
                "sowing_month": [sowing_month],
                "harvest_year": [harvest_year],
                "harvest_month": [harvest_month],
                "duration_months": calc_months_delta(
                    start_year=sowing_year,
                    start_month=sowing_month,
                    end_year=harvest_year,
                    end_month=harvest_month,
                ),
            }
        )
        x_df = pd.concat([x_df, stats_forecast], axis=1)

        pred = self.model.predict(x_df[CROP_YIELD_MODEL_FEATURES].to_numpy())
        return pred[0]

    def __generate_individual(self) -> Individual:
        return [randbool() for _ in range(self.chromosome_length)]

    def __generate_population(
        self,
    ) -> Population:
        return [self.__generate_individual() for _ in range(self.population_size)]

    def process_chunk(self, position: int, chunk: Population):
        return position, [self.fitness_func(individual) for individual in chunk]

    def __calc_fitnesses_in_pool(self, population: Population) -> list[float]:
        if self.parallel_workers == 1:
            fitnesses = [self.fitness_func(individual) for individual in population]
        else:
            chunk_size = len(population) // self.parallel_workers
            chunks: list[list[Individual]] = []
            remainder = len(population) % self.parallel_workers
            start = 0
            end = 0
            for i in range(self.parallel_workers):
                end = start + chunk_size + (1 if i < remainder else 0)
                chunks.append(population[start:end])
                start = end

            with ProcessPoolExecutor(max_workers=self.parallel_workers) as pool:
                futures = [
                    pool.submit(self.process_chunk, position=i, chunk=chunk)
                    for i, chunk in enumerate(chunks)
                ]
                results = [future.result() for future in as_completed(futures)]

            results = sorted(results, key=lambda result: result[0])
            fitnesses = [
                fitness
                for position, chunk_fitnesses in results
                for fitness in chunk_fitnesses
            ]
        return fitnesses

    def __select(self, population: Population):
        fitnesses: list[float] = self.__calc_fitnesses_in_pool(population)
        total_fitness = sum(fitnesses)
        if total_fitness == 0:
            selection_probs = [1 / len(population) for i in range(len(population))]
        else:
            selection_probs = [fitness / total_fitness for fitness in fitnesses]
        return population[
            random.choices(range(len(population)), weights=selection_probs, k=1)[0]
        ]

    def __crossover(self, parent1: Individual, parent2: Individual):
        if random.random() < self.crossover_rate:
            point = random.randint(1, len(parent1) - 1)
            return parent1[:point] + parent2[point:], parent2[:point] + parent1[point:]
        return parent1, parent2

    def __mutate(self, individual: Individual) -> Individual:
        return [
            bit if random.random() > self.mutation_rate else not bit
            for bit in individual
        ]

    def run(
        self,
    ) -> tuple[list[Individual], list[float]]:
        best_individuals: list[Individual] = []
        best_fitnesses: list[float] = []
        population: Population = self.__generate_population()
        for i in range(self.generations - 1):
            new_population: Population = []
            for _ in range(len(population) // 2):
                parent1 = self.__select(population)
                parent2 = self.__select(population)
                child1, child2 = self.__crossover(parent1, parent2)
                new_population.append(self.__mutate(child1))
                new_population.append(self.__mutate(child2))
            population = new_population
            if self.on_population_processed is not None:
                self.on_population_processed(i + 1, population)
                fitnesses = self.__calc_fitnesses_in_pool(population)
            best_fitness = max(fitnesses)
            best_individual_index = fitnesses.index(best_fitness)
            best_individual = population[best_individual_index]

            best_fitnesses.append(best_fitness)
            best_individuals.append(best_individual)
        
        if self.on_population_processed is not None:
        
            self.on_population_processed(self.generations, population)

        
        return best_individuals, best_fitnesses

 
def randbool() -> bool:
    return random.randint(0, 1) == 1


def individual_to_str(individual: Individual) -> str:
    result = ""
    for bit in individual:
        result += str(int(bit))
    return result


def individual_to_int(individual: Individual) -> int:
    result = 0
    for i in range(len(individual)):
        result += int(individual[i]) * 2**i
    return result


@dataclass
class SowingAndHarvestingDTO:
    sowing_year: int
    sowing_month: int
    harvest_year: int
    harvest_month: int
    estimated_yield_per_hectar: float
    duration: int


@dataclass
class CropOptimizerResultDTO:
    best_combinations: list[SowingAndHarvestingDTO]
    forecast: list[ClimateDataDTO]


class CropOptimizerService:
    def __init__(
        self,
        crop_repository: CropRepository,
        past_climate_data_repository: PastClimateDataRepository,
        future_climate_data_repository: FutureClimateDataRepository,
        location_repository: LocationRepository,
        climate_generative_model_repository: ClimateGenerativeModelRepository,
    ) -> None:
        self.crop_repository = crop_repository
        self.past_climate_data_repository = past_climate_data_repository
        self.future_climate_data_repository = future_climate_data_repository
        self.location_repository = location_repository
        self.climate_generative_model_repository = climate_generative_model_repository

    async def get_best_crop_sowing_and_harvesting(
        self, session: AsyncSession, crop_name: str, location_id: UUID
    ) -> CropOptimizerResultDTO:
        """_summary_

        Args:
            crop_id (UUID): _description_
            location_id (UUID): _description_
            start_year (int): _description_
            start_month (int): _description_

        Returns:
            CropOptimizerResultDTO:
        """
        location = await self.location_repository.get_location_by_id(
            session=session, location_id=location_id
        )

        if location is None:
            raise LocationNotFoundError(str(location_id))

        crop = await self.crop_repository.get_crop_by_id(
            session=session, crop_name=crop_name
        )
        if crop is None:
            raise CropNotFoundError(str(crop_name))

        model = crop.crop_yield_model
        if model is None:
            raise CropYieldModelNotFoundError(str(crop_name))

        forecast = await self.climate_generative_model_repository.generate_climate_data_from_last_past_climate_data(
            session=session, location_id=location.id, months=24
        )
        forecast_df = ClimateDataDTO.from_list_to_dataframe(forecast)
        forecast_df = forecast_df.drop(columns=["location_id"])

        best_combinations: list[SowingAndHarvestingDTO] = []

        loop = asyncio.get_running_loop()

        with ProcessPoolExecutor() as pool:
            results, fitnesses = await loop.run_in_executor(
                pool, run_genetic_algorithm, forecast_df, crop, model
            )

        for i in range(len(results)):
            result = results[i]
            fitness = fitnesses[i]

            sowing = individual_to_int(result[:5])
            harvesting = individual_to_int(result[5:])

            sowing_year, sowing_month = forecast_df.index[sowing]
            harvest_year, harvest_month = forecast_df.index[harvesting]
            duration = calc_months_delta(
                start_year=sowing_year,
                start_month=sowing_month,
                end_year=harvest_year,
                end_month=harvest_month,
            )
            best_combinations.append(
                SowingAndHarvestingDTO(
                    sowing_year=sowing_year,
                    sowing_month=sowing_month,
                    harvest_year=harvest_year,
                    harvest_month=harvest_month,
                    estimated_yield_per_hectar=fitness,
                    duration=duration,
                )
            )
        best_combinations = sorted(
            best_combinations, key=lambda comb: comb.estimated_yield_per_hectar, reverse=True
        )
        return CropOptimizerResultDTO(
            best_combinations=best_combinations[:3],
            forecast=forecast,
        )
