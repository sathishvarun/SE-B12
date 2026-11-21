import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { SiteLayout } from "@/components/site/SiteLayout";
import { PageTitle } from "@/components/layout/PageTitle";
import Home from "@/pages/site/Home";

// Signed-in screens load only when needed, so the landing page stays light.
const HowItWorks = lazy(() => import("@/pages/site/HowItWorks"));
const About = lazy(() => import("@/pages/site/About"));
const PricingPage = lazy(() => import("@/pages/site/PricingPage"));
const Compare = lazy(() => import("@/pages/site/Compare"));
const WhatsNext = lazy(() => import("@/pages/site/WhatsNext"));
const DemoBooking = lazy(() => import("@/pages/site/DemoBooking"));
const Contact = lazy(() => import("@/pages/site/Contact"));
const PrivacyPage = lazy(() => import("@/pages/site/Legal").then((m) => ({ default: m.PrivacyPage })));
const TermsPage = lazy(() => import("@/pages/site/Legal").then((m) => ({ default: m.TermsPage })));
const DataProcessingPage = lazy(() => import("@/pages/site/Legal").then((m) => ({ default: m.DataProcessingPage })));
const AccountDeleted = lazy(() => import("@/pages/site/AccountDeleted"));
const RefundsPage = lazy(() => import("@/pages/site/Legal").then((m) => ({ default: m.RefundsPage })));
const SecurityPage = lazy(() => import("@/pages/site/Legal").then((m) => ({ default: m.SecurityPage })));
const ForgotPasswordPage = lazy(() => import("@/pages/AuthPages").then((m) => ({ default: m.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import("@/pages/AuthPages").then((m) => ({ default: m.ResetPasswordPage })));
const AppLayout = lazy(() => import("@/components/layout/AppLayout").then((m) => ({ default: m.AppLayout })));
const LoginPage = lazy(() => import("@/pages/AuthPages").then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import("@/pages/AuthPages").then((m) => ({ default: m.RegisterPage })));
const InvitePage = lazy(() => import("@/pages/JoinPages").then((m) => ({ default: m.InvitePage })));
const AuthCallbackPage = lazy(() => import("@/pages/JoinPages").then((m) => ({ default: m.AuthCallbackPage })));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Inbox = lazy(() => import("@/pages/Inbox"));
const Alerts = lazy(() => import("@/pages/Alerts"));
const AddReviews = lazy(() => import("@/pages/AddReviews"));
const Connections = lazy(() => import("@/pages/Connections"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));
const Automation = lazy(() => import("@/pages/Automation"));
const FeedbackPage = lazy(() => import("@/pages/Feedback"));
const Ask = lazy(() => import("@/pages/Ask"));
const Billing = lazy(() => import("@/pages/Billing"));
const Support = lazy(() => import("@/pages/Support"));
const ShareFeedbackPage = lazy(() => import("@/pages/ShareFeedback"));
const ShareFeedback = lazy(() => import("@/pages/site/ShareFeedback"));
const Insights = lazy(() => import("@/pages/Insights"));
const AiUsage = lazy(() => import("@/pages/AiUsage"));
const Branches = lazy(() => import("@/pages/Branches"));
const Widget = lazy(() => import("@/pages/site/Widget"));
const ReceiptPage = lazy(() => import("@/pages/Receipt"));
const AiStaffPage = lazy(() => import("@/pages/AiStaff"));
const Admin = lazy(() => import("@/pages/Admin"));
const NotFound = lazy(() => import("@/pages/NotFound"));

export default function App() {
  return (
    <Suspense fallback={<div className="min-h-dvh" aria-busy="true" />}>
      <PageTitle />
      <Routes>
        <Route path="/w/:token" element={<Widget />} />
        <Route element={<SiteLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/about" element={<About />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/whats-next" element={<WhatsNext />} />
          <Route path="/demo/:token" element={<DemoBooking />} />
          <Route path="/share-feedback" element={<ShareFeedback />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/data-processing" element={<DataProcessingPage />} />
          <Route path="/account-deleted" element={<AccountDeleted />} />
          <Route path="/refunds" element={<RefundsPage />} />
          <Route path="/security" element={<SecurityPage />} />
        </Route>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/invite/:token" element={<InvitePage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/f/:token" element={<FeedbackPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="ai-staff" element={<AiStaffPage />} />
            <Route path="inbox" element={<Inbox />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="import" element={<AddReviews />} />
            <Route path="connections" element={<Connections />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="billing" element={<Billing />} />
            <Route path="receipt/:id" element={<ReceiptPage />} />
            <Route path="ask" element={<Ask />} />
            <Route path="insights" element={<Insights />} />
            <Route path="usage" element={<AiUsage />} />
            <Route path="branches" element={<Branches />} />
            <Route path="support" element={<Support />} />
            <Route path="feedback" element={<ShareFeedbackPage />} />
            <Route path="automation" element={<Automation />} />
            <Route path="admin" element={<Admin />} />
            <Route path="admin/:section" element={<Admin />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
