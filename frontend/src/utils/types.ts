export interface User {
    id: string;
    username: string;
}

export interface ZappaiLocation {
    id: string;
    country: string;
    name: string;
    longitude: number;
    latitude: number;
    isModelReady: boolean;
    isDownloadingPastClimateData: boolean;
    lastPastClimateDataYear: number | null;
    lastPastClimateDataMonth: number | null;
}
  

// Define a type for the context
export interface AuthContextType {
    currentUser: User | null;
    setCurrentUser: React.Dispatch<React.SetStateAction<User | null>>;
}

export interface Crop {
    name: string;
}

export interface ClimateDataDetails {
    year: number;
    month: number;
    temperature2m: number;
    totalPrecipitation: number;
    surfaceSolarRadiationDownwards: number;
    surfaceThermalRadiationDownwards: number;
    surfaceNetSolarRadiation: number;
    surfaceNetThermalRadiation: number;
    totalCloudCover: number;
    dewpointTemperature2m: number;
    soilTemperatureLevel3: number;
    volumetricSoilWaterLayer3: number;
}

export interface SowingAndHarvestingDetails {
    sowingYear: number;
    sowingMonth: number;
    harvestYear: number;
    harvestMonth: number;
    estimatedYieldPerHectar: number;
    duration: number;
}

export interface PredictionsResponse {
    bestCombinations: SowingAndHarvestingDetails[];
    forecast: ClimateDataDetails[];
}