/**
 * Project credit footer. Always visible on the dashboard, templates list,
 * admin pages, and the auth screens. Skipped on the full-screen editor
 * workspace where every pixel of vertical space matters.
 */

const REPO_URL = "https://github.com/AmigoUK/BarcodeLabelGen";

export function AppFooter() {
  return (
    <footer className="border-t border-slate-800 bg-slate-950 px-4 py-2 text-center text-[11px] text-slate-500">
      <a href="mailto:dev@attv.uk" className="hover:text-slate-300">
        dev@attv.uk
      </a>
      <span className="mx-2 text-slate-700">·</span>
      <span>Project &amp; Development: Tomasz &lsquo;Amigo&rsquo; Lewandowski</span>
      <span className="mx-2 text-slate-700">·</span>
      <a
        href="https://www.attv.uk"
        target="_blank"
        rel="noreferrer"
        className="hover:text-slate-300"
      >
        www.attv.uk
      </a>
      <span className="mx-2 text-slate-700">·</span>
      <a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-slate-300">
        GitHub
      </a>
    </footer>
  );
}
