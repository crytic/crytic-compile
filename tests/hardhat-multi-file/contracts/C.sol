//SPDX-License-Identifier: Unlicense
pragma solidity ^0.7.0;

contract C {
  uint256 x;
  uint256 y;

  constructor(uint256 yval) {
    x = 0;
    y = yval;
  }

  function sum() public view returns (uint256) {
    return x+y;
  }

  function setX(uint256 xval) public {
    x = xval;
  }
}

contract D {
  uint256 x;
  uint256 y;
  C c;

  constructor(uint256 yval) {
    x = 0;
    y = yval;
    c = new C(5);
  }

  function diff() public view returns (uint256) {
    return x-y;
  }
}
