import type { Metadata } from "next";
import { Instrument_Sans, Newsreader, JetBrains_Mono } from "next/font/google";
import "./globals.css";


const sans = Instrument_Sans({ subsets: ["latin"], variable: "--font-instrument" });
const serif = Newsreader({ subsets: ["latin"], variable: "--font-newsreader" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });

export const metadata: Metadata = {
  title: "Horkos",
  description:
    "An AI guard that enforces your spending rules and holds payments until work is proven.",
  icons: {
    icon: "/horkos%20logo.jpg",
  },
};

// Runs before the page paints, so there is no light/dark flash
const themeScript = `
(function () {
  try {
    var saved = localStorage.getItem("horkos-theme");
    var dark = saved
      ? saved === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${sans.variable} ${serif.variable} ${mono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  );
}