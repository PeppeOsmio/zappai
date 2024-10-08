import { useContext, useEffect, useState } from "react";
import { AuthContext } from "./AuthProvider";
import { getUserInfo } from "../utils/utils";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Splash from "./Splash";
import Login from "./Login";
import { MainPage } from "./MainPage";

export default function App() {

    const authContext = useContext(AuthContext);

    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        getUserInfo().then((user) => {
            authContext!.setCurrentUser(user);
            setIsLoading(false);
        });
    }, []);

    return (
        isLoading
            ? <Splash />
            : <BrowserRouter>
                <Routes>
                    <Route path="/*" element={<MainPage />} />
                    <Route path="/login" element={<Login />} />
                </Routes>
            </BrowserRouter>
    );
}