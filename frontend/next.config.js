/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Support output standalone for lightweight container deployments
  output: "standalone",
  // Proxy backend API requests during dev
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
