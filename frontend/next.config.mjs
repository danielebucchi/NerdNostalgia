/** @type {import('next').NextConfig} */
const nextConfig = {
  // Bundle minimale per Docker prod (richiesto da Dockerfile.prod)
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "7373", pathname: "/static/**" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
