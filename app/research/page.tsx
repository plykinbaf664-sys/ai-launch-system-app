import { Montserrat } from "next/font/google";

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: "700",
});

export default function ResearchPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className={`${montserrat.className} text-4xl font-bold tracking-tight`}>
        Research
      </h1>
      <svg
        aria-hidden="true"
        className="h-16 w-16 text-current"
        fill="none"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="11" cy="11" r="6" stroke="currentColor" strokeWidth="2" />
        <path
          d="M16 16L21 21"
          stroke="currentColor"
          strokeLinecap="round"
          strokeWidth="2"
        />
      </svg>
    </main>
  );
}
