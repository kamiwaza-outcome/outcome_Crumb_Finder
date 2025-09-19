import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  reactStrictMode: false,
  webpack: (config, { dev }) => {
    if (dev) {
      // Disable React DevTools in development
      config.resolve.alias = {
        ...config.resolve.alias,
        'react-devtools-core': false,
        'react-devtools': false,
      };
    }
    return config;
  },
};

export default nextConfig;
