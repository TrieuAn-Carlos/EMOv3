import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EMO - AI Personal Assistant",
  description: "Your intelligent personal assistant powered by AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
