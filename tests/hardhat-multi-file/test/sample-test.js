const { expect } = require("chai");

describe("example test", function() {
  it("A", async function() {
    const A = await ethers.getContractFactory("A");
    const a = await A.deploy(100,101);
    
    await a.deployed();
    expect(await a.sum()).to.equal(195);

    await a.set(50);
    expect(await a.sum()).to.equal(295);
  });
});
