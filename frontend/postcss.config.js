/**
 * PostCSS compilation engine pipeline configuration.
 * Binds Tailwind CSS directly into the Next.js styling compilation thread.
 */
module.exports = {
  plugins: {
    // Registers Tailwind as an active plugin for styling extraction
    tailwindcss: {},
    // Automatically appends vendor rules for cross-browser enterprise parity
    autoprefixer: {},
  },
};
