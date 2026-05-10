import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { z } from "zod";
import { toast } from "sonner";
import {
  ClipboardCheck,
  Lock,
  ScanSearch,
  ShieldCheck,
  Network,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

import { apiClient, type ApiError } from "@/lib/apiClient";
import { useAuthStore, type UserSelf } from "@/stores/auth";
import type { components } from "@/types/api";

type TokenResponse = components["schemas"]["TokenResponse"];

const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});
type LoginValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const status = useAuthStore((s) => s.status);
  const setSession = useAuthStore((s) => s.setSession);
  const setToken = useAuthStore((s) => s.setToken);
  const clearSession = useAuthStore((s) => s.clearSession);

  const [submitting, setSubmitting] = useState(false);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  // Already signed in → don't show the form, bounce to the intended
  // destination (or the dashboard).
  if (status === "authenticated") {
    const from = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  async function onSubmit(values: LoginValues) {
    setSubmitting(true);
    try {
      const tokenResp = await apiClient.post<TokenResponse>(
        "/auth/login",
        values,
      );
      const token = tokenResp.data.access_token;
      // Stage the token so the request interceptor attaches it on /me.
      setToken(token);
      const meResp = await apiClient.get<UserSelf>("/auth/me");
      setSession(token, meResp.data);

      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 401) {
        form.setError("password", {
          type: "server",
          message: apiErr.detail || "Invalid username or password.",
        });
      } else {
        toast.error(apiErr.detail || "Could not sign in. Please try again.");
      }
      clearSession();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-[#070b14] text-slate-100">
      <BackgroundGrid />
      <BackgroundGlows />

      <div className="relative grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
        {/* ─── Left: identity + architecture ────────────────────────────── */}
        <section className="hidden lg:flex flex-col justify-between px-12 xl:px-20 py-12">
          <BrandChip />

          <div className="max-w-xl">
            <p className="text-xs uppercase tracking-[0.2em] text-blue-400/80 font-medium">
              Security operations platform
            </p>
            <h1 className="mt-4 text-5xl xl:text-6xl font-semibold tracking-tight text-slate-50 leading-[1.05]">
              PA Platform
            </h1>
            <p className="mt-6 text-lg text-slate-300 leading-relaxed">
              Detect vulnerabilities with Wazuh, remediate them through
              approved AWX playbooks, and verify every fix — with full
              RBAC and an append-only audit trail.
            </p>

            <div className="mt-10 grid grid-cols-2 gap-3 max-w-md">
              <ArchitectureCard
                icon={ScanSearch}
                title="Wazuh detection"
                body="Continuous CVE inventory across every monitored agent."
              />
              <ArchitectureCard
                icon={Wrench}
                title="AWX remediation"
                body="Approved playbooks only — never ad-hoc shell."
              />
              <ArchitectureCard
                icon={ShieldCheck}
                title="Audit & RBAC"
                body="Per-action authorization with full audit history."
              />
              <ArchitectureCard
                icon={Network}
                title="Enterprise security"
                body="Asset scope, approval workflow, separation of duties."
              />
            </div>
          </div>

          <p className="text-xs text-slate-500 font-mono">
            v0.1 · Internal build
          </p>
        </section>

        {/* ─── Right: sign-in card ──────────────────────────────────────── */}
        <section className="flex items-center justify-center px-6 py-10 lg:border-l lg:border-slate-800/60">
          <div className="w-full max-w-sm">
            {/* Mobile-only brand header — left column is hidden below lg. */}
            <div className="lg:hidden mb-8">
              <BrandChip />
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-8 shadow-xl shadow-black/30">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-500/40 bg-blue-500/10">
                  <Lock className="h-4 w-4 text-blue-400" />
                </span>
                <div>
                  <h2 className="text-xl font-semibold tracking-tight text-slate-50">
                    Sign in
                  </h2>
                  <p className="text-xs text-slate-400 uppercase tracking-wider">
                    Secure access only
                  </p>
                </div>
              </div>

              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className="mt-6 space-y-4"
                  noValidate
                >
                  <FormField
                    control={form.control}
                    name="username"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs uppercase tracking-wider text-slate-400">
                          Username
                        </FormLabel>
                        <FormControl>
                          <Input
                            autoComplete="username"
                            autoFocus
                            disabled={submitting}
                            className="h-10 bg-slate-950/60 border-slate-800 focus-visible:border-blue-500 focus-visible:ring-blue-500/30"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage className="text-xs" />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs uppercase tracking-wider text-slate-400">
                          Password
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            autoComplete="current-password"
                            disabled={submitting}
                            className="h-10 bg-slate-950/60 border-slate-800 focus-visible:border-blue-500 focus-visible:ring-blue-500/30"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage className="text-xs" />
                      </FormItem>
                    )}
                  />

                  <Button
                    type="submit"
                    className="w-full h-10 mt-2 bg-blue-500 hover:bg-blue-400 text-slate-950 font-medium"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <span className="inline-flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full border-2 border-slate-950/40 border-t-slate-950 animate-spin" />
                        Signing in…
                      </span>
                    ) : (
                      "Sign in"
                    )}
                  </Button>
                </form>
              </Form>

              <p className="mt-5 text-[11px] text-slate-500 leading-relaxed">
                Access is restricted to authorized operators. Sessions are
                ephemeral and scoped to this browser tab.
              </p>
            </div>

            <FooterAuditBadge />
          </div>
        </section>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */

function BrandChip() {
  return (
    <div className="flex items-center gap-3">
      <span className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 shadow-lg shadow-blue-500/30">
        <ShieldCheck className="h-5 w-5 text-slate-950" />
        <span
          aria-hidden
          className="absolute inset-0 rounded-xl ring-1 ring-white/20"
        />
      </span>
      <div className="leading-tight">
        <div className="text-sm font-semibold tracking-tight text-slate-50">
          PA Platform
        </div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
          Operator console
        </div>
      </div>
    </div>
  );
}

interface ArchCardProps {
  icon: LucideIcon;
  title: string;
  body: string;
}
function ArchitectureCard({ icon: Icon, title, body }: ArchCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 hover:border-slate-700 hover:bg-slate-900/70 transition-colors">
      <span className="flex h-8 w-8 items-center justify-center rounded-md border border-blue-500/30 bg-blue-500/10 text-blue-400">
        <Icon className="h-4 w-4" />
      </span>
      <div className="mt-3 text-sm font-medium text-slate-100">{title}</div>
      <div className="mt-0.5 text-xs text-slate-400 leading-snug">{body}</div>
    </div>
  );
}

function FooterAuditBadge() {
  return (
    <div className="mt-6 flex items-center justify-center gap-2 text-[11px] text-slate-500">
      <ClipboardCheck className="h-3.5 w-3.5 text-emerald-500/70" />
      <span>Audit logging enabled</span>
      <span aria-hidden className="h-1 w-1 rounded-full bg-slate-700" />
      <span className="font-mono">all events recorded</span>
    </div>
  );
}

/**
 * Subtle moving grid for the dark backdrop. Two layers — one fixed,
 * one that drifts diagonally — give the cybersecurity-console feel
 * without distracting from the form. Both layers are
 * `pointer-events-none` so they never eat clicks.
 */
function BackgroundGrid() {
  return (
    <>
      <style>{`
        @keyframes pa-grid-drift {
          from { background-position: 0 0; }
          to   { background-position: 48px 48px; }
        }
      `}</style>
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #ffffff 1px, transparent 1px)," +
            "linear-gradient(to bottom, #ffffff 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #38bdf8 1px, transparent 1px)," +
            "linear-gradient(to bottom, #38bdf8 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          animation: "pa-grid-drift 20s linear infinite",
        }}
      />
      {/* Edge fade so the grid melts away at the top/bottom rather
          than running edge-to-edge like a spreadsheet. */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 30%, #070b14 90%)",
        }}
      />
    </>
  );
}

function BackgroundGlows() {
  return (
    <div
      aria-hidden
      className="absolute inset-0 pointer-events-none"
      style={{
        background:
          "radial-gradient(45% 40% at 22% 30%, rgba(59,130,246,0.18) 0%, rgba(7,11,20,0) 65%)," +
          "radial-gradient(45% 35% at 80% 78%, rgba(34,211,238,0.10) 0%, rgba(7,11,20,0) 70%)",
      }}
    />
  );
}
