function parse(input) {
  return JSON.parse(input);
}

function stringify(value) {
  return JSON.stringify(value);
}

module.exports = { parse, stringify };
