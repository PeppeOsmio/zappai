import { Typography } from "@mui/material";
import React from "react";

const Splash: React.FC = () => {
    console.log("In the splashhh");
    
    return <div style={{ display: "flex", width: "100vw", height: "100vh", justifyContent: "center", alignItems: "center" }}>
        <Typography variant="h1" component="h1">
            🌱⚡
        </Typography>
    </div>
}

export default Splash;