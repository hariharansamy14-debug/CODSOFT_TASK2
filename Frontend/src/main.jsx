import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "./styles/theme.css";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";

// WHY AuthProvider WRAPS EVERYTHING:
// Almost every page needs to know "who is logged in?" and "do I have a
// valid token?". Putting that state in a Context at the very top means any
// component, no matter how deeply nested, can read it with one hook call
// (`useAuth()`) instead of passing the user down through 10 layers of props
// ("prop drilling").
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
