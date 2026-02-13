import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import ApolloProviderWrapper from "@/components/ApolloProvider";
import BackendWakeupOnLoad from "@/components/BackendWakeupOnLoad";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "SoundCanvas - AI Music from Images",
  description: "Transform images into unique music compositions with AI",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${outfit.variable} antialiased`}
        style={{ fontFamily: "'Outfit', system-ui, sans-serif" }}
      >
        <ApolloProviderWrapper>
          <BackendWakeupOnLoad />
          {children}
        </ApolloProviderWrapper>
      </body>
    </html>
  );
}
