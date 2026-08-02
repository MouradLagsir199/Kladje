import { useEffect } from "react";
import * as WebBrowser from "expo-web-browser";

// Pre-warms Android's Custom Tabs so the OAuth browser opens without a visible
// delay — Clerk's documented recommendation for the Expo SSO flow.
export function useWarmUpBrowser() {
  useEffect(() => {
    void WebBrowser.warmUpAsync();
    return () => {
      void WebBrowser.coolDownAsync();
    };
  }, []);
}
