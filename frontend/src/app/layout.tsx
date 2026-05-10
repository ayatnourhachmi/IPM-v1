/**
 * Root layout — fonts, theme bootstrap (no-flash), ThemeProvider.
 */

import type { Metadata } from "next";
import { Toaster } from "sonner";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
    title: "IPM — Innovation Progress Model",
    description: "Innovation portfolio management platform. Submit and manage your business needs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className="light">
            <head>
                {/* Read saved theme before first paint to prevent flash */}
                <script
                    dangerouslySetInnerHTML={{
                        __html: `try{var t=localStorage.getItem('ipm-theme');if(t==='dark')document.documentElement.className='dark';}catch(e){}`,
                    }}
                />
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600&family=DM+Mono:wght@400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&family=Playfair+Display:ital,wght@1,700&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body>
                <ThemeProvider>
                    <div className="theme-utility-tray">
                        <ThemeToggle />
                    </div>
                    {children}
                    <Toaster position="bottom-right" richColors />
                </ThemeProvider>
            </body>
        </html>
    );
}
