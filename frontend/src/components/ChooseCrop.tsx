import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Typography, Grid, Card, CardContent, CardMedia, Button, Box, CardActionArea, Alert, CircularProgress } from '@mui/material';
import { Crop, ZappaiLocation } from '../utils/types';
import axios from 'axios';

const cropPhotoMap = new Map<string, string>([
    ['sunflower', '/images/crops/sunflower.png'],
    ['soybean', '/images/crops/soybean.png'],
    ['barley', '/images/crops/barley.png'],
    ['sorghum', '/images/crops/sorghum.png'],
    ['rice', '/images/crops/rice.png'],
    ['maize', '/images/crops/maize.png'],
    ['wheat', '/images/crops/wheat.png'],
    ['cotton', '/images/crops/cotton.png'],
]);

const ChooseCrop: React.FC = () => {
    const { locationId } = useParams<{ locationId: string }>();

    const navigate = useNavigate();

    const [location, setLocation] = useState<ZappaiLocation | null>(null);
    const [crops, setCrops] = useState<Crop[] | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // State to keep track of the selected crop
    const [selectedCrop, setSelectedCrop] = useState<string | null>(null);

    const loadData = async () => {
        const zappaiAccessToken = localStorage.getItem("zappaiAccessToken");

        await axios.get<Crop[]>(`${import.meta.env.VITE_API_URL!}/api/crops`, {
            headers: {
                Authorization: `Bearer ${zappaiAccessToken}`
            }
        }).then((response) => {
            setCrops(response.data);
            setErrorMessage(null);
        }).catch((error) => {
            setErrorMessage(error.toString());
        });

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

        setIsLoading(false);
    }

    useEffect(() => {
        loadData();
    }, [])

    const handleCardClick = (cropName: string) => {
        setSelectedCrop(cropName);
    };

    const handleMakePrediction = () => {
        navigate(`/predictions?locationId=${locationId}&cropName=${selectedCrop}`);
    };

    return (
        <Box sx={{ width: "100%", height: "100%", display: "flex", overflow: "scroll", flexDirection: "column", justifyContent: "start", alignItems: "center", paddingLeft: 16, paddingRight: 16, paddingTop: 2 }}>
            {errorMessage !== null ? <Alert severity="error" style={{}}>{errorMessage}</Alert> : <></>}
            {
                isLoading
                    ? <Box sx={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "center", flexGrow: 1 }}>
                        <CircularProgress sx={{}}></CircularProgress>
                    </Box>
                    : <>
                        <Typography variant="h4" sx={{ marginBottom: 4 }}>
                            Choose a crop to make predictions for location "{location!.name}, {location!.country}"
                        </Typography>
                        <Grid container spacing={2}>
                            {crops!.map((crop) => (
                                <Grid item key={crop.name}>
                                    <Card
                                        sx={{
                                            boxShadow: selectedCrop === crop.name ? '0 0 16px #1976d2' : 'none',
                                            transition: 'border 0.3s, box-shadow 0.3s',
                                        }}
                                    >
                                        <CardActionArea onClick={() => handleCardClick(crop.name)}>
                                            <CardMedia
                                                component="img"
                                                image={cropPhotoMap.get(crop.name)}
                                                sx={{
                                                    height: "256px"
                                                }}
                                                alt={crop.name}
                                            />
                                            <CardContent>
                                                <Typography variant="h6" gutterBottom>
                                                    {crop.name}
                                                </Typography>
                                            </CardContent>
                                        </CardActionArea>
                                    </Card>
                                </Grid>
                            ))}
                        </Grid>
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleMakePrediction}
                            disabled={!selectedCrop}  // Disable the button if no crop is selected
                            sx={{ position: 'fixed', bottom: '32px', right: '32px' }}
                        >
                            Make Prediction
                        </Button>
                    </>
            }
        </Box>
    );
};

export default ChooseCrop;
