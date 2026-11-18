import { CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";

/** Shown right after an owner deletes their restaurant. */
export default function AccountDeleted() {
  return (
    <main className="mx-auto flex min-h-[70dvh] max-w-xl flex-col items-center justify-center px-6 py-16 text-center">
      <CheckCircle2 className="h-14 w-14 text-leaf" strokeWidth={1.6} />
      <h1 className="mt-4 font-display text-3xl font-bold">Your account has been deleted</h1>
      <p className="mt-3 text-ink-soft">Your restaurant, its reviews, replies, settings and your login are gone. There is no balance to pay, and nothing
        more will be charged. We've emailed you a confirmation.</p>
      <p className="mt-3 text-ink-soft">If you didn't mean to do this, contact us straight away.</p>
      <div className="mt-6 flex gap-3">
        <Link to="/" className="rounded-[12px] bg-night px-4 py-2.5 font-semibold text-jasmine">Back to the home page</Link>
        <Link to="/contact" className="rounded-[12px] border-2 border-line px-4 py-2.5 font-semibold">Contact us</Link>
      </div>
    </main>
  );
}
