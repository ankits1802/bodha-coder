import { logout } from "@/lib/api/auth";
import { SIGN_IN_PATH, urlFor } from "@/lib/api/client";

export type SignOutReason = "idle";

export async function signOut(reason: SignOutReason | null = null): Promise<void> {
  const destination = reason ? urlFor(SIGN_IN_PATH, { reason }) : SIGN_IN_PATH;
  try {
    await logout();
  } finally {
    window.location.replace(destination);
  }
}
