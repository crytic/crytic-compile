import "../C.sol";
import "../E/E.sol";

contract I {
  uint256 x;
  uint256 y;
  D d;
  E e;

  constructor(uint256 yval) public {
    x = 0;
    y = yval;
    d = new D(yval);
    e = new E(yval+1);
  }

  function sum() public view returns (uint256) {
    return x+y+d.diff()+e.sum();
  }

  function setX(uint256 xval) public {
    x = xval;
    e.setX(y);
  }
}
