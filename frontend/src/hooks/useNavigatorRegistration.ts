import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { registerNavigator } from "@/lib/navigation";

/**
 * Hand React Router's `navigate` to the apiClient's 401 interceptor so
 * it can SPA-navigate to /login instead of falling back to a hard
 * `window.location` reload.
 */
export function useNavigatorRegistration(): void {
  const navigate = useNavigate();
  useEffect(() => {
    registerNavigator(navigate);
  }, [navigate]);
}
