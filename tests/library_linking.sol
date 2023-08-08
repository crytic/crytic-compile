library NeedsLinkingA {
    function testA() external pure returns (uint) {
        return type(uint).max;
    }
}
library NeedsLinkingB {
    function testB() external pure returns (uint) {
        return type(uint).min;
    }
}
contract TestLibraryLinking {
    function test() external {
        NeedsLinkingA.testA();
        NeedsLinkingB.testB();
    }
}
