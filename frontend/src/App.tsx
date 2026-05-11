import { useEffect, useState } from "react";

type CheckResult = { ok: boolean; error: string | null };
type HealthResponse = {
  status: "ok" | "degraded";
  service: string;
  version: string;
  checks: {
    database: CheckResult;
    redis: CheckResult;
  };
};

type FetchState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: HealthResponse };

export function App() {
  const [state, setState] = useState<FetchState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then(async (r) => {
        const body = (await r.json()) as HealthResponse;
        if (!cancelled) setState({ kind: "ready", data: body });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: err instanceof Error ? err.message : String(err),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="max-w-xl w-full space-y-6">
        <header className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">BarcodeLabelGen</h1>
          <p className="text-slate-400">
            Web label editor &amp; PDF batch generator — Sprint 0 skeleton
          </p>
        </header>

        <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="text-lg font-semibold mb-4">Backend health</h2>
          {state.kind === "loading" && <p className="text-slate-400">Sprawdzam…</p>}
          {state.kind === "error" && <p className="text-rose-400">Błąd: {state.message}</p>}
          {state.kind === "ready" && (
            <dl className="space-y-2 text-sm">
              <Row label="Service" value={state.data.service} />
              <Row label="Version" value={state.data.version} />
              <Row
                label="Status"
                value={
                  <span
                    className={state.data.status === "ok" ? "text-emerald-400" : "text-amber-400"}
                  >
                    {state.data.status}
                  </span>
                }
              />
              <Row label="Database" value={<CheckBadge check={state.data.checks.database} />} />
              <Row label="Redis" value={<CheckBadge check={state.data.checks.redis} />} />
            </dl>
          )}
        </section>

        <footer className="text-center text-xs text-slate-500">
          <code>https://HOST.TAILNET.ts.net:18003</code>
        </footer>
      </div>
    </main>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-400">{label}</dt>
      <dd className="font-mono">{value}</dd>
    </div>
  );
}

function CheckBadge({ check }: { check: CheckResult }) {
  return check.ok ? (
    <span className="text-emerald-400">ok</span>
  ) : (
    <span className="text-rose-400" title={check.error ?? ""}>
      failed
    </span>
  );
}
