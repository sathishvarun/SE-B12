import { Eye, EyeOff } from "lucide-react";
import { forwardRef, useCallback, useEffect, useRef, useState, type InputHTMLAttributes, type ReactNode, type Ref } from "react";
import { cn } from "@/lib/utils";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string | null;
  icon?: ReactNode;
}

/**
 * A password box that never writes the password into the page's HTML.
 * React normally copies a controlled input's value into the HTML "value" attribute, where anyone looking at the
 * browser's Elements panel can read it. Here the box is uncontrolled: the typed text lives only in the input itself,
 * and the parent still gets every change through onChange. If the parent clears its state, the box is cleared too.
 */
export const SecretInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ value, defaultValue, ...props }, ref) => {
  const inner = useRef<HTMLInputElement | null>(null);
  const setRefs = useCallback((node: HTMLInputElement | null) => {
    inner.current = node;
    if (typeof ref === "function") ref(node);
    else if (ref) (ref as { current: HTMLInputElement | null }).current = node;
  }, [ref]);
  useEffect(() => {
    const el = inner.current;
    const want = value === undefined || value === null ? undefined : String(value);
    if (el && want !== undefined && el.value !== want) el.value = want;
  }, [value]);
  void defaultValue;
  return <input ref={setRefs as Ref<HTMLInputElement>} {...props} />;
});
SecretInput.displayName = "SecretInput";

/** Labelled input with optional icon, hint, error and show/hide for passwords. */
export const Field = forwardRef<HTMLInputElement, FieldProps>(({ label, hint, error, icon, id, type, className, ...props }, ref) => {
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  const Input = isPassword ? SecretInput : "input";
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink">{label}</label>
      <div className="relative">
        {icon ? <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-soft">{icon}</span> : null}
        <Input
          ref={ref}
          id={id}
          type={isPassword && show ? "text" : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined}
          className={cn(
            "h-12 w-full rounded-[12px] border-2 border-line bg-white text-[0.98rem] text-ink transition-colors",
            "placeholder:text-ink-soft/55 focus:border-night focus:outline-none focus-visible:outline-none",
            icon ? "pl-11" : "pl-4", isPassword ? "pr-12" : "pr-4",
            error && "border-chilli focus:border-chilli",
          )}
          {...props}
        />
        {isPassword ? (
          <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-ink-soft hover:text-ink cursor-pointer">
            {show ? <EyeOff className="h-[18px] w-[18px]" /> : <Eye className="h-[18px] w-[18px]" />}
          </button>
        ) : null}
      </div>
      {error ? <p id={`${id}-err`} className="mt-1.5 text-sm font-medium text-chilli">{error}</p>
        : hint ? <p id={`${id}-hint`} className="mt-1.5 text-sm text-ink-soft">{hint}</p> : null}
    </div>
  );
});
Field.displayName = "Field";
