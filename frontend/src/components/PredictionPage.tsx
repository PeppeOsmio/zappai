import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { ClimateDataDetails, PredictionsResponse, ZappaiLocation } from '../utils/types';
import { Alert, Box, CircularProgress, MenuItem, Paper, Select, SelectChangeEvent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Grid } from '@mui/material';
import { useSearchParams } from 'react-router-dom';
import { LineChart } from '@mui/x-charts';

const PredictionPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const cropName = searchParams.get('cropName');
    const locationId = searchParams.get('locationId');

    const [predictions, setPredictions] = useState<PredictionsResponse | null>(null);
    const [selectedForecast, setSelectedForecast] = useState<string>('temperature2M');
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [location, setLocation] = useState<ZappaiLocation | null>(null);

    const loadData = async () => {
        if (!cropName || !locationId) {
            setErrorMessage('Missing cropName or locationId parameter');
            setIsLoading(false);
            return;
        }

        const zappaiAccessToken = localStorage.getItem("zappaiAccessToken");
        await axios.get<ZappaiLocation>(`${import.meta.env.VITE_API_URL!}/api/locations/${locationId}`, {
            headers: {
                Authorization: `Bearer ${zappaiAccessToken}`
            }
        }).then((response) => {
            setLocation(response.data);
            setErrorMessage(null);
        }).catch((error) => {
            setErrorMessage(error.toString());
        });

        await axios.get<PredictionsResponse>(`${import.meta.env.VITE_API_URL!}/api/predictions`, {
            headers: {
                Authorization: `Bearer ${zappaiAccessToken}`
            },
            params: {
                crop_name: cropName,
                location_id: locationId
            }
        })
            .then((response) => {
                setPredictions(response.data);
                setErrorMessage(null);
                setIsLoading(false);
            })
            .catch((error) => {
                console.error('Error fetching predictions:', error);
                setErrorMessage(error.toString());
            });
    }

    useEffect(() => {
        loadData();
    }, []);

    const handleForecastChange = (event: SelectChangeEvent<{ value: unknown }>) => {
        setSelectedForecast(event.target.value as string);
    };

    // Mapping of climate variable keys to display names
    const displayNames: { [key: string]: string } = {
        temperature2M: 'Temperature (2m) [K]',
        totalPrecipitation: 'Total Precipitation [m]',
        surfaceSolarRadiationDownwards: 'Surface Solar Radiation Downwards [W/m²]',
        surfaceThermalRadiationDownwards: 'Surface Thermal Radiation Downwards [W/m²]',
        surfaceNetSolarRadiation: 'Surface Net Solar Radiation [W/m²]',
        surfaceNetThermalRadiation: 'Surface Net Thermal Radiation [W/m²]',
        totalCloudCover: 'Total Cloud Cover [%]',
        dewpointTemperature2M: 'Dewpoint Temperature (2m) [K]',
        soilTemperatureLevel3: 'Soil Temperature (Level 3) [K]',
        volumetricSoilWaterLayer3: 'Volumetric Soil Water (Layer 3) [m³/m³]',
    };

    // Descriptions for each climate variable
    const descriptions: { [key: string]: string } = {
        temperature2M: 'The temperature of the air at 2 meters above the surface of the Earth, measured in Kelvin (K).',
        totalPrecipitation: 'The total amount of precipitation (rain, snow, etc.) accumulated over time, measured in meters (m).',
        surfaceSolarRadiationDownwards: 'The total amount of solar radiation that reaches the surface of the Earth, measured in watts per square meter (W/m²).',
        surfaceThermalRadiationDownwards: 'The total thermal radiation emitted by the atmosphere towards the surface, measured in watts per square meter (W/m²).',
        surfaceNetSolarRadiation: 'The net balance of solar radiation at the surface, which is the incoming solar radiation minus the reflected portion, measured in watts per square meter (W/m²).',
        surfaceNetThermalRadiation: 'The net balance of thermal radiation at the surface, measured in watts per square meter (W/m²).',
        totalCloudCover: 'The fraction of the sky covered by clouds, measured as a percentage (%).',
        dewpointTemperature2M: 'The temperature at which air becomes saturated with moisture and dew begins to form, measured at 2 meters above the surface in Kelvin (K).',
        soilTemperatureLevel3: 'The temperature of the soil at level 3, which corresponds to a specific depth, measured in Kelvin (K).',
        volumetricSoilWaterLayer3: 'The amount of water in the soil at level 3, measured as the volume of water per volume of soil (m³/m³).',
    };

    return (
        <Box sx={{ width: "100%", height: "100%", display: "flex", overflow: "scroll", flexDirection: "column", justifyContent: "start", alignItems: "center", padding: 2 }}>
            {errorMessage !== null ? <Alert severity="error">{errorMessage}</Alert> : <></>}
            {isLoading
                ? <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexGrow: 1 }}>
                    <Typography variant='h4' gutterBottom>
                    Evaluating prediction...
                    </Typography>
                    <CircularProgress></CircularProgress>
                </Box>
                : <Box sx={{ padding: 2, width: "100%" }}>
                    {location && (
                        <Box sx={{ marginBottom: 4, textAlign: 'center' }}>
                            <Typography variant="h4" gutterBottom>
                                {location.name}, {location.country}
                            </Typography>
                            <Typography variant="h6" color="textSecondary">
                                Crop: {cropName}
                            </Typography>
                        </Box>
                    )}

                    <Typography variant="h5" gutterBottom>
                        Best Combinations
                    </Typography>
                    <TableContainer component={Paper} sx={{ marginBottom: 4 }}>
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Sowing Date</TableCell>
                                    <TableCell>Harvest Date</TableCell>
                                    <TableCell>Estimated Yield (tons/ha)</TableCell>
                                    <TableCell>Duration (months)</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {predictions!.bestCombinations.map((combination, index) => (
                                    <TableRow key={index}>
                                        <TableCell>{`${combination.sowingMonth}/${combination.sowingYear}`}</TableCell>
                                        <TableCell>{`${combination.harvestMonth}/${combination.harvestYear}`}</TableCell>
                                        {/* Round the estimated yield to the nearest integer */}
                                        <TableCell>{Math.round(combination.estimatedYieldPerHectar)}</TableCell>
                                        <TableCell>{combination.duration}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>

                    <Typography variant="h5" gutterBottom>
                        Climate Forecast
                    </Typography>

                    <Grid container spacing={2} alignItems="center" sx={{ marginBottom: 4 }}>
                        <Grid item xs={12} md={3}>
                            <Select title={selectedForecast} fullWidth value={selectedForecast as any} onChange={handleForecastChange}>
                                {/* Dynamically map display names for the forecast options */}
                                {Object.keys(displayNames).map((key) => (
                                    <MenuItem key={key} value={key}>
                                        {displayNames[key]}
                                    </MenuItem>
                                ))}
                            </Select>

                            {/* Display description of the selected forecast */}
                            <Typography variant="body1" sx={{ marginTop: 2 }}>
                                {descriptions[selectedForecast]}
                            </Typography>
                        </Grid>
                        <Grid item xs={12} md={9}>
                            <LineChart
                                series={[
                                    {
                                        data: predictions!.forecast.map(data => data[selectedForecast as keyof ClimateDataDetails])
                                    }
                                ]}
                                xAxis={[{ scaleType: "point", data: predictions!.forecast.map((data) => `${data.month}/${data.year}`) }]}
                                height={400}
                                sx={{ width: "100%" }}
                            />
                        </Grid>
                    </Grid>
                </Box>}
        </Box>
    );
};

export default PredictionPage;
