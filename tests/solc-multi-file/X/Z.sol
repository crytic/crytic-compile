import "./X.sol";

contract Z {
  uint256 y;
  X x;

  constructor(uint256 yval) public {
    y = yval;
    x = new X(5);
  }

  function sum() public view returns (uint256) {
    return x.sum();
  }

  function setX(uint256 xval) public {
    x.setX(xval+1);
  }
}
