/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark theme. "paper"/"ink" keep their names from the light
        // version (so every component that references them needs zero
        // changes) but now mean "background" / "primary text" instead of
        // literally paper-colored and ink-colored.
        ink: "#EDEEE9", // primary text - soft ivory, not stark white (easier on the eyes)
        paper: "#16181A", // background - near-black with a touch of warmth, not pure black
        slate: "#22252A", // panels / hover states - a lifted dark surface
        signal: "#E3A757", // awaiting approval / pending - brightened amber for dark-bg contrast
        moss: "#6FA383", // approved / sent / success - brightened green
        rust: "#DD7E5F", // high risk / rejected / error - brightened terracotta-red
        mist: "#82AFD1", // low risk / informational - brightened dusty blue
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["\"Work Sans\"", "system-ui", "sans-serif"],
        mono: ["\"IBM Plex Mono\"", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};