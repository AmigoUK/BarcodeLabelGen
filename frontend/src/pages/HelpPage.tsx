/**
 * In-app help & FAQ. Renders the canonical Markdown that lives in
 * `docs/HELP.{pl,en}.md` and `docs/FAQ.{pl,en}.md` — same source of
 * truth for both this page and the repo's docs/ folder, so they can't
 * drift apart. Markdown is bundled at build time via Vite's `?raw`
 * import, so there's no runtime fetch.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import helpPl from "../../../docs/HELP.pl.md?raw";
import helpEn from "../../../docs/HELP.en.md?raw";
import faqPl from "../../../docs/FAQ.pl.md?raw";
import faqEn from "../../../docs/FAQ.en.md?raw";

// Screenshots referenced from the markdown live in docs/screenshots/help/;
// Vite bundles them and we rewrite the relative src to the hashed asset URL.
const helpImages = import.meta.glob("../../../docs/screenshots/help/**/*.png", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

function resolveImageSrc(src: string | undefined): string | undefined {
  if (!src) return src;
  const match = Object.entries(helpImages).find(([key]) => key.endsWith(src));
  return match ? match[1] : src;
}

type Tab = "help" | "faq";

export function HelpPage() {
  const { i18n, t } = useTranslation();
  const [tab, setTab] = useState<Tab>("help");

  const lang = i18n.language?.toLowerCase().startsWith("en") ? "en" : "pl";
  const source = useMemo(() => {
    if (tab === "help") return lang === "en" ? helpEn : helpPl;
    return lang === "en" ? faqEn : faqPl;
  }, [tab, lang]);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">{t("help.title")}</h1>
        <div className="flex gap-1 rounded-md border border-slate-800 bg-slate-900/40 p-1">
          <TabBtn active={tab === "help"} onClick={() => setTab("help")}>
            {t("help.tabHelp")}
          </TabBtn>
          <TabBtn active={tab === "faq"} onClick={() => setTab("faq")}>
            {t("help.tabFaq")}
          </TabBtn>
        </div>
      </div>

      <article className="help-prose rounded-lg border border-slate-800 bg-slate-900/30 p-6 leading-relaxed text-slate-200">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            img: ({ src, alt }) => (
              <img
                src={resolveImageSrc(src)}
                alt={alt}
                loading="lazy"
                className="my-3 w-full rounded-md border border-slate-700"
              />
            ),
          }}
        >
          {source}
        </ReactMarkdown>
      </article>
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white",
      ].join(" ")}
    >
      {children}
    </button>
  );
}
