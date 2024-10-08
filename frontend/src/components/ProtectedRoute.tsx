import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import {AuthContext} from "./AuthProvider";

interface ProtectedRouteProps {
    children: React.ReactNode
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {

    const authContext = useContext(AuthContext);

    if (authContext!.currentUser === null) {
        // If user is not authenticated, redirect to /login
        return <Navigate to="/login" replace />;
    }

    // If user is authenticated, render the children components (protected content)
    return children;
}

export default ProtectedRoute;
