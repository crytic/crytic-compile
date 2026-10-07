// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
// OpenZeppelin 4.9.6 does not have this file
import {IAccessManager} from "@openzeppelin/contracts-v5/access/manager/IAccessManager.sol";

contract Aliased is Ownable {
  IAccessManager public manager;
}
