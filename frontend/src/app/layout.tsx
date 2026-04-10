import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reading and Writing Adventure",
  description: "MVP scaffold for the local reading app",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
