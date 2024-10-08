import React from 'react';
import { Card, CardContent, Typography, Button, Box, CircularProgress, IconButton } from '@mui/material';
import { Delete } from '@mui/icons-material';
import { ZappaiLocation } from '../utils/types';

interface LocationCardProps {
    location: ZappaiLocation;
    onDelete: (location: ZappaiLocation) => void;
    onDownloadData: (location: ZappaiLocation) => void;
    onMakePrediction: (location: ZappaiLocation) => void;  // Added this prop
}

const LocationCard: React.FC<LocationCardProps> = ({ location, onDelete, onDownloadData, onMakePrediction }) => {
    const {
        country,
        name,
        longitude,
        latitude,
        isModelReady,
        isDownloadingPastClimateData,
        lastPastClimateDataYear,
        lastPastClimateDataMonth,
    } = location;

    // Determine the "last updated" value
    const lastUpdated = lastPastClimateDataYear && lastPastClimateDataMonth
        ? `${lastPastClimateDataMonth}/${lastPastClimateDataYear}`
        : "never";

    return (
        <Card sx={{ position: 'relative' }}>
            {/* Delete Icon at the top right */}
            <IconButton
                aria-label="delete"
                onClick={() => onDelete(location)}
                sx={{ position: 'absolute', top: 8, right: 8 }}
            >
                <Delete />
            </IconButton>
            <CardContent>
                <Typography variant="h6">{name}</Typography>
                <Typography variant="subtitle1">{country}</Typography>
                <Typography variant="body2" color="text.secondary">
                    Coordinates: {`${latitude}, ${longitude}`}
                </Typography>
                <Typography variant="body2" color={isModelReady ? 'green' : 'red'}>
                    Weather AI model {isModelReady ? 'ready' : 'not ready'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Last past climate data: {lastUpdated}
                </Typography>
                <Box sx={{ display: "flex", flexDirection: "row", justifyContent: "space-between", alignItems: "center", mt: 2 }}>
                    {isDownloadingPastClimateData
                        ? <Box sx={{ display: "flex", flexDirection: "row", alignItems: "center" }}>
                            <CircularProgress sx={{ padding: 1, height: "16px" }} />
                            <Typography variant="body2" color="text.secondary">
                                Downloading data for AI model...
                            </Typography>
                        </Box>
                        : <Button
                            variant="contained"
                            color="primary"
                            onClick={() => onDownloadData(location)}
                        >
                            Download data and create AI model
                        </Button>}

                    {
                        isModelReady ?
                            <Button
                                variant="contained"
                                color="secondary"
                                onClick={() => onMakePrediction(location)}
                                sx={{ ml: 2 }}  // Adds some space between the buttons
                            >
                                Make Prediction
                            </Button>
                            : <></>
                    }

                </Box>
            </CardContent>
        </Card>
    );
};

export default LocationCard;
