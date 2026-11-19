import { FeedbackForm } from "@/components/feedback/FeedbackForm";
import { PageHero } from "@/components/site/SiteLayout";

export default function ShareFeedback() {
  return (
    <>
      <PageHero title="Tell us what you think" intro="Tried Virundhu, saw the demo, or just looked around? Ideas, problems and praise all help. Leave your email if you'd like a reply." />
      <section className="mx-auto max-w-4xl px-5 py-14 sm:px-8">
        <div className="rounded-[24px] border-2 border-night bg-white p-6 shadow-[8px_8px_0_#0c3b2e] sm:p-8">
          <FeedbackForm publicForm page="/share-feedback" />
        </div>
      </section>
    </>
  );
}
