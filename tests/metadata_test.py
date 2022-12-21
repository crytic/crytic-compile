import sys
import json
from crytic_compile import CryticCompile

crytic_compile_instance = CryticCompile(
    '0x6B175474E89094C44Da98b954EedeAC495271d0F', # Dai
    etherscan_api_key=sys.argv[1]
)
# There is only 1 compilation unit
compilation_unit = list(crytic_compile_instance.compilation_units.values())[0]

# print out the parsed metadata
print(json.dumps(compilation_unit.metadata_of('Dai')))
