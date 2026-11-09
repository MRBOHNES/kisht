"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ManagerNav } from "@/components/ManagerNav";
import { useLang } from "@/lib/i18n";

type ImportResult = {
  file_name: string;
  file_size: number;
  rows: number;
  imported: number;
  not_imported: number;
  assigned: number;
  cured: number;
  errors: { row: number; loan_id: string; field: string; message: string; fix: string }[];
  assignment: { officer_id: number; officer_name: string; branch: string; pincodes: string[]; open_loans: number; new_in_import: number }[];
};

const SAMPLES = ["overdue-sample.csv", "overdue-with-errors.csv"];

export default function ImportPage() {
  const { t } = useLang();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);

  async function upload(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      // not the JSON helper: the browser must set the multipart boundary itself
      const response = await fetch("/api/imports", { method: "POST", body: form });
      if (response.status === 401) {
        router.replace("/manager/login");
        return;
      }
      const body = await response.json();
      if (!response.ok) setError(importError(response.status, body.detail));
      else setResult(body);
    } catch {
      setError(t("errNetwork"));
    } finally {
      setBusy(false);
    }
  }

  function importError(status: number, detail: { code?: string; columns?: string[] } | undefined) {
    if (detail?.code === "missing_columns") return t("importErrMissing", { cols: (detail.columns ?? []).join(", ") });
    if (detail?.code === "empty_file") return t("importErrEmpty");
    if (detail?.code === "file_too_large" || status === 413) return t("importErrTooLarge");
    if (detail?.code === "not_utf8") return t("importErrEncoding");
    return t("errGeneric");
  }

  const maxOpen = Math.max(1, ...(result?.assignment.map((a) => a.open_loans) ?? [1]));

  return (
    <>
      <ManagerNav />
      <main className="mx-auto flex max-w-6xl flex-col gap-4 p-4">
        <h1 className="text-xl font-semibold">{t("importTitle")}</h1>
        <form onSubmit={upload} className="card flex flex-col gap-3 p-4">
          <p className="text-sm text-muted">{t("importHelp")}</p>
          <label className="flex min-h-12 cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-line px-4 text-sm font-medium text-accent">
            {file ? `${file.name} · ${Math.max(1, Math.round(file.size / 1024))} KB` : t("chooseFile")}
            <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <button type="submit" disabled={!file || busy} className="min-h-12 rounded-xl bg-accent font-medium text-white disabled:opacity-40">
            {busy ? t("uploading") : t("upload")}
          </button>
          {error && <p role="alert" className="rounded-xl bg-red-bg p-3 text-sm text-red">{error}</p>}
          <p className="text-sm text-muted">
            {t("sampleFiles")}:{" "}
            {SAMPLES.map((name, i) => (
              <span key={name}>
                {i > 0 && " · "}
                <a href={`/sample-data/${name}`} download className="inline-flex min-h-12 items-center text-accent underline">{name}</a>
              </span>
            ))}
          </p>
        </form>

        {!result && !busy && <p className="card p-6 text-center text-sm text-muted">{t("importEmpty")}</p>}
        {busy && <div className="h-32 animate-pulse rounded-2xl bg-line" aria-hidden />}
        {result && !busy && (
          <>
            <section className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <Kpi label={t("kRows")} value={result.rows} />
              <Kpi label={t("kImported")} value={result.imported} tone="text-green" />
              <Kpi label={t("kNotImported")} value={result.not_imported} tone={result.not_imported ? "text-red" : ""} />
              <Kpi label={t("kCured")} value={result.cured} />
              <Kpi label={t("kAssigned")} value={result.assigned} />
            </section>

            {result.errors.length > 0 && (
              <section className="card overflow-x-auto p-4">
                <h2 className="font-semibold">{t("errorsTitle")} ({result.not_imported})</h2>
                <table className="mt-2 w-full text-left text-sm">
                  <thead className="text-xs text-muted">
                    <tr><th className="py-2 pr-3">{t("colRow")}</th><th className="pr-3">Loan</th><th className="pr-3">{t("colField")}</th><th className="pr-3">{t("colProblem")}</th><th>{t("colFix")}</th></tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {result.errors.map((e, i) => (
                      <tr key={i}>
                        <td className="py-2 pr-3">{e.row}</td>
                        <td className="pr-3">{e.loan_id || "–"}</td>
                        <td className="pr-3 font-mono text-xs">{e.field}</td>
                        <td className="pr-3 text-red">{e.message}</td>
                        <td>{e.fix}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}

            <section className="card overflow-x-auto p-4">
              <h2 className="font-semibold">{t("assignTitle")}</h2>
              <table className="mt-2 w-full text-left text-sm">
                <thead className="text-xs text-muted">
                  <tr><th className="py-2 pr-3">{t("colOfficer")}</th><th className="pr-3">{t("colBranch")}</th><th className="pr-3">{t("colPincodes")}</th><th className="pr-3">{t("colNew")}</th><th>{t("colOpen")}</th></tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {result.assignment.map((a) => (
                    <tr key={a.officer_id}>
                      <td className="py-2 pr-3 font-medium">{a.officer_name}</td>
                      <td className="pr-3">{a.branch}</td>
                      <td className="pr-3 text-xs">{a.pincodes.join(", ")}</td>
                      <td className="pr-3">{a.new_in_import}</td>
                      <td className="min-w-40">
                        <div className="flex items-center gap-2">
                          <div className="h-2 flex-1 rounded-full bg-line">
                            <div className="h-2 rounded-full bg-accent" style={{ width: `${(a.open_loans / maxOpen) * 100}%` }} />
                          </div>
                          <span className="w-8 text-right">{a.open_loans}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}
      </main>
    </>
  );
}

function Kpi({ label, value, tone = "" }: { label: string; value: number; tone?: string }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
