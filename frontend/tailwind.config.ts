import type { Config } from "tailwindcss";

/**
 * Tailwind CSS configuration engine.
 * Maps out specific layout structures within the InsightX Next.js app directory.
 */
const config: Config = {
  // Scans all domain features, custom hooks, pages, and components for CSS classes
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/core/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // Future custom corporate banking themes or UI colors for InsightX go here
    },
  },
  plugins: [],
};

export default config;
