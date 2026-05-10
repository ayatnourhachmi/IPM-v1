/** @type {import('next').NextConfig} */
const nextConfig = {
    // Avoid output: "standalone" here — it breaks App Router on Vercel (404).
    reactStrictMode: true,
};

module.exports = nextConfig;
