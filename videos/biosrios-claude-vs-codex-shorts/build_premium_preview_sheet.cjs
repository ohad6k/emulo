const path = require("node:path");

const root = __dirname;
const expectedSharpVersion = "0.34.5";

function loadSharp() {
  let modulePath;

  try {
    modulePath = require.resolve("sharp");
  } catch {
    const injectedModule = process.env.BIOSRIOS_SHARP_MODULE;
    if (injectedModule) {
      try {
        modulePath = require.resolve(injectedModule);
      } catch (error) {
        throw new Error(
          `Unable to resolve BIOSRIOS_SHARP_MODULE "${injectedModule}": ${error.message}`,
        );
      }
    }
  }

  if (!modulePath) {
    throw new Error(
      `Unable to resolve Sharp ${expectedSharpVersion}. Install sharp@${expectedSharpVersion} in the project/workspace or set BIOSRIOS_SHARP_MODULE to its module path.`,
    );
  }

  const sharp = require(modulePath);
  const loadedVersion = sharp.versions?.sharp ?? "unknown";
  if (loadedVersion !== expectedSharpVersion) {
    throw new Error(
      `Premium preview builder requires Sharp exactly ${expectedSharpVersion}, but loaded ${loadedVersion} from ${modulePath}.`,
    );
  }

  return sharp;
}

const sharp = loadSharp();
const frameTimes = {
  s01: ["0.5", "3.5", "7.5", "12.5", "19.5", "26.5", "34", "38.5", "41"],
  s02: ["0.5", "3.5", "10.5", "14.5", "20.5", "26.5", "33", "36", "37.5"],
  s03: ["0.5", "3.5", "7.5", "13.5", "19.5", "25.8", "32", "36.5", "39"],
};

const inputs = [];
for (let row = 0; row < 9; row += 1) {
  for (const id of ["s01", "s02", "s03"]) {
    const time = frameTimes[id][row];
    inputs.push(
      path.join(
        root,
        `snapshots-premium-${id}`,
        `frame-${String(row).padStart(2, "0")}-at-${time}s.png`,
      ),
    );
  }
}

async function build() {
  const tileWidth = 360;
  const tileHeight = 640;
  const composites = [];

  for (let index = 0; index < inputs.length; index += 1) {
    const tile = await sharp(inputs[index])
      .resize(tileWidth - 8, tileHeight - 8, { fit: "cover" })
      .jpeg({ quality: 90, chromaSubsampling: "4:4:4" })
      .toBuffer();

    composites.push({
      input: tile,
      left: (index % 3) * tileWidth + 4,
      top: Math.floor(index / 3) * tileHeight + 4,
    });
  }

  await sharp({
    create: {
      width: tileWidth * 3,
      height: tileHeight * 9,
      channels: 3,
      background: "#171714",
    },
  })
    .composite(composites)
    .jpeg({ quality: 92, chromaSubsampling: "4:4:4" })
    .toFile(path.join(root, "SHORTS-PREVIEW-CONTACT-SHEET-PREMIUM.jpg"));
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
