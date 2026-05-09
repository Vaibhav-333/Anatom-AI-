/** @type {import('next').NextConfig} */
const nextConfig = {
  // ── Compression ─────────────────────────────────────────────────────────────
  // Next.js compresses responses with gzip automatically in production.
  compress: true,

  // ── 3-D / Three.js packages ─────────────────────────────────────────────────
  transpilePackages: ["three"],

  // ── Image optimisation ──────────────────────────────────────────────────────
  images: {
    formats: ["image/avif", "image/webp"],          // prefer modern formats
    minimumCacheTTL: 60 * 60 * 24 * 7,             // 7-day browser cache
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/**",
      },
      {
        protocol: "https",
        // Railway backend
        hostname: "*.up.railway.app",
        pathname: "/**",
      },
      {
        protocol: "https",
        // Render backend
        hostname: "*.onrender.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "images.unsplash.com",
        pathname: "/**",
      },
    ],
  },

  // ── API proxy rewrites ───────────────────────────────────────────────────────
  // NOTE: /api/* is now handled by app/api/[...path]/route.ts (Edge runtime).
  // That handler reads the backend URL at REQUEST TIME (not build time), which
  // is essential for ngrok tunnels whose URLs change on every restart.
  // The rewrite below is intentionally removed — the route handler takes
  // priority and is more robust for dynamic ngrok URLs.

  // ── Security headers ────────────────────────────────────────────────────────
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options",    value: "nosniff" },
          { key: "X-Frame-Options",            value: "DENY" },
          { key: "X-XSS-Protection",           value: "1; mode=block" },
          { key: "Referrer-Policy",            value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(self)",
          },
        ],
      },
      // Long-lived cache for all static 3-D model files
      {
        source: "/assets/:path*.glb",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },

  // ── Webpack optimisations ───────────────────────────────────────────────────
  webpack(config, { isServer }) {
    if (!isServer) {
      // Split Three.js + R3F into its own chunk so the main bundle stays small.
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          ...(config.optimization.splitChunks?.cacheGroups ?? {}),
          three: {
            test: /[\\/]node_modules[\\/](three|@react-three)[\\/]/,
            name: "three-vendor",
            chunks: "all",
            priority: 30,
          },
          recharts: {
            test: /[\\/]node_modules[\\/]recharts[\\/]/,
            name: "recharts-vendor",
            chunks: "all",
            priority: 20,
          },
          framer: {
            test: /[\\/]node_modules[\\/]framer-motion[\\/]/,
            name: "framer-vendor",
            chunks: "all",
            priority: 20,
          },
        },
      };
    }
    return config;
  },
};

export default nextConfig;
