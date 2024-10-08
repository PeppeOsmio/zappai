import React, { useContext, useState } from 'react';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { Box, Menu, MenuItem } from '@mui/material';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Person } from '@mui/icons-material';
import { AuthContext } from './AuthProvider';
import { useTheme } from '@mui/material/styles';  // Import MUI theme hook

const Navbar: React.FC = () => {
    const authContext = useContext(AuthContext);
    const navigate = useNavigate();
    const location = useLocation();  // Hook to get current path
    const theme = useTheme();  // Access the MUI theme

    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
    const open = Boolean(anchorEl);

    // Function to determine if the button is active based on the current route
    const isActive = (path: string) => location.pathname === path;

    return (
        <AppBar position="static">
            <Toolbar sx={{ justifyContent: 'space-between' }}>
                <Typography variant="h6" sx={{ flexGrow: 0 }}>
                    <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
                        🌱⚡ ZappAI
                    </Link>
                </Typography>

                <Box sx={{ display: 'flex', gap: 2, flexGrow: 1, justifyContent: 'center' }}>
                    <Button 
                        color="inherit" 
                        component={Link} 
                        to="/locations"
                        sx={{ 
                            color: isActive('/locations') ? theme.palette.primary.main : 'inherit'
                        }}
                    >
                        Locations
                    </Button>
                    <Button 
                        color="inherit" 
                        component={Link} 
                        to="/users"
                        sx={{ 
                            color: isActive('/users') ? theme.palette.primary.main : 'inherit'
                        }}
                    >
                        Users
                    </Button>
                </Box>

                <Button 
                    color="inherit" 
                    onClick={(event) => {
                        setAnchorEl(event.currentTarget);
                    }} 
                    startIcon={<Person />}
                >
                    {authContext!.currentUser?.username}
                </Button>
                <Menu
                    anchorEl={anchorEl}
                    open={open}
                    onClose={() => {
                        setAnchorEl(null);
                    }}
                    anchorOrigin={{
                        vertical: 'bottom',
                        horizontal: 'right',
                    }}
                    transformOrigin={{
                        vertical: 'top',
                        horizontal: 'right',
                    }}
                >
                    <MenuItem onClick={() => {
                        localStorage.removeItem("zappaiAccessToken");
                        authContext!.setCurrentUser(null);
                        setAnchorEl(null);
                        navigate("/", { replace: true });
                    }}>Logout</MenuItem>
                </Menu>
            </Toolbar>
        </AppBar>
    );
};

export default Navbar;
