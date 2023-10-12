//SPDX-License-Identifier: Unlicense
pragma solidity ^0.7.0;

import "./C.sol";
import "./E/G.sol";
import "./I/K.sol";

contract A {
  uint256 x;
  uint256 y;
  uint256 z;
  B b;
  C c;
  D d;

  constructor(uint256 yval, uint256 zval) {
    x = 0;
    y = yval;
    z = zval;
    b = new B();
    c = new C(zval);
    d = new D(zval);
  }

  function sum() public view returns (uint256) {
    return x+y+z+b.diff()+c.sum()+d.diff();
  }

  function set(uint256 xval) public {
    x = xval;
    c.setX(xval);
  }
}

contract B {
  uint256 x;
  uint256 y;
  G g;
  K k;

  constructor() {
    x = 0;
    y = 6;
    g = new G(x+1);
    k = new K(x+2);
  }

  function diff() public view returns (uint256) {
    return x-y+g.sum();
  }
}
