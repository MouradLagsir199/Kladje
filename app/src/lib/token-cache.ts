import type { TokenCache } from "@clerk/clerk-expo";
import * as SecureStore from "expo-secure-store";

// Keychain/Keystore-backed, per Clerk's own recommendation for Expo — a different
// concern from the MMKV query cache (docs/05-client.md): this holds the session
// token itself, not app data.
export const tokenCache: TokenCache = {
  async getToken(key) {
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      return null;
    }
  },
  async saveToken(key, value) {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch {
      // SecureStore can fail on some devices — the session just won't persist across restarts.
    }
  },
  async clearToken(key) {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch {
      // no-op
    }
  },
};
