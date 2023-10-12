//SPDX-License-Identifier: Unlicense
pragma solidity ^0.7.0;

import "./I.sol";

contract K {
  uint256 x;
  uint256 y;
  I i;

  constructor(uint256 yval) {
    x = 0;
    y = yval;
    i = new I(5);
  }

  function sum() public view returns (uint256) {
    return i.sum();
  }

  function setX(uint256 xval) public {
    x = xval;
    i.setX(xval+1);
  }
}
