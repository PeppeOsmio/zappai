import { Alert, Button, CircularProgress, TextField, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";

import { Box, Grid } from '@mui/material';
import { ZappaiLocation } from "../utils/types";
import LocationCard from "./LocationCard";
import axios from "axios";
import { Add } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";


interface LocationsProps {
}

const Locations: React.FC<LocationsProps> = () => {

    const [locations, setLocations] = useState<ZappaiLocation[]>([]);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const [filteredLocations, setFilteredLocations] = useState<ZappaiLocation[]>([]);
    const [searchQuery, setSearchQuery] = useState("");

    const navigate = useNavigate();

    const updateLocations = async (isActive: () => boolean) => {
        const zappaiAccessToken = localStorage.getItem("zappaiAccessToken");
        while (isActive()) {
            await axios.get<ZappaiLocation[]>(`${import.meta.env.VITE_API_URL!}/api/locations`, {
                headers: {
                    "Authorization": `Bearer ${zappaiAccessToken}`
                }
            }).then((response) => {

                setLocations(response.data);
            }).catch((error) => {
                console.log(error);
                setErrorMessage(error.toString());
            });
            setIsLoading(false);
            await new Promise((resolve) => setTimeout(resolve, 30000));
        }
    }

    useEffect(() => {
        let isMounted = true;

        const isActive = () => isMounted;

        updateLocations(isActive);

        return () => {
            isMounted = false; // Cleanup function to stop the loop
        };
    }, []);

    useEffect(() => {
        if (locations === null) {
            return
        }
        const lowerCaseQuery = searchQuery.toLowerCase();
        const filtered = locations.filter((location) =>
            location.country.toLowerCase().includes(lowerCaseQuery) ||
            location.name.toLowerCase().includes(lowerCaseQuery) ||
            location.latitude.toString().includes(lowerCaseQuery) ||
            location.longitude.toString().includes(lowerCaseQuery)
        );
        setFilteredLocations(filtered);
    }, [searchQuery, locations]);

    const onDeleteLocation = (location: ZappaiLocation) => {
        const zappaiAccessToken = localStorage.getItem("zappaiAccessToken");
        axios.delete(`${import.meta.env.VITE_API_URL!}/api/locations/${location.id}`, { headers: { Authorization: `Bearer ${zappaiAccessToken}` } })
            .then(
                () => {
                    setLocations(old => old?.filter(loc => loc.id !== location.id) ?? null);
                    setErrorMessage(null);
                }
            )
            .catch((error) => setErrorMessage(error.toString()));
    }

    const onDownloadData = (location: ZappaiLocation) => {
        const zappaiAccessToken = localStorage.getItem("zappaiAccessToken");
        axios.get(`${import.meta.env.VITE_API_URL!}/api/locations/past_climate_data/${location.id}`, { headers: { Authorization: `Bearer ${zappaiAccessToken}` } })
            .then(
                () => {
                    setLocations(old => old?.map((loc) => {
                        if (loc.id !== location.id) {
                            return loc;
                        }
                        loc.isDownloadingPastClimateData = true;
                        return loc;
                    }) ?? null);
                    setErrorMessage(null);
                }
            )
            .catch((error) => setErrorMessage(error.toString()));
    }

    const onMakePrediction = (location: ZappaiLocation) => {
        navigate(`/predictions/create/${location.id}`);
    }

    return <Box sx={{ paddingTop: 2, paddingRight: 16, paddingLeft: 16, overflow: "scroll", flexGrow: 1, width: "100%", height: "100%", display: "flex", flexDirection: "column", gap: 2 }}>
        {errorMessage !== null ? <Alert severity="error" style={{}}>{errorMessage}</Alert> : <></>}
        {
            isLoading
                ? <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexGrow: 1 }}>
                    <CircularProgress sx={{}}></CircularProgress>
                </Box>
                : locations.length > 0
                    ? <Grid container spacing={2}>
                        <TextField
                            label="Search Locations"
                            variant="outlined"
                            fullWidth
                            margin="normal"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        {filteredLocations.map((location, index) => (
                            <Grid item xs={12} sm={6} key={index}>
                                <LocationCard
                                    location={location}
                                    onDelete={onDeleteLocation}
                                    onDownloadData={onDownloadData}
                                    onMakePrediction={onMakePrediction}
                                />
                            </Grid>
                        ))}
                    </Grid>
                    : <Box sx={{ display: "flex", flexDirection: "column", flexGrow: 1, justifyContent: "center", alignItems: "center" }}>
                        <Typography variant="h4">
                            There's no locations yet. Create one!
                        </Typography>
                    </Box>
        }
        <Button
            variant="contained"
            color="primary"
            sx={{
                mt: 2, position: 'fixed',
                bottom: '32px',
                right: '32px'
            }}
            startIcon={<Add />}
            onClick={() => navigate("/locations/create")}>
            Create a Location
        </Button>
    </Box>
}

export default Locations;