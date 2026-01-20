import hre from 'hardhat'

async function main (): Promise<void> {
  const n = await hre.network.connect()

  const Greeter = await n.ethers.getContractFactory('Greeter')
  const greeter = await Greeter.deploy('Hello, Hardhat!')

  await greeter.waitForDeployment()

  console.log('Greeter deployed to:', await greeter.getAddress())
}

main()
  .then(() => process.exit(0))
  .catch(error => {
    console.error(error)
    process.exit(1)
  })
