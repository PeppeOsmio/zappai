import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom';
import NavBar from './NavBar';
import ProtectedRoute from './ProtectedRoute';
import Locations from './Locations';
import { Box } from '@mui/material';
import CreateLocation from './CreateLocation';
import ChooseCrop from './ChooseCrop';
import PredictionPage from './PredictionPage';
import UsersList from './UsersList';

export const MainPage: React.FC = () => {
    return (
        <Box sx={{width: "100vw", height: "100vh", display: "flex", flexDirection: "column", justifyContent: "start", alignItems: "center"}}>
            <NavBar />
            <Routes>
                <Route path="/locations" element={
                    <ProtectedRoute>
                        <Locations />
                    </ProtectedRoute>
                } />
                <Route path="/locations/create" element={<CreateLocation/>}/>
                <Route path="/predictions/create/:locationId" element={
                    <ProtectedRoute>
                        <ChooseCrop />
                    </ProtectedRoute>
                } />
                <Route path="/predictions" element={<PredictionPage/>}/>
                <Route path="/users" element={
                    <ProtectedRoute>
                        <UsersList />
                    </ProtectedRoute>
                } />
                <Route path="/" element={<Navigate to="/locations" />} />
            </Routes>
        </Box>
    )
}
