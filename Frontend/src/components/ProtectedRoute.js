// components/ProtectedRoute.js
import React from "react";
import { Navigate, Outlet } from "react-router-dom";

export default function ProtectedRoute({ allowedRoles }) {
  const isAuthenticated = localStorage.getItem("loggedIn") === "true";
  const userRole = localStorage.getItem("userRole");

  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check if user has required role
  if (allowedRoles && !allowedRoles.includes(userRole)) {
    // Redirect to role-appropriate page
    switch (userRole) {
      case "candidate":
        return <Navigate to="/candidates" replace />;
      case "recruiter":
        return <Navigate to="/recruiters" replace />;
      case "admin":
        return <Navigate to="/collegeadmins" replace />;
      case "database_admin":
        return <Navigate to="/database-admin" replace />;
     default:
      break
    }
  }

  // User is authenticated and has required role
  return <Outlet />;
}
