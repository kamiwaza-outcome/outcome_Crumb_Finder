import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  reactStrictMode: false,
  eslint: {
    // Ignore ESLint errors during production builds
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Ignore TypeScript errors during production builds
    ignoreBuildErrors: true,
  },
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
