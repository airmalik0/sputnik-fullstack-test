/**
 * App-level providers.
 *
 * QueryClient is built once and exposed to the whole tree. Defaults
 * are tuned for a single-page admin tool:
 *
 *   - staleTime 0: data is considered stale immediately, so a focus
 *     event triggers a refetch. We're operating on a small dataset
 *     where freshness matters more than network thrift.
 *   - retry 1: don't hammer a flaky backend; surface errors fast so
 *     the operator can react.
 *   - refetchOnWindowFocus true (the default): leaving the tab and
 *     coming back gives a free refresh.
 */

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  // Lazily initialise inside state so a single client is used for the
  // lifetime of the component tree, even across HMR reloads in dev.
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 0,
            retry: 1,
            refetchOnWindowFocus: true,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
