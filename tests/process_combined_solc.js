// Used in hardhat-multi-file and solc-multi-file tests
// Edits the combined_solc.json output file
// Takes only the sourceList (since the contracts themselves are unstable)
//   and in the sourceList filenames, takes only the "[letter].sol" part, rather than the whole thing
//   since the temp dir path isn't going to be the same every run

const fs = require("fs");
const process = require("process");
const fileName = process.argv[2];
const fileData = JSON.parse(fs.readFileSync(fileName));
const toWrite = fileData.sourceList.map((s) => s.substring(s.length-5));
fs.writeFileSync(fileName, JSON.stringify(toWrite));
