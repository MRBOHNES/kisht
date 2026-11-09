import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin", "devanagari"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Kisht",
  description: "Field collections for overdue loans",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="hi" className={`${poppins.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
