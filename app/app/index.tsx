import { Redirect } from "expo-router";

// `/` has no screen of its own: signed-in users land on the first tab. The auth gate in
// `_layout.tsx` sends signed-out users to (auth) before this ever renders.
export default function Index() {
  return <Redirect href="/ontdek" />;
}
