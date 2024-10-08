import { Alert, Button, TextField, Typography } from "@mui/material";
import axios, { AxiosError } from "axios";
import React, { useContext, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getUserInfo } from "../utils/utils";
import { AuthContext } from "./AuthProvider";


interface LoginResponse {
    access_token: string
}

const Login: React.FC = () => {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const navigate = useNavigate();

    const authContext = useContext(AuthContext);

    return <div style={{ width: "100vw", height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "16px" }}>

            <Typography variant='h3' component="h3" style={{ marginBottom: "16px" }}>
                Welcome to 🌱⚡ ZappAI
            </Typography>

            {errorMessage !== null ? <Alert severity="error" style={{ width: "100%" }}>{errorMessage}</Alert> : <></>}

            <TextField label="Username" placeholder='John Doe' type="email" style={{ width: "100%" }} defaultValue={username} onBlur={(event) => setUsername(event.currentTarget.value)}>
            </TextField>
            <TextField label="Password" type='password' placeholder='ComplexPassword!' style={{ width: "100%" }} defaultValue={password} onBlur={(event) => setPassword(event.currentTarget.value)}>
            </TextField>

            <Button variant='contained' style={{ width: "100%" }} onClick={async () => {
                if (username.trim() === "" || password.trim() === "") {
                    return;
                }
                try {
                    const response = await axios.post<LoginResponse>(`${import.meta.env.VITE_API_URL}/api/auth/`, new URLSearchParams({ username: username, password: password }));
                    localStorage.setItem('zappaiAccessToken', response.data.access_token);
                    const user = await getUserInfo();
                    authContext!.setCurrentUser(user);
                    // set user to inform main component to display nav bar
                    navigate("/locations");
                } catch (error) {
                    if (axios.isAxiosError(error)) {
                        const axiosError = error as AxiosError;
                        if (axiosError.status === 401) {
                            setErrorMessage("Invalid credentials")
                        } else {
                            setErrorMessage(`Error ${axiosError.status}: "${axiosError.message}"`);
                        }
                    } else {
                        setErrorMessage((error as Error).toString());
                    }
                    return;
                }
                setErrorMessage(null);
            }}>Login</Button>

        </div>
    </div>
}

export default Login;