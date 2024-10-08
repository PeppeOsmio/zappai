import axios, { AxiosError } from "axios";
import { User } from "./types";

interface GetUserInfoResponse {
    id: string;
    username: string;
}

export async function getUserInfo(): Promise<User | null> {
    try {
        const token = localStorage.getItem('zappaiAccessToken');
        if (token === null) {
            return null;
        }
        const result = await axios.get<GetUserInfoResponse>(`${import.meta.env.VITE_API_URL!}/api/auth/me`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });
        return { id: result.data.id, username: result.data.username };
    } catch (error) {
        if (axios.isAxiosError(error)) {
            const axiosError = error as AxiosError;
            if (axiosError.status === 401) {
                return null;
            }
        }
        throw error;
    }
}