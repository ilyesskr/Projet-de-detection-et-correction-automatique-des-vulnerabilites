import { QueryClientProvider } from "@tanstack/react-query";

import AppRouter from "@/router/AppRouter";
import { Toaster } from "@/components/ui/sonner";
import { queryClient } from "@/lib/queryClient";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRouter />
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  );
}

export default App;
