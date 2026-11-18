import { Link } from "react-router-dom";
import { Logo } from "@/components/layout/Logo";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="kolam-dark flex min-h-dvh flex-col items-center justify-center gap-5 px-6 text-center text-jasmine">
      <Logo onDark />
      <h1 className="text-[2.6rem] font-bold">This page isn't on the menu</h1>
      <p className="text-mist">The link may be old, or the page was moved.</p>
      <Link to="/" className={buttonVariants({ size: "lg" })}>Go to the home page</Link>
    </div>
  );
}
