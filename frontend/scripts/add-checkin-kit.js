// Copies the standalone check-in kit (../checkin-kit) into build/pass so it is
// served at /pass/. Skipped when the kit isn't present, e.g. in the Docker build.
const fs = require("fs");
const path = require("path");

const src = path.resolve(__dirname, "../../checkin-kit");
const dest = path.resolve(__dirname, "../build/pass");

if (!fs.existsSync(src)) {
  console.log("checkin-kit not found, skipping /pass");
  process.exit(0);
}
fs.cpSync(src, dest, {
  recursive: true,
  filter: (file) => !["vercel.json", "README.md"].includes(path.basename(file)),
});
console.log("Copied checkin-kit to build/pass");
