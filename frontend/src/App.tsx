import { Route, Routes } from "react-router-dom";

import LandingPage from "./pages/LandingPage";
import RoomPage from "./pages/RoomPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/room/:code" element={<RoomPage />} />
    </Routes>
  );
}
