import { forwardRef } from "react";
import type { ReactNode, SelectHTMLAttributes } from "react";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  children: ReactNode;
};

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { label, className = "", id, children, ...rest },
  ref,
) {
  const selectId = id ?? `sel-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-slate-200">
          {label}
        </label>
      )}
      <select
        id={selectId}
        ref={ref}
        className={[
          "block w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100",
          "focus:outline-none focus:ring-2 focus:ring-indigo-400",
          className,
        ].join(" ")}
        {...rest}
      >
        {children}
      </select>
    </div>
  );
});
