/**
 * Tests for the OAuth redirect URL logic in authStore.
 *
 * Verifies that the redirectTo URL is always built from the *current* origin
 * (window.location.origin) so that it works correctly in both local development
 * and production environments.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Supabase mock
const mockSignInWithOAuth = vi.fn();

vi.mock("../lib/supabase", () => ({
  isSupabaseConfigured: true,
  supabase: {
    auth: {
      signInWithOAuth: mockSignInWithOAuth,
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
    },
  },
}));

function mockWindowOrigin(origin: string) {
  Object.defineProperty(window, "location", {
    writable: true,
    value: { origin },
  });
}

describe("authStore - OAuth redirectTo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSignInWithOAuth.mockResolvedValue({ error: null });
  });

  afterEach(() => {
    mockWindowOrigin("http://localhost:3000");
  });

  it("uses window.location.origin for the redirectTo URL in local development", async () => {
    mockWindowOrigin("http://localhost:5173");
    const { useAuthStore } = await import("./authStore");
    await useAuthStore.getState().loginWithOAuth("google");
    expect(mockSignInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: "http://localhost:5173/auth/callback" },
    });
  });

  it("uses window.location.origin for the redirectTo URL in production", async () => {
    mockWindowOrigin("https://kai-code-studio-h83nbpgfj-kiran08461kumar-9455s-projects.vercel.app");
    const { useAuthStore } = await import("./authStore");
    await useAuthStore.getState().loginWithOAuth("google");
    expect(mockSignInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: {
        redirectTo: "https://kai-code-studio-h83nbpgfj-kiran08461kumar-9455s-projects.vercel.app/auth/callback",
      },
    });
  });

  it("never uses a hardcoded 127.0.0.1 address for the redirect", async () => {
    mockWindowOrigin("https://example.vercel.app");
    const { useAuthStore } = await import("./authStore");
    await useAuthStore.getState().loginWithOAuth("github");
    const [[callArg]] = mockSignInWithOAuth.mock.calls;
    expect(callArg.options.redirectTo).not.toContain("127.0.0.1");
  });
});
