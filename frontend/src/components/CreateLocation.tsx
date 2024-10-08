import React, { useState, ChangeEvent, FormEvent } from 'react';
import { TextField, Button, Grid, Typography, Box, Alert } from '@mui/material';
import axios from 'axios';
import { ZappaiLocation } from '../utils/types';
import { useNavigate } from 'react-router-dom';

const LocationForm: React.FC = () => {
    const [country, setCountry] = useState<string>('');
    const [name, setName] = useState<string>('');
    const [longitude, setLongitude] = useState<string>('');
    const [latitude, setLatitude] = useState<string>('');

    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const navigate = useNavigate();

    const handleCountryChange = (e: ChangeEvent<HTMLInputElement>) => {
        setCountry(e.target.value);
    };

    const handleNameChange = (e: ChangeEvent<HTMLInputElement>) => {
        setName(e.target.value);
    };

    const handleLongitudeChange = (e: ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        if (Number(value) >= -180 && Number(value) <= 180) {
            setLongitude(value);
        } else {
            // Optionally, provide some feedback to the user that the value is out of bounds
            console.log('Longitude must be between -180 and 180');
        }
    };

    const handleLatitudeChange = (e: ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        if (Number(value) >= -90 && Number(value) <= 90) {
            setLatitude(value);
        } else {
            // Optionally, provide some feedback to the user that the value is out of bounds
            console.log('Latitude must be between -90 and 90');
        }
    };

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        const zappaiAccessToken = localStorage.getItem("zappaiAccessToken");
        axios.post<ZappaiLocation>(`${import.meta.env.VITE_API_URL!}/api/locations`,
            { country: country, name: name, longitude: longitude, latitude: latitude },
            {
                headers: {
                    Authorization: `Bearer ${zappaiAccessToken}`
                }
            }).then(() => {
                navigate("/locations");
            }).catch((error) => {
                console.log(error);
                setErrorMessage(error.toString());
            })
    };


    return (
        <Box sx={{ paddingTop: 2, paddingRight: 16, paddingLeft: 16, flexGrow: 1, width: "100%", display: "flex", flexDirection: "column" }}>
            {errorMessage !== null ? <Alert severity="error" style={{}}>{errorMessage}</Alert> : <></>}
            <Typography variant="h4" gutterBottom>
                Create Location
            </Typography>
            <form onSubmit={handleSubmit}>
                <Grid container spacing={2}>
                    <Grid item xs={12}>
                        <TextField
                            fullWidth
                            label="Country"
                            value={country}
                            onChange={handleCountryChange}
                            variant="outlined"
                            required
                        />
                    </Grid>
                    <Grid item xs={12}>
                        <TextField
                            fullWidth
                            label="Name"
                            value={name}
                            onChange={handleNameChange}
                            variant="outlined"
                            required
                        />
                    </Grid>
                    <Grid item xs={6}>
                        <TextField
                            fullWidth
                            label="Longitude"
                            value={longitude}
                            onChange={handleLongitudeChange}
                            variant="outlined"
                            required
                            type="number"
                            inputProps={{
                                min: -180,
                                max: 180,
                                step: "any", // Allowing decimal values
                            }}
                        />
                    </Grid>
                    <Grid item xs={6}>
                        <TextField
                            fullWidth
                            label="Latitude"
                            value={latitude}
                            onChange={handleLatitudeChange}
                            variant="outlined"
                            required
                            type="number"
                            inputProps={{
                                min: -90,
                                max: 90,
                                step: "any", // Allowing decimal values
                            }}
                        />
                    </Grid>
                    <Grid item xs={12}>
                        <Button type="submit" variant="contained" color="primary" fullWidth>
                            Create
                        </Button>
                    </Grid>
                </Grid>
            </form>
        </Box>
    );
};

export default LocationForm;
