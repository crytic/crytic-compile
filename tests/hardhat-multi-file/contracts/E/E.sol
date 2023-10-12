//SPDX-License-Identifier: Unlicense
pragma solidity ^0.7.0;

import "../C.sol";
import "../I/I.sol";

contract E {
  uint256 x;
  uint256 y;
  D d;

  constructor(uint256 yval) {
    x = 0;
    y = yval;
    d = new D(yval);
  }

  function sum() public view returns (uint256) {
    return x+y+d.diff();
  }

  function setX(uint256 xval) public {
    x = xval;
  }
}
