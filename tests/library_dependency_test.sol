// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Simple library with no dependencies
library MathLib {
    function add(uint256 a, uint256 b) external pure returns (uint256) {
        return a + b;
    }

    function multiply(uint256 a, uint256 b) external pure returns (uint256) {
        return a * b;
    }
}

// Library that depends on MathLib
library AdvancedMath {
    function square(uint256 a) external pure returns (uint256) {
        return MathLib.multiply(a, a);
    }

    function addAndSquare(uint256 a, uint256 b) external pure returns (uint256) {
        uint256 sum = MathLib.add(a, b);
        return MathLib.multiply(sum, sum);
    }
}

// Library that depends on both MathLib and AdvancedMath
library ComplexMath {
    function complexOperation(uint256 a, uint256 b) external pure returns (uint256) {
        uint256 squared = AdvancedMath.square(a);
        return MathLib.add(squared, b);
    }

    function megaOperation(uint256 a, uint256 b, uint256 c) external pure returns (uint256) {
        uint256 result1 = AdvancedMath.addAndSquare(a, b);
        uint256 result2 = MathLib.multiply(result1, c);
        return result2;
    }
}

// Contract that uses ComplexMath (which transitively depends on others)
contract TestComplexDependencies {
    uint256 public result;

    constructor() {
        result = 0;
    }

    function performComplexCalculation(uint256 a, uint256 b, uint256 c) public {
        result = ComplexMath.megaOperation(a, b, c);
    }

    function performSimpleCalculation(uint256 a, uint256 b) public {
        result = ComplexMath.complexOperation(a, b);
    }

    function getResult() public view returns (uint256) {
        return result;
    }
}

// Another contract that only uses MathLib directly
contract SimpleMathContract {
    uint256 public value;

    constructor(uint256 _initial) {
        value = _initial;
    }

    function addValue(uint256 _amount) public {
        value = MathLib.add(value, _amount);
    }

    function multiplyValue(uint256 _factor) public {
        value = MathLib.multiply(value, _factor);
    }
}

// Contract that uses multiple libraries at the same level
contract MultiLibraryContract {
    uint256 public simpleResult;
    uint256 public advancedResult;

    function calculate(uint256 a, uint256 b) public {
        simpleResult = MathLib.add(a, b);
        advancedResult = AdvancedMath.square(a);
    }
}