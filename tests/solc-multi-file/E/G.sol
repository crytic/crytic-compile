import "./E.sol";

contract G {
  uint256 x;
  uint256 y;
  E e;

  constructor(uint256 yval) public {
    x = 0;
    y = yval;
    e = new E(5);
  }

  function sum() public view returns (uint256) {
    return e.sum();
  }

  function setX(uint256 xval) public {
    x = xval;
    e.setX(xval+1);
  }
}
