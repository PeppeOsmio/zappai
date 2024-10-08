import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
    Container,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    CircularProgress,
    Typography,
    TextField,
} from '@mui/material';

// Define the interface for the user data
interface UserDetailsResponse {
    id: string;
    username: string;
    name: string;
    createdAt: string;
    email?: string | null;
}

const UsersPage: React.FC = () => {
    const [users, setUsers] = useState<UserDetailsResponse[]>([]);
    const [filteredUsers, setFilteredUsers] = useState<UserDetailsResponse[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState<string>('');

    useEffect(() => {
        const fetchUsers = async () => {
            const zappaiAccessToken = localStorage.getItem("zappaiAccessToken");
            try {
                setLoading(true);
                const response = await axios.get<UserDetailsResponse[]>(`${import.meta.env.VITE_API_URL!}/api/users`, {
                    headers: {
                        Authorization: `Bearer ${zappaiAccessToken}`
                    }
                }); // Replace with your actual API endpoint
                setUsers(response.data);
                setFilteredUsers(response.data); // Initialize filtered users with all users
            } catch (err) {
                setError('Failed to load users');
            } finally {
                setLoading(false);
            }
        };

        fetchUsers();
    }, []);

    useEffect(() => {
        const lowerCaseQuery = searchQuery.toLowerCase();
        const filtered = users.filter((user) =>
            user.username.toLowerCase().includes(lowerCaseQuery) ||
            user.name.toLowerCase().includes(lowerCaseQuery) ||
            (user.email && user.email.toLowerCase().includes(lowerCaseQuery))
        );
        setFilteredUsers(filtered);
    }, [searchQuery, users]);

    // Format date in a user-friendly way
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    };

    return (
        <Container sx={{ marginTop: 4, marginLeft: 16, marginRight: 16 }}>

            <TextField
                label="Search Users"
                variant="outlined"
                fullWidth
                margin="normal"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
            />

            {loading ? (
                <CircularProgress />
            ) : error ? (
                <Typography color="error">{error}</Typography>
            ) : (
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>ID</TableCell>
                                <TableCell>Username</TableCell>
                                <TableCell>Name</TableCell>
                                <TableCell>Created At</TableCell>
                                <TableCell>Email</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {filteredUsers.length > 0 ? (
                                filteredUsers.map((user) => (
                                    <TableRow key={user.id}>
                                        <TableCell>{user.id}</TableCell>
                                        <TableCell>{user.username}</TableCell>
                                        <TableCell>{user.name}</TableCell>
                                        <TableCell>{formatDate(user.createdAt)}</TableCell>
                                        <TableCell>{user.email || 'N/A'}</TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={5} align="center">
                                        No users found
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}
        </Container>
    );
};

export default UsersPage;
