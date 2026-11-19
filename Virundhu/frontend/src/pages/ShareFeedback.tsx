import { EaseCheck } from "@/components/feedback/EaseCheck";
import { FeedbackForm } from "@/components/feedback/FeedbackForm";

/** In-app: the ease-of-use check and the share-feedback form, both read by Isai, the feedback agent. */
export default function ShareFeedbackPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Share feedback</h1>
        <p className="mt-1 text-ink-soft">Tell us how Virundhu is working for you. Isai, our feedback agent, reads every word within a minute; problems go straight to Tara, who replies with the fix.</p>
      </div>
      <section className="rounded-[20px] border-2 border-line bg-white p-6">
        <h2 className="font-display text-xl font-bold">Is Virundhu easy to use?</h2>
        <p className="mb-4 text-sm text-ink-soft">Three quick questions. Your answers decide what we make simpler next.</p>
        <EaseCheck />
      </section>
      <section className="rounded-[20px] border-2 border-line bg-white p-6">
        <h2 className="mb-4 font-display text-xl font-bold">Ideas, problems or praise</h2>
        <FeedbackForm page="/app/feedback" />
      </section>
    </div>
  );
}
