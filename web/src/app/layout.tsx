import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IdeaRadar - SaaS Idea Finder",
  description: "Discover validated SaaS ideas from Twitter",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
