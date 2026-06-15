/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "7373", pathname: "/static/**" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
