import { used } from "./lib.js";
import render from "./view.js";

const { parse } = require("./cjs.js");

used();
render();
parse("{}");
import("./lazy.js");
