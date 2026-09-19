/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server bundle (server.js + traced dependencies) for the
  // production Docker image — the runtime stage then ships only what's needed.
  output: "standalone",
};

export default nextConfig;
