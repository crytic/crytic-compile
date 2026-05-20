"""
Library utilities for dependency resolution and auto-linking
"""


def get_deployment_order(
    dependencies: dict[str, list[str]], target_contracts: list[str]
) -> tuple[list[str], set[str]]:
    """Get deployment order using topological sorting (Kahn's algorithm)

    Args:
        dependencies: Dict mapping contract_name -> [required_libraries]
        target_contracts: List of target contracts to prioritize

    Raises:
        ValueError: if a circular dependency is identified

    Returns:
        Tuple of (deployment_order, libraries_needed)
    """
    # Build complete dependency graph
    all_contracts = set(dependencies.keys())
    for deps in dependencies.values():
        all_contracts.update(deps)

    # Calculate in-degrees
    in_degree = {contract: 0 for contract in all_contracts}
    for contract, deps in dependencies.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[contract] += 1

    # Initialize queue with nodes that have no dependencies
    queue = [contract for contract in all_contracts if in_degree[contract] == 0]

    result = []
    libraries_needed = set()

    deployment_order = []

    while queue:
        # Sort queue to prioritize libraries first, then target contracts in order
        queue.sort(
            key=lambda x: (
                x in target_contracts,  # Libraries (False) come before targets (True)
                target_contracts.index(x) if x in target_contracts else 0,  # Target order
            )
        )

        current = queue.pop(0)
        result.append(current)

        # Check if this is a library (not in target contracts but required by others)
        if current not in target_contracts:
            libraries_needed.add(current)
            deployment_order.append(current)  # Only add libraries to deployment order

        # Update in-degrees for dependents
        for contract, deps in dependencies.items():
            if current in deps:
                in_degree[contract] -= 1
                if in_degree[contract] == 0 and contract not in result:
                    queue.append(contract)

    # Check for circular dependencies
    if len(result) != len(all_contracts):
        remaining = all_contracts - set(result)
        raise ValueError(f"Circular dependency detected involving: {remaining}")

    return deployment_order, libraries_needed


def generate_library_addresses(
    libraries_needed: set[str], start_address: int = 0xA070
) -> dict[str, int]:
    """Generate sequential addresses for libraries

    Args:
        libraries_needed: Set of library names that need addresses
        start_address: Starting address (default 0xa070, resembling "auto")

    Returns:
        Dict mapping library_name -> address
    """
    library_addresses = {}
    current_address = start_address

    # Sort libraries for consistent ordering
    for library in sorted(libraries_needed):
        library_addresses[library] = current_address
        current_address += 1

    return library_addresses
