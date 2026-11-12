import type {Metadata} from "next";
import {AuthProvider} from "@/lib/auth";
import {Shell} from "@/components/layout/shell";
import "./globals.css";

export const metadata: Metadata = {
  title: {default: "Framewise · Movie Intelligence", template: "%s · Framewise"},
  description: "Local movie discovery with audience evidence, personal recommendations and grounded conversation.",
  icons: {icon: "/favicon.svg"},
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Shell>{children}</Shell>
        </AuthProvider>
      </body>
    </html>
  );
}
