import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, hint, error, className = "", id, ...rest },
  ref,
) {
  const inputId = id ?? `in-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-slate-200">
          {label}
        </label>
      )}
      <input
        id={inputId}
        ref={ref}
        className={[
          "block w-full rounded-md border bg-slate-900 px-3 py-2 text-sm text-slate-100",
          "placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-400",
          error ? "border-rose-500" : "border-slate-700",
          className,
        ].join(" ")}
        {...rest}
      />
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  );
});
