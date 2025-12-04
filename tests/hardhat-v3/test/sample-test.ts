import { expect } from "chai";
import hre from "hardhat";

describe("Greeter", function() {
    
  it("Should return the new greeting once it's changed", async function() {
    let n = await hre.network.connect();
    const Greeter = await n.ethers.getContractFactory("Greeter");
    const greeter = await Greeter.deploy("Hello, world!");
    
    await greeter.waitForDeployment();
    expect(await greeter.greet()).to.equal("Hello, world!");

    await greeter.setGreeting("Hola, mundo!");
    expect(await greeter.greet()).to.equal("Hola, mundo!");
  });
});

