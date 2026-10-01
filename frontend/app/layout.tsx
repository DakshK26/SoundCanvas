// Root layout: Next.js wraps every route (app/page.tsx and app/playground/page.tsx) in this.
// It loads the Outfit font and globals.css, sets the page title, and puts the Apollo provider
// from components/ApolloProvider.tsx around every page so they can all talk to the API.

import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import ApolloProviderWrapper from "@/components/ApolloProvider";

// next/font downloads the font at build time and serves it from this site. The variable option
// exposes it as the CSS variable --font-outfit, which globals.css can then use.
const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

// Next.js turns this into the <title>, description and favicon tags in <head>.
export const metadata: Metadata = {
  title: "SoundCanvas - AI Music from Images",
  description: "Transform images into unique music compositions with AI",
  icons: {
    icon: "/icon.svg",
  },
};

// children is whichever page matches the current URL.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${outfit.variable} antialiased`}>
        <ApolloProviderWrapper>
          {children}
        </ApolloProviderWrapper>
      </body>
    </html>
  );
}
